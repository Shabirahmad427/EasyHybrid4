"""User-visible fallback behavior when VisMol cannot initialize OpenGL."""

import sys
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
for source_path in (ROOT / "src", ROOT / "src" / "graphics_engine" / "src"):
    if str(source_path) not in sys.path:
        sys.path.insert(0, str(source_path))

from vismol.gui import vismol_gtkwidget


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


def test_disabled_graphics_view_stops_rendering():
    calls = []
    widget = SimpleNamespace(
        _graphics_failure_reported=True,
        vm_glcore=SimpleNamespace(render=lambda: calls.append("render")),
    )

    assert vismol_gtkwidget.VismolGTKWidget.render(widget, None, None) is True
    assert calls == []
