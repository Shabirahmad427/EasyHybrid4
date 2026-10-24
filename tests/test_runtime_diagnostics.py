"""EH4-601 runtime diagnostic report: complete, and never fatal without GL."""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT, ROOT / "src", ROOT / "src" / "graphics_engine" / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from src.os_integration.gtk_startup import configure_gl_context_environment  # noqa: E402

# Match the launcher's GL backend before any test opens a display.
configure_gl_context_environment()

from src.os_integration import diagnostics  # noqa: E402

REQUIRED = (
    "EasyHybrid", "OS", "Architecture", "Python", "PyGObject", "GTK", "GLib",
    "GDK backend", "OpenGL", "pDynamo3", "Graphics engine",
)


def test_report_lists_every_component_without_a_gl_context():
    report = diagnostics.collect_diagnostics(app_home=str(ROOT))

    for label in REQUIRED:
        assert label in report and report[label]
    assert report["OpenGL"].startswith("unavailable (no graphics widget)")
    assert report["GTK"].count(".") == 2
    assert report["Graphics engine"].startswith("vismol ")
    text = diagnostics.format_diagnostics(report)
    assert "GTK" in text and "\n" in text


@pytest.mark.parametrize(
    "gl_area, reason",
    [
        (SimpleNamespace(get_realized=lambda: False), "graphics view not realized"),
        (
            SimpleNamespace(
                get_realized=lambda: True,
                make_current=lambda: None,
                get_error=lambda: SimpleNamespace(message="no 3.3 core profile"),
            ),
            "context error: no 3.3 core profile",
        ),
        (
            SimpleNamespace(
                get_realized=lambda: True,
                make_current=lambda: (_ for _ in ()).throw(RuntimeError("driver lost")),
            ),
            "RuntimeError: driver lost",
        ),
    ],
)
def test_unusable_gl_area_is_reported_not_raised(gl_area, reason):
    report = diagnostics.collect_diagnostics(app_home=str(ROOT), gl_area=gl_area)

    assert report["OpenGL"].startswith("unavailable")
    assert reason in report["OpenGL"]


def test_failing_probes_are_isolated(monkeypatch):
    def broken(*_args, **_kwargs):
        raise OSError("probe failed")

    monkeypatch.setattr(diagnostics, "_gtk_versions", broken)
    monkeypatch.setattr(diagnostics, "_gdk_backend", broken)
    monkeypatch.setattr(diagnostics, "_pdynamo", broken)
    monkeypatch.setattr(diagnostics, "_graphics_engine", broken)
    monkeypatch.setattr(diagnostics.platform, "platform", broken)

    report = diagnostics.collect_diagnostics(app_home=str(ROOT))

    for label in ("GTK", "GDK backend", "pDynamo3", "Graphics engine", "OS"):
        assert report[label] == "unavailable (OSError: probe failed)"
    assert report["Python"] != "unavailable"


def _display_or_skip():
    gi = pytest.importorskip("gi")
    gi.require_version("Gtk", "4.0")
    gi.require_version("Gdk", "4.0")
    from gi.repository import Gdk, GLib, Gtk

    if Gdk.Display.get_default() is None:
        pytest.skip("requires a native GTK display")
    return GLib, Gtk


def test_realized_glarea_reports_driver_version_and_renderer():
    GLib, Gtk = _display_or_skip()
    area = Gtk.GLArea()
    area.set_required_version(3, 3)
    window = Gtk.Window(title="EH4-601 diagnostics")
    window.set_default_size(160, 120)
    window.set_child(area)
    window.present()
    context = GLib.MainContext.default()
    deadline = GLib.get_monotonic_time() + 3_000_000
    while not area.get_realized() and GLib.get_monotonic_time() < deadline:
        context.iteration(True)
    try:
        report = diagnostics.collect_diagnostics(app_home=str(ROOT), gl_area=area)
        if area.get_error() is not None:
            assert report["OpenGL"].startswith("unavailable (context error")
        else:
            assert report["OpenGL"][0].isdigit() or "OpenGL" in report["OpenGL"]
            assert report["GL renderer"] and report["GL renderer"] != "unavailable"
            assert report["GL API"] in ("desktop OpenGL", "OpenGL ES")
        assert report["GDK backend"].startswith("Gdk")
    finally:
        window.destroy()


def test_about_dialog_shows_system_information():
    import os

    GLib, Gtk = _display_or_skip()
    if (Gtk.get_major_version(), Gtk.get_minor_version()) < (4, 10) and "fatal-criticals" in (
        os.environ.get("G_DEBUG", "")
    ):
        pytest.skip(
            "GTK 4.8 bare Gtk.AboutDialog emits an upstream GtkImage critical "
            "(Debian #1041599, fixed in GTK 4.10); see GTK4_COMPATIBILITY.md"
        )
    dialog = Gtk.AboutDialog()
    text = diagnostics.format_diagnostics(diagnostics.collect_diagnostics(app_home=str(ROOT)))
    dialog.set_system_information(text)
    try:
        assert dialog.get_system_information() == text
    finally:
        dialog.destroy()
