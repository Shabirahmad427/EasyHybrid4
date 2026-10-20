"""Native smoke for the real EasyHybridApplication and MainWindow.

This is separate from the pDynamo-independent menu/VisMol component smoke.
It requires a compiled pDynamo3 installation and a real GTK display.
"""

import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

import pytest


_FULL_APP_CYCLE = textwrap.dedent(
    r"""
    import os
    import sys
    import time

    from src.os_integration.gtk_startup import configure_startup_environment
    configure_startup_environment(os.path.abspath("."))
    from OpenGL import GL

    import gi
    gi.require_version("Gtk", "4.0")
    gi.require_version("Gdk", "4.0")
    from gi.repository import Gdk, GLib, Gtk

    import easyhybrid
    from pCore import logFile

    display = Gdk.Display.get_default()
    if display is None:
        raise RuntimeError("Full EasyHybrid smoke requires a native GTK display")

    fixture = os.path.abspath(sys.argv[1])
    app = easyhybrid.EasyHybridApplication()
    state = {
        "started": time.monotonic(), "scene_draws": 0,
        "core_renders": 0, "phase": "application_start", "picked": False,
    }

    def fail(message):
        print("EASYHYBRID_FULL_APP_ERROR=" + message, flush=True)
        app.quit()
        return GLib.SOURCE_REMOVE

    def poll_app():
        main = getattr(app, "main_window", None)
        if main is None:
            if time.monotonic() - state["started"] > 35:
                return fail("EasyHybridApplication did not create MainWindow")
            return GLib.SOURCE_CONTINUE

        vm_session = main.vm_session
        if not state.get("observing"):
            if main.window.get_application() != app:
                return fail("production MainWindow is not attached to EasyHybridApplication")
            if not isinstance(main, easyhybrid.MainWindow):
                return fail("application did not construct the production MainWindow")
            state["observing"] = True
            state["phase"] = "main_window_ready"
            print("EASYHYBRID_FULL_APP_MAIN_WINDOW=True", flush=True)

        # The fixture is supplied as a normal command-line open request. The
        # real application forwards it to EasyHybridSession.load() after the
        # MainWindow and pDynamo session are ready.
        if not vm_session.vm_objects_dic or not main.p_session.psystem:
            if main.p_session.psystem and not state.get("system_seen"):
                state["system_seen"] = time.monotonic()
            if (
                state.get("system_seen")
                and time.monotonic() - state["system_seen"] > 3
            ):
                return fail(
                    "pDynamo system loaded but no VisMol object was attached "
                    "(systems=%d objects=%d)"
                    % (len(main.p_session.psystem), len(vm_session.vm_objects_dic))
                )
            if time.monotonic() - state["started"] > 35:
                return fail(
                    "startup fixture did not load through EasyHybridSession.load; "
                    "pending=%r systems=%d objects=%d"
                    % (app.pending_open_files, len(main.p_session.psystem),
                       len(vm_session.vm_objects_dic))
                )
            return GLib.SOURCE_CONTINUE

        if not state.get("scene_ready"):
            state["phase"] = "initializing_gl_area"
            vm_widget = vm_session.vm_widget
            core = vm_session.vm_glcore
            vm_widget.make_current()
            context_error = vm_widget.get_error()
            if context_error is not None:
                return fail("production MainWindow GLArea failed: %s" % context_error)

            gl_version = GL.glGetString(GL.GL_VERSION)
            gl_renderer = GL.glGetString(GL.GL_RENDERER)
            if not gl_version or not gl_renderer:
                return fail("production MainWindow has no current OpenGL context")
            state["gl_version"] = bytes(gl_version)
            state["gl_renderer"] = bytes(gl_renderer)

            render_core = core.render

            def count_core_render(*args, **kwargs):
                state["core_renders"] += 1
                return render_core(*args, **kwargs)

            core.render = count_core_render

            molecule = next(iter(vm_session.vm_objects_dic.values()))
            atoms = list(molecule.atoms.values())
            oxygen = next((atom for atom in atoms if atom.symbol == "O"), None)
            if oxygen is None:
                return fail("loaded pDynamo-backed molecule has no oxygen atom")
            if len(atoms) != 3:
                return fail("expected 3 fixture atoms, got %d" % len(atoms))
            if len(molecule.bonds) < 2:
                return fail("expected 2 inferred water bonds, got %d" % len(molecule.bonds))

            for representation in molecule.representations.values():
                if representation is None or not representation.active:
                    continue
                draw = representation.draw_representation

                def count_draw(draw=draw):
                    draw()
                    state["scene_draws"] += 1

                representation.draw_representation = count_draw

            state.update(molecule=molecule, oxygen=oxygen, scene_ready=True)
            state["phase"] = "waiting_for_scene_render"
            active_representations = [
                name for name, representation in molecule.representations.items()
                if representation is not None and representation.active
            ]
            print(
                "EASYHYBRID_FULL_APP_GLAREA="
                "realized:%s,mapped:%s,visible:%s,size:%sx%s,active:%s"
                % (
                    vm_widget.get_realized(), vm_widget.get_mapped(),
                    vm_widget.get_visible(), vm_widget.get_width(),
                    vm_widget.get_height(), ",".join(active_representations),
                ),
                flush=True,
            )
            vm_widget.queue_render()
            return GLib.SOURCE_CONTINUE

        if state["scene_draws"] == 0:
            return GLib.SOURCE_CONTINUE

        if not state.get("pick_started"):
            state["phase"] = "waiting_for_pick"
            from gui.windows.builder.click_mode import _project_local_point_to_pixel

            vm_widget = vm_session.vm_widget
            core = vm_session.vm_glcore
            widget_width, widget_height = vm_widget.get_width(), vm_widget.get_height()
            if min(widget_width, widget_height, core.width, core.height) <= 0:
                state["phase"] = "waiting_for_gl_area_allocation"
                vm_widget.queue_render()
                return GLib.SOURCE_CONTINUE
            px, py, _depth = _project_local_point_to_pixel(
                core, state["molecule"], state["oxygen"].coords(vm_session.frame)
            )
            if px is None:
                return fail("fixture oxygen is behind the production camera")
            # Use the latest measured projection directly. Camera centering
            # is animated asynchronously and may keep moving while low-FPS
            # software renderers service the main loop; requiring a stable
            # coordinate can starve this integration smoke without testing a
            # user-visible behavior.
            x = px * widget_width / core.width
            y = py * widget_height / core.height
            state["pick_dimensions"] = (
                widget_width, widget_height, core.width, core.height
            )
            state["pick_projection"] = (round(px, 5), round(py, 5))

            class TestGesture:
                def __init__(self, x, y):
                    self.x, self.y = x, y

                def get_current_button(self):
                    return 1

                def get_current_event_state(self):
                    return Gdk.ModifierType(0)

                def get_current_event(self):
                    return None

            gesture = TestGesture(x, y)
            vm_widget._on_mouse_pressed(gesture, 1, x, y)
            vm_widget._on_mouse_released(gesture, 1, x, y)
            state["pick_started"] = True
            state["pick_attempts"] = state.get("pick_attempts", 0) + 1
            vm_widget.queue_render()
            return GLib.SOURCE_CONTINUE

        core = vm_session.vm_glcore
        if core.picking:
            return GLib.SOURCE_CONTINUE
        picked = core.atom_picked
        if picked is None or picked.symbol != "O":
            if state.get("pick_attempts", 0) < 5:
                core.atom_picked = None
                state["pick_started"] = False
                vm_session.vm_widget.queue_render()
                return GLib.SOURCE_CONTINUE
            return fail("production MainWindow GTK gesture pick missed oxygen: %r" % picked)

        vm_session.vm_widget.make_current()
        gl_error = GL.glGetError()
        if gl_error != GL.GL_NO_ERROR:
            return fail("production scene left OpenGL error 0x%x" % gl_error)

        print("EASYHYBRID_FULL_APP_PICK=O:%s" % picked.atom_id, flush=True)
        print("EASYHYBRID_FULL_APP_SYSTEMS=%d" % len(main.p_session.psystem), flush=True)
        system = next(iter(main.p_session.psystem.values()))
        print("EASYHYBRID_FULL_APP_SYSTEM_LABEL=%s" % system.label, flush=True)
        print("EASYHYBRID_FULL_APP_ATOMS=%d" % len(state["molecule"].atoms), flush=True)
        print("EASYHYBRID_FULL_APP_SCENE_DRAWS=%d" % state["scene_draws"], flush=True)
        print("EASYHYBRID_FULL_APP_GL_VERSION=%s" % state["gl_version"].decode("ascii", "replace"), flush=True)
        print("EASYHYBRID_FULL_APP_GL_RENDERER=%s" % state["gl_renderer"].decode("utf-8", "replace"), flush=True)

        # A newly loaded system is dirty by design and would open the real
        # save-confirmation dialog. This renderer regression discards only its
        # temporary fixture, then follows MainWindow's standard close handler.
        main.p_session.changed = False
        main.window.close()
        main.window.set_visible(False)
        state["closed"] = True
        app.quit()
        return GLib.SOURCE_REMOVE

    def safe_poll_app():
        try:
            return poll_app()
        except Exception as error:
            import traceback
            traceback.print_exc()
            return fail("full-app callback raised %s: %s" % (
                type(error).__name__, error
            ))

    GLib.timeout_add(50, safe_poll_app)

    def lifecycle_timeout():
        main = getattr(app, "main_window", None)
        widget = getattr(getattr(main, "vm_session", None), "vm_widget", None)
        if widget is None:
            details = "gl_area=unavailable"
        else:
            molecule = state.get("molecule")
            active = [] if molecule is None else [
                name for name, representation in molecule.representations.items()
                if representation is not None and representation.active
            ]
            details = (
                "gl_area(realized=%s,mapped=%s,visible=%s,size=%sx%s) "
                "core_renders=%s scene_draws=%s active=%s picking=%s "
                "pick_xy=%r pick_dimensions=%r pick_attempts=%s "
                "pick_projection=%r atom_picked=%r"
                % (
                    widget.get_realized(), widget.get_mapped(),
                    widget.get_visible(), widget.get_width(), widget.get_height(),
                    state["core_renders"], state["scene_draws"], ",".join(active),
                    getattr(main.vm_session.vm_glcore, "picking", None),
                    (
                        getattr(main.vm_session.vm_glcore, "picking_x", None),
                        getattr(main.vm_session.vm_glcore, "picking_y", None),
                    ),
                    state.get("pick_dimensions"),
                    state.get("pick_attempts", 0),
                    state.get("pick_projection"),
                    getattr(
                        getattr(main.vm_session.vm_glcore, "atom_picked", None),
                        "name", None,
                    ),
                )
            )
        return fail(
            "full-app lifecycle timed out phase=%s %s" %
            (state["phase"], details)
        )

    GLib.timeout_add_seconds(45, lifecycle_timeout)
    status = app.run([sys.argv[0], fixture])
    print("EASYHYBRID_FULL_APP_STATUS=%d CLOSED=%s" % (status, state.get("closed")), flush=True)
    if status != 0 or not state.get("closed"):
        raise SystemExit(2)
    """
)


