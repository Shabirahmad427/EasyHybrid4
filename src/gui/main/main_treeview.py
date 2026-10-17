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
import os, sys, time
import gi 
import signal
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, GObject, Gio, Pango
from gi.repository import GdkPixbuf
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

class SystemTreeRow(GObject.Object):
    """A system or visualization object displayed by the GTK4 tree model."""

    system_id = GObject.Property(type=int, default=-1)
    object_id = GObject.Property(type=int, default=-1)
    name = GObject.Property(type=str, default="")
    active_system = GObject.Property(type=bool, default=False)
    visible = GObject.Property(type=bool, default=False)
    show_visibility = GObject.Property(type=bool, default=False)
    frames = GObject.Property(type=int, default=0)
    show_frames = GObject.Property(type=bool, default=False)
    color = GObject.Property(type=GdkPixbuf.Pixbuf)

    def __init__(self, system_id, object_id, name, *, active_system=False,
                 visible=False, show_visibility=False, frames=0,
                 show_frames=False, color=None):
        super().__init__(system_id=system_id, object_id=object_id, name=name,
                         active_system=active_system, visible=visible,
                         show_visibility=show_visibility, frames=frames,
                         show_frames=show_frames, color=color)
        self.children = Gio.ListStore.new(SystemTreeRow)


