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
from gi.repository import Gio, Gtk, GObject
from gui.gtk4_builder import connect_builder_signals, load_builder_file, load_builder_string
#from GTKGUI.gtkWidgets.filechooser import FileChooser
#from easyhybrid.pDynamoMethods.pDynamo2Vismol import *
import gc
import os

from gui.widgets.custom_widgets import SystemComboBox
from gui.widgets.custom_widgets import CoordinatesComboBox
from gui.gtk4_context_menu import ContextMenu, append_mapping
from gui.windows.setup.windows_and_dialogs  import AddHarmonicRestraintDialog
VISMOL_HOME = os.environ.get('VISMOL_HOME')
HOME        = os.environ.get('HOME')


class SelectionRow(GObject.Object):
    name = GObject.Property(type=str, default="")
    atom_count = GObject.Property(type=int, default=0)

    def __init__(self, name, atom_count):
        super().__init__()
        self.name = name
        self.atom_count = atom_count


class RestraintRow(GObject.Object):
    active = GObject.Property(type=bool, default=True)
    name = GObject.Property(type=str, default="")
    restraint_type = GObject.Property(type=str, default="")
    atoms = GObject.Property(type=str, default="")
    value = GObject.Property(type=str, default="")
    force_constant = GObject.Property(type=str, default="")
    system_id = GObject.Property(type=int, default=-1)

    def __init__(self, active, name, restraint_type, atoms, value,
                 force_constant, system_id):
        super().__init__()
        self.active = active
        self.name = name
        self.restraint_type = restraint_type
        self.atoms = atoms
        self.value = value
        self.force_constant = force_constant
        self.system_id = system_id


