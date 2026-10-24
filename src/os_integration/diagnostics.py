"""Runtime diagnostic report for the About dialog and bug reports (EH4-601).

Every probe is independent and never raises: a missing OpenGL context,
pDynamo3 installation or Git checkout is reported as unavailable instead of
failing the caller.
"""

import os
import platform
import subprocess
import sys

UNAVAILABLE = "unavailable"


def _probe(function):
    try:
        value = function()
    except Exception as error:  # diagnostics must never take the UI down
        return "%s (%s: %s)" % (UNAVAILABLE, type(error).__name__, error)
    return UNAVAILABLE if value in (None, "") else str(value)


def _decode(value):
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return value


def _git_revision(path, *pathspec):
    """Short commit (and dirty flag) for *path*, or None outside a checkout."""
    if not path or not os.path.isdir(path):
        return None
    command = ["git", "-C", path, "log", "-1", "--format=%h"]
    if pathspec:
        command += ["--", *pathspec]
    revision = subprocess.run(
        command, capture_output=True, text=True, timeout=5, check=False
    ).stdout.strip()
    if not revision:
        return None
    dirty = subprocess.run(
        ["git", "-C", path, "status", "--porcelain", "--", *(pathspec or ("."))],
        capture_output=True, text=True, timeout=5, check=False,
    ).stdout.strip()
    return revision + (" (modified)" if dirty else "")


def _gtk_versions():
    import gi

    gi.require_version("Gtk", "4.0")
    from gi.repository import GLib, Gtk

    return {
        "PyGObject": ".".join(map(str, gi.version_info)),
        "GTK": "%d.%d.%d" % (
            Gtk.get_major_version(), Gtk.get_minor_version(), Gtk.get_micro_version()
        ),
        "GLib": "%d.%d.%d" % (GLib.MAJOR_VERSION, GLib.MINOR_VERSION, GLib.MICRO_VERSION),
    }


def _gdk_backend():
    from gi.repository import Gdk

    display = Gdk.Display.get_default()
    if display is None:
        return "no display"
    # e.g. GdkX11Display, GdkWaylandDisplay, GdkWin32Display, GdkMacosDisplay
    return display.__gtype__.name


def _gl_details(gl_area):
    """GL facts from a realized Gtk.GLArea; an unavailable context is reported."""
    if gl_area is None:
        return {"OpenGL": UNAVAILABLE + " (no graphics widget)"}
    if not gl_area.get_realized():
        return {"OpenGL": UNAVAILABLE + " (graphics view not realized)"}
    gl_area.make_current()
    error = gl_area.get_error()
    if error is not None:
        return {"OpenGL": UNAVAILABLE + " (context error: %s)" % getattr(error, "message", error)}
    context = gl_area.get_context()
    if context is None:
        return {"OpenGL": UNAVAILABLE + " (no GL context)"}
    from OpenGL import GL

    details = {
        "OpenGL": _probe(lambda: _decode(GL.glGetString(GL.GL_VERSION))),
        "GL renderer": _probe(lambda: _decode(GL.glGetString(GL.GL_RENDERER))),
        "GL vendor": _probe(lambda: _decode(GL.glGetString(GL.GL_VENDOR))),
        "GDK GL context": context.__gtype__.name,
        "GL API": "OpenGL ES" if context.get_use_es() else "desktop OpenGL",
    }
    return details


def _pdynamo():
    import pCore

    return getattr(pCore, "__version__", None)


def _pdynamo_location():
    home = os.environ.get("PDYNAMO3_HOME")
    if not home:
        import pCore

        home = os.path.dirname(os.path.dirname(os.path.abspath(pCore.__file__)))
    revision = _git_revision(home)
    return home + (" @ " + revision if revision else "")


def _graphics_engine(app_home):
    import vismol

    version = getattr(vismol, "__version__", None) or UNAVAILABLE
    # The graphics engine is vendored as tracked files, so its revision is the
    # last EasyHybrid commit that touched it.
    revision = _git_revision(app_home, "src/graphics_engine")
    return "vismol %s%s" % (version, ", source " + revision if revision else "")


def collect_diagnostics(app_home=None, gl_area=None):
    """Return an ordered mapping of label -> value; never raises."""
    if app_home is None:
        app_home = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    report = {}

    def version():
        from _version import EASYHYBRID_VERSION

        return EASYHYBRID_VERSION

    report["EasyHybrid"] = _probe(version)
    report["EasyHybrid source"] = _probe(lambda: _git_revision(app_home))
    report["OS"] = _probe(platform.platform)
    report["Architecture"] = _probe(platform.machine)
    report["Python"] = _probe(lambda: "%s (%s)" % (platform.python_version(), sys.executable))
    try:
        report.update(_gtk_versions())
    except Exception as error:
        report["GTK"] = "%s (%s: %s)" % (UNAVAILABLE, type(error).__name__, error)
    report["GDK backend"] = _probe(_gdk_backend)
    try:
        report.update(_gl_details(gl_area))
    except Exception as error:
        report["OpenGL"] = "%s (%s: %s)" % (UNAVAILABLE, type(error).__name__, error)
    report["pDynamo3"] = _probe(_pdynamo)
    report["pDynamo3 location"] = _probe(_pdynamo_location)
    report["Graphics engine"] = _probe(lambda: _graphics_engine(app_home))
    return report


def format_diagnostics(report):
    width = max(len(label) for label in report)
    return "\n".join("%s: %s" % (label.ljust(width), value) for label, value in report.items())
