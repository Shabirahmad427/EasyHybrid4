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

    # The Windows CI software driver must remain loaded while GDI chooses
    # and sets the pixel format. Older GTK bootstraps can otherwise unload
    # Mesa between those calls, discarding its per-HDC pixel-format state.
    # This opt-in test setup never selects a driver on user installations.
    ci_opengl = None
    if os.name == "nt" and os.environ.get("EASYHYBRID_TEST_OPENGL_DLL"):
        import ctypes
        ci_opengl = ctypes.WinDLL(os.environ["EASYHYBRID_TEST_OPENGL_DLL"])
        print("CI_OPENGL_DLL_RETAINED=" + os.environ["EASYHYBRID_TEST_OPENGL_DLL"], flush=True)

    import gi

    from src.os_integration.gtk_startup import configure_startup_environment
    configure_startup_environment(os.path.abspath("."))

    gi.require_version("Gtk", "4.0")
    gi.require_version("Gdk", "4.0")
    from gi.repository import Gdk, GLib, Gtk, Gio
    from src.gtk4_compat import (
        apply_legacy_win32_wgl_workaround,
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
    state = {}

    def activate(app):
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
        gl_area.set_required_version(3, 3)
        state["legacy_wgl_workaround"] = apply_legacy_win32_wgl_workaround(gl_area, Gtk)
        state["gl_ready"] = False

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
                state["gl_renderer"] = gl_renderer.decode("utf-8", errors="replace")
                state["gl_ready"] = True
                GLib.timeout_add(100, lambda: (window.close(), app.quit(), False)[2])
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
    application.run(None)
    if not state.get("gl_ready"):
        raise RuntimeError(
            "Gtk.GLArea did not produce a real OpenGL render: %s"
            % state.get("gl_error", "render signal not emitted")
        )
    print(
        "GTK=%d.%d.%d display=%s icon-theme=%s picture=%s scroll-unit=%s action=%s GL=%s renderer=%s legacy-wgl=%s GSK_RENDERER=%s" % (
            *state["runtime"], state["display"], state["theme"],
            state["picture_api"], state["scroll_unit_api"], state["menu_action"],
            state["gl_version"], state["gl_renderer"],
            state["legacy_wgl_workaround"], os.environ.get("GSK_RENDERER", "")
        )
    )
    """
)


_EASYHYBRID_LIFECYCLE_SMOKE = textwrap.dedent(
    """
    # Import the application first so its startup environment setup runs
    # before PyGObject initializes GTK or PyOpenGL selects a GL platform.
    import easyhybrid
    import os
    import re

    import gi

    gi.require_version("Gtk", "4.0")
    gi.require_version("Gdk", "4.0")
    from gi.repository import Gdk, Gio, GLib, Gtk

    display = Gdk.Display.get_default()
    if display is None:
        raise RuntimeError("EasyHybrid lifecycle smoke requires a native display")

    class ProbeApplication(easyhybrid.EasyHybridApplication):
        def __init__(self):
            Gtk.Application.__init__(
                self,
                application_id="org.easyhybrid.tests.FullLifecycle",
                flags=(Gio.ApplicationFlags.HANDLES_OPEN |
                       Gio.ApplicationFlags.NON_UNIQUE),
            )
            self.pending_open_files = []

    application = ProbeApplication()
    state = {"closed": False}

    def close_when_ready():
        main_window = getattr(application, "main_window", None)
        if main_window is not None:
            vm_widget = main_window.vm_session.vm_widget
            vm_widget.make_current()
            context_error = vm_widget.get_error()
            if context_error is not None:
                raise RuntimeError("EasyHybrid Gtk.GLArea failed: %s" % context_error)

            from OpenGL import GL
            gl_version = GL.glGetString(GL.GL_VERSION)
            gl_renderer = GL.glGetString(GL.GL_RENDERER)
            if not gl_version or not gl_renderer:
                raise RuntimeError("EasyHybrid Gtk.GLArea has no current OpenGL context")
            version_text = gl_version.decode("ascii", errors="replace")
            version_match = re.search(r"(\\d+)\\.(\\d+)", version_text)
            if not version_match or tuple(map(int, version_match.groups())) < (3, 3):
                raise RuntimeError("EasyHybrid requires OpenGL 3.3+, got %s" % version_text)

            print("EASYHYBRID_MAIN_WINDOW_OPENED", flush=True)
            print("EASYHYBRID_GL_VERSION=%s" % version_text, flush=True)
            print("EASYHYBRID_GL_RENDERER=%s" % gl_renderer.decode("utf-8", errors="replace"), flush=True)
            print("EASYHYBRID_GDK_DEBUG=%s" % os.environ.get("GDK_DEBUG", ""), flush=True)
            print("EASYHYBRID_PYOPENGL_PLATFORM=%s" % os.environ.get("PYOPENGL_PLATFORM", ""), flush=True)
            main_window.window.close()
            application.quit()
            state["closed"] = True
            return GLib.SOURCE_REMOVE
        return GLib.SOURCE_CONTINUE

    def timed_out():
        application.quit()
        return GLib.SOURCE_REMOVE

    GLib.timeout_add(500, close_when_ready)
    GLib.timeout_add_seconds(30, timed_out)
    status = application.run(["easyhybrid-lifecycle-test"])
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
    os.environ.get("EASYHYBRID_RUN_FULL_APP_TESTS") != "1",
    reason="requires pDynamo, graphics extensions, and a native GTK display",
)
def test_easyhybrid_full_application_opens_and_closes_without_critical_warnings():
    """Exercise actual EasyHybrid startup, GtkBuilder, GLArea, and close path."""
    environment = os.environ.copy()
    environment["G_DEBUG"] = "fatal-criticals"
    result = subprocess.run(
        [sys.executable, "-c", _EASYHYBRID_LIFECYCLE_SMOKE],
        cwd=os.path.dirname(os.path.dirname(__file__)),
        capture_output=True,
        text=True,
        timeout=45,
        env=environment,
        check=False,
    )
    print(result.stdout.strip())
    assert result.returncode == 0, result.stdout + result.stderr
    assert "EASYHYBRID_MAIN_WINDOW_OPENED" in result.stdout
    assert "EASYHYBRID_GL_VERSION=" in result.stdout
    assert "EASYHYBRID_GL_RENDERER=" in result.stdout
    assert "CLOSED=True" in result.stdout
    assert "Traceback" not in result.stderr
    assert "CRITICAL" not in result.stderr


if __name__ == "__main__":
    # Standalone entry point for native CI runners. Calling the smoke directly
    # avoids importing the scientific test fixtures and their Cython modules.
    os.environ["EASYHYBRID_RUN_GTK_GUI_TESTS"] = "1"
    test_application_resolves_icon_theme_after_display_startup()
