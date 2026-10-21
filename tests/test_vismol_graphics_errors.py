"""User-visible fallback behavior when VisMol cannot initialize OpenGL."""

import sys
from pathlib import Path
from types import SimpleNamespace

import gi
import pytest


ROOT = Path(__file__).resolve().parents[1]
for source_path in (ROOT / "src", ROOT / "src" / "graphics_engine" / "src"):
    if str(source_path) not in sys.path:
        sys.path.insert(0, str(source_path))

from vismol.gui import vismol_gtkwidget

gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gtk


def test_graphics_failure_disables_view_and_shows_actionable_dialog(monkeypatch):
    shown = []
    dialog = object()
    monkeypatch.setattr(
        "gui.message_dialogs.show_message",
        lambda *args, **kwargs: shown.append((args, kwargs)) or dialog,
    )
    widget = SimpleNamespace(set_sensitive=lambda value: setattr(widget, "sensitive", value))

    vismol_gtkwidget._report_graphics_failure(widget, RuntimeError("no core context"))

    assert widget.sensitive is False
    assert widget._graphics_error_dialog is dialog
    assert len(shown) == 1
    assert shown[0][0][1] == "EasyHybrid could not initialize 3D molecular rendering."
    assert shown[0][1]["kind"] == "error"
    assert "OpenGL 3.3 or newer core context" in shown[0][1]["details"]
    assert "no core context" in shown[0][1]["details"]


def test_graphics_failure_is_reported_once(monkeypatch):
    shown = []
    monkeypatch.setattr(
        "gui.message_dialogs.show_message",
        lambda *args, **kwargs: shown.append((args, kwargs)),
    )
    widget = SimpleNamespace(set_sensitive=lambda _value: None)

    vismol_gtkwidget._report_graphics_failure(widget, RuntimeError("first"))
    vismol_gtkwidget._report_graphics_failure(widget, RuntimeError("second"))

    assert len(shown) == 1


def test_gl_area_context_error_enters_user_visible_fallback(monkeypatch):
    shown = []
    error = RuntimeError("context negotiation failed")
    monkeypatch.setattr(
        "gui.message_dialogs.show_message",
        lambda *args, **kwargs: shown.append((args, kwargs)),
    )
    widget = SimpleNamespace(
        make_current=lambda: None,
        get_error=lambda: error,
        set_sensitive=lambda value: setattr(widget, "sensitive", value),
    )

    vismol_gtkwidget.VismolGTKWidget.initialize(widget, widget)

    assert widget.sensitive is False
    assert widget._graphics_failure_reported is True
    assert len(shown) == 1
    assert "context negotiation failed" in shown[0][1]["details"]


def test_gl_core_initialization_exception_enters_user_visible_fallback(monkeypatch):
    shown = []
    monkeypatch.setattr(
        "gui.message_dialogs.show_message",
        lambda *args, **kwargs: shown.append((args, kwargs)),
    )

    def fail_initialization():
        raise RuntimeError("shader compiler rejected GLSL")

    widget = SimpleNamespace(
        make_current=lambda: None,
        get_error=lambda: None,
        vm_glcore=SimpleNamespace(initialize=fail_initialization),
        set_sensitive=lambda value: setattr(widget, "sensitive", value),
    )

    vismol_gtkwidget.VismolGTKWidget.initialize(widget, widget)

    assert widget.sensitive is False
    assert widget._graphics_failure_reported is True
    assert len(shown) == 1
    assert "shader compiler rejected GLSL" in shown[0][1]["details"]


def test_disabled_graphics_view_stops_rendering():
    calls = []
    widget = SimpleNamespace(
        _graphics_failure_reported=True,
        vm_glcore=SimpleNamespace(render=lambda: calls.append("render")),
    )

    assert vismol_gtkwidget.VismolGTKWidget.render(widget, None, None) is True
    assert calls == []


@pytest.mark.skipif(
    Gdk.Display.get_default() is None,
    reason="native graphics failure dialog test requires a GTK display",
)
def test_graphics_failure_shows_real_dialog_and_keeps_parent_window_open():
    parent = Gtk.Window(title="Graphics failure test")
    widget = Gtk.GLArea()
    parent.set_child(widget)
    parent.present()
    try:
        vismol_gtkwidget._report_graphics_failure(
            widget, RuntimeError("simulated driver context failure")
        )
        dialog = widget._graphics_error_dialog
        assert parent.get_visible()
        assert dialog.get_visible()
        assert dialog.get_title() == "3D graphics unavailable"
        assert dialog.dialog_kind == "error"
        assert not widget.get_sensitive()

        text_buffer = dialog.details_view.get_buffer()
        details = text_buffer.get_text(
            text_buffer.get_start_iter(), text_buffer.get_end_iter(), True
        )
        assert "OpenGL 3.3 or newer core context" in details
        assert "simulated driver context failure" in details
    finally:
        if getattr(widget, "_graphics_error_dialog", None) is not None:
            widget._graphics_error_dialog.destroy()
        parent.destroy()
