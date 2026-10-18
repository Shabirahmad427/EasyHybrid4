"""Native GTK4 DYFF type and protonation inspector for the Builder."""

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gio, Gtk
from gui.response_dialog import ResponseDialog

from gui.model_rows import AtomTypeRow
from gui.windows.builder.atom_types import (
    compute_atom_types,
    set_manual_atom_type_override,
    valid_type_labels_for_symbol,
)


class AtomTypesWindow:
    """Inspect atom typing and edit Builder atom properties."""

    def __init__(self, main=None):
        self.main = main
        self.vm_session = main.vm_session
        self.visible = False
        self.target_object = None
        self.atoms = []

    def open_window(self, target_object, atom_ids):
        self.target_object = target_object
        self.atoms = [target_object.atoms[i] for i in sorted(atom_ids)
                      if i in target_object.atoms]
        if not self.visible:
            self._build_window()
        else:
            self.window.present()
        self._refresh_rows()

    def _build_window(self):
        self.window = Gtk.Window(title="Atom Types", transient_for=self.main.window)
        self.window.set_default_size(760, 440)
        self.window.connect("close-request", self.on_close_request)
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        for side in ("top", "bottom", "start", "end"):
            getattr(root, f"set_margin_{side}")(8)
        self.window.set_child(root)

        self.header_label = Gtk.Label(xalign=0)
        self.header_label.set_wrap(True)
        root.append(self.header_label)

        self.liststore = Gio.ListStore.new(AtomTypeRow)
        self.selection = Gtk.MultiSelection.new(self.liststore)
        self.selection.connect("selection-changed", self.on_selection_changed)
        self.column_view = Gtk.ColumnView.new(self.selection)
        self.column_view.set_show_row_separators(True)
        self.column_view.set_show_column_separators(True)
        columns = (
            ("#", "atom_id", False), ("Element", "symbol", False),
            ("Name", "name", False), ("DYFF Type", "type_label", True),
            ("Source", "source", False), ("Charge", "formal_charge", True),
            ("Hybridization", "hybridization", False),
        )
        for title, attribute, editable in columns:
            factory = Gtk.SignalListItemFactory()
            factory.connect("setup", self._setup_cell, attribute, editable)
            factory.connect("bind", self._bind_cell, attribute, editable)
            column = Gtk.ColumnViewColumn.new(title, factory)
            column.set_resizable(True)
            column.set_expand(attribute in ("type_label", "name"))
            self.column_view.append_column(column)
        scroller = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        scroller.set_child(self.column_view)
        root.append(scroller)

        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        root.append(actions)
        for label, callback in (
            ("Refresh", self.on_refresh),
            ("Clear Override(s)", self.on_clear_overrides),
            ("Protonate", self.on_protonate),
            ("Deprotonate", self.on_deprotonate),
            ("Rename Residue…", self.on_rename_residue),
        ):
            button = Gtk.Button(label=label)
            button.connect("clicked", callback)
            actions.append(button)
        close = Gtk.Button(label="Close")
        close.connect("clicked", self.close_window)
        actions.append(close)

        self.status_label = Gtk.Label(xalign=0)
        self.status_label.set_wrap(True)
        root.append(self.status_label)
        self.visible = True
        self.window.present()

    def _setup_cell(self, factory, list_item, attribute, editable):
        if editable:
            child = Gtk.Entry()
            child.set_has_frame(False)
            child.set_hexpand(True)
            child.connect("activate", self._on_cell_activate, list_item, attribute)
        else:
            child = Gtk.Label(xalign=0)
        list_item.set_child(child)

    def _bind_cell(self, factory, list_item, attribute, editable):
        row = list_item.get_item()
        child = list_item.get_child()
        value = getattr(row, attribute)
        if editable:
            child.set_text(str(value))
            child.set_tooltip_text(row.tooltip if attribute == "type_label" else None)
        else:
            child.set_text(str(value))
            child.set_tooltip_text(row.tooltip or None)

    def _on_cell_activate(self, entry, list_item, attribute):
        row = list_item.get_item()
        if attribute == "type_label":
            self._edit_type(row, entry.get_text())
        elif attribute == "formal_charge":
            self._edit_charge(row, entry.get_text())

    def _refresh_rows(self):
        if self.target_object is None:
            return
        self.atoms = [atom for atom in self.atoms
                      if self.target_object.atoms.get(atom.atom_id) is atom]
        atom_ids = [atom.atom_id for atom in self.atoms]
        self.header_label.set_text(
            f"{self.target_object.name} — {len(atom_ids)} atom(s) selected"
        )
        types = compute_atom_types(self.target_object, atom_ids=atom_ids)
        hybridizations = self._hybridizations()
        overrides = getattr(self.target_object, "manual_atom_type_overrides", None) or {}
        self.liststore.remove_all()
        for atom_id in atom_ids:
            atom = self.target_object.atoms.get(atom_id)
            if atom is None:
                continue
            perceived, effective = types.get(atom_id, (None, None))
            labels = valid_type_labels_for_symbol(self.vm_session, atom.symbol)
            tip = (f"Valid {atom.symbol} types: {', '.join(labels)}" if labels
                   else f"No DYFF type is defined for element {atom.symbol}.")
            self.liststore.append(AtomTypeRow(
                atom_id, atom.symbol, atom.name,
                effective if effective is not None else "?",
                "manual" if atom_id in overrides else "auto", tip,
                int(getattr(atom, "formal_charge", 0)),
                hybridizations.get(atom_id, ""),
            ))
        self.vm_session.builder_atom_types_labeled_atoms = list(self.atoms)
        core = getattr(self.vm_session, "vm_glcore", None)
        if core is not None:
            core.queue_draw()

    def _hybridizations(self):
        try:
            from gui.windows.builder.residue_chemistry import (
                atom_hybridizations, perceive_aromatic_bonds,
            )
            obj = self.target_object
            manual = getattr(obj, "manual_bond_orders", None) or {}
            orders = {pair: int(manual.get(pair, 1))
                      for pair in (getattr(obj, "manual_bonds", None) or set())
                      if pair[0] in obj.atoms and pair[1] in obj.atoms}
            charges = {aid: int(getattr(atom, "formal_charge", 0))
                       for aid, atom in obj.atoms.items()}
            aromatic = perceive_aromatic_bonds(obj.atoms, orders, charges)
            return atom_hybridizations(obj.atoms, orders, aromatic)
        except Exception as error:
            print(f"Atom Types: hybridization unavailable ({error})")
            return {}

    def _edit_type(self, row, text):
        text = text.strip()
        atom = self.target_object.atoms.get(row.atom_id)
        if atom is None:
            return
        if text:
            valid = valid_type_labels_for_symbol(self.vm_session, atom.symbol)
            if valid and text not in valid:
                self.status_label.set_text(
                    f'"{text}" is not a valid DYFF type for {atom.symbol}: {", ".join(valid)}.'
                )
                return
        set_manual_atom_type_override(self.target_object, row.atom_id, text or None)
        self.status_label.set_text(
            f"Atom #{row.atom_id}: " +
            (f'type manually set to "{text}".' if text else "override cleared.")
        )
        self._refresh_rows()

    def _edit_charge(self, row, text):
        try:
            charge = int(text.strip())
        except ValueError:
            self.status_label.set_text(f'"{text}" is not a valid integer charge.')
            return
        atom = self.target_object.atoms.get(row.atom_id)
        if atom is None:
            return
        from gui.windows.builder.atom_ops import push_undo_snapshot
        push_undo_snapshot(self.target_object)
        atom.formal_charge = charge
        from gui.windows.builder.empty_object import sync_pdynamo_system
        sync_pdynamo_system(self.target_object)
        dyff_window = getattr(self.main, "dyff_parameters_window", None)
        if dyff_window is not None and dyff_window.visible and dyff_window.target_object is self.target_object:
            dyff_window.refresh()
        self.status_label.set_text(f"Atom #{row.atom_id}: formal charge set to {charge:+d}.")
        self._refresh_rows()

    def _selected_rows(self):
        return [self.liststore.get_item(i) for i in range(self.liststore.get_n_items())
                if self.selection.is_selected(i)]

    def on_selection_changed(self, selection, position, n_items):
        rows = self._selected_rows()
        if rows and self.target_object is not None:
            atom = self.target_object.atoms.get(rows[-1].atom_id)
            core = getattr(self.vm_session, "vm_glcore", None)
            if atom is not None and core is not None:
                core.center_on_atom(atom)

    def on_refresh(self, button):
        self._refresh_rows()
        self.status_label.set_text("Refreshed.")

    def on_clear_overrides(self, button):
        rows = self._selected_rows()
        for row in rows:
            set_manual_atom_type_override(self.target_object, row.atom_id, None)
        self.status_label.set_text(
            f"Cleared {len(rows)} override(s)." if rows else "Select one or more rows first."
        )
        if rows:
            self._refresh_rows()

    def _selected_atoms(self):
        rows = self._selected_rows()
        if not rows:
            return []
        return [self.target_object.atoms[row.atom_id]
                for row in rows if row.atom_id in self.target_object.atoms]

    def on_protonate(self, button):
        self._change_protonation("protonate_atom")

    def on_deprotonate(self, button):
        self._change_protonation("deprotonate_atom")

    def _change_protonation(self, operation):
        atoms = self._selected_atoms()
        if not atoms:
            self.status_label.set_text("Select one or more rows first.")
            return
        from gui.windows.builder import atom_ops
        messages = [getattr(atom_ops, operation)(self.target_object, atom.atom_id)[1]
                    for atom in atoms]
        self.status_label.set_text("  |  ".join(messages))
        self._refresh_rows()

    def _residues_of_selection(self):
        atoms = self._selected_atoms()
        if not atoms:
            atoms = [atom for atom in self.atoms
                     if self.target_object.atoms.get(atom.atom_id) is atom]
        result = []
        for atom in atoms:
            residue = getattr(atom, "residue", None)
            if residue is not None and residue not in result:
                result.append(residue)
        return result

    def on_rename_residue(self, button):
        residues = self._residues_of_selection()
        if not residues:
            self.status_label.set_text("No residue found for the listed atoms.")
            return
        dialog = ResponseDialog(title="Rename Residue", transient_for=self.window, modal=True)
        dialog.add_buttons("Cancel", Gtk.ResponseType.CANCEL,
                           "Rename", Gtk.ResponseType.OK)
        dialog.set_default_response(Gtk.ResponseType.OK)
        grid = Gtk.Grid(column_spacing=8, row_spacing=6)
        for side in ("top", "bottom", "start", "end"):
            getattr(grid, f"set_margin_{side}")(10)
        names = ", ".join(f"{r.chain.name}:{r.name} {r.index}" for r in residues[:6])
        if len(residues) > 6:
            names += f", ... ({len(residues)} residues)"
        grid.attach(Gtk.Label(label="Residue(s):", xalign=0), 0, 0, 1, 1)
        grid.attach(Gtk.Label(label=names, xalign=0), 1, 0, 1, 1)
        grid.attach(Gtk.Label(label="New name:", xalign=0), 0, 1, 1, 1)
        name_entry = Gtk.Entry(text=residues[0].name, max_length=4,
                               activates_default=True)
        grid.attach(name_entry, 1, 1, 1, 1)
        grid.attach(Gtk.Label(label="Number:", xalign=0), 0, 2, 1, 1)
        number = Gtk.SpinButton.new_with_range(-9999, 99999, 1)
        number.set_value(int(residues[0].index))
        number.set_sensitive(len(residues) == 1)
        grid.attach(number, 1, 2, 1, 1)
        dialog.get_content_area().append(grid)

        def response(current, answer):
            new_name = name_entry.get_text()
            new_number = int(number.get_value()) if len(residues) == 1 else None
            current.destroy()
            if answer == Gtk.ResponseType.OK:
                ok, message = self.apply_residue_rename(
                    residues, new_name=new_name, new_index=new_number
                )
                self.status_label.set_text(message)
                if ok:
                    self._refresh_rows()
        dialog.connect("response", response)
        dialog.present()

    def apply_residue_rename(self, residues, new_name=None, new_index=None):
        from gui.windows.builder.atom_ops import push_undo_snapshot, rename_residue
        from gui.windows.builder.empty_object import sync_pdynamo_system
        if not residues:
            return False, "No residue to rename."
        if new_index is not None and len(residues) != 1:
            return False, "A residue number can only be set for one residue at a time."
        push_undo_snapshot(self.target_object)
        renamed = 0
        try:
            for residue in residues:
                rename_residue(self.target_object, residue,
                               new_name=new_name, new_index=new_index)
                renamed += 1
        except ValueError as error:
            if renamed == 0:
                self.target_object.undo_stack.pop()
            else:
                from gui.windows.builder.atom_ops import undo
                undo(self.target_object)
                self.target_object.redo_stack = []
            return False, str(error)
        sync_pdynamo_system(self.target_object)
        labels = ", ".join(f"{r.chain.name}:{r.name}{r.index}" for r in residues)
        return True, f"Renamed: {labels}"

    def close_window(self, *args):
        self.vm_session.builder_atom_types_labeled_atoms = []
        core = getattr(self.vm_session, "vm_glcore", None)
        if core is not None:
            core.queue_draw()
        if getattr(self, "window", None) is not None:
            self.window.destroy()
        self.visible = False
        return True

    def on_close_request(self, *args):
        return self.close_window()
