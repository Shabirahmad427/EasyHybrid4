"""Native GTK4 DYFF parameter inspector/editor for Builder molecules."""

import threading

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk

from gui.windows.builder import dyff_parameters as D


_TABS = (("atoms", "Atoms"), ("bond", "Bonds"), ("angle", "Angles"),
         ("dihedral", "Dihedrals"), ("outofplane", "Impropers"), ("lj", "Lennard-Jones"))


class DYFFParametersWindow:
    def __init__(self, main=None):
        self.main = main
        self.vm_session = main.vm_session
        self.visible = False
        self.target_object = None
        self.selected_atoms = []
        self.tables = None
        self.current = None
        self.torsion_fit_window = None

    def open_window(self, target_object, atom_ids=None):
        self.target_object = target_object
        self.selected_atoms = sorted(atom_ids or [])
        if not self.visible:
            self._build_window()
        else:
            self.window.present()
        self.refresh()

    def _build_window(self):
        self.window = Gtk.Window(title="DYFF Parameters", transient_for=self.main.window)
        self.window.set_default_size(1100, 700)
        self.window.connect("close-request", self.on_close_request)
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        for side in ("top", "bottom", "start", "end"):
            getattr(root, f"set_margin_{side}")(10)
        self.window.set_child(root)
        self.header = Gtk.Label(xalign=0)
        self.header.set_wrap(True)
        root.append(self.header)
        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        root.append(actions)
        for label, handler in (("Atom Types / Charges…", self.on_atom_types),
                               ("Compute CM5 Charges", self.on_compute_cm5),
                               ("Incorporate with DYFF", self.on_incorporate)):
            button = Gtk.Button(label=label)
            button.connect("clicked", handler)
            actions.append(button)
        self.notebook = Gtk.Notebook()
        self.notebook.set_vexpand(True)
        root.append(self.notebook)
        self.lists = {}
        for key, title in _TABS:
            listing = Gtk.ListBox()
            listing.set_selection_mode(Gtk.SelectionMode.SINGLE)
            listing.connect("row-selected", self.on_row_selected, key)
            scroll = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
            scroll.set_child(listing)
            self.notebook.append_page(scroll, Gtk.Label(label=title))
            self.lists[key] = listing
        editor = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        root.append(editor)
        self.edit_label = Gtk.Label(label="Select a parameter row to edit it.", xalign=0)
        self.edit_label.set_hexpand(True)
        editor.append(self.edit_label)
        self.parameter_entry = Gtk.Entry(hexpand=True)
        self.parameter_entry.set_placeholder_text("bond: length force constant; cosine: c n; c n; …")
        editor.append(self.parameter_entry)
        self.apply_button = Gtk.Button(label="Apply Edit")
        self.apply_button.connect("clicked", self.on_apply_edit)
        editor.append(self.apply_button)
        self.revert_button = Gtk.Button(label="Revert")
        self.revert_button.connect("clicked", self.on_revert_edit)
        editor.append(self.revert_button)
        self.fit_button = Gtk.Button(label="Fit Dihedral with xTB…")
        self.fit_button.connect("clicked", self.on_fit_torsion)
        editor.append(self.fit_button)
        self.fit_button.set_sensitive(False)
        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        root.append(footer)
        self.status = Gtk.Label(xalign=0)
        self.status.set_hexpand(True)
        footer.append(self.status)
        close = Gtk.Button(label="Close")
        close.connect("clicked", self.close_window)
        footer.append(close)
        self.visible = True
        self.window.present()

    def refresh(self):
        if self.target_object is None:
            return
        self.tables = D.build_tables(self.target_object)
        self.header.set_text(
            f"{self.target_object.name} — formal charge {self.tables.get('total_formal', 0):+d}; "
            f"partial charge {self.tables.get('total_partial', 0.0):+.3f}"
        )
        self.current = None
        for key, _title in _TABS:
            listing = self.lists[key]
            child = listing.get_first_child()
            while child is not None:
                nxt = child.get_next_sibling()
                listing.remove(child)
                child = nxt
            rows = self.tables.get(key, [])
            if key == "atoms" and self.selected_atoms:
                selected = set(self.selected_atoms)
                rows = [row for row in rows if row.get("atom_id") in selected]
            for data in rows:
                row = Gtk.ListBoxRow()
                row._dyff_data = data
                label = Gtk.Label(label=self._format_row(key, data), xalign=0)
                label.set_selectable(True)
                for side in ("start", "end", "top", "bottom"):
                    getattr(label, f"set_margin_{side}")(5)
                row.set_child(label)
                listing.append(row)
        self.status.set_text(self.tables.get("error") or "DYFF tables refreshed.")
        self._update_actions()

    @staticmethod
    def _format_row(term, row):
        if term == "atoms":
            charge = "—" if row["charge"] is None else f"{row['charge']:+.3f}"
            return (f"#{row['atom_id']} {row['symbol']} {row['name']} {row['residue']} | "
                    f"{row['type']} (perceived {row['perceived']}) | hybrid {row['hybridization']} | "
                    f"formal {row['formal']:+d} | partial {charge} | {row['quality']}")
        return f"{row.get('types', row.get('key'))} | {row.get('v0','')} {row.get('v1','')} | " \
               f"{row.get('count',0)} term(s) | {row.get('example','')} | {row.get('quality','')}"

    def on_row_selected(self, _listing, row, term):
        self.current = (term, row._dyff_data) if row is not None else None
        self._update_actions()

    def _update_actions(self):
        if self.current is None:
            self.edit_label.set_text("Select a parameter row to edit it.")
            self.fit_button.set_sensitive(False)
            return
        term, row = self.current
        self.edit_label.set_text(f"{term}: {row.get('types', row.get('key'))}")
        value = row.get("value")
        if term == "bond" and value is not None:
            self.parameter_entry.set_text(f"{value[0]} {value[1]}")
        elif value is not None:
            self.parameter_entry.set_text("; ".join(f"{fc} {period}" for fc, period in value))
        else:
            self.parameter_entry.set_text("")
        self.fit_button.set_sensitive(term == "dihedral" and bool(row.get("instances")))

    def on_apply_edit(self, _button):
        if self.current is None:
            return
        term, row = self.current
        if term in ("atoms", "lj"):
            self.status.set_text("This row is not a bonded parameter.")
            return
        try:
            text = self.parameter_entry.get_text()
            value = tuple(float(part) for part in text.replace(",", " ").split()) if term == "bond" else D.parse_pairs(text)
            if term == "bond" and len(value) != 2:
                raise ValueError("Enter equilibrium length and force constant.")
            D.set_parameter_edit(self.target_object, term, row["key"], value)
        except (ValueError, TypeError) as error:
            self.status.set_text(str(error))
            return
        self.refresh()

    def on_revert_edit(self, _button):
        if self.current is None:
            return
        term, row = self.current
        if term not in ("atoms", "lj"):
            D.set_parameter_edit(self.target_object, term, row["key"], None)
            self.refresh()

    def on_fit_torsion(self, _button):
        if self.current is None or self.current[0] != "dihedral":
            return
        _term, row = self.current
        from gui.windows.builder.torsion_fit_window import TorsionFitWindow
        if self.torsion_fit_window is None:
            self.torsion_fit_window = TorsionFitWindow(main=self.main, on_applied=self._fit_applied)
        try:
            target = D.DYFFTorsionTarget(self.target_object, row, row["instances"][0])
            self.torsion_fit_window.open_window(target)
        except Exception as error:
            self.status.set_text(str(error))

    def _fit_applied(self, message):
        self.status.set_text(message)
        self.refresh()

    def on_atom_types(self, _button):
        ids = self.selected_atoms or list(self.target_object.atoms)
        self.main.atom_types_window.open_window(self.target_object, ids)

    def on_compute_cm5(self, _button):
        self.status.set_text("Computing CM5 charges with xTB…")
        target = self.target_object
        def work():
            try:
                message = D.compute_cm5_charges(target)
            except Exception as error:
                message = str(error)
            GLib.idle_add(self._cm5_done, message)
        threading.Thread(target=work, daemon=True).start()

    def _cm5_done(self, message):
        if self.visible:
            self.status.set_text(str(message))
            self.refresh()
        return False

    def on_incorporate(self, _button):
        ok, message = D.incorporate_with_dyff(self.main, self.target_object)
        self.status.set_text(message)

    def on_close_request(self, *_args):
        self.close_window()
        return True

    def close_window(self, *_args):
        if self.torsion_fit_window is not None:
            self.torsion_fit_window.close_window()
        if self.visible:
            self.window.destroy()
            self.visible = False
