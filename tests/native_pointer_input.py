"""Desktop pointer injection helpers for native full-application smoke tests."""

from __future__ import annotations

import ctypes
import shutil
import subprocess
import sys
import time
from collections.abc import Callable


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


def add_window_point_offset(
    offset: tuple[float, float], correction: tuple[float, float]
) -> tuple[float, float]:
    """Accumulate measured native-window correction across click attempts."""
    return offset[0] + correction[0], offset[1] + correction[1]


def retry_until_native_hit_target(
    prepare_target: Callable[[], None],
    move_pointer: Callable[[], None],
    is_target_under_pointer: Callable[[], bool],
    *,
    attempts: int = 5,
) -> int | None:
    """Restack a native test window until hit-testing confirms the target."""
    if attempts < 1:
        raise ValueError("attempts must be positive")
    for attempt in range(1, attempts + 1):
        prepare_target()
        move_pointer()
        if is_target_under_pointer():
            return attempt
    return None


def minimize_hosted_runner_console_blocker(
    hit_window: int,
    target_window: int,
    window_title: str,
    window_class: str,
    minimize: Callable[[int], bool],
) -> bool:
    """Hide the GitHub runner console only when it blocks the GTK test window."""
    hosted_console = (
        window_class.lower() == "consolewindowclass"
        and "hostedcomputeagent" in window_title.lower()
        and "hosted-compute-agent" in window_title.lower()
    )
    if not hosted_console or hit_window == target_window:
        return False
    return bool(minimize(hit_window))


