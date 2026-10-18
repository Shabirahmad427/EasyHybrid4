"""Small GTK4 popover menus for pointer and row actions."""

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, Gdk, Gtk


class ContextMenu:
    """A reusable popover menu whose entries are native GTK4 widgets."""

    def __init__(self, anchor):
        self.anchor = anchor
        self.actions = Gio.SimpleActionGroup()
        self.menu_model = Gio.Menu()
        self.section = Gio.Menu()
        self.popover = Gtk.Popover()
        self.popover.set_autohide(True)
        self.content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.content.set_margin_top(6)
        self.content.set_margin_bottom(6)
        self.content.set_margin_start(6)
        self.content.set_margin_end(6)
        self.header = None
        self.menu_widget = Gtk.PopoverMenu.new_from_model(self.menu_model)
        self.menu_widget.insert_action_group("context", self.actions)
        self.content.append(self.menu_widget)
        self.popover.set_child(self.content)
        self._next_action = 0

    def add_item(self, label, callback=None, *, enabled=True, header=False):
        if header:
            item = Gtk.Label(label=label, xalign=0)
            item.add_css_class("heading")
            self.header = item
            self.content.prepend(item)
        else:
            action_name = f"entry_{self._next_action}"
            self._next_action += 1
            action = Gio.SimpleAction.new(action_name, None)
            action.set_enabled(enabled and callback is not None)
            if callback is not None:
                action.connect("activate", self._activate, callback)
            self.actions.add_action(action)
            self.section.append(label, f"context.{action_name}")
            return action

    def add_separator(self):
        if self.section.get_n_items():
            self.menu_model.append_section(None, self.section)
            self.section = Gio.Menu()

    def add_submenu(self, label):
        submenu = Gio.Menu()
        self.section.append_submenu(label, submenu)
        return _SubmenuBuilder(self, submenu)

    def set_header(self, label):
        if self.header is None:
            self.add_item(label, enabled=False, header=True)
        else:
            self.header.set_text(label)

    def present(self, event=None, *, x=None, y=None):
        if self.section.get_n_items():
            self.menu_model.append_section(None, self.section)
            self.section = Gio.Menu()
        if self.popover.get_parent() is None:
            self.popover.set_parent(self.anchor)
        rectangle = Gdk.Rectangle()
        rectangle.width = 1
        rectangle.height = 1
        if event is not None:
            position = event.get_position()
            if position is not None:
                if len(position) == 3:
                    _success, x, y = position
                else:
                    x, y = position
        if x is not None and y is not None:
            rectangle.x = int(x)
            rectangle.y = int(y)
        self.popover.set_pointing_to(rectangle)
        self.popover.popup()

    def present_at_widget(self, widget):
        """Pop up below ``widget`` (e.g. a button), like GTK3's popup_at_widget.

        Uses Gtk.Widget.compute_bounds, available in every GTK4 release, to
        place the popover in the anchor's coordinates. Falls back to the
        anchor itself when the widget is not in the same window.
        """
        found, bounds = widget.compute_bounds(self.anchor)
        if not found:
            return self.present()
        return self.present(
            x=bounds.get_x() + bounds.get_width() / 2,
            y=bounds.get_y() + bounds.get_height(),
        )

    def _activate(self, action, _parameter, callback):
        self.popover.popdown()
        callback(action)


class _SubmenuBuilder:
    def __init__(self, parent, model):
        self.parent = parent
        self.model = model
        self.section = Gio.Menu()

    def add_item(self, label, callback=None, *, enabled=True, header=False):
        if header:
            return None
        action_name = f"entry_{self.parent._next_action}"
        self.parent._next_action += 1
        action = Gio.SimpleAction.new(action_name, None)
        action.set_enabled(enabled and callback is not None)
        if callback is not None:
            action.connect("activate", self.parent._activate, callback)
        self.parent.actions.add_action(action)
        self.section.append(label, f"context.{action_name}")
        return action

    def add_separator(self):
        if self.section.get_n_items():
            self.model.append_section(None, self.section)
            self.section = Gio.Menu()

    def add_submenu(self, label):
        submenu = Gio.Menu()
        self.section.append_submenu(label, submenu)
        return _SubmenuBuilder(self.parent, submenu)

    def finish(self):
        if self.section.get_n_items():
            self.model.append_section(None, self.section)
            self.section = Gio.Menu()


def append_mapping(menu, entries):
    """Append a nested label-to-callback menu mapping."""
    for label, value in entries.items():
        if label in ("_separator", "separator"):
            menu.add_separator()
        elif label == "header":
            menu.add_item(str(label), enabled=False, header=True)
        elif isinstance(value, dict):
            child = menu.add_submenu(label)
            append_mapping(child, value)
            if hasattr(child, "finish"):
                child.finish()
        elif value is None:
            menu.add_item(label, enabled=False)
        else:
            menu.add_item(label, value)
    return menu
