#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  EasyHybrid: Python interface for QM/MM and molecular simulations using pDynamo3
#  Module: Radial distribution function g(r) analysis window
#
#  Copyright 2022-2026 Fernando Bachega
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#
#  Maintainer:
#      Fernando Bachega <ferbachega@gmail.com> or <easyhybrid3@gmail.com>
#
#  Description:
#      "RDF Analysis" window -- the pair radial distribution function g(r)
#      (plus running coordination number) between two named selections
#      over a trajectory's periodic cell. Reuses the exact same
#      named-selection mechanism as the SMD window's pulled/fixed-group
#      pickers (system.e_selections, populated via Selection -> Send to
#      Selection List) instead of building a new atom picker, and the
#      same per-frame orthorhombic cell (vismol_object.cell_coordinates)
#      reimaging_trajectory.py already reads. The actual math lives in
#      util/md_analysis.py (GTK-free, reusable, NumPy-only).
#
import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

import os

from gui.widgets.custom_widgets import SystemComboBox
from gui.widgets.custom_widgets import CoordinatesComboBox
from gui.windows.setup.windows_and_dialogs import TextWindow
from util import md_analysis

_ALL_ATOMS = "(all atoms)"


class RDFAnalysisWindow:

    def __init__(self, main=None):
        """ Class initialiser """
        self.main       = main
        self.home       = main.home
        self.p_session  = self.main.p_session
        self.vm_session = self.main.vm_session
        self.Visible    = False

    def open_window(self):
        """ Function doc """
        if self.Visible:
            self.window.present()
            return

        self.window = Gtk.Window(title="RDF Analysis", transient_for=self.main.window)
        self.window.set_resizable(False)
        self.window.connect("close-request", self.close_window)
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        for side in ("top", "bottom", "start", "end"):
            getattr(root, f"set_margin_{side}")(8)
        self.window.set_child(root)

        self.label_info = Gtk.Label(
            label=("g(r) between two groups. Choose the same group twice for a self-RDF. "
                   "Groups come from Selections and Restraints; add one through the "
                   "Selection menu before running the analysis."),
            wrap=True,
            max_width_chars=60,
        )
        root.append(self.label_info)

        trajectory = Gtk.Frame(label="Trajectory")
        trajectory_grid = Gtk.Grid(column_spacing=8, row_spacing=6)
        trajectory_grid.set_margin_top(6)
        trajectory_grid.set_margin_bottom(6)
        trajectory_grid.set_margin_start(6)
        trajectory_grid.set_margin_end(6)
        trajectory.set_child(trajectory_grid)
        root.append(trajectory)
        trajectory_grid.attach(Gtk.Label(label="System:", xalign=0), 0, 0, 1, 1)
        self.box_system = Gtk.Box()
        trajectory_grid.attach(self.box_system, 1, 0, 1, 1)
        trajectory_grid.attach(Gtk.Label(label="Object:", xalign=0), 0, 1, 1, 1)
        self.box_coordinates = Gtk.Box()
        trajectory_grid.attach(self.box_coordinates, 1, 1, 1, 1)

        self.combobox_systems = SystemComboBox(self.main)
        self.combobox_systems.connect("notify::selected", self.on_combobox_systems_changed)
        self.box_system.append(self.combobox_systems)

        self.coordinates_combobox = CoordinatesComboBox()
        self.coordinates_combobox.connect("notify::selected", self.on_combobox_coordinates_changed)
        self.box_coordinates.append(self.coordinates_combobox)

        groups = Gtk.Frame(label="Groups")
        groups_grid = Gtk.Grid(column_spacing=8, row_spacing=6)
        groups_grid.set_margin_top(6)
        groups_grid.set_margin_bottom(6)
        groups_grid.set_margin_start(6)
        groups_grid.set_margin_end(6)
        groups.set_child(groups_grid)
        root.append(groups)
        groups_grid.attach(Gtk.Label(label="Group A:", xalign=0), 0, 0, 1, 1)
        groups_grid.attach(Gtk.Label(label="Group B:", xalign=0), 1, 0, 1, 1)
        self.combo_group_a = Gtk.DropDown.new(Gtk.StringList.new([_ALL_ATOMS]), None)
        self.combo_group_b = Gtk.DropDown.new(Gtk.StringList.new([_ALL_ATOMS]), None)
        groups_grid.attach(self.combo_group_a, 0, 1, 1, 1)
        groups_grid.attach(self.combo_group_b, 1, 1, 1, 1)

        parameters = Gtk.Frame(label="RDF parameters")
        parameter_grid = Gtk.Grid(column_spacing=8, row_spacing=6)
        parameter_grid.set_margin_top(6)
        parameter_grid.set_margin_bottom(6)
        parameter_grid.set_margin_start(6)
        parameter_grid.set_margin_end(6)
        parameters.set_child(parameter_grid)
        root.append(parameters)
        parameter_grid.attach(Gtk.Label(label="Maximum distance (Å):", xalign=0), 0, 0, 1, 1)
        parameter_grid.attach(Gtk.Label(label="Bin width (Å):", xalign=0), 1, 0, 1, 1)
        self.spinbtn_r_max = Gtk.SpinButton.new(
            Gtk.Adjustment.new(15.0, 1.0, 100.0, 0.5, 5.0, 0.0), 0.1, 2
        )
        self.spinbtn_bin_width = Gtk.SpinButton.new(
            Gtk.Adjustment.new(0.1, 0.01, 5.0, 0.01, 0.1, 0.0), 0.01, 2
        )
        parameter_grid.attach(self.spinbtn_r_max, 0, 1, 1, 1)
        parameter_grid.attach(self.spinbtn_bin_width, 1, 1, 1, 1)

        range_frame = Gtk.Frame(label="Frame range")
        range_grid = Gtk.Grid(column_spacing=8, row_spacing=6)
        range_grid.set_margin_top(6)
        range_grid.set_margin_bottom(6)
        range_grid.set_margin_start(6)
        range_grid.set_margin_end(6)
        range_frame.set_child(range_grid)
        root.append(range_frame)
        self.chk_frames_from = Gtk.CheckButton(label="Use frame range")
        self.chk_frames_from.connect("toggled", self.on_frame_range_checkbox)
        range_grid.attach(self.chk_frames_from, 0, 0, 2, 1)
        self.entry_frame_init = Gtk.SpinButton.new(
            Gtk.Adjustment.new(0, 0, 1000000, 1, 10, 0), 1, 0
        )
        self.entry_frame_last = Gtk.SpinButton.new(
            Gtk.Adjustment.new(1, 1, 1000000, 1, 10, 0), 1, 0
        )
        self.entry_frame_init.set_sensitive(False)
        self.entry_frame_last.set_sensitive(False)
        range_grid.attach(Gtk.Label(label="First frame:", xalign=0), 0, 1, 1, 1)
        range_grid.attach(self.entry_frame_init, 1, 1, 1, 1)
        range_grid.attach(Gtk.Label(label="Last frame:", xalign=0), 0, 2, 1, 1)
        range_grid.attach(self.entry_frame_last, 1, 2, 1, 1)
        self.chk_step_size = Gtk.CheckButton(label="Use step size")
        self.chk_step_size.connect("toggled", self.on_step_size_checkbox)
        range_grid.attach(self.chk_step_size, 0, 3, 2, 1)
        self.entry_step_size = Gtk.SpinButton.new(
            Gtk.Adjustment.new(1, 1, 1000000, 1, 10, 0), 1, 0
        )
        self.entry_step_size.set_sensitive(False)
        range_grid.attach(Gtk.Label(label="Step:", xalign=0), 0, 4, 1, 1)
        range_grid.attach(self.entry_step_size, 1, 4, 1, 1)
        self.chk_plot = Gtk.CheckButton(label="Plot g(r)")
        self.chk_plot.set_active(True)
        range_grid.attach(self.chk_plot, 0, 5, 2, 1)

        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        buttons.set_halign(Gtk.Align.END)
        root.append(buttons)
        close = Gtk.Button(label="Close")
        close.connect("clicked", self.close_window)
        run = Gtk.Button(label="Run Analysis")
        run.add_css_class("suggested-action")
        run.connect("clicked", self.on_btn_run_analysis)
        buttons.append(close)
        buttons.append(run)

        if self.p_session.psystem:
            self.combobox_systems.set_active_system(e_id=self.p_session.active_id)

        self.window.present()
        self.Visible = True

    def close_window(self, button=None, data=None):
        """ Function doc """
        if not self.Visible:
            return
        self.window.destroy()
        self.Visible = False
        return True

    def on_step_size_checkbox(self, widget):
        self.entry_step_size.set_sensitive(widget.get_active())

    def on_frame_range_checkbox(self, widget):
        active = widget.get_active()
        self.entry_frame_init.set_sensitive(active)
        self.entry_frame_last.set_sensitive(active)

    def on_combobox_systems_changed(self, widget, _pspec=None):
        system_id = self.combobox_systems.get_system_id()
        if system_id is None:
            return
        model = self.main.vobject_liststore_dict.get(system_id)
        self.coordinates_combobox.set_model(model)
        size = model.get_n_items() if model is not None else 0
        self.coordinates_combobox.set_active_vobject(size - 1)

    def on_combobox_coordinates_changed(self, widget, _pspec=None):
        self._refresh_group_combos()

    def _refresh_group_combos(self):
        system_id = self.coordinates_combobox.get_system_id()
        groups = [_ALL_ATOMS]
        if system_id is None:
            self.combo_group_a.set_model(Gtk.StringList.new(groups))
            self.combo_group_b.set_model(Gtk.StringList.new(groups))
            return
        system = self.p_session.psystem.get(system_id)
        if system is not None:
            groups.extend(system.e_selections.keys())
        self.combo_group_a.set_model(Gtk.StringList.new(groups))
        self.combo_group_b.set_model(Gtk.StringList.new(groups))
        self.combo_group_a.set_selected(0)
        self.combo_group_b.set_selected(0)

    def _resolve_group(self, combo, system_id, n_atoms):
        selected = combo.get_selected_item()
        name = selected.get_string() if selected is not None else None
        if name is None or name == _ALL_ATOMS:
            return list(range(n_atoms))
        return list(self.p_session.psystem[system_id].e_selections[name])

    def on_btn_run_analysis(self, widget, event=None):
        """ Function doc """
        vobject_id = self.coordinates_combobox.get_vobject_id()
        system_id = self.coordinates_combobox.get_system_id()
        if vobject_id is None or system_id is None:
            self.main.simple_dialog.info(msg='Please select a System and an Object (trajectory) first.')
            return

        vismol_object = self.main.vm_session.vm_objects_dic.get(vobject_id)
        if vismol_object is None:
            self.main.simple_dialog.info(msg='Please select a valid Object (trajectory).')
            return

        n_atoms = len(vismol_object.atoms)
        n_frames = vismol_object.frames.shape[0]
        group_a = self._resolve_group(self.combo_group_a, system_id, n_atoms)
        group_b = self._resolve_group(self.combo_group_b, system_id, n_atoms)
        if not group_a or not group_b:
            self.main.simple_dialog.info(msg='Both Group A and Group B must contain at least one atom.')
            return
        same_selection = (
            self._selected_group_name(self.combo_group_a)
            == self._selected_group_name(self.combo_group_b)
        )

        if vismol_object.cell_coordinates is None or len(vismol_object.cell_coordinates) == 0:
            self.main.simple_dialog.info(
                msg='This Object has no periodic cell information -- g(r) needs a periodic '
                    'box to normalise by density (see util/md_analysis.py). '
                    'Import/build the trajectory with its cell, or set one via "Reimaging (Wrapping)" first.')
            return

        f_init = 0
        f_last = n_frames
        step_size = 1
        if self.chk_frames_from.get_active():
            f_init = self.entry_frame_init.get_value_as_int()
            f_last = self.entry_frame_last.get_value_as_int()
        if self.chk_step_size.get_active():
            step_size = self.entry_step_size.get_value_as_int()
        f_init = max(0, min(f_init, n_frames))
        f_last = max(f_init, min(f_last, n_frames))
        step_size = max(1, step_size)

        frame_indices = range(f_init, f_last, step_size)
        n_cell_frames = vismol_object.cell_coordinates.shape[0]

        coords_a = [vismol_object.frames[f][group_a] for f in frame_indices]
        coords_b = [vismol_object.frames[f][group_b] for f in frame_indices]
        # . cell_coordinates[f][-1] is the box's far corner (a, b, c) for an
        #   orthorhombic cell built from the origin -- same convention
        #   reimaging_trajectory.py already relies on. Falls back to the
        #   single stored cell (index 0) for a trajectory whose box was
        #   only ever set once (no per-frame XST/XSC data).
        boxes = [vismol_object.cell_coordinates[min(f, n_cell_frames - 1)][-1] for f in frame_indices]

        if len(coords_a) < 1:
            self.main.simple_dialog.info(msg='No frames in the selected range.')
            return

        r_max = self.spinbtn_r_max.get_value()
        bin_width = self.spinbtn_bin_width.get_value()

        try:
            r, g_r, coordination = md_analysis.compute_rdf(
                coords_a, coords_b, boxes, same_selection=same_selection,
                r_max=r_max, bin_width=bin_width)
        except (ValueError, FloatingPointError) as error:
            self.main.simple_dialog.info(msg='RDF calculation failed: {}'.format(error))
            return

        text = 'r (Å)\tg(r)\tN(r)\n'
        for i in range(len(r)):
            text += '{:.4f}\t{:.6f}\t{:.4f}\n'.format(r[i], g_r[i], coordination[i])
        textwindow = TextWindow(text)

        if self.chk_plot.get_active():
            from util.easyplot import XYPlot
            self.plot = XYPlot()
            self.plot.add(X=list(r), Y=list(g_r),
                           symbol=None, sym_color=[1, 1, 1], sym_fill=False,
                           line='solid', line_color=[0, 0, 0], energy_label=None)
            self.plot.Ymin_list = [0]

            window = Gtk.Window()
            window.set_title('g(r)')
            window.set_child(self.plot)
            window.set_default_size(700, 420)
            window.present()

        self.label_info.set_text(
            'Done -- {} frames, {} atoms in A, {} in B.'.format(len(coords_a), len(group_a), len(group_b)))

    @staticmethod
    def _selected_group_name(combo):
        selected = combo.get_selected_item()
        return selected.get_string() if selected is not None else _ALL_ATOMS
