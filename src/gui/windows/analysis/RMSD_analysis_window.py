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
from gi.repository import Gtk
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

class RMSDAnalysisWindow:

    def __init__(self, main = None, system_liststore=None ):
        """ Class initialiser """
        self.main                = main
        self.home                = main.home
        self.p_session           = self.main.p_session
        self.vm_session          = self.main.vm_session
        self.Visible             = False  
        
        self.parameters = []
        
        self.is_frame_reference = True

    def open_window (self, vobject = None):
        """ Function doc """
        if self.Visible  ==  False:

            self.builder = Gtk.Builder()
            load_builder_file(self.builder, os.path.join(self.main.home,'src/gui/windows/analysis/RMSD_analysis.glade'))
            connect_builder_signals(self.builder, self)
            
            self.window = self.builder.get_object('window')
            self.window.set_title('RMSD Analysis')
            
            self.radio_frame = self.builder.get_object('radio_frame_reference')
            self.radio_frame.connect("toggled", self.on_button_toggled)
            
            self.radio_average = self.builder.get_object('radio_average')
            #self.radio_frame.connect("toggled", self.on_button_toggled)
            
            
            self.chk_frames_from =  self.builder.get_object('chk_frames_from')
            self.chk_frames_from.connect('toggled' ,self.on_frame_range_checkbox)
            
            self.chk_step_size = self.builder.get_object('chk_step_size')
            self.chk_step_size.connect('toggled' ,self.on_step_size_checkbox)
            
            self.btn_close = self.builder.get_object('btn_close')
            self.btn_close.connect('clicked' ,self.close_window)
            #on_button_toggled
            
            #self.window.set_default_size(100, 500)
            
            ##------------------------------------------------------------------------
            ## define_measurement
            ##------------------------------------------------------------------------
            #self.btn_distance = self.builder.get_object('btn_distance')
            #self.btn_distance.connect("button_press_event"  ,self.define_measurement) 
            #self.btn_distance = self.builder.get_object('btn_angle')
            #self.btn_distance.connect("button_press_event"  ,self.define_measurement) 
            #self.btn_distance = self.builder.get_object('btn_dihedral')
            #self.btn_distance.connect("button_press_event"  ,self.define_measurement) 
            ##------------------------------------------------------------------------
            #self.btn_cancel = self.builder.get_object('btn_cancel')
            #self.btn_cancel.connect("button_press_event"  ,self.close_window)
            ##------------------------------------------------------------------------
            ##------------------------------------------------------------------------
            #self.btn_clear = self.builder.get_object('btn_clear')
            #self.btn_clear.connect("button_press_event"  ,self.on_btn_clear)
            ##------------------------------------------------------------------------
            #
            #
            #self.folder_chooser_button = FolderChooserButton(main =  self.main, sel_type = 'folder', home =  self.home)
            #system_id      = self.p_session.active_id

            
            #self.build_treeview()
            
            self.window.present()
            #self.column_type.set_spacing(40)
            #self.column_1   .set_spacing(40)
            #self.column_2   .set_spacing(40)
            #self.column_3   .set_spacing(40)
            #self.column_4   .set_spacing(40)
            self.builder.get_object('scroll_treeview').hide()
            #self.builder.get_object('output_box').hide()
            self.builder.get_object('btn_distance').hide()
            self.Visible  = True
            
            
    def close_window (self, button, data  = None):
        """ Function doc """
        self.window.destroy()
        self.Visible    =  False
        return True
        #self.on_btn_clear(None, None)


    def on_step_size_checkbox (self, widget):
        """ Function doc """
        if self.builder.get_object('chk_step_size').get_active():
            self.builder.get_object('entry_step_size').set_sensitive(True)
        else:
            self.builder.get_object('entry_step_size').set_sensitive(False)

    def on_frame_range_checkbox (self, widget):
        """ Function doc """
        if self.builder.get_object('chk_frames_from').get_active():
            self.builder.get_object('entry_frame_init').set_sensitive(True)
            #self.builder.get_object('label1').set_sensitive(True)
            self.builder.get_object('entry_frame_last').set_sensitive(True)
        else:
            self.builder.get_object('entry_frame_init').set_sensitive(False)
            #self.builder.get_object('label1').set_sensitive(False)
            self.builder.get_object('entry_frame_last').set_sensitive(False)
            #f_init = int(self.builder.get_object('entry_frame_init').get_text())
            #f_last = int(self.builder.get_object('entry_frame_last').get_text())        
        
        

    def on_button_toggled(self, button):
        
        if self.radio_frame.get_active():
            self.builder.get_object('entry_ref_frame').set_sensitive(True)
            self.is_frame_reference = True
        else:
            self.builder.get_object('entry_ref_frame').set_sensitive(False)
            self.is_frame_reference = False

            
    def get_average_structure(self, 
                              vismol_object  = None, 
                              selection_list = None, 
                              step_size      = 1   ,
                              frame_range    = [0,-1]):
        """ Function doc """
        
        
        #frame_average = np.copy(vismol_object.frames[0])
        frame_average = np.zeros_like(vismol_object.frames[0])
        #print(frame_average)
        
        n = 0
        for frame in vismol_object.frames:
            for index, coords in enumerate(frame):
                frame_average[index][0] += coords[0]
                frame_average[index][1] += coords[1]
                frame_average[index][2] += coords[2]
                
                pass
                #print(coords)
            
            n+=1
        dprint(frame_average)

        for coords in frame_average:
            coords[0] = coords[0]/n
            coords[1] = coords[1]/n
            coords[2] = coords[2]/n

        #print(frame_average)
        return frame_average
        
    def on_btn_run_analysis (self, widget, event = None):
        """ Function doc """
        
        f_last    = -1
        f_init    = 0
        step_size = 1
        
        #.1 - defining the  reference vismol object and selection list
        selection_list, residue_dict, vismol_object = self.vm_session.build_index_list_from_atom_selection (return_vobject = True)
        if vismol_object == None:
            text = 'RMSD calculation failed: invalid atom selection! Please select the desired group of atoms from a single VObject only.'

            dialog = Gtk.MessageDialog(
                        transient_for=self.main.window,
                        message_type=Gtk.MessageType.ERROR,
                        buttons=Gtk.ButtonsType.OK,
                        text="Failed!",
                        )
            dialog.format_secondary_text(
                text #"The folder you have selected does not appear to be valid. Please select a different folder or create a new one."
            )
            dialog.connect("response", lambda current_dialog, _response: current_dialog.destroy())
            dialog.present()
            
            dprint('RMSD calculation failed: invalid atom selection! Please select the desired group of atoms from a single VObject only.')
            return False
        
        #.2 redefining the range of frames and step size
        # frame range
        if self.builder.get_object('chk_frames_from').get_active():
            f_init = int(self.builder.get_object('entry_frame_init').get_text())
            f_last = int(self.builder.get_object('entry_frame_last').get_text())
        # stepsize
        if self.builder.get_object('chk_step_size').get_active():
            step_size = int(self.builder.get_object('entry_step_size').get_text())
        #-------------------------------------------------------------------------

        #.3 defining the reference set of coordinates 
        if self.is_frame_reference:
            try:
                ref_frame = int(self.builder.get_object('entry_ref_frame').get_text())
            except:
                dprint('fail ref_frame')
                return False
            ref_frame = vismol_object.frames[ref_frame]
        
        else:
            ref_frame = self.get_average_structure(vismol_object, selection_list)
        #-------------------------------------------------------------------------


        
        #print('on_btn_run_analysis')

        #print(selection_list, residue_dict, vismol_object)
        #print(vismol_object.frames[0])
        
        
        
        
        
        
        RMSD_list = []
        text = ''
        n = 0
        #a.size
        
        if f_last == -1:
            traj_size = vismol_object.frames.shape
            dprint(traj_size)
            traj_size = traj_size[0]
            f_last = traj_size

        
        #for frame in vismol_object.frames:
            #print('\n')        
        for f_index in range(f_init, f_last, step_size):
            #print(f_index)
            frame = vismol_object.frames[f_index]

            
            rmsd   = 0.0
            d2_sum = 0.0 
            
            for index in selection_list:
                #print(vismol_object.frames[0][index])
                
                ci = ref_frame[index] # reference
                cj = frame[index]     # actual frame
                
                
                #For each atom, the squared distance between the two positions is calculated:
                d2 = (((cj[0]-ci[0])**2) +((cj[1]-ci[1])**2) + ((cj[2]-ci[2])**2))
                
                #Add up all distances squared:
                d2_sum += d2
            
            #It is divided by N (number of atoms), and take the square root:
            rmsd = ( d2_sum/ (len(selection_list)) )**0.5
            #print(rmsd)
            RMSD_list.append(rmsd)
            text += str(rmsd)+'\n'
        
            n+=1
        
        average   = (sum(RMSD_list)) / n
        min_value = min(RMSD_list)
        max_value = max(RMSD_list)
        
        dprint('average:   ', average)
        dprint('min_value: ', min_value)
        dprint('max_value: ', max_value)
        
        textwindow = TextWindow(text)
        
        if self.builder.get_object('chk_plot').get_active():
            from util.easyplot import ImagePlot, XYPlot
            import random
            self.plot = XYPlot()
            X =  range(n)
            Y =  RMSD_list
            rgb = [0,0,0,]
            self.plot.add ( X = X, Y = Y,
                                symbol = None, sym_color = [1,1,1], sym_fill = False, 
                                line = 'solid', line_color = rgb, energy_label = None)
            
            
            window =  Gtk.Window()
            window.set_child(self.plot)
            self.plot.Ymin_list= [0]
            window.set_default_size(600, 500)
            window.present()
        else:
            dprint('chk_plot_off')
            