def win32_hit_belongs_to_target(
    target_window: int,
    hit_window: int,
    *,
    is_child: Callable[[int, int], bool],
    root_owner: Callable[[int], int],
) -> bool:
    """Check whether hit-testing landed in the GTK window's HWND tree.

    GTK may use an owned helper HWND for native input, so WindowFromPoint can
    return a different top-level HWND even when it belongs to this GtkWindow.
    The full-app smoke separately verifies that the injected click reached
    GTK's production picking callback.
    """
    if hit_window == target_window:
        return True
    return bool(is_child(target_window, hit_window)) or (
        root_owner(hit_window) == target_window
    )


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
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetClassNameW.restype = ctypes.c_int
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.IsWindow.argtypes = [wintypes.HWND]
    user32.IsWindow.restype = wintypes.BOOL
    user32.WindowFromPoint.argtypes = [Point]
    user32.WindowFromPoint.restype = wintypes.HWND
    user32.IsChild.argtypes = [wintypes.HWND, wintypes.HWND]
    user32.IsChild.restype = wintypes.BOOL
    user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.GetAncestor.restype = wintypes.HWND
    user32.GetCursorPos.argtypes = [ctypes.POINTER(Point)]
    user32.GetCursorPos.restype = wintypes.BOOL
    user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
    user32.SetCursorPos.restype = wintypes.BOOL
    user32.SetWindowPos.argtypes = [
        wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
        ctypes.c_int, ctypes.c_int, wintypes.UINT,
    ]
    user32.SetWindowPos.restype = wintypes.BOOL
    user32.SetActiveWindow.argtypes = [wintypes.HWND]
    user32.SetActiveWindow.restype = wintypes.HWND
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
    # Hosted Windows can refuse foreground activation, or restack a window
    # from the previous app cycle above a newly created window. Attempt
    # activation first, then put this disposable test window at the top of the
    # topmost band and verify the actual hit target before injecting a click.
    topmost = ctypes.c_void_p(-1)  # HWND_TOPMOST
    not_topmost = ctypes.c_void_p(-2)  # HWND_NOTOPMOST
    z_order_flags = 0x0053  # SWP_NOMOVE|SWP_NOSIZE|SWP_NOACTIVATE|SWP_SHOWWINDOW
    user32.SetForegroundWindow(hwnd)
    user32.BringWindowToTop(hwnd)
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
    hit_attempts = []
    minimized_consoles = []

    def minimize_console(hwnd_to_minimize):
        return bool(user32.ShowWindow(hwnd_to_minimize, 6))  # SW_MINIMIZE

    def restore_consoles():
        for console in minimized_consoles:
            user32.ShowWindow(console, 9)  # SW_RESTORE
        minimized_consoles.clear()

    def describe_window(candidate):
        """Return native identity for a window obscuring the click target."""
        title_length = user32.GetWindowTextLengthW(candidate)
        title_buffer = ctypes.create_unicode_buffer(max(title_length + 1, 2))
        user32.GetWindowTextW(candidate, title_buffer, len(title_buffer))
        class_buffer = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(candidate, class_buffer, len(class_buffer))
        process_id = wintypes.DWORD()
        thread_id = user32.GetWindowThreadProcessId(candidate, ctypes.byref(process_id))
        rect = Rect()
        user32.GetWindowRect(candidate, ctypes.byref(rect))
        return {
            "hwnd": candidate,
            "is_window": bool(user32.IsWindow(candidate)),
            "title": title_buffer.value,
            "class": class_buffer.value,
            "pid": process_id.value,
            "tid": thread_id,
            "rect": (rect.left, rect.top, rect.right, rect.bottom),
        }

    def prepare_target():
        foreground_activated = bool(user32.SetForegroundWindow(hwnd))
        brought_to_top = bool(user32.BringWindowToTop(hwnd))
        active_window_matches = user32.SetActiveWindow(hwnd) == hwnd
        positioned_topmost = bool(
            user32.SetWindowPos(hwnd, topmost, 0, 0, 0, 0, z_order_flags)
        )
        if not positioned_topmost:
            raise ctypes.WinError(ctypes.get_last_error())
        hit_attempts.append({
            "target": describe_window(hwnd),
            "foreground_activation_result": foreground_activated,
            "bring_to_top_result": brought_to_top,
            "active_window_matches_target": active_window_matches,
            "set_topmost_result": positioned_topmost,
        })

    def move_pointer():
        if not user32.SetCursorPos(point.x, point.y):
            raise ctypes.WinError(ctypes.get_last_error())
        time.sleep(0.025)

    def target_is_under_pointer():
        cursor = Point()
        if not user32.GetCursorPos(ctypes.byref(cursor)):
            raise ctypes.WinError(ctypes.get_last_error())
        hit_window = user32.WindowFromPoint(cursor)
        foreground = user32.GetForegroundWindow()
        hit_description = describe_window(hit_window)
        console_minimized = minimize_hosted_runner_console_blocker(
            hit_window,
            hwnd,
            hit_description["title"],
            hit_description["class"],
            minimize_console,
        )
        if console_minimized:
            minimized_consoles.append(hit_window)
        hit_attempts.append({
            "cursor": (cursor.x, cursor.y),
            "hit": hit_description,
            "foreground": describe_window(foreground),
            "hosted_runner_console_minimized": console_minimized,
        })
        if console_minimized:
            return False
        return win32_hit_belongs_to_target(
            hwnd,
            hit_window,
            is_child=user32.IsChild,
            # GA_ROOTOWNER (3) handles owned top-level GTK helper windows.
            root_owner=lambda candidate: user32.GetAncestor(candidate, 3),
        )

    confirmed_attempt = retry_until_native_hit_target(
        prepare_target, move_pointer, target_is_under_pointer
    )
    cursor = Point()
    if not user32.GetCursorPos(ctypes.byref(cursor)):
        raise ctypes.WinError(ctypes.get_last_error())
    hit_window = user32.WindowFromPoint(cursor)
    foreground = user32.GetForegroundWindow()
    if confirmed_attempt is None:
        restore_consoles()
        hit_rect = Rect()
        user32.GetWindowRect(hit_window, ctypes.byref(hit_rect))
        raise RuntimeError(
            "Win32 pointer is not over EasyHybrid: hwnd=%s hit=%s "
            "cursor=(%s,%s) screen=(%s,%s) window_rect=%r client_rect=%r "
            "hit_rect=%r foreground=%r client=%r scale=%s target=%r "
            "attempts=%r"
            % (
                hwnd, hit_window, cursor.x, cursor.y, point.x, point.y,
                (window_rect.left, window_rect.top,
                 window_rect.right, window_rect.bottom),
                (client_rect.left, client_rect.top,
                 client_rect.right, client_rect.bottom),
                (hit_rect.left, hit_rect.top, hit_rect.right, hit_rect.bottom),
                describe_window(foreground), client_point, scale,
                describe_window(hwnd), hit_attempts,
            )
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

    try:
        user32.mouse_event(0x0002, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTDOWN
        time.sleep(0.04)
    finally:
        user32.mouse_event(0x0004, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTUP
        user32.SetWindowPos(hwnd, not_topmost, 0, 0, 0, 0, z_order_flags)
        restore_consoles()
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


def _shortcut_linux_x11() -> str:
    xdotool = shutil.which("xdotool")
    if xdotool is None:
        raise RuntimeError("native Linux keyboard smoke requires xdotool")
    # Without --window, xdotool uses XTest on the focused window.
    result = subprocess.run(
        [xdotool, "key", "--clearmodifiers", "ctrl+n"],
        capture_output=True, text=True, timeout=5, check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("native xdotool key failed: %s" % result.stderr.strip())
    return "linux-x11-xtest:ctrl+n"


def _shortcut_windows() -> str:
    import ctypes

    user32 = ctypes.windll.user32
    vk_control, vk_n, keyup = 0x11, 0x4E, 0x0002
    user32.keybd_event(vk_control, 0, 0, 0)
    user32.keybd_event(vk_n, 0, 0, 0)
    time.sleep(0.03)
    user32.keybd_event(vk_n, 0, keyup, 0)
    user32.keybd_event(vk_control, 0, keyup, 0)
    return "windows-win32-keybd:ctrl+n"


def _shortcut_macos(window) -> str:
    from AppKit import NSApplication
    import Quartz

    title = window.get_title()
    application = NSApplication.sharedApplication()
    native_window = next(
        (candidate for candidate in application.windows() if candidate.title() == title),
        None,
    )
    if native_window is not None:
        native_window.makeKeyAndOrderFront_(None)
    application.activateIgnoringOtherApps_(True)
    # Numeric values, not Quartz.k* names: PyObjC resolves those through a
    # lazy metadata regex scan that stalled a macOS cycle past 90 s
    # (run 40150573184). Values from CGEventTypes.h / Events.h.
    key_n = 45  # kVK_ANSI_N
    command_flag = 0x00100000  # kCGEventFlagMaskCommand (NX_COMMANDMASK)
    hid_event_tap = 0  # kCGHIDEventTap
    create = Quartz.CGEventCreateKeyboardEvent
    set_flags = Quartz.CGEventSetFlags
    post = Quartz.CGEventPost
    for down in (True, False):
        event = create(None, key_n, down)
        if event is None:
            raise RuntimeError("Quartz could not create a keyboard event")
        # The macOS convention users press: Command+N.
        set_flags(event, command_flag)
        post(hid_event_tap, event)
        time.sleep(0.03)
    return "macos-quartz-hid:cmd+n"


def inject_native_shortcut(window) -> str:
    """Press the platform's standard New shortcut (Cmd+N on macOS, else Ctrl+N)."""
    if sys.platform.startswith("linux"):
        return _shortcut_linux_x11()
    if sys.platform == "win32":
        return _shortcut_windows()
    if sys.platform == "darwin":
        return _shortcut_macos(window)
    raise RuntimeError("native keyboard injection is not implemented for %s" % sys.platform)


def native_window_visible_for_process(process_id: int) -> bool:
    """Return whether the process owns a visible EasyHybrid main window."""
    if sys.platform.startswith("linux"):
        xdotool = shutil.which("xdotool")
        if xdotool is None:
            raise RuntimeError("native Linux keyboard smoke requires xdotool")
        result = subprocess.run(
            [xdotool, "search", "--onlyvisible", "--pid", str(process_id),
             "--name", "^EasyHybrid "],
            capture_output=True, text=True, timeout=5, check=False,
        )
        return result.returncode == 0 and bool(result.stdout.strip())

    if sys.platform == "win32":
        from ctypes import wintypes

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.IsWindowVisible.argtypes = [wintypes.HWND]
        user32.IsWindowVisible.restype = wintypes.BOOL
        user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
        user32.GetWindowTextLengthW.restype = ctypes.c_int
        user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        user32.GetWindowTextW.restype = ctypes.c_int
        user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        user32.GetWindowThreadProcessId.restype = wintypes.DWORD
        found = []
        callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def inspect(hwnd, _lparam):
            owner = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
            if owner.value == process_id and user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                title = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, title, length + 1)
                if title.value.startswith("EasyHybrid "):
                    found.append(hwnd)
            return True

        user32.EnumWindows(callback_type(inspect), 0)
        return bool(found)

    if sys.platform == "darwin":
        import Quartz

        windows = Quartz.CGWindowListCopyWindowInfo(1, 0)
        return any(
            int(window.get("kCGWindowOwnerPID", -1)) == process_id
            and str(window.get("kCGWindowName", "")).startswith("EasyHybrid ")
            for window in windows
        )

    raise RuntimeError("native window detection is not implemented for %s" % sys.platform)


def inject_native_quit_shortcut(process_id: int) -> str:
    """Send the production Ctrl+Q / Cmd+Q shortcut to the target app process."""
    if sys.platform.startswith("linux"):
        xdotool = shutil.which("xdotool")
        if xdotool is None:
            raise RuntimeError("native Linux keyboard smoke requires xdotool")
        search = subprocess.run(
            [xdotool, "search", "--onlyvisible", "--pid", str(process_id),
             "--name", "^EasyHybrid "],
            capture_output=True, text=True, timeout=5, check=False,
        )
        if search.returncode != 0 or not search.stdout.strip():
            raise RuntimeError("could not find the visible EasyHybrid X11 window")
        window_id = search.stdout.strip().splitlines()[0]
        focus = subprocess.run(
            [xdotool, "windowfocus", "--sync", window_id],
            capture_output=True, text=True, timeout=5, check=False,
        )
        if focus.returncode != 0:
            raise RuntimeError("native X11 window focus failed: %s" % focus.stderr.strip())
        result = subprocess.run(
            [xdotool, "key", "--clearmodifiers", "ctrl+q"],
            capture_output=True, text=True, timeout=10, check=False,
        )
        if result.returncode != 0:
            raise RuntimeError("native XTest Ctrl+Q failed: %s" % result.stderr.strip())
        return "linux-x11-xtest:ctrl+q"

    if sys.platform == "win32":
        from ctypes import wintypes

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.IsWindowVisible.argtypes = [wintypes.HWND]
        user32.IsWindowVisible.restype = wintypes.BOOL
        user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
        user32.GetWindowTextLengthW.restype = ctypes.c_int
        user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        user32.GetWindowTextW.restype = ctypes.c_int
        user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        user32.GetWindowThreadProcessId.restype = wintypes.DWORD
        user32.SetForegroundWindow.argtypes = [wintypes.HWND]
        user32.SetForegroundWindow.restype = wintypes.BOOL
        found = []
        callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def inspect(hwnd, _lparam):
            owner = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
            if owner.value == process_id and user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                title = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, title, length + 1)
                if title.value.startswith("EasyHybrid "):
                    found.append(hwnd)
            return True

        user32.EnumWindows(callback_type(inspect), 0)
        if not found:
            raise RuntimeError("could not find the EasyHybrid Win32 window")
        user32.SetForegroundWindow(found[0])
        vk_control, vk_q, keyup = 0x11, 0x51, 0x0002
        user32.keybd_event(vk_control, 0, 0, 0)
        user32.keybd_event(vk_q, 0, 0, 0)
        time.sleep(0.03)
        user32.keybd_event(vk_q, 0, keyup, 0)
        user32.keybd_event(vk_control, 0, keyup, 0)
        return "windows-win32-keybd:ctrl+q"

    if sys.platform == "darwin":
        import Quartz
        from AppKit import NSRunningApplication

        app = NSRunningApplication.runningApplicationWithProcessIdentifier_(process_id)
        if app is None:
            raise RuntimeError("could not locate the EasyHybrid macOS application process")
        app.activateWithOptions_(1 << 1)  # NSApplicationActivateIgnoringOtherApps
        for down in (True, False):
            event = Quartz.CGEventCreateKeyboardEvent(None, 12, down)  # kVK_ANSI_Q
            if event is None:
                raise RuntimeError("Quartz could not create a Command+Q key event")
            Quartz.CGEventSetFlags(event, 0x00100000)  # kCGEventFlagMaskCommand
            Quartz.CGEventPost(0, event)  # kCGHIDEventTap
            time.sleep(0.03)
        return "macos-quartz-hid:cmd+q"

    raise RuntimeError("native keyboard injection is not implemented for %s" % sys.platform)
