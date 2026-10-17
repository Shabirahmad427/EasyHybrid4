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
from gui.gtk4_builder import connect_builder_signals, load_builder_file, load_builder_string
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

# --- imports entre modulos adicionados na refatoracao ---
from gui.widgets.custom_widgets.file_choosers import FolderChooserButton

class SaveTrajectoryBox:
    """ Class doc """
    
    def __init__ (self, parent, home):
        """ Class initialiser """
        
        self.builder = Gtk.Builder()
        load_builder_file(self.builder, os.path.join(home,'src/gui/widgets/trajectory_box.glade'))
        connect_builder_signals(self.builder, self)
        
        self.box = self.builder.get_object('trajectory_box')
        
        self.folder_chooser_button = FolderChooserButton(main =  parent, home = home)
        self.builder.get_object('folder_chooser_box').append(self.folder_chooser_button.btn)
        self.folder_chooser_button.btn.set_hexpand(True)
        self.folder_chooser_button.btn.set_vexpand(True)
        self.folder_chooser_button.btn.set_sensitive(False)
                
        '''--------------------------------------------------------------------------------------------'''
        formats = [
                    "pDynamo / pkl" ,
                    #"amber / crd"   ,
                    #"charmm / dcd"  ,
                    #"xyz"           ,
            ]
        self.format_model = Gtk.StringList.new(formats)
        self.format_dropdown = self.builder.get_object('format_dropdown')
        format_expression = Gtk.PropertyExpression.new(
            Gtk.StringObject, None, "string"
        )
        self.format_dropdown.set_model(self.format_model)
        self.format_dropdown.set_expression(format_expression)
        '''--------------------------------------------------------------------------------------------'''
        self.format_dropdown.set_selected(0)
        self.set_folder(None)
        #simParameters["trajectory_name"] = self.save_trajectory_box.builder.get_object('entry_trajectory_name').get_text()
    #====================================================================================
    def on_toggle_save_checkbox (self, widget):
        """ Function doc """
        if self.builder.get_object('checkbox_save_traj').get_active():
            self.builder.get_object('entry_trajectory_name').set_sensitive(True)
            
            self.builder.get_object('label_working_folder').set_sensitive(True)
            #self.builder.get_object('file_chooser_working_folder').set_sensitive(True)
            self.builder.get_object('label_format').set_sensitive(True)
            self.format_dropdown.set_sensitive(True)
            self.builder.get_object('label_trajectory_frequency').set_sensitive(True)
            self.builder.get_object('entry_trajectory_frequency').set_sensitive(True)
            self.folder_chooser_button.btn.set_sensitive(True)

        else:
            self.builder.get_object('entry_trajectory_name').set_sensitive(False)

            self.builder.get_object('label_working_folder').set_sensitive(False)
            #self.builder.get_object('file_chooser_working_folder').set_sensitive(False)
            self.builder.get_object('label_format').set_sensitive(False)
            self.format_dropdown.set_sensitive(False)
            self.builder.get_object('label_trajectory_frequency').set_sensitive(False)
            self.builder.get_object('entry_trajectory_frequency').set_sensitive(False)
            self.folder_chooser_button.btn.set_sensitive(False)
       
    
    def get_trajectory_frequency (self):
        """ Function doc """
        return int(self.builder.get_object('entry_trajectory_frequency').get_text())
    
    def set_trajectory_frequency (self, freq = 10):
        """ Function doc """
        self.builder.get_object('entry_trajectory_frequency').set_text(str(freq))
    
    def get_format (self):
        return self.format_dropdown.get_selected()
    
    def set_format (self, _format):
        return self.format_dropdown.set_selected(_format)
        
    def get_active (self):
        """ Function doc  """
        if self.builder.get_object('checkbox_save_traj').get_active():
            return True
        else:
            return False
    
    def set_active (self, active = True):
        """ Function doc  """
        self.builder.get_object('checkbox_save_traj').set_active(active) 

    #====================================================================================
    def get_folder (self):
        """ Function doc """
        return self.folder_chooser_button.get_folder()
    #====================================================================================    
    def set_folder (self, folder):
        """ Function doc """
        self.folder_chooser_button.set_folder(folder)
    
    def get_filename (self):
        """ Function doc """
        return self.builder.get_object('entry_trajectory_name').get_text()
    
    def set_filename (self, filename = 'filename'):
        """ Function doc """
        return self.builder.get_object('entry_trajectory_name').set_text(filename)
