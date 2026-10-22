"""Desktop pointer injection helpers for native full-application smoke tests."""

from __future__ import annotations

import ctypes
import sys
import time


def logical_to_device_point(x: float, y: float, scale: int) -> tuple[int, int]:
    """Convert GTK application-pixel coordinates to integer device pixels."""
    if scale < 1:
        raise ValueError("surface scale factor must be positive")
    return round(x * scale), round(y * scale)


def appkit_to_quartz_point(
    x: float,
    y: float,
    appkit_origin_x: float,
    appkit_origin_y: float,
    appkit_width: float,
    appkit_height: float,
    quartz_origin_x: float,
    quartz_origin_y: float,
) -> tuple[int, int]:
    """Map AppKit's bottom-left screen coordinates to Quartz desktop points."""
    quartz_x = quartz_origin_x + x - appkit_origin_x
    quartz_y = quartz_origin_y + appkit_origin_y + appkit_height - y
    return round(quartz_x), round(quartz_y)


def _click_windows(window, x: float, y: float) -> str:
    """Inject a left click through Win32 at a GtkWindow client coordinate."""
    from ctypes import wintypes

    class Point(ctypes.Structure):
        _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

    class Rect(ctypes.Structure):
        _fields_ = [
            ("left", wintypes.LONG), ("top", wintypes.LONG),
            ("right", wintypes.LONG), ("bottom", wintypes.LONG),
        ]

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
    user32.FindWindowW.restype = wintypes.HWND
    user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(Point)]
    user32.ClientToScreen.restype = wintypes.BOOL
    user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(Rect)]
    user32.GetClientRect.restype = wintypes.BOOL
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(Rect)]
    user32.GetWindowRect.restype = wintypes.BOOL
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.WindowFromPoint.argtypes = [Point]
    user32.WindowFromPoint.restype = wintypes.HWND
    user32.IsChild.argtypes = [wintypes.HWND, wintypes.HWND]
    user32.IsChild.restype = wintypes.BOOL
    user32.GetCursorPos.argtypes = [ctypes.POINTER(Point)]
    user32.GetCursorPos.restype = wintypes.BOOL
    user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
    user32.SetCursorPos.restype = wintypes.BOOL
    user32.mouse_event.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.c_size_t]
    user32.mouse_event.restype = None

    title = window.get_title()
    hwnd = user32.FindWindowW(None, title)
    if not hwnd:
        raise RuntimeError("could not find the EasyHybrid Win32 window %r" % title)

    surface = window.get_surface()
    scale = surface.get_scale_factor()
    point = Point(*logical_to_device_point(x, y, scale))
    if not user32.ClientToScreen(hwnd, ctypes.byref(point)):
        raise ctypes.WinError(ctypes.get_last_error())
    client_rect, window_rect = Rect(), Rect()
    if not user32.GetClientRect(hwnd, ctypes.byref(client_rect)):
        raise ctypes.WinError(ctypes.get_last_error())
    if not user32.GetWindowRect(hwnd, ctypes.byref(window_rect)):
        raise ctypes.WinError(ctypes.get_last_error())
    client_point = logical_to_device_point(x, y, scale)
    if not (0 <= client_point[0] < client_rect.right
            and 0 <= client_point[1] < client_rect.bottom):
        raise RuntimeError(
            "GTK point is outside Win32 client area: local=%r client=%sx%s "
            "scale=%s window_rect=%r"
            % (
                client_point, client_rect.right, client_rect.bottom, scale,
                (window_rect.left, window_rect.top,
                 window_rect.right, window_rect.bottom),
            )
        )
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    user32.SetForegroundWindow(hwnd)
    foreground = user32.GetForegroundWindow()
    if foreground != hwnd:
        raise RuntimeError(
            "Win32 refused to foreground EasyHybrid: hwnd=%s foreground=%s"
            % (hwnd, foreground)
        )
    if not user32.SetCursorPos(point.x, point.y):
        raise ctypes.WinError(ctypes.get_last_error())

    cursor = Point()
    if not user32.GetCursorPos(ctypes.byref(cursor)):
        raise ctypes.WinError(ctypes.get_last_error())
    hit_window = user32.WindowFromPoint(cursor)
    if hit_window != hwnd and not user32.IsChild(hwnd, hit_window):
        raise RuntimeError(
            "Win32 pointer is not over EasyHybrid: hwnd=%s hit=%s "
            "cursor=(%s,%s) client=%r scale=%s"
            % (hwnd, hit_window, cursor.x, cursor.y, client_point, scale)
        )
    print(
        "EASYHYBRID_WIN32_POINTER_DIAGNOSTIC="
        "hwnd:%s,foreground:%s,hit:%s,client:%r,screen:(%s,%s),scale:%s,"
        "client_size:%sx%s"
        % (
            hwnd, foreground, hit_window, client_point, point.x, point.y,
            scale, client_rect.right, client_rect.bottom,
        ),
        flush=True,
    )

    user32.mouse_event(0x0002, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTDOWN
    time.sleep(0.04)
    user32.mouse_event(0x0004, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTUP
    return "windows-win32-user32"


def _click_macos(window, x: float, y: float) -> str:
    """Inject a Quartz HID click at a point in the GTK window's content view."""
    from AppKit import NSApplication, NSMakePoint, NSMakeRect
    import Quartz

    title = window.get_title()
    application = NSApplication.sharedApplication()
    native_window = next(
        (candidate for candidate in application.windows() if candidate.title() == title),
        None,
    )
    if native_window is None:
        raise RuntimeError("could not find the EasyHybrid AppKit window %r" % title)

    native_window.makeKeyAndOrderFront_(None)
    application.activateIgnoringOtherApps_(True)
    content_view = native_window.contentView()
    bounds = content_view.bounds()
    local_y = y if content_view.isFlipped() else bounds.size.height - y
    window_point = content_view.convertPoint_toView_(NSMakePoint(x, local_y), None)
    screen_point = native_window.convertRectToScreen_(
        NSMakeRect(window_point.x, window_point.y, 0.0, 0.0)
    ).origin

    screen = native_window.screen()
    if screen is None:
        raise RuntimeError("EasyHybrid AppKit window is not assigned to a screen")
    screen_frame = screen.frame()
    display_id = int(screen.deviceDescription()["NSScreenNumber"])
    quartz_bounds = Quartz.CGDisplayBounds(display_id)
    quartz_x, quartz_y = appkit_to_quartz_point(
        screen_point.x,
        screen_point.y,
        screen_frame.origin.x,
        screen_frame.origin.y,
        screen_frame.size.width,
        screen_frame.size.height,
        quartz_bounds.origin.x,
        quartz_bounds.origin.y,
    )
    location = Quartz.CGPointMake(quartz_x, quartz_y)

    def post(event_type):
        event = Quartz.CGEventCreateMouseEvent(
            None, event_type, location, Quartz.kCGMouseButtonLeft
        )
        if event is None:
            raise RuntimeError("Quartz could not create a mouse event")
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)

    post(Quartz.kCGEventMouseMoved)
    time.sleep(0.04)
    post(Quartz.kCGEventLeftMouseDown)
    time.sleep(0.04)
    post(Quartz.kCGEventLeftMouseUp)
    return "macos-quartz-hid"


def inject_native_pointer(window, x: float, y: float) -> str:
    """Deliver a real desktop left-click to ``window`` at local point ``x,y``."""
    if sys.platform == "win32":
        return _click_windows(window, x, y)
    if sys.platform == "darwin":
        return _click_macos(window, x, y)
    raise RuntimeError("native pointer injection is not implemented for %s" % sys.platform)
