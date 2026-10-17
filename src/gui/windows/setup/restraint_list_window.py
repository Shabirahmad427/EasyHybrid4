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
from gi.repository import Gtk, Gio
from src.gtk4_compat import GTK_INVALID_LIST_POSITION
from gui.gtk4_builder import connect_builder_signals, load_builder_file, load_builder_string
#from GTKGUI.gtkWidgets.filechooser import FileChooser
#from easyhybrid.pDynamoMethods.pDynamo2Vismol import *
import gc
import os

from gui.widgets.custom_widgets import SystemComboBox
from gui.widgets.custom_widgets import CoordinatesComboBox
from gui.gtk4_context_menu import ContextMenu, append_mapping
from gui.model_rows import SelectionChoiceRow

VISMOL_HOME = os.environ.get('VISMOL_HOME')
HOME        = os.environ.get('HOME')


class RestraintListWindow(Gtk.Window):
    """ Class doc """
    def __init__(self, main = None, system_liststore = None ):
        """ Class initialiser """
        self.main_session          = main#self.main_session.system_liststore
        self.home                  = main.home
        self.visible               = False        
        self.p_session             = main.p_session
        self.vm_session            = main.vm_session

        self.selection_liststore = Gio.ListStore.new(SelectionChoiceRow)
    
    def open_window (self):
        """ Function doc ~/programs/VisMol/easyhybrid/gui/selection_list.glade"""
        if self.visible  ==  False:
            self.builder = Gtk.Builder()
            load_builder_file(self.builder, os.path.join(self.home,'src/gui/windows/setup/restraint_list.glade'))
            connect_builder_signals(self.builder, self)
            
            self.window = self.builder.get_object('window')
            self.window.set_default_size(200, 600)  
            self.window.set_title('Restraints')  
            
            # - - - - - - - systems combobox - - - - - - -
            '''--------------------------------------------------------------------------------------------'''
            self.box = self.builder.get_object('box_system')
            self.combobox_systems = SystemComboBox(self.main_session)
            self.combobox_systems.connect("notify::selected", self.on_combobox_systemsbox_changed)
            '''--------------------------------------------------------------------------------------------'''
            self.box.append(self.combobox_systems)



            # - - - - - - - coordinates combobox - - - - - - -
            '''--------------------------------------------------------------------------------------------'''
            self.box_coordinates = self.builder.get_object('box_coordinates')
            self.coordinates_combobox = CoordinatesComboBox() #self.builder.get_object('coordinates_combobox')
            self.box_coordinates.append(self.coordinates_combobox)
            
            '''--------------------------------------------------------------------------------------------'''


            system  = self.main_session.p_session.get_system()
            self.combobox_systems.set_active_system(system.e_id)
            


            # - - - - - - - GTK4 selection list - - - - - - -
            '''--------------------------------------------------------------------------------------------'''
            self.treeview = self.builder.get_object('selection_treeview')
            self.tree_selection = Gtk.SingleSelection.new(self.selection_liststore)
            self.treeview.set_model(self.tree_selection)
            self._install_selection_columns()
            self.treeview.connect('activate', self.on_treeview_Objects_row_activated)
            click = Gtk.GestureClick()
            click.set_button(0)
            click.connect("released", self.on_treeview_Objects_button_release_event)
            self.treeview.add_controller(click)
            '''--------------------------------------------------------------------------------------------'''


            #self.refresh_system_liststore()
            self.treeview_menu = SelectionContextMenu(self)
            self.window.present()                                               
            #self.combobox_systems.set_selected(0)
            self.visible    =  True
            '''--------------------------------------------------------------------------------------------'''

        else:
            self.window.present()

    def _install_selection_columns(self):
        for title, attribute in (("Selection", "name"), ("Number of Atoms", "atom_count")):
            factory = Gtk.SignalListItemFactory()
            factory.connect("setup", self._setup_selection_cell)
            factory.connect("bind", self._bind_selection_cell, attribute)
            self.treeview.append_column(Gtk.ColumnViewColumn.new(title, factory))

    @staticmethod
    def _setup_selection_cell(_factory, list_item):
        label = Gtk.Label(xalign=0)
        label.set_margin_start(6)
        label.set_margin_end(6)
        list_item.set_child(label)

    @staticmethod
    def _bind_selection_cell(_factory, list_item, attribute):
        row = list_item.get_item()
        value = getattr(row, attribute)
        list_item.get_child().set_text(str(value))
            
    def close_window (self, button, data  = None):
        """ Function doc """
        #self.BackUpWindowData()
        self.window.destroy()
        self.visible    =  False
        return True
        #print('self.visible',self.visible)
    
    def _coordinates_model_update (self, e_id):
        """ Function doc """
        #------------------------------------------------------------------------------------
        '''The combobox accesses, according to the id of the active system, 
        listostore of the dictionary object_list state_dict'''
        if self.Visible:
            #e_id = self.main.p_session.active_id 
            self.combobox_starting_coordinates.set_model(e_id)
            #------------------------------------------------------------------------------------
            size = self.main.vobject_liststore_dict[e_id].get_n_items()
            self.combobox_starting_coordinates.set_selected(size-1)
            #------------------------------------------------------------------------------------
        else:
            pass
    
    
    def update_window (self, system_names = True, coordinates = False,  selections = True):
        """ Function doc """
        if self.visible:
            
            system_id = self.combobox_systems.get_system_id()
            if system_id is not None:
                if selections:
                    self.refresh_selection_liststore(system_id)
        else:
            pass
    
    
    def update (self, system_names = True, coordinates = False,  selections = True ):
        """ Function doc """
        self.update_window(system_names=system_names, coordinates=coordinates,
                           selections=selections)

    
    def refresh_system_liststore (self):
        """ Function doc """
        self.main_session.refresh_system_liststore()
    
    def refresh_selection_liststore (self, system_id = None ):
        """ Function doc """
        self.selection_liststore.remove_all()
        
        
        ''' QC atoms'''
        if self.p_session.psystem[system_id].qcModel:
            self.p_session.psystem[system_id].e_selections["QC atoms"] = list(self.p_session.psystem[system_id].qcState.pureQCAtoms)


        '''Fixed atoms'''
        if self.p_session.psystem[system_id].freeAtoms is None:
            pass
        
        else:
            self.p_session.psystem[system_id].e_selections["fixed atoms"] = self.p_session.get_fixed_atoms_from_system(self.p_session.psystem[system_id])
  
        
        for selection , indexes in self.p_session.psystem[system_id].e_selections.items():
            self.selection_liststore.append(SelectionChoiceRow(selection, len(indexes)))
    
    
    def on_combobox_systemsbox_changed(self, widget, _pspec=None):
        """ Function doc """
        system_id = self.combobox_systems.get_system_id()
       
        if system_id is not None:
            self.coordinates_combobox.set_model(self.main_session.vobject_liststore_dict[system_id])
            self.refresh_selection_liststore (system_id)            
            size  =  self.main_session.vobject_liststore_dict[system_id].get_n_items()
            self.coordinates_combobox.set_selected(size-1)

        
    def on_treeview_Objects_row_activated(self, tree, position):
        system_id = self.combobox_systems.get_system_id()
        model = self.treeview.get_model().get_item(position)
        if model is None:
            return
        
        key = model.name
        indexes = self.p_session.psystem[system_id].e_selections[key] 
        coords_cb_index = self.coordinates_combobox.get_selected()
        if coords_cb_index == GTK_INVALID_LIST_POSITION:
            return
        
        #_, e_id          = self.main_session.system_liststore[sys_names_cb_index]
        coordinate_row = self.main_session.vobject_liststore_dict[system_id].get_item(coords_cb_index)
        vobj_id = coordinate_row.object_id
        e_id = coordinate_row.system_id
        

        vobject = self.vm_session.vm_objects_dic[vobj_id]
        self.vm_session.selections[self.vm_session.current_selection].selecting_by_indexes (vismol_object = vobject, indexes = indexes, clear = True)
        self.vm_session.selections[self.vm_session.current_selection].active = True
                
        self.vm_session.vm_glcore.queue_draw()
        
    
    def on_treeview_Objects_button_release_event(self, gesture, _n_press, x, y):
        '''
         str  ,   #                                   # 0
         bool ,   # toggle active=1                   # 1
         bool ,   # toggle visible = 3                # 2 
                                                      
         bool ,   # radio  active  = 2                # 3 
         bool ,   # radio  visible = 4                # 4 
                                                      
         bool  ,  # traj radio  active = 5            # 5 
         bool  ,  # is trajectory radio visible?      # 6 
                                                      
         int,     #                                   # 7
         int,     # pdynamo system index              # 8
         int,)    # frames  # 9
        '''
        
        
        system_id = self.combobox_systems.get_system_id()
            
            
        if gesture.get_current_button() == 3:
            selected = self.tree_selection.get_selected_item()
            if selected is not None:
                self.treeview_menu.open_menu(selected, system_id, x, y)

        if gesture.get_current_button() == 1:
            dprint ('event.button == 1:')



