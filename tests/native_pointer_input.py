"""Desktop pointer injection helpers for native full-application smoke tests."""

from __future__ import annotations

import ctypes
import shutil
import subprocess
import sys
import time


def logical_to_device_point(x: float, y: float, scale: int) -> tuple[int, int]:
    """Convert GTK application-pixel coordinates to integer device pixels."""
    if scale < 1:
        raise ValueError("surface scale factor must be positive")
    return round(x * scale), round(y * scale)


def adjust_window_point_from_gesture_feedback(
    window_x: float,
    window_y: float,
    *,
    target_framebuffer_point: tuple[float, float],
    observed_framebuffer_point: tuple[float, float],
    widget_size: tuple[float, float],
    framebuffer_size: tuple[float, float],
) -> tuple[float, float]:
    """Correct a native click point using the coordinates GTK actually saw.

    Native window systems can include client-area offsets that differ from
    GTK's widget-to-toplevel transform. Convert the measured pick error back
    to logical widget units and apply that correction to the next OS click.
    """
    widget_width, widget_height = map(float, widget_size)
    framebuffer_width, framebuffer_height = map(float, framebuffer_size)
    if min(widget_width, widget_height, framebuffer_width, framebuffer_height) <= 0:
        raise ValueError("widget and framebuffer dimensions must be positive")
    dx = (target_framebuffer_point[0] - observed_framebuffer_point[0]) * (
        widget_width / framebuffer_width
    )
    dy = (target_framebuffer_point[1] - observed_framebuffer_point[1]) * (
        widget_height / framebuffer_height
    )
    return window_x + dx, window_y + dy


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
    user32.SetWindowPos.argtypes = [
        wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
        ctypes.c_int, ctypes.c_int, wintypes.UINT,
    ]
    user32.SetWindowPos.restype = wintypes.BOOL
    user32.mouse_event.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.c_size_t]
    user32.mouse_event.restype = None

    title = window.get_title()
    hwnd = user32.FindWindowW(None, title)
    if not hwnd:
        raise RuntimeError("could not find the EasyHybrid Win32 window %r" % title)

    surface = window.get_surface()
    scale = surface.get_scale_factor()
    # Restore/raise before converting client coordinates: SW_RESTORE may move
    # a minimized window, which would make a pre-restore ClientToScreen stale.
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    user32.BringWindowToTop(hwnd)
    # Also place it above non-foreground runner windows. The click itself will
    # activate the target; SetForegroundWindow may be blocked by Windows policy.
    if not user32.SetWindowPos(hwnd, None, 0, 0, 0, 0, 0x0053):
        raise ctypes.WinError(ctypes.get_last_error())  # NOMOVE|NOSIZE|NOACTIVATE|SHOWWINDOW
    user32.SetForegroundWindow(hwnd)
    foreground = user32.GetForegroundWindow()
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
    # Hosted runners may keep the previous test process or runner shell as
    # the foreground window. Windows can refuse SetForegroundWindow in that
    # case, but a real pointer click still activates the verified window under
    # the cursor. The hit-test below and the production GTK pick are the actual
    # delivery checks; foreground state alone is not.
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
        "hwnd:%s,foreground:%s,foreground_match:%s,hit:%s,client:%r,screen:(%s,%s),scale:%s,"
        "client_size:%sx%s"
        % (
            hwnd, foreground, foreground == hwnd, hit_window, client_point, point.x, point.y,
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


def _click_linux_x11(window, x: float, y: float) -> str:
    """Inject an XTest click at a GtkWindow content coordinate on X11."""
    import gi

    gi.require_version("GdkX11", "4.0")
    from gi.repository import GdkX11

    xdotool = shutil.which("xdotool")
    if xdotool is None:
        raise RuntimeError("native Linux pointer smoke requires xdotool")
    surface = window.get_surface()
    if surface is None or not isinstance(surface, GdkX11.X11Surface):
        raise RuntimeError("native Linux pointer smoke requires a GDK X11 surface")
    scale = surface.get_scale_factor()
    xid = GdkX11.X11Surface.get_xid(surface)
    click_x, click_y = logical_to_device_point(x, y, scale)
    try:
        result = subprocess.run(
            [xdotool, "mousemove", "--window", str(xid), str(click_x), str(click_y), "click", "1"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RuntimeError("native xdotool click failed: %s" % error) from error
    if result.returncode != 0:
        raise RuntimeError("native xdotool click failed: %s" % result.stderr.strip())
    return "linux-x11-xtest"


def inject_native_pointer(window, x: float, y: float) -> str:
    """Deliver a real desktop left-click to ``window`` at local point ``x,y``."""
    if sys.platform.startswith("linux"):
        return _click_linux_x11(window, x, y)
    if sys.platform == "win32":
        return _click_windows(window, x, y)
    if sys.platform == "darwin":
        return _click_macos(window, x, y)
    raise RuntimeError("native pointer injection is not implemented for %s" % sys.platform)
