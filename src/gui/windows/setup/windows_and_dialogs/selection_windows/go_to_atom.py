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
from gi.repository import Gtk, Pango, Gio, GObject
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gui.gtk4_builder import connect_builder_signals
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
from types import SimpleNamespace


class NavigationResidueRow(GObject.Object):
    color = GObject.Property(type=GdkPixbuf.Pixbuf)
    index = GObject.Property(type=int, default=0)
    name = GObject.Property(type=str, default="")
    chain = GObject.Property(type=str, default="")
    size = GObject.Property(type=int, default=0)

    def __init__(self, color, index, name, chain, size):
        super().__init__()
        self.color, self.index, self.name = color, index, name
        self.chain, self.size = chain, size


class NavigationAtomRow(GObject.Object):
    color = GObject.Property(type=GdkPixbuf.Pixbuf)
    index = GObject.Property(type=int, default=0)
    name = GObject.Property(type=str, default="")
    atom_type = GObject.Property(type=str, default="")
    charge = GObject.Property(type=float, default=0.0)
    atom_id = GObject.Property(type=int, default=0)

    def __init__(self, color, index, name, atom_type, charge, atom_id):
        super().__init__()
        self.color, self.index, self.name = color, index, name
        self.atom_type, self.charge, self.atom_id = atom_type, charge, atom_id

import traceback


VISMOL_HOME      = os.environ.get('VISMOL_HOME')
HOME             = os.environ.get('HOME')
PDYNAMO3_SCRATCH = os.environ.get('PDYNAMO3_SCRATCH')


