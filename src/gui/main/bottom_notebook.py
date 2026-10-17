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
import os, sys, time
from types import SimpleNamespace
import gi 
import signal
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, GObject, Gio, GLib
from gi.repository import GdkPixbuf
from gui.gtk4_builder import load_builder_file, load_builder_string


from gui.widgets.custom_widgets  import VismolSelectionTypeBox
from gui.widgets.custom_widgets  import FileChooser
from gui.widgets.custom_widgets  import get_colorful_square_pixel_buffer
from gui.widgets.custom_widgets  import ReactionCoordinateBox
from gui.widgets.custom_widgets  import SequenceViewerBox

from gui.windows.setup.windows_and_dialogs import ImportANewSystemWindow
from gui.windows.setup.windows_and_dialogs import EasyHybridDialogSetQCAtoms
from gui.windows.setup.windows_and_dialogs import EasyHybridSetupQCModelWindow
from gui.windows.setup.windows_and_dialogs import EasyHybridGoToAtomWindow
#from gui.windows.setup.windows_and_dialogs import PDynamoSelectionWindow
from gui.windows.setup.windows_and_dialogs import EasyHybridSelectionWindow
from gui.windows.setup.windows_and_dialogs import ExportDataWindow
from gui.windows.setup.windows_and_dialogs import EasyHybridDialogPrune
from gui.windows.setup.windows_and_dialogs import MakeSolventBoxWindow


from gui.windows.setup.windows_and_dialogs import ImportTrajectoryWindow
from gui.windows.setup.windows_and_dialogs import TrajectoryPlayerWindow
from gui.windows.setup.windows_and_dialogs import InfoWindow
from gui.windows.setup.windows_and_dialogs import MergeSystemWindow
from gui.windows.setup.windows_and_dialogs import SolvateSystemWindow
from gui.windows.setup.windows_and_dialogs import SimpleDialog
from gui.windows.setup.edit_frames_dialog import EditFrameDialog

from gui.windows.setup.easyhybrid_terminal    import TerminalWindow
from gui.windows.setup.selection_list_window  import *
from gui.windows.setup.setup_interface        import EasyHybridPreferencesWindow
from gui.windows.setup.process_manager_window import ProcessManagerWindow

from gui.windows.simulation.single_point_window          import SinglePointWindow
from gui.windows.simulation.geometry_optimization_window import GeometryOptimization
from gui.windows.simulation.PES_scan_window              import PotentialEnergyScanWindow 
from gui.windows.simulation.PES_advanced_scan_window     import AdvancedPotentialEnergyScanWindow 
from gui.windows.simulation.molecular_dynamics_window    import MolecularDynamicsWindow 
from gui.windows.simulation.umbrella_sampling_window     import UmbrellaSamplingWindow 
from gui.windows.simulation.chain_of_states_opt_window   import ChainOfStatesOptWindow 
from gui.windows.simulation.normal_modes_window          import NormalModesWindow 

from gui.windows.analysis.WHAM_analysis_window                    import WHAMWindow 
from gui.windows.analysis.normal_modes_analysis_window            import NormalModesAnalysisWindow 
from gui.windows.analysis.surface_analysis_window                 import SurfaceAnalysisWindow 
#from gui.windows.analysis.surface_list_window                     import SurfaceListWindow 
from gui.windows.analysis.energy_refinement_window                import EnergyRefinementWindow
from gui.windows.analysis.PES_analysis_window                     import PotentialEnergyAnalysisWindow
from gui.windows.analysis.distance_angle_dihedral_analysis_window import DistanceAngleDihedralAnalysisWindow
from gui.windows.analysis.RMSD_tool                               import RMSDToolWindow
from gui.windows.analysis.RMSD_analysis_window                    import RMSDAnalysisWindow #~/programs/EasyHybrid3/src/gui/windows/analysis/RMSD_analysis_window.py
from gui.windows.analysis.align_trajectory                        import AlignTrajectoryWindow #~/programs/EasyHybrid3/src/gui/windows/analysis/RMSD_analysis_window.py
from gui.windows.analysis.reimaging_trajectory                    import ReimagingTrajectoryWindow #~/programs/EasyHybrid3/src/gui/windows/analysis/RMSD_analysis_window.py

from util.geometric_analysis import get_simple_distance
from util.sequence_plot import GtkSequenceViewer
from util.rama_plot import RamachandranWindow


