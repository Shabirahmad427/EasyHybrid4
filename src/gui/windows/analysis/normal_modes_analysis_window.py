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
from gi.repository import Gtk, GObject
from src.gtk4_compat import GTK_INVALID_LIST_POSITION
from gui.gtk4_builder import connect_builder_signals, load_builder_file, load_builder_string
#from GTKGUI.gtkWidgets.filechooser import FileChooser
#from easyhybrid.pDynamoMethods.pDynamo2Vismol import *
import gc
import os
import threading
import time

from gui.widgets.custom_widgets import SystemComboBox
from gui.widgets.custom_widgets import CoordinatesComboBox
from gui.model_rows import CoordinateChoiceRow
from gi.repository import Gio


VISMOL_HOME = os.environ.get('VISMOL_HOME')
HOME        = os.environ.get('HOME')


class NormalModeRow(GObject.Object):
    active = GObject.Property(type=bool, default=False)
    mode_id = GObject.Property(type=str, default="")
    frequency = GObject.Property(type=str, default="")

    def __init__(self, active, mode_id, frequency):
        super().__init__()
        self.active = active
        self.mode_id = mode_id
        self.frequency = frequency


def _mode_text_factory(property_name):
    factory = Gtk.SignalListItemFactory()

    def setup(_factory, item):
        item.set_child(Gtk.Label(xalign=0))

    def bind(_factory, item):
        item.get_child().set_text(getattr(item.get_item(), property_name))

    factory.connect("setup", setup)
    factory.connect("bind", bind)
    return factory