class SelectionListWindow(Gtk.Window):
    """ Class doc """
    def __init__(self, main = None, system_liststore = None ):
        """ Class initialiser """
        self.main_session          = main#self.main_session.system_liststore
        self.home                  = main.home
        self.visible               = False        
        self.p_session             = main.p_session
        self.vm_session            = main.vm_session
        

        
        self.selection_liststore = Gio.ListStore.new(SelectionRow)
    
        #-------------------------------------------
        # - - - - - - - - Restraints - - - - - - - - 
        #-------------------------------------------
        self.restraint_types = {0 : 'distance',
                                #1 : 'angle',
                                #2 : 'dihedral',
                                3 : 'all'
                                }
        self.restraint_liststore = Gio.ListStore.new(RestraintRow)
        #--------------------------------------------
    def open_window (self):
        """ Function doc ~/programs/VisMol/easyhybrid/gui/selection_list.glade"""
        if self.visible  ==  False:
            self.builder = Gtk.Builder()
            load_builder_file(self.builder, os.path.join(self.home,'src/gui/windows/setup/selection_and_restraint_list.glade'))
            connect_builder_signals(self.builder, self)
            
            self.window = self.builder.get_object('window')
            self.window.set_default_size(200, 600)  
            self.window.set_title('Selections')  
            
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


            system = self.main_session.p_session.get_system()
            if system:
                self.combobox_systems.set_active_system(system.e_id)
            


            # - - - - - - - Selection Treeview - - - - - - -
            '''--------------------------------------------------------------------------------------------'''
            self.treeview = self.builder.get_object('selection_treeview')
            self.selection_selection = Gtk.SingleSelection.new(self.selection_liststore)
            self.treeview.set_model(self.selection_selection)
            self._append_text_column(self.treeview, "Selection", "name")
            self._append_text_column(self.treeview, "Number of Atoms", "atom-count")
            self.treeview.connect('activate', self.on_treeview_Objects_row_activated)
            click = Gtk.GestureClick()
            click.set_button(0)
            click.connect("released", self.on_treeview_Objects_button_release_event)
            self.treeview.add_controller(click)
            '''--------------------------------------------------------------------------------------------'''

            
            
            #---------------------------------------------------------------------------------
            #                - - - - - - - Restraint Treeview - - - - - - -
            #---------------------------------------------------------------------------------
            self.restraint_treeview = self.builder.get_object('restraint_treeview')
            self.restraint_selection = Gtk.SingleSelection.new(self.restraint_liststore)
            self.restraint_treeview.set_model(self.restraint_selection)
            self.restraint_treeview.connect("activate", self.on_restraint_treeview_row_activated)
            click = Gtk.GestureClick()
            click.set_button(0)
            click.connect("released", self.on_restraint_treeview_button_release_event)
            self.restraint_treeview.add_controller(click)
            self._append_toggle_column(self.restraint_treeview, "A", "active")
            for title, prop in (("Index", "name"), ("Type", "restraint-type"),
                                ("Atoms", "atoms"), ("Dist/Angle", "value"),
                                ("Force Constant", "force-constant")):
                self._append_text_column(self.restraint_treeview, title, prop)
            #---------------------------------------------------------------------------------
            
            
            
            
            #---------------------------------------------------------------------------------
            #                           Restraints COMBOBOX
            #---------------------------------------------------------------------------------
            self.comobobox_restraints = self.builder.get_object('combobox_restraints')
            restraint_type_names = Gtk.StringList.new(
                list(self.restraint_types.values())
            )
            self.comobobox_restraints.set_model(restraint_type_names)
            self.comobobox_restraints.set_selected(0)
            self.comobobox_restraints.connect(
                "notify::selected", self._on_rest_types_changed
            )
            #self.restraint_treeview.connect('row_activated', self.on_treeview_Objects_row_activated )
            #self.restraint_treeview.connect('button-release-event', self.on_treeview_Objects_button_release_event )
            '''--------------------------------------------------------------------------------------------'''



            #self.refresh_system_liststore()
            self.treeview_menu           = TreeViewMenu(self)
            self.restraint_treeview_menu = RestraintTreeViewMenu(self)
            self.window.present()                                               
            #self.combobox_systems.set_selected(0)
            
            #------------------------------------------------------------------------------------------------
            if self.p_session.psystem[self.p_session.active_id]:
                active_id = self.p_session.active_id
                self.combobox_systems.set_active_system (e_id = active_id)
            #------------------------------------------------------------------------------------------------
            
            self.visible    =  True
            '''--------------------------------------------------------------------------------------------'''
            self.update_window()
        else:
            self.window.present()
            
    def close_window (self, button, data  = None):
        """ Function doc """
        #self.BackUpWindowData()
        self.window.destroy()
        self.visible    =  False
        return True

    def _append_text_column(self, view, title, property_name):
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._setup_text_cell)
        factory.connect("bind", self._bind_text_cell, property_name)
        column = Gtk.ColumnViewColumn.new(title, factory)
        column.set_expand(True)
        view.append_column(column)

    @staticmethod
    def _setup_text_cell(_factory, list_item):
        label = Gtk.Label(xalign=0)
        list_item.set_child(label)

    @staticmethod
    def _bind_text_cell(_factory, list_item, property_name):
        row = list_item.get_item()
        list_item.get_child().set_text(str(getattr(row, property_name.replace("-", "_"))))

    def _append_toggle_column(self, view, title, property_name):
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._setup_toggle_cell)
        factory.connect("bind", self._bind_toggle_cell, property_name)
        factory.connect("unbind", self._unbind_toggle_cell)
        view.append_column(Gtk.ColumnViewColumn.new(title, factory))

    def _setup_toggle_cell(self, _factory, list_item):
        check = Gtk.CheckButton()
        check._updating_row = False
        check._restraint_row = None
        check.connect("toggled", self._on_cell_visible_toggled)
        list_item.set_child(check)

    @staticmethod
    def _bind_toggle_cell(_factory, list_item, property_name):
        check = list_item.get_child()
        row = list_item.get_item()
        check._updating_row = True
        check._restraint_row = row
        check.set_active(getattr(row, property_name.replace("-", "_")))
        check._updating_row = False

    @staticmethod
    def _unbind_toggle_cell(_factory, list_item):
        check = list_item.get_child()
        check._restraint_row = None

    def _on_rest_types_changed (self, widget, _pspec=None):
        """ Function doc """
        dprint(self.comobobox_restraints.get_selected())

    def on_restraint_treeview_button_release_event (self, gesture, _n_press, x, y):
        """ Function doc """
        if gesture.get_current_button() == 3:
            row = self.restraint_selection.get_selected_item()
            if row is not None:
                self.restraint_treeview_menu.open_menu(row, x, y)

        if gesture.get_current_button() == 1:
            pass
            #print ('event.button == 1:')

    def on_restraint_treeview_row_activated(self, treeview, position):
        """ Function doc """
        row = self.restraint_liststore.get_item(position)
        if row is not None:
            dprint(f"Double click on row: {row.name} (ID={row.system_id})")

    def _on_cell_visible_toggled(self, widget):
        """ 
            This function changes the status of the 
            check box for each item, in this case,
            each item corresponds to a constraint.

            system.e_restraints_dict <- stores the constraints
        """
        if widget._updating_row or widget._restraint_row is None:
            return
        row = widget._restraint_row
        row.active = widget.get_active()
        e_id = row.system_id
        name = row.name
        system = self.main_session.p_session.psystem[e_id]
        system.e_restraints_dict[name][0] = row.active
        dprint(system.e_restraints_dict)
        self.p_session.update_restaint_representation(e_id)

    def update_window (self, system_names = True, coordinates = False,  selections = True, restraints = True):
        """ Function doc """
        if self.visible:
            
            system_id = self.combobox_systems.get_system_id()
            if system_id is not None:
                if selections:
                    self.refresh_selection_liststore(system_id)
                if restraints:
                    self.refresh_restraint_liststore(system_id)
        else:
            self.refresh_restraint_liststore(self.main_session.p_session.active_id)
    
    def update (self, system_names = True, coordinates = False,  selections = True ):
        """ Function doc """
        pass

    def refresh_system_liststore (self):
        """ Function doc """
        self.main_session.refresh_system_liststore()

    def refresh_restraint_liststore (self, system_id = None):
        """ Function doc """
        rows = []
        for name, restraint in self.p_session.psystem[system_id].e_restraints_dict.items():
            _bool = restraint[0]
            name  = restraint[1]
            _type = restraint[2]
            if _type == 'distance':
                atons = '{} / {}'.format(restraint[3][0],restraint[3][1])
                dist_or_angle = '{:.4f}'.format(restraint[4])
            
            elif _type == 'position':
                atons = '{}'.format(len(restraint[3]))
                dist_or_angle = '{}'.format('dynamic')
            
            force_const   = str(restraint[5])
            e_id          =  restraint[6] 
                                           #(bool,  str,   str,   str,          str,       str    , int    )
            rows.append(RestraintRow(
                _bool, name, _type, atons, dist_or_angle, force_const, e_id
            ))

        self.restraint_liststore.splice(
            0, self.restraint_liststore.get_n_items(), rows
        )
            
        self.p_session.update_restaint_representation(system_id)
        self.main_session.vm_session.vm_glcore.queue_draw()

    def refresh_selection_liststore (self, system_id = None ):
        """ Function doc """
        rows = []
        
        ''' QC atoms'''
        if self.p_session.psystem[system_id].qcModel:
            self.p_session.psystem[system_id].e_selections["QC atoms"] = list(self.p_session.psystem[system_id].qcState.pureQCAtoms)


        '''Fixed atoms'''
        if self.p_session.psystem[system_id].freeAtoms is None:
            pass
        
        else:
            self.p_session.psystem[system_id].e_selections["fixed atoms"] = self.p_session.get_fixed_atoms_from_system(self.p_session.psystem[system_id])
  
        
        for selection , indexes in self.p_session.psystem[system_id].e_selections.items():
            rows.append(SelectionRow(selection, len(indexes)))
        self.selection_liststore.splice(
            0, self.selection_liststore.get_n_items(), rows
        )
    
    def on_combobox_systemsbox_changed(self, widget, _pspec=None):
        """ Function doc """
        system_id = self.combobox_systems.get_system_id()
       
        if system_id is not None:
            self.coordinates_combobox.set_model(self.main_session.vobject_liststore_dict[system_id])
            self.refresh_selection_liststore (system_id)            
            size  =  self.main_session.vobject_liststore_dict[system_id].get_n_items()
            self.coordinates_combobox.set_selected(size-1)
            
            self.update_window ( selections = False, restraints = True)
        
    def on_treeview_Objects_row_activated(self, tree, position):
        
        system_id = self.combobox_systems.get_system_id()
        
        row = self.selection_liststore.get_item(position)
        if row is None:
            return
        
        '''
        "key" is the acesses key to the dictionary containg the selection lists
        there is no two selection lists with the same name.
        indexes =  A list of atoms for selection
        '''
        key = row.name
        indexes = self.p_session.psystem[system_id].e_selections[key] 
        #print(self.p_session.psystem[system_id].e_qc_table)
        #print(self.p_session.psystem[system_id].e_selections)
        
        #pymol_indexes = []
        #for i in indexes:
        #    pymol_indexes.append(i+1)
        #print(pymol_indexes)
        
        '''
        first we have to get the indexes from the comboboxes. These indexes are 
        not the same access keys as system or vobject, they are just the 
        positions in the respective liststores
        '''
        sys_names_cb_index = self.combobox_systems.get_selected()
        coords_cb_index    = self.coordinates_combobox.get_selected()
        
        
        #_, e_id          = self.main_session.system_liststore[sys_names_cb_index]
        coordinate_row = self.main_session.vobject_liststore_dict[system_id].get_item(coords_cb_index)
        vobj_id = coordinate_row.object_id
        e_id = coordinate_row.system_id
        

        '''----------------------------- Applying the selection ------------------------------------'''
        vobject = self.vm_session.vm_objects_dic[vobj_id]
        self.vm_session.selections[self.vm_session.current_selection].selecting_by_indexes (vismol_object = vobject, indexes = indexes, clear = True)
        self.vm_session.selections[self.vm_session.current_selection].active = True
        '''-----------------------------------------------------------------------------------------'''
                
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
            row = self.selection_selection.get_selected_item()
            if row is not None:
                self.treeview_menu.open_menu(row, system_id, x, y)

        if gesture.get_current_button() == 1:
            dprint ('event.button == 1:')



