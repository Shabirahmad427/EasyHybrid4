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
from gi.repository import Gdk
from gi.repository import GdkPixbuf
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
from types import SimpleNamespace

# --- imports entre modulos adicionados na refatoracao ---
from gui.widgets.custom_widgets.comboboxes import CoordinatesComboBox

class SequenceViewerBox(Gtk.Box):
    """ Class doc """
    
    def __init__ (self, main = None, mode = 0 ):
        """ Class initialiser """
        Gtk.Box.__init__(self)
        
        self.main = main
        self.seqview   = GtkSequenceViewer(main = main)
        #-----------------------------------------------------------------------
        motion = Gtk.EventControllerMotion()
        motion.connect("motion", self._on_pointer_motion)
        self.seqview.add_controller(motion)
        click = Gtk.GestureClick()
        click.set_button(0)
        click.connect("pressed", self._on_pointer_pressed)
        click.connect("released", self._on_pointer_released)
        self.seqview.add_controller(click)
        #-----------------------------------------------------------------------

        #self.add()
        
        #--------------------------------------------------------------#

        self.box_horizontal1 = Gtk.Box(orientation = Gtk.Orientation.HORIZONTAL, spacing = 10)
        
        self.label1  = Gtk.Label()
        self.label1.set_text('Coordinates:')
        self.box_horizontal1.append(self.label1)
        self.coordinates_combobox = CoordinatesComboBox(self.main.vobject_liststore_dict[self.main.p_session.active_id])
        
        self.box_horizontal1.append(self.coordinates_combobox)
        #--------------------------------------------------------------#




        #------------------------------------------------------------------#
        #                  CHAIN combobox and Label
        #------------------------------------------------------------------#
        self.label2  = Gtk.Label()
        self.label2.set_text('Chain:')
        self.box_horizontal1.append(self.label2)

        self.chain_names = Gtk.StringList.new([])
        self.chain_dropdown = Gtk.DropDown.new(self.chain_names, None)
        self.chain_dropdown.connect("notify::selected", self.on_chain_selected)
        self.box_horizontal1.append(self.chain_dropdown)




    @staticmethod
    def _pointer_event(controller, x, y):
        button = controller.get_current_button() if isinstance(controller, Gtk.GestureClick) else 0
        state = controller.get_current_event_state() if isinstance(controller, Gtk.Gesture) else Gdk.ModifierType(0)
        return SimpleNamespace(x=x, y=y, button=button, state=state)

    def _on_pointer_motion(self, controller, x, y):
        self.seqview.on_motion(self.seqview, self._pointer_event(controller, x, y))

    def _on_pointer_pressed(self, gesture, _n_press, x, y):
        self.seqview.button_press(self.seqview, self._pointer_event(gesture, x, y))

    def _on_pointer_released(self, gesture, _n_press, x, y):
        self.seqview.button_release(self.seqview, self._pointer_event(gesture, x, y))
    def on_chain_selected(self, dropdown, _pspec=None):
        """Update the sequence viewer filter for the selected chain."""
        selected = dropdown.get_selected_item()
        if selected is None:
            return
        chain = selected.get_string()
        self.current_filter_chain = chain
        #print("%s Chain selected!" % self.current_filter_chain)
        # we update the filter, which updates in turn the view
        self.chain_filter.refilter()
