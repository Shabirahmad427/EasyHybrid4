"""Build EasyHybrid4's GTK4 menu from its native menu data."""

from __future__ import annotations

import json
import re
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, GLib, Gtk


_STOCK_LABELS = {
    "gtk-about": "About",
    "gtk-new": "New",
    "gtk-open": "Open",
    "gtk-quit": "Quit",
    "gtk-save": "Save",
    "gtk-save-as": "Save As",
}


class Gtk4MainMenu:
    """GTK4 action/menu-model implementation of the application menu."""

    HIDDEN_ITEMS = {"test_item", "_show_cell"}

    def __init__(self, owner, source_path):
        self.owner = owner
        self.items = {}
        self._action_group = Gio.SimpleActionGroup()
        with open(source_path, encoding="utf-8") as source:
            menu_items = json.load(source)
        self.model = self._build_menu(menu_items)

    def create_widget(self):
        widget = Gtk.PopoverMenuBar.new_from_model(self.model)
        widget.insert_action_group("main", self._action_group)
        return widget

    def _build_menu(self, entries):
        model = Gio.Menu()
        section = Gio.Menu()

        def finish_section():
            nonlocal section
            if section.get_n_items():
                model.append_section(None, section)
                section = Gio.Menu()

        for element in entries:
            if element.get("type") == "separator":
                finish_section()
                continue

            item_id = element.get("id")
            if item_id in self.HIDDEN_ITEMS:
                continue
            label = element.get("label", item_id or "")
            label = _STOCK_LABELS.get(label, label).replace("_", "")
            submenu = element.get("items")
            if submenu is not None:
                section.append_submenu(label, self._build_menu(submenu))
                continue
            if not item_id:
                continue

            action_name = re.sub(r"[^a-zA-Z0-9_-]", "-", item_id)
            is_check = element.get("type") == "check"
            if is_check:
                active = bool(element.get("active", False))
                action = Gio.SimpleAction.new_stateful(
                    action_name, None, GLib.Variant.new_boolean(active)
                )
                action.get_active = lambda current=action: current.get_state().get_boolean()
            else:
                action = Gio.SimpleAction.new(action_name, None)

            action.connect("activate", self._activate, is_check)
            self._action_group.add_action(action)
            self.items[item_id] = action
            section.append(label, f"main.{action_name}")

        finish_section()
        return model

    def _activate(self, action, _parameter, is_check):
        if is_check:
            action.set_state(GLib.Variant.new_boolean(not action.get_state().get_boolean()))
        self.owner.on_main_menu_activate(action)