class SelectionContextMenu:
    """Context actions for the selected restraint selection."""
    
    def __init__ (self, sele_window):
        """ Class initialiser """
        pass
        self.treeview = sele_window.treeview
        self.p_session = sele_window.p_session
        self.sele_window = sele_window 
        functions = {
                    'Rename'                : self.print_test ,
                    'Delete'                : self.delete_system ,
                    }
        self.build_tree_view_menu(functions)
        self.rename_window_visible = False

    def print_test (self, menu_item = None ):
        """  
        """
        if self.rename_window_visible:
            pass
        else:
            #
            self.e_id = self.sele_window.combobox_systems.get_system_id()
            model = self.sele_window.tree_selection.get_selected_item()
            if model is None:
                return
            self.key = model.name
            
            dprint(self.key, self.e_id)
            self.window = Gtk.Window()
            self.window.connect('close-request', self.destroy)
            self.entry  = Gtk.Entry()
            
            self.entry.connect('activate', self.rename)
            self.window.set_child(self.entry)
            self.rename_window_visible = True
            self.window.present()
            dprint(menu_item)

    def rename (self, menu_item):
        """ Function doc """
        dprint(self.entry.get_text())
        new_name = self.entry.get_text()
        pass
        
        
        self.p_session.psystem[self.e_id].e_selections[new_name] = self.p_session.psystem[self.e_id].e_selections[self.key]
        self.p_session.psystem[self.e_id].e_selections.pop(self.key)
        self.sele_window.update_window()
        self.window.destroy()
        self.rename_window_visible = False
        
    def destroy (self, widget):
        """ Function doc """
        self.rename_window_visible = False

    def delete_system (self, menu_item = None ):
        """ Function doc """
        model = self.sele_window.tree_selection.get_selected_item()
        if model is None:
            return


        self.p_session.psystem[self.system_id].e_selections.pop(model.name)
        #print ('deleting',sele)
        #print ('selections', self.p_session.systems[self.system_id]['selections'])
        self.sele_window.update_window (system_names = False, coordinates = False,  selections = True )


    def build_tree_view_menu (self, menu_items = None):
        """Build a GTK4 popover menu attached to the restraint tree."""
        self.tree_view_menu = append_mapping(ContextMenu(self.treeview), menu_items)

    
    def open_menu (self, vobject = None, system_id = None, x=0, y=0):
        """ Function doc """
        self.system_id = system_id
        #print (vobject)
        self.tree_view_menu.present(x=x, y=y)
