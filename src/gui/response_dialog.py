"""A drop-in replacement for Gtk.Dialog that works on every supported GTK4 minor.

Gtk.Dialog is deprecated since GTK 4.10. ResponseDialog is a plain Gtk.Window
with the parts of the Gtk.Dialog API EasyHybrid uses: a content area, action
buttons tied to response ids, a default response, and the ``response``
signal. Like Gtk.Dialog, closing the window (window button or Escape) emits
``Gtk.ResponseType.DELETE_EVENT`` and then closes it. Only widgets present
since GTK 4.0 are used, so behavior is identical on GTK 4.8 through the
latest release on Linux, Windows and macOS.
"""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, GObject, Gtk  # noqa: E402


class ResponseDialog(Gtk.Window):
    """Gtk.Window with a content area, response buttons and a ``response`` signal."""

    __gsignals__ = {
        "response": (GObject.SignalFlags.RUN_LAST, None, (int,)),
    }

    def __init__(self, **properties):
        super().__init__(**properties)
        self._buttons = {}
        layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._content_area = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, vexpand=True)
        self._action_area = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=6, halign=Gtk.Align.END,
        )
        for side in ("top", "bottom", "start", "end"):
            getattr(self._action_area, "set_margin_%s" % side)(6)
        layout.append(self._content_area)
        layout.append(self._action_area)
        super().set_child(layout)

        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self._on_key_pressed)
        self.add_controller(keys)
        self.connect("close-request", self._on_close_request)

    # -- Gtk.Dialog compatible API ---------------------------------------- #

    def get_content_area(self):
        return self._content_area

    def add_button(self, label, response_id):
        button = Gtk.Button(label=label, use_underline=True)
        button.connect("clicked", lambda _button: self.response(response_id))
        self._action_area.append(button)
        self._buttons[int(response_id)] = button
        return button

    def add_buttons(self, *label_response_pairs):
        if len(label_response_pairs) % 2:
            raise ValueError("add_buttons expects (label, response) pairs")
        for index in range(0, len(label_response_pairs), 2):
            self.add_button(label_response_pairs[index], label_response_pairs[index + 1])

    def get_widget_for_response(self, response_id):
        return self._buttons.get(int(response_id))

    def set_default_response(self, response_id):
        button = self.get_widget_for_response(response_id)
        if button is not None:
            button.add_css_class("suggested-action")
            self.set_default_widget(button)

    def set_response_sensitive(self, response_id, sensitive):
        button = self.get_widget_for_response(response_id)
        if button is not None:
            button.set_sensitive(sensitive)

    def response(self, response_id):
        self.emit("response", int(response_id))

    # -- internals -------------------------------------------------------- #

    def _on_key_pressed(self, _controller, keyval, _keycode, _state):
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True
        return False

    def _on_close_request(self, _window):
        self.response(Gtk.ResponseType.DELETE_EVENT)
        return False
