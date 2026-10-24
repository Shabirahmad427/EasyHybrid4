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
    import faulthandler
    import pickle
    import numpy as np

    from src.os_integration.gtk_startup import configure_startup_environment
    configure_startup_environment(os.path.abspath("."))
    from OpenGL import GL

    import gi
    gi.require_version("Gtk", "4.0")
    gi.require_version("Gdk", "4.0")
    gi.require_version("Graphene", "1.0")
    from gi.repository import Gdk, GLib, Graphene, Gtk

    import easyhybrid
    from pCore import logFile

    # Centering is a UI animation unrelated to the load/render/pick lifecycle
    # under test. Use the production centering method with one animation step
    # so the test does not depend on the host's main-loop scheduling cadence.
    from gui.config import VismolConfig
    original_config_init = VismolConfig.__init__

    def fast_test_config(self, *args, **kwargs):
        original_config_init(self, *args, **kwargs)
        self.gl_parameters["center_steps"] = 1
        self.gl_parameters["center_on_coord_sleep_time"] = 0.001

    VismolConfig.__init__ = fast_test_config

    display = Gdk.Display.get_default()
    if display is None:
        raise RuntimeError("Full EasyHybrid smoke requires a native GTK display")

    fixture = os.path.abspath(sys.argv[1])
    app = easyhybrid.EasyHybridApplication()
    print("EASYHYBRID_FULL_APP_TEST_CENTER_STEPS=1", flush=True)
    state = {
        "started": time.monotonic(), "scene_draws": 0,
        "core_renders": 0, "phase": "application_start", "picked": False,
        "poll_calls": 0, "last_poll": None, "pick_render_calls": 0,
        "gesture_events": [],
        "last_render_seconds": None, "max_render_seconds": 0.0,
    }

    def fail(message):
        print("EASYHYBRID_FULL_APP_ERROR=" + message, flush=True)
        app.quit()
        return GLib.SOURCE_REMOVE

    def finish_session_round_trip(main, expected_camera):
        core = main.vm_session.vm_glcore
        if state["core_renders"] <= state["session_render_baseline"]:
            if time.monotonic() - state["session_round_trip_started"] > 8:
                return fail("reopened .easy session did not render")
            return GLib.SOURCE_CONTINUE

        main.vm_session.vm_widget.make_current()
        gl_error = GL.glGetError()
        if gl_error != GL.GL_NO_ERROR:
            return fail("reopened .easy session left OpenGL error 0x%x" % gl_error)
        if len(main.p_session.psystem) != 1 or len(main.vm_session.vm_objects_dic) != 1:
            return fail("reopened .easy session did not restore its system and molecule")
        if not np.array_equal(core.model_mat, expected_camera["model_mat"]):
            return fail("reopened .easy session did not restore model matrix")
        if not np.array_equal(
            core.zero_reference_point, expected_camera["zero_reference_point"]
        ):
            return fail("reopened .easy session did not restore camera reference point")
        if not np.array_equal(
            core.glcamera.view_matrix, expected_camera["view_matrix"]
        ):
            return fail("reopened .easy session did not restore view matrix")
        if core.dist_cam_zrp != expected_camera["dist_cam_zrp"]:
            return fail("reopened .easy session did not restore camera distance")
        print("EASYHYBRID_FULL_APP_CAMERA_SESSION_ROUND_TRIP=True", flush=True)
        print("EASYHYBRID_FULL_APP_SESSION_REOPEN_RENDER=True", flush=True)

        # Session load restores a dirty session; discard this generated test
        # fixture and close through the normal MainWindow lifecycle.
        main.p_session.changed = False
        main.window.close()
        main.window.set_visible(False)
        state["closed"] = True
        app.quit()
        return GLib.SOURCE_REMOVE

    def complete_pick(main):
        # Finish after the production GL pick pass selected the fixture O.
        if state.get("completion_started"):
            return GLib.SOURCE_REMOVE
        state["completion_started"] = True
        if state.get("pick_completion_scheduled"):
            print("EASYHYBRID_FULL_APP_PICK_COMPLETED_AFTER_RENDER=True", flush=True)
        vm_widget = main.vm_session.vm_widget
        vm_widget.make_current()
        gl_error = GL.glGetError()
        if gl_error != GL.GL_NO_ERROR:
            return fail("production scene left OpenGL error 0x%x" % gl_error)

        picked = main.vm_session.vm_glcore.atom_picked
        molecule = state["molecule"]
        print("EASYHYBRID_FULL_APP_PICK=O:%s" % picked.atom_id, flush=True)
        viewing_selection = main.vm_session.selections[
            main.vm_session.current_selection
        ]
        residue_atom_ids = {atom.atom_id for atom in molecule.atoms.values()}
        selected_atom_ids = {
            atom.atom_id for atom in viewing_selection.selected_atoms
        }
        if selected_atom_ids != residue_atom_ids:
            return fail(
                "production residue pick selected atom IDs %r, expected %r"
                % (sorted(selected_atom_ids), sorted(residue_atom_ids))
            )
        print(
            "EASYHYBRID_FULL_APP_RESIDUE_SELECTION=%d"
            % len(viewing_selection.selected_atoms),
            flush=True,
        )

        # Exercise atom mode through the same production viewing-selection
        # object and confirm it replaces the residue selection precisely.
        viewing_selection.selection_function_viewing_set(None)
        viewing_selection.selection_mode = "atom"
        viewing_selection.selection_function_viewing_set({picked}, disable=False)
        atom_selection_ids = {
            atom.atom_id for atom in viewing_selection.selected_atoms
        }
        if atom_selection_ids != {picked.atom_id}:
            return fail(
                "production atom selection returned %r, expected [%r]"
                % (sorted(atom_selection_ids), picked.atom_id)
            )
        print("EASYHYBRID_FULL_APP_ATOM_SELECTION=True", flush=True)

        # Exercise the real session representation controls for the selected
        # atom and its label. Assertions inspect the production index list and
        # atom flags consumed by the renderer.
        main.vm_session.show_or_hide(rep_type="nonbonded", show=False)
        nonbonded = molecule.representations["nonbonded"]
        if picked.nonbonded or picked.atom_id in nonbonded.indexes:
            return fail("production nonbonded hide left oxygen visible")
        main.vm_session.show_or_hide(rep_type="nonbonded", show=True)
        if not picked.nonbonded or picked.atom_id not in nonbonded.indexes:
            return fail("production nonbonded show did not restore oxygen")

        picked.label_text = picked.name
        main.vm_session.show_or_hide(rep_type="labels", show=True)
        label_representation = molecule.representations["labels"]
        if not picked.labels or picked.atom_id not in label_representation.indexes:
            return fail("production atom label was not added to the label representation")
        label_entries = []
        label_representation.vm_glcore._draw_text_labels = (
            lambda _font, entries, **_kwargs: label_entries.extend(entries)
        )
        label_representation.draw_representation()
        if not any(entry[0] == "O" for entry in label_entries):
            return fail("production atom label draw did not emit oxygen text")
        main.vm_session.show_or_hide(rep_type="labels", show=False)
        if picked.labels or label_representation.active:
            return fail("production atom label hide did not deactivate the label")
        print("EASYHYBRID_FULL_APP_LABEL_REPRESENTATION=True", flush=True)
        print("EASYHYBRID_FULL_APP_SCENE_REPRESENTATION=True", flush=True)

        # Run the production pk1/pk2/pk3 measurement workflow on the loaded
        # water geometry: H1-O and O-H2 distances, plus the H1-O-H2 angle.
        atoms_by_name = {atom.name: atom for atom in molecule.atoms.values()}
        picking = main.vm_session.picking_selections
        picking.selection_function_picking(atoms_by_name["H1"])
        picking.selection_function_picking(atoms_by_name["O"])
        picking.selection_function_picking(atoms_by_name["H2"])
        if not np.isclose(picking.dist_pk1_pk2, 0.957, atol=0.002):
            return fail(
                "production H1-O measurement was %r, expected 0.957 angstrom"
                % picking.dist_pk1_pk2
            )
        if not np.isclose(picking.dist_pk2_pk3, 0.957, atol=0.002):
            return fail(
                "production O-H2 measurement was %r, expected 0.957 angstrom"
                % picking.dist_pk2_pk3
            )
        if not np.isclose(picking.theta_deg, 104.5, atol=0.3):
            return fail(
                "production H1-O-H2 measurement was %r, expected 104.5 degrees"
                % picking.theta_deg
            )
        picking.selection_function_picking(None)
        print("EASYHYBRID_FULL_APP_GEOMETRY_MEASUREMENTS=True", flush=True)

        print("EASYHYBRID_FULL_APP_SYSTEMS=%d" % len(main.p_session.psystem), flush=True)
        system = next(iter(main.p_session.psystem.values()))
        print("EASYHYBRID_FULL_APP_SYSTEM_LABEL=%s" % system.label, flush=True)
        print("EASYHYBRID_FULL_APP_ATOMS=%d" % len(molecule.atoms), flush=True)
        print("EASYHYBRID_FULL_APP_SCENE_DRAWS=%d" % state["scene_draws"], flush=True)
        print("EASYHYBRID_FULL_APP_GL_VERSION=%s" % state["gl_version"].decode("ascii", "replace"), flush=True)
        print("EASYHYBRID_FULL_APP_GL_RENDERER=%s" % state["gl_renderer"].decode("utf-8", "replace"), flush=True)

        # Exercise the actual .easy serializer and loader with a generated
        # filename. Corrupt the live camera after saving so reopening must
        # restore the serialized view, then require a real scene render.
        session_path = os.path.join(os.path.dirname(fixture), "camera-roundtrip.easy")
        live_tree_row = getattr(system, "tree_row", None)
        live_choice_row = getattr(system, "system_choice_row", None)
        print("EASYHYBRID_FULL_APP_SESSION_SAVE_STARTED=True", flush=True)
        main.p_session.save_easyhybrid_session(filename=session_path)
        if system.tree_row is not live_tree_row:
            return fail("session save did not restore the live system tree row")
        if system.system_choice_row is not live_choice_row:
            return fail("session save did not restore the live system choice row")
        with open(session_path, "rb") as session_file:
            saved_session = pickle.load(session_file)
        expected_camera = saved_session.get("camera")
        if not expected_camera:
            return fail("saved .easy session omitted camera state")
        core = main.vm_session.vm_glcore
        core.model_mat = np.zeros_like(core.model_mat)
        core.zero_reference_point = np.zeros_like(core.zero_reference_point)
        core.dist_cam_zrp = -1.0
        core.glcamera.set_view_matrix(np.zeros_like(core.glcamera.view_matrix))
        core.glcamera.set_projection_matrix(
            np.zeros_like(core.glcamera.projection_matrix)
        )
        main.p_session.load_easyhybrid_serialization_file(filename=session_path)
        print("EASYHYBRID_FULL_APP_SESSION_LOADED=True", flush=True)
        core = main.vm_session.vm_glcore
        if not np.array_equal(core.model_mat, expected_camera["model_mat"]):
            return fail(".easy load did not immediately restore model matrix")
        if not np.array_equal(
            core.zero_reference_point, expected_camera["zero_reference_point"]
        ):
            return fail(".easy load did not immediately restore camera reference point")
        if not np.array_equal(
            core.glcamera.view_matrix, expected_camera["view_matrix"]
        ):
            return fail(".easy load did not immediately restore view matrix")
        if core.dist_cam_zrp != expected_camera["dist_cam_zrp"]:
            return fail(".easy load did not immediately restore camera distance")
        state["molecule"] = next(iter(main.vm_session.vm_objects_dic.values()))
        state["session_render_baseline"] = state["core_renders"]
        state["session_round_trip_started"] = time.monotonic()
        state["phase"] = "rendering_reopened_session"
        main.vm_session.vm_widget.queue_render()
        GLib.timeout_add(10, safe_finish_session_round_trip, main, expected_camera)
        return GLib.SOURCE_REMOVE

    def safe_finish_session_round_trip(main, expected_camera):
        try:
            return finish_session_round_trip(main, expected_camera)
        except Exception as error:
            import traceback
            traceback.print_exc()
            return fail(".easy round-trip callback raised %s: %s" % (
                type(error).__name__, error
            ))

    def safe_complete_pick(main):
        try:
            return complete_pick(main)
        except Exception as error:
            import traceback
            traceback.print_exc()
            return fail("full-app completion raised %s: %s" % (
                type(error).__name__, error
            ))

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
                was_picking = core.picking
                render_started = time.monotonic()
                state["core_renders"] += 1
                result = render_core(*args, **kwargs)
                render_seconds = time.monotonic() - render_started
                state["last_render_seconds"] = round(render_seconds, 3)
                state["max_render_seconds"] = max(
                    state["max_render_seconds"], render_seconds
                )
                if was_picking:
                    state["pick_render_calls"] += 1
                    state["last_pick_render"] = {
                        "requested": was_picking,
                        "pending_after": core.picking,
                        "picked_after": getattr(core.atom_picked, "name", None),
                        "xy": (float(core.picking_x), float(core.picking_y)),
                        "size": (core.width, core.height),
                    }
                    if (
                        not core.picking
                        and getattr(core.atom_picked, "symbol", None) == "O"
                        and not state.get("pick_completion_scheduled")
                    ):
                        # Complete from the main loop as soon as the real GL
                        # readback confirms oxygen; do not depend on another
                        # periodic poll being serviced by the native backend.
                        state["pick_completion_scheduled"] = True
                        state["pick_completion_source"] = GLib.timeout_add(
                            1,
                            safe_complete_pick, main
                        )
                return result

            core.render = count_core_render

            # Keep evidence that a real desktop event reached GTK's
            # production gesture callbacks. This distinguishes a Win32
            # desktop/window targeting problem from a framebuffer pick miss.
            original_mouse_pressed = core.mouse_pressed
            original_mouse_released = core.mouse_released

            def trace_mouse_pressed(*args, **kwargs):
                state["gesture_events"].append(("pressed", args[:4]))
                return original_mouse_pressed(*args, **kwargs)

            def trace_mouse_released(*args, **kwargs):
                state["gesture_events"].append(("released", args[:4]))
                return original_mouse_released(*args, **kwargs)

            core.mouse_pressed = trace_mouse_pressed
            core.mouse_released = trace_mouse_released

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
            model_transform = np.asarray(state["molecule"].model_mat)
            transform_snapshot = model_transform.tobytes()
            state.setdefault("center_wait_started", time.monotonic())
            previous_transform = state.get("last_model_transform_array")
            state["last_transform_delta"] = (
                None if previous_transform is None else float(
                    np.max(np.abs(model_transform - previous_transform))
                )
            )
            state["last_model_transform_array"] = model_transform.copy()
            target = np.append(state["molecule"].mass_center, 1.0)
            centered_target = model_transform.T.dot(target)[:3]
            state["centering_residual"] = float(np.linalg.norm(centered_target))
            if transform_snapshot == state.get("last_model_transform"):
                state["stable_transform_ticks"] = state.get("stable_transform_ticks", 0) + 1
            else:
                state["last_model_transform"] = transform_snapshot
                state["stable_transform_ticks"] = 0
            # The one-step test centering animation is complete when the target
            # residual is zero and the transform is not changing. Do not require
            # repeated GLib timer ticks: macOS may render/poll sparsely while
            # still reaching the exact final transform.
            center_is_settled = (
                state["centering_residual"] <= 1.0e-5
                and (
                    state["last_transform_delta"] is None
                    or state["last_transform_delta"] <= 1.0e-6
                )
            )
            if not center_is_settled:
                state["phase"] = "waiting_for_center_animation"
                if time.monotonic() - state["center_wait_started"] > 10:
                    return fail(
                        "molecular centering did not settle before pick "
                        "(stable_ticks=%s residual=%.7g transform_delta=%r "
                        "last_render_seconds=%r max_render_seconds=%.3f)"
                        % (
                            state["stable_transform_ticks"],
                            state["centering_residual"],
                            state["last_transform_delta"],
                            state["last_render_seconds"],
                            state["max_render_seconds"],
                        )
                    )
                return GLib.SOURCE_CONTINUE

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

            if os.environ.get("EASYHYBRID_FULL_APP_NATIVE_POINTER") == "1":
                mapped, window_point = vm_widget.compute_point(
                    main.window, Graphene.Point().init(x, y)
                )
                if not mapped:
                    return fail("could not map projected atom point into main window")
                mapped_window_point = (window_point.x, window_point.y)
                window_offset = state.get("native_window_offset", (0.0, 0.0))
                window_point = Graphene.Point().init(
                    mapped_window_point[0] + window_offset[0],
                    mapped_window_point[1] + window_offset[1],
                )
                native_correction = (0.0, 0.0)
                # Correct any measured discrepancy between the OS window
                # coordinate and the framebuffer point received by GTK. A
                # zero offset on Linux/macOS leaves their native mapping as-is.
                events = state.get("gesture_events", [])
                feedback_start = state.get("native_feedback_event_count", 0)
                new_events = events[feedback_start:]
                released = next(
                    (event[1] for event in reversed(new_events)
                     if event[0] == "released"),
                    None,
                )
                if released is not None:
                    sys.path.insert(0, os.path.join(os.path.abspath("."), "tests"))
                    from native_pointer_input import (
                        add_window_point_offset,
                        adjust_window_point_from_gesture_feedback,
                    )

                    corrected = adjust_window_point_from_gesture_feedback(
                        window_point.x,
                        window_point.y,
                        target_framebuffer_point=(px, py),
                        observed_framebuffer_point=(released[1], released[2]),
                        widget_size=(widget_width, widget_height),
                        framebuffer_size=(core.width, core.height),
                    )
                    native_correction = (
                        corrected[0] - window_point.x,
                        corrected[1] - window_point.y,
                    )
                    window_offset = add_window_point_offset(
                        window_offset, native_correction
                    )
                    state["native_window_offset"] = window_offset
                    window_point = Graphene.Point().init(*corrected)
                state["native_feedback_event_count"] = len(events)
                state["native_points"] = {
                    "widget": (round(x, 4), round(y, 4)),
                    "mapped_window": tuple(round(v, 4) for v in mapped_window_point),
                    "click_window": (round(window_point.x, 4), round(window_point.y, 4)),
                    "projection": (round(px, 4), round(py, 4)),
                    "dimensions": (widget_width, widget_height, core.width, core.height),
                    "surface_scale": main.window.get_surface().get_scale_factor(),
                    "feedback_correction": tuple(round(v, 4) for v in native_correction),
                }
                sys.path.insert(0, os.path.join(os.path.abspath("."), "tests"))
                try:
                    from native_pointer_input import inject_native_pointer

                    state["pointer_input"] = inject_native_pointer(
                        main.window, window_point.x, window_point.y
                    )
                except Exception as error:
                    return fail("native desktop pointer click failed: %s" % error)
            else:
                class TestGesture:
                    def __init__(self, x, y):
                        self.x, self.y = x, y

                    def get_current_button(self):
                        return 1

                    def get_current_event_state(self):
                        return Gdk.ModifierType(0)

                    def get_current_event(self):
                        raise AssertionError(
                            "release handler must not marshal GdkButtonEvent"
                        )

                gesture = TestGesture(x, y)
                vm_widget._on_mouse_pressed(gesture, 1, x, y)
                vm_widget._on_mouse_released(gesture, 1, x, y)
                state["pointer_input"] = "synthetic-gtk-callback"
            state["pick_started"] = True
            state["pick_attempts"] = state.get("pick_attempts", 0) + 1
            if state["pick_attempts"] == 1:
                print("EASYHYBRID_FULL_APP_POINTER=%s" % state["pointer_input"], flush=True)
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
            return fail(
                "production MainWindow GTK gesture pick missed oxygen: %r "
                "(events=%r last_pick_render=%r requested=%r native_points=%r)"
                % (
                    picked, state.get("gesture_events", [])[-10:],
                    state.get("last_pick_render"), state.get("pick_dimensions"),
                    state.get("native_points"),
                )
            )

        return safe_complete_pick(main)

    def safe_poll_app():
        state["poll_calls"] += 1
        state["last_poll"] = time.monotonic()
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
        core = getattr(getattr(main, "vm_session", None), "vm_glcore", None)
        last_pick = state.get("last_pick_render") or {}
        picked = getattr(core, "atom_picked", None)
        # On macOS the native HID event can complete the actual GL readback
        # while the next 50 ms lifecycle poll is delayed. The render wrapper
        # records the completed pick; accept that verified production result
        # and close cleanly instead of turning poll cadence into a false fail.
        if (
            main is not None
            and state.get("pick_started")
            and state.get("pick_attempts", 0) > 0
            and last_pick.get("requested") is True
            and last_pick.get("pending_after") is False
            and last_pick.get("picked_after") == "O"
            and not getattr(core, "picking", True)
            and getattr(picked, "symbol", None) == "O"
        ):
            print("EASYHYBRID_FULL_APP_PICK_COMPLETED_AFTER_POLL_TIMEOUT=True", flush=True)
            return safe_complete_pick(main)

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
                "pick_projection=%r atom_picked=%r polls=%s poll_age=%r "
                "pick_render_calls=%s last_pick_render=%r stable_transform_ticks=%s "
                "centering_residual=%r transform_delta=%r last_render_seconds=%r "
                "max_render_seconds=%.3f"
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
                    state["poll_calls"],
                    None if state["last_poll"] is None else round(
                        time.monotonic() - state["last_poll"], 3
                    ),
                    state["pick_render_calls"],
                    state.get("last_pick_render"),
                    state.get("stable_transform_ticks", 0),
                    state.get("centering_residual"),
                    state.get("last_transform_delta"),
                    state.get("last_render_seconds"),
                    state["max_render_seconds"],
                )
            )
        return fail(
            "full-app lifecycle timed out phase=%s %s" %
            (state["phase"], details)
        )

    GLib.timeout_add_seconds(45, lifecycle_timeout)
    faulthandler.dump_traceback_later(15, repeat=True)
    status = app.run([sys.argv[0], fixture])
    faulthandler.cancel_dump_traceback_later()
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


