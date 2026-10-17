"""Print the actual OS, Python, PyGObject, GTK and GLib versions for CI evidence.

Usage: python record_runtime.py PROVIDER [EXPECTED_GTK_MINOR]
Exits non-zero when the loaded GTK minor differs from EXPECTED_GTK_MINOR, so
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
    loaded = f"{Gtk.get_major_version()}.{Gtk.get_minor_version()}"
    if loaded != sys.argv[2]:
        sys.exit(f"GTK minor mismatch: requested {sys.argv[2]}, loaded {loaded}")
