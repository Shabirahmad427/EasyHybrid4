"""Native GTK4 OPLS parameter inspection, editing, and torsion fitting."""

import traceback

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gio, GLib, Gtk

from gui.model_rows import OPLSParameterRow
from gui.widgets.custom_widgets import SystemComboBox


_TAB_SPECS = [
    ("charges", "Charges", [("Atom", "index", False), ("Residue", "residue", False),
     ("Name", "name", False), ("Type", "types", False), ("Charge", "v0", True),
     ("OPLS-AA class range", "range", False), ("Source", "source", False)]),
    ("bond", "Bonds", [("Types", "types", False), ("b0 (A)", "v0", True),
     ("k (kcal/mol/A2)", "v1", True), ("Terms", "count", False),
     ("Example", "example", False), ("Source", "source", False)]),
    ("angle", "Angles", [("Types", "types", False), ("theta0 (deg)", "v0", True),
     ("k (kcal/mol/rad2)", "v1", True), ("Terms", "count", False),
     ("Example", "example", False), ("Source", "source", False)]),
    ("dihedral", "Dihedrals", [("Types", "types", False), ("k n phase; ...", "terms", True),
     ("Terms", "count", False), ("Example", "example", False), ("Source", "source", False)]),
    ("outofplane", "Impropers", [("Types (central first)", "types", False), ("K (kcal/mol)", "v0", True),
     ("Terms", "count", False), ("Example", "example", False), ("Source", "source", False)]),
    ("lj", "Lennard-Jones", [("Type", "types", False), ("epsilon (kcal/mol)", "v0", True),
     ("sigma (A)", "v1", True), ("Atoms", "count", False), ("Source", "source", False)]),
]
_FILTERS = [("ligand", "Ligand parameters"), ("attention", "Needs attention (yellow/red)"),
            ("all", "All parameters")]
_LEVEL_COLORS = {"green": "#4caf50", "yellow": "#f2c94c", "red": "#e5534b",
                 "blue": "#4a90d9", "gray": "#9e9e9e"}


