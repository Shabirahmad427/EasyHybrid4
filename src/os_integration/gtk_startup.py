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
    GDK preference flag. On Linux, GDK uses EGL on supported X11 and Wayland
    runtimes, so tell PyOpenGL to query that same current context. Other
    platforms retain PyOpenGL's native WGL/CGL selection.
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
        environ.setdefault("PYOPENGL_PLATFORM", "egl")


def configure_startup_environment(project_home):
    """Prepare legacy driver environment before importing GTK."""
    configure_vblank_mode(
        config_path=os.path.join(project_home, ".config.json")
    )
    configure_gl_context_environment()