class EasyHybridGoToAtomWindow(Gtk.Window):
    """Window for navigating through systems, residues, and atoms.

    This class provides a GTK4-based interface to select a molecular
    system, view chains, residues, and atoms, and perform visualization 
    actions such as centering and selecting.
    """
    def __init__(self, main = None, system_liststore = None):
        """Initialize the Go-To-Atom window.

        Args:
            main: Reference to the main application object.
            system_liststore: GTK ListStore containing the available systems.
        """
        
        self.main  = main
        self.vm_session    = self.main.vm_session
        self.p_session     = self.main.p_session
        self.system_liststore      = system_liststore
        self.residue_liststore = Gio.ListStore.new(NavigationResidueRow)
        self.atom_liststore = Gio.ListStore.new(NavigationAtomRow)
        self.residue_filter    = False
        self.visible           = False
        
        self.shift = False
        
        # Dictionary for assigning colors to residues.
        self.residues_dictionary = {
                               'WAT': [165,42,42], 
                               'SOL': [165,42,42], 
                               'HOH': [165,42,42], 
                               
                               'CYS': [207,40,168], 
                               'ASP': [128,0,128], 
                               'SER': [0, 128, 0], 
                               'GLN': [0, 128, 0], 
                               'LYS': [255, 0, 0],
                               'ILE': [30, 144, 255], 
                               'PRO': [255, 255,0], 
                               'THR': [0, 128, 0], 
                               'PHE': [6,176,176], 
                               'ASN': [0, 128, 0], 
                               'GLY': [255, 165,0], 
                               'HIS': [6,176,176], 
                               
                               # amber
                               "HID": [6,176,176],
                               "HIE": [6,176,176],
                               "HIP": [6,176,176],
                               "ASH": [0, 128, 0],
                               "GLH": [0, 128, 0],
                               "CYX": [207,40,168],
                               
                               # charmm
                               "HSD": [6,176,176], 
                               "HSE": [6,176,176], 
                               "HSP": [6,176,176], 
                               
                               
                               'LEU': [30, 144, 255], 
                               'ARG': [255, 0, 0], 
                               'TRP': [6,176,176], 
                               'ALA': [30, 144, 255], 
                               'VAL': [30, 144, 255], 
                               'GLU': [128,0,128], 
                               'TYR': [6,176,176], 
                               'MET': [30, 144, 255]}

    def open_window (self):
        """Open the Go-To-Atom window.

        Builds and displays the interface elements such as system 
        combobox, residue and chain lists, and atom treeviews.
        
        Args:
            main: Reference to the main application object.
            system_liststore: GTK ListStore containing the available systems.
        
        """
       
        #'''
        if self.visible  ==  False:
            
            #self.vm_session.Vismol_Objects_ListStore
            
            #------------------------------------------------------------------#
            #                  SYSTEM combobox and Label
            #------------------------------------------------------------------#
            self.box_vertical    = Gtk.Box(orientation = Gtk.Orientation.VERTICAL,   spacing = 10)
            self.box_horizontal1 = Gtk.Box(orientation = Gtk.Orientation.HORIZONTAL, spacing = 10)
             

            
            self.label1  = Gtk.Label()
            self.label1.set_text('System:')
            self.box_horizontal1.append(self.label1)
            self.label1.set_halign(Gtk.Align.CENTER)
            self.label1.set_valign(Gtk.Align.CENTER)

            self.combobox_systems = SystemComboBox(self.main)
            self.combobox_systems.connect("notify::selected", self.on_combobox_systems_changed)
            self.box_horizontal1.append(self.combobox_systems)
            self.combobox_systems.set_halign(Gtk.Align.CENTER)
            self.combobox_systems.set_valign(Gtk.Align.CENTER)
            #------------------------------------------------------------------#

            #------------------------------------------------------------------#
            #                  COORDINATES combobox and Label
            #------------------------------------------------------------------#
            self.label1  = Gtk.Label()
            self.label1.set_text('Coordinates:')
            self.box_horizontal1.append(self.label1)
            self.label1.set_halign(Gtk.Align.CENTER)
            self.label1.set_valign(Gtk.Align.CENTER)
            self.coordinates_combobox = CoordinatesComboBox(self.main.vobject_liststore_dict[self.main.p_session.active_id])
            
            self.box_horizontal1.append(self.coordinates_combobox)
            self.coordinates_combobox.set_halign(Gtk.Align.CENTER)
            self.coordinates_combobox.set_valign(Gtk.Align.CENTER)
            #------------------------------------------------------------------#
            

            #------------------------------------------------------------------#
            #                  CHAIN combobox and Label
            #------------------------------------------------------------------#
            self.box_horizontal2 = Gtk.Box(orientation = Gtk.Orientation.HORIZONTAL, spacing = 6)
            
            
            self.label2  = Gtk.Label()
            self.label2.set_text('Chain:')
            self.box_horizontal2.append(self.label2)
            self.label2.set_halign(Gtk.Align.CENTER)
            self.label2.set_valign(Gtk.Align.CENTER)

            self.liststore_chains = Gtk.StringList.new([])
            self.combobox_chains = Gtk.DropDown.new(self.liststore_chains, None)
            self.combobox_chains.connect("notify::selected", self.on_combobox_chains_changed)
            self.box_horizontal2.append(self.combobox_chains)
            self.combobox_chains.set_halign(Gtk.Align.CENTER)
            self.combobox_chains.set_valign(Gtk.Align.CENTER)
            

            #------------------------------------------------------------------#
            #                  RESIDUES combobox and Label
            #------------------------------------------------------------------#
            
            self.label3  = Gtk.Label()
            self.label3.set_text('Residue type:')
            self.box_horizontal2.append(self.label3)
            self.label3.set_halign(Gtk.Align.CENTER)
            self.label3.set_valign(Gtk.Align.CENTER)

            self.liststore_residues = Gtk.StringList.new([])
            self.combobox_residues = Gtk.DropDown.new(self.liststore_residues, None)
            self.combobox_residues.connect("notify::selected", self.on_combobox_residues_changed)
            self.box_horizontal2.append(self.combobox_residues)
            self.combobox_residues.set_halign(Gtk.Align.CENTER)
            self.combobox_residues.set_valign(Gtk.Align.CENTER)
            
            
            #------------------------------------------------------------------#
            self.treeviewbox_horizontal = Gtk.Box(orientation = Gtk.Orientation.HORIZONTAL, spacing = 6)
            #------------------------------------------------------------------------------------------
            
            
            #-----------------------------------------------------------------------------------------
            #                                      Chain filter
            #-----------------------------------------------------------------------------------------
            self.current_filter_chain = None
            self.residue_filter = Gtk.CustomFilter.new(self.residue_filter_func)
            self.chain_filter = Gtk.CustomFilter.new(self.chain_filter_func)
            self.filtered_residues = Gtk.FilterListModel.new(
                self.residue_liststore, self.chain_filter
            )
            self.filtered_residues = Gtk.FilterListModel.new(
                self.filtered_residues, self.residue_filter
            )
            #-----------------------------------------------------------------------------------------
            
            
            self.residue_selection = Gtk.MultiSelection.new(self.filtered_residues)
            self.treeview = Gtk.ColumnView.new(self.residue_selection)
            self.treeview.connect("activate", self.on_treeview_row_activated_event)
            keys = Gtk.EventControllerKey()
            keys.connect("key-pressed", self._on_key_pressed)
            keys.connect("key-released", self._on_key_released)
            self.treeview.add_controller(keys)

            for title, attribute in (("", "color"), ("index", "index"),
                                     ("Residue", "name"), ("Chain", "chain"),
                                     ("size", "size")):
                self.treeview.append_column(self._make_column(title, attribute))

            
            self.current_filter_chain = None

            self.scrollable_treelist = Gtk.ScrolledWindow()
            self.scrollable_treelist.set_vexpand(True)
            self.scrollable_treelist.set_child(self.treeview)
            #------------------------------------------------------------------------------------------
            


            #------------------------------------------------------------------------------------------
            self.atom_selection = Gtk.SingleSelection.new(self.atom_liststore)
            self.treeview_atom = Gtk.ColumnView.new(self.atom_selection)
            self.treeview_atom.connect("activate", self.on_treeview_atom_row_activated_event)

            for title, attribute in (("", "color"), ("index", "index"),
                                     ("name", "name"), ("MM atom", "atom_type"),
                                     ("MM charge", "charge")):
                self.treeview_atom.append_column(self._make_column(title, attribute))

            self.scrollable_treelist2 = Gtk.ScrolledWindow()
            self.scrollable_treelist2.set_vexpand(True)
            self.scrollable_treelist2.set_child(self.treeview_atom)
            #------------------------------------------------------------------------------------------
            
            
            self.box_vertical.append(self.box_horizontal1)
            self.box_vertical.append(self.box_horizontal2)
            self.treeviewbox_horizontal.append(self.scrollable_treelist)
            self.scrollable_treelist.set_hexpand(True)
            self.scrollable_treelist.set_vexpand(True)
            self.treeviewbox_horizontal.append(self.scrollable_treelist2)
            self.scrollable_treelist2.set_hexpand(True)
            self.scrollable_treelist2.set_vexpand(True)
            
            self.box_vertical.append(self.treeviewbox_horizontal)
            
            
            self.combobox_systems.set_selected(0)
            self.window =  Gtk.Window()
            self.window.set_margin_top(10)
            self.window.set_margin_bottom(10)
            self.window.set_margin_start(10)
            self.window.set_margin_end(10)
            self.window.set_default_size(600, 600)  
            self.window.set_child(self.box_vertical)
            self.window.connect("close-request", self.close_window)
            self.window.set_title('Go to Atom Window') 
            self.window.present() 
                                                          
            #                                                                
            #connect_builder_signals(self.builder, self)                                   
            
            self.visible  =  True
            #----------------------------------------------------------------
        else:
            self.window.present()
        #'''
    def close_window (self, button):
        """ Function doc """
        self.window.destroy()
        self.visible    =  False
        return True

    def getColouredPixmap( self, r, g, b, a=255 ):
        """ Given components, return a colour swatch pixmap """
        CHANNEL_BITS=8
        WIDTH=10
        HEIGHT=10
        swatch = GdkPixbuf.Pixbuf.new( GdkPixbuf.Colorspace.RGB, True, CHANNEL_BITS, WIDTH, HEIGHT ) 
        swatch.fill( (r<<24) | (g<<16) | (b<<8) | a ) # RGBA
        return swatch

    @staticmethod
    def _make_column(title, attribute):
        factory = Gtk.SignalListItemFactory()
        if attribute == "color":
            factory.connect("setup", lambda _factory, item: item.set_child(Gtk.Image()))
            factory.connect("bind", lambda _factory, item: item.get_child().set_from_pixbuf(
                getattr(item.get_item(), attribute)
            ))
        else:
            factory.connect("setup", lambda _factory, item: item.set_child(Gtk.Label(xalign=0)))
            factory.connect("bind", lambda _factory, item: item.get_child().set_text(
                str(getattr(item.get_item(), attribute))
            ))
        return Gtk.ColumnViewColumn.new(title, factory)

    def refresh (self, option = 'all'):
        """ Function doc """
        self.update_window()
    
    def update_window (self, system_names = False, coordinates = True,  selections = False ):
        """ Function doc """

        if self.visible:
            
            _id = self.combobox_systems.get_selected()
            if _id == -1:
                '''_id = -1 means no item inside the combobox'''
                return None
            else:    
                system_id = self.system_liststore.get_item(_id).system_id
            
            if system_names:
                self.refresh_system_liststore ()
                self.combobox_systems.set_selected(_id)
            
            if coordinates:
                self.refresh_coordinates_liststore ()
                
            
            #if selections:
            #    _, system_id = self.system_liststore[_id]
            #    self.refresh_selection_liststore(system_id)
        else:
            if system_names:
                self.refresh_system_liststore ()
            if coordinates:
                self.refresh_coordinates_liststore ()
            
    def refresh_coordinates_liststore(self, system_id = None):
        """
        Refreshes the coordinates ListStore associated with the currently selected system.

        This method updates the model of the coordinates_combobox with the ListStore corresponding 
        to the system currently selected in the systems combobox. It then resets the active selection 
        in the coordinates_combobox to a default state (-1), which typically means no selection.

        Parameters
        ----------
        system_id : optional
            Not used directly; the selected system ID is obtained from the combobox.
        """
        # Override any passed system_id with the ID obtained from the combobox.
        system_id = self.combobox_systems.get_system_id()

        # Update the coordinates combobox model with the ListStore for the selected system.
        # vobject_liststore_dict  maps system IDs to their associated ListStore objects.
        self.coordinates_combobox.set_model(self.main.vobject_liststore_dict[system_id])

        # Reset the active selection in the coordinates combobox. -1 typically indicates no selection.
        self.coordinates_combobox.set_active_vobject(-1)

    def refresh_system_liststore (self):
        """ Function doc """

    def on_combobox_residues_changed(self, widget, _pspec=None):
        selected = widget.get_selected_item()
        self.current_filter_residue = selected.get_string() if selected else None
        self.residue_filter.changed(Gtk.FilterChange.DIFFERENT)

    def on_combobox_chains_changed(self, widget, _pspec=None):
        selected = widget.get_selected_item()
        self.current_filter_chain = selected.get_string() if selected else None
        self.chain_filter.changed(Gtk.FilterChange.DIFFERENT)

    def _build_chain_liststore(self):
        self.liststore_chains = Gtk.StringList.new(['all'])
        for chain in self.vobject.chains.keys():
            self.liststore_chains.append(chain)
        self.combobox_chains.set_model(self.liststore_chains)
        self.combobox_chains.set_selected(0)

    def _build_res_liststore(self):
        self.residue_liststore.remove_all()
        for chain in self.vobject.chains:
            for index, residue in self.vobject.chains[chain].residues.items():
                color = self.vobject.color_palette['C']
                swatch = self.getColouredPixmap(*(int(component * 255) for component in color))
                self.residue_liststore.append(NavigationResidueRow(
                    swatch, index, residue.name, chain, len(residue.atoms)
                ))

    def on_combobox_systems_changed(self, widget, _pspec=None):
        system_id = widget.get_system_id()
        if system_id is None:
            return
        self.refresh_coordinates_liststore()
        object_id = self.coordinates_combobox.get_vobject_id()
        if object_id is None:
            return
        self.vobject = self.vm_session.vm_objects_dic[object_id]
        self._build_chain_liststore()
        self._build_res_liststore()

        self.current_filter_chain = None
        self.current_filter_residue = None
        chains_filter = Gtk.CustomFilter.new(self.chain_filter_func)
        residue_filter = Gtk.CustomFilter.new(self.residue_filter_func)
        chain_model = Gtk.FilterListModel.new(self.residue_liststore, chains_filter)
        filtered_model = Gtk.FilterListModel.new(chain_model, residue_filter)
        self.chain_filter = chains_filter
        self.residue_filter = residue_filter
        self.filtered_residues = filtered_model
        self.residue_selection.set_model(filtered_model)

        residue_names = {"all"}
        for chain in self.vobject.chains.values():
            residue_names.update(residue.name for residue in chain.residues.values())
        self.liststore_residues = Gtk.StringList.new(sorted(residue_names))
        self.combobox_residues.set_model(self.liststore_residues)
        self.combobox_residues.set_selected(0)

    def _populate_atoms_for_residue(self, residue):
        system = self.p_session.psystem[self.vobject.e_id]
        try:
            charges = list(system.mmState.charges)
            atom_types = system.mmState.atomTypes
            atom_type_indices = list(system.mmState.atomTypeIndices)
        except Exception:
            charges = [0.0] * len(system.atoms)
            atom_types = ['-'] * len(system.atoms)
            atom_type_indices = [atom.index for atom in system.atoms.items]

        self.atom_liststore.remove_all()
        for atom in residue.atoms.values():
            color = self.vobject.color_palette[atom.symbol]
            swatch = self.getColouredPixmap(*(int(component * 255) for component in color))
            self.atom_liststore.append(NavigationAtomRow(
                swatch, int(atom.index), str(atom.name),
                str(atom_types[atom_type_indices[atom.index - 1]]),
                charges[atom.index - 1], int(atom.atom_id),
            ))
        residue.get_center_of_mass(frame=self.vm_session.get_frame())
        self.vm_session.vm_glcore.center_on_coordinates(residue.vm_object, residue.mass_center)

    def on_treeview_row_activated_event(self, view, position):
        row = self.filtered_residues.get_item(position)
        if row is None:
            return
        self.selectedID, self.selectedObj, self.selectedChn = row.index, row.name, row.chain
        residue = self.vobject.chains[row.chain].residues[row.index]
        self._populate_atoms_for_residue(residue)
        if self.shift:
            for chain in self.vobject.chains.values():
                for candidate in chain.residues.values():
                    if candidate.name == residue.name and candidate.atoms:
                        self.vm_session._selection_function_set({next(iter(candidate.atoms.values()))})
        elif residue.atoms:
            self.vm_session._selection_function_set({next(iter(residue.atoms.values()))})
        self.vm_session.vm_glcore.updated_coords = True
        self.vm_session.vm_glcore.queue_draw()

    def on_treeview_atom_row_activated_event(self, view, position):
        row = self.atom_liststore.get_item(position)
        if row is None:
            return
        atom = self.vobject.atoms[row.atom_id]
        selection = self.vm_session.selections[self.vm_session.current_selection]
        selection.selecting_by_atom([atom], True)
        selection._build_selected_atoms_coords_and_selected_objects_from_selected_atoms()
        self.vm_session.vm_glcore.queue_draw()

    def on_treeview_Objects_button_release_event(self, _tree, _event):
        return

    def on_treeview_atom_button_release_event(self, _tree, _event):
        return

    def residue_filter_func(self, row, _data=None):
        return self.current_filter_residue in (None, "all", row.name)

    def chain_filter_func(self, row, _data=None):
        return self.current_filter_chain in (None, "all", row.chain)

    def update (self):
        """ Function doc """
        #print('VismolGoToAtomWindow2 update')
        pass

    def key_pressed  (self, widget, event):
        key = Gdk.keyval_name(event.keyval)
        
        if key == 'Shift_R' or key == 'Shift_L':
            self.shift = True
        dprint(widget, event, Gdk.keyval_name(event.keyval), self.shift)
    
    def key_released (self, widget, event):
        key = Gdk.keyval_name(event.keyval)
        if key == 'Shift_R' or key == 'Shift_L':
            self.shift = False
        dprint(widget, event, Gdk.keyval_name(event.keyval), self.shift)

    def _on_treeview_released(self, gesture, _n_press, _x, _y):
        self.on_treeview_Objects_button_release_event(
            gesture.get_widget(),
            SimpleNamespace(button=gesture.get_current_button()),
        )

    def _on_atom_treeview_released(self, gesture, _n_press, _x, _y):
        self.on_treeview_atom_button_release_event(
            gesture.get_widget(),
            SimpleNamespace(button=gesture.get_current_button()),
        )

    def _on_key_pressed(self, controller, keyval, _keycode, _state):
        self.key_pressed(controller.get_widget(), SimpleNamespace(keyval=keyval))
        return False

    def _on_key_released(self, controller, keyval, _keycode, _state):
        self.key_released(controller.get_widget(), SimpleNamespace(keyval=keyval))
