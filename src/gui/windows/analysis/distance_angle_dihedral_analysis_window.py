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
from src.gtk4_compat import GTK_INVALID_LIST_POSITION
import gc
import os

#import math
from gi.repository import Gtk, Pango
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gui.gtk4_builder import connect_builder_signals, load_builder_file, load_builder_string
#from gui.widgets.custom_widgets import CoordinatesComboBox
from gui.widgets.custom_widgets import FolderChooserButton

from gui.windows.setup.windows_and_dialogs import TextWindow

from util.geometric_analysis import get_simple_distance
from util.geometric_analysis import get_simple_angle
from util.geometric_analysis import get_simple_dihedral


from pprint import pprint
import numpy as np


class DistanceMeasureRow(GObject.Object):
    measure_type = GObject.Property(type=str, default="")
    atom1 = GObject.Property(type=str, default="-")
    atom2 = GObject.Property(type=str, default="-")
    atom3 = GObject.Property(type=str, default="-")
    atom4 = GObject.Property(type=str, default="-")

    def __init__(self, values):
        super().__init__()
        self.measure_type, self.atom1, self.atom2, self.atom3, self.atom4 = values[:5]


def _measure_column_factory(property_name):
    factory = Gtk.SignalListItemFactory()

    def setup(_factory, item):
        item.set_child(Gtk.Label(xalign=0))

    def bind(_factory, item):
        item.get_child().set_text(getattr(item.get_item(), property_name))

    factory.connect("setup", setup)
    factory.connect("bind", bind)
    return factory

