"""Opt-in native GTK startup smoke for display-bound icon-theme lookup."""

import os
import subprocess
import sys
import textwrap

import pytest


_GTK_SMOKE = textwrap.dedent(
    """
    import importlib.util
    import os

    import gi

    from src.os_integration.gtk_startup import configure_startup_environment
    configure_startup_environment(os.path.abspath("."))

    gi.require_version("Gtk", "4.0")
    gi.require_version("Gdk", "4.0")
    from gi.repository import Gdk, GLib, Gtk, Gio
    from src.gtk4_compat import (
        apply_legacy_win32_wgl_workaround,
        gl_area_required_version,
        set_picture_contain,
        supports_scroll_unit,
    )
    menu_spec = importlib.util.spec_from_file_location(
        "easyhybrid_menu_smoke", os.path.abspath("src/gui/main/gtk4_menu.py")
    )
    menu_module = importlib.util.module_from_spec(menu_spec)
    menu_spec.loader.exec_module(menu_module)
    Gtk4MainMenu = menu_module.Gtk4MainMenu

    display = Gdk.Display.get_default()
    if display is None:
        raise RuntimeError(
            "GTK GUI smoke requires an available display; refusing to register "
            "the application in a headless process"
        )

    application = Gtk.Application(
        application_id="org.easyhybrid.tests.IconThemeSmoke",
        flags=Gio.ApplicationFlags.NON_UNIQUE,
    )
    state = {"cycles": 0}

    def activate(app):
        cycle = state["cycles"] + 1
        theme = Gtk.IconTheme.get_for_display(display)
        if theme is None:
            raise RuntimeError("GTK returned no icon theme for the active display")
        settings = Gtk.Settings.get_for_display(display)
        picture = Gtk.Picture()
        state["picture_api"] = set_picture_contain(picture)
        state["scroll_unit_api"] = supports_scroll_unit(Gtk, Gdk)
        state["runtime"] = (
            Gtk.get_major_version(), Gtk.get_minor_version(), Gtk.get_micro_version()
        )
        state["display"] = display.get_name()
        state["theme"] = settings.get_property("gtk-icon-theme-name")
        window = Gtk.ApplicationWindow(application=app)
        window.set_default_size(320, 240)
        gl_area = Gtk.GLArea()
        gl_area.set_size_request(160, 120)
        gl_area.set_required_version(*gl_area_required_version(Gtk))
        state["legacy_wgl_workaround"] = apply_legacy_win32_wgl_workaround(gl_area, Gtk)
        state["gl_ready"] = False
        cycle_state = {"close_scheduled": False}

        def realize(area):
            area.make_current()
            error = area.get_error()
            if error is not None:
                state["gl_error"] = str(error)
                return
            area.queue_render()

        def render(area, _context):
            try:
                area.make_current()
                error = area.get_error()
                if error is not None:
                    raise RuntimeError("Gtk.GLArea context creation failed: %s" % error)

                from OpenGL import GL

                gl_version = GL.glGetString(GL.GL_VERSION)
                gl_renderer = GL.glGetString(GL.GL_RENDERER)
                if not gl_version or not gl_renderer:
                    raise RuntimeError("Gtk.GLArea has no current OpenGL context")
                state["gl_version"] = gl_version.decode("ascii", errors="replace")
                import re
                match = re.search(r"(\\d+)\\.(\\d+)", state["gl_version"])
                if not match or tuple(map(int, match.groups())) < (3, 3):
                    raise RuntimeError(
                        "EasyHybrid needs OpenGL 3.3+, got %s" % state["gl_version"]
                    )
                state["gl_renderer"] = gl_renderer.decode("utf-8", errors="replace")
                state["gl_ready"] = True
                if not cycle_state["close_scheduled"]:
                    cycle_state["close_scheduled"] = True

                    def close_cycle():
                        window.close()
                        state["cycles"] = cycle
                        if cycle < 3:
                            GLib.idle_add(
                                lambda: (app.activate(), GLib.SOURCE_REMOVE)[1]
                            )
                        else:
                            app.release()
                            app.quit()
                        return GLib.SOURCE_REMOVE

                    GLib.timeout_add(100, close_cycle)
            except Exception as error:
                state["gl_error"] = str(error)
                GLib.idle_add(lambda: (app.quit(), False)[1])
            return True

        gl_area.connect("realize", realize)
        gl_area.connect("render", render)
        class ActionProbe:
            last_action = None

            def on_main_menu_activate(self, action):
                self.last_action = action.get_name()

        action_probe = ActionProbe()
        menu = Gtk4MainMenu(action_probe, "src/gui/MainMenu.json")
        menu_bar = menu.create_widget()
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content.append(menu_bar)
        content.append(gl_area)
        window.set_child(content)
        menu.items["menuitem_open"].activate(None)
        if action_probe.last_action != "menuitem_open":
            raise RuntimeError("Gio main-menu action did not dispatch")
        stateful_action = menu.items["menuitem_check_xyz_axes"]
        original_state = stateful_action.get_state().get_boolean()
        stateful_action.activate(None)
        if stateful_action.get_state().get_boolean() == original_state:
            raise RuntimeError("Gio stateful menu action did not toggle")
        state["menu_bar"] = menu_bar
        state["menu_action"] = action_probe.last_action
        window.present()
        GLib.timeout_add_seconds(20, lambda: (app.quit(), False)[1])

    application.connect("activate", activate)
    application.hold()
    application.run(None)
    if not state.get("gl_ready"):
        raise RuntimeError(
            "Gtk.GLArea did not produce a real OpenGL render: %s"
            % state.get("gl_error", "render signal not emitted")
        )
    if state.get("cycles") != 3:
        raise RuntimeError(
            "GTK open/close lifecycle completed %d of 3 cycles"
            % state.get("cycles", 0)
        )
    print(
        "GTK=%d.%d.%d display=%s icon-theme=%s picture=%s scroll-unit=%s action=%s GL=%s renderer=%s legacy-wgl=%s GSK_RENDERER=%s" % (
            *state["runtime"], state["display"], state["theme"],
            state["picture_api"], state["scroll_unit_api"], state["menu_action"],
            state["gl_version"], state["gl_renderer"],
            state["legacy_wgl_workaround"], os.environ.get("GSK_RENDERER", "")
        )
    )
    print("GTK_WINDOW_OPEN_CLOSE_CYCLES=%d" % state["cycles"])
    """
)


