#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  EasyHybrid: Python interface for QM/MM and molecular simulations using pDynamo3
#  Module: Conjugate Peak Refinement (CPR) window
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
#      "Conjugate Peak Refinement" window -- pDynamo3's addOns.pyCPR
#      transition-state search. Modeled on chain_of_states_opt_window.py
#      for the two-endpoint (reactants/products) coordinate pickers
#      (same pattern the Nudged Elastic Band tool already uses), since
#      CPR -- unlike the Baker search -- takes a pair of structures
#      instead of a single starting point and needs no initial Hessian.
#
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk
from src.gtk4_compat import GTK_INVALID_LIST_POSITION
from gui.gtk4_builder import connect_builder_signals, load_builder_file
from gui.windows.simulation.gtk4_simulation_helpers import selected_vobject, show_folder_error, show_message

import os
import copy

from gui.widgets.custom_widgets import FolderChooserButton
from gui.widgets.custom_widgets import CoordinatesComboBox

HOME = os.environ.get('HOME')


class ConjugatePeakRefinementWindow:
    """ "Conjugate Peak Refinement" (CPR) window. """

    def __init__(self, main=None):
        """ Class initialiser """
        self.main      = main
        self.home      = main.home
        self.p_session = main.p_session
        self.Visible   = False
        self.sym_tag   = 'cpr'

    def open_window(self):
        """ Function doc """
        if self.Visible:
            self.window.present()
            return

        self.builder = Gtk.Builder()
        load_builder_file(self.builder, os.path.join(self.home, 'src/gui/windows/simulation/conjugate_peak_refinement_window.glade'))
        connect_builder_signals(self.builder, self)

        self.window = self.builder.get_object('cpr_window')
        self.window.set_title('Conjugate Peak Refinement')
        

        # -------------------- reactant / product coordinates --------------------
        self.box_coordinates1 = self.builder.get_object('box_coordinates1')
        self.combobox_starting_coordinates = CoordinatesComboBox()
        self.combobox_starting_coordinates.connect("notify::selected", self.on_name_combo_changed)
        self.box_coordinates1.append(self.combobox_starting_coordinates)

        self.box_coordinates2 = self.builder.get_object('box_coordinates2')
        self.combobox_starting_coordinates2 = CoordinatesComboBox()
        self.combobox_starting_coordinates2.connect("notify::selected", self.on_name_combo_changed)
        self.box_coordinates2.append(self.combobox_starting_coordinates2)

        self._starting_coordinates_model_update(init=True)

        # -------------------- CPR-specific widgets --------------------
        self.combobox_beta_type = self.builder.get_object('combobox_beta_type')

        # -------------------- working folder --------------------
        self.folder_chooser_button = FolderChooserButton(main=self.main, sel_type='folder', home=self.home)
        self.builder.get_object('folder_chooser_box').append(self.folder_chooser_button.btn)

        if self.main.p_session.psystem[self.main.p_session.active_id]:
            folder = self.main.p_session.psystem[self.main.p_session.active_id].e_working_folder
            if folder is None:
                folder = HOME
            self.folder_chooser_button.set_folder(folder=folder)

            output_name = self.p_session.get_output_filename_from_system(self.sym_tag)
            self.builder.get_object('traj_name').set_text(output_name)

        self.window.present()
        self.Visible = True

    def close_window(self, button=None, data=None):
        """ Function doc """
        self.window.destroy()
        self.Visible = False
        return True

    def on_name_combo_changed(self, widget, _pspec=None):
        """ Function doc """
        pass

    def run_dialog(self):
        show_folder_error(self.main.window)

    def get_parameters(self):
        """ Function doc """
        parameters = {
            "simulation_type"           : "Conjugate_Peak_Refinement",
            "number_of_structures"      : 8,
            "rmsGradientTolerance"      : 0.1,
            "rmsdMaximumTolerance"      : 1.5,
            "maxCPRrun"                 : 1000,
            "stepsPerSegment"           : 3,
            "betaType"                  : "PRP",
            "initialOrthogonalRuns"     : 0,
            "increaseTau"               : False,
            "breakIfTauReached"         : True,
            "finalUnrefinableRefinement": False,
            "trajectory_name"           : 'new_trajectory',
            "folder"                    : os.getcwd(),
        }

        parameters["number_of_structures"]       = int(self.builder.get_object('entry_num_structures').get_text())
        parameters["rmsGradientTolerance"]       = float(self.builder.get_object('entry_rmsd_tol').get_text())
        parameters["rmsdMaximumTolerance"]       = float(self.builder.get_object('entry_rmsd_max_tol').get_text())
        parameters["stepsPerSegment"]            = int(self.builder.get_object('entry_steps_per_segment').get_text())
        parameters["maxCPRrun"]                  = int(self.builder.get_object('entry_max_cpr_run').get_text())
        parameters["initialOrthogonalRuns"]      = int(self.builder.get_object('entry_initial_orthogonal_runs').get_text())
        parameters["betaType"]                   = self.combobox_beta_type.get_active_id()
        parameters["breakIfTauReached"]          = self.builder.get_object('check_break_if_tau_reached').get_active()
        parameters["increaseTau"]                = self.builder.get_object('check_increase_tau').get_active()
        parameters["finalUnrefinableRefinement"] = self.builder.get_object('check_final_unrefinable_refinement').get_active()

        parameters["trajectory_name"] = self.builder.get_object('traj_name').get_text()
        parameters["folder"]          = self.folder_chooser_button.get_folder()

        # Reactant and product structures are selected from native GTK4 list models.
        reactant = selected_vobject(self.combobox_starting_coordinates, self.main)
        product = selected_vobject(self.combobox_starting_coordinates2, self.main)
        if reactant is None or product is None:
            raise ValueError("Select both reactant and product coordinate sets.")

        self.main.p_session.set_psystem_coordinates_from_vobject(reactant)
        parameters["reac_coordinates"] = copy.deepcopy(
            self.main.p_session.psystem[self.main.p_session.active_id].coordinates3
        )
        parameters['obj1_key6'] = reactant.key6

        self.main.p_session.set_psystem_coordinates_from_vobject(product)
        parameters["prod_coordinates"] = copy.deepcopy(
            self.main.p_session.psystem[self.main.p_session.active_id].coordinates3
        )
        parameters['obj2_key6'] = product.key6

        return parameters

    def run(self, button):
        try:
            return self._run(button)
        except (ValueError, TypeError) as error:
            show_message(self.main.window, "Invalid simulation settings", str(error))
            return None

    def _run(self, button):
        """ Function doc """
        parameters = self.get_parameters()

        if not os.path.exists(parameters['folder']):
            self.run_dialog()
            return None

        self.main.p_session.run_simulation(parameters=parameters)
        self.window.destroy()
        self.Visible = False

    def _starting_coordinates_model_update(self, init=False):
        """ Function doc """
        if self.Visible or init:
            e_id = self.main.p_session.active_id
            self.combobox_starting_coordinates.set_model(self.main.vobject_liststore_dict[e_id])
            self.combobox_starting_coordinates2.set_model(self.main.vobject_liststore_dict[e_id])
            size = self.main.vobject_liststore_dict[e_id].get_n_items()
            self.combobox_starting_coordinates.set_selected(size - 1 if size else GTK_INVALID_LIST_POSITION)
            self.combobox_starting_coordinates2.set_selected(size - 1 if size else GTK_INVALID_LIST_POSITION)

    def update(self, parameters=None):
        """ Function doc """
        self._starting_coordinates_model_update()
        if self.Visible:
            self.update_working_folder_chooser()
            if self.p_session.psystem[self.p_session.active_id]:
                output_name = self.p_session.get_output_filename_from_system(self.sym_tag)
                self.builder.get_object('traj_name').set_text(output_name)

    def update_working_folder_chooser(self, folder=None):
        """ Function doc """
        if folder:
            self.folder_chooser_button.set_folder(folder=folder)
        else:
            folder = self.main.p_session.psystem[self.main.p_session.active_id].e_working_folder
            if folder:
                self.folder_chooser_button.set_folder(folder=folder)

    def restore_the_parameters_to_the_window(self, parameters):
        """ Restore exported parameters into the GTK window (Process Manager "reopen job"). """
        self.combobox_starting_coordinates.set_selected(parameters['cb1_active'])
        self.combobox_starting_coordinates2.set_selected(parameters['cb2_active'])

        self.builder.get_object('entry_num_structures').set_text(str(parameters.get('number_of_structures', 8)))
        self.builder.get_object('entry_rmsd_tol').set_text(str(parameters.get('rmsGradientTolerance', 0.1)))
        self.builder.get_object('entry_rmsd_max_tol').set_text(str(parameters.get('rmsdMaximumTolerance', 1.5)))
        self.builder.get_object('entry_steps_per_segment').set_text(str(parameters.get('stepsPerSegment', 3)))
        self.builder.get_object('entry_max_cpr_run').set_text(str(parameters.get('maxCPRrun', 1000)))
        self.builder.get_object('entry_initial_orthogonal_runs').set_text(str(parameters.get('initialOrthogonalRuns', 0)))

        self.combobox_beta_type.set_active_id(parameters.get('betaType', 'PRP'))
        self.builder.get_object('check_break_if_tau_reached').set_active(parameters.get('breakIfTauReached', True))
        self.builder.get_object('check_increase_tau').set_active(parameters.get('increaseTau', False))
        self.builder.get_object('check_final_unrefinable_refinement').set_active(parameters.get('finalUnrefinableRefinement', False))

        if 'trajectory_name' in parameters:
            self.builder.get_object('traj_name').set_text(parameters['trajectory_name'])
        if 'folder' in parameters and parameters['folder']:
            self.folder_chooser_button.set_folder(parameters['folder'])
