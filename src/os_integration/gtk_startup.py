"""Portable, display-independent startup environment preparation.

This module contains the legacy Linux graphics-driver workarounds at the OS
boundary. Importing it does not load GTK or initialize a display.
"""

import glob
import json
import os
import re
import sys
from pathlib import Path

from src.os_integration.win32_wgl import needs_legacy_wgl_workaround
from src.os_integration.app_paths import config_file_candidates


def load_vblank_mode_preference(config_path):
    """Read the saved vblank preference, defaulting safely to ``auto``."""
    try:
        with open(config_path, "r", encoding="utf-8") as config_file:
            data = json.load(config_file)
        return data.get("vblank_mode", "auto")
    except (OSError, ValueError):
        return "auto"


def configure_vblank_mode(*, config_path, platform=None, environ=None,
                          vendor_paths=None):
    """Apply the saved preference and existing Linux Intel driver default."""
    platform = sys.platform if platform is None else platform
    environ = os.environ if environ is None else environ
    if "vblank_mode" in environ:
        return

    preference = load_vblank_mode_preference(config_path)
    if preference in ("on", "off"):
        environ["vblank_mode"] = "1" if preference == "on" else "0"
        return
    if platform != "linux":
        return

    paths = glob.glob("/sys/class/drm/card*/device/vendor") if vendor_paths is None else vendor_paths
    for vendor_path in paths:
        path_parts = Path(vendor_path).parents
        if len(path_parts) < 2:
            continue
        card_name = path_parts[1].name
        if not re.fullmatch(r"card\d+", card_name):
            continue
        try:
            with open(vendor_path, "r", encoding="ascii") as vendor_file:
                vendor_id = vendor_file.read().strip()
        except OSError:
            continue
        if vendor_id == "0x8086":
            environ["vblank_mode"] = "0"
            return


def load_gtk_library():
    """Load the GTK4 shared library, or return ``None`` if unavailable.

    Windows builds name the DLL ``gtk-4-1.dll``; other platforms resolve
    ``gtk-4``. Only full paths found by ``find_library`` are loaded.
    """
    import ctypes
    import ctypes.util

    for name in ("gtk-4", "gtk-4-1", "libgtk-4-1"):
        library_path = ctypes.util.find_library(name)
        if not library_path:
            continue
        try:
            return ctypes.CDLL(library_path)
        except OSError:
            continue
    return None


def gtk_runtime_version():
    """Return the loaded GTK runtime version when it can be found safely."""
    try:
        import ctypes

        gtk_library = load_gtk_library()
        if gtk_library is None:
            return None
        major = gtk_library.gtk_get_major_version
        minor = gtk_library.gtk_get_minor_version
        major.restype = minor.restype = ctypes.c_uint
        return major(), minor()
    except (AttributeError, OSError):
        return None


def configure_gl_context_environment(*, platform=None, environ=None,
                                    runtime_version=None):
    """Align PyOpenGL and GTK context selection with EasyHybrid's GL needs.

    EasyHybrid shaders require desktop OpenGL. GTK 4.14 changed its default
    GDK context preference to GLES; GTK 4.14+ therefore needs the portable
    GDK preference flag. On Linux X11, GTK and PyOpenGL use GLX so PyOpenGL
    can recognize the Gtk.GLArea context on Mesa and native drivers. GTK
    4.16/4.18 builds that reject GDK's ``gl-glx`` flag use EGL for both.
    Wayland uses EGL. Other platforms retain PyOpenGL's native WGL/CGL
    selection.
    """
    platform = sys.platform if platform is None else platform
    environ = os.environ if environ is None else environ

    version = gtk_runtime_version() if runtime_version is None else runtime_version
    if version is not None and version >= (4, 14):
        flags = environ.get("GDK_DEBUG", "").replace(",", ":").split(":")
        if "gl-prefer-gl" not in flags:
            flags.append("gl-prefer-gl")
        environ["GDK_DEBUG"] = ":".join(flag for flag in flags if flag)

    if version is not None and (4, 16) <= tuple(version[:2]) < (4, 18):
        # With GTK 4.16's previous "gl" renderer, closing a window that
        # contains a Gtk.GLArea aborts in libepoxy: gsk_renderer_unrealize
        # drops the last frame's GLArea texture and its release callback
        # (release_gl_texture, gtkglarea.c) calls glDeleteSync with no
        # current context. GTK 4.16's new "ngl" renderer tears down safely
        # (verified with debug symbols on Fedora 41 GTK 4.16.13).
        environ.setdefault("GSK_RENDERER", "ngl")

    if needs_legacy_wgl_workaround(platform, version):
        # GSK's GL renderer would set the ARB-chosen pixel format on each
        # toplevel before the GLArea preset in win32_wgl can run, leaving
        # surface contexts unusable. Explicit user choices are kept.
        environ.setdefault("GSK_RENDERER", "cairo")

    if platform.startswith("linux"):
        if environ.get("WAYLAND_DISPLAY") and not environ.get("DISPLAY"):
            environ.setdefault("PYOPENGL_PLATFORM", "egl")
        elif environ.get("DISPLAY"):
            # Some distro GTK 4.16/4.18 builds reject ``gl-glx`` and fall
            # back to EGL. Keep PyOpenGL on GTK's backend there; forcing GLX
            # gives PyOpenGL a wrapper with no current context.
            if version is not None and (4, 16) <= tuple(version[:2]) < (4, 20):
                environ.setdefault("PYOPENGL_PLATFORM", "egl")
            elif version is not None and tuple(version[:2]) >= (4, 24):
                # GTK 4.24 removed ``gl-glx`` ('Unrecognized value') and picks
                # EGL or GLX per system: EGL on native NVIDIA X11, GLX on
                # Xvfb/Mesa (GTK 4.24.1). Pin GLX with GDK_DISABLE=egl so it
                # matches PyOpenGL, unless the user chose EGL explicitly.
                platform_name = environ.setdefault("PYOPENGL_PLATFORM", "glx")
                if platform_name == "glx":
                    disabled = environ.get("GDK_DISABLE", "").replace(",", ":").split(":")
                    if "egl" not in disabled:
                        disabled.append("egl")
                    environ["GDK_DISABLE"] = ":".join(flag for flag in disabled if flag)
            else:
                environ.setdefault("PYOPENGL_PLATFORM", "glx")
                flags = environ.get("GDK_DEBUG", "").replace(",", ":").split(":")
                if "gl-glx" not in flags:
                    flags.append("gl-glx")
                environ["GDK_DEBUG"] = ":".join(flag for flag in flags if flag)
        else:
            environ.setdefault("PYOPENGL_PLATFORM", "egl")