class DistanceAngleDihedralAnalysisWindow:

    def __init__(self, main = None ):
        """ Class initialiser """
        self.main                = main
        self.home                = main.home
        self.p_session           = self.main.p_session
        self.vm_session          = self.main.vm_session
        self.Visible             = False  
        
        self.parameters = []
        

    def open_window (self, vobject = None):
        """ Function doc """
        if self.Visible  ==  False:

            self.builder = Gtk.Builder()
            load_builder_file(self.builder, os.path.join(self.main.home,'src/gui/windows/analysis/distance_angle_dihedral_analysis_window.glade'))
            connect_builder_signals(self.builder, self)
            
            self.window = self.builder.get_object('window')
            self.window.set_title('Distance, Angle, and Dihedral Analysis')
            self.window.set_default_size(100, 500)
            
            #------------------------------------------------------------------------
            # define_measurement
            #------------------------------------------------------------------------
            self.btn_distance = self.builder.get_object('btn_distance')
            self.btn_distance.connect("clicked", self.define_measurement) 
            self.btn_distance = self.builder.get_object('btn_angle')
            self.btn_distance.connect("clicked", self.define_measurement) 
            self.btn_distance = self.builder.get_object('btn_dihedral')
            self.btn_distance.connect("clicked", self.define_measurement) 
            #------------------------------------------------------------------------
            self.btn_cancel = self.builder.get_object('btn_cancel')
            self.btn_cancel.connect("clicked", self.close_window)
            #------------------------------------------------------------------------
            #------------------------------------------------------------------------
            self.btn_clear = self.builder.get_object('btn_clear')
            self.btn_clear.connect("clicked", self.on_btn_clear)
            #------------------------------------------------------------------------
            
            
            self.folder_chooser_button = FolderChooserButton(main =  self.main, sel_type = 'folder', home =  self.home)
            self.builder.get_object('folder_chooser_box').append(self.folder_chooser_button.btn)
            self.folder_chooser_button.btn.set_hexpand(True)
            self.folder_chooser_button.btn.set_vexpand(True)
            system_id      = self.p_session.active_id

            
            self.build_treeview()
            
            self.window.present()
            #self.column_type.set_spacing(40)
            #self.column_1   .set_spacing(40)
            #self.column_2   .set_spacing(40)
            #self.column_3   .set_spacing(40)
            #self.column_4   .set_spacing(40)
            
            self.Visible  = True
            
            
    def build_treeview (self):
        """ Function doc """
       
        self.liststore = Gio.ListStore.new(DistanceMeasureRow)
        self.selection_model = Gtk.SingleSelection.new(self.liststore)
        self.treeview = Gtk.ColumnView.new(self.selection_model)
        host = self.builder.get_object('selection_treeview')
        host.append(self.treeview)
        for title, prop in (("Type", "measure_type"), ("#1", "atom1"),
                            ("#2", "atom2"), ("#3", "atom3"), ("#4", "atom4")):
            column = Gtk.ColumnViewColumn.new(title, _measure_column_factory(prop))
            column.set_expand(prop == "measure_type")
            self.treeview.append_column(column)
        self.treeview.connect("activate", self.on_select)
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self.on_key_press)
        self.treeview.add_controller(key_controller)


    def close_window (self, button, data  = None):
        """ Function doc """
        self.window.destroy()
        self.Visible    =  False
        self.on_btn_clear(None, None)
        return True


    def define_measurement(self, widget, event=None):
        """ Function doc """
        
        atom1 = self.vm_session.picking_selections.picking_selections_list[0]
        atom2 = self.vm_session.picking_selections.picking_selections_list[1]
        atom3 = self.vm_session.picking_selections.picking_selections_list[2]
        atom4 = self.vm_session.picking_selections.picking_selections_list[3]

        #print(atom1, atom2, atom3, atom4)
        
        atom_list = [atom1, atom2, atom3, atom4]
        
        
        if widget ==  self.builder.get_object('btn_distance'):
            
            liststore_item = ['distance']
            
            if atom1 and atom2:
                
                idx1 = str(atom1.index)
                idx2 = str(atom2.index)
                
                sym1 = atom1.symbol
                sym2 = atom2.symbol
                
                self.parameters.append(['distance',atom1, atom2])
                
                item1 = '  {} / {}  '.format(idx1, sym1)
                liststore_item.append(item1)
                item2 = '  {} / {}  '.format(idx2, sym2)
                liststore_item.append(item2)
                
                liststore_item.append('-')
                liststore_item.append('-')
                liststore_item.append('-')
                self.liststore.append(DistanceMeasureRow(liststore_item))
                
        if widget ==  self.builder.get_object('btn_angle'):
            
            liststore_item = ['angle']
            if atom1 and atom2 and atom3:
                
                idx1 = str(atom1.index)
                idx2 = str(atom2.index)
                idx3 = str(atom3.index)
                
                sym1 = atom1.symbol
                sym2 = atom2.symbol
                sym3 = atom3.symbol
                
                self.parameters.append(['angle',atom1, atom2, atom3])
                
                item1 = '  {} / {}  '.format(idx1, sym1)
                liststore_item.append(item1)
                
                item2 = '  {} / {}  '.format(idx2, sym2)
                liststore_item.append(item2)
                
                item3 = '  {} / {}  '.format(idx3, sym3)
                liststore_item.append(item3)
                
                #liststore_item.append('-')
                liststore_item.append('-')
                liststore_item.append('-')
                self.liststore.append(DistanceMeasureRow(liststore_item))
                
        if widget ==  self.builder.get_object('btn_dihedral'):
            
            liststore_item = ['dihedral']
            if atom1 and atom2 and atom3 and atom4:
                
                idx1 = str(atom1.index)
                idx2 = str(atom2.index)
                idx3 = str(atom3.index)
                idx4 = str(atom4.index)
                
                sym1 = atom1.symbol
                sym2 = atom2.symbol
                sym3 = atom3.symbol
                sym4 = atom4.symbol
                
                self.parameters.append(['dihedral',atom1, atom2, atom3, atom4])
                
                item1 = '  {} / {}  '.format(idx1, sym1)
                liststore_item.append(item1)
                
                item2 = '  {} / {}  '.format(idx2, sym2)
                liststore_item.append(item2)
                
                item3 = '  {} / {}  '.format(idx3, sym3)
                liststore_item.append(item3)
                
                item4 = '  {} / {}  '.format(idx4, sym4)
                liststore_item.append(item4)
                
                liststore_item.append('-')
                #liststore_item.append('-')
                self.liststore.append(DistanceMeasureRow(liststore_item))
    

    def on_select(self, tree, position):
        row = self.liststore.get_item(position)
        if row is not None:
            dprint(row.measure_type, row.atom1, row.atom2)


    def on_btn_clear (self, widget, event=None):
        """ Function doc """
        self.liststore.remove_all()
        self.parameters = []
    
    
    def on_key_press(self, controller, keyval, _keycode, _state):
        """ Deletes the key pressed and deletes an item if it is 'Delete' """
        if keyval == Gdk.KEY_Delete:
            deleted_line = self.selection_model.get_selected()
            if deleted_line != GTK_INVALID_LIST_POSITION:
                self.parameters.pop(deleted_line)
                dprint(f"Selected line to be deleted: {deleted_line}")
                self.liststore.remove(deleted_line)
        return False


    def on_btn_run_analysis (self, widget, event = None):
        """ Function doc """

        measures = []
        jobsize   = len(self.parameters)
        dprint('\n\n')
        
        for job in self.parameters:
            
            vobject      = job[1].vm_object
            size         = len(vobject.frames)
            job_distance = []
            
            for i in range(size):
                if job[0] == 'distance':    
                    a1_coord = job[1].coords(frame=i)
                    a2_coord = job[2].coords(frame=i)
                    
                    dist1 = get_simple_distance(a1_coord, a2_coord)            
                    job_distance.append(dist1)
                
                elif job[0] == 'angle':
                    a1_coord = job[1].coords(frame=i)
                    a2_coord = job[2].coords(frame=i)
                    a3_coord = job[3].coords(frame=i)
                    
                    angle = get_simple_angle( a1_coord, a2_coord, a3_coord)            
                    job_distance.append(angle)
                
                
                elif  job[0] == 'dihedral':
                    a1_coord = job[1].coords(frame=i)
                    a2_coord = job[2].coords(frame=i)
                    a3_coord = job[3].coords(frame=i)
                    a4_coord = job[4].coords(frame=i)
                    
                    dangle = get_simple_dihedral( a1_coord, a2_coord, a3_coord, a4_coord)
                    job_distance.append(dangle)
                
                else:
                    pass
                    
            measures.append(job_distance)
        
        #print(measures)
        '''
        # printing the results 
        '''
        text = ''
        for i in range(size):
            text += ' {:<4} '.format(i)
            for j in range(jobsize):
                text += ' {:^.7f} '.format(measures[j][i])
            
            text += '\n' 
        
        dprint(text)
        textwindow = TextWindow(text)

    
    
    
