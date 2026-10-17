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
from logging import getLogger
logger = getLogger(__name__)
import os, sys, time
import gi 
import signal
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, Gio, Pango
from gi.repository import GdkPixbuf
from gi.repository import GLib
from gui.gtk4_builder import connect_builder_signals, load_builder_file, choose_color
from gui.model_rows import CoordinateChoiceRow, SystemChoiceRow


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
from gui.windows.setup.windows_and_dialogs import OPLSParametersWindow


from gui.windows.setup.windows_and_dialogs import ImportTrajectoryWindow
from gui.windows.setup.windows_and_dialogs import TrajectoryPlayerWindow
from gui.windows.setup.windows_and_dialogs import InfoWindow
from gui.windows.setup.windows_and_dialogs import MergeSystemWindow
from gui.windows.setup.windows_and_dialogs import SolvateSystemWindow
from gui.windows.setup.windows_and_dialogs import SimpleDialog
from gui.windows.setup.edit_frames_dialog import EditFrameDialog
from gui.windows.setup.edit_cell          import EditCellWindow

from gui.windows.setup.easyhybrid_terminal    import TerminalWindow
from gui.windows.setup.selection_list_window  import *
from gui.windows.setup.setup_interface        import EasyHybridPreferencesWindow
from gui.windows.setup.process_manager_window import ProcessManagerWindow, JobHistoryRow

from gui.windows.simulation.single_point_window          import SinglePointWindow
from gui.windows.simulation.geometry_optimization_window import GeometryOptimization
from gui.windows.simulation.PES_scan_window              import PotentialEnergyScanWindow 
from gui.windows.simulation.PES_advanced_scan_window     import AdvancedPotentialEnergyScanWindow 
from gui.windows.simulation.molecular_dynamics_window    import MolecularDynamicsWindow 
from gui.windows.simulation.umbrella_sampling_window     import UmbrellaSamplingWindow 
from gui.windows.simulation.chain_of_states_opt_window   import ChainOfStatesOptWindow 
from gui.windows.simulation.normal_modes_window          import NormalModesWindow 
from gui.windows.simulation.transition_state_search_window import TransitionStateSearchWindow
from gui.windows.simulation.reaction_path_window import ReactionPathWindow
from gui.windows.simulation.conjugate_peak_refinement_window import ConjugatePeakRefinementWindow

from gui.windows.analysis.WHAM_analysis_window                    import WHAMWindow 
from gui.windows.analysis.normal_modes_analysis_window            import NormalModesAnalysisWindow 
from gui.windows.analysis.surface_analysis_window                 import SurfaceAnalysisWindow 
#from gui.windows.analysis.surface_list_window                     import SurfaceListWindow 
from gui.windows.analysis.energy_refinement_window                import EnergyRefinementWindow
from gui.windows.analysis.PES_analysis_window                     import PotentialEnergyAnalysisWindow
from gui.windows.analysis.distance_angle_dihedral_analysis_window import DistanceAngleDihedralAnalysisWindow
from gui.windows.analysis.RMSD_tool                               import RMSDToolWindow
from gui.windows.analysis.RMSD_analysis_window                    import RMSDAnalysisWindow #~/programs/EasyHybrid3/src/gui/windows/analysis/RMSD_analysis_window.py
from gui.windows.analysis.RDF_analysis_window                     import RDFAnalysisWindow
from gui.windows.analysis.density_analysis_window                 import DensityAnalysisWindow
from gui.windows.analysis.RMSF_analysis_window                    import RMSFAnalysisWindow
from gui.windows.analysis.ramachandran_analysis_window            import RamachandranAnalysisWindow
from gui.windows.analysis.align_trajectory                        import AlignTrajectoryWindow #~/programs/EasyHybrid3/src/gui/windows/analysis/RMSD_analysis_window.py
from gui.windows.analysis.reimaging_trajectory                    import ReimagingTrajectoryWindow #~/programs/EasyHybrid3/src/gui/windows/analysis/RMSD_analysis_window.py

from util.geometric_analysis import get_simple_distance
from util.sequence_plot import GtkSequenceViewer

from gui.windows.builder.builder_sidebar      import BuilderSidebarWindow
from gui.windows.builder.solvate_window       import SolvateWindow
from gui.windows.builder.atom_types_window    import AtomTypesWindow
from gui.windows.builder.transform_selection_window import TransformSelectionWindow
from gui.windows.builder.dihedral_angle_window import DihedralAngleWindow
from gui.windows.builder.fragment_library_window import FragmentLibraryWindow
from gui.windows.builder.structure_library_window import StructureLibraryWindow
from gui.windows.builder.dyff_parameters_window import DYFFParametersWindow


from pdynamo.pDynamo2EasyHybrid import pDynamoSession
import numpy as np



from pCore                     import Align                                        , \
                                      Clone                                        , \
                                      logFile                                      , \
                                      Selection                                    , \
                                      TestScript_InputDataPath                     , \
                                      TestScript_OutputDataPath                    , \
                                      XHTMLLogFileWriter

# --- imports entre modulos adicionados na refatoracao ---
from gui.main.main_treeview import EasyHybridMainTreeView
from gui.main.treeview_menu import TreeViewMenu
from gui.main.bottom_notebook import BottomNoteBook
from gui.main.preferences_window import PreferencesWindow
from gui.main.gtk4_menu import Gtk4MainMenu

