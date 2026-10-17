"""Centralized GTK4 capability checks and compatibility helpers.

Feature detection is used instead of release-string comparisons so the
application follows the APIs exposed by the loaded GTK runtime and typelib.
"""

import sys

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gtk  # noqa: E402  (require_version first)

from src.os_integration.win32_wgl import install_legacy_wgl_workaround  # noqa: E402


# GTK's invalid list position is a guint sentinel. Some older GTK4 typelib
# builds omit exporting this C macro through introspection.
GTK_INVALID_LIST_POSITION = getattr(Gtk, "INVALID_LIST_POSITION", 2**32 - 1)


def supports_picture_content_fit(gtk=Gtk):
    """Whether Gtk.Picture exposes GTK 4.8's content-fit API."""
    content_fit = getattr(gtk, "ContentFit", None)
    return (
        callable(getattr(gtk.Picture, "set_content_fit", None))
        and content_fit is not None
        and hasattr(content_fit, "CONTAIN")
    )


def set_picture_contain(picture, gtk=Gtk):
    """Keep a picture's full image visible using the available GTK API."""
    if supports_picture_content_fit(gtk):
        picture.set_content_fit(gtk.ContentFit.CONTAIN)
        return "content-fit"

    # Defensive fallback for GTK builds predating the GTK 4.8 runtime floor.
    picture.set_can_shrink(True)
    picture.set_keep_aspect_ratio(True)
    return "aspect-ratio"


def supports_scroll_unit(gtk=Gtk, gdk=Gdk):
    """Whether scroll controllers can identify wheel vs surface units."""
    scroll_unit = getattr(gdk, "ScrollUnit", None)
    return (
        callable(getattr(gtk.EventControllerScroll, "get_unit", None))
        and scroll_unit is not None
        and hasattr(scroll_unit, "SURFACE")
    )


def scroll_controller_flags(gtk=Gtk, gdk=Gdk, *, use_surface_units=False):
    """Return portable scroll flags for the selected input semantics.

    Surface-unit handling is only selected by a caller that knows it consumes
    smooth surface deltas. Otherwise GTK emits discrete, wheel-like steps.
    """
    flags = gtk.EventControllerScrollFlags.BOTH_AXES
    if not (use_surface_units and supports_scroll_unit(gtk, gdk)):
        flags |= gtk.EventControllerScrollFlags.DISCRETE
    return flags


def get_scroll_unit(controller):
    """Return the controller's scroll unit when the loaded API provides it."""
    getter = getattr(controller, "get_unit", None)
    return getter() if callable(getter) else None


def set_gl_area_allowed_apis(gl_area, gdk=Gdk, api=None):
    """Restrict Gtk.GLArea APIs when supported by the loaded GTK runtime.

    ``set_allowed_apis`` is not present in the GTK 4.8 API. Use its older
    ``set_use_es(False)`` equivalent when available; GTK 4.12+ deprecates that
    method in favor of the explicit allowed-APIs setter.
    """
    setter = getattr(gl_area, "set_allowed_apis", None)
    if callable(setter):
        gl_api = api
        if gl_api is None:
            gl_api = getattr(getattr(gdk, "GLAPI", None), "GL", None)
        if gl_api is not None:
            setter(gl_api)
            return True

    # GTK 4.8's Gtk.GLArea has no allowed-APIs property, but this method
    # explicitly requests desktop GL and is still present throughout the
    # GTK4 range. If the runtime lacks both APIs, its default remains usable.
    set_use_es = getattr(gl_area, "set_use_es", None)
    if callable(set_use_es):
        set_use_es(False)
        return True
    return False


def apply_legacy_win32_wgl_workaround(gl_area, gtk=Gtk, platform=None):
    """Align a GLArea's WGL pixel format with GTK 4.8/4.10's bootstrap HDC.

    This is a version range check, not feature detection: the defect is in
    GDK's private Win32 WGL code and exposes no API to probe. Returns
    whether the workaround was connected.
    """
    return install_legacy_wgl_workaround(
        gl_area,
        platform=sys.platform if platform is None else platform,
        version=(gtk.get_major_version(), gtk.get_minor_version()),
    )


def gl_area_required_version(gtk=Gtk, platform=None):
    """Return the GL version to request for EasyHybrid's ``#version 330`` shaders.

    GTK 4.8/4.10's macOS backend maps only exact 3.2 and 4.1 requests to Core
    profiles; any other version (including 3.3) silently gets a Legacy
    profile, which cannot share objects with GDK's Core context and fails
    with "invalid share context". GTK 4.12 fixed the mapping. On macOS a
    3.2 Core request returns the highest Core version the Mac supports
    (4.1), which runs ``#version 330``; callers still verify the real
    context version after realization.
    """
    platform = sys.platform if platform is None else platform
    version = (gtk.get_major_version(), gtk.get_minor_version())
    if platform == "darwin" and version < (4, 12):
        return (3, 2)
    return (3, 3)
