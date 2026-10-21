"""Unit coverage for desktop pointer coordinate mapping and event posting."""

import ctypes
import sys
from types import SimpleNamespace

import pytest

from tests import native_pointer
from src.os_integration import win32_wgl


class _FakeCall:
    def __init__(self, callback):
        self.callback = callback

    def __call__(self, *args):
        return self.callback(*args)


def test_windows_click_maps_logical_coordinates_and_posts_button_pair(monkeypatch):
    target = {}

    class FakeUser32:
        def __init__(self):
            self.ClientToScreen = _FakeCall(
                lambda _hwnd, point: (
                    setattr(point._obj, "x", 100),
                    setattr(point._obj, "y", 200),
                    1,
                )[-1]
            )
            self.SetCursorPos = _FakeCall(
                lambda x, y: target.update(cursor=(x, y)) or 1
            )
            self.SendInput = _FakeCall(
                lambda _count, inputs, _size: (
                    target.setdefault("flags", []).append(
                        inputs._obj.mi.dwFlags
                    ),
                    1,
                )[-1]
            )

    user32 = FakeUser32()
    monkeypatch.setattr(ctypes, "WinDLL", lambda *_args, **_kwargs: user32, raising=False)
    monkeypatch.setattr(
        win32_wgl,
        "_win32_api",
        lambda: SimpleNamespace(surface_hwnd=lambda _surface: 42),
    )

    result = native_pointer._click_windows(
        object(), SimpleNamespace(x=12, y=17), scale=2
    )

    assert result == "windows-sendinput"
    assert target == {"cursor": (124, 234), "flags": [0x0002, 0x0004]}


def test_macos_click_converts_content_to_quartz_coordinates_and_posts_events(
    monkeypatch,
):
    events = []

    class FakeContentView:
        def frame(self):
            return SimpleNamespace(size=SimpleNamespace(height=400.0))

        def convertPoint_toView_(self, point, _view):
            return point

    class FakeWindow:
        def title(self):
            return "EasyHybrid test"

        def contentView(self):
            return FakeContentView()

        def convertPointToScreen_(self, point):
            return SimpleNamespace(x=point[0] + 100.0, y=point[1] + 200.0)

    appkit = SimpleNamespace(
        NSApplication=SimpleNamespace(
            sharedApplication=lambda: SimpleNamespace(windows=lambda: [FakeWindow()])
        ),
        NSScreen=SimpleNamespace(
            mainScreen=lambda: SimpleNamespace(
                frame=lambda: SimpleNamespace(size=SimpleNamespace(height=1000.0))
            )
        ),
    )

    class FakeQuartz:
        kCGMouseButtonLeft = 0
        kCGEventMouseMoved = 5
        kCGEventLeftMouseDown = 1
        kCGEventLeftMouseUp = 2
        kCGHIDEventTap = 0

        @staticmethod
        def CGPointMake(x, y):
            return (x, y)

        @staticmethod
        def CGEventCreateMouseEvent(_source, event_type, point, _button):
            return (event_type, point)

        @staticmethod
        def CGEventPost(_tap, event):
            events.append(event)

    monkeypatch.setitem(sys.modules, "AppKit", appkit)
    monkeypatch.setitem(sys.modules, "Quartz", FakeQuartz)

    result = native_pointer._click_macos(
        SimpleNamespace(get_title=lambda: "EasyHybrid test"),
        SimpleNamespace(x=12.5, y=34.5),
    )

    assert result == "macos-quartz-cgevent"
    assert events == [
        (FakeQuartz.kCGEventMouseMoved, (112.5, 434.5)),
        (FakeQuartz.kCGEventLeftMouseDown, (112.5, 434.5)),
        (FakeQuartz.kCGEventLeftMouseUp, (112.5, 434.5)),
    ]