class EasyHybridMainTreeView(Gtk.Box):
    """Hierarchical GTK4 browser for systems and visualization objects."""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.root_rows = Gio.ListStore.new(SystemTreeRow)
        self.tree_model = Gtk.TreeListModel.new(
            self.root_rows, False, False, self._create_child_model
        )
        self.selection = Gtk.SingleSelection.new(self.tree_model)
        self.view = Gtk.ColumnView.new(self.selection)
        self.view.set_show_row_separators(False)
        self.view.set_show_column_separators(False)
        self.append(self.view)

        self.system_rows = {}
        self._setting_check = set()
        self._row_signals = {}
        self._radio_group = None
        self._install_columns()

        self.view.connect("activate", self._on_activate)
        click = Gtk.GestureClick()
        click.set_button(0)
        click.connect("released", self.on_treeview_mouse_button_release_event)
        self.view.add_controller(click)

    @staticmethod
    def _create_child_model(row):
        return row.children

    def _expand_parent(self, row):
        parents = []
        parent = getattr(row, "parent_row", None)
        while parent is not None:
            parents.append(parent)
            parent = getattr(parent, "parent_row", None)
        for parent in reversed(parents):
            for position in range(self.tree_model.get_n_items()):
                tree_list_row = self.tree_model.get_item(position)
                if tree_list_row.get_item() is parent:
                    tree_list_row.set_expanded(True)
                    break

    def _install_columns(self):
        radio_factory = Gtk.SignalListItemFactory()
        radio_factory.connect("setup", self._setup_radio)
        radio_factory.connect("bind", self._bind_radio)
        radio_factory.connect("unbind", self._unbind_radio)
        self.view.append_column(Gtk.ColumnViewColumn.new("A", radio_factory))

        name_factory = Gtk.SignalListItemFactory()
        name_factory.connect("setup", self._setup_name)
        name_factory.connect("bind", self._bind_name)
        name_factory.connect("unbind", self._unbind_name)
        name_column = Gtk.ColumnViewColumn.new("System", name_factory)
        name_column.set_expand(True)
        self.view.append_column(name_column)

        visible_factory = Gtk.SignalListItemFactory()
        visible_factory.connect("setup", self._setup_visibility)
        visible_factory.connect("bind", self._bind_visibility)
        visible_factory.connect("unbind", self._unbind_visibility)
        self.view.append_column(Gtk.ColumnViewColumn.new("V", visible_factory))

        frames_factory = Gtk.SignalListItemFactory()
        frames_factory.connect("setup", self._setup_frames)
        frames_factory.connect("bind", self._bind_frames)
        frames_factory.connect("unbind", self._unbind_frames)
        self.view.append_column(Gtk.ColumnViewColumn.new("F", frames_factory))

    @staticmethod
    def _row(list_item):
        tree_list_row = list_item.get_item()
        return tree_list_row.get_item() if tree_list_row else None

    def _setup_radio(self, factory, list_item):
        check = Gtk.CheckButton()
        if self._radio_group is None:
            self._radio_group = check
        else:
            check.set_group(self._radio_group)
        check.connect("toggled", self._radio_toggled, list_item)
        list_item.set_child(check)

    def _bind_radio(self, factory, list_item):
        row = self._row(list_item)
        check = list_item.get_child()
        check.set_visible(row.object_id == -1 and row.system_id >= 0)
        self._setting_check.add(id(list_item))
        check.set_active(row.active_system)
        self._setting_check.discard(id(list_item))
        self._connect_row_notify(list_item, row, "notify::active-system",
                                 lambda item: self._set_cell_active(list_item, item.active_system))

    def _radio_toggled(self, check, list_item):
        if id(list_item) in self._setting_check or not check.get_active():
            return
        row = self._row(list_item)
        if row and row.system_id >= 0:
            self.on_cell_active_radio_toggled(row)

    def _setup_name(self, factory, list_item):
        expander = Gtk.TreeExpander()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        picture = Gtk.Picture()
        picture.set_size_request(16, 16)
        picture.set_can_shrink(True)
        label = Gtk.Label(xalign=0)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_hexpand(True)
        box.append(picture)
        box.append(label)
        expander.set_child(box)
        list_item.set_child(expander)

    def _bind_name(self, factory, list_item):
        tree_list_row = list_item.get_item()
        row = tree_list_row.get_item()
        expander = list_item.get_child()
        expander.set_list_row(tree_list_row)
        box = expander.get_child()
        picture = box.get_first_child()
        label = picture.get_next_sibling()
        picture.set_pixbuf(row.color)
        label.set_text(row.name)
        self._connect_row_notify(list_item, row, "notify::name",
                                 lambda item: label.set_text(item.name))
        self._connect_row_notify(list_item, row, "notify::color",
                                 lambda item: picture.set_pixbuf(item.color))

    def _setup_visibility(self, factory, list_item):
        check = Gtk.CheckButton()
        check.connect("toggled", self._visibility_toggled, list_item)
        list_item.set_child(check)

    def _bind_visibility(self, factory, list_item):
        row = self._row(list_item)
        check = list_item.get_child()
        check.set_visible(row.show_visibility)
        self._setting_check.add(id(list_item))
        check.set_active(row.visible)
        self._setting_check.discard(id(list_item))
        self._connect_row_notify(list_item, row, "notify::visible",
                                 lambda item: self._set_cell_active(list_item, item.visible))

    def _visibility_toggled(self, check, list_item):
        if id(list_item) in self._setting_check:
            return
        row = self._row(list_item)
        if row and row.object_id >= 0:
            row.visible = check.get_active()
            obj = self.main.vm_session.vm_objects_dic.get(row.object_id)
            if obj is not None:
                obj.active = row.visible
            self.main.bottom_notebook.seqview.refresh_vobject_sequence_list(
                self.main.vm_session.vm_objects_dic
            )
            self.refresh_trajectory_scalebar()
            self.main.vm_session.vm_glcore.queue_draw()

    def _setup_frames(self, factory, list_item):
        label = Gtk.Label(xalign=1)
        list_item.set_child(label)

    def _bind_frames(self, factory, list_item):
        row = self._row(list_item)
        label = list_item.get_child()
        label.set_visible(row.show_frames)
        label.set_text(str(row.frames) if row.show_frames else "")
        self._connect_row_notify(list_item, row, "notify::frames",
                                 lambda item: label.set_text(str(item.frames)))

    def _connect_row_notify(self, list_item, row, signal, callback):
        self._disconnect_row_notify(list_item)
        handler = row.connect(signal, lambda item, _pspec: callback(item))
        self._row_signals[id(list_item)] = (row, handler)

    def _disconnect_row_notify(self, list_item):
        binding = self._row_signals.pop(id(list_item), None)
        if binding:
            row, handler = binding
            if row.handler_is_connected(handler):
                row.disconnect(handler)

    def _unbind_radio(self, factory, list_item):
        self._disconnect_row_notify(list_item)

    def _unbind_name(self, factory, list_item):
        self._disconnect_row_notify(list_item)

    def _unbind_visibility(self, factory, list_item):
        self._disconnect_row_notify(list_item)

    def _unbind_frames(self, factory, list_item):
        self._disconnect_row_notify(list_item)

    def _set_cell_active(self, list_item, value):
        self._setting_check.add(id(list_item))
        list_item.get_child().set_active(value)
        self._setting_check.discard(id(list_item))

    def add_new_system_to_treeview(self, system):
        color = get_colorful_square_pixel_buffer(system)
        row = SystemTreeRow(system.e_id, -1, f"{system.e_id} - {system.label}",
                            active_system=(system.e_id == self.main.p_session.active_id),
                            color=color)
        self.root_rows.append(row)
        self.system_rows[system.e_id] = row
        choice_row = SystemChoiceRow(row.name, system.e_id, color)
        self.main.system_liststore.append(choice_row)
        self.main.system_choice_rows[system.e_id] = choice_row
        system.system_choice_row = choice_row
        self.main.vobject_liststore_dict[system.e_id] = Gio.ListStore.new(
            CoordinateChoiceRow
        )
        self.main.bottom_notebook.set_active_system_text_to_textbuffer()
        return row

    def add_vismol_object_to_treeview(self, vismol_object, vobj_parent=False):
        original_e_id = vismol_object.e_id
        system = self.main.p_session.psystem.get(original_e_id) if original_e_id is not None else None
        system_id = original_e_id if system is not None else -1
        color = get_colorful_square_pixel_buffer(system) if system is not None else None
        if vobj_parent:
            parent_row = vobj_parent
            vismol_object.is_surface = True
            color = None
        elif system is not None:
            parent_row = self.system_rows[system_id]
        else:
            parent_row = None
        row = SystemTreeRow(system_id, vismol_object.index, vismol_object.name,
                            visible=vismol_object.active, show_visibility=True,
                            frames=len(vismol_object.frames), show_frames=True,
                            color=color)
        row.parent_row = parent_row
        (parent_row.children if parent_row else self.root_rows).append(row)
        if parent_row is not None:
            self._expand_parent(row)
        vismol_object.tree_row = row
        self.refresh_trajectory_scalebar()
        self.main.bottom_notebook.seqview.refresh_vobject_sequence_list(
            self.main.vm_session.vm_objects_dic
        )
        return row

    def remove_row(self, row):
        if row is None:
            return False
        def remove_from(model):
            for index in range(model.get_n_items()):
                candidate = model.get_item(index)
                if candidate is row:
                    model.remove(index)
                    return True
                if remove_from(candidate.children):
                    return True
            return False

        if remove_from(self.root_rows):
            if row.object_id == -1:
                self.system_rows.pop(row.system_id, None)
            return True
        return False

    def set_active_system(self, e_id):
        for row in self.system_rows.values():
            row.active_system = row.system_id == e_id
        self.main.p_session.active_id = e_id

    def on_cell_active_radio_toggled(self, row):
        before = self.main.p_session.active_id
        self.set_active_system(row.system_id)
        self.main.bottom_notebook.change_annotations_textbuffer(before, row.system_id)
        self.main.refresh_main_statusbar()
        self.main.uptade_interface_windows_and_dialogs()

    def _on_activate(self, view, position):
        tree_list_row = self.tree_model.get_item(position)
        row = tree_list_row.get_item() if tree_list_row else None
        if row is None:
            return
        self.vm_object_index = row.object_id
        self.system_e_id = row.system_id
        self.main.trajectory_player_window.change_range(upper=row.frames)
        for obj in self.main.vm_session.vm_objects_dic.values():
            obj_row = getattr(obj, "tree_row", None)
            if obj_row:
                obj_row.frames = len(obj.frames)
                obj_row.visible = obj.active

    def on_treeview_mouse_button_release_event(self, gesture, number_of_presses, x, y):
        selected = self.selection.get_selected_item()
        row = selected.get_item() if selected else None
        if row is None:
            return
        button = gesture.get_current_button()
        if button == Gdk.BUTTON_SECONDARY and row.system_id >= 0:
            self.treeview_menu.open_menu(row.system_id, row.object_id, x, y)
        elif button == Gdk.BUTTON_MIDDLE and row.object_id >= 0:
            obj = self.main.vm_session.vm_objects_dic.get(row.object_id)
            if obj:
                self.main.vm_session.vm_glcore.center_on_coordinates(obj, obj.mass_center)

    def refresh_number_of_frames(self):
        for obj in self.main.vm_session.vm_objects_dic.values():
            row = getattr(obj, "tree_row", None)
            if row:
                row.frames = len(obj.frames)
                row.visible = obj.active

    def refresh_trajectory_scalebar(self):
        upper = max((len(obj.frames) for obj in self.main.vm_session.vm_objects_dic.values()
                     if obj.active), default=1)
        self.main.trajectory_player_window.change_range(upper=upper)
        self.main.trajectory_player_window.upper = upper

    def refresh(self):
        self.root_rows.remove_all()
        self.system_rows.clear()
        self.main.system_liststore.remove_all()
        self.main.system_choice_rows.clear()
        self.main.vobject_liststore_dict.clear()
        for system in self.main.p_session.psystem.values():
            if system is not None:
                self.add_new_system_to_treeview(system)
        for system_id, system in self.main.p_session.psystem.items():
            if system is None:
                self.main.vobject_liststore_dict[system_id] = Gio.ListStore.new(
                    CoordinateChoiceRow
                )
        for obj in self.main.vm_session.vm_objects_dic.values():
            self.add_vismol_object_to_treeview(obj)
            self.main.add_vobject_to_vobject_liststore_dict(obj)
        self.main.uptade_interface_windows_and_dialogs()