from pdynamo.pDynamo2EasyHybrid import pDynamoSession
import numpy as np



from pCore                     import Align                                        , \
                                      Clone                                        , \
                                      logFile                                      , \
                                      Selection                                    , \
                                      TestScript_InputDataPath                     , \
                                      TestScript_OutputDataPath                    , \
                                      XHTMLLogFileWriter

class StatusRow(GObject.Object):
    """One immutable-time status entry with an updateable message."""

    timestamp = GObject.Property(type=str, default="")
    message = GObject.Property(type=str, default="")
    logfile = GObject.Property(type=str, default="")
    icon = GObject.Property(type=GdkPixbuf.Pixbuf)

    def __init__(self, timestamp, message, logfile, icon):
        super().__init__(timestamp=timestamp, message=message or "",
                         logfile=logfile or "", icon=icon)


class BottomNoteBook:
    
    def __init__ (self, main):
        """ Function doc """
        self.home    = main.home
        self.main    = main
        self.builder = Gtk.Builder()
        load_builder_file(self.builder, os.path.join(self.home,'src/gui/MainWindow_text_and_logs.glade'))
        
        self.widget = self.builder.get_object('notebook_text_and_logs')
        self._define_status_view()
    
        #-----------------------------------------------------------------------
        self.annotations_textviewer = self.builder.get_object('annontations_textviewer')
        self.annotations_textbuffer = self.annotations_textviewer.get_buffer()
        #-----------------------------------------------------------------------
        
        
        
        #-----------------------------------------------------------------------
        self.seqview =  GtkSequenceViewer(main = self.main)
        notebook = self.widget
        tab_label = Gtk.Label(label="-")
        tab_label1 = Gtk.Label(label="sequence")
        self.seqview.label = tab_label
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        #vbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        vbox.append(tab_label)
        vbox.append(self.seqview)
        
        #notebook.append_page(self.seqview, tab_label)
        notebook.append_page(vbox, tab_label1)
        #-----------------------------------------------------------------------
        self.sequence_motion_controller = Gtk.EventControllerMotion()
        self.sequence_motion_controller.connect(
            "motion",
            lambda controller, x, y: self.seqview.on_motion(
                self.seqview, SimpleNamespace(x=x, y=y)
            )
        )
        self.seqview.add_controller(self.sequence_motion_controller)

        self.sequence_click_controller = Gtk.GestureClick()
        self.sequence_click_controller.set_button(0)
        self.sequence_click_controller.connect(
            "pressed",
            lambda gesture, count, x, y: self.seqview.button_press(
                self.seqview,
                SimpleNamespace(x=x, y=y, button=gesture.get_current_button())
            )
        )
        self.sequence_click_controller.connect(
            "released",
            lambda gesture, count, x, y: self.seqview.button_release(
                self.seqview,
                SimpleNamespace(x=x, y=y, button=gesture.get_current_button())
            )
        )
        self.seqview.add_controller(self.sequence_click_controller)
        self.seqview.set_font_size(17)
        ##-----------------------------------------------------------------------
    
    def meu_evento_personalizado (self, widget, event):
        """ Function doc """
        #print(widget, event)
        
        #self.main.bottom_notebook.seqview.text_drawing_area.queue_draw()
        #print(self.main.vm_session.selections[self.main.vm_session.current_selection].active)
    
    def _define_status_view(self):
        """   
        This function builds the status treeview
        """
        self.status_view = self.builder.get_object('status_view')
        self.status_liststore = Gio.ListStore.new(StatusRow)
        self._status_message_handlers = {}
        self.status_view.set_model(Gtk.NoSelection.new(self.status_liststore))

        time_factory = Gtk.SignalListItemFactory()
        time_factory.connect("setup", self._setup_time_cell)
        time_factory.connect("bind", self._bind_time_cell)
        time_column = Gtk.ColumnViewColumn.new("", time_factory)
        time_column.set_resizable(True)
        self.status_view.append_column(time_column)

        message_factory = Gtk.SignalListItemFactory()
        message_factory.connect("setup", self._setup_message_cell)
        message_factory.connect("bind", self._bind_message_cell)
        message_factory.connect("unbind", self._unbind_message_cell)
        message_column = Gtk.ColumnViewColumn.new("", message_factory)
        message_column.set_expand(True)
        self.status_view.append_column(message_column)

    def _setup_time_cell(self, factory, list_item):
        label = Gtk.Label(xalign=0)
        label.set_selectable(True)
        list_item.set_child(label)

    def _bind_time_cell(self, factory, list_item):
        list_item.get_child().set_text(list_item.get_item().timestamp)

    def _setup_message_cell(self, factory, list_item):
        row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        picture = Gtk.Picture()
        picture.set_can_shrink(True)
        picture.set_size_request(16, 16)
        label = Gtk.Label(xalign=0)
        label.set_selectable(True)
        label.set_hexpand(True)
        label.set_wrap(True)
        row_box.append(picture)
        row_box.append(label)
        list_item.set_child(row_box)

    def _bind_message_cell(self, factory, list_item):
        row = list_item.get_item()
        row_box = list_item.get_child()
        picture = row_box.get_first_child()
        label = picture.get_next_sibling()
        picture.set_pixbuf(row.icon)
        label.set_text(row.message)
        self._unbind_message_cell(factory, list_item)
        handler_id = row.connect(
            "notify::message", lambda item, _pspec: label.set_text(item.message)
        )
        self._status_message_handlers[id(list_item)] = (row, handler_id)

    def _unbind_message_cell(self, factory, list_item):
        binding = self._status_message_handlers.pop(id(list_item), None)
        if binding is not None:
            row, handler_id = binding
            if row.handler_is_connected(handler_id):
                row.disconnect(handler_id)

    def status_teeview_add_new_item (self, message = None , logfile = '', system = None):
        """ Function doc """
        sqr_color      = get_colorful_square_pixel_buffer(system)
        current_time   = time.time()
        formatted_time = time.strftime("%Y-%m-%d   %H:%M:%S", time.localtime(current_time))
        #print(sqr_color)
        
        row = StatusRow(formatted_time, message, logfile, sqr_color)
        self.status_liststore.append(row)
        row_index = self.status_liststore.get_n_items() - 1
        scroller = self.status_view.get_parent()
        if isinstance(scroller, Gtk.ScrolledWindow):
            adjustment = scroller.get_vadjustment()
            GLib.idle_add(lambda: adjustment.set_value(adjustment.get_upper()) or GLib.SOURCE_REMOVE)
        return row_index

    def update_status_message(self, row_index, old_text, new_text):
        """Replace a status message fragment by its stable model position."""
        row = self.status_liststore.get_item(int(row_index))
        if row is not None:
            row.message = row.message.replace(old_text, new_text)
        
    def set_active_system_text_to_textbuffer (self):
        e_id = self.main.p_session.active_id
        # [BUG FIX] Used to index psystem[e_id] directly -- raised
        # KeyError (if e_id had just been removed, e.g. by delete_system)
        # or AttributeError (psystem[e_id] is the None placeholder used
        # when no system is loaded, see pDynamoSession.__init__). Neither
        # case means there's really an "active system" to show
        # annotations for, so just clear the buffer instead of crashing.
        system = self.main.p_session.psystem.get(e_id)
        if system is None:
            self.annotations_textbuffer.set_text('', -1)
            return
        self.annotations_textbuffer.set_text(system.e_annotations, -1)

    def get_active_system_text_from_textbuffer (self):
        """ Function doc """
        start_iter = self.annotations_textbuffer.get_start_iter()
        end_iter = self.annotations_textbuffer.get_end_iter()
        extracted_text = self.annotations_textbuffer.get_text(start_iter, end_iter, include_hidden_chars=False)

        e_id = self.main.p_session.active_id
        # [BUG FIX] Same guard as set_active_system_text_to_textbuffer --
        # see comment there. Nothing to write the annotations back onto
        # when there's no real active system (e.g. every system was
        # closed/deleted), so just skip it instead of crashing (this is
        # called from save_easyhybrid_session(), i.e. every single save).
        system = self.main.p_session.psystem.get(e_id)
        if system is None:
            return
        system.e_annotations = extracted_text

    def change_annotations_textbuffer (self, before, after):
        """ Function doc """
        start_iter = self.annotations_textbuffer.get_start_iter()
        end_iter = self.annotations_textbuffer.get_end_iter()
        extracted_text = self.annotations_textbuffer.get_text(start_iter, end_iter, include_hidden_chars=False)
        
        self.main.p_session.psystem[before].e_annotations = extracted_text
        new_text = self.main.p_session.psystem[after].e_annotations
        self.annotations_textbuffer.set_text(new_text, -1)