class RestraintTreeViewMenu:
    """ Class doc """
    
    def __init__ (self, sele_window):
        """ Class initialiser """
        #self.restraint_treeview
        self.treeview = sele_window.restraint_treeview
        self.p_session = sele_window.p_session
        self.sele_window = sele_window 
        functions = {
                    'Edit'                : self.edit ,
                    'Delete'                : self.delete ,
                    }
        self.build_tree_view_menu(functions)
        #self.rename_window_visible = False
    
    def build_tree_view_menu (self, menu_items = None):
        """Build a GTK4 popover menu attached to the selection tree."""
        self.tree_view_menu = append_mapping(ContextMenu(self.treeview), menu_items)

    
    def open_menu(self, row, x=0, y=0):
        """ Function doc """
        self.system_id = row.system_id
        self.restraint_id = row.name
        #print(self.p_session.psystem[self.system_id].e_restraints_dict)
        #print(self.p_session.psystem[self.system_id].e_restraints_dict[self.restraint_id])
        
        #print (model[iter][0])
        #self.system_id = system_id
        #print (vobject)
        self.tree_view_menu.present(x=x, y=y)

    def edit (self, menu_item):
        """ Function doc """
        
        restraint = self.p_session.psystem[self.system_id].e_restraints_dict[self.restraint_id]
        #
        # it returns something like: 
        # [True, '0', 'distance', [2326, 3457], 1.0, 4000.0, 1], '1': [True, '1', 'distance', [3457, 3456], 1.0, 4000.0, 1]
        #
        atom1 = restraint[3][0]
        atom2 = restraint[3][1]
        
        dist  = restraint[4] 
        force = restraint[5]
        add_harmonic_restraint_dialog =  AddHarmonicRestraintDialog(main      = self.sele_window.main_session, 
                                                                    atom1     = atom1, 
                                                                    atom2     = atom2, 
                                                                    distance  = dist , 
                                                                    force     = force,
                                                                    system_id = self.system_id,
                                                                    edit      = True,
                                                                    on_complete=self._finish_edit)

    def _finish_edit(self, dialog):
        if dialog.ok:
            self.p_session.psystem[self.system_id].e_restraints_dict[self.restraint_id][4] = float(dialog.dist)
            self.p_session.psystem[self.system_id].e_restraints_dict[self.restraint_id][5] = float(dialog.force)
            self.sele_window.refresh_restraint_liststore(system_id=self.system_id)
        pass
        #print('edit')
        #new_name = self.entry.get_text()
        #self.p_session.psystem[self.e_id].e_selections[new_name] = self.p_session.psystem[self.e_id].e_selections[self.key]
        #self.p_session.psystem[self.e_id].e_selections.pop(self.key)
        #self.sele_window.update_window()
        #self.window.destroy()
        #self.rename_window_visible = False
        
    def delete (self, menu_item = None):
        """ Function doc """
        
        self.p_session.psystem[self.system_id].e_restraints_dict.pop(self.restraint_id)
        dprint(self.p_session.psystem[self.system_id].e_restraints_dict)
        self.sele_window.refresh_restraint_liststore ( system_id = self.system_id)
        #print('delete')

class TreeViewMenu:
    """ Class doc """
    
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
            row = self.sele_window.selection_selection.get_selected_item()
            if row is None:
                return
            self.key = row.name
            
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
        row = self.sele_window.selection_selection.get_selected_item()
        if row is None:
            return
        self.p_session.psystem[self.system_id].e_selections.pop(row.name)
        #print ('deleting',sele)
        #print ('selections', self.p_session.systems[self.system_id]['selections'])
        self.sele_window.update_window (system_names = False, coordinates = False,  selections = True )


    def build_tree_view_menu (self, menu_items = None):
        """Build a GTK4 popover menu attached to the selection tree."""
        self.tree_view_menu = append_mapping(ContextMenu(self.treeview), menu_items)

    
    def open_menu(self, row, system_id=None, x=0, y=0):
        """ Function doc """
        self.system_id = system_id
        self.key = row.name
        self.tree_view_menu.present(x=x, y=y)
