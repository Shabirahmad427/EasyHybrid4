"""Native desktop pointer injection for the real MainWindow smoke test."""

import ctypes
import shutil
import subprocess
import sys


def _mapped_window_point(widget, root, x, y, Graphene):
    mapped, point = widget.compute_point(root, Graphene.Point().init(float(x), float(y)))
    if not mapped:
        raise RuntimeError("could not map projected atom point into the main window")
    surface = root.get_surface()
    if surface is None:
        raise RuntimeError("main window has no native GDK surface")
    return point, surface, int(surface.get_scale_factor())


def _click_linux_x11(surface, point, scale):
    from gi.repository import GdkX11

    if not isinstance(surface, GdkX11.X11Surface):
        raise RuntimeError("native Linux pointer smoke requires a GDK X11 surface")
    xdotool = shutil.which("xdotool")
    if xdotool is None:
        raise RuntimeError("native Linux pointer smoke requires xdotool")
    xid = GdkX11.X11Surface.get_xid(surface)
    result = subprocess.run(
        [xdotool, "mousemove", "--window", str(xid),
         str(round(point.x * scale)), str(round(point.y * scale)), "click", "1"],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("native Linux XTest click failed: %s" % result.stderr.strip())
    return "linux-x11-xtest"


def _click_windows(surface, point, scale):
    from ctypes import wintypes
    from src.os_integration.win32_wgl import _win32_api

    api = _win32_api()
    if api is None:
        raise RuntimeError("could not load GDK's Win32 surface API")
    hwnd = api.surface_hwnd(surface)
    if not hwnd:
        raise RuntimeError("GDK returned no HWND for the main window")

    class Point(ctypes.Structure):
        _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

    client_origin = Point(0, 0)
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(Point)]
    user32.ClientToScreen.restype = wintypes.BOOL
    if not user32.ClientToScreen(hwnd, ctypes.byref(client_origin)):
        raise ctypes.WinError(ctypes.get_last_error())

    target_x = client_origin.x + round(point.x * scale)
    target_y = client_origin.y + round(point.y * scale)
    if not user32.SetCursorPos(target_x, target_y):
        raise ctypes.WinError(ctypes.get_last_error())

    class MouseInput(ctypes.Structure):
        _fields_ = [
            ("dx", wintypes.LONG),
            ("dy", wintypes.LONG),
            ("mouseData", wintypes.DWORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ctypes.c_size_t),
        ]

    class InputUnion(ctypes.Union):
        _fields_ = [("mi", MouseInput)]

    class Input(ctypes.Structure):
        _anonymous_ = ("value",)
        _fields_ = [("type", wintypes.DWORD), ("value", InputUnion)]

    user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(Input), ctypes.c_int]
    user32.SendInput.restype = wintypes.UINT
    for flags in (0x0002, 0x0004):  # MOUSEEVENTF_LEFTDOWN / MOUSEEVENTF_LEFTUP
        event = Input(type=0, mi=MouseInput(0, 0, 0, flags, 0, 0))
        if user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(Input)) != 1:
            raise ctypes.WinError(ctypes.get_last_error())
    return "windows-sendinput"


def _click_macos(root, point):
    try:
        import AppKit
        import Quartz
    except ImportError as error:
        raise RuntimeError(
            "native macOS pointer smoke requires pyobjc-framework-Cocoa and "
            "pyobjc-framework-Quartz"
        ) from error

    title = root.get_title()
    windows = AppKit.NSApplication.sharedApplication().windows()
    native_window = next((window for window in windows if window.title() == title), None)
    if native_window is None:
        raise RuntimeError("could not match the GTK MainWindow to its native NSWindow")

    # GTK coordinates originate at the content view's upper-left. Convert
    # through the actual view hierarchy so titlebar and window decorations
    # are included before converting to Quartz's screen coordinate space.
    content_view = native_window.contentView()
    content_height = float(content_view.frame().size.height)
    window_point = content_view.convertPoint_toView_(
        (float(point.x), content_height - float(point.y)), None
    )
    cocoa_point = native_window.convertPointToScreen_(window_point)
    screen_height = float(AppKit.NSScreen.mainScreen().frame().size.height)
    quartz_point = Quartz.CGPointMake(float(cocoa_point.x), screen_height - float(cocoa_point.y))

    def post(event_type):
        event = Quartz.CGEventCreateMouseEvent(
            None, event_type, quartz_point, Quartz.kCGMouseButtonLeft
        )
        if event is None:
            raise RuntimeError("CoreGraphics could not create a mouse event")
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)

    post(Quartz.kCGEventMouseMoved)
    post(Quartz.kCGEventLeftMouseDown)
    post(Quartz.kCGEventLeftMouseUp)
    return "macos-quartz-cgevent"


def inject_native_click(widget, root, x, y, Graphene):
    """Click a widget-local point through the active OS input system."""
    point, surface, scale = _mapped_window_point(widget, root, x, y, Graphene)
    if sys.platform.startswith("linux"):
        return _click_linux_x11(surface, point, scale)
    if sys.platform == "win32":
        return _click_windows(surface, point, scale)
    if sys.platform == "darwin":
        return _click_macos(root, point)
    raise RuntimeError("native pointer smoke is unsupported on %s" % sys.platform)