class NormalModesAnalysisWindow(Gtk.Window):
    """ Class doc """
    def __init__(self, main = None, system_liststore = None ):
        """ Class initialiser """
        self.main          = main#self.main.system_liststore
        self.home                  = main.home
        self.visible               = False        
        self.p_session             = main.p_session
        self.vm_session            = main.vm_session
        
        self.modes = None
        self.running = False
        self.stop_thread = True
        
        self.lower = 0
        self.upper = 0
        self._mode_bindings = {}
        
    
    def open_window (self):
        """  """
        if self.visible  ==  False:
            self.builder = Gtk.Builder()
            load_builder_file(self.builder, os.path.join(self.home,'src/gui/windows/analysis/normal_modes_analysis_window.glade')) #~/programs/EasyHybrid3/gui/windows/normal_mode_analysis.glade
            connect_builder_signals(self.builder, self)
            
            self.window = self.builder.get_object('window')
            self.window.set_default_size(200, 600)  
            self.window.set_title('Normal Modes')  
            
            
            
            
            # - - - - - - - systems combobox - - - - - - -
            '''--------------------------------------------------------------------------------------------'''
            self.box1 = self.builder.get_object('box_system')
            self.system_names_combo = SystemComboBox (self.main)
            #self.system_names_combo =self.builder.get_object('systems_combobox')
            #self.system_names_combo.set_model(self.main.system_liststore)

            self.system_names_combo.connect("notify::selected", self.on_system_names_combobox_changed)
            '''--------------------------------------------------------------------------------------------'''
            self.box1.append(self.system_names_combo)


            self.coordinates_liststore = Gio.ListStore.new(CoordinateChoiceRow)
            self.coordinates_liststore.append(CoordinateChoiceRow('New Visual Object', -1, -1))
            # - - - - - - - coordinates combobox - - - - - - -
            '''--------------------------------------------------------------------------------------------'''
            self.coordinates_combobox = CoordinatesComboBox()
            self.builder.get_object('box_coordinates').append(self.coordinates_combobox)
            self.coordinates_combobox.connect("notify::selected", self.on_coordinates_combobox_changed)
            '''--------------------------------------------------------------------------------------------'''
            
            
            active_coordinates = self.main.vobject_liststore_dict[self.main.p_session.active_id]
            for index in range(active_coordinates.get_n_items()):
                row = active_coordinates.get_item(index)
                self.coordinates_liststore.append(CoordinateChoiceRow(
                    row.name, row.object_id, row.system_id, row.icon
                ))

            
            self.coordinates_combobox.set_model(self.coordinates_liststore)
            self.coordinates_combobox.set_selected(self.coordinates_liststore.get_n_items() - 1)
            




            self.liststore = Gio.ListStore.new(NormalModeRow)
            self.treeview = Gtk.ColumnView.new(Gtk.NoSelection.new(self.liststore))
            self.builder.get_object('selection_treeview').append(self.treeview)
            self.treeview.append_column(Gtk.ColumnViewColumn.new(
                "A", self._mode_check_factory()))
            self.treeview.append_column(Gtk.ColumnViewColumn.new(
                "Mode", _mode_text_factory("mode_id")))
            self.treeview.append_column(Gtk.ColumnViewColumn.new(
                "Frequency", _mode_text_factory("frequency")))






            self.spin_button =self.builder.get_object('spin_button')






            self.window.present()                                               
            #self.system_names_combo.set_selected(0)
            self.visible    =  True
            '''--------------------------------------------------------------------------------------------'''

    def close_window (self, button, data  = None):
        """ Function doc """

        self.stop(None)
        #self.running = False  


        self.window.destroy()
        self.visible    =  False
        return True
        #print('self.visible',self.visible)
    
    def _mode_check_factory(self):
        factory = Gtk.SignalListItemFactory()

        def setup(_factory, item):
            check = Gtk.CheckButton()
            check.connect("toggled", self._on_mode_toggled, item)
            item.set_child(check)

        def bind(_factory, item):
            row = item.get_item()
            binding = row.bind_property(
                "active", item.get_child(), "active",
                GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE,
            )
            self._mode_bindings[id(item)] = binding

        def unbind(_factory, item):
            binding = self._mode_bindings.pop(id(item), None)
            if binding is not None:
                binding.unbind()

        factory.connect("setup", setup)
        factory.connect("bind", bind)
        factory.connect("unbind", unbind)
        return factory

    def _on_mode_toggled(self, check, list_item):
        row = list_item.get_item()
        if row is None:
            return
        row.active = check.get_active()
        if row.active:
            for position in range(self.liststore.get_n_items()):
                other = self.liststore.get_item(position)
                if other is not row:
                    other.active = False
            mode = self.modes[int(row.mode_id)]
            self.lower = int(mode[1][0])
            self.upper = int(mode[1][1])
            self.value = self.lower
    
    def on_button_import(self, button):
        """Import selected normal-mode trajectory folders asynchronously."""
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
            selected = chooser.get_files() if response == Gtk.ResponseType.OK else []
            folder_paths = [item.get_path() for item in selected]
            chooser.destroy()
            if not folder_paths:
                return

            parameters = {}
            system_row = self.system_names_combo.get_selected_item()
            coordinate_row = self.coordinates_combobox.get_selected_item()
            parameters['system_id'] = system_row.system_id if system_row else 0
            parameters['vobject_id'] = coordinate_row.object_id if coordinate_row else -1
            parameters.update({
                'new_vobj_name': 'normal modes',
                'data_type': 'normal_modes',
                'trajectories': folder_paths,
                'logfile': False,
            })
            self.modes = self.p_session.import_data(parameters)
            self.liststore.remove_all()
            for index, data in self.modes.items():
                self.liststore.append(NormalModeRow(
                    False, str(index), '{:.3f}'.format(float(data[0]))
                ))

        dialog.connect("response", on_response)
        dialog.present()

    def _coordinates_model_update (self, e_id):
        """ Function doc """
        #------------------------------------------------------------------------------------
        '''The combobox accesses, according to the id of the active system, 
        listostore of the dictionary object_list state_dict'''
        if self.visible:
            #e_id = self.main.p_session.active_id 
            rows = self.main.vobject_liststore_dict[e_id]
            model = Gio.ListStore.new(CoordinateChoiceRow)
            model.append(CoordinateChoiceRow('New Visual Object', -1, -1))
            for position in range(rows.get_n_items()):
                row = rows.get_item(position)
                model.append(CoordinateChoiceRow(row.name, row.object_id, row.system_id, row.icon))
            self.coordinates_combobox.set_model(model)
            #------------------------------------------------------------------------------------
            size = model.get_n_items()
            self.coordinates_combobox.set_selected(size-1)
            #------------------------------------------------------------------------------------
        else:
            pass
    
    
    def update_window (self, system_names = True, coordinates = False,  selections = True):
        """Refresh the coordinate choices when the system list changes."""
        if not self.visible:
            return
        if not self.p_session.psystem:
            return
        system_id = self.system_names_combo.get_system_id()
        if system_id not in self.p_session.psystem:
            system_id = self.p_session.active_id
            if system_id in self.p_session.psystem:
                self.system_names_combo.set_active_system(system_id)
        if coordinates and system_id is not None:
            self._coordinates_model_update(system_id)
    
    
    def update (self, system_names = True, coordinates = False,  selections = True ):
        """ Function doc """
        pass
    
    def on_system_names_combobox_changed (self, widget, _pspec=None):
        """Update coordinate choices when the system dropdown changes."""
        system_id = self.system_names_combo.get_system_id()
        if system_id is not None:
            self._coordinates_model_update(system_id)

    def on_coordinates_combobox_changed(self, widget, _pspec=None):
        """ Function doc """
        index = self.coordinates_combobox.get_selected()
       
        if index == GTK_INVALID_LIST_POSITION:
            '''_id = -1 means no item inside the combobox'''
            return None
        
        else:    
            row = self.coordinates_liststore.get_item(index)
            name, vobject_id, system_id = row.name, row.object_id, row.system_id
            
            #print(name, vobject_id, system_id)
            
            try:
                vobject = self.vm_session.vm_objects_dic[vobject_id]
                self.liststore.remove_all()
                for i, data in vobject.normal_modes_dict.items():
                    self.liststore.append(NormalModeRow(False, str(i), str(data[0])))
            except:
                dprint('vobject has no Normal Modes data')
                pass
            

        
    def play (self, button):
        # Create and start a new thread when the button is clicked
        if self.running:
            pass
        
        else:
            thread = threading.Thread(target=self.long_task)
            thread.start()
            
            self.running = True
        
        
    def long_task(self):
        # This flag is used to stop the thread
        self.stop_thread = False
        i = 0
        
        self.lower
        self.upper
        
        self.value = self.lower
        while self.stop_thread == False:
            if self.stop_thread:
                return

            self.vm_session.set_frame(int(self.value))
            self.value += 1
            #print(self.value)

            if self.value >= self.upper:
                self.value = self.lower
                self.vm_session.set_frame(self.value)
            #time.sleep(0.01)
            time.sleep(1/self.spin_button.get_value())
            
    def stop (self, button):
        """ Function doc """
        self.stop_thread = True
        self.running = False    

    def forward (self, button):
        """ Function doc """
        value =  int(self.scale.get_value())
        value = value+1
        self.scale.set_value(int(value))
        self.vm_session.set_frame(int(value))
        #print(value)
        return value
