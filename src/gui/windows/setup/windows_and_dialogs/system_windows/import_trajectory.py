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
from gi.repository import Gtk, Pango
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gui.gtk4_builder import connect_builder_signals, load_builder_file, load_builder_string, choose_path
from gui.windows.setup.windows_and_dialogs.dialogs.import_charges_dialog import ChargeTypeSelectionDialog
import cairo


#---------------------------------------
from pBabel                    import*                                     
from pCore                     import*  
#---------------------------------------
from pMolecule                 import*                              
from pMolecule.MMModel         import*
from pMolecule.NBModel         import*                                     
from pMolecule.QCModel         import*
#---------------------------------------
from pScientific               import*                                     
from pScientific.Arrays        import*                                     
from pScientific.Geometry3     import*                                     
from pScientific.RandomNumbers import*                                     
from pScientific.Statistics    import*
from pScientific.Symmetry      import*
#---------------------------------------                              
from pSimulation               import*
#---------------------------------------

#import Pickle
from gui.widgets.custom_widgets import FolderChooserButton
from gui.widgets.custom_widgets import VismolTrajectoryFrame
from gui.widgets.custom_widgets import SystemComboBox
from gui.widgets.custom_widgets import CoordinatesComboBox
from gui.widgets.custom_widgets import get_colorful_square_pixel_buffer
from gui.widgets.custom_widgets import ReactionCoordinateBox

#from gui.widgets.custom_widgets import get_distance
from util.geometric_analysis            import get_distance 
from util.geometric_analysis            import get_dihedral 
from util.geometric_analysis            import get_angle 

from pdynamo.p_methods import LogFile


import util.orca_qc_keywords as orca_keys

from util.file_parser import get_file_type  
from util.file_parser import read_MOL2  
import pprint
import numpy as np
import gc
import os

import traceback

# --- cross-module imports added during refactor ---
from gui.windows.setup.windows_and_dialogs.dialogs.simple_dialog import SimpleDialog


VISMOL_HOME      = os.environ.get('VISMOL_HOME')
HOME             = os.environ.get('HOME')
PDYNAMO3_SCRATCH = os.environ.get('PDYNAMO3_SCRATCH')


