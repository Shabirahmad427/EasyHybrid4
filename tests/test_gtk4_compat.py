"""Unit coverage for GTK API feature detection and compatibility branches."""

from enum import IntFlag
from types import SimpleNamespace

from src.gtk4_compat import (
    get_scroll_unit,
    scroll_controller_flags,
    set_gl_area_allowed_apis,
    set_picture_contain,
    supports_picture_content_fit,
    supports_scroll_unit,
)


class _ScrollFlags(IntFlag):
    BOTH_AXES = 1
    DISCRETE = 2


class _ScrollUnit:
    SURFACE = "surface"


def test_picture_content_fit_capability_and_legacy_fallback():
    calls = []

    class ModernPicture:
        def set_content_fit(self, value):
            calls.append(("fit", value))

        def set_can_shrink(self, value):
            calls.append(("shrink", value))

        def set_keep_aspect_ratio(self, value):
            calls.append(("aspect", value))

    modern_gtk = SimpleNamespace(
        Picture=ModernPicture,
        ContentFit=SimpleNamespace(CONTAIN="contain"),
    )
    assert supports_picture_content_fit(modern_gtk)
    assert set_picture_contain(ModernPicture(), modern_gtk) == "content-fit"
    assert calls == [("fit", "contain")]

    class LegacyPicture:
        def set_can_shrink(self, value):
            calls.append(("shrink", value))

        def set_keep_aspect_ratio(self, value):
            calls.append(("aspect", value))

    legacy_gtk = SimpleNamespace(Picture=LegacyPicture)
    assert not supports_picture_content_fit(legacy_gtk)
    assert set_picture_contain(LegacyPicture(), legacy_gtk) == "aspect-ratio"
    assert calls[-2:] == [("shrink", True), ("aspect", True)]

    incomplete_gtk = SimpleNamespace(
        Picture=ModernPicture,
        ContentFit=SimpleNamespace(),
    )
    assert not supports_picture_content_fit(incomplete_gtk)
    assert set_picture_contain(ModernPicture(), incomplete_gtk) == "aspect-ratio"


def test_scroll_api_capability_selects_smooth_or_discrete_flags():
    class ModernScrollController:
        def get_unit(self):
            return "surface"

    class LegacyScrollController:
        pass

    modern_gtk = SimpleNamespace(
        EventControllerScroll=ModernScrollController,
        EventControllerScrollFlags=_ScrollFlags,
    )
    legacy_gtk = SimpleNamespace(
        EventControllerScroll=LegacyScrollController,
        EventControllerScrollFlags=_ScrollFlags,
    )
    gdk = SimpleNamespace(ScrollUnit=_ScrollUnit)
    incomplete_gdk = SimpleNamespace()

    assert supports_scroll_unit(modern_gtk, gdk)
    assert scroll_controller_flags(
        modern_gtk, gdk, use_surface_units=True
    ) == _ScrollFlags.BOTH_AXES
    assert scroll_controller_flags(modern_gtk) == (
        _ScrollFlags.BOTH_AXES | _ScrollFlags.DISCRETE
    )
    assert not supports_scroll_unit(legacy_gtk, gdk)
    assert scroll_controller_flags(legacy_gtk, gdk, use_surface_units=True) == (
        _ScrollFlags.BOTH_AXES | _ScrollFlags.DISCRETE
    )
    assert not supports_scroll_unit(modern_gtk, incomplete_gdk)
    assert scroll_controller_flags(
        modern_gtk, incomplete_gdk, use_surface_units=True
    ) == (_ScrollFlags.BOTH_AXES | _ScrollFlags.DISCRETE)
    assert get_scroll_unit(ModernScrollController()) == "surface"
    assert get_scroll_unit(LegacyScrollController()) is None


def test_gl_area_api_selection_is_optional_for_gtk_48():
    calls = []

    class Gtk48GLArea:
        def set_use_es(self, use_es):
            calls.append(("use-es", use_es))

    class ModernGLArea:
        def set_allowed_apis(self, apis):
            calls.append((apis,))

    old_gdk = SimpleNamespace()
    modern_gdk = SimpleNamespace(GLAPI=SimpleNamespace(GL="desktop-gl"))

    assert set_gl_area_allowed_apis(Gtk48GLArea(), old_gdk) is True
    assert set_gl_area_allowed_apis(ModernGLArea(), modern_gdk) is True
    assert calls == [("use-es", False), ("desktop-gl",)]


def test_loaded_gtk_gl_area_exposes_runtime_capability_truthfully():
    from src.gtk4_compat import Gdk, Gtk

    setter_available = callable(getattr(Gtk.GLArea, "set_allowed_apis", None))
    gl_api_available = getattr(getattr(Gdk, "GLAPI", None), "GL", None) is not None
    gl_area = SimpleNamespace()
    if setter_available:
        gl_area.set_allowed_apis = lambda api: setattr(gl_area, "selected_api", api)
    else:
        gl_area.set_use_es = lambda value: setattr(gl_area, "use_es", value)

    result = set_gl_area_allowed_apis(gl_area, Gdk)
    if setter_available and gl_api_available:
        assert result is True
        assert gl_area.selected_api == Gdk.GLAPI.GL
    else:
        assert result is True
        assert gl_area.use_es is False