_EASYHYBRID_GRAPHICS_SMOKE = textwrap.dedent(
    """
    import os
    import re
    import sys
    import tempfile
    import importlib.util

    from src.os_integration.gtk_startup import configure_startup_environment
    configure_startup_environment(os.path.abspath("."))
    sys.path.insert(0, os.path.abspath("src"))
    sys.path.insert(0, os.path.abspath("src/graphics_engine/src"))

    import gi

    gi.require_version("Gtk", "4.0")
    gi.require_version("Gdk", "4.0")
    from gi.repository import Gdk, Gio, GLib, Gtk
    from vismol.core.vismol_session import VismolSession
    from vismol.utils import parser

    display = Gdk.Display.get_default()
    if display is None:
        raise RuntimeError("EasyHybrid graphics smoke requires a native display")

    menu_spec = importlib.util.spec_from_file_location(
        "easyhybrid_menu_graphics_smoke",
        os.path.abspath("src/gui/main/gtk4_menu.py"),
    )
    menu_module = importlib.util.module_from_spec(menu_spec)
    menu_spec.loader.exec_module(menu_module)
    Gtk4MainMenu = menu_module.Gtk4MainMenu

    application = Gtk.Application(
        application_id="org.easyhybrid.tests.GraphicsLifecycle",
        flags=Gio.ApplicationFlags.NON_UNIQUE,
    )
    state = {
        "closed": False,
        "scene_started": False,
        "scene_draws": 0,
        "area_renders": 0,
    }

    def activate(app):
        vm_session = VismolSession("Gtk_4.0")
        vm_session.vm_widget.set_size_request(640, 420)
        vm_session.vm_widget.connect(
            "render",
            lambda *_args: state.__setitem__(
                "area_renders", state["area_renders"] + 1
            ),
        )
        window = Gtk.ApplicationWindow(application=app)
        window.set_default_size(900, 650)
        class ActionProbe:
            last_action = None

            def on_main_menu_activate(self, action):
                self.last_action = action.get_name()

        action_probe = ActionProbe()
        menu = Gtk4MainMenu(action_probe, "src/gui/MainMenu.json")
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content.append(menu.create_widget())
        content.append(vm_session.vm_widget)
        window.set_child(content)
        menu.items["menuitem_open"].activate(None)
        if action_probe.last_action != "menuitem_open":
            raise RuntimeError("EasyHybrid main-menu action did not dispatch")
        window.present()
        state.update(vm_session=vm_session, window=window)

    def close_when_ready():
        if state.get("window") is not None:
            vm_widget = state["vm_session"].vm_widget
            vm_widget.make_current()
            context_error = vm_widget.get_error()
            if context_error is not None:
                raise RuntimeError("EasyHybrid VisMol Gtk.GLArea failed: %s" % context_error)

            from OpenGL import GL
            gl_version = GL.glGetString(GL.GL_VERSION)
            gl_renderer = GL.glGetString(GL.GL_RENDERER)
            if not gl_version or not gl_renderer:
                raise RuntimeError("EasyHybrid VisMol has no current OpenGL context")
            version_text = gl_version.decode("ascii", errors="replace")
            version_match = re.search(r"(\\d+)\\.(\\d+)", version_text)
            if not version_match or tuple(map(int, version_match.groups())) < (3, 3):
                raise RuntimeError("EasyHybrid requires OpenGL 3.3+, got %s" % version_text)

            if not state["scene_started"]:
                # A tiny synthetic water molecule exercises the bundled PDB
                # parser, bond perception, representation setup, shader/VBO
                # creation, and actual VisMol draw calls without checking in
                # scientific or user-provided molecular data.
                atom_lines = []
                for serial, name, x, y, z, element in (
                    (1, "O", 0.000, 0.000, 0.000, "O"),
                    (2, "H1", 0.957, 0.000, 0.000, "H"),
                    (3, "H2", -0.240, 0.927, 0.000, "H"),
                ):
                    atom_lines.append(
                        "ATOM  %5d %-4s HOH A%4d    %8.3f%8.3f%8.3f%6.2f%6.2f          %2s  "
                        % (serial, name, 1, x, y, z, 1.0, 0.0, element)
                    )
                with tempfile.TemporaryDirectory(prefix="easyhybrid-scene-") as fixture_dir:
                    molecule_path = os.path.join(fixture_dir, "water.pdb")
                    with open(molecule_path, "w", encoding="ascii") as fixture:
                        fixture.write("\\n".join(atom_lines) + "\\nEND\\n")
                    vm_session = state["vm_session"]
                    molecule, show_molecule = parser.parse_file(
                        vm_session, molecule_path
                    )
                    molecule._generate_color_vectors(vm_session.atom_id_counter)
                    molecule.active = True
                    # This synthetic graphics fixture intentionally has no
                    # pDynamo scientific-system record.
                    VismolSession._add_vismol_object(
                        vm_session, molecule, show_molecule=show_molecule
                    )

                molecule = next(iter(vm_session.vm_objects_dic.values()))
                if len(molecule.atoms) != 3 or not molecule.bonds:
                    raise RuntimeError(
                        "VisMol did not load the three-atom water scene and its bonds"
                    )
                active_representations = [
                    representation
                    for representation in molecule.representations.values()
                    if representation is not None and representation.active
                ]
                if not active_representations:
                    raise RuntimeError("VisMol created no active molecule representation")
                for representation in active_representations:
                    draw = representation.draw_representation

                    def counted_draw(draw=draw):
                        draw()
                        state["scene_draws"] += 1

                    representation.draw_representation = counted_draw

                state["molecule"] = molecule
                state["scene_started"] = True
                vm_widget.queue_render()
                return GLib.SOURCE_CONTINUE

            if state["scene_draws"] == 0:
                return GLib.SOURCE_CONTINUE

            if os.environ.get("EASYHYBRID_TEST_COORDINATE_PICKING") == "1":
                if not state.get("hidpi_pick_started"):
                    widget_width = vm_widget.get_width()
                    widget_height = vm_widget.get_height()
                    core = state["vm_session"].vm_glcore
                    if (
                        os.environ.get("EASYHYBRID_REQUIRE_HIDPI_PICKING") == "1"
                        and (core.width <= widget_width or core.height <= widget_height)
                    ):
                        raise RuntimeError(
                            "GDK_SCALE=2 did not produce a larger GL framebuffer: "
                            "widget=%sx%s framebuffer=%sx%s"
                            % (widget_width, widget_height, core.width, core.height)
                        )

                    class CenterClick:
                        def __init__(self, x, y):
                            self.x, self.y = x, y

                        def get_current_button(self):
                            return 1

                        def get_current_event_state(self):
                            return Gdk.ModifierType(0)

                        def get_current_event(self):
                            return None

                    from gui.windows.builder.click_mode import (
                        _project_local_point_to_pixel,
                    )
                    oxygen = next(
                        atom for atom in state["molecule"].atoms.values()
                        if atom.symbol == "O"
                    )
                    frame = state["vm_session"].frame
                    px, py, _view_z = _project_local_point_to_pixel(
                        core, state["molecule"], oxygen.coords(frame)
                    )
                    if px is None:
                        raise RuntimeError("oxygen is behind the view camera")
                    x = px * widget_width / core.width
                    y = py * widget_height / core.height
                    gesture = CenterClick(x, y)
                    vm_widget._on_mouse_pressed(gesture, 1, x, y)
                    vm_widget._on_mouse_released(gesture, 1, x, y)
                    state["hidpi_pick_started"] = True
                    return GLib.SOURCE_CONTINUE

                core = state["vm_session"].vm_glcore
                if core.picking:
                    return GLib.SOURCE_CONTINUE
                picked = core.atom_picked
                if picked is None:
                    raise RuntimeError(
                        "HiDPI center click did not pick a rendered atom"
                    )
                print(
                    "EASYHYBRID_HIDPI_PICK=%s:%s"
                    % (picked.symbol, picked.atom_id),
                    flush=True,
                )
                state["hidpi_pick_checked"] = True

            vm_widget.make_current()
            gl_error = GL.glGetError()
            if gl_error != GL.GL_NO_ERROR:
                raise RuntimeError("VisMol scene render left OpenGL error 0x%x" % gl_error)
            molecule = state["molecule"]
            print("EASYHYBRID_MOLECULE_ATOMS=%d" % len(molecule.atoms), flush=True)
            print("EASYHYBRID_MOLECULE_BONDS=%d" % len(molecule.bonds), flush=True)
            print("EASYHYBRID_MOLECULE_DRAW_CALLS=%d" % state["scene_draws"], flush=True)

            print("EASYHYBRID_GRAPHICS_WINDOW_OPENED", flush=True)
            print("EASYHYBRID_GL_VERSION=%s" % version_text, flush=True)
            print("EASYHYBRID_GL_RENDERER=%s" % gl_renderer.decode("utf-8", errors="replace"), flush=True)
            print("EASYHYBRID_GDK_DEBUG=%s" % os.environ.get("GDK_DEBUG", ""), flush=True)
            print("EASYHYBRID_PYOPENGL_PLATFORM=%s" % os.environ.get("PYOPENGL_PLATFORM", ""), flush=True)
            state["window"].close()
            application.quit()
            state["closed"] = True
            return GLib.SOURCE_REMOVE
        return GLib.SOURCE_CONTINUE

    def timed_out():
        print(
            "EASYHYBRID_RENDER_TIMEOUT realized=%s area_renders=%d draws=%d"
            % (
                state.get("window") is not None
                and state["vm_session"].vm_widget.get_realized(),
                state["area_renders"],
                state["scene_draws"],
            ),
            flush=True,
        )
        application.quit()
        return GLib.SOURCE_REMOVE

    GLib.timeout_add(500, close_when_ready)
    GLib.timeout_add_seconds(30, timed_out)
    application.connect("activate", activate)
    application.hold()
    status = application.run(None)
    print("EASYHYBRID_STATUS=%d CLOSED=%s" % (status, state["closed"]), flush=True)
    if not state["closed"]:
        raise SystemExit(2)
    """
)


