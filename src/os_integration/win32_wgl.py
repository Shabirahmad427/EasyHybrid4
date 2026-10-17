"""Workaround for the GTK 4.8/4.10 Win32 WGL pixel-format mismatch.

GTK 4.8 and 4.10 give the display's bootstrap HDC a pixel format chosen by
GDI ``ChoosePixelFormat()`` but choose each GL surface's format with
``wglChoosePixelFormatARB()``. GDK then makes surface contexts current on
the bootstrap HDC, which WGL rejects with ``ERROR_INVALID_PIXEL_FORMAT``
whenever the two choices differ (Mesa llvmpipe: 75 versus 1). GTK 4.12
reworked the bootstrap HDC and is not affected.

GDK keeps a pixel format that is already set on a window. Setting the GDI
choice, made with GDK's own legacy descriptor, on the GLArea's toplevel
before GDK realizes its context makes both HDCs use the same format.
Importing this module does not load GTK or any Win32 library.
"""

import ctypes
import sys

# GTK 4.12 replaced the bootstrap HDC handling; 4.8 is the supported floor.
LEGACY_WGL_GTK_RANGE = ((4, 8), (4, 12))

PFD_DOUBLEBUFFER = 0x00000001
PFD_DRAW_TO_WINDOW = 0x00000004
PFD_SUPPORT_OPENGL = 0x00000020
PFD_TYPE_RGBA = 0
PFD_MAIN_PLANE = 0
BITSPIXEL = 12


class PIXELFORMATDESCRIPTOR(ctypes.Structure):
    _fields_ = [
        ("nSize", ctypes.c_uint16),
        ("nVersion", ctypes.c_uint16),
        ("dwFlags", ctypes.c_uint32),
        ("iPixelType", ctypes.c_ubyte),
        ("cColorBits", ctypes.c_ubyte),
        ("cRedBits", ctypes.c_ubyte),
        ("cRedShift", ctypes.c_ubyte),
        ("cGreenBits", ctypes.c_ubyte),
        ("cGreenShift", ctypes.c_ubyte),
        ("cBlueBits", ctypes.c_ubyte),
        ("cBlueShift", ctypes.c_ubyte),
        ("cAlphaBits", ctypes.c_ubyte),
        ("cAlphaShift", ctypes.c_ubyte),
        ("cAccumBits", ctypes.c_ubyte),
        ("cAccumRedBits", ctypes.c_ubyte),
        ("cAccumGreenBits", ctypes.c_ubyte),
        ("cAccumBlueBits", ctypes.c_ubyte),
        ("cAccumAlphaBits", ctypes.c_ubyte),
        ("cDepthBits", ctypes.c_ubyte),
        ("cStencilBits", ctypes.c_ubyte),
        ("cAuxBuffers", ctypes.c_ubyte),
        ("iLayerType", ctypes.c_ubyte),
        ("bReserved", ctypes.c_ubyte),
        ("dwLayerMask", ctypes.c_uint32),
        ("dwVisibleMask", ctypes.c_uint32),
        ("dwDamageMask", ctypes.c_uint32),
    ]


def needs_legacy_wgl_workaround(platform, version):
    """Whether this platform/GTK minor has the bootstrap-HDC defect."""
    if platform != "win32" or version is None:
        return False
    low, high = LEGACY_WGL_GTK_RANGE
    return low <= tuple(version[:2]) < high


def legacy_gdk_pixel_format_descriptor(color_bits):
    """Return the descriptor GTK 4.8/4.10 pass to ``ChoosePixelFormat``."""
    pfd = PIXELFORMATDESCRIPTOR()
    pfd.nSize = ctypes.sizeof(PIXELFORMATDESCRIPTOR)
    pfd.nVersion = 1
    pfd.dwFlags = PFD_SUPPORT_OPENGL | PFD_DRAW_TO_WINDOW | PFD_DOUBLEBUFFER
    pfd.iPixelType = PFD_TYPE_RGBA
    pfd.cColorBits = color_bits
    pfd.cAlphaBits = 8
    pfd.dwLayerMask = PFD_MAIN_PLANE
    return pfd