class ImportTrajectoryWindow:
    """ Class doc """
    def __init__(self, main = None):
        """ Class initialiser """
        self.main                = main
        self.p_session           = main.p_session
        self.home                = main.home
        
        self.Visible             =  False        
        self.logfile_path = None
        
        self.data_type_dict = {
                        0:'pklfile'    , #  single file
                        1:'pklfolder'  , #  trajectory
                        2:'pklfolder2D', #  2d trajectory  
                        3:'pdbfile'    ,
                        4:'pdbfolder'  ,
                        5:'dcd',
                        6:'crd',
                        7:'xyz',
                        8:'mol2',
                        9:'netcdf',
                       10:'log_file',
                       11:'charges'  }
        
        self.folder_type_list = ['pklfolder', 'pklfolder2D', 'pdbfolder']

    def open_window (self, sys_selected = None):
        """ Function doc """
        if self.Visible  ==  False:
            '''--------------------------------------------------------------------------------------------'''
            self.builder = Gtk.Builder()
            load_builder_file(self.builder, os.path.join(self.home,'src/gui/windows/setup/import_trajectory_window.glade'))
            connect_builder_signals(self.builder, self)
            self.window = self.builder.get_object('import_trajectory_window')
            self.builder.get_object('file_chooser_btn_logfile').connect('clicked', self._choose_logfile)
            self.window.set_title('Import Data Window')
            '''--------------------------------------------------------------------------------------------'''
            self.box = self.builder.get_object('box_system')
            #------------------------------------------------------------------------------------
            
            self.combobox_pdynamo_system = SystemComboBox (self.main)
            self.box.append(self.combobox_pdynamo_system)
            self.combobox_pdynamo_system.connect(
                "notify::selected", self.on_combobox_pdynamo_system
            )
            if sys_selected is not None:
                self.combobox_pdynamo_system.set_active_system(sys_selected)
            else:
                self.combobox_pdynamo_system.set_selected(0)
            #'''--------------------------------------------------------------------------------------------------
            self.folder_chooser_button = FolderChooserButton(main =  self.main)
            self.builder.get_object('folder_chooser_box').append(self.folder_chooser_button.btn)
            self.folder_chooser_button.btn.set_hexpand(True)
            self.folder_chooser_button.btn.set_vexpand(True)
            #'''--------------------------------------------------------------------------------------------------
            
            
            
            #------------------------------------------------------------------------------------
            self.coordinates_box = self.builder.get_object('vobjects_combobox')
            self.combobox_starting_coordinates = CoordinatesComboBox()
            self.coordinates_box.append(self.combobox_starting_coordinates)
            self.combobox_starting_coordinates.connect(
                "notify::selected", self.on_vobject_combo_changed
            )
            
            #------------------------------------------------------------------------------------
            
            
            #------------------------------------------------------------------------------------
            self.combobox_starting_coordinates.set_sensitive(False)
            #------------------------------------------------------------------------------------

            #'''--------------------------------------------------------------------------------------------'''
            self.combox = self.builder.get_object('combobox_coordinate_type')
            coordinate_types = [
                'pkl file - pDynamo coordinates',
                'pkl folder - pDynamo trajectory',
                'pkl folder2d - pDynamo 2D trajectory',
                'pdb file - Protein Data Bank files',
                'pdb folder - multiple files trajectory',
                'dcd - CHARMM binary trajectory file',
                'crd - AMBER coordinates',
                'xyz - simple coordinate file',
                'mol2 - SYBIL coordinate file',
                'netcdf - AMBER trajectory file',
                'log - pDynamo/EasyHybrid logfile',
                'charges - mol2, aux, txt and etc.',
            ]
            self.coordinate_type_model = Gtk.StringList.new(coordinate_types)
            self.combox.set_model(self.coordinate_type_model)
            self.combox.set_expression(
                Gtk.PropertyExpression.new(Gtk.StringObject, None, "string")
            )
            self.combox.connect("notify::selected", self.on_combobox_coordinate_type)
    
            self.folder_chooser_button.btn.connect('clicked', self.update_logfile_chooser_btn)
            self.on_combobox_pdynamo_system(None)
            self.combox.set_selected(0)
            self.window.present()
            self.Visible  = True
        
        else:
            self.window.present()
    
    def close_window (self, button, data  = None):
        """ Function doc """
        self.window.destroy()
        self.Visible    =  False
        return True
    
    def update_logfile_chooser_btn (self, widget):
        """ Function doc """
        #print(self.folder_chooser_button.folder)
        trajfolder = self.folder_chooser_button.get_folder()
        #print(trajfolder)
        
        
        isdir = os.path.isdir(trajfolder)
        if isdir:
            files = os.listdir(trajfolder)
        
        
            logfiles = []
            for file_name in files:
                if file_name.endswith("log"):
                    logfiles.append(file_name)


            #basename  = os.path.basename(trajfolder)
            #logfile   = basename[:-5]+'log'

            #logfile   = os.path.join(trajfolder, logfile)
            #if exists(logfiles[0]):
            if len(logfiles):
                fullpath = os.path.join(trajfolder, logfiles[0])
                self._set_logfile_path(fullpath)

    def _choose_logfile(self, _button):
        choose_path(
            self.window, self._set_logfile_path,
            title="Select log file",
            action=Gtk.FileChooserAction.OPEN,
            initial_path=self.logfile_path or self.folder_chooser_button.get_folder(),
        )

    def _set_logfile_path(self, path):
        if path:
            self.logfile_path = path
            self.builder.get_object('file_chooser_btn_logfile').set_label(os.path.basename(path))
        
    def on_combobox_pdynamo_system (self, widget=None, _pspec=None):
        """ Function doc """
        sys_id = self.combobox_pdynamo_system.get_system_id()
        if sys_id is not None:
            pass
        else:
            return False

        self.combobox_starting_coordinates.set_model(self.main.vobject_liststore_dict[sys_id])
        model = self.combobox_starting_coordinates.get_model()
        if model is not None and model.get_n_items() > 0:
            self.combobox_starting_coordinates.set_selected(model.get_n_items() - 1)
        self.folder_chooser_button.folder = self.main.p_session.psystem[sys_id].e_working_folder

    def on_combobox_coordinate_type (self, widget, _pspec=None):
        """ Function doc """
        data_type = self.combox.get_selected()

        
        
        if data_type == 10:
            self.builder.get_object('frame_stride_box').set_sensitive(False) 
            self.builder.get_object('folder_chooser_box').set_sensitive(False) 
            self.builder.get_object('entry_create_a_new_vobj').set_sensitive(False)
            self.combobox_starting_coordinates.set_sensitive(True)

        
        elif data_type == 11:
            self.builder.get_object('frame_stride_box').set_sensitive(False) 
            self.builder.get_object('folder_chooser_box').set_sensitive(True) 
            self.builder.get_object('entry_create_a_new_vobj').set_sensitive(False)
            self.combobox_starting_coordinates.set_sensitive(False)
        
        elif data_type == 0:
            self.builder.get_object('frame_stride_box').set_sensitive(False) 
            self.builder.get_object('folder_chooser_box').set_sensitive(True) 
            self.builder.get_object('entry_create_a_new_vobj').set_sensitive(True)
            self.combobox_starting_coordinates.set_sensitive(True)

        elif data_type in [1,3,5,6,7,8,9]:
            self.builder.get_object('frame_stride_box').set_sensitive(True) 
            self.builder.get_object('folder_chooser_box').set_sensitive(True) 
            self.builder.get_object('entry_create_a_new_vobj').set_sensitive(True)
            self.combobox_starting_coordinates.set_sensitive(True)

        elif data_type in [2,4]:
            self.builder.get_object('frame_stride_box').set_sensitive(False) 
            self.builder.get_object('folder_chooser_box').set_sensitive(True) 
            self.builder.get_object('entry_create_a_new_vobj').set_sensitive(True)
            self.combobox_starting_coordinates.set_sensitive(False)
        else:
            self.builder.get_object('frame_stride_box').set_sensitive(True) 
            self.builder.get_object('folder_chooser_box').set_sensitive(True) 
            self.builder.get_object('entry_create_a_new_vobj').set_sensitive(True)
            self.combobox_starting_coordinates.set_sensitive(True)
        
        #print ('\ndata_type: ', data_type, '\ndata_type_dict: ',self.data_type_dict[data_type])
        data_type = self.data_type_dict[data_type]
        
        if  data_type in self.folder_type_list:
            self.folder_chooser_button.sel_type = 'folder'
        else:
            self.folder_chooser_button.sel_type = 'file'        

    def on_vobject_combo_changed (self, widget, _pspec=None):
        '''this combobox has the reference to the starting coordinates of a simulation'''
        #combobox_starting_coordinates = self.builder.get_object('combobox_starting_coordinates')
        coordinate_row = self.combobox_starting_coordinates.get_selected_item()
        if coordinate_row is not None:
            
            '''selecting the vismol object from the content that is in the combobox '''
            vobject_id = coordinate_row.object_id

    def on_name_combo_changed (self, widget, _pspec=None):
        """ Function doc """
        traj_type = self.combox.get_selected()
        #print (traj_type, self.data_type_dict[traj_type])
        traj_type = self.data_type_dict[traj_type]
        
        if  traj_type in self.folder_type_list:
            self.folder_chooser_button.sel_type = 'folder'
        else:
            self.folder_chooser_button.sel_type = 'file'

    def on_radio_button_change (self, widget):
        """ Function doc """
        if self.builder.get_object('radiobutton_import_as_new_object').get_active():
            self.combobox_starting_coordinates.set_sensitive(False)
            self.builder.get_object('entry_create_a_new_vobj').set_sensitive(True)

        if self.builder.get_object('radiobutton_append_to_a_vobject').get_active():
            self.builder.get_object('entry_create_a_new_vobj').set_sensitive(False)
            self.combobox_starting_coordinates.set_sensitive(True)

    def import_data (self, button):
        """ Function doc """
        
        parameters = {
                      'system_id'    : None,
                                     
                      'data_path'    : None,
                      'data_type'    : 0   ,
                      
                      'new_vobj_name': None, 
                      'vobject_id'   : None,
                      'vobject'      : None,
                      
                      'isAppend'     : False,
                      
                      'logfile'      : None,
                      
                      'first'        : None,
                      'last'         : None,
                      'stride'       : None,
                     }
        
        #entry_name     = None
        # - - - system - - - 
        system_row = self.combobox_pdynamo_system.get_selected_item()
        # GTK returns -1 when no system is selected (for example, when the
        # trajectory dialog is opened before importing a system).  Indexing
        # the model with -1 raises an opaque Gtk.IndexError.
        if system_row is None:
            self.main.bottom_notebook.status_teeview_add_new_item(
                message = 'Import Data requires an imported and selected pDynamo system.',
                system = None
            )
            return
        sys_id = system_row.system_id
        parameters['system_id'] = sys_id
        
        # data, a file or a folder - many files
        parameters['data_path'] = self.folder_chooser_button.get_folder()
        
        # A log file - optional
        parameters['logfile'] = self.logfile_path
        
        
        data_type = self.combox.get_selected()
        parameters['data_type'] = self.data_type_dict[data_type]
        
        try:
            parameters['first']  = int(self.builder.get_object('entry_first').get_text()  )
            parameters['last']   = int(self.builder.get_object('entry_last').get_text()   )
            parameters['stride'] = int(self.builder.get_object('entry_stride').get_text() )
        except:
            pass
        
        #----------------------------------------------------------------------------------------------
        '''Here, we determine whether it is necessary to create a new object 
        or append the coordinates to an existing one.'''
        if self.builder.get_object('radiobutton_import_as_new_object').get_active():
            parameters['new_vobj_name'] = self.builder.get_object('entry_create_a_new_vobj').get_text()
        else:
            #-----------------------------------------------------------------------------
            coordinate_row = self.combobox_starting_coordinates.get_selected_item()
            if coordinate_row is not None:
                
                '''selecting the vismol object from the content that is in the combobox '''
                vobject_id = coordinate_row.object_id
                vobject = self.main.vm_session.vm_objects_dic[vobject_id]
                
                parameters['vobject_id'] = vobject_id
                parameters['vobject']    = vobject
                parameters['isAppend']   = True
                
            #-------------------------------------------------------------------------------------------

        #print('\n parameters: ', parameters)
        try:
            if parameters['data_type'] == 'charges':
                from util.file_parser import chrg_file_parser
                charge_sets = chrg_file_parser(parameters['data_path'])
                if isinstance(charge_sets, dict):
                    dialog = ChargeTypeSelectionDialog(self.window, charge_sets.keys())

                    def on_charge_response(current_dialog, response):
                        selected = current_dialog.get_selected_item() if response == Gtk.ResponseType.OK else None
                        current_dialog.destroy()
                        if selected is not None:
                            self._apply_selected_charges(charge_sets[selected])

                    dialog.connect("response", on_charge_response)
                    dialog.present()
                    return

            self.main.p_session.import_data(parameters)
        except Exception as e:
            tb = traceback.format_exc()
            self.main.bottom_notebook.status_teeview_add_new_item(
                message=f"Error loading data: {e}", system=None)

            simpledialog = SimpleDialog(self.main )
            simpledialog.error_details(parent  = self.window,
                                        msg     = f"Error loading data: {e}",
                                        details = tb,
                                        title   = 'Import Error')

            dprint(f"Error loading data: {e}\n{tb}")

    def _apply_selected_charges(self, charges):
        for index, charge in enumerate(charges):
            self.main.p_session.psystem[self.main.p_session.active_id].mmState.charges[index] = float(charge)
           
            #system = None
        
    def update (self):
        """ Function doc """
        #print('VismolGoToAtomWindow2 update')
        pass
