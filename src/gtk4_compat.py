"""Small compatibility values for the GTK 4.0 baseline."""

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk


# GTK's invalid list position is a guint sentinel. Some older GTK4 typelib
# builds omit exporting this C macro through introspection.
GTK_INVALID_LIST_POSITION = getattr(Gtk, "INVALID_LIST_POSITION", 2**32 - 1)
