"""Small native GTK4 helpers shared by simulation windows."""

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk


def selected_vobject(combo, main):
    """Return the VismolObject selected in a GTK4 CoordinatesComboBox."""
    row = combo.get_selected_item()
    if row is None:
        return None
    return main.vm_session.vm_objects_dic.get(row.object_id)


def show_message(parent, title, message):
    """Present a small non-blocking GTK4 message window."""
    window = Gtk.Window(
        title=title, transient_for=parent, modal=True
    )
    window.set_default_size(400, -1)
    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    for edge in ("top", "bottom", "start", "end"):
        getattr(content, f"set_margin_{edge}")(16)
    content.append(Gtk.Label(
        label=message,
        wrap=True,
        xalign=0,
    ))
    button = Gtk.Button(label="Close")
    button.set_halign(Gtk.Align.END)
    button.connect("clicked", lambda *_args: window.close())
    content.append(button)
    window.set_child(content)
    window.present()
    return window


def show_folder_error(parent):
    """Present a non-blocking GTK4 error window for a missing output folder."""
    return show_message(
        parent,
        "Folder not found",
        "The selected folder is not valid. Choose another folder or create it first.",
    )
