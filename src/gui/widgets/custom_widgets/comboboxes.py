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
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk
from src.gtk4_compat import GTK_INVALID_LIST_POSITION
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gui.model_rows import CoordinateChoiceRow, SystemChoiceRow
import os

import threading
import time

from util.geometric_analysis            import get_distance 
from util.geometric_analysis            import get_dihedral 
from util.geometric_analysis            import get_angle 
#from util.periodic_table import atomic_dic 

from util.sequence_plot import GtkSequenceViewer
from pprint import pprint

import numpy as np

class SystemComboBox(Gtk.DropDown):
    """
    A custom GTK4 ComboBox widget for selecting a system from the application's
    available systems. Supports optional linkage to a coordinates combobox.
    """
    
    def __init__(self, main=None, coord_combobox=False):
        """
        Initialize the SystemComboBox instance.

        Parameters:
        main : object
            Reference to the main application object, which provides access
            to the global system liststore and other resources.
        coord_combobox : bool
            Flag indicating whether this combobox is linked to a coordinates
            combobox for updating available coordinate sets when the system changes.
        """
        # Initialize the native GTK4 dropdown.
        Gtk.DropDown.__init__(self)
        
        self.main = main  # Reference to main application object
        
        # Set the model for the combobox using the main application's system liststore
        self.system_liststore = self.main.system_liststore
        self.set_model(self.system_liststore)
        self.set_expression(Gtk.PropertyExpression.new(SystemChoiceRow, None, "name"))
        self.connect("notify::selected", self.on_change)
        
        # Store whether this combobox should update a coordinates combobox
        self.coord_combobox = coord_combobox
    
    def get_system_id(self, widget = None):
        row = self.get_selected_item()
        return row.system_id if row is not None else None
    
    def get_system_name(self, widget = None):
        row = self.get_selected_item()
        return row.name if row is not None else None
        
    def set_active_system (self, e_id = 0):
        """ Function doc """
        
        for position in range(self.system_liststore.get_n_items()):
            row = self.system_liststore.get_item(position)
            if row.system_id == int(e_id):
                self.set_selected(position)
                return
        self.set_selected(GTK_INVALID_LIST_POSITION)

    def on_change(self, widget, _pspec=None):
        """ Function doc """
        #print('AQUI', self.coord_combobox)
        
        if self.coord_combobox:
            system_id = self.get_system_id()
            if system_id is not None:
                self.coord_combobox.set_model(self.main.vobject_liststore_dict[system_id])
                size = self.main.vobject_liststore_dict[system_id].get_n_items()
                self.coord_combobox.set_active_vobject(size - 1)
        else:
            pass


class CoordinatesComboBox(Gtk.DropDown):
    """
    A custom GTK4 ComboBox widget for selecting a coordinate set (vobject) associated
    with a molecular or simulation system. Supports optional pixbuf icons for visual
    representation.
    """
    
    def __init__(self, coordinates_liststore=None, system_combobox=None, pixbuf=True):
        """
        Initialize the CoordinatesComboBox instance.

        Parameters:
        coordinates_liststore : Gio.ListModel
            The Gio.ListModel containing coordinate choices.
        system_combobox : SystemComboBox or None
            Optional reference to the system combobox this coordinates combobox is linked to.
            Can be used to update the coordinates dynamically when the system changes.
        pixbuf : bool
            Kept for API compatibility with callers that request coordinate icons.
        """
        # Initialize the native GTK4 dropdown.
        Gtk.DropDown.__init__(self)
        
        # Set the Gio.ListModel containing coordinate choices.
        self.coordinates_liststore = coordinates_liststore
        self.set_model(self.coordinates_liststore)
        
        self.set_expression(
            Gtk.PropertyExpression.new(CoordinateChoiceRow, None, "name")
        )

    def get_vobject(self):
        """
        Retrieve the currently selected vobject (coordinate object) from the combobox.

        Returns:
        tuple
            Information about the selected coordinate set, typically including:
            - name: The display name of the vobject
            - key1: Primary identifier (e.g., system ID)
            - key2: Secondary identifier (e.g., coordinate set ID)
            - pixbuf: Optional icon associated with the vobject
        """
        return self.get_selected_item()
        
    def get_vobject_id (self):
        """ Returns the id of the vobject (id number of the vobject - 
        generated in eSession.py / self._add_vismol_object() ) """
        row = self.get_selected_item()
        return row.object_id if row is not None else None

    
    def get_system_id (self):
        """ Returns the id of the vobject (id number of the vobject - 
        generated in eSession.py / self._add_vismol_object() ) """
        row = self.get_selected_item()
        return row.system_id if row is not None else None
        
        
    def _get_coordinates_info (self):
        """ Function doc """
        row = self.get_selected_item()
        if row is None:
            return None, None, None, None
        return row.name, row.object_id, row.system_id, row.icon


    def set_active_vobject (self, pos = 0):
        """ Function doc """
        if pos ==-1:
            model = self.get_model()
            n = model.get_n_items() if model is not None else 0
            self.set_selected(n - 1 if n else GTK_INVALID_LIST_POSITION)
        else:
            self.set_selected(pos)

    
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
