"""GTK4 browser and 3D preview for Builder fragment definitions."""

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from gui.windows.builder.fragment_library import (
    FragmentError, discover_fragment_files, load_fragment,
)
from gui.windows.builder.molecule_preview import MoleculePreview


class FragmentLibraryWindow:
    def __init__(self, main=None):
        self.main = main
        self.vm_session = main.vm_session if main is not None else None
        self.visible = False
        self.categories = []
        self._row_paths = {}

    def open_window(self):
        if self.visible:
            self.window.present()
            return

        self.categories = discover_fragment_files()
        self.preview = MoleculePreview()
        self.window = Gtk.Window(
            title="Fragment Library", transient_for=self.main.window
        )
        self.window.set_default_size(860, 500)
        self.window.connect("close-request", self.on_close_button_clicked)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        root.set_margin_top(8)
        root.set_margin_bottom(8)
        root.set_margin_start(8)
        root.set_margin_end(8)

        self.category_model = Gtk.StringList.new(
            [category for category, _entries in self.categories]
        )
        self.category_dropdown = Gtk.DropDown.new(self.category_model, None)
        self.category_dropdown.connect(
            "notify::selected", self.on_category_changed
        )
        root.append(self.category_dropdown)

        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_position(245)
        paned.set_vexpand(True)
        self.fragment_list = Gtk.ListBox()
        self.fragment_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.fragment_list.connect("row-selected", self.on_selection_changed)
        self.fragment_list.connect("row-activated", self.on_fragment_row_activated)
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_child(self.fragment_list)
        paned.set_start_child(scroller)

        self.preview_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.preview_box.set_hexpand(True)
        self.preview_box.set_vexpand(True)
        self.preview_box.append(self.preview.widget)
        paned.set_end_child(self.preview_box)
        root.append(paned)

        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.status_label = Gtk.Label(label="Select a fragment to preview it.", xalign=0)
        self.status_label.set_hexpand(True)
        footer.append(self.status_label)
        use_button = Gtk.Button(label="Use Fragment")
        use_button.connect("clicked", self.on_use_button_clicked)
        footer.append(use_button)
        close_button = Gtk.Button(label="Close")
        close_button.connect("clicked", self.on_close_button_clicked)
        footer.append(close_button)
        root.append(footer)

        self.window.set_child(root)
        self.visible = True
        self.window.present()
        if self.categories:
            self.category_dropdown.set_selected(0)
        else:
            self.status_label.set_text("No fragment definitions were found.")

    def on_category_changed(self, dropdown, _pspec):
        index = dropdown.get_selected()
        self._clear_fragment_rows()
        if index >= len(self.categories):
            return
        _category, entries = self.categories[index]
        for name, path in entries:
            row = Gtk.ListBoxRow()
            row.set_child(Gtk.Label(label=name, xalign=0, margin_start=8))
            self._row_paths[row] = path
            self.fragment_list.append(row)
        first = self.fragment_list.get_row_at_index(0)
        if first is not None:
            self.fragment_list.select_row(first)

    def _clear_fragment_rows(self):
        self._row_paths.clear()
        child = self.fragment_list.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            self.fragment_list.remove(child)
            child = next_child
        self.preview.clear()

    def on_selection_changed(self, _listbox, row):
        if row is None:
            self.preview.clear()
            return
        path = self._row_paths.get(row)
        if path is None:
            self.preview.clear()
            return
        try:
            fragment = load_fragment(path)
        except FragmentError:
            self.preview.clear()
            return
        self.preview.show(fragment["name"], fragment["atoms"], fragment["bonds"])
        self.status_label.set_text(
            f"Preview: {fragment['name']} — choose Use Fragment to arm attachment."
        )

    def _load_and_select(self, row):
        path = self._row_paths.get(row)
        if path is None:
            self.status_label.set_text("Select a fragment first.")
            return
        try:
            fragment = load_fragment(path)
        except FragmentError as error:
            self.status_label.set_text(f"Error: {error}")
            return

        sidebar = getattr(self.main, "builder_sidebar_window", None)
        if sidebar is not None and sidebar.visible:
            sidebar.tool_fragment_radio.set_active(True)
        self.vm_session.builder_selected_fragment = fragment
        self.vm_session.builder_tool = "attach_fragment"
        self.status_label.set_text(
            f"Selected: {fragment['name']} — click a hydrogen in the Builder to attach it."
        )

    def on_fragment_row_activated(self, _listbox, row):
        self._load_and_select(row)

    def on_use_button_clicked(self, _button):
        row = self.fragment_list.get_selected_row()
        self._load_and_select(row)

    def close_window(self, *args):
        if getattr(self, "window", None) is not None:
            self.window.destroy()
            self.window = None
        self.preview = None
        self.visible = False
        return True

    def on_close_button_clicked(self, *args):
        return self.close_window()