class OPLSParametersWindow:
    """Review parameter quality and edit values on an OPLS system."""

    def __init__(self, main=None):
        self.main = main
        self.vm_session = main.vm_session
        self.p_session = main.p_session
        self.visible = False
        self.pending = {}
        self.current = None
        self.torsion_fit_window = None

    def open_window(self, e_id=None):
        was_visible = self.visible
        if not was_visible:
            self._build_window()
        else:
            self.window.present()
        if e_id is not None:
            self.combobox_systems.set_active_system(e_id=e_id)
        elif not was_visible:
            self.combobox_systems.set_active_system(e_id=self.p_session.active_id)
        self.on_system_changed()

    def _build_window(self):
        self.window = Gtk.Window(title="OPLS Parameters", transient_for=self.main.window)
        self.window.set_default_size(1080, 680)
        self.window.connect("close-request", self.on_close_request)
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        for side in ("top", "bottom", "start", "end"):
            getattr(root, f"set_margin_{side}")(10)
        self.window.set_child(root)

        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        root.append(top)
        top.append(Gtk.Label(label="System:", xalign=0))
        self.combobox_systems = SystemComboBox(self.main)
        self.combobox_systems.set_hexpand(True)
        top.append(self.combobox_systems)
        top.append(Gtk.Label(label="Show:", xalign=0))
        self.combo_filter = Gtk.ComboBoxText()
        for key, label in _FILTERS:
            self.combo_filter.append(key, label)
        self.combo_filter.connect("changed", self.on_combo_filter_changed)
        top.append(self.combo_filter)
        self.label_legend = Gtk.Label(xalign=1)
        top.append(self.label_legend)
        from pdynamo.opls.editor import LEVEL_TEXT
        self.label_legend.set_markup("  ".join(
            f'<span background="{_LEVEL_COLORS[level]}">  </span> {LEVEL_TEXT[level]}'
            for level in ("green", "yellow", "red", "blue")))

        self.notebook = Gtk.Notebook(scrollable=True, vexpand=True)
        root.append(self.notebook)
        self.stores, self.filters, self.columns, self.lists, self.tab_labels = {}, {}, {}, {}, {}
        for term, title, columns in _TAB_SPECS:
            model = Gio.ListStore.new(OPLSParameterRow)
            listing = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
            listing.set_filter_func(self._row_visible)
            listing.connect("row-selected", self.on_row_selected, term)
            listing.connect("row-activated", self.on_row_activated)
            scroll = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
            scroll.set_child(listing)
            label = Gtk.Label(label=title)
            self.notebook.append_page(scroll, label)
            self.stores[term], self.filters[term] = model, listing
            self.columns[term], self.lists[term] = columns, listing
            self.tab_labels[term] = (label, title)

        project = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        root.append(project)
        self.checkbox_project = Gtk.CheckButton(label="Show the selected parameter in the structure (picking pk1-pk4)")
        self.checkbox_project.set_active(True)
        project.append(self.checkbox_project)
        self.checkbox_center = Gtk.CheckButton(label="Center")
        self.checkbox_center.set_active(True)
        project.append(self.checkbox_center)
        prev = Gtk.Button(label="◀")
        prev.set_tooltip_text("Previous term with these atom types")
        prev.connect("clicked", lambda *_: self._step_instance(-1))
        project.append(prev)
        nxt = Gtk.Button(label="▶")
        nxt.set_tooltip_text("Next term with these atom types")
        nxt.connect("clicked", lambda *_: self._step_instance(1))
        project.append(nxt)
        self.label_instance = Gtk.Label(xalign=0, hexpand=True, selectable=True)
        project.append(self.label_instance)
        self.button_fit_torsion = Gtk.Button(label="Fit with xTB scan…")
        self.button_fit_torsion.set_sensitive(False)
        self.button_fit_torsion.connect("clicked", self.on_button_fit_torsion_clicked)
        project.append(self.button_fit_torsion)

        help_label = Gtk.Label(label=("Double-click a value to edit it (dihedral terms as 'k n phase; k n phase'). "
            "Charges must keep an integral total; bonded and Lennard-Jones changes rebuild the MM model "
            "and cannot be applied while a QC model is active."), xalign=0, wrap=True)
        root.append(help_label)
        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        root.append(footer)
        self.label_charge = Gtk.Label(xalign=0, use_markup=True)
        footer.append(self.label_charge)
        self.label_status = Gtk.Label(xalign=0, hexpand=True)
        footer.append(self.label_status)
        for label, handler in (("Revert", self.on_button_revert_clicked),
                               ("Apply changes", self.on_button_apply_clicked),
                               ("Close", self.close_window)):
            button = Gtk.Button(label=label)
            button.connect("clicked", handler)
            footer.append(button)
            if label == "Apply changes":
                self.button_apply = button
        self.combobox_systems.connect("notify::selected", self.on_system_changed)
        self.visible = True
        self.window.present()

    @staticmethod
    def _fmt(value, digits=4):
        return "" if value is None else f"{float(value):.{digits}f}"

    def _render_row(self, term, row_id, data):
        from pdynamo.opls.editor import LEVEL_TEXT
        pending_key = data.get("index") if term == "charges" else data.get("key")
        is_pending = pending_key in self.pending.get(term, {})
        display_data = dict(data)
        if is_pending:
            display_data["value"] = self.pending[term][pending_key]
        cells = []
        for _name, field, _editable in self.columns[term]:
            value = display_data.get(field, "")
            if field == "types":
                value = data["type"] if term == "charges" else " - ".join(data["key"])
            elif field == "index":
                value = str(data["index"] + 1)
            elif field == "v0":
                parameter = data.get("value")
                if term == "charges": value = self._fmt(parameter)
                elif term == "outofplane": value = self._fmt(parameter, 3)
                else: value = self._fmt(parameter[0] if parameter else None)
            elif field == "v1":
                parameter = data.get("value")
                value = self._fmt(parameter[1] if parameter else None, 3)
            elif field == "terms":
                value = "; ".join(f"{k:.4f} {int(n)} {phase:.1f}" for k, n, phase in (data.get("value") or []) if k != 0) or "none"
            cells.append(str(value))
        quality = "edited (not applied)" if is_pending else data.get("quality", "")
        level = "blue" if is_pending else data.get("level", "gray")
        row = OPLSParameterRow(row_id, cells, level, quality)
        widget = Gtk.ListBoxRow()
        widget._opls_term = term
        widget._opls_row_id = row_id
        widget._opls_data = data
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_margin_start(5); box.set_margin_end(5); box.set_margin_top(3); box.set_margin_bottom(3)
        for cell, (heading, _field, editable) in zip(cells, self.columns[term]):
            text = Gtk.Label(label=cell, xalign=0, hexpand=True, selectable=True)
            text.set_width_chars(max(8, min(25, len(heading) + 2)))
            if editable:
                text.add_css_class("editable")
                text.set_tooltip_text("Double-click this row to edit this value")
            box.append(text)
        badge = Gtk.Label()
        badge.set_markup(f'<span foreground="{_LEVEL_COLORS[row.level]}">{GLib.markup_escape_text(quality)}  '
                         f'[{LEVEL_TEXT[row.level]}]</span>')
        badge.set_width_chars(24)
        badge.set_xalign(0)
        badge.add_css_class(f"opls-{row.level}")
        box.append(badge)
        widget.set_child(box)
        return widget

    def _row_visible(self, row):
        if row is None: return True
        mode = self.combo_filter.get_active_id() or "all"
        data = row._opls_data
        return mode == "all" or (mode == "ligand" and bool(data.get("ligand"))) or (
            mode == "attention" and data.get("level") in ("yellow", "red"))

    def on_combo_filter_changed(self, *_args):
        for listing in self.lists.values(): listing.invalidate_filter()
        self._update_tab_titles()

    def _update_tab_titles(self):
        for term, (label, title) in self.tab_labels.items():
            rows = self.tables.get(term, []) if self.tables else []
            shown = sum(1 for row in rows if (self.combo_filter.get_active_id() == "all"
                or self.combo_filter.get_active_id() is None
                or self.combo_filter.get_active_id() == "ligand" and row.get("ligand")
                or self.combo_filter.get_active_id() == "attention" and row.get("level") in ("yellow", "red")))
            red = sum(1 for row in rows if row.get("level") == "red")
            yellow = sum(1 for row in rows if row.get("level") == "yellow")
            label.set_markup(f"{title} ({shown})" + (f' <span foreground="#e5534b">●{red}</span>' if red else "")
                              + (f' <span foreground="#c9a227">●{yellow}</span>' if yellow else ""))

    def on_system_changed(self, *_args):
        from pdynamo.opls import editor
        self.pending, self.current, self.tables = {}, None, None
        eid = self.combobox_systems.get_system_id()
        self.system = self.p_session.psystem.get(eid) if eid is not None else None
        if self.system is not None:
            try:
                self.tables = editor.build_tables(self.system)
                editable = editor.editable_parameter_folder(self.system) is not None
                self.button_apply.set_sensitive(editable)
                self.label_status.set_tooltip_text(
                    None if editable else "Built-in pDynamo parameter sets are read-only. Prepare a per-system OPLS set to edit."
                )
                has_ligand = any(row["ligand"] for row in self.tables["charges"])
                if self.combo_filter.get_active_id() is None:
                    self.combo_filter.set_active_id("ligand" if has_ligand else "attention")
            except Exception as error:
                self.label_status.set_text(str(error))
                self.button_apply.set_sensitive(False)
        self._fill()

    def _fill(self):
        self.button_fit_torsion.set_sensitive(False)
        self.label_instance.set_text("")
        for term, _title, _columns in _TAB_SPECS:
            listing = self.lists[term]
            child = listing.get_first_child()
            while child is not None:
                following = child.get_next_sibling(); listing.remove(child); child = following
            rows = self.tables.get(term, []) if self.tables else []
            self.stores[term].remove_all()
            for row_id, data in enumerate(rows):
                self.stores[term].append(OPLSParameterRow(row_id, [], data.get("level", "gray"), data.get("quality", "")))
                listing.append(self._render_row(term, row_id, data))
        if self.tables is not None:
            self.label_status.set_text("Parameter set: " + self.tables["folder"])
        self._update_charge_label(); self._update_tab_titles()

    def on_row_selected(self, _listing, row, term):
        if row is None or self.tables is None: return
        self.current = [term, row._opls_row_id, 0]
        self.button_fit_torsion.set_sensitive(term == "dihedral")
        GLib.idle_add(self._project_idle)

    def _vobject(self):
        eid = getattr(self.system, "e_id", None)
        candidates = [v for v in self.vm_session.vm_objects_dic.values()
                      if getattr(v, "e_id", None) == eid and not getattr(v, "is_surface", False)]
        return next((v for v in candidates if getattr(v, "active", False)), candidates[-1] if candidates else None)

    def _project_idle(self):
        try: self._project()
        except Exception: traceback.print_exc()
        return GLib.SOURCE_REMOVE

    def _project(self):
        if not self.current or self.tables is None: return
        from pdynamo.opls import editor
        term, row_id, instance_id = self.current
        data = self.tables[term][row_id]
        instances = data.get("instances", [])
        if not instances:
            self.label_instance.set_text(""); return
        instance = instances[instance_id % len(instances)]
        vobject = self._vobject()
        atoms = [vobject.atoms.get(i) for i in instance] if vobject is not None else []
        text = "Term {}/{}: {}".format(instance_id % len(instances) + 1, len(instances),
            "-".join(atom.name if atom is not None else "?" for atom in atoms))
        if atoms and all(atom is not None for atom in atoms):
            points = [atom.coords() for atom in atoms]
            value = editor.measure(term, points)
            if value is not None: text += f"   {term}: {value:.3f}"
            if term == "charges": text += f"   charge {data['value']:+.4f}"
            if self.checkbox_project.get_active(): self._pick(atoms, vobject, points)
        self.label_instance.set_text(text)

    def _pick(self, atoms, vobject, points):
        session = self.vm_session
        frame = getattr(session, "selection_box_frame", None)
        if frame is not None: frame.change_toggle_button_selecting_mode_status(True)
        else: session.picking_selection_mode = True
        picking = session.picking_selections
        picking.selection_function_picking(None)
        for atom in atoms[:4]: picking.selection_function_picking(atom)
        if self.checkbox_center.get_active():
            import numpy as np
            session.vm_glcore.center_on_coordinates(vobject, np.mean(np.asarray(points, dtype=np.float32), axis=0))
        session.vm_glcore.queue_draw()

    def _step_instance(self, delta):
        if not self.current: return
        term, row_id, index = self.current
        count = len(self.tables[term][row_id].get("instances", [])) or 1
        self.current[2] = (index + delta) % count
        self._project()

    def on_button_fit_torsion_clicked(self, *_args):
        if not self.current or self.current[0] != "dihedral" or self.pending: return
        from pdynamo.opls.torsion_fit import OPLSTorsionTarget
        term, row_id, index = self.current
        row = self.tables[term][row_id]
        vobject = self._vobject()
        coordinates = None
        if vobject is not None and len(vobject.atoms) == len(self.system.atoms):
            import numpy as np
            frame = min(getattr(self.vm_session, "frame", 0) or 0, len(vobject.frames) - 1)
            coordinates = np.asarray(vobject.frames[frame], dtype=float)
        try:
            target = OPLSTorsionTarget(self.system, row, row["instances"][index], coordinates=coordinates)
            from gui.windows.builder.torsion_fit_window import TorsionFitWindow
            if self.torsion_fit_window is None:
                self.torsion_fit_window = TorsionFitWindow(self.main, self._on_torsion_fit_applied)
            self.torsion_fit_window.open_window(target)
        except Exception as error:
            self.main.simple_dialog.error(msg=str(error))

    def _on_torsion_fit_applied(self, message):
        if self.visible: self.on_system_changed()
        self.label_status.set_text(message)

    def _parse_edit(self, text, field):
        if field != "terms": return float(text)
        values = []
        for chunk in text.replace(",", " ").split(";"):
            parts = chunk.split()
            if not parts or parts[0].lower() == "none": continue
            if len(parts) != 3: raise ValueError("Enter terms as 'k n phase; k n phase'.")
            values.append((float(parts[0]), int(parts[1]), float(parts[2])))
        return values

    def on_row_activated(self, listing, row):
        term = row._opls_term
        columns = self.columns[term]
        dialog = Gtk.Dialog(title="Edit OPLS parameter", transient_for=self.window, modal=True)
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL); dialog.add_button("Set", Gtk.ResponseType.OK)
        box = dialog.get_content_area(); box.set_spacing(8)
        entry = Gtk.Entry(hexpand=True)
        values = self._display_values(term, row._opls_data)
        editable = [(i, col) for i, col in enumerate(columns) if col[2]]
        for i, col in editable:
            line = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            line.append(Gtk.Label(label=col[0], xalign=0)); line.append(Gtk.Label(label=values[i], xalign=0, hexpand=True))
            box.append(line)
        if len(editable) > 1:
            entry.set_placeholder_text("Enter both values separated by spaces")
            entry.set_text(" ".join(values[i] for i, _ in editable))
        elif editable:
            entry.set_text(values[editable[0][0]])
        box.append(entry)
        dialog.connect("response", self._edit_response, row, entry, editable)
        dialog.present()

    def _display_values(self, term, data):
        value = data.get("value")
        if term == "charges": return [str(data.get("index", 0)+1), data.get("residue", ""), data.get("name", ""), data.get("type", ""), self._fmt(value), data.get("range", ""), data.get("source", "")]
        out=[]
        for _, field, _ in self.columns[term]:
            if field == "types": out.append(" - ".join(data["key"]))
            elif field == "v0": out.append(self._fmt(value[0] if isinstance(value, (list, tuple)) else value))
            elif field == "v1": out.append(self._fmt(value[1] if value else None))
            elif field == "terms": out.append("; ".join(f"{k:.4f} {n} {p:.1f}" for k,n,p in (value or [])) or "none")
            else: out.append(str(data.get(field, "")))
        return out

    def _edit_response(self, dialog, response, row, entry, editable):
        text = entry.get_text(); dialog.destroy()
        if response != Gtk.ResponseType.OK: return
        term = row._opls_term; data = row._opls_data
        try:
            parsed = text.split() if len(editable) > 1 and editable[0][1][1] != "terms" else [text]
            changes = self.pending.setdefault(term, {})
            if term == "charges": changes[data["index"]] = float(text)
            elif term == "outofplane": changes[data["key"]] = float(text)
            elif term == "dihedral":
                changes[data["key"]] = self._parse_edit(text, "terms")
            else:
                current = list(changes.get(data["key"], tuple(data["value"])))
                if len(parsed) != len(editable): raise ValueError("Enter one value for each editable field.")
                for value, (column_index, column) in zip(parsed, editable):
                    current[0 if column[1] == "v0" else 1] = float(value)
                changes[data["key"]] = tuple(current)
            listing = self.lists[term]
            listing.remove(row)
            listing.append(self._render_row(term, row._opls_row_id, data))
            self.label_status.set_text(f"{sum(len(v) for v in self.pending.values())} pending change(s): press Apply changes.")
            self._update_charge_label()
            self._update_tab_titles()
        except (ValueError, IndexError) as error:
            self.label_status.set_text(f"Invalid value: {error}")

    def on_row_selected_for_edit(self, listing, row): return self.on_row_selected(listing, row, row._opls_term)

    def _pending_total_charge(self):
        if self.tables is None: return None
        charges=[row["value"] for row in self.tables["charges"]]
        for index, value in self.pending.get("charges", {}).items(): charges[index]=value
        return sum(charges)

    def _update_charge_label(self):
        total=self._pending_total_charge()
        if total is None: self.label_charge.set_text(""); return
        color="#4caf50" if abs(total-round(total)) <= 1.0e-4 else "#e5534b"
        self.label_charge.set_markup(f'Total charge: <span foreground="{color}"><b>{total:+.4f}</b></span>')

    def on_button_revert_clicked(self, *_args):
        self.on_system_changed(); self.label_status.set_text("Changes discarded.")

    def on_button_apply_clicked(self, *_args):
        if not self.pending or self.system is None:
            self.label_status.set_text("Nothing to apply."); return
        from pdynamo.opls import editor
        try:
            before=self.system.Energy(log=None)
        except Exception: before=None
        try: summary=editor.apply_edits(self.system, self.pending)
        except Exception as error:
            self.main.simple_dialog.error(msg=str(error)); return
        try: after=self.system.Energy(log=None)
        except Exception: after=None
        self.on_system_changed()
        energy=f" Energy {before:.3f} → {after:.3f} kJ/mol." if before is not None and after is not None else ""
        self.label_status.set_text(f"Applied {summary['charges']} charge(s), {summary['terms']} parameter(s).{energy}")
        try:
            self.main.bottom_notebook.status_teeview_add_new_item(
                message=f"OPLS parameters edited: {summary['charges']} charge(s), {summary['terms']} parameter(s).", system=self.system)
            self.main.refresh_main_statusbar()
        except Exception: pass

    def on_close_request(self, *_args): self.close_window(); return True

    def close_window(self, *_args):
        if self.torsion_fit_window is not None: self.torsion_fit_window.close_window()
        if self.visible:
            self.window.destroy(); self.visible=False; self.tables=None; self.pending={}
