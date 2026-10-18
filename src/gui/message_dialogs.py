"""Portable message and question dialogs for every supported GTK4 minor.

Gtk.MessageDialog is deprecated since GTK 4.10 and its replacement,
Gtk.AlertDialog, does not exist on GTK 4.8. These dialogs are plain
Gtk.Window instances built only from widgets present since GTK 4.0, so the
same code path runs on GTK 4.8 through the latest release on Linux, Windows
and macOS.

Every dialog reports exactly one response: the clicked button's value, or
``cancel_response`` when the window is closed or Escape is pressed.
"""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402

KIND_TITLES = {
    "info": "Information",
    "warning": "Warning",
    "error": "Error",
    "question": "Question",
}


def _parent_window(parent):
    if isinstance(parent, Gtk.Window):
        return parent
    root = parent.get_root() if isinstance(parent, Gtk.Widget) else None
    return root if isinstance(root, Gtk.Window) else None


def choose(parent, text, buttons, callback=None, *, secondary=None, details=None,
           kind="question", title=None, modal=True, cancel_response=None,
           default_response=None):
    """Show a dialog with ``buttons`` and report the chosen response.

    ``buttons`` is a sequence of ``(label, response)`` pairs, laid out left to
    right. ``callback(response)`` runs after the window is destroyed. Returns
    the dialog window.
    """
    if kind not in KIND_TITLES:
        raise ValueError("unknown dialog kind: %r" % (kind,))

    window = Gtk.Window(title=title or KIND_TITLES[kind], modal=modal)
    window.set_resizable(details is not None)
    window.set_default_size(440, -1)
    window.set_destroy_with_parent(True)
    transient = _parent_window(parent)
    if transient is not None:
        window.set_transient_for(transient)
    window.add_css_class("easyhybrid-message-dialog")
    window.dialog_kind = kind

    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    for side in ("top", "bottom", "start", "end"):
        getattr(content, "set_margin_%s" % side)(18)
    window.set_child(content)

    primary = Gtk.Label(xalign=0, wrap=True, selectable=True)
    primary.set_markup("<b>%s</b>" % GLib.markup_escape_text(str(text or "")))
    content.append(primary)
    window.primary_label = primary

    window.secondary_label = None
    if secondary:
        label = Gtk.Label(label=str(secondary), xalign=0, wrap=True, selectable=True)
        content.append(label)
        window.secondary_label = label

    window.details_view = None
    if details is not None:
        view = Gtk.TextView(editable=False, monospace=True, wrap_mode=Gtk.WrapMode.WORD_CHAR)
        view.get_buffer().set_text(str(details) if details else "No further details available.")
        scrolled = Gtk.ScrolledWindow(min_content_height=250, hexpand=True, vexpand=True)
        scrolled.set_child(view)
        expander = Gtk.Expander(label="Show details")
        expander.set_child(scrolled)
        content.append(expander)
        window.details_view = view

    button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, halign=Gtk.Align.END)
    content.append(button_box)

    state = {"done": False}

    def finish(response):
        if state["done"]:
            return
        state["done"] = True
        window.destroy()
        if callback is not None:
            callback(response)

    window.buttons = {}
    default_button = None
    for label, response in buttons:
        button = Gtk.Button(label=label)
        button.connect("clicked", lambda _button, value=response: finish(value))
        button_box.append(button)
        window.buttons[label] = button
        if response == default_response:
            default_button = button
    if default_button is None and window.buttons:
        default_button = button_box.get_last_child()
    if default_button is not None:
        default_button.add_css_class("suggested-action")
        window.set_default_widget(default_button)

    def on_key(_controller, keyval, _keycode, _state):
        if keyval == Gdk.KEY_Escape:
            finish(cancel_response)
            return True
        return False

    keys = Gtk.EventControllerKey()
    keys.connect("key-pressed", on_key)
    window.add_controller(keys)

    def on_close_request(_window):
        finish(cancel_response)
        return True

    window.connect("close-request", on_close_request)
    window.respond = finish
    window.present()
    if default_button is not None:
        default_button.grab_focus()
    return window


def show_message(parent, text, secondary=None, *, kind="info", title=None,
                 details=None, modal=True, on_close=None):
    """Show an informational, warning or error message with an OK button."""
    return choose(
        parent, text, (("OK", True),),
        (lambda _response: on_close()) if on_close is not None else None,
        secondary=secondary, details=details, kind=kind, title=title,
        modal=modal, cancel_response=True, default_response=True,
    )


def ask_yes_no(parent, text, callback=None, *, secondary=None, title=None, modal=True):
    """Ask a yes/no question; ``callback(True)`` only when Yes is chosen."""
    return choose(
        parent, text, (("No", False), ("Yes", True)),
        callback, secondary=secondary, kind="question", title=title,
        modal=modal, cancel_response=False, default_response=True,
    )
