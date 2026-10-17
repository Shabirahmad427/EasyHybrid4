#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GTK4 tools shared by VisMol and EasyHybrid."""

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, GObject, Gtk
from src.gtk4_compat import GTK_INVALID_LIST_POSITION

from gui.widgets.custom_widgets.selection_box import VismolSelectionTypeBox
from gui.widgets.custom_widgets.trajectory_frame import VismolTrajectoryFrame


class VismolStatusBar(Gtk.Box):
    """Small GTK4 status area retained for VisMol callers."""

    def __init__(self, vismol_session=None):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)
        self.vm_session = vismol_session
        self.statusbar = Gtk.Label(xalign=0)
        self.append(self.statusbar)

    def push(self, _context_id, message):
        self.statusbar.set_text(str(message))


class _ResidueRow(GObject.Object):
    include = GObject.Property(type=bool, default=True)
    index = GObject.Property(type=int, default=0)
    name = GObject.Property(type=str, default="")
    chain = GObject.Property(type=str, default="")
    size = GObject.Property(type=int, default=0)

    def __init__(self, residue):
        super().__init__()
        self.residue = residue
        self.index = int(residue.resi)
        self.name = str(residue.resn)
        self.chain = str(residue.chain.name if hasattr(residue, "chain") else "")
        self.size = len(residue.atoms)


class _AtomRow(GObject.Object):
    include = GObject.Property(type=bool, default=True)
    index = GObject.Property(type=int, default=0)
    name = GObject.Property(type=str, default="")
    element = GObject.Property(type=str, default="")
    mass = GObject.Property(type=float, default=0.0)
    atom_id = GObject.Property(type=int, default=-1)

    def __init__(self, atom):
        super().__init__()
        self.atom = atom
        self.index = int(atom.index)
        self.name = str(atom.name)
        self.element = str(atom.symbol)
        self.mass = float(getattr(atom, "mass", 0.0) or 0.0)
        self.atom_id = int(atom.atom_id)


