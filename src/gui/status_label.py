"""A status line that works on every supported GTK4 minor.

Gtk.Statusbar is deprecated since GTK 4.10. StatusLabel is a Gtk.Label with
the part of its API EasyHybrid uses: push(context_id, text), pop(context_id)
and remove_all(context_id), showing the most recently pushed message, like
Gtk.Statusbar. Builder files name it ``EasyHybridStatusLabel``; importing
this module registers that type (gui.gtk4_builder imports it).
"""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Pango", "1.0")
from gi.repository import Gtk, Pango  # noqa: E402


class StatusLabel(Gtk.Label):
    """Gtk.Label showing the top of a Gtk.Statusbar-style message stack."""

    __gtype_name__ = "EasyHybridStatusLabel"

    def __init__(self, **properties):
        super().__init__(**properties)
        self._messages = []  # (message id, context id, text), oldest first
        self._next_id = 1
        self.set_xalign(0.0)
        self.set_ellipsize(Pango.EllipsizeMode.END)
        self.set_single_line_mode(True)
        self.add_css_class("statusbar")

    def push(self, context_id, text):
        message_id = self._next_id
        self._next_id += 1
        self._messages.append((message_id, int(context_id), str(text)))
        self._refresh()
        return message_id

    def pop(self, context_id):
        for index in range(len(self._messages) - 1, -1, -1):
            if self._messages[index][1] == int(context_id):
                del self._messages[index]
                break
        self._refresh()

    def remove_all(self, context_id):
        self._messages = [message for message in self._messages if message[1] != int(context_id)]
        self._refresh()

    def get_message(self):
        return self._messages[-1][2] if self._messages else ""

    def _refresh(self):
        self.set_text(self.get_message())