def _write_water_pdb(path):
    lines = []
    for serial, name, x, y, z, element in (
        (1, "O", 0.000, 0.000, 0.000, "O"),
        (2, "H1", 0.957, 0.000, 0.000, "H"),
        (3, "H2", -0.240, 0.927, 0.000, "H"),
    ):
        lines.append(
            "ATOM  %5d %-4s HOH A%4d    %8.3f%8.3f%8.3f%6.2f%6.2f          %2s  "
            % (serial, name, 1, x, y, z, 1.0, 0.0, element)
        )
    lines.extend(("CONECT    1    2    3", "MASTER        0    0    0    0    0    0    0    3    0    1    0", "END"))
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


@pytest.mark.skipif(
    os.environ.get("EASYHYBRID_RUN_FULL_APP_GRAPHICS") != "1",
    reason="requires the real pDynamo3 runtime, bundled extensions, and a native GTK display",
)
def test_real_easyhybrid_application_mainwindow_load_render_pick_close():
    """Repeat the real app launch, pDynamo file-open, render, pick, and close."""
    pdynamo_home = os.environ.get("PDYNAMO3_HOME")
    assert pdynamo_home and Path(pdynamo_home, "pCore").is_dir(), (
        "Set PDYNAMO3_HOME to the compiled pDynamo3 source tree"
    )

    cycles = int(os.environ.get("EASYHYBRID_FULL_APP_CYCLES", "20"))
    assert cycles >= 1
    base_environment = os.environ.copy()
    base_environment["G_DEBUG"] = "fatal-criticals"
    base_environment["PDYNAMO3_PARAMETERS"] = os.path.join(pdynamo_home, "parameters")
    base_environment["PDYNAMO3_SCRATCH"] = os.path.join(
        tempfile.gettempdir(), "easyhybrid-full-app-scratch"
    )
    base_environment["PDYNAMO3_STYLE"] = os.path.join(
        pdynamo_home, "parameters", "ccsStyleSheets", "defaultStyle.css"
    )
    python_path = base_environment.get("PYTHONPATH", "")
    base_environment["PYTHONPATH"] = os.pathsep.join(
        part for part in (pdynamo_home, python_path) if part
    )
    Path(base_environment["PDYNAMO3_SCRATCH"]).mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="easyhybrid-full-app-") as temp_dir:
        temp_root = Path(temp_dir)
        home = temp_root / "home"
        (home / ".VisMol").mkdir(parents=True)
        # Keep packages installed with ``pip --user`` (distro CI images)
        # importable after HOME is isolated for the application's config.
        import site

        base_environment.setdefault("PYTHONUSERBASE", site.getuserbase())
        base_environment["HOME"] = str(home)
        if os.name == "nt":
            base_environment["USERPROFILE"] = str(home)
        fixture = temp_root / "water.pdb"
        _write_water_pdb(fixture)

        for cycle in range(1, cycles + 1):
            result = subprocess.run(
                [sys.executable, "-c", _FULL_APP_CYCLE, str(fixture)],
                cwd=Path(__file__).resolve().parents[1],
                env=base_environment,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            print("EASYHYBRID_FULL_APP_CYCLE=%d" % cycle)
            print(result.stdout.strip())
            assert result.returncode == 0, result.stdout + result.stderr
            assert "EASYHYBRID_FULL_APP_MAIN_WINDOW=True" in result.stdout
            assert "EASYHYBRID_FULL_APP_PICK=O:" in result.stdout
            assert "EASYHYBRID_FULL_APP_SYSTEMS=1" in result.stdout
            assert "EASYHYBRID_FULL_APP_SYSTEM_LABEL=water" in result.stdout
            assert "EASYHYBRID_FULL_APP_ATOMS=3" in result.stdout
            assert "EASYHYBRID_FULL_APP_SCENE_DRAWS=" in result.stdout
            assert "EASYHYBRID_FULL_APP_STATUS=0 CLOSED=True" in result.stdout
            assert "Traceback" not in result.stderr
            assert "CRITICAL" not in result.stderr
