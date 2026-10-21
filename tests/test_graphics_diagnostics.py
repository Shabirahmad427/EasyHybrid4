"""Platform-independent wording and GL-version parsing for EH4-205."""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT / "src", ROOT / "src" / "graphics_engine" / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from vismol.gui.graphics_diagnostics import (  # noqa: E402
    graphics_failure_message,
    parse_gl_version,
    report_graphics_failure,
)


def test_parse_gl_version_accepts_common_driver_strings():
    assert parse_gl_version("4.6.0 NVIDIA 560.35") == (4, 6)
    assert parse_gl_version(b"4.1 APPLE-21.0.19") == (4, 1)
    assert parse_gl_version("OpenGL ES 3.2 Mesa") == (3, 2)
    assert parse_gl_version(None) is None
    assert parse_gl_version("unknown") is None


def test_context_failure_diagnostic_includes_actionable_cause_and_requirement():
    primary, details = graphics_failure_message(
        "OpenGL context creation",
        context_error="domain=gtk-gl-area code=2 message=No GL implementation",
    )
    assert "molecular graphics view" in primary
    assert "OpenGL context creation" in details
    assert "No GL implementation" in details
    assert "OpenGL 3.3 core" in details
    assert "graphics driver" in details


def test_unsupported_version_and_render_exception_are_described():
    _primary, unsupported = graphics_failure_message(
        "OpenGL capability check", gl_version="2.1 Mesa 23.0"
    )
    _primary, failed_render = graphics_failure_message(
        "OpenGL rendering", gl_version="4.6 Mesa", exception="RuntimeError: shader failed"
    )
    assert "Detected OpenGL version: 2.1 Mesa 23.0" in unsupported
    assert "OpenGL 3.3 core" in unsupported
    assert "shader failed" in failed_render


def test_native_graphics_failure_dialog_is_visible_and_idempotent():
    gi = pytest.importorskip("gi")
    gi.require_version("Gtk", "4.0")
    gi.require_version("Gdk", "4.0")
    from gi.repository import Gdk, Gtk

    if Gdk.Display.get_default() is None:
        pytest.skip("native GTK fallback dialog requires a display")

    parent = Gtk.Window(title="Graphics host")
    dialog = report_graphics_failure(
        parent,
        "OpenGL context creation",
        context_error="No GL implementation is available",
    )
    assert parent._graphics_failed is True
    assert dialog is not None
    assert dialog.get_visible()
    assert dialog.get_title() == "Graphics unavailable"
    assert "No GL implementation is available" in dialog.details_view.get_buffer().get_text(
        dialog.details_view.get_buffer().get_start_iter(),
        dialog.details_view.get_buffer().get_end_iter(),
        True,
    )
    assert report_graphics_failure(parent, "second failure") is None
    dialog.destroy()
    parent.destroy()


def test_glarea_unsupported_version_uses_visible_fallback_without_core_init(monkeypatch):
    gi = pytest.importorskip("gi")
    gi.require_version("Gtk", "4.0")
    gi.require_version("Gdk", "4.0")
    from gi.repository import Gdk, GLib, Gtk

    if Gdk.Display.get_default() is None:
        pytest.skip("Gtk.GLArea failure-path test requires a display")

    import vismol.gui.vismol_gtkwidget as widget_module

    session = SimpleNamespace(
        vm_config=SimpleNamespace(representations_available=[], gl_parameters={})
    )
    widget = widget_module.VismolGTKWidget(session)
    core_initialized = []
    dialogs = []
    monkeypatch.setattr(widget.vm_glcore, "initialize", lambda: core_initialized.append(True))
    monkeypatch.setattr(widget_module, "glGetString", lambda _name: b"2.1 Legacy Driver")
    report = widget_module.report_graphics_failure

    def capture_dialog(*args, **kwargs):
        dialog = report(*args, **kwargs)
        dialogs.append(dialog)
        return dialog

    monkeypatch.setattr(widget_module, "report_graphics_failure", capture_dialog)
    window = Gtk.Window(title="GLArea failure test")
    window.set_child(widget)
    window.present()
    context = GLib.MainContext.default()
    deadline = GLib.get_monotonic_time() + 2_000_000
    while not widget._graphics_failed and GLib.get_monotonic_time() < deadline:
        context.iteration(True)

    assert widget._graphics_failed
    assert core_initialized == []
    assert len(dialogs) == 1 and dialogs[0] is not None
    assert "2.1 Legacy Driver" in dialogs[0].details_view.get_buffer().get_text(
        dialogs[0].details_view.get_buffer().get_start_iter(),
        dialogs[0].details_view.get_buffer().get_end_iter(),
        True,
    )
    assert widget.render(widget, None) is True
    dialogs[0].destroy()
    window.destroy()


def test_render_exception_is_reported_once_and_stops_scene_rendering(monkeypatch):
    gi = pytest.importorskip("gi")
    gi.require_version("Gtk", "4.0")
    gi.require_version("Gdk", "4.0")
    from gi.repository import Gdk, Gtk

    if Gdk.Display.get_default() is None:
        pytest.skip("Gtk.GLArea render failure test requires a display")

    import vismol.gui.vismol_gtkwidget as widget_module

    session = SimpleNamespace(
        vm_config=SimpleNamespace(representations_available=[], gl_parameters={})
    )
    widget = widget_module.VismolGTKWidget(session)
    render_calls = []
    dialogs = []

    def fail_render():
        render_calls.append(True)
        raise RuntimeError("test shader failure")

    monkeypatch.setattr(widget.vm_glcore, "render", fail_render)
    report = widget_module.report_graphics_failure
    monkeypatch.setattr(
        widget_module,
        "report_graphics_failure",
        lambda *args, **kwargs: dialogs.append(report(*args, **kwargs)),
    )

    assert widget.render(widget, None) is True
    assert widget.render(widget, None) is True
    assert render_calls == [True]
    assert len(dialogs) == 1 and dialogs[0] is not None
    details = dialogs[0].details_view.get_buffer().get_text(
        dialogs[0].details_view.get_buffer().get_start_iter(),
        dialogs[0].details_view.get_buffer().get_end_iter(),
        True,
    )
    assert "test shader failure" in details
    dialogs[0].destroy()
