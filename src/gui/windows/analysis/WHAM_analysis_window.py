#!/usr/bin/env python
# -*- coding: utf-8 -*-
#  
#  EasyHybrid: Python interface for QM/MM and molecular simulations using pDynamo3
#  Module: Selection utilities for pDynamo systems
#
#  Copyright 2022-2025 Fernando Bachega
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
#      Provides functions for selecting atoms and residues in pDynamo systems
#      to facilitate QM/MM partitioning and molecular simulations.
#
from util.debug import dprint
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gio, GObject
from gui.gtk4_builder import connect_builder_signals, load_builder_file, load_builder_string
import gc
import os
from gui.widgets.custom_widgets import FolderChooserButton
from gui.widgets.custom_widgets import SaveTrajectoryBox

from gui.widgets.custom_widgets import CoordinatesComboBox
from gui.widgets.custom_widgets import SystemComboBox

VISMOL_HOME = os.environ.get('VISMOL_HOME')
HOME        = os.environ.get('HOME')


class TrajectoryBlockRow(GObject.Object):
    included = GObject.Property(type=bool, default=True)
    folder = GObject.Property(type=str, default="")

    def __init__(self, folder, included=True):
        super().__init__()
        self.folder = folder
        self.included = included

##====================================================================================
class WHAMWindow(Gtk.Window):
    """ Class doc """
    
    def __init__(self, main = None ):
        """ Class initialiser """
        self.main     = main
        self.home     = main.home 
        self.p_session= main.p_session 
        self.Visible  =  False        
        self.liststore = Gio.ListStore.new(TrajectoryBlockRow)

    
    def open_window (self):
        """ Function doc """
        if self.Visible  ==  False:
            self.builder = self.main.builder #Gtk.Builder()
            
            #load_builder_file(self.builder, os.path.join(VISMOL_HOME,'easyhybrid/gui/geometry_optimization_window.glade'))
            self.builder = Gtk.Builder()
            load_builder_file(self.builder, os.path.join(self.home,'src/gui/windows/analysis/WHAM_analysis_window.glade'))
            connect_builder_signals(self.builder, self)

            self.window = self.builder.get_object('window')
            self.window.set_title('WHAM Analysis')
            
            
            
            
            self.block_list_box = self.builder.get_object('treeview_trajectory_blocks')
            self.block_selection = Gtk.NoSelection.new(self.liststore)
            self.treeview = Gtk.ColumnView.new(self.block_selection)
            self.treeview.append_column(self._make_included_column())
            self.treeview.append_column(self._make_folder_column())
            self.block_list_box.append(self.treeview)
            
            
            '''------------------------------------FolderChooserButton-------------------------------'''     
            if self.p_session.psystem[self.p_session.active_id]:
                try:
                    wfolder = self.p_session.psystem[self.p_session.active_id].e_working_folder
                except:
                    wfolder = None
            else:
                wfolder = None
            self.folder_chooser_button = FolderChooserButton(main =  self.main, 
                                                         sel_type = 'folder', 
                                                             home = wfolder, 
                                                           parent = self.window)
            '''---------------------------------------------------------------------------------------'''     

            
            
            
            
            
            # - - - - - - - systems combobox - - - - - - -
            '''--------------------------------------------------------------------------------------------'''
            self.box = self.builder.get_object('box_system')
            self.combobox_systems = SystemComboBox(self.main)
            self.combobox_systems.connect("notify::selected", self.on_combobox_systemsbox_changed)
            '''--------------------------------------------------------------------------------------------'''
            self.box.append(self.combobox_systems)
            '''--------------------------------------------------------------------------------------------'''
            
            if self.p_session.psystem[self.p_session.active_id]:
                active_id = self.p_session.active_id
                self.combobox_systems.set_active_system (e_id = active_id)
            
            
            
            '''--------------------------------------------------------------------------------------------'''
            methods = [
                        '1D',
                        '2D',
                        ]
            self.methods_combo = self.builder.get_object('PMF_combobox')
            self.method_model = Gtk.StringList.new(methods)
            method_expression = Gtk.PropertyExpression.new(
                Gtk.StringObject, None, "string"
            )
            self.methods_combo.set_model(self.method_model)
            self.methods_combo.set_expression(method_expression)
            self.methods_combo.set_selected(0)
            
            
            
            

            
            
            self.builder.get_object('folder_chooser_box').append(self.folder_chooser_button.btn)
            self.folder_chooser_button.btn.set_hexpand(True)
            self.folder_chooser_button.btn.set_vexpand(True)
            
            #self.folder_chooser_button
            
            
            
            
            self.builder.get_object('button_add_trajectory_blocks').connect("clicked", self.button_add_trajectories)
            
            self.button_cancel = self.builder.get_object('button_cancel')
            self.button_cancel.connect("clicked", self.clear_treeview)
            self.window.connect("close-request", self.close_window)
            self.window.present()
            
            self.builder.get_object('entry_bins_RC2').hide()
            self.builder.get_object('label_bins_RC2').hide()

            
            self.Visible  = True   
        
        else:
            self.window.present()
    
    def close_window (self, button, data  = None):
        """ Function doc """
        self.window.destroy()
        self.Visible    =  False
        return True


    def run (self, button):
        """ Function doc """
        
        try:
            e_id   = self.combobox_systems.get_system_id()
            system = self.p_session.psystem[e_id]
        except:
            system = None
        
        _type     = self.methods_combo.get_selected()

        bins      = self.builder.get_object('entry_bins'     ).get_text()
        frequency = self.builder.get_object('entry_frequency').get_text()
        max_int   = self.builder.get_object('entry_max_int'  ).get_text()
        RMS_grad  = self.builder.get_object('entry_RMS_grad' ).get_text()
        temp      = self.builder.get_object('entry_temp'     ).get_text()
        
        
        
        #fileNames = glob.glob ( os.path.join ( outPath, "bAla_phi_*_psi_*.ptRes" ) )
        fileNames = []
        for position in range(self.liststore.get_n_items()):
            item = self.liststore.get_item(position)
            if item.included:
                fileNames.append(item.folder)
                
        fileNames.sort ( )
        
        parameters = {'analysis_type'        : 'wham'    , 
                      'system'               : system    ,
                      'file_names'            : fileNames ,
                      'type'                 : _type     ,
                      'logFrequency'         : int(frequency) ,
                      'maximumIterations'       : int(max_int  ) ,
                      'rmsGradientTolerance'         : float(RMS_grad ) ,
                      'temperature'          : int(temp     )  
                      }


        
        if _type ==1:
            bins_RC1 = self.builder.get_object('entry_bins'     ).get_text()
            bins_RC2 = self.builder.get_object('entry_bins_RC2').get_text()
            parameters['bins'] = [int(bins_RC2), int(bins_RC1)] 

        else:
            parameters['bins'] = [int(bins)] 
        
        parameters["folder"]  = self.folder_chooser_button.get_folder()
        
        
        #----------------------------------------------------------------------
        if parameters["folder"]:
            pass
        else:
            dprint('folder: ', parameters["folder"] )
        #----------------------------------------------------------------------
        
        #----------------------------------------------------------------------
        parameters["logfile"] = self.builder.get_object('log_name').get_text() 
        #----------------------------------------------------------------------
        
        
        #print(parameters)
        TrueFalse = self.p_session.run_analysis(parameters)
        
        if TrueFalse:
            self.window.destroy()
            self.Visible    =  False

        else:
            pass
            self.window.present()

    def _make_included_column(self):
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._setup_included_cell)
        factory.connect("bind", self._bind_included_cell)
        return Gtk.ColumnViewColumn.new("", factory)

    def _make_folder_column(self):
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._setup_folder_cell)
        factory.connect("bind", self._bind_folder_cell)
        return Gtk.ColumnViewColumn.new("Block", factory)

    @staticmethod
    def _setup_included_cell(_factory, list_item):
        check = Gtk.CheckButton()
        check.connect("toggled", lambda button, item=list_item: setattr(
            item.get_item(), "included", button.get_active()
        ) if item.get_item() is not None else None)
        list_item.set_child(check)

    @staticmethod
    def _bind_included_cell(_factory, list_item):
        list_item.get_child().set_active(list_item.get_item().included)

    @staticmethod
    def _setup_folder_cell(_factory, list_item):
        list_item.set_child(Gtk.Label(xalign=0))

    @staticmethod
    def _bind_folder_cell(_factory, list_item):
        list_item.get_child().set_text(list_item.get_item().folder)
    
    def clear_treeview (self, widget):
        """ Function doc """
        #print('clear_treeview')
        self.liststore.remove_all()
    
    
    def button_add_trajectories(self, button):
        """Select trajectory folders with the native GTK4 response flow."""
        dialog = Gtk.FileChooserDialog(
            title="Select Folders", transient_for=self.window,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        dialog.add_buttons(
            "Cancel", Gtk.ResponseType.CANCEL,
            "Open", Gtk.ResponseType.OK,
        )
        dialog.set_select_multiple(True)

        def on_response(chooser, response):
            files = chooser.get_files() if response == Gtk.ResponseType.OK else []
            folder_paths = [item.get_path() for item in files]
            chooser.destroy()
            for folder in folder_paths:
                self.liststore.append(TrajectoryBlockRow(folder))

        dialog.connect("response", on_response)
        dialog.present()

    def on_name_combo_changed(self, widget, _pspec=None):
        """ Function doc """


    def run_dialog (self):
        """ Function doc """
        dialog = Gtk.MessageDialog(
                    transient_for=self.main.window,
                    message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.OK,
                    text="Folder not found",
                    )
        dialog.format_secondary_text(
            "The folder you have selected does not appear to be valid. Please select a different folder or create a new one."
        )
        dialog.connect("response", lambda current_dialog, _response: current_dialog.destroy())
        dialog.present()


    def update (self, parameters = None):
        """ Function doc """
        #self._starting_coordinates_model_update()
        folder = self.p_session.psystem[self.p_session.active_id].e_working_folder
        if self.Visible:
            self.update_working_folder_chooser(folder)
            
        
    def update_working_folder_chooser (self, folder = None):
        """ Function doc """
        #folder = self.main.p_session.psystem[self.main.p_session.active_id].e_working_folder
        if folder:
            #print('update_working_folder_chooser')
            self.folder_chooser_button.set_folder(folder = folder)
        else:
            folder = self.p_session.psystem[self.p_session.active_id].e_working_folder
            if folder:
                self.folder_chooser_button.set_folder(folder = folder)
            else:
                pass

#=====================================================================================
    def on_combobox_PMF_type(self, widget, _pspec=None):
        _type     = self.methods_combo.get_selected()
        if _type ==1:
            self.builder.get_object('entry_bins_RC2').show()
            self.builder.get_object('label_bins_RC2').show()
            #parameters['bins'] = [int(bins), int(bins)] 
        else:
            self.builder.get_object('entry_bins_RC2').hide()
            self.builder.get_object('label_bins_RC2').hide()
        
        #self.builder.get_object('label_bins_RC2').hide()
        
    
    def on_combobox_systemsbox_changed(self, widget, _pspec=None):
        """ Function doc """
        system_id = self.combobox_systems.get_system_id()
        working_folder = self.p_session.psystem[system_id].e_working_folder
        #print(system_id, working_folder)
        self.folder_chooser_button.set_folder(working_folder)    
        #self.update_window ( selections = False, restraints = True)