def load_glib_library():
    """Load the GLib shared library, or return ``None`` if unavailable.

    Windows builds name the DLL ``glib-2.0-0.dll`` (conda-forge) or
    ``libglib-2.0-0.dll`` (MSYS2); other platforms resolve ``glib-2.0``.
    """
    import ctypes
    import ctypes.util

    for name in ("glib-2.0", "glib-2.0-0", "libglib-2.0-0"):
        library_path = ctypes.util.find_library(name)
        if not library_path:
            continue
        try:
            return ctypes.CDLL(library_path)
        except OSError:
            continue
    return None


# GLogLevelFlags: G_LOG_FLAG_RECURSION | G_LOG_FLAG_FATAL |
# G_LOG_LEVEL_CRITICAL | G_LOG_LEVEL_WARNING
_GLIB_RECURSION_SAFE_LEVELS = (1 << 0) | (1 << 1) | (1 << 3) | (1 << 4)


def needs_native_glib_log_handler(version):
    """GTK 4.8 emits a GLib-GObject critical whenever a GtkImage is freed.

    PyGObject turns GLib-GObject criticals into Python warnings, so Python
    code (and its cyclic garbage collector) runs inside the GLib log
    handler. If that collection frees another GtkImage, the nested critical
    is a *recursive* log message, which GLib always treats as fatal: the
    app aborts. GTK 4.10 fixed the GtkImage critical.
    """
    return version is not None and tuple(version[:2]) < (4, 10)


def install_native_glib_log_handler(*, runtime_version=None, glib_library=None):
    """Print GLib-GObject warnings from C on GTK < 4.10. Returns True if set.

    GLib uses the most recently installed handler for a domain, so this
    must run after PyGObject installed its own (on ``import gi``). The
    handler is GLib's own ``g_log_default_handler``; no Python runs inside
    it. Fatal-critical settings such as ``G_DEBUG=fatal-criticals`` still
    apply because GLib checks them outside the handler.
    """
    version = gtk_runtime_version() if runtime_version is None else runtime_version
    if not needs_native_glib_log_handler(version):
        return False
    try:
        import ctypes

        import gi  # noqa: F401  (installs PyGObject's handler first)

        glib = load_glib_library() if glib_library is None else glib_library
        if glib is None:
            return False
        set_handler = glib.g_log_set_handler
        set_handler.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p]
        set_handler.restype = ctypes.c_uint
        default_handler = ctypes.cast(glib.g_log_default_handler, ctypes.c_void_p)
        return bool(set_handler(b"GLib-GObject", _GLIB_RECURSION_SAFE_LEVELS, default_handler, None))
    except (AttributeError, ImportError, OSError):
        return False


def configure_startup_environment(project_home):
    """Prepare legacy driver environment before importing GTK."""
    config_path = next(
        (path for path in config_file_candidates(project_home) if path.is_file()),
        config_file_candidates(project_home)[0],
    )
    configure_vblank_mode(
        config_path=config_path
    )
    configure_gl_context_environment()
    install_native_glib_log_handler()