class MainWindow:
    """
    The main application window for EasyHybrid, a graphical interface for pDynamo3.
    This class handles the initialization of all GUI components, including system
    and coordinate management, treeviews, notebooks, status bars, and auxiliary windows.
    """
    def _ui(self, object_id):
        """Return a GTK4 menu action or an object from the UI builder."""
        menu_item = getattr(self, "_menu_items", {}).get(object_id)
        if menu_item is not None:
            return menu_item
        return self.builder.get_object(object_id)

    def __init__ (self, vm_session = None, home = None, version = None):
        """
        Initialize the MainWindow instance.

        Parameters:
        vm_session : object
            The virtual molecular session providing visualization and simulation tools.
        home : str
            Home directory path, used for loading resources such as UI files and icons.
        version : str
            The version string of the EasyHybrid application.
        """
        self.home               =  home
        self.EASYHYBRID_VERSION =  version


        '''Search home folder. Every time a file is loaded into memory 
        this attribute will be modified.'''
        self.current_search_folder = None

        


        '''#- - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - -#'''
        self.system_liststore        = Gio.ListStore.new(SystemChoiceRow)
        
        #.Connects a system to a treeview postion
        self.system_choice_rows = {}
        
        '''The "vobject_liststore_dict" is a dictionary where the access key is
        the e_id, which is the index of the system of interest generated in 
        "pDynamo2Easyhybrid/pDynamoSession/add_new_system_to_psession". 
        Each dictionary element contains a liststore that includes the respective 
        vobjects.'''
        self.vobject_liststore_dict = {0: Gio.ListStore.new(CoordinateChoiceRow)}
        '''#- - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - -#'''
        self.job_history_liststore = Gio.ListStore.new(JobHistoryRow)

        # -------------------- GTK BUILDER --------------------
        # Load Glade UI and connect signals
        self._menu_items = {}
        self.builder = Gtk.Builder()
        load_builder_file(
            self.builder, os.path.join(self.home, 'src/gui/MainWindow.glade')
        )
        connect_builder_signals(self.builder, self)
        self.window = self._ui('window1')
        menu = Gtk4MainMenu(
            self, os.path.join(self.home, 'src/gui/MainMenu.json')
        )
        self._menu_items = menu.items
        self._ui('menubar1').append(menu.create_widget())
        # Restore the dimensions saved from the last session, but only if
        # gl_parameters['save_window_size'] is on (the "Save window size"
        # checkbox in Preferences). If off, always use the fixed 1200x600
        # size -- window_resize() below also respects this flag, so nothing
        # is overwritten in gl_parameters in that case.
        # [BUG FIX] Uses the local PARAMETER 'vm_session', not 'self.vm_session'
        # -- self.vm_session is only assigned further down in this __init__
        # (line ~223), so accessing it here raised AttributeError.
        if vm_session.vm_config.gl_parameters.get('save_window_size', True):
            saved_w = vm_session.vm_config.gl_parameters.get('main_window_width', 1200)
            saved_h = vm_session.vm_config.gl_parameters.get('main_window_height', 600)
        else:
            saved_w, saved_h = 1200, 600
        # Stored to compute the initial position of paned_V further down in
        # this __init__ (see 'self.paned_V_position'), based on the same
        # window height restored here.
        self._restored_window_height = saved_h
        self.window.set_default_size(saved_w, saved_h)                          
        self.window.set_title('EasyHybrid {}'.format(self.EASYHYBRID_VERSION))                          
        
        
        # Preserve EasyHybrid3's file drag-and-drop behavior with GTK4's
        # typed drop-target API.
        target = Gtk.DropTarget.new(Gdk.FileList, Gdk.DragAction.COPY)
        target.connect("drop", self.on_files_dropped)
        self.window.add_controller(target)
        
        
        # GTK4 associates the application icon with the application ID and
        # installed desktop metadata instead of setting it on each window.
        
        # Status bar initialization
        self.statusbar_main = self._ui('statusbar1')
        self.statusbar_main.push(1,'Welcome to EasyHybrid version {}, a pDynamo3 graphical tool'.format(self.EASYHYBRID_VERSION))
        
        self.paned_V         = self._ui('paned_V')
        
        # -------------------- SESSION MANAGEMENT --------------------
        self.vm_session      = vm_session#( main = None)
        self.vm_session.main = self
        
        self.vm_session.vm_object_counter = 0
        self.vm_session.insert_glmenu()
        
        # Forward main-window keyboard input to VisMol through GTK4's event
        # controller while preserving EasyHybrid3's shortcuts.
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self.vm_session.vm_widget._on_key_pressed)
        key_controller.connect("key-released", self.vm_session.vm_widget._on_key_released)
        self.window.add_controller(key_controller)

        # Route Escape through the same unsaved-session check as the window
        # close button.
        self.vm_session.vm_widget._pressed_Escape = lambda: self.on_delete_event(self.window, None)


        # -------------------- SELECTION BOX --------------------
        self.menu_box = self._ui('toolbutton_selection_box')
        self.box2 = self._ui('box2')
    
        self.selection_box_frame = VismolSelectionTypeBox(vm_session = self.vm_session)
        self.vm_session.selection_box_frame = self.selection_box_frame 
        self.menu_box.append(self.selection_box_frame.box)

        '''#- - - - - - - - - - - -  pDynamo - - - - - - - - - - - - - - -#'''
        self.p_session = pDynamoSession(vm_session = vm_session)
        '''#- - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - -#'''


        '''This gtk list is declared in the VismolGLWidget file 
           (it does not depend on the creation of Treeview)'''
        #self.Vismol_Objects_ListStore = self.vm_session.Vismol_Objects_ListStore
        
        #-------------------------------------------------------------------      
        #                         notebook_V1
        #-------------------------------------------------------------------
       
        #-------------------------------------------------------------------      
        #                         notebook_H1
        #-------------------------------------------------------------------
        self.notebook_H1 = Gtk.Notebook()
        self.ScrolledWindow_notebook_H1 = Gtk.ScrolledWindow()
        
        self.main_treeview                = EasyHybridMainTreeView()
        self.main_treeview.main           = self
        self.main_treeview.treeview_menu  = TreeViewMenu(self.main_treeview)
        
        
        self.ScrolledWindow_notebook_H1.set_child(self.main_treeview)
        
        #self.treeview = GtkEasyHybridMainTreeView(self, vm_session)
        #self.ScrolledWindow_notebook_H1.add(self.treeview)

        self.notebook_H1.append_page(child = self.ScrolledWindow_notebook_H1, tab_label= Gtk.Label(label = 'Objects'))
        


        # the label we use to show the selection
        self.label = Gtk.Label()
        self.label.set_text("")

        
        #-------------------------------------------------------------------
        #                         notebook_H2
        #-------------------------------------------------------------------
        self.notebook_H2 = Gtk.Notebook()
        #-------------------------------------------------------------------
        
        self.paned_H = Gtk.Paned(orientation = Gtk.Orientation.HORIZONTAL)
        self.button = Gtk.Button(label="Click Here")
        #-------------------------------------------------------------------
        self.vm_session = vm_session#( main = None)
        #-------------------------------------------------------------------
        
        
        self.container = Gtk.Box (orientation = Gtk.Orientation.VERTICAL)
        self.command_line_entry = Gtk.Entry()

        
        if self.vm_session is not None:
            # Add the main visualization widget to the container
            self.vm_session.vm_widget.set_hexpand(True)
            self.vm_session.vm_widget.set_vexpand(True)
            self.container.append(self.vm_session.vm_widget)
            self.notebook_H2.append_page(child = self.container, tab_label = Gtk.Label(label = 'view'))
            
            # Horizontal paned layout: notebook_H1 on left, notebook_H2 on right
            self.HBOX = Gtk.Box(orientation = Gtk.Orientation.VERTICAL, spacing = 0)
            self.notebook_H1.set_vexpand(True)
            self.HBOX.append(self.notebook_H1)

            self.paned_H.set_start_child(self.HBOX)
            self.paned_H.set_end_child(self.notebook_H2)
            self.paned_H.set_position(250)

            # . paned_V splits the GL/treeview area (top) from the bottom
            #   notebook (Status/Annotations/Sequence). Using plain .add()
            #   here would make the FIRST child (the top, containing the
            #   GL area) fixed-size and the SECOND child (the bottom
            #   notebook) absorb all resizing -- the opposite of what we
            #   want: the 3D view should resize with the window, and the
            #   bottom notebook should keep whatever size the user set for
            #   it. pack1/pack2 let us set "resize" explicitly instead of
            #   relying on add()'s implicit (and here backwards) default.
            self.bottom_notebook = BottomNoteBook(main = self)
            self.paned_V.set_start_child(self.paned_H)
            self.paned_V.set_end_child(self.bottom_notebook.widget)
            self.paned_V.set_resize_start_child(True)
            self.paned_V.set_resize_end_child(False)
            self.paned_V.set_shrink_start_child(True)
            self.paned_V.set_shrink_end_child(True)
            # [UPDATE] It used to be a fixed value (400px), which made no
            # sense at all if the restored window had a quite different
            # height (see self._restored_window_height, computed up top
            # from gl_parameters['main_window_height']).
            # Now it stores/uses the position as a PROPORTION of the window
            # height (gl_parameters['main_window_paned_v_ratio']) -- so the
            # split between the 3D/treeview area and the bottom notebook
            # follows the window size, instead of being "stuck" at a pixel
            # number that only made sense for the old default size
            # (1200x600). See window_resize() and on_paned_v_position_
            # changed() below, which keep this continuously updated.
            default_paned_v_ratio = 400.0 / 600.0
            paned_v_ratio = self.vm_session.vm_config.gl_parameters.get(
                'main_window_paned_v_ratio', default_paned_v_ratio)
            self.paned_V_position = int(round(paned_v_ratio * self._restored_window_height))
            GLib.idle_add(self._restore_initial_paned_position)
            self.paned_V.connect("notify::position", self.on_paned_v_position_changed)

            self.bottom_notebook.status_teeview_add_new_item(message = 'Welcome to EasyHybrid, have a happy simulation day!')

        ''' - - - - - - - - - - - - Terminal e Trajectory Play - - - - - - - - - - - - - - - - '''
        self.trajectory_player_button = self._ui('toolbutton_trajectory_tool1')
        self.cmd_terminal_button      = self._ui('toolbutton_terminal')
        ''' - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - - - - - - - - - - - - '''
        
        
        '''Text buffer associated with the command terminal (cmd) output
           
           used in:
                self.terminal_window           = TerminalWindow  (main = self)
            
        '''
        self.terminal_text_buffer    = Gtk.TextBuffer()
        
        
        
        


        #             EASYHYBRID SESSION FILE
        self.session_filename = None
        
        # Timer periodico de autosave (criterio "a cada N minutos" -- o
        # criterio "a cada N eventos" fica em pDynamoSession.register_
        # change_and_maybe_autosave, chamado nas acoes do treeview). Os dois
        # disparam o mesmo p_session._do_autosave(), o que vier primeiro.
        self._autosave_timer_id = None
        self._restart_autosave_timer()
        

        
        '''#- - - - - - - - - - G T K  W I N D O W S - - - - - - - - - - -#'''
        self.window_list = []
        
        self.filechooser                  = FileChooser(main_window = self)
        self.NewSystemWindow              = ImportANewSystemWindow       ( main = self )
        
        self.setup_QCModel_window         = EasyHybridSetupQCModelWindow ( main = self )
        self.window_list.append(self.setup_QCModel_window)
        
        self.geometry_optimization_window = GeometryOptimization  ( main = self )
        self.window_list.append(self.geometry_optimization_window)
        
        self.PES_scan_window              = PotentialEnergyScanWindow    ( main=  self)
        self.window_list.append(self.PES_scan_window)
        
        self.PES_advanced_scan_window              = AdvancedPotentialEnergyScanWindow ( main=  self)
        self.window_list.append(self.PES_advanced_scan_window)

        self.selection_list_window        = SelectionListWindow          ( main = self, system_liststore =  self.system_liststore)
        self.window_list.append(self.selection_list_window)

        
        self.process_manager_window = ProcessManagerWindow( main =  self)
        self.window_list.append(self.process_manager_window)
        
        
        self.go_to_atom_window            = EasyHybridGoToAtomWindow     ( main = self, system_liststore = self.system_liststore)
        self.window_list.append(self.go_to_atom_window)

        self.pDynamo_selection_window     = EasyHybridSelectionWindow    ( main = self)
        
        self.export_data_window           = ExportDataWindow             ( main = self)
        self.window_list.append(self.export_data_window)

        
        self.energy_refinement_window     = EnergyRefinementWindow       ( main = self)
        self.window_list.append(self.energy_refinement_window)
        
        self.single_point_window          = SinglePointWindow            ( main = self)
        self.window_list.append(self.single_point_window)
        #self.window_list.append(self.energy_refinement_window)

        self.import_trajectory_window     = ImportTrajectoryWindow       (main = self)
        self.window_list.append(self.import_trajectory_window)

        
        self.PES_analysis_window          = PotentialEnergyAnalysisWindow(main = self)#, coor_liststore = self.system_liststore)
        self.window_list.append(self.PES_analysis_window)


        self.trajectory_player_window  = TrajectoryPlayerWindow (main = self)
        self.terminal_window           = TerminalWindow  (main = self)
        self.builder_sidebar_window    = BuilderSidebarWindow (main = self)
        self.solvate_window           = SolvateWindow (main = self)
        self.atom_types_window        = AtomTypesWindow (main = self)
        self.transform_selection_window = TransformSelectionWindow (main = self)
        self.dihedral_angle_window = DihedralAngleWindow(main=self)
        self.fragment_library_window = FragmentLibraryWindow(main=self)
        self.structure_library_window = StructureLibraryWindow(main=self)
        self.dyff_parameters_window = DYFFParametersWindow(main=self)
        self.opls_parameters_window = OPLSParametersWindow(main=self)
        
        self.molecular_dynamics_window  = MolecularDynamicsWindow(main = self)
        self.window_list.append(self.molecular_dynamics_window)
        
        self.umbrella_sampling_window   = UmbrellaSamplingWindow(main = self)
        self.window_list.append(self.umbrella_sampling_window)
        
        
        self.chain_of_states_opt_window = ChainOfStatesOptWindow(main = self)
        self.window_list.append(self.chain_of_states_opt_window)

        self.transition_state_search_window = TransitionStateSearchWindow(main=self)
        self.window_list.append(self.transition_state_search_window)
        self.reaction_path_window = ReactionPathWindow(main=self)
        self.window_list.append(self.reaction_path_window)
        self.conjugate_peak_refinement_window = ConjugatePeakRefinementWindow(main=self)
        self.window_list.append(self.conjugate_peak_refinement_window)
        
        self.normal_modes_analysis_window =   NormalModesAnalysisWindow (main = self)
        self.surface_analysis_window =   SurfaceAnalysisWindow (main = self)

        self.distance_angle_dihedral_analysis_window = DistanceAngleDihedralAnalysisWindow (main = self)
        

        self.rmsd_analysis_window = RMSDAnalysisWindow (main = self, system_liststore = self.system_liststore)
        self.rdf_analysis_window = RDFAnalysisWindow(main=self)
        self.window_list.append(self.rdf_analysis_window)
        self.density_analysis_window = DensityAnalysisWindow(main=self)
        self.window_list.append(self.density_analysis_window)
        self.rmsf_analysis_window = RMSFAnalysisWindow(main=self)
        self.window_list.append(self.rmsf_analysis_window)
        self.ramachandran_analysis_window = RamachandranAnalysisWindow(main=self)
        self.window_list.append(self.ramachandran_analysis_window)
        
        self.align_trajectory_window = AlignTrajectoryWindow (main = self, system_liststore = self.system_liststore)
        
        self.reimaging_trajectory_window = ReimagingTrajectoryWindow (main = self, system_liststore = self.system_liststore)
        
        
        self.normal_modes_window          =   NormalModesWindow (main = self)
        self.window_list.append(self.normal_modes_window)

        
        self.WHAM_window   =  WHAMWindow(main = self)
        self.window_list.append(self.WHAM_window)

        self.simple_dialog =  SimpleDialog(main = self)

        self.edit_frames_dialog = EditFrameDialog(main = self)
        self.merge_system_window = MergeSystemWindow(main = self)
        self.solvate_system_window = SolvateSystemWindow(main = self)
        self.preferences_window = EasyHybridPreferencesWindow(main = self)

        self.make_solvent_box_window = MakeSolventBoxWindow(main = self)

        self.edit_cell_window = EditCellWindow(main = self)
        self.window_list.append(self.edit_cell_window)
        '''#- - - - - - - - - - - - - - - -  - - - - - - - - - - - - - - -#'''

        # -------------------- WINDOW SIGNALS --------------------
        #self.window.connect("close-request",      self.quit_easyhybrid)
        self.window.connect("close-request", self.on_delete_event)
        self.window.present()
        # [EN] macOS fix belt-and-suspenders: present() + an idle_add()
        # nudge for the very first frame. Harmless on every platform
        # (present() is a no-op if the window is already focused/shown;
        # the idle callback just asks the glArea/DrawingArea to redraw
        # once the main loop is idle) -- not gated to macOS.
        self.window.present()
        GLib.idle_add(self.vm_session.vm_widget.queue_draw)

    def _restore_initial_paned_position(self):
        self.paned_V.set_position(self.paned_V_position)
        return GLib.SOURCE_REMOVE


    def on_files_dropped(self, _target, file_list, _x, _y):
        """Load every local file dropped on the main window."""
        loaded = False
        for gio_file in file_list.get_files():
            path = gio_file.get_path()
            if path:
                dprint(path)
                self.vm_session.load(path)
                loaded = True
        return loaded

    def restart (self):
        """ Function doc """
        self.main_treeview.root_rows.remove_all()
        self.main_treeview.system_rows.clear()
        self.system_choice_rows.clear()
        self.system_liststore.remove_all()
        self.vobject_liststore_dict.clear()
        self.vobject_liststore_dict[0] = Gio.ListStore.new(CoordinateChoiceRow)
        #self.bottom_notebook.treeview.clear()
        self.session_filename = None
        
        #-------------------------------------------
        self.p_session.restart()
        
        #self.p_session.active_id = 0
        #self.p_session.psystem   =  {
        #                           0:None
        #                          }
        #self.p_session.psystem_name_list    = []
        #self.p_session.psystem_name_counter = 1
        #
        #self.p_session.counter      = 0
        #self.p_session.color_palette_counter = 0
        #-------------------------------------------

        
        self.vm_session.restart()
        self.job_history_liststore.remove_all()
        
    def window_resize (self, a, b =None, c=None):
        """ Function doc """
        # [BUG FIX] This function used to read w,h and do nothing with them --
        # no window dimension was persisted anywhere. It stores
        # em memoria aqui (barato, roda a cada evento 'check-resize'); a
        # the actual disk write happens in on_delete_event, not here, so as
        # not to write to the config file on every dragged pixel.
        # Respects gl_parameters['save_window_size']: if off, does not
        # atualiza nada (o tamanho fixo 1200x600 continua valendo na
        # proxima abertura).
        if not self.vm_session.vm_config.gl_parameters.get('save_window_size', True):
            return
        w, h = a.get_width(), a.get_height()
        self.vm_session.vm_config.gl_parameters['main_window_width']  = int(w)
        self.vm_session.vm_config.gl_parameters['main_window_height'] = int(h)
        
        # Mantem o divisor paned_V (area 3D/treeview vs. notebook de baixo)
        # following the current proportion, instead of staying fixed at a
        # pixel number while the window grows/shrinks. set_position() triggers
        # "notify::position" -> on_paned_v_position_changed(), que so'
        # reconfirms the SAME proportion (does not diverge, just redundant).
        paned_v = getattr(self, 'paned_V', None)
        if paned_v is not None and h > 0:
            ratio = self.vm_session.vm_config.gl_parameters.get('main_window_paned_v_ratio', 400.0/600.0)
            new_pos = int(round(ratio * h))
            if paned_v.get_position() != new_pos:
                paned_v.set_position(new_pos)
    
    def on_paned_v_position_changed (self, paned, gparam):
        """ Atualiza gl_parameters['main_window_paned_v_ratio'] sempre que a
            posicao do paned_V muda -- seja por arrasto do usuario (o caso
            que realmente importa persistir) ou programaticamente (quando
            window_resize acima reaplica a mesma proporcao apos a janela
            mudar de tamanho -- nesse caso o valor recalculado e' o mesmo,
            so' um pouco redundante, sem problema).

            Respeita gl_parameters['save_window_size'] (mesma flag que
            controla o resto da persistencia de layout da janela -- ver
            window_resize/on_delete_event). """
        if not self.vm_session.vm_config.gl_parameters.get('save_window_size', True):
            return
        h = self.window.get_height()
        if h > 0:
            self.paned_V_position = paned.get_position()
            self.vm_session.vm_config.gl_parameters['main_window_paned_v_ratio'] = self.paned_V_position / float(h)
    
    def _restart_autosave_timer (self):
        """ (Re)inicia o timer periodico de autosave, conforme gl_parameters
            ['autosave_interval_minutes']. Chamado uma vez no __init__ e de
            novo sempre que a janela de Preferences aplica mudancas (o
            intervalo pode ter sido alterado la'). """
        if getattr(self, '_autosave_timer_id', None) is not None:
            GLib.source_remove(self._autosave_timer_id)
            self._autosave_timer_id = None
        interval_min = self.vm_session.vm_config.gl_parameters.get('autosave_interval_minutes', 5)
        try:
            interval_min = float(interval_min)
        except (TypeError, ValueError):
            interval_min = 5.0
        # Piso de 10s: evita um valor absurdo (ex.: 0 ou negativo, digitado
        # por engano na Preferences) travar a interface com autosave a
        # cada tick do loop.
        interval_sec = max(int(interval_min * 60), 10)
        self._autosave_timer_id = GLib.timeout_add_seconds(interval_sec, self._on_autosave_timer_tick)

    def _on_autosave_timer_tick (self):
        """ Callback do timer periodico de autosave (criterio "a cada N
            minutos"). So' salva se autosave estiver ligado E houver
            mudancas nao salvas (self.p_session.changed). Retorna True
            sempre, pra o GLib manter o timer se repetindo -- retornar
            False cancelaria o timer. """
        gl_parameters = self.vm_session.vm_config.gl_parameters
        if gl_parameters.get('autosave', True) and self.p_session.changed:
            self.p_session._do_autosave()
        return True
    
    def add_vobject_to_vobject_liststore_dict (self, vismol_object):
        """ Adds a vobject to the vobject liststore. """
        e_id   = vismol_object.e_id
        if getattr(vismol_object, 'is_surface', False):
            vismol_object.coordinate_choice_row = None
            return
        if e_id not in self.vobject_liststore_dict:
            vismol_object.coordinate_choice_row = None
            return
        system = self.p_session.psystem.get(e_id)
        if system is None:
            vismol_object.coordinate_choice_row = None
            return
        
        #--------------------------------------------------
        #                  PIXEL BUFFER 
        #--------------------------------------------------
        sqr_color = get_colorful_square_pixel_buffer(system)
        
        
        row = CoordinateChoiceRow(
            vismol_object.name, vismol_object.index, vismol_object.e_id,
            sqr_color,
        )
        self.vobject_liststore_dict[e_id].append(row)
        vismol_object.coordinate_choice_row = row

    @staticmethod
    def _remove_list_model_row(model, row):
        for position in range(model.get_n_items()):
            if model.get_item(position) is row:
                model.remove(position)
                return True
        return False

    def get_active_vobject (self, e_id = None):
        """ [EN] BUG FIX: replaces a made-up lookup
        (self.p_session.systems[e_id]['vobject']) that was used at three
        call sites in this file (two added by a fix earlier in this same
        project, one pre-existing at 'toolbutton_system_check') -- all
        three crashed with "AttributeError: 'pDynamoSession' object has
        no attribute 'systems'". self.p_session.systems never actually
        exists anywhere in pDynamoSession (confirmed by grepping the
        whole class); the earlier fix mistakenly copied this exact
        pattern from the pre-existing, apparently equally untested
        'toolbutton_system_check' handler, assuming it was a proven,
        working pattern.

        The only thing that IS real is self.p_session.psystem[e_id],
        which gives the pDynamo "system" wrapper object itself -- but
        that object has no back-reference to its own VismolObject either
        (confirmed: no "system.vobject" assignment exists anywhere in
        session.py). The correct way to get "the" VismolObject for a
        given system is the other direction: every VismolObject already
        stores its OWN system's e_id (vismol_object.e_id, set when the
        object was created/added -- see eSession._add_vismol_object() and
        main_treeview.add_vismol_object_to_treeview(), both of which
        already rely on exactly this attribute), so this searches
        vm_session.vm_objects_dic for the (normally unique) object
        belonging to that system, deliberately excluding is_surface
        objects (a system can have surface VismolObjects attached too,
        sharing the same e_id -- see the Surface Analysis Window work --
        which are not "the" molecule object callers here actually want).

        e_id defaults to the currently active system
        (self.p_session.active_id) if not given explicitly. Returns None
        if nothing matches (e.g. no system loaded yet). """
        if e_id is None:
            e_id = self.p_session.active_id
        for vobject in self.vm_session.vm_objects_dic.values ( ):
            if getattr ( vobject, "e_id", None ) == e_id and not getattr ( vobject, "is_surface", False ):
                return vobject
        return None

    def on_main_toolbar_clicked (self, button):
        """ Function doc """
        if button  == self._ui('toolbutton_new_system'):
            self.NewSystemWindow.open_window()
            '''
            from gui.windows.setup.xtb_fragment_charges_window import XtbFragmentChargesWindow
            system = self.p_session.psystem[self.p_session.active_id]
            
            win = XtbFragmentChargesWindow(main=self.window, system=system)
            win.open_window()
            #'''        
        if button  == self._ui('toolbutton_save'):
            
            if self.session_filename == None:
                self.gtk_save_as_file(button)
                
            else:
                self.p_session.save_easyhybrid_session( filename = self.session_filename)
        
        if button  == self._ui('toolbutton_save_as'):
            self.gtk_save_as_file (button)
        
        if button  == self._ui('_show_cell'):
            # [EN] Was "print('Under construction!')" -- the Builder GUI
            # didn't exist at all when this was written (only the
            # backend atom_ops.py/click_mode.py modules did, driven
            # entirely via the terminal's `new`/`placemode`/`add`/`tool`
            # commands -- see easyhybrid_terminal.py). Now that the
            # sidebar exists (gui/windows/builder/builder_sidebar.py),
            # this button opens it -- opening the sidebar IS entering
            # Builder editing mode, see that module's own design note.
            from gui.windows.builder.builder_entry_dialog import choose_and_open_builder
            choose_and_open_builder(self)
            
        if button == self._ui('toolbutton_terminal'):
            if button.get_active ():
                self.terminal_window.open_window()
            else:
                self.terminal_window.close_window(None, None)
        
        if button == self._ui('toolbutton_trajectory_tool1'):
            if button.get_active ():
                self.trajectory_player_window.open_window()
                #self.traj_frame.hide()
            else:
                self.trajectory_player_window.close_window(button = None)
        
        if button == self._ui('button_go_to_atom'):
            self.go_to_atom_window.open_window()

        if button  == self._ui('selections'):
            self.selection_list_window.open_window()

        if button  == self._ui('toolbutton_energy'):
            #self.p_session.run_simulation (parameters = {'simulation_type' : 'Energy', 'system': self.p_session.psystem[self.p_session.active_id]})
            #self.energy_refinement_window.open_window()
            self.single_point_window.open_window()
            
        if button  == self._ui('toolbutton_setup_QCModel'):
            # [EN] BUG FIX: this used to call open_window() with no
            # argument at all -- qcmodel_window.py's open_window()
            # defaults vismol_object to None in that case, and
            # on_button_ok() (clicking "OK" in that window) later crashes
            # with "AttributeError: 'NoneType' object has no attribute
            # 'chains'" inside check_charge_fragmentation(), unrelated to
            # the Builder or anything else -- ANY use of this exact
            # toolbar button hit this. Fixed by passing the active
            # vismol_object, same pattern already used two lines below by
            # 'toolbutton_system_check' in this same handler.
            self.setup_QCModel_window.open_window(self.get_active_vobject())
        
        if button  == self._ui('toolbutton_system_check'): 
            self.get_active_vobject().get_backbone_indexes ()

        if button  == self._ui('toolbutton_geometry_optimization'):
            self.geometry_optimization_window.open_window()
        
        if button  == self._ui('toolbutton_pDynamo_selections'):
            self.pDynamo_selection_window.open_window()
            
            '''
            atom1 = self.vm_session.picking_selections.picking_selections_list[0]
            ##print (atom1.chain, atom1.resn, atom1.resi, atom1.name)
            #print ("%s:%s.%s:%s" %(atom1.chain, atom1.resn, atom1.resi, atom1.name))
            
            _centerAtom ="%s:%s.%s:%s" %(atom1.chain, atom1.resn, atom1.resi, atom1.name)
            _radius =  10.0
            
            self.p_session.selections (_centerAtom, _radius)
            '''
       
        if button  == self._ui('toolbutton_normal_modes'):
            self.normal_modes_window.open_window()
        
        if button  == self._ui('toolbutton_pes_scan'):
            self.PES_scan_window.open_window()
        
        #if button  == self._ui('toolbutton_pes_scan'):
        #    self.PES_scan_window.open_window()
        
        if button  == self._ui('toolbutton_molecular_dynamics'):
            self.molecular_dynamics_window.open_window()
            
        if button  == self._ui('toolbutton_umbrella_sampling'):
            ##print('toolbutton_umbrella_sampling')
            self.umbrella_sampling_window.open_window()
        
        if button  == self._ui('toolbutton_chain_of_states_opt'):
            ##print('toolbutton_umbrella_sampling')
            self.chain_of_states_opt_window.open_window()
        
        if button  == self._ui('toolbutton_monte_carlo'):
            ##print('toolbutton_umbrella_sampling')
            
            self.vm_session.get_dihedral()
            #lista = list(self.vm_session.vobject_names.keys())
            #print(lista)
            #obj = self.vm_session.vobject_names[lista[0]]
            #print(obj.topology)
        
        #if button  == self._ui('button_test'):
        if button  == self._ui('button_task_list'):
            ##print('toolbutton_umbrella_sampling')
            self.process_manager_window.open_window()

        if button  == self._ui('toolbutton_export_img'):
            
            ##print('toolbutton_umbrella_sampling')
            self.save_glArea_image(None)
            #self.vm_session.vm_widget.save_image("saida.png")
    
    def on_main_menu_activate (self, menuitem):
        """ Function doc """
        ##print(menuitem)
        
        if menuitem == self._ui('menuitem_new'):
            self.NewSystemWindow.open_window()
        
        elif menuitem == self._ui('menuitem_open'):
            self.open_gtk_load_files (menuitem)
            
        elif menuitem == self._ui('menuitem_save'):
            if self.session_filename == None:
                self.gtk_save_as_file(menuitem)
            else:
                self.p_session.save_easyhybrid_session( filename = self.session_filename)            

        elif menuitem == self._ui('menuitem_save_as'):
            self.gtk_save_as_file (menuitem)

        elif menuitem == self._ui('menuitem_export'):
            self.export_data_window.open_window(sys_selected = self.p_session.active_id)
        
        elif menuitem == self._ui('menuitem_import'):
            self.import_trajectory_window.open_window()
            
        elif menuitem == self._ui('menuitem_quit'):
            self.on_delete_event(self, None)
            pass
        
        
        #----------------------------------------------------------------------
        #                           E D I T 
        #----------------------------------------------------------------------
        elif menuitem == self._ui('menuitem_make_solvent_box'):
            self.make_solvent_box_window.open_window()
        elif menuitem == self._ui('menuitem_go_to_atom'):
            self.go_to_atom_window.open_window()
        
        elif menuitem == self._ui('menuitem_preferences'):
            self.preferences_window.open_window()
            #print(menuitem, 'menuitem_preferences', self.vm_session.vm_glcore.bckgrnd_color)
            #self.vm_session.vm_glcore.bckgrnd_color = [1,1,1,1]
            #print(menuitem, 'menuitem_preferences', self.vm_session.vm_glcore.bckgrnd_color)
            #self.vm_session.vm_config.gl_parameters["line_width"] =20
            #self.vm_session.vm_glcore.light_position = [0, 10, 100.0]
        #----------------------------------------------------------------------
        
        
        #----------------------------------------------------------------------
        #                           S E L E C T I N G
        #----------------------------------------------------------------------
        elif menuitem == self._ui('menuitem_list'):
            self.selection_list_window.open_window()

        elif menuitem == self._ui('menuitem_seltype_viewing'):
            if self.selection_box_frame:
                self.selection_box_frame.change_toggle_button_selecting_mode_status(False)
            else:
                self.picking_selection_mode = False
            self.vm_session.vm_glcore.queue_draw()
            
        elif menuitem == self._ui('menuitem_seltype_picking'):
            if self.selection_box_frame:
                self.selection_box_frame.change_toggle_button_selecting_mode_status(True)
            else:
                self.picking_selection_mode = True
            self.vm_session.vm_glcore.queue_draw()
        
        
        elif menuitem == self._ui('menuitem_send_to_sel_list'):
            sel_list, sel_resi_table = self.vm_session.build_index_list_from_atom_selection()
            if sel_list:
                
                self.p_session.add_a_new_item_to_selection_list (system_id = self.p_session.active_id, 
                                                                                   indexes = sel_list, 
                                                                                    )
            
            
        elif menuitem == self._ui('menuitem_extend_selection'):
            self.pDynamo_selection_window.open_window()
        
        elif menuitem == self._ui('menuitem_by_atom'):
            self.vm_session.viewing_selection_mode(sel_type = 'atom')
        
        elif menuitem == self._ui('menuitem_by_residue'):
            self.vm_session.viewing_selection_mode(sel_type = 'residue')
        
        elif menuitem == self._ui('menuitem_by_chain'):
            self.vm_session.viewing_selection_mode(sel_type = 'chain')
        
        elif menuitem == self._ui('menuitem_by_molecule'):
            self.vm_session.viewing_selection_mode(sel_type = 'molecule')
        
        elif menuitem == self._ui('menuitem_color'):
            def apply_selection_color(color):
                if color is not None:
                    self.vm_session.set_color(color=[color.red, color.green, color.blue])
            choose_color(self.window, apply_selection_color)
        
        elif menuitem == self._ui('menuitem_set_as_qc'):
            active_id = self.p_session.active_id
            qc_list, residue_dict, vismol_object = self.vm_session.build_index_list_from_atom_selection(return_vobject = True )
            if qc_list:
                self.p_session.psystem[active_id].e_qc_residue_table = residue_dict
                self.p_session.psystem[active_id].e_qc_table = qc_list
                self.run_dialog_set_QC_atoms(vismol_object = vismol_object)

        elif menuitem == self._ui('menuitem_show_qc_only'):
            self.vm_session._set_qc_only_visualization(qc_only=True)

        elif menuitem == self._ui('menuitem_show_all_atoms'):
            self.vm_session._set_qc_only_visualization(qc_only=False)
            
        elif menuitem == self._ui('menuitem_set_as_fixed'):
            self.vm_session.set_as_fixed_atoms()
        
        elif menuitem == self._ui('menuitem_set_as_free'):
            self.vm_session.set_as_free_atoms()
        
        elif menuitem == self._ui('menuitem_prune'):
            #self.vm_session.prune_atoms()
            atomlist, resi_table = self.vm_session.build_index_list_from_atom_selection()

            if atomlist:
                atomlist = list(set(atomlist))
                
                num_of_atoms = len(atomlist)
                name = self.p_session.psystem[self.p_session.active_id].label
                tag  = self.p_session.psystem[self.p_session.active_id].e_tag
                
                def apply_prune(dialog):
                    if dialog.prune:
                        self.p_session.prune_system(
                            selection=atomlist, name=dialog.name, summary=True,
                            tag=dialog.tag, color=dialog.color)
                EasyHybridDialogPrune(self, num_of_atoms, name, tag, on_complete=apply_prune)


        #----------------------------------------------------------------------
        #                            V I E W     M E N U
        #----------------------------------------------------------------------
        elif menuitem == self._ui('menuitem_terminal'):
            button = self._ui('toolbutton_terminal') 
            self.terminal_window.open_window()
            if self.terminal_window.visible:
                button.set_active (True) 
            else:
                self.terminal_window.close_window(button = None)



        elif menuitem == self._ui('menuitem_trajectory_tool'):
            button = self._ui('toolbutton_trajectory_tool1') 
            
            self.trajectory_player_window.open_window()
            if self.trajectory_player_window.Visible:
                button.set_active(True)
            else:
                self.trajectory_player_window.close_window(button = None)

        elif menuitem == self._ui('menuitem_file_tools'):
            if menuitem.get_active():
                self._ui('toolbar1').show()
            else:
                self._ui('toolbar1').hide()
        

        elif menuitem == self._ui('menuitem_seltype_box'):
            if menuitem.get_active():
                self._ui('toolbutton_selection_box').show()
            else:
                self._ui('toolbutton_selection_box').hide()

        
        
        elif menuitem == self._ui('menuitem_check_selection_toolbar'):
            if menuitem.get_active():
                self._ui('toolbar2_selections').show()
            else:
                self._ui('toolbar2_selections').hide()
        
        
        elif menuitem == self._ui('menuitem_check_pDynamo_tools_bar'):
            if menuitem.get_active():
                self._ui('toolbar4_pdynamo_tools').show()
            else:
                self._ui('toolbar4_pdynamo_tools').hide()
        
        elif menuitem == self._ui('menuitem_message_window'):
            if menuitem.get_active():
                self.bottom_notebook.widget.show()
            else:
                self.bottom_notebook.widget.hide()
        
        #----------------------------------------------------------------------
        elif menuitem == self._ui('menuitem_check_xyz_axes'):
            if menuitem.get_active():
                self.vm_session.show_axes()
            else:
                self.vm_session.hide_axes()
        
        
        elif menuitem == self._ui('menuitem_bg_color'):
            def apply_background_color(color):
                if color is not None:
                    self.vm_session.vm_glcore.bckgrnd_color = [color.red, color.green, color.blue, 1]
            choose_color(self.window, apply_background_color)
                #system = self.p_session.psystem[self.p_session.active_id]
                #self.change_reference_color(system, new_color)
        #----------------------------------------------------------------------
        
        
        
        
        
        
        
        
        
        
        #----------------------------------------------------------------------
        #                            S Y S T E M 
        #----------------------------------------------------------------------
        elif menuitem == self._ui('menuitem_info'):
            system = self.p_session.psystem[self.p_session.active_id]
            window = InfoWindow(system)
        
        elif menuitem == self._ui('menuitem_rename'):
            e_id = self.p_session.active_id
            v_id = -1
            self.preferences = PreferencesWindow(main = self , 
                                         e_id = e_id     ,
                                         v_id = v_id     )
        
        
        elif menuitem == self._ui('menuitem_qc_setup'):
            # [EN] Same bug/fix as 'toolbutton_setup_QCModel' above --
            # see that comment for the full traceback/reasoning.
            self.setup_QCModel_window.open_window(self.get_active_vobject())

        elif menuitem == self._ui('menuitem_opls_parameters'):
            self.opls_parameters_window.open_window()
            
        elif menuitem == self._ui('menuitem_show_cell'):
            system = self.p_session.psystem[self.p_session.active_id]
            for key, vobject in self.vm_session.vm_objects_dic.items():
                self.vm_session.show_cell (vobject)
            
            
        elif menuitem == self._ui('menuitem_hide_cell'):
            system = self.p_session.psystem[self.p_session.active_id]
            for key, vobject in self.vm_session.vm_objects_dic.items():
                self.vm_session.hide_cell (vobject)
            #if self._ui('toogle_show_cell').get_active():
            #    print('toogle_show_cell - show', self._ui('toogle_show_cell').get_active())
            #else:
            #    print('toogle_show_cell - hide', self._ui('toogle_show_cell').get_active())
        
        #elif menuitem == self._ui('menuitem_cell_and_symmetry'):
        #    print ('menuitem_cell_and_symmetry')

        elif menuitem == self._ui('menuitem_edit_cell'):
            self.edit_cell_window.open_window()
            
            
            
        elif menuitem == self._ui('menuitem_change_color'):
            #selection               = self.selections[self.current_selection]
            def apply_reference_color(color):
                if color is not None:
                    system = self.p_session.psystem[self.p_session.active_id]
                    self.change_reference_color(system, [color.red, color.green, color.blue])
            choose_color(self.window, apply_reference_color)
        
        elif menuitem == self._ui('menuitem_remove_restraints'): 
            #print('menuitem_remove_restraints')
            system = self.p_session.psystem[self.p_session.active_id]
            system.e_restraint_counter = 0
            system.e_restraints_dict   = {}
        
        elif menuitem == self._ui('menuitem_custom_colors'): 
            system = self.p_session.psystem[self.p_session.active_id]
            name = system.label
            num_of_custom_colors = len(system.e_custom_colors)
            
            msg = 'You are about to remove {} customized atom color list(s) from the system:\n\n{}\n\nDo you want to continue?'.format(num_of_custom_colors,name )
            dialog = SimpleDialog(self )
            yes_or_no = dialog.question (msg)
            if yes_or_no:
                system.e_custom_colors = []
            else:
                pass



            
        elif menuitem == self._ui('menuitem_remove_fixed'): 
            system = self.p_session.psystem[self.p_session.active_id]
            
            for key, vobject in self.vm_session.vm_objects_dic.items():
                if vobject.e_id == self.p_session.active_id:
                    for index, atom in vobject.atoms.items():
                        atom.color = atom._init_color()
                    
                    #for index in system.e_fixed_table:
                    #    atom = vobject.atoms[index] 
                    #    atom.color = atom._init_color()
                    #    #print(atom, index, atom.index)
                    self.p_session._apply_fixed_representation_to_vobject(system_id = None, vismol_object = vobject)
                    self.p_session._apply_QC_representation_to_vobject   (system_id = None, vismol_object = vobject)                    
            
            self.vm_session.vm_glcore.queue_draw()
            system.e_fixed_table = []
            system.freeAtoms = None            
            self.refresh_widgets()



        elif menuitem == self._ui('menuitem_fragment_charges'):
            from gui.windows.setup.xtb_fragment_charges_window import XtbFragmentChargesWindow
            system = self.p_session.psystem[self.p_session.active_id]
            
            win = XtbFragmentChargesWindow(main=self, system=system)
            win.open_window()
            
            
        elif menuitem == self._ui('menuitem_charge_inspection'): 
            TrueFalse, msg = self.p_session.check_for_fragmented_charges()
            #if true_or_false:
            if TrueFalse:
                self.simple_dialog.info(msg = msg )
            else:
                self.simple_dialog.error(msg = msg )
        
        
        elif menuitem == self._ui('menuitem_nb_model'): 
            self.p_session.remove_NBModel()
            self.refresh_main_statusbar()
        
        elif menuitem == self._ui('menuitem_PES_data'): 
            msg = self.p_session.remove_PES_data()
            #if TrueFalse:
            self.simple_dialog.info(msg = msg )
            #else:
            #    self.simple_dialog.error(msg = msg )
        
        
        elif menuitem == self._ui('menuitem_new_nb_model'): 
            self.p_session.define_NBModel()
            self.refresh_main_statusbar()
            
            
            
        elif menuitem == self._ui('menuitem_remove_qc'): 
            system = self.p_session.psystem[self.p_session.active_id]
            '''
            # The QC region will be deleted. First we have to disable 
            # the QC representation and restore the MM representation 
            # to the atoms.
            '''
            self.p_session.clean_QC_representation_to_vobject()

            system.qcModel = None
            #for vismol_object in self.vm_session.vm_objects_dic.values():
            #    if vismol_object.e_id == system.e_id:
            #        self.p_session._apply_QC_representation_to_vobject   (system_id = None, vismol_object = vismol_object)                   
            self.vm_session.vm_glcore.queue_draw()
            self.refresh_widgets()

        
        elif menuitem == self._ui('menuitem_solvate'): 
            self.solvate_system_window.open_window()
        
        elif menuitem == self._ui('menuitem_merge'): 
            """ Function doc """
            system = self.p_session.psystem[self.p_session.active_id]
            e_id = system.e_id
            self.merge_system_window.selected_system_id = e_id
            self.merge_system_window.open_window()
            
        
        
        
        elif menuitem == self._ui('menuitem_clone'): 
            system = self.p_session.psystem[self.p_session.active_id]
            
            backup = []
            backup.append(system.tree_row)
            backup.append(system.system_choice_row)
            system.tree_row   = None
            system.system_choice_row  = None
            
            new_system = Clone(system)
            system.tree_row   = backup[0]
            system.system_choice_row  = backup[1]
            #print('menuitem_clone')
            
            new_system = self.p_session.add_new_system_to_psession (system = new_system)
            self.main_treeview.add_new_system_to_treeview (new_system)
            ff  =  getattr(new_system.mmModel, 'forceField', "None")
        
            self.bottom_notebook.status_teeview_add_new_item(message = 'New System:  {} ({}) - Force Field:  {}'.format(new_system.label, new_system.e_tag, ff), system = new_system)
            self.p_session._add_vismol_object_to_easyhybrid_session (new_system, True) #, name = 'olha o  coco')
            #----------------------------------------------------------------------
        elif menuitem == self._ui('menuitem_prune_to_qc_region'): 
            system = self.p_session.psystem[self.p_session.active_id]
            
            new_system = system.PruneToQCRegion()
            new_system = self.p_session.add_new_system_to_psession (system = new_system)            
            self.main_treeview.add_new_system_to_treeview (new_system)
            # Determine the force field used
            # sys_type = {0: 'AMBER', 1: 'CHARMM'}        
            ff  =  getattr(new_system.mmModel, 'forceField', "None")
            
            
            # Add information about the new system to the status treeview
            self.bottom_notebook.status_teeview_add_new_item(message = 'New System:  {} ({}) - Force Field:  {}'.format(system.label, system.e_tag, ff), system =system)
            
            # Add the system as a vismol object to the easyhybrid session
            self.p_session._add_vismol_object_to_easyhybrid_session (new_system, True)  
        
        #---------------------------------------------------------------------------------------------------------
        
        
        elif menuitem == self._ui('menuitem_energy'): 
            self.single_point_window.open_window()
            
        elif menuitem == self._ui('menuitem_geometry_optimization'):
            self.geometry_optimization_window.open_window()
            
        elif menuitem == self._ui('menuitem_molecular_dynamics'):
            self.molecular_dynamics_window.open_window()
            
        elif menuitem == self._ui('menuitem_normal_modes'):
            self.normal_modes_window.open_window()
            
        elif menuitem == self._ui('menuitem_rection_coordinate_scans'):
            self.PES_scan_window.open_window()
        
        elif menuitem == self._ui('menuitem_advanced_rc_scans'):
            self.PES_advanced_scan_window.open_window()
            
        elif menuitem == self._ui('menuitem_nudged_elastic_band'):
            self.chain_of_states_opt_window.open_window()

        elif menuitem == self._ui('menuitem_transition_state_search'):
            self.transition_state_search_window.open_window()

        elif menuitem == self._ui('menuitem_reaction_path'):
            self.reaction_path_window.open_window()

        elif menuitem == self._ui('menuitem_cpr'):
            self.conjugate_peak_refinement_window.open_window()
            
        elif menuitem == self._ui('menuitem_umbrella_sampling'):
            self.umbrella_sampling_window.open_window()
        


        #----------------------------------------------------------------------
        #                        A N A L Y S I S 
        #----------------------------------------------------------------------


        elif menuitem == self._ui('menuitem_energy_analysis'):
            self.PES_analysis_window.open_window()

        elif menuitem == self._ui('menuitem_mormal_modes_analysis'):
            self.normal_modes_analysis_window.open_window()
        
        elif menuitem == self._ui('menuitem_surface_analysis'):
            self.surface_analysis_window.open_window()
            #self.surface_list_window.open_window()

        
        elif menuitem == self._ui('menuitem_energy_refinement'):
            self.energy_refinement_window.open_window()
        
        elif menuitem == self._ui('menuitem_align_trajectory'):
            #print('Hello!!')
            self.align_trajectory_window.open_window()
            #self.energy_refinement_window.open_window()
        
        elif menuitem == self._ui('menuitem_reimaging'):
            #print('reimaging_trajectory!!')
            self.reimaging_trajectory_window.open_window()
            #self.energy_refinement_window.open_window()
        
        elif menuitem == self._ui('menuitem_d_a_d_analysis'):
            self.distance_angle_dihedral_analysis_window.open_window()
        
        elif menuitem == self._ui('menuitem_rama'):
            self.ramachandran_analysis_window.open_window()
        
        elif menuitem == self._ui('menuitem_RMSD_tool'):
            #self.rmsd_tool_window.open_window()
            self.rmsd_analysis_window.open_window()

        elif menuitem == self._ui('menuitem_RDF_analysis'):
            self.rdf_analysis_window.open_window()

        elif menuitem == self._ui('menuitem_density_analysis'):
            self.density_analysis_window.open_window()

        elif menuitem == self._ui('menuitem_RMSF_analysis'):
            self.rmsf_analysis_window.open_window()
        
        elif menuitem == self._ui('test_histograms'):
            from util.easyplot import ImagePlot, XYPlot
            import random
            self.plot = XYPlot()
            
            
            logs = [
                #'~/PROJECTS/OMP/HPC_19_09_2024/5-Hu_OMPD_QC196_AMBER_XTB QC MODEL_QC196_umb_sam/data_collection/window0.ptRes_Values_simpler2.dat' ,
                #'~/PROJECTS/OMP/HPC_19_09_2024/5-Hu_OMPD_QC196_AMBER_XTB QC MODEL_QC196_umb_sam/data_collection/window1.ptRes_Values_simpler2.dat' ,
                #'~/PROJECTS/OMP/HPC_19_09_2024/5-Hu_OMPD_QC196_AMBER_XTB QC MODEL_QC196_umb_sam/data_collection/window2.ptRes_Values_simpler2.dat' ,
                #'~/PROJECTS/OMP/HPC_19_09_2024/5-Hu_OMPD_QC196_AMBER_XTB QC MODEL_QC196_umb_sam/data_collection/window3.ptRes_Values_simpler2.dat' ,
                #'~/PROJECTS/OMP/HPC_19_09_2024/5-Hu_OMPD_QC196_AMBER_XTB QC MODEL_QC196_umb_sam/data_collection/window4.ptRes_Values_simpler2.dat' ,
                #'~/PROJECTS/OMP/HPC_19_09_2024/5-Hu_OMPD_QC196_AMBER_XTB QC MODEL_QC196_umb_sam/data_collection/window5.ptRes_Values_simpler2.dat' ,
                #'~/PROJECTS/OMP/HPC_19_09_2024/5-Hu_OMPD_QC196_AMBER_XTB QC MODEL_QC196_umb_sam/data_collection/window6.ptRes_Values_simpler2.dat' ,
                #'~/PROJECTS/OMP/HPC_19_09_2024/5-Hu_OMPD_QC196_AMBER_XTB QC MODEL_QC196_umb_sam/data_collection/window7.ptRes_Values_simpler2.dat' ,
                #'~/PROJECTS/OMP/HPC_19_09_2024/5-Hu_OMPD_QC196_AMBER_XTB QC MODEL_QC196_umb_sam/data_collection/window8.ptRes_Values_simpler2.dat' ,
                #'~/PROJECTS/OMP/HPC_19_09_2024/5-Hu_OMPD_QC196_AMBER_XTB QC MODEL_QC196_umb_sam/data_collection/window9.ptRes_Values_simpler2.dat' ,
                #'~/PROJECTS/OMP/HPC_19_09_2024/5-Hu_OMPD_QC196_AMBER_XTB QC MODEL_QC196_umb_sam/data_collection/window10.ptRes_Values_simpler2.dat',
                #'~/PROJECTS/OMP/HPC_19_09_2024/5-Hu_OMPD_QC196_AMBER_XTB QC MODEL_QC196_umb_sam/data_collection/window11.ptRes_Values_simpler2.dat',
                #'~/PROJECTS/OMP/HPC_19_09_2024/5-Hu_OMPD_QC196_AMBER_XTB QC MODEL_QC196_umb_sam/data_collection/window12.ptRes_Values_simpler2.dat',
                #'~/PROJECTS/OMP/HPC_19_09_2024/5-Hu_OMPD_QC196_AMBER_XTB QC MODEL_QC196_umb_sam/data_collection/window13.ptRes_Values_simpler2.dat',
                #'~/PROJECTS/OMP/HPC_19_09_2024/5-Hu_OMPD_QC196_AMBER_XTB QC MODEL_QC196_umb_sam/data_collection/window14.ptRes_Values_simpler2.dat',
                #'~/PROJECTS/OMP/HPC_19_09_2024/5-Hu_OMPD_QC196_AMBER_XTB QC MODEL_QC196_umb_sam/data_collection/window15.ptRes_Values_simpler2.dat',
                #'~/PROJECTS/OMP/HPC_19_09_2024/5-Hu_OMPD_QC196_AMBER_XTB QC MODEL_QC196_umb_sam/data_collection/window16.ptRes_Values_simpler2.dat',
                #'~/PROJECTS/OMP/HPC_19_09_2024/5-Hu_OMPD_QC196_AMBER_XTB QC MODEL_QC196_umb_sam/data_collection/window17.ptRes_Values_simpler2.dat',
                #'~/PROJECTS/OMP/HPC_19_09_2024/5-Hu_OMPD_QC196_AMBER_XTB QC MODEL_QC196_umb_sam/data_collection/window18.ptRes_Values_simpler2.dat',
                #'~/PROJECTS/OMP/HPC_19_09_2024/5-Hu_OMPD_QC196_AMBER_XTB QC MODEL_QC196_umb_sam/data_collection/window19.ptRes_Values_simpler2.dat',
                #'~/PROJECTS/OMP/HPC_19_09_2024/5-Hu_OMPD_QC196_AMBER_XTB QC MODEL_QC196_umb_sam/data_collection/window20.ptRes_Values_simpler2.dat',
                #'~/PROJECTS/OMP/HPC_19_09_2024/5-Hu_OMPD_QC196_AMBER_XTB QC MODEL_QC196_umb_sam/data_collection/window21.ptRes_Values_simpler2.dat',
                #'~/PROJECTS/OMP/HPC_19_09_2024/5-Hu_OMPD_QC196_AMBER_XTB QC MODEL_QC196_umb_sam/data_collection/window22.ptRes_Values_simpler2.dat',
                #'~/PROJECTS/OMP/HPC_19_09_2024/5-Hu_OMPD_QC196_AMBER_XTB QC MODEL_QC196_umb_sam/data_collection/window24.ptRes_Values_simpler2.dat',
       
                '~/Documents/teste/output_window0.ptRes_histogram.dat',
                '~/Documents/teste/output_window1.ptRes_histogram.dat',
                '~/Documents/teste/output_window2.ptRes_histogram.dat',
                '~/Documents/teste/output_window3.ptRes_histogram.dat',
                '~/Documents/teste/output_window4.ptRes_histogram.dat',
                '~/Documents/teste/output_window5.ptRes_histogram.dat',
                '~/Documents/teste/output_window6.ptRes_histogram.dat',
                '~/Documents/teste/output_window7.ptRes_histogram.dat',
                '~/Documents/teste/output_window8.ptRes_histogram.dat',
                '~/Documents/teste/output_window9.ptRes_histogram.dat',
                '~/Documents/teste/output_window10.ptRes_histogram.dat',
                '~/Documents/teste/output_window11.ptRes_histogram.dat',
                '~/Documents/teste/output_window12.ptRes_histogram.dat',
                '~/Documents/teste/output_window13.ptRes_histogram.dat',
                '~/Documents/teste/output_window14.ptRes_histogram.dat',
                '~/Documents/teste/output_window15.ptRes_histogram.dat',
                '~/Documents/teste/output_window16.ptRes_histogram.dat',
                '~/Documents/teste/output_window17.ptRes_histogram.dat',
                '~/Documents/teste/output_window18.ptRes_histogram.dat',
                '~/Documents/teste/output_window19.ptRes_histogram.dat',
                '~/Documents/teste/output_window20.ptRes_histogram.dat',
                '~/Documents/teste/output_window21.ptRes_histogram.dat',
                '~/Documents/teste/output_window22.ptRes_histogram.dat',
                '~/Documents/teste/output_window23.ptRes_histogram.dat',
       
             
            # '~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_phi_0.ptRes_Values.dat'  ,
            # '~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_phi_1.ptRes_Values.dat'  ,
            # '~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_phi_2.ptRes_Values.dat'  ,
            # '~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_phi_3.ptRes_Values.dat'  ,
            # '~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_phi_4.ptRes_Values.dat'  ,
            # '~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_phi_5.ptRes_Values.dat'  ,
            # '~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_phi_6.ptRes_Values.dat'  ,
            # '~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_phi_7.ptRes_Values.dat'  ,
            # '~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_phi_8.ptRes_Values.dat'  ,
            # '~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_phi_9.ptRes_Values.dat'  ,
            # '~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_phi_10.ptRes_Values.dat' ,
            # '~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_phi_11.ptRes_Values.dat' ,
            # '~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_phi_12.ptRes_Values.dat' ,
            # '~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_phi_13.ptRes_Values.dat' ,
            # '~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_phi_14.ptRes_Values.dat' ,
            # '~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_phi_15.ptRes_Values.dat' ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_phi_16.ptRes_Values.dat' ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_phi_17.ptRes_Values.dat' ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_phi_18.ptRes_Values.dat' ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_phi_19.ptRes_Values.dat' ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_phi_20.ptRes_Values.dat' ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_phi_21.ptRes_Values.dat' ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_phi_22.ptRes_Values.dat' ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_phi_23.ptRes_Values.dat' ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_phi_24.ptRes_Values.dat' ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_phi_25.ptRes_Values.dat' ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_phi_26.ptRes_Values.dat' ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_phi_27.ptRes_Values.dat' ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_phi_28.ptRes_Values.dat' ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_phi_29.ptRes_Values.dat' ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_phi_30.ptRes_Values.dat' ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_phi_31.ptRes_Values.dat' ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_phi_32.ptRes_Values.dat' ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_phi_33.ptRes_Values.dat' ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_phi_34.ptRes_Values.dat' ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_phi_35.ptRes_Values.dat' ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_psi_0.ptRes_Values.dat'  ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_psi_1.ptRes_Values.dat'  ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_psi_2.ptRes_Values.dat'  ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_psi_3.ptRes_Values.dat'  ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_psi_4.ptRes_Values.dat'  ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_psi_5.ptRes_Values.dat'  ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_psi_6.ptRes_Values.dat'  ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_psi_7.ptRes_Values.dat'  ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_psi_8.ptRes_Values.dat'  ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_psi_9.ptRes_Values.dat'  ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_psi_10.ptRes_Values.dat' ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_psi_11.ptRes_Values.dat' ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_psi_12.ptRes_Values.dat' ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_psi_13.ptRes_Values.dat' ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_psi_14.ptRes_Values.dat' ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_psi_15.ptRes_Values.dat' ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_psi_16.ptRes_Values.dat' ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_psi_17.ptRes_Values.dat' ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_psi_18.ptRes_Values.dat' ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_psi_19.ptRes_Values.dat' ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_psi_20.ptRes_Values.dat' ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_psi_21.ptRes_Values.dat' ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_psi_22.ptRes_Values.dat' ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_psi_23.ptRes_Values.dat' ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_psi_24.ptRes_Values.dat' ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_psi_25.ptRes_Values.dat' ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_psi_26.ptRes_Values.dat' ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_psi_27.ptRes_Values.dat' ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_psi_28.ptRes_Values.dat' ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_psi_29.ptRes_Values.dat' ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_psi_30.ptRes_Values.dat' ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_psi_31.ptRes_Values.dat' ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_psi_32.ptRes_Values.dat' ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_psi_33.ptRes_Values.dat' ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_psi_34.ptRes_Values.dat' ,
            #'~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_psi_35.ptRes_Values.dat' ,           
            ]
            
            
            
            
            for i , log in enumerate(logs):
                
                X = [] 
                Y = [] 
                
                r = random.random()
                g = random.random()
                b = random.random()
                rgb = [r,g,b,]
                
                #print(rgb)
                data = open(log, 'r')
                for line in data:
                    line2 = line.split()
                    X.append(float(line2[0]) )
                    Y.append(float(line2[1]))
                #for i  in range(10):
                #    X.append(i ) 
                #    Y.append(i**2)
                self.plot.add ( X = X, Y = Y,
                                symbol = None, sym_color = [1,1,1], sym_fill = False, 
                                line = 'solid', line_color = rgb, energy_label = None)
            
            #X = []
            #Y = []
            #data = open('~/programs/pDynamo3/scratch/examples-3.1.2/bAlaPhiPsiPMF/generatedFiles/bAla_phi_14.ptRes_Values.dat', 'r')
            #
            #for line in data:
            #    line2 = line.split()
            #    X.append(float(line2[0]) )
            #    Y.append(float(line2[1]))
            #self.plot.add ( X = X, Y = Y)
            #self.plot.Ymax = 100
            #print(self.plot.Ymax_list)
            
            self.plot.Ymax_list= [100]
            window =  Gtk.Window()
            window.set_child(self.plot)
            window.present()
        
        
        elif menuitem == self._ui('menuitem_WHAM'):
            self.WHAM_window.open_window()
        
        
        
        elif menuitem == self._ui('menuitem_about'):
            dialog = Gtk.AboutDialog(transient_for=self.window, modal=True)
            dialog.set_program_name('EasyHybrid')
            dialog.set_version('4.0.0 Beta')
            dialog.set_comments(
                'EasyHybrid is a molecular modeling environment based on pDynamo3, '
                'with a focus on QC/MM hybrid simulations.'
            )
            dialog.set_website('https://github.com/ferbachega/EasyHybrid3')
            dialog.set_website_label('EasyHybrid - project page on GitHub')
            dialog.set_authors([
                'Fernando Bachega (main developer)',
                'Carlos Cerqueiros',
                'Luis Fernando S. Timmers',
                'Martin John Field',
            ])
            dialog.set_license_type(Gtk.License.GPL_3_0)
            logo_path = os.path.join(self.home, 'src/gui/icons/easyhybrid_solo_100x100.png')
            if os.path.isfile(logo_path):
                dialog.set_logo(GdkPixbuf.Pixbuf.new_from_file(logo_path))
            dialog.connect("response", lambda current_dialog, _response: current_dialog.destroy())
            dialog.present()

    def gtk_save_as_file(self, button, on_saved=None):
        """Save the current EasyHybrid session using a GTK4 file chooser."""
        from gi.repository import Gio
        dialog = Gtk.FileChooserDialog(
            title="Save File", transient_for=self.window,
            action=Gtk.FileChooserAction.SAVE,
        )
        dialog.add_buttons(
            "Cancel", Gtk.ResponseType.CANCEL,
            "Save", Gtk.ResponseType.OK,
        )
        dialog.set_current_name("untitled.easy")
        documents = os.path.join(os.path.expanduser("~"), "Documents")
        if os.path.isdir(documents):
            dialog.set_current_folder(Gio.File.new_for_path(documents))

        def on_response(chooser, response):
            selected = chooser.get_file()
            chooser.destroy()
            if response == Gtk.ResponseType.OK and selected is not None:
                filename = selected.get_path()
                dprint("File selected: " + filename)
                self.p_session.save_easyhybrid_session(filename=filename)
                if on_saved is not None:
                    on_saved()
            elif response == Gtk.ResponseType.CANCEL:
                dprint("Save operation canceled.")

        dialog.connect("response", on_response)
        dialog.present()

    def open_gtk_load_files (self, button):
        '''Easyhybrid and pkl pdynamo file search '''
        filters = []

        file_filter = Gtk.FileFilter()
        file_filter.set_name("EasyHybrid / pDynamo files (*.easy, *.pkl, *.yaml)")
        file_filter.add_pattern("*.easy")
        file_filter.add_pattern("*.pkl")
        file_filter.add_pattern("*.yaml")

        filters.append(file_filter)

        
        # EasyHybrid session
        file_filter = Gtk.FileFilter()
        file_filter.set_name("EasyHybrid session files (*.easy)")
        file_filter.add_pattern("*.easy")
        filters.append(file_filter)

        # pDynamo PKL
        file_filter = Gtk.FileFilter()
        file_filter.set_name("pDynamo3 system files (*.pkl)")
        file_filter.add_pattern("*.pkl")
        filters.append(file_filter)

        # YAML
        file_filter = Gtk.FileFilter()
        file_filter.set_name("YAML files (*.yaml)")
        file_filter.add_pattern("*.yaml")
        filters.append(file_filter)

        # All files
        file_filter = Gtk.FileFilter()
        file_filter.set_name("All files")
        file_filter.add_pattern("*")
        filters.append(file_filter)

        self.filechooser.open(
            callback=lambda filename: self.vm_session.load(filename) if filename else None,
            filters=filters,
        )

    def run_dialog_set_QC_atoms (self, _type = None, vismol_object = None):
        """ Function doc """
        dialog = EasyHybridDialogSetQCAtoms(self.window)
        def on_response(current_dialog, response):
            current_dialog.destroy()
            if response == Gtk.ResponseType.YES:
                self.setup_QCModel_window.open_window(vismol_object)
        dialog.connect("response", on_response)
        dialog.present()

    def uptade_interface_windows_and_dialogs (self, parameters = None):
        """ Function doc """
        for window in self.window_list:
            #try:
            window.update()
            #except:
            #    pass    
            #if window.Visible:
            #    window.update()
        
    def change_reference_color (self, system, new_color):
        """ Function doc """
        system.e_color_palette['C'] = new_color
        sqr_color                   = get_colorful_square_pixel_buffer (system)
        e_id =system.e_id
        #print(system.system_choice_row, sqr_color)
        self.system_choice_rows[e_id].icon = sqr_color
        self.main_treeview.system_rows[e_id].color = sqr_color
        
        for index, vobject in self.vm_session.vm_objects_dic.items():
            
           
            tree_row = vobject.tree_row
            if tree_row.system_id == system.e_id:
                
                #If vobject is a surface, no pixelsqr on treeview
                is_surface = getattr(vobject, 'is_surface', False)
                if is_surface:                
                    tree_row.color = None
                else:
                    tree_row.color = sqr_color
                if vobject.coordinate_choice_row is not None:
                    vobject.coordinate_choice_row.icon = sqr_color
            else:
                pass

    def rename_tag (self, e_id, tag):
        """ Function doc """
        #(model, iter) = selection.get_selected()
        #e_id     = model.get_value(iter, 0)
        self.p_session.psystem[e_id].e_tag = tag

    def rename (self, e_id = None, v_id = -1, name = None):
        #print(name, v_id,  e_id)
        #print(name)
        if v_id == -1: #.change the header
            row = self.main_treeview.system_rows[e_id] 
            row.name = str(e_id)+' - '+ name
            self.p_session.psystem[e_id].label  = name
            
            self.system_choice_rows[e_id].name = str(e_id)+' - '+ name
  
        else:
            #print(self.vm_session.vobject_names.values())
            if name in self.vm_session.vobject_names.keys():
                dprint('Invalid name.')
                return False

            else:
                row = self.vm_session.vm_objects_dic[v_id].tree_row
                row.name = name
                
                old_name = self.vm_session.vm_objects_dic[v_id].name          
                self.vm_session.vobject_names.pop(old_name)
                

                self.vm_session.vm_objects_dic[v_id].name = name
                
                self.vm_session.vobject_names[name] = self.vm_session.vm_objects_dic[v_id]
                #print('aqui')
                try:
                    self.vm_session.vm_objects_dic[v_id].coordinate_choice_row.name = name
                except:
                    #means that it is surface 
                    pass
    
    def delete_system (self, system_e_id = None ):
        """Remove a system and its associated vobjects from the session.

        This method deletes a system identified by its `system_e_id` from all
        relevant data structures, including:
            1. `vm_objects_dic` in `vm_session`.
            2. `vobject_liststore_dict` in the main object.
            3. `vobject_names` in `vm_session`.
            4. `system_liststore` and `treestore` in the main object.
            5. `psystem` in the `p_session` object.

        Args:
            system_e_id (int, optional): Identifier of the system (access key).
                This value can be obtained from `vobject.e_id`. If `None`, 
                nothing will be removed.

        Returns:
            None
        """      
        
        if system_e_id != None:
            
            '''organizing the list of vobjects that should be removed from vm_object_dic'''
            pop_list = []
            for index, vobject in self.vm_session.vm_objects_dic.items():
                if vobject.e_id == system_e_id:                   
                    self.main_treeview.remove_row(vobject.tree_row)
                    pop_list.append(index)
            
            '''removing from vm_object_dic'''
            for index in pop_list:
                dprint('removing sys = {}, obj = {}, name = {}'.format(system_e_id, 
                                                                      index,
                                                                      self.vm_session.vm_objects_dic[index].name))
                
                name  = self.vm_session.vm_objects_dic[index].name
                self.vm_session.vm_objects_dic.pop(index)
                self.vm_session.vobject_names.pop(name)
            
            '''removing vobject from vobject_liststore_dict'''
            self.vobject_liststore_dict.pop(system_e_id)
            
            
            #  - - - - - - - - removing system treeview items - - - - - - - - - - -
            system = self.p_session.get_system(index = system_e_id)
            e_id = system.e_id 
            self._remove_list_model_row(
                self.system_liststore, self.system_choice_rows.pop(e_id)
            )
            self.main_treeview.remove_row(self.main_treeview.system_rows[e_id])
            # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
            
            # Remove the system from p_session and update the graphical view.
            a = self.p_session.delete_system(system_e_id)

            # [BUG FIX] active_id was never updated here -- if the system
            # just removed was the active one (the common case), active_id
            # kept pointing at a key delete_system() had just popped from
            # psystem. Nothing crashed immediately, but the very next
            # thing that touched "the active system" (e.g. File > Save As
            # -> get_active_system_text_from_textbuffer()) blew up with
            # KeyError instead. Point active_id at another remaining
            # system if there is one, otherwise reset to the same empty
            # placeholder state used by pDynamoSession.__init__/restart().
            if self.p_session.active_id not in self.p_session.psystem:
                remaining_ids = list(self.p_session.psystem.keys())
                if remaining_ids:
                    self.p_session.active_id = remaining_ids[-1]
                else:
                    self.p_session.active_id = 0
                    self.p_session.psystem[0] = None
                    self.vobject_liststore_dict[0] = Gio.ListStore.new(
                        CoordinateChoiceRow
                    )

            self.vm_session.vm_glcore.queue_draw()

            # Keep the restraint/selection window in sync so it doesn't keep
            # stale rows pointing at the now-removed system id.
            self.selection_list_window.update_window()

    def delete_vm_object (self, vm_object_index = None):
        """ 
        
        vm_object_index = is the access key to the object. You can get it from vobject.index
        
        '''When an object is removed it has to be removed from the treeview and 
        vobject_liststore_dict, in addition to the vm_object_dic in the .vm_session.'''
        
        """
        if vm_object_index != None:
            #  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
            vobject = self.vm_session.vm_objects_dic[vm_object_index]
            #  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
            
            name = vobject.name
            #  - - - - REMOVING plotting data FROM system.e_logfile_data - - - - - -
            system = self.p_session.psystem[vobject.e_id]
            #print(vobject.e_id, vm_object_index)
            if vm_object_index in system.e_logfile_data.keys():
                dprint ('deleting plotting data...')
                system.e_logfile_data[vm_object_index] = None
                system.e_logfile_data.pop(vm_object_index)
            #  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
            
            #  - - - - - - REMOVING vobj FROM  vobject_liststore_dict - - - - - - -
            if getattr(vobject, 'is_surface', False):
                pass
            else:
                self._remove_list_model_row(
                    self.vobject_liststore_dict[vobject.e_id],
                    vobject.coordinate_choice_row,
                )
            #  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
            
            #  - - - - - - REMOVING vobj FROM  treestore - - - - - - -
            self.main_treeview.remove_row(vobject.tree_row)
            #  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
            
            #  - - - - - - - - REMOVING vobj FROM vm_object_dic - - - - - - - - - -
            self.vm_session.vm_objects_dic[vm_object_index] = None
            self.vm_session.vm_objects_dic.pop(vm_object_index)# = None
            self.vm_session.vobject_names.pop(name)# = None
            #  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

            self.vm_session.vm_glcore.queue_draw()
        
    def refresh_main_statusbar(self, message = None, psystem = None):
        """ Function doc """
        psystem = self.p_session.psystem[self.p_session.active_id]
            
        if message:
            string = message
            #print(string)
            #self.statusbar_main.push(1,string)
        else:

            #string = 'System: {}  Size: {}  '.format()
            name    = psystem.label
            size    = len(psystem.atoms)
            string = 'system: {}    atoms: {}    '.format(name, size)

            if psystem.qcModel:
                hamiltonian   = getattr(psystem.qcModel, 'hamiltonian', False)
                if hamiltonian:
                    pass
                else:
                    try:
                        itens = psystem.qcModel.SummaryItems()
                        #print(itens)
                        hamiltonian = itens[0][0]
                    except:
                        hamiltonian = 'external'
                    
                    
                    
                
                n_QC_atoms    = len(list(psystem.qcState.pureQCAtoms))
                
                
                summary_items = psystem.electronicState.SummaryItems()
                
                string += 'hamiltonian: {}    QC atoms: {}    QC charge: {}    spin multiplicity {}    '.format(  hamiltonian, 
                                                                                                                  n_QC_atoms,
                                                                                                                  summary_items[1][1],
                                                                                                                  summary_items[2][1],
                                                                                                                 )
                
            n_fixed_atoms = len(psystem.e_fixed_table)
            string += 'fixed atoms: {}    '.format(n_fixed_atoms)
            
            if psystem.mmModel:
                forceField = psystem.mmModel.forceField
                string += 'force field: {}    '.format(forceField)
            
                if psystem.nbModel:
                    nbmodel = psystem.mmModel.forceField
                    string += 'nbModel: True    '
                    
                    summary_items = psystem.nbModel.SummaryItems()
                    
                
                else:
                    string += 'nbModel: False    '
                
                
                if psystem.symmetry:
                    #nbmodel = psystem.mmModel.forceField
                    string += 'PBC: True    symmetry: {}    '.format( psystem.symmetry.crystalSystem.label)
                    #print(psystem.symmetry)
                    #print(psystem.symmetryParameters)
                    #summary_items = psystem.nbModel.SummaryItems()
                    
                
                else:
                    string += 'PBC: False    '
            
            
            
            
            
            '''
            color_palette = self.p_session.get_color_palette()
            color     = color_palette['C']
            res_color = [int(color[0]*255),int(color[1]*255),int(color[2]*255)] 
            #swatch    = self.getColouredPixmap( res_color[0], res_color[1], res_color[2] )
            
            r, g, b, a = int(color[0]*255), int(color[1]*255), int(color[2]*255), 255 
            
            
            CHANNEL_BITS=8
            WIDTH=10
            HEIGHT=10
            swatch = GdkPixbuf.Pixbuf.new( GdkPixbuf.Colorspace.RGB, True, CHANNEL_BITS, WIDTH, HEIGHT ) 
            swatch.fill( (r<<24) | (g<<16) | (b<<8) | a ) # RGBA
            
            self.statusbar_main.push(0, string, swatch)
            '''
        self.statusbar_main.push(1,string)

    def refresh_widgets (self, statusbar = True):
        """ Function doc """
        #if self.main_treeview:
        #    self.main_treeview.refresh_trajectory_scalebar()
        if statusbar:
            self.refresh_main_statusbar()

    def print_btn (self, widget):
        """ Function doc """
        #print(self.box_reac)
        parm = self.box_reac.get_rc_data()

    def run_menu_item_test (self, widget):
        """ Function doc """
        pklist = self.vm_session.picking_selections.picking_selections_list
        vobj =  pklist[0].vm_object
        #print(vobj.residues)
        #print(vobj.chains)
        
        #print(self.vm_session.picking_selections.picking_selections_list)
        pklist = self.vm_session.picking_selections.picking_selections_list
        if pklist[0]  and pklist[1]:
            #print(pklist[0], pklist[1])
            vobject = pklist[0].vm_object
            size = len(vobject.frames)
            
            dist1 = None
            dist2 = None
            dist3 = None
            
            for i in range(size):

                a1_coord = pklist[0].coords(frame=i)
                a2_coord = pklist[1].coords(frame=i)
                
                dist1 = get_simple_distance(a1_coord, a2_coord)
                
                
                if pklist[1] and pklist[2]:
                    a1_coord = pklist[1].coords(frame=i)
                    a2_coord = pklist[2].coords(frame=i)
                    dist2 = get_simple_distance(a1_coord, a2_coord)
                
                if pklist[2] and pklist[3]:
                    a1_coord = pklist[2].coords(frame=i)
                    a2_coord = pklist[3].coords(frame=i)
                    dist3 = get_simple_distance(a1_coord, a2_coord)
                dprint(dist1, dist2, dist3)
                
    def run_test (self, widget):
        '''Test'''
        pass
        
    def save_glArea_image (self, widget):
        """ Opens the Preview/Export window: a live (screen-resolution)
            preview of the current OpenGL view where the user can toggle
            and tweak the cartoon filter, save/load named style presets,
            and export the final PNG at a chosen resolution multiplier.
            The export re-captures the scene at full quality through
            VismolGLCore.render_to_image() rather than upscaling the
            preview image - see VismolGTKWidget.open_export_preview().
        """
        glwidget = self.vm_session.vm_glcore.parent_widget
        glwidget.open_export_preview()

    def opengl_to_povray_camera(self,  view_matrix, projection_matrix, camera_position, use_clipping=True):
        """
        Convert OpenGL matrices to a POV-Ray camera block.

        Args:
            view_matrix (np.ndarray): 4x4 OpenGL view matrix.
            projection_matrix (np.ndarray): 4x4 OpenGL projection matrix.
            camera_position (list/np.ndarray): Camera position [x, y, z].
            use_clipping (bool): Se True, adiciona o clipping (near/far).

        Returns:
            str: POV-Ray camera block.
        """
        import math
        # Vertical field of view (in degrees)
        fov_y_rad = 2 * math.atan(1 / projection_matrix[1,1])
        fov_y_deg = math.degrees(fov_y_rad)
        
        # near/far planes from the projection matrix
        if use_clipping:
            p22 = projection_matrix[2,2]
            p32 = projection_matrix[3,2]
            # resolver f e n: 
            # p22 = -(f+n)/(f-n), p32 = -2*f*n/(f-n)
            denom = p22 - 1e-12  # avoid division by zero
            far = (-p32)/(p22 + 1)
            near = far * (p22 - 1)/(p22 + 1)
        else:
            near, far = None, None

        # POV-Ray default look_at (origin)
        look_at = np.array([0,0,0], dtype=float)
        
        # Assemble the camera block
        pov_lines = []
        pov_lines.append("camera {")
        pov_lines.append(f"    location <{camera_position[0]}, {camera_position[1]}, {camera_position[2]}>")
        pov_lines.append(f"    look_at <{look_at[0]}, {look_at[1]}, {look_at[2]}>")
        pov_lines.append(f"    angle {fov_y_deg:.4f}")
        
        if use_clipping and near is not None and far is not None:
            pov_lines.append(f"    clipping {{ {near:.4f}, {far:.4f} }}")
        
        pov_lines.append("}")
        
        return "\n".join(pov_lines)

    def _persist_window_and_config (self):
        """ Salva gl_parameters (incluindo as dimensoes atuais da janela,
            atualizadas a cada resize em window_resize()) em disco antes de
            fechar o EasyHybrid, para restaurar na proxima abertura (ver
            MainWindow.__init__). Silencioso em caso de falha -- nao deve
            impedir o encerramento do programa. """
        try:
            self.vm_session.vm_config.save_easyhybrid_config()
        except Exception as e:
            logger.warning('Could not save preferences on exit: %s', e)

    def on_delete_event(self, widget, event=None):
        if self.p_session.changed:
            if self.session_filename == None:
                filename = 'untitled'
                #dialog.set_text('''Save changes to the project "{}" before closing?\n Your changes will be lost if you don't save them'''.format(filename))
            else:
                #dialog.set_text('''Save changes to the project "{}" before closing?\n Your changes will be lost if you don't save them'''.format(self.session_filename))
                filename = os.path.split(self.session_filename)
                filename = filename[-1]
            
            
            dialog = Gtk.MessageDialog(
                transient_for=self.window,
                modal=True,
                message_type=Gtk.MessageType.QUESTION,
                text='''Save changes to the EasyHybrid session "{}" before closing?\n Your changes will be lost if you don't save them'''.format(filename)
            )
            
            # .Save changes to the project "Untitled" before closing?
            # .Your changes will be lost if you don' tsave them
            
            dialog.add_button("Don't Save", Gtk.ResponseType.NO)
            dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
            dialog.add_button("Save", Gtk.ResponseType.YES)
            def on_response(current_dialog, response):
                current_dialog.destroy()
                if response == Gtk.ResponseType.NO:
                    self._persist_window_and_config()
                    Gtk.Application.get_default().quit()
                elif response == Gtk.ResponseType.YES:
                    if self.session_filename is None:
                        self.gtk_save_as_file(widget, on_saved=self._finish_quit_after_save)
                        return
                    else:
                        self.p_session.save_easyhybrid_session(filename=self.session_filename)
                    self._persist_window_and_config()
                    Gtk.Application.get_default().quit()

            dialog.connect("response", on_response)
            dialog.present()
            return True
        else:
            self._persist_window_and_config()
            Gtk.Application.get_default().quit()
            return True

    def _finish_quit_after_save(self):
        self._persist_window_and_config()
        Gtk.Application.get_default().quit()