class VismolGoToAtomWindow2(Gtk.Window):
    """GTK4 object, residue, and atom browser for the VisMol viewer."""

    def __init__(self, vismol_session=None):
        super().__init__(title="Go to Atom")
        self.vm_session = vismol_session
        self.Visible = False
        self.VObj = None
        self.current_filter_chain = "all"
        self.current_filter_residue = "all"

        self.residue_store = Gio.ListStore.new(_ResidueRow)
        self.atom_store = Gio.ListStore.new(_AtomRow)
        self.chain_filter = Gtk.CustomFilter.new(self._filter_chain)
        self.residue_filter = Gtk.CustomFilter.new(self._filter_residue)
        self.chain_filtered_rows = Gtk.FilterListModel.new(
            self.residue_store, self.chain_filter
        )
        self.filtered_residues = Gtk.FilterListModel.new(
            self.chain_filtered_rows, self.residue_filter
        )
        self._built = False
        self.connect("close-request", self._on_close_request)

    def OpenWindow(self):
        if not self._built:
            self._build_window()
        if not self.Visible:
            self.present()
            self.Visible = True

    def _build_window(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        root.set_margin_top(10)
        root.set_margin_bottom(10)
        root.set_margin_start(10)
        root.set_margin_end(10)

        objects_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        objects_row.append(Gtk.Label(label="Object:", xalign=0))
        self.object_dropdown = Gtk.DropDown()
        self.object_dropdown.set_hexpand(True)
        self.object_dropdown.connect("notify::selected", self.on_object_selected)
        objects_row.append(self.object_dropdown)
        root.append(objects_row)

        filters_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        filters_row.append(Gtk.Label(label="Chain:", xalign=0))
        self.chain_dropdown = Gtk.DropDown()
        self.chain_dropdown.connect("notify::selected", self.on_chain_selected)
        filters_row.append(self.chain_dropdown)
        filters_row.append(Gtk.Label(label="Residue type:", xalign=0))
        self.residue_dropdown = Gtk.DropDown()
        self.residue_dropdown.connect("notify::selected", self.on_residue_type_selected)
        filters_row.append(self.residue_dropdown)
        root.append(filters_row)

        views = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.residue_selection = Gtk.SingleSelection.new(self.filtered_residues)
        self.residue_selection.set_autoselect(False)
        self.residue_selection.set_can_unselect(True)
        self.residue_view = Gtk.ColumnView.new(self.residue_selection)
        self._append_columns(
            self.residue_view,
            (("", "include", "check"), ("Index", "index", "text"),
             ("Residue", "name", "text"), ("Chain", "chain", "text"),
             ("Atoms", "size", "text")),
        )
        self.residue_view.connect("activate", self.on_residue_activated)
        self.residue_selection.connect(
            "notify::selected-item", self.on_residue_selection_changed
        )
        self._add_middle_click(self.residue_view, self.on_residue_middle_click)
        residue_scroll = Gtk.ScrolledWindow()
        residue_scroll.set_hexpand(True)
        residue_scroll.set_vexpand(True)
        residue_scroll.set_child(self.residue_view)
        views.append(residue_scroll)

        self.atom_selection = Gtk.SingleSelection.new(self.atom_store)
        self.atom_selection.set_autoselect(False)
        self.atom_selection.set_can_unselect(True)
        self.atom_view = Gtk.ColumnView.new(self.atom_selection)
        self._append_columns(
            self.atom_view,
            (("", "include", "check"), ("Index", "index", "text"),
             ("Name", "name", "text"), ("Element", "element", "text"),
             ("Mass", "mass", "text")),
        )
        self.atom_view.connect("activate", self.on_atom_activated)
        self._add_middle_click(self.atom_view, self.on_atom_middle_click)
        atom_scroll = Gtk.ScrolledWindow()
        atom_scroll.set_hexpand(True)
        atom_scroll.set_vexpand(True)
        atom_scroll.set_child(self.atom_view)
        views.append(atom_scroll)

        root.append(views)
        self.set_default_size(700, 600)
        self.set_child(root)
        self._refresh_object_choices()
        self._built = True

    @staticmethod
    def _append_columns(view, columns):
        for title, attribute, kind in columns:
            factory = Gtk.SignalListItemFactory()
            if kind == "check":
                factory.connect("setup", VismolGoToAtomWindow2._setup_check)
                factory.connect("bind", VismolGoToAtomWindow2._bind_check, attribute)
            else:
                factory.connect("setup", VismolGoToAtomWindow2._setup_label)
                factory.connect("bind", VismolGoToAtomWindow2._bind_label, attribute)
            view.append_column(Gtk.ColumnViewColumn.new(title, factory))

    @staticmethod
    def _setup_label(_factory, list_item):
        label = Gtk.Label(xalign=0)
        label.set_margin_start(5)
        label.set_margin_end(5)
        list_item.set_child(label)

    @staticmethod
    def _bind_label(_factory, list_item, attribute):
        value = getattr(list_item.get_item(), attribute)
        list_item.get_child().set_text(str(value))

    @staticmethod
    def _setup_check(_factory, list_item):
        check = Gtk.CheckButton()
        check.connect("toggled", VismolGoToAtomWindow2._on_check_toggled, list_item)
        list_item.set_child(check)

    @staticmethod
    def _bind_check(_factory, list_item, attribute):
        check = list_item.get_child()
        check._binding = True
        check._attribute = attribute
        check.set_active(getattr(list_item.get_item(), attribute))
        check._binding = False

    @staticmethod
    def _on_check_toggled(check, list_item):
        if not getattr(check, "_binding", False):
            setattr(list_item.get_item(), check._attribute, check.get_active())

    @staticmethod
    def _add_middle_click(widget, callback):
        click = Gtk.GestureClick()
        click.set_button(2)
        click.connect("released", callback)
        widget.add_controller(click)

    def _refresh_object_choices(self):
        objects = self.vm_session.vm_objects_dic if self.vm_session else {}
        self._object_ids = list(objects)
        names = [str(getattr(objects[key], "name", key)) for key in self._object_ids]
        self.object_dropdown.set_model(Gtk.StringList.new(names))
        self.object_dropdown.set_selected(
            0 if names else GTK_INVALID_LIST_POSITION
        )

    def on_object_selected(self, dropdown, _pspec=None):
        position = dropdown.get_selected()
        if position == GTK_INVALID_LIST_POSITION or position >= len(self._object_ids):
            self.VObj = None
            self.residue_store.remove_all()
            self.atom_store.remove_all()
            return

        self.VObj = self.vm_session.vm_objects_dic[self._object_ids[position]]
        self._populate_residues()
        self._populate_filter_choices()

    def _populate_residues(self):
        self.residue_store.remove_all()
        for chain_name, chain in self.VObj.chains.items():
            for residue in chain.residues:
                row = _ResidueRow(residue)
                row.chain = str(chain_name)
                self.residue_store.append(row)
        self._clear_atom_rows()
        self._refresh_filters()

    def _populate_filter_choices(self):
        chain_names = ["all", *(str(name) for name in self.VObj.chains)]
        residue_names = ["all", *sorted({str(residue.resn) for residue in self.VObj.residues})]
        self.current_filter_chain = "all"
        self.current_filter_residue = "all"
        self.chain_dropdown.set_model(Gtk.StringList.new(chain_names))
        self.residue_dropdown.set_model(Gtk.StringList.new(residue_names))
        self.chain_dropdown.set_selected(0 if chain_names else GTK_INVALID_LIST_POSITION)
        self.residue_dropdown.set_selected(0 if residue_names else GTK_INVALID_LIST_POSITION)

    def on_chain_selected(self, dropdown, _pspec=None):
        value = dropdown.get_selected_item()
        self.current_filter_chain = value.get_string() if value else "all"
        self._refresh_filters()

    def on_residue_type_selected(self, dropdown, _pspec=None):
        value = dropdown.get_selected_item()
        self.current_filter_residue = value.get_string() if value else "all"
        self._refresh_filters()

    def _refresh_filters(self):
        self.chain_filter.changed(Gtk.FilterChange.DIFFERENT)
        self.residue_filter.changed(Gtk.FilterChange.DIFFERENT)

    def _filter_chain(self, row, _data=None):
        return self.current_filter_chain in (None, "all", row.chain)

    def _filter_residue(self, row, _data=None):
        return self.current_filter_residue in (None, "all", row.name)

    def on_residue_selection_changed(self, _selection, _pspec=None):
        row = self.residue_selection.get_selected_item()
        self._populate_atoms(row.residue if row is not None else None)

    def _populate_atoms(self, residue):
        self.atom_store.remove_all()
        if residue is None:
            return
        for atom in residue.atoms:
            self.atom_store.append(_AtomRow(atom))

    def _clear_atom_rows(self):
        self.atom_store.remove_all()

    def on_residue_activated(self, _view, position):
        row = self.residue_selection.get_item(position)
        if row is None or self.VObj is None:
            return
        residue = row.residue
        frame = self.vm_session.get_frame()
        residue.get_center_of_mass(frame=frame)
        self.vm_session.glwidget.vm_widget.center_on_coordinates(
            residue.Vobject, residue.mass_center
        )
        self.vm_session._selection_function(residue.atoms[0], _type="residue")
        self.vm_session.glwidget.queue_draw()

    def on_atom_activated(self, _view, position):
        row = self.atom_selection.get_item(position)
        if row is None:
            return
        atom = self.vm_session.atom_dic_id[row.atom_id]
        self.vm_session._selection_function(atom, _type="atom")
        self.vm_session.glwidget.queue_draw()

    def on_residue_middle_click(self, _gesture, _presses, _x, _y):
        row = self.residue_selection.get_selected_item()
        if row is None:
            return
        residue = row.residue
        residue.get_center_of_mass(frame=self.vm_session.get_frame())
        self.vm_session.glwidget.vm_widget.center_on_coordinates(
            residue.Vobject, residue.mass_center
        )

    def on_atom_middle_click(self, _gesture, _presses, _x, _y):
        row = self.atom_selection.get_selected_item()
        if row is None:
            return
        atom = self.vm_session.atom_dic_id[row.atom_id]
        self.vm_session.glwidget.vm_widget.center_on_atom(atom)

    def _on_close_request(self, _window):
        self.Visible = False
        self.set_visible(False)
        return True

    def CloseWindow(self, *_args):
        return self._on_close_request(self)


__all__ = [
    "VismolStatusBar",
    "VismolGoToAtomWindow2",
    "VismolSelectionTypeBox",
    "VismolTrajectoryFrame",
]