@pytest.mark.skipif(
    os.environ.get("EASYHYBRID_RUN_GTK_GUI_TESTS") != "1",
    reason="requires an explicitly selected native or virtual GTK display",
)
def test_application_resolves_icon_theme_after_display_startup():
    """Exercise real GTK startup with GLib criticals promoted to failures."""
    environment = os.environ.copy()
    environment["G_DEBUG"] = "fatal-criticals"
    result = subprocess.run(
        [sys.executable, "-c", _GTK_SMOKE],
        capture_output=True,
        text=True,
        timeout=35,
        env=environment,
        check=False,
    )
    print(result.stdout.strip())
    assert result.returncode == 0, result.stdout + result.stderr
    assert "icon-theme=" in result.stdout


@pytest.mark.skipif(
    os.environ.get("EASYHYBRID_RUN_GTK_ENV_DIAGNOSTIC") != "1",
    reason="diagnostic probe intentionally launches with no display",
)
def test_missing_display_is_reported_before_gapplication_registration():
    """Avoid GTK's display-bound icon lookup when a GUI runner has no display."""
    environment = os.environ.copy()
    environment.pop("DISPLAY", None)
    environment.pop("WAYLAND_DISPLAY", None)
    environment["GDK_BACKEND"] = "x11"
    environment["G_DEBUG"] = "fatal-criticals"
    result = subprocess.run(
        [sys.executable, "-X", "faulthandler", "-c", _GTK_SMOKE],
        capture_output=True,
        text=True,
        timeout=15,
        env=environment,
        check=False,
    )

    assert result.returncode != 0
    assert "requires an available display" in result.stderr
    assert "gtk_icon_theme_get_for_display" not in result.stderr


