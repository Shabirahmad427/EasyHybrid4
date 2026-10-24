"""Centralized GTK4 capability checks and compatibility helpers.

Feature detection is used instead of release-string comparisons so the
application follows the APIs exposed by the loaded GTK runtime and typelib.
"""

import math
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

    When the caller can distinguish event units, leave deltas continuous so
    it can normalize wheel detents and surface pixels itself. Otherwise ask
    GTK for discrete, wheel-like steps as a compatibility fallback.
    """
    flags = gtk.EventControllerScrollFlags.BOTH_AXES
    if not (use_surface_units and supports_scroll_unit(gtk, gdk)):
        flags |= gtk.EventControllerScrollFlags.DISCRETE
    return flags


def get_scroll_unit(controller):
    """Return the controller's scroll unit when the loaded API provides it."""
    getter = getattr(controller, "get_unit", None)
    return getter() if callable(getter) else None


def widget_to_framebuffer_coordinates(
    x, y, *, widget_width, widget_height, framebuffer_width, framebuffer_height
):
    """Map GTK widget-local input coordinates to GL framebuffer pixels.

    GTK input coordinates use logical widget units while Gtk.GLArea's resize
    dimensions describe the render target. Their measured ratio accounts for
    HiDPI scale and avoids assuming a fixed monitor scale factor.
    """
    try:
        widget_width = float(widget_width)
        widget_height = float(widget_height)
        framebuffer_width = float(framebuffer_width)
        framebuffer_height = float(framebuffer_height)
        x = float(x)
        y = float(y)
    except (TypeError, ValueError):
        return x, y

    if widget_width <= 0 or widget_height <= 0:
        return x, y
    if framebuffer_width <= 0 or framebuffer_height <= 0:
        return x, y

    return (
        x * framebuffer_width / widget_width,
        y * framebuffer_height / widget_height,
    )


def scroll_delta_to_steps(delta, *, surface, remainder=0.0, pixels_per_step=30.0):
    """Convert deltas to steps; positive consistently means scroll down.

    GDK reports positive wheel deltas in southward detents and positive
    surface deltas in downward logical pixels. Preserve that direction while
    scaling surface pixels and retaining partial steps.
    """
    try:
        delta = float(delta)
        remainder = float(remainder)
        pixels_per_step = float(pixels_per_step)
    except (TypeError, ValueError):
        return 0, remainder
    if not math.isfinite(delta) or not math.isfinite(remainder):
        return 0, remainder
    if surface:
        if not math.isfinite(pixels_per_step) or pixels_per_step <= 0:
            raise ValueError("pixels_per_step must be finite and positive")
        total = remainder + delta / pixels_per_step
        steps = int(total)
        return steps, total - steps
    total = remainder + delta
    steps = int(total)
    return steps, total - steps


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


# PyGObject cannot construct Gtk expressions against GTK 4.8: on every
# PyGObject release conda-forge pairs with it (3.42-3.46),
# ``Gtk.PropertyExpression.new`` raises "TypeError: No means to translate
# argument or return value for 'GtkPropertyExpression'". GTK 4.10+ works.
# The helpers below avoid expressions entirely so one code path serves every
# minor. Gtk.DropDown displays Gtk.StringList items without any expression;
# only models of custom rows need ``bind_dropdown_label_property``.


def _setup_dropdown_label(_factory, list_item):
    list_item.set_child(Gtk.Label(xalign=0))


def _bind_dropdown_label(_factory, list_item, property_name):
    item = list_item.get_item()
    text = item.get_property(property_name) if item is not None else ""
    list_item.get_child().set_text("" if text is None else str(text))


def bind_dropdown_label_property(dropdown, property_name, gtk=Gtk):
    """Show each item's ``property_name`` in ``dropdown`` on every GTK4 minor.

    Replaces ``dropdown.set_expression(Gtk.PropertyExpression.new(Row, None,
    property_name))``, which fails on GTK 4.8. Returns the factory.
    """
    factory = gtk.SignalListItemFactory()
    factory.connect("setup", _setup_dropdown_label)
    factory.connect("bind", _bind_dropdown_label, property_name)
    dropdown.set_factory(factory)
    return factory


def property_sorter(property_name, numeric=False, gtk=Gtk):
    """Return a sorter ordering items by ``property_name`` on every GTK4 minor.

    Replaces ``Gtk.StringSorter``/``Gtk.NumericSorter`` built from a
    ``Gtk.PropertyExpression`` (unavailable from Python on GTK 4.8). Strings
    compare case-insensitively, like Gtk.StringSorter's default; numbers
    compare numerically with missing values first.
    """

    def key(item):
        value = item.get_property(property_name)
        if numeric:
            try:
                return (1, float(value))
            except (TypeError, ValueError):
                return (0, 0.0)
        return "" if value is None else str(value).casefold()

    def compare(first, second, *_data):
        first_key, second_key = key(first), key(second)
        return (first_key > second_key) - (first_key < second_key)

    return gtk.CustomSorter.new(compare, None)


def rgba_components(rgba):
    """Return ``[red, green, blue, alpha]`` of a Gdk.RGBA.

    ``list(rgba)`` only works from PyGObject 3.58 (Gdk.RGBA gained
    ``__iter__``); PyGObject 3.42-3.50, common with GTK 4.8-4.14, raises
    TypeError.
    """
    return [rgba.red, rgba.green, rgba.blue, rgba.alpha]


def texture_from_pixbuf(pixbuf, gdk=Gdk):
    """Return a Gdk.Texture with ``pixbuf``'s pixels, or None.

    Gtk.Image.set_from_pixbuf, Gtk.Picture.set_pixbuf and their
    constructors are deprecated since GTK 4.12, and their replacement
    Gdk.Texture.new_for_pixbuf is itself deprecated since GTK 4.20.
    Gdk.MemoryTexture exists since GTK 4.0, so this one path works on every
    supported minor. GdkPixbuf stores 8-bit, non-premultiplied RGB(A).
    """
    if pixbuf is None:
        return None
    memory_format = (gdk.MemoryFormat.R8G8B8A8 if pixbuf.get_has_alpha()
                     else gdk.MemoryFormat.R8G8B8)
    return gdk.MemoryTexture.new(pixbuf.get_width(), pixbuf.get_height(), memory_format,
                                 pixbuf.read_pixel_bytes(), pixbuf.get_rowstride())
