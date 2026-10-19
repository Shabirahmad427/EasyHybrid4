"""Print the actual OS, Python, PyGObject, GTK and GLib versions for CI evidence.

Usage: python record_runtime.py PROVIDER [EXPECTED_GTK_VERSION]
EXPECTED_GTK_VERSION may be a minor (4.8) or exact patch release (4.8.2).
Exits non-zero when the loaded runtime differs from the requested version, so
a package provider cannot silently substitute another release.
"""

import platform
import sys

import gi

gi.require_version("GdkPixbuf", "2.0")
gi.require_version("Gtk", "4.0")
from gi.repository import GdkPixbuf, GLib, Gtk  # noqa: E402,F401

gtk_version = ".".join(
    map(str, (Gtk.get_major_version(), Gtk.get_minor_version(), Gtk.get_micro_version()))
)
glib_version = ".".join(map(str, (GLib.MAJOR_VERSION, GLib.MINOR_VERSION, GLib.MICRO_VERSION)))
pygobject_version = ".".join(map(str, gi.version_info))
provider = sys.argv[1] if len(sys.argv) > 1 else "unspecified"
print(
    f"OS={platform.platform()} ARCH={platform.machine()} "
    f"PYTHON={platform.python_version()} PYGOBJECT={pygobject_version} "
    f"GTK={gtk_version} GLIB={glib_version} GDK_PIXBUF_API=2.0 (imported) "
    f"PROVIDER={provider}"
)
if len(sys.argv) > 2:
    expected = sys.argv[2]
    loaded = gtk_version if expected.count(".") == 2 else ".".join(gtk_version.split(".")[:2])
    if loaded != expected:
        sys.exit(f"GTK version mismatch: requested {expected}, loaded {gtk_version}")