def preset_gdi_pixel_format(api, hwnd):
    """Set GDK's legacy GDI pixel format on ``hwnd`` unless one is set.

    Returns the window's pixel format index, or ``None`` on failure.
    """
    hdc = api.GetDC(hwnd)
    if not hdc:
        return None
    try:
        current = api.GetPixelFormat(hdc)
        if current:
            return current
        pfd = legacy_gdk_pixel_format_descriptor(api.GetDeviceCaps(hdc, BITSPIXEL))
        index = api.ChoosePixelFormat(hdc, ctypes.byref(pfd))
        if index and api.SetPixelFormat(hdc, index, ctypes.byref(pfd)):
            return index
        return None
    finally:
        api.ReleaseDC(hwnd, hdc)


class Win32Api:
    """Typed user32/gdi32 entry points plus GDK's surface-handle getter."""

    def __init__(self, gtk_library):
        from ctypes import wintypes

        # GDI forwards pixel-format calls to the loaded OpenGL ICD. Keep
        # opengl32 loaded for the process lifetime: unloading it between
        # ChoosePixelFormat and GDK's own WGL calls discards the format.
        self.opengl32 = ctypes.WinDLL("opengl32")
        user32 = ctypes.WinDLL("user32")
        gdi32 = ctypes.WinDLL("gdi32")

        self.GetDC = user32.GetDC
        self.GetDC.argtypes = [wintypes.HWND]
        self.GetDC.restype = wintypes.HDC
        self.ReleaseDC = user32.ReleaseDC
        self.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
        self.ReleaseDC.restype = ctypes.c_int
        self.GetDeviceCaps = gdi32.GetDeviceCaps
        self.GetDeviceCaps.argtypes = [wintypes.HDC, ctypes.c_int]
        self.GetDeviceCaps.restype = ctypes.c_int
        self.GetPixelFormat = gdi32.GetPixelFormat
        self.GetPixelFormat.argtypes = [wintypes.HDC]
        self.GetPixelFormat.restype = ctypes.c_int
        self.ChoosePixelFormat = gdi32.ChoosePixelFormat
        self.ChoosePixelFormat.argtypes = [wintypes.HDC, ctypes.c_void_p]
        self.ChoosePixelFormat.restype = ctypes.c_int
        self.SetPixelFormat = gdi32.SetPixelFormat
        self.SetPixelFormat.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_void_p]
        self.SetPixelFormat.restype = wintypes.BOOL

        self._get_handle = gtk_library.gdk_win32_surface_get_handle
        self._get_handle.argtypes = [ctypes.c_void_p]
        self._get_handle.restype = ctypes.c_void_p
        self._capsule_pointer = ctypes.pythonapi.PyCapsule_GetPointer
        self._capsule_pointer.argtypes = [ctypes.py_object, ctypes.c_char_p]
        self._capsule_pointer.restype = ctypes.c_void_p

    def surface_hwnd(self, surface):
        """Return the HWND of a PyGObject ``Gdk.Surface``."""
        return self._get_handle(self._capsule_pointer(surface.__gpointer__, None))


_API = None


def _win32_api():
    global _API
    if _API is None:
        from src.os_integration.gtk_startup import load_gtk_library

        gtk_library = load_gtk_library()
        if gtk_library is None:
            return None
        _API = Win32Api(gtk_library)
    return _API


def _on_create_context(area, api):
    native = area.get_native()
    surface = native.get_surface() if native is not None else None
    if surface is not None:
        try:
            if preset_gdi_pixel_format(api, api.surface_hwnd(surface)) is None:
                print("EasyHybrid: could not preset the legacy WGL pixel format;"
                      " GTK will choose its own.", file=sys.stderr)
        except (AttributeError, OSError, ctypes.ArgumentError) as error:
            print("EasyHybrid: legacy WGL pixel-format preset failed: %s" % error,
                  file=sys.stderr)
    # No context: GTK's default handler still creates and realizes it.
    return None


def install_legacy_wgl_workaround(gl_area, *, platform, version, api=None):
    """Connect the pixel-format preset to ``gl_area`` on affected runtimes."""
    if not needs_legacy_wgl_workaround(platform, version):
        return False
    api = _win32_api() if api is None else api
    if api is None:
        return False
    gl_area.connect("create-context", _on_create_context, api)
    return True