@pytest.mark.skipif(
    os.environ.get("EASYHYBRID_RUN_GRAPHICS_TESTS") != "1",
    reason="requires bundled graphics extensions and a native GTK display",
)
def test_easyhybrid_menu_and_molecular_renderer_open_and_close_cleanly():
    """Exercise fresh EasyHybrid scene lifecycles with native GTK events."""
    environment = os.environ.copy()
    environment["G_DEBUG"] = "fatal-criticals"
    cycles = int(environment.get("EASYHYBRID_GRAPHICS_SMOKE_CYCLES", "2"))
    assert cycles >= 1
    for cycle in range(1, cycles + 1):
        result = subprocess.run(
            [sys.executable, "-c", _EASYHYBRID_GRAPHICS_SMOKE],
            cwd=os.path.dirname(os.path.dirname(__file__)),
            capture_output=True,
            text=True,
            timeout=45,
            env=environment,
            check=False,
        )
        print("MOLECULAR_SCENE_CYCLE=%d" % cycle)
        print(result.stdout.strip())
        assert result.returncode == 0, result.stdout + result.stderr
        assert "EASYHYBRID_GRAPHICS_WINDOW_OPENED" in result.stdout
        assert "EASYHYBRID_GL_VERSION=" in result.stdout
        assert "EASYHYBRID_GL_RENDERER=" in result.stdout
        assert "EASYHYBRID_MOLECULE_ATOMS=3" in result.stdout
        assert "EASYHYBRID_MOLECULE_BONDS=2" in result.stdout
        assert "EASYHYBRID_MOLECULE_DRAW_CALLS=" in result.stdout
        if environment.get("EASYHYBRID_TEST_COORDINATE_PICKING") == "1":
            assert "EASYHYBRID_HIDPI_PICK=O:" in result.stdout
        assert "CLOSED=True" in result.stdout
        assert "Traceback" not in result.stderr
        assert "CRITICAL" not in result.stderr


if __name__ == "__main__":
    # Standalone entry point for native CI runners. Calling the smoke directly
    # avoids importing the scientific test fixtures and their Cython modules.
    os.environ["EASYHYBRID_RUN_GTK_GUI_TESTS"] = "1"
    test_application_resolves_icon_theme_after_display_startup()
