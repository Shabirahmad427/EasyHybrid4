"""Native GTK4 browser and preview for complete MOL2 structures."""

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from gui.windows.builder.structure_library import (
    StructureError, discover_structure_files, load_structure,
)
from gui.windows.builder.molecule_preview import MoleculePreview


class StructureLibraryWindow:
    def __init__(self, main=None):
        self.main = main
        self.vm_session = main.vm_session if main is not None else None
        self.visible = False
        self._row_paths = {}

    def open_window(self):
        if self.visible:
            self.window.present()
            return
        self.categories = discover_structure_files()
        self.preview = MoleculePreview()
        self.window = Gtk.Window(title="Structure Library", transient_for=self.main.window)
        self.window.set_default_size(860, 500)
        self.window.connect("close-request", self.on_close_button_clicked)
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        for side in ("top", "bottom", "start", "end"):
            getattr(root, f"set_margin_{side}")(8)
        self.category_dropdown = Gtk.DropDown.new(
            Gtk.StringList.new([name for name, _entries in self.categories]), None
        )
        self.category_dropdown.connect("notify::selected", self.on_category_changed)
        root.append(self.category_dropdown)
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_position(245)
        paned.set_vexpand(True)
        self.structure_list = Gtk.ListBox()
        self.structure_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.structure_list.connect("row-selected", self.on_selection_changed)
        self.structure_list.connect("row-activated", self.on_row_activated)
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_child(self.structure_list)
        paned.set_start_child(scroller)
        self.preview_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.preview_box.set_hexpand(True)
        self.preview_box.set_vexpand(True)
        self.preview_box.append(self.preview.widget)
        paned.set_end_child(self.preview_box)
        root.append(paned)
        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.status_label = Gtk.Label(label="Select a structure to preview it.", xalign=0)
        self.status_label.set_hexpand(True)
        footer.append(self.status_label)
        use = Gtk.Button(label="Use Structure")
        use.connect("clicked", self.on_use_clicked)
        footer.append(use)
        close = Gtk.Button(label="Close")
        close.connect("clicked", self.on_close_button_clicked)
        footer.append(close)
        root.append(footer)
        self.window.set_child(root)
        self.visible = True
        self.window.present()
        if self.categories:
            self.category_dropdown.set_selected(0)
        else:
            self.status_label.set_text("No structure files were found.")

    def on_category_changed(self, dropdown, _pspec):
        self._clear_rows()
        index = dropdown.get_selected()
        if index >= len(self.categories):
            return
        for name, path in self.categories[index][1]:
            row = Gtk.ListBoxRow()
            row.set_child(Gtk.Label(label=name, xalign=0, margin_start=8))
            self._row_paths[row] = path
            self.structure_list.append(row)
        first = self.structure_list.get_row_at_index(0)
        if first is not None:
            self.structure_list.select_row(first)

    def _clear_rows(self):
        self._row_paths.clear()
        child = self.structure_list.get_first_child()
        while child is not None:
            following = child.get_next_sibling()
            self.structure_list.remove(child)
            child = following
        self.preview.clear()

    def on_selection_changed(self, _listbox, row):
        path = self._row_paths.get(row) if row is not None else None
        if path is None:
            self.preview.clear()
            return
        try:
            structure = load_structure(path)
        except StructureError as error:
            self.preview.clear()
            self.status_label.set_text(f"Error: {error}")
            return
        self.preview.show(structure["name"], structure["atoms"], structure["bonds"])
        self.status_label.set_text(f"Preview: {structure['name']}")

    def _use_row(self, row):
        path = self._row_paths.get(row) if row is not None else None
        if path is None:
            self.status_label.set_text("Select a structure first.")
            return
        try:
            structure = load_structure(path)
        except StructureError as error:
            self.status_label.set_text(f"Error: {error}")
            return
        self.vm_session.builder_selected_structure = structure
        self.vm_session.builder_tool = "add_structure"
        sidebar = getattr(self.main, "builder_sidebar_window", None)
        if sidebar is not None and sidebar.visible:
            sidebar.tool_add_structure_radio.set_active(True)
        self.status_label.set_text(
            f"Selected {structure['name']} ({len(structure['atoms'])} atoms); click in the Builder to place it."
        )

    def on_row_activated(self, _listbox, row):
        self._use_row(row)

    def on_use_clicked(self, _button):
        self._use_row(self.structure_list.get_selected_row())

    def on_close_button_clicked(self, *_args):
        if getattr(self, "window", None) is not None:
            self.window.destroy()
            self.window = None
        self.preview = None
        self.visible = False
        return True
