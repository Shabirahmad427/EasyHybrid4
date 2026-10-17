"""Regression coverage for the GTK 4.8/4.10 Win32 WGL pixel-format workaround.

These tests use a fake Win32 API; the native behaviour is verified only by
the Windows CI GLArea smoke, never by these Linux-runnable checks.
"""

import ctypes

import pytest

from src.os_integration.gtk_startup import configure_gl_context_environment
from src.os_integration.win32_wgl import (
    PFD_DOUBLEBUFFER,
    PFD_DRAW_TO_WINDOW,
    PFD_SUPPORT_OPENGL,
    PIXELFORMATDESCRIPTOR,
    _on_create_context,
    install_legacy_wgl_workaround,
    legacy_gdk_pixel_format_descriptor,
    needs_legacy_wgl_workaround,
    preset_gdi_pixel_format,
)


@pytest.mark.parametrize(
    "platform, version, expected",
    [
        ("win32", (4, 8), True),
        ("win32", (4, 10, 1), True),
        ("win32", (4, 11), True),
        ("win32", (4, 12), False),
        ("win32", (4, 24), False),
        ("win32", None, False),
        ("linux", (4, 8), False),
        ("darwin", (4, 10), False),
    ],
)
def test_workaround_is_limited_to_windows_gtk_before_412(platform, version, expected):
    assert needs_legacy_wgl_workaround(platform, version) is expected


def test_descriptor_matches_gdk_legacy_choose_pixel_format_request():
    pfd = legacy_gdk_pixel_format_descriptor(32)

    assert ctypes.sizeof(PIXELFORMATDESCRIPTOR) == 40
    assert pfd.nSize == 40
    assert pfd.nVersion == 1
    # 37 is the dwFlags value GDK passed in the native Windows WGL trace.
    assert pfd.dwFlags == PFD_SUPPORT_OPENGL | PFD_DRAW_TO_WINDOW | PFD_DOUBLEBUFFER == 37
    assert (pfd.cColorBits, pfd.cAlphaBits, pfd.cDepthBits) == (32, 8, 0)


class FakeWin32:
    def __init__(self, current=0, chosen=75, set_ok=True, hdc=0x1234):
        self.current = current
        self.chosen = chosen
        self.set_ok = set_ok
        self.hdc = hdc
        self.calls = []

    def GetDC(self, hwnd):
        self.calls.append(("GetDC", hwnd))
        return self.hdc

    def ReleaseDC(self, hwnd, hdc):
        self.calls.append(("ReleaseDC", hwnd, hdc))
        return 1

    def GetDeviceCaps(self, hdc, index):
        return 32

    def GetPixelFormat(self, hdc):
        return self.current

    def ChoosePixelFormat(self, hdc, pfd):
        self.calls.append(("ChoosePixelFormat", hdc))
        return self.chosen

    def SetPixelFormat(self, hdc, index, pfd):
        self.calls.append(("SetPixelFormat", hdc, index))
        if self.set_ok:
            self.current = index
        return self.set_ok

    def surface_hwnd(self, surface):
        return surface.hwnd


def test_preset_sets_gdi_choice_on_unformatted_window_and_releases_dc():
    api = FakeWin32()

    assert preset_gdi_pixel_format(api, 0x99) == 75
    assert ("SetPixelFormat", 0x1234, 75) in api.calls
    assert api.calls[-1] == ("ReleaseDC", 0x99, 0x1234)


def test_preset_never_replaces_existing_window_pixel_format():
    api = FakeWin32(current=1)

    assert preset_gdi_pixel_format(api, 0x99) == 1
    assert not any(call[0] == "SetPixelFormat" for call in api.calls)


@pytest.mark.parametrize("api", [FakeWin32(chosen=0), FakeWin32(set_ok=False), FakeWin32(hdc=0)])
def test_preset_reports_failure_without_raising(api):
    assert preset_gdi_pixel_format(api, 0x99) is None


class FakeSurface:
    hwnd = 0x99


class FakeNative:
    def get_surface(self):
        return FakeSurface()


class FakeGLArea:
    def __init__(self):
        self.connections = []

    def connect(self, signal, handler, *data):
        self.connections.append((signal, handler, data))

    def get_native(self):
        return FakeNative()


def test_create_context_handler_presets_format_and_defers_to_gtk():
    api = FakeWin32()

    # Returning None lets GtkGLArea's default handler create the context.
    assert _on_create_context(FakeGLArea(), api) is None
    assert api.current == 75


def test_install_connects_only_on_affected_runtimes():
    affected, current = FakeGLArea(), FakeGLArea()
    api = FakeWin32()

    assert install_legacy_wgl_workaround(affected, platform="win32", version=(4, 10), api=api)
    assert not install_legacy_wgl_workaround(current, platform="win32", version=(4, 12), api=api)
    assert [signal for signal, _, _ in affected.connections] == ["create-context"]
    assert current.connections == []


def test_startup_selects_cairo_gsk_renderer_only_for_legacy_windows():
    legacy, modern, linux_legacy = {}, {}, {}

    configure_gl_context_environment(platform="win32", environ=legacy, runtime_version=(4, 10))
    configure_gl_context_environment(platform="win32", environ=modern, runtime_version=(4, 12))
    configure_gl_context_environment(platform="linux", environ=linux_legacy, runtime_version=(4, 8))

    assert legacy == {"GSK_RENDERER": "cairo"}
    assert "GSK_RENDERER" not in modern
    assert "GSK_RENDERER" not in linux_legacy


def test_startup_keeps_user_selected_gsk_renderer():
    environment = {"GSK_RENDERER": "gl"}

    configure_gl_context_environment(platform="win32", environ=environment, runtime_version=(4, 8))

    assert environment["GSK_RENDERER"] == "gl"