def test_full_app_native_pointer_test_uses_one_shared_os_dispatcher():
    """Every native full-app cell shares the same click path and assertions."""
    assert "from gi.repository import Gdk, GLib, Graphene, Gtk" in _FULL_APP_CYCLE
    assert "inject_native_pointer(\n                    main.window, window_point.x, window_point.y" in _FULL_APP_CYCLE
    assert 'last_pick.get("picked_after") == "O"' in _FULL_APP_CYCLE
    assert "state[\"pick_completion_source\"] = GLib.timeout_add(\n                        1,\n                        safe_complete_pick, main" in _FULL_APP_CYCLE
    assert 'state["completion_started"] = True' in _FULL_APP_CYCLE
    assert "EASYHYBRID_FULL_APP_PICK_COMPLETED_AFTER_POLL_TIMEOUT=True" in _FULL_APP_CYCLE
    assert "GdkX11" not in _FULL_APP_CYCLE
    assert "xdotool" not in _FULL_APP_CYCLE


def _run_full_app_cycle(fixture, environment, cycle, timeout=60):
    """Run one app cycle; on timeout keep its partial output and native stack."""
    process = subprocess.Popen(
        [sys.executable, "-c", _FULL_APP_CYCLE, str(fixture)],
        cwd=Path(__file__).resolve().parents[1],
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        native_stack = ""
        if sys.platform == "darwin":
            # faulthandler only shows Python frames; a main loop blocked in
            # GTK, GSK or the GL driver needs the native call graph.
            sampled = subprocess.run(
                ["sample", str(process.pid), "3", "-mayDie"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            native_stack = sampled.stdout[-12000:] + sampled.stderr[-2000:]
        process.kill()
        stdout, stderr = process.communicate()
        pytest.fail(
            "full-app cycle %d exceeded %d s\n--- stdout ---\n%s\n--- stderr ---\n%s"
            "\n--- native stack ---\n%s" % (cycle, timeout, stdout, stderr, native_stack)
        )
    return subprocess.CompletedProcess(process.args, process.returncode, stdout, stderr)


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
            result = _run_full_app_cycle(fixture, base_environment, cycle)
            print("EASYHYBRID_FULL_APP_CYCLE=%d" % cycle)
            print(result.stdout.strip())
            assert result.returncode == 0, result.stdout + result.stderr
            assert "EASYHYBRID_FULL_APP_MAIN_WINDOW=True" in result.stdout
            assert "EASYHYBRID_FULL_APP_PICK=O:" in result.stdout
            assert "EASYHYBRID_FULL_APP_RESIDUE_SELECTION=3" in result.stdout
            assert "EASYHYBRID_FULL_APP_ATOM_SELECTION=True" in result.stdout
            assert "EASYHYBRID_FULL_APP_LABEL_REPRESENTATION=True" in result.stdout
            assert "EASYHYBRID_FULL_APP_SCENE_REPRESENTATION=True" in result.stdout
            assert "EASYHYBRID_FULL_APP_CAMERA_SESSION_ROUND_TRIP=True" in result.stdout
            assert "EASYHYBRID_FULL_APP_SESSION_REOPEN_RENDER=True" in result.stdout
            if os.environ.get("EASYHYBRID_FULL_APP_NATIVE_POINTER") == "1":
                expected_pointer = {
                    "linux": "linux-x11-xtest",
                    "win32": "windows-win32-user32",
                    "darwin": "macos-quartz-hid",
                }.get(sys.platform, "")
                assert expected_pointer, "native pointer path is not defined for this OS"
                assert "EASYHYBRID_FULL_APP_POINTER=%s" % expected_pointer in result.stdout
            assert "EASYHYBRID_FULL_APP_SYSTEMS=1" in result.stdout
            assert "EASYHYBRID_FULL_APP_SYSTEM_LABEL=water" in result.stdout
            assert "EASYHYBRID_FULL_APP_ATOMS=3" in result.stdout
            assert "EASYHYBRID_FULL_APP_SCENE_DRAWS=" in result.stdout
            assert "EASYHYBRID_FULL_APP_STATUS=0 CLOSED=True" in result.stdout
            assert "Traceback" not in result.stderr
            assert "CRITICAL" not in result.stderr
