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
import os
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Pango
from gui.gtk4_builder import connect_builder_signals, load_builder_file, load_builder_string, choose_path

from gui.widgets.custom_widgets import FolderChooserButton
#from gui.widgets.custom_widgets import SystemComboBox
from gui.widgets.custom_widgets import CoordinatesComboBox
from gui.widgets.custom_widgets import ReactionCoordinateBox
from pprint import pprint

class EnergyRefinementWindow():

    def __init__(self, main = None ):
        """ Class initialiser """
        self.main       = main
        self.home       = main.home
        self.p_session  = main.p_session
        self.vm_session = main.vm_session
        self.Visible    =  False        
        self.input_folder = None
        
        self.input_types_liststore = Gtk.StringList.new([])
        self.input_types = {
                        0:'Vobject'    , #  single file
                        1:'pklfolder - pDynamo Trajectory'  , #  trajectory
                        2:'pklfolder2D - pDynamo 2D Trajectory', #  2d trajectory  
                      # 3:'pdbfile'    ,
                      # 4:'pdbfolder'  ,
                      # 5:'dcd',
                      # 6:'crd',
                      # 7:'xyz',
                      # 8:'mol2',
                      # 9:'netcdf',
                      #10:'log_file'  
                           }
        for key, input_type in self.input_types.items():
                self.input_types_liststore.append(input_type)

    def open_window (self, vobject = None):
        """ Function doc """
        if self.Visible  ==  False:
            self.builder = Gtk.Builder()
            load_builder_file(self.builder, os.path.join(self.home,'src/gui/windows/analysis/energy_refinement_window.glade'))
            connect_builder_signals(self.builder, self)
            #self.vobject = vobject
            self.window = self.builder.get_object('window')
            self.window.set_title('Energy Refinement Window')
            self.window.connect('close-request', self.close_window)
            self.builder.get_object('filechooser_file_folder').connect('clicked', self._choose_input_folder)
            
            
            
            
            
            
            #---------------------------------------------------------------------------------
            #                           INPUT TYPE COMBOBOX
            #---------------------------------------------------------------------------------
            self.comobobox_input_type = self.builder.get_object('comobobox_input_type')
            
            
            self.comobobox_input_type.set_model(self.input_types_liststore)
            self.comobobox_input_type.connect(
                "notify::selected", self.on_input_types_changed
            )
            #---------------------------------------------------------------------------------
           
           
           
            
            #----------------------------------------------------------------------------------------------
            #                                Starting Coordinates ComboBox  
            #----------------------------------------------------------------------------------------------
            self.box_coordinates = self.builder.get_object('box_coordinates')
            self.combobox_starting_coordinates = CoordinatesComboBox() #self.builder.get_object('coordinates_combobox')
            self.combobox_starting_coordinates.connect("notify::selected", self.on_coordinates_combobox_change)
            self.box_coordinates.append(self.combobox_starting_coordinates)
            self._starting_coordinates_model_update(init = True)
            #----------------------------------------------------------------------------------------------
            
            
            
            #----------------------------------------------------------------------------------------------
            #                                    Reaction Coordinate Boxes  
            #'''--------------------------------------------------------------------------------------------'''
            self.RC_box1 = ReactionCoordinateBox(self.main)
            self.builder.get_object('rc1_aligment').append(self.RC_box1)
            self.RC_box2 = ReactionCoordinateBox(self.main)
            self.builder.get_object('rc2_aligment').append(self.RC_box2)
            #'''--------------------------------------------------------------------------------------------'''
    
            
            
            
            
            
            '''--------------------------------------------------------------------------------------------'''     
            self.folder_chooser_button = FolderChooserButton(main =  self.main, sel_type = 'folder', home =  self.home)
            self.builder.get_object('folder_chooser_box').append(self.folder_chooser_button.btn)
            self.folder_chooser_button.btn.set_hexpand(True)
            self.folder_chooser_button.btn.set_vexpand(True)
            system_id      = self.p_session.active_id
            
            #------------------------------------------------------------------------------------------------
            if self.main.p_session.psystem[self.p_session.active_id]:
                if self.main.p_session.psystem[self.p_session.active_id].e_working_folder == None:
                    # NOTE: 'HOME' was an undefined name here (NameError bug) - it should
                    # refer to the window's own home path, exactly like self.home is used
                    # everywhere else in this file.
                    folder = self.home
                else:
                    folder = self.main.p_session.psystem[self.p_session.active_id].e_working_folder
                self.folder_chooser_button.set_folder(folder = folder)
            #------------------------------------------------------------------------------------------------
            
            
            if  self.p_session.psystem[self.p_session.active_id]:
                output_name = self.p_session.get_output_filename_from_system('energy_ref')
                self.builder.get_object('entry_logfile').set_text(output_name)  
            

            self.window.present()
            
            self.RC_box1.set_hide_scan_parameters()
            self.RC_box2.set_hide_scan_parameters()
            
            self.RC_box1.set_rc_type(0)
            self.RC_box2.set_rc_type(0)            
            
            self.comobobox_input_type.set_selected(0)
            
            self.combobox_starting_coordinates.set_selected(0)
            self.builder.get_object('button_cancel').connect('clicked', self.close_window)
            self.builder.get_object('button_run').connect('clicked', self.on_button_run_clicked)
            
            self.Visible  = True
    
        else:
            pass


    def _starting_coordinates_model_update (self, init = False):
        """ Function doc """
        #------------------------------------------------------------------------------------
        '''The combobox accesses, according to the id of the active system, 
        listostore of the dictionary object_list state_dict'''
        if self.Visible:

            e_id = self.main.p_session.active_id 
            self.combobox_starting_coordinates.set_model(self.main.vobject_liststore_dict[e_id])
            #------------------------------------------------------------------------------------
            size = self.main.vobject_liststore_dict[e_id].get_n_items()
            self.combobox_starting_coordinates.set_selected(size-1)
            #------------------------------------------------------------------------------------
        else:
            if init:
                e_id = self.main.p_session.active_id 
                self.combobox_starting_coordinates.set_model(self.main.vobject_liststore_dict[e_id])
                #------------------------------------------------------------------------------------
                size = self.main.vobject_liststore_dict[e_id].get_n_items()
                self.combobox_starting_coordinates.set_selected(size-1)
                #------------------------------------------------------------------------------------
            else:
                pass


    def on_input_types_changed(self, widget, _pspec=None):
        """ Function doc """
        _id = self.comobobox_input_type.get_selected()
        #print(_id)
        
        if _id == 0:
            self.builder.get_object('label_coordinates').show()
            self.combobox_starting_coordinates.show()
            
            self.builder.get_object('label_file_folder').hide()
            self.builder.get_object('filechooser_file_folder').hide()
            self.builder.get_object('box_reaction_coordinate2').set_sensitive(False)
        
        elif _id in [1,2]:
            self.builder.get_object('label_coordinates').hide()
            self.combobox_starting_coordinates.hide()
            
            self.builder.get_object('label_file_folder').show()
            self.builder.get_object('filechooser_file_folder').show()
            
            if _id ==1:
                self.builder.get_object('box_reaction_coordinate2').set_sensitive(False)
            elif _id ==2:
                self.builder.get_object('box_reaction_coordinate2').set_sensitive(True)
            else:
                pass

    def _choose_input_folder(self, button):
        choose_path(
            self.window, self._set_input_folder,
            title="Select trajectory folder",
            action=Gtk.FileChooserAction.SELECT_FOLDER,
            initial_path=self.input_folder or self.home,
        )

    def _set_input_folder(self, path):
        if path:
            self.input_folder = path
            self.builder.get_object('filechooser_file_folder').set_label(os.path.basename(path) or path)
            

    def _get_selected_vobject_info (self):
        """ Resolves the vismol object currently selected in
        combobox_starting_coordinates, along with its idx_2D_xy attribute
        (if any). Returns (vobject, idx_2D_xy) or (None, None) if nothing
        is selected.

        This used to be duplicated (identically) in on_coordinates_combobox_change
        and on_button_run_clicked - now both call this single implementation.
        """
        coordinate_row = self.combobox_starting_coordinates.get_selected_item()
        if coordinate_row is None:
            return None, None

        vobject_id = coordinate_row.object_id

        vobject   = self.main.vm_session.vm_objects_dic[vobject_id]
        idx_2D_xy = getattr(vobject, 'idx_2D_xy', None)

        return vobject, idx_2D_xy

    def on_coordinates_combobox_change (self, widget, _pspec=None):
        """ Function doc """
        vobject, idx_2D_xy = self._get_selected_vobject_info()

        if vobject is not None:
            dprint("is_2D_xy" , bool(idx_2D_xy))
            dprint("idx_2D_xy", idx_2D_xy)

            self.builder.get_object('box_reaction_coordinate2').set_sensitive(bool(idx_2D_xy))








    def close_window (self, button, data  = None):
        """ Function doc """
        self.window.destroy()
        self.Visible    =  False
        return True


    def on_button_run_clicked (self, button):
        """ Function doc """
        parameters = {"simulation_type":"Energy_Refinement"                ,
                      "dialog":True                                        ,                      
                      "system"     : self.p_session.psystem[self.p_session.active_id],
                      "system_name": self.p_session.psystem[self.p_session.active_id].label,
                      "initial_coordinates": None                          ,                       
                      "traj_type":'pklfolder'                              ,
                      'ignore_mm_charges': False                           ,
                      "NmaxThreads":1                                      ,
                      "show":False                                         }

        
        parameters['folder'] = self.folder_chooser_button.get_folder()
        
        input_type = self.comobobox_input_type.get_selected()
        dprint('_type: ',input_type)
        #----------------------------------------------------------------------
        if input_type == 0:
            parameters["traj_type"] = 'vobject'

            vobject, idx_2D_xy = self._get_selected_vobject_info()
            if vobject is not None:
                parameters["is_2D_xy"]  = bool(idx_2D_xy)
                parameters["idx_2D_xy"] = idx_2D_xy if idx_2D_xy else False

                parameters["trajectory"] = vobject.frames
                parameters["filename"] = self.builder.get_object('entry_logfile').get_text()



        elif input_type in [1,2]:
            if input_type == 1:
                parameters["traj_type"]  = 'pklfolder'
                parameters["is_2D_xy"] = False
            else:
                parameters["traj_type"]  = 'pklfolder2D'
                parameters["is_2D_xy"] = True
            
            parameters["data_path"] = self.input_folder
            if not parameters["data_path"]:
                return
            parameters["filename"] = self.builder.get_object('entry_logfile').get_text()
            files = os.listdir( parameters['data_path'])
            pkl_files = []
            
            for _file in files:
                # Check if the file is a text file
                if _file.endswith('.pkl'):
                    pkl_files.append(_file)

            dprint ('pDynamo pkl folder:' , parameters['traj_type'])
            dprint ('Number of pkl files:', len(pkl_files))
            parameters["trajectory"] = pkl_files
        
        else:
            pass
        #----------------------------------------------------------------------
        
        if self.builder.get_object('check_box_MM_chrg_to_zero').get_active():
            parameters["ignore_mm_charges"] = True
        else:
            pass
        
        parameters["RC1"] = self.RC_box1.get_rc_data()
        
        #if self.builder.get_object('label_check_button_reaction_coordinate2').get_active():
        #if parameters["traj_type"]  == 'pklfolder2D':
        
        if parameters["is_2D_xy"]:
            parameters["RC2"] = self.RC_box2.get_rc_data()
            parameters["NmaxThreads"] =  int(self.builder.get_object('n_CPUs_spinbutton').get_value())
            #parameters["traj_type"]   = 'pklfolder2D'
        
        else:
            parameters["RC2"] = None
            parameters["NmaxThreads"] = 1
            #parameters["traj_type"]   = 'pklfolder'
        
        #----------------------------------------------------------------------
        
        #pprint (parameters)
        self.p_session.run_simulation( parameters = parameters )


    def update (self):
        """ Function doc """
        #print('VismolGoToAtomWindow2 update')
        self._starting_coordinates_model_update()
        if self.Visible:
            self.update_working_folder_chooser()
            
            if  self.p_session.psystem[self.p_session.active_id]:
                output_name = self.p_session.get_output_filename_from_system('energy_ref')
                self.builder.get_object('entry_logfile').set_text(output_name)  

    def update_working_folder_chooser (self, folder = None):
        """ Function doc """
        if folder:
            #print('update_working_folder_chooser')
            self.folder_chooser_button.set_folder(folder = folder)
        else:
            
            folder = self.main.p_session.psystem[self.main.p_session.active_id].e_working_folder
            if folder:
                self.folder_chooser_button.set_folder(folder = folder)
            else:
                pass
