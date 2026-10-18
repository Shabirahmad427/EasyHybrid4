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
from gi.repository import Gio
from gui.gtk4_builder import connect_builder_signals, load_builder_file, load_builder_string
from gui.model_rows import ReactionCoordinateRow
import os

import threading
import time
from util.debug import dprint

from util.geometric_analysis            import get_distance 
from util.geometric_analysis            import get_dihedral 
from util.geometric_analysis            import get_angle 
#from util.periodic_table import atomic_dic 

from util.sequence_plot import GtkSequenceViewer
from pprint import pprint

import numpy as np

def compute_sigma_a1_a3 (vobject = None, 
                          index1 = None, 
                          index3 = None,
                          atom1  = None,
                          atom3  = None,
                         ):

    """ example:
        pk1 ---> pk2 ---> pk3
         N  ---   H  ---  O	    
         
         where H is the moving atom
         calculation only includes N and O ! 
    """
    if vobject:
        periodic_table = vobject.vm_session.periodic_table
        
        atom1 = vobject.atoms[index1]
        atom3 = vobject.atoms[index3]
    else:
        periodic_table = atom1.vm_object.vm_session.periodic_table
        
        #periodic_table = vobject.vm_session.periodic_table
        #atom1 = atoms1 
        #atom3 = atoms3 
        
        
    symbol1 = atom1.symbol
    symbol3 = atom3.symbol    

    mass1 = periodic_table.get_atomic_mass(symbol1)
    mass3 = periodic_table.get_atomic_mass(symbol3)
    
    dprint(atom1.name, symbol1, mass1)
    dprint(atom3.name, symbol3, mass3)

    sigma_pk1_pk3 =  mass1/(mass1+mass3)
    dprint ("sigma_pk1_pk3: ",sigma_pk1_pk3)
    #
    sigma_pk3_pk1 =  mass3/(mass1+mass3)
    sigma_pk3_pk1 = sigma_pk3_pk1*-1
    #
    dprint ("sigma_pk3_pk1: ", sigma_pk3_pk1)
    return(sigma_pk1_pk3, sigma_pk3_pk1)


class AdvancedReactionCoordinateBox(Gtk.Box):
    def __init__ (self, main = None, liststore =  None, mode = 1 ):
        """ Class initialiser """
        Gtk.Box.__init__(self)
        self.home = main.home
        self.vm_session = main.vm_session
        self.p_session  = main.p_session
        self.rc_model = (
            liststore if liststore is not None
            else Gio.ListStore.new(ReactionCoordinateRow)
        )
        
        
        self.import_picking_selection_button = Gtk.Button(label="Import from Picking Selection")
        self.import_picking_selection_button.connect("clicked", self.import_picking_selection_data)

        self.remove_row_button = Gtk.Button(label="Remove Selected Row")
        self.remove_row_button.connect("clicked", self.remove_selected_row)

        if mode == 0:
            xml = open(os.path.join(self.home,'src/gui/widgets/RC_box_mode_0_advanced.glade'), 'r')#~/programs/EasyHybrid3_dev/src/gui/widgets/RC_box_mode_advanced.glade
            xml = xml.read()
        elif mode == 1:
            xml = open(os.path.join(self.home,'src/gui/widgets/RC_box_mode_1_advanced.glade'), 'r')#~/programs/EasyHybrid3_dev/src/gui/widgets/RC_box_mode_advanced.glade
            xml = xml.read()
        else:
            pass
            

        self.builder = Gtk.Builder()
        load_builder_string(self.builder, xml)

        box = self.builder.get_object('reaction_coordinate_box')
        self.append(box)
        self.scrolledbox = self.builder.get_object('scrolledbox')

        self.rc_selection = Gtk.SingleSelection.new(self.rc_model)
        self.rc_selection.set_autoselect(False)
        self.rc_selection.set_can_unselect(True)
        self.treeview = Gtk.ColumnView.new(self.rc_selection)
        for title, attribute in (
            ("Atom 1", "atom1_name"), ("Index 1", "atom1_index"),
            ("Atom 2", "atom2_name"), ("Index 2", "atom2_index"),
            ("Weight", "weight"), ("Distance", "distance"),
        ):
            factory = Gtk.SignalListItemFactory()
            factory.connect("setup", self._setup_rc_cell)
            factory.connect("bind", self._bind_rc_cell, attribute)
            self.treeview.append_column(Gtk.ColumnViewColumn.new(title, factory))
        self.scrolledbox.set_child(self.treeview)
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self._on_rc_key_pressed)
        self.treeview.add_controller(key_controller)
        
        if mode == 0:
            self.btn_pk_info_box = self.builder.get_object('mode0_box')
            self.btn_pk_info_box.append(self.import_picking_selection_button)
            self.import_picking_selection_button.set_hexpand(True)
            self.btn_pk_info_box.append(self.remove_row_button)
            self.remove_row_button.set_hexpand(True)

        elif mode == 1:
            self.btn_pk_info_box = self.builder.get_object('mode1_box')
            self.btn_pk_info_box.append(self.import_picking_selection_button)
            self.import_picking_selection_button.set_hexpand(True)
            self.btn_pk_info_box.append(self.remove_row_button)
            self.remove_row_button.set_hexpand(True)
        else:
            pass
            

        #self.import_picking_selection_button = self.builder.get_object('import_picking_selection_button')
        #self.import_picking_selection_button.connect( 'clicked',  self.import_picking_selection_data )
        
        
        #self.mass_restraints1 = self.builder.get_object('mass_restraints1')
        #self.mass_restraints1.connect( 'toggled',  self.toggle_mass_restraint1 )

        self.entry_step_size = self.builder.get_object('entry_step_size1')
        self.entry_nsteps    = self.builder.get_object('entry_nsteps1')
        self.entry_dmin_coord= self.builder.get_object('entry_dmin_coord1')
        
        self.label_step_size      = self.builder.get_object('label_step_size')
        self.label_nsteps         = self.builder.get_object('label_nsteps')
        self.label_force_constant = self.builder.get_object('label_force_constant')
        self.label_dmin           = self.builder.get_object('label_dmin')
        self.label_initial_dist_angle_dihedral = self.builder.get_object('label_initial_distance_angle_dihedral')
    
    def toggle_mass_restraint1 (self, widget):
        """ Function doc """
        self.refresh_dmininum(coord1 =  True)

    def refresh_dmininum (self, coord1 =  False, coord2 = False):
        """ Function doc """
        if hasattr(self, 'vobject'):
            pass
        else:
            return False
        
        _type = self.combobox_reaction_coord1.get_selected()
        if _type == 0:
            index1 = int(self.builder.get_object('entry_atom1_index_coord1').get_text() )
            index2 = int(self.builder.get_object('entry_atom2_index_coord1').get_text() )

            dist1 = get_distance(self.vobject, index1, index2 )
            self.builder.get_object('entry_dmin_coord1').set_text(str(dist1))
        
        elif _type == 1:
            index1 = int(self.builder.get_object('entry_atom1_index_coord1').get_text() )
            index2 = int(self.builder.get_object('entry_atom2_index_coord1').get_text() )
            index3 = int(self.builder.get_object('entry_atom3_index_coord1').get_text() )
            
            dist1 = get_distance(self.vobject, index1, index2 )
            dist2 = get_distance(self.vobject, index2, index3 )
            
            if self.builder.get_object('mass_restraints1').get_active():
                self.sigma_pk1_pk3, self.sigma_pk3_pk1  = compute_sigma_a1_a3(self.vobject, index1, index3)
                #print('distance a1 - a2:', dist1 - dist2)
                DMINIMUM =  (self.sigma_pk1_pk3 * dist1) -(self.sigma_pk3_pk1 * dist2*-1)
                self.builder.get_object('entry_dmin_coord1').set_text(str(DMINIMUM))
            else:
                DMINIMUM =  dist1- dist2
                self.builder.get_object('entry_dmin_coord1').set_text(str(DMINIMUM))
        
        elif _type == 2:
            index1 = int(self.builder.get_object('entry_atom1_index_coord1').get_text() )
            index2 = int(self.builder.get_object('entry_atom2_index_coord1').get_text() )
            index3 = int(self.builder.get_object('entry_atom3_index_coord1').get_text() )
            index4 = int(self.builder.get_object('entry_atom4_index_coord1').get_text() )
            
            dist1 = get_distance(self.vobject, index1, index2 )
            dist2 = get_distance(self.vobject, index3, index4 )
            
            #if self.builder.get_object('mass_restraints1').get_active():
            #    self.sigma_pk1_pk3, self.sigma_pk3_pk1  = compute_sigma_a1_a3(self.vobject, index1, index3)
            #    #print('distance a1 - a2:', dist1 - dist2)
            #    DMINIMUM =  (self.sigma_pk1_pk3 * dist1) -(self.sigma_pk3_pk1 * dist2*-1)
            #    self.builder.get_object('entry_dmin_coord1').set_text(str(DMINIMUM))
            #else:
            DMINIMUM =  dist1- dist2
            self.builder.get_object('entry_dmin_coord1').set_text(str(DMINIMUM))
        
        elif _type == 3:
            index1 = int(self.builder.get_object('entry_atom1_index_coord1').get_text() )
            index2 = int(self.builder.get_object('entry_atom2_index_coord1').get_text() )
            index3 = int(self.builder.get_object('entry_atom3_index_coord1').get_text() )
            index4 = int(self.builder.get_object('entry_atom4_index_coord1').get_text() )
            
            
            dihedral = get_dihedral(self.vobject, index1, index2, index3, index4)
            print(dihedral)
            #dist2 = get_distance(self.vobject, index2, index3 )
            self.builder.get_object('entry_dmin_coord1').set_text(str(dihedral))
            
            #if self.builder.get_object('mass_restraints1').get_active():
            #    self.sigma_pk1_pk3, self.sigma_pk3_pk1  = compute_sigma_a1_a3(self.vobject, index1, index3)
            #    #print('distance a1 - a2:', dist1 - dist2)
            #    DMINIMUM =  (self.sigma_pk1_pk3 * dist1) -(self.sigma_pk3_pk1 * dist2*-1)
            #    self.builder.get_object('entry_dmin_coord1').set_text(str(DMINIMUM))
            #else:
            #    DMINIMUM =  dist1- dist2
            #    self.builder.get_object('entry_dmin_coord1').set_text(str(DMINIMUM))
        
        
        
        else:
            pass    
              
    def import_picking_selection_data (self, widget):
        """  
                   R                    R
                    \\                  /
                     A1--A2  . . . . A3
                    /                  \\ 
                   R                    R
                     ^   ^            ^
                     |   |            |
                    pk1-pk2  . . . . pk3
                       d1       d2	

                q1 =  1 / (mpk1 + mpk3)  =  [ mpk1 * r (pk3_pk2)  -   mpk3 * r (pk1_pk2) ]
              
          mpk1 = mass of pk1 atom  
          mpk2 = mass of pk2 atom  
          mpk3 = mass of pk3 atom  
                
        """       
        model = self._reaction_coordinate_model()
        atom1 = self.vm_session.picking_selections.picking_selections_list[0]
        atom2 = self.vm_session.picking_selections.picking_selections_list[1]
        atom3 = self.vm_session.picking_selections.picking_selections_list[2]
        atom4 = self.vm_session.picking_selections.picking_selections_list[3]
        
        if atom1 and atom2:
            i1 = str(atom1.index-1)
            a1 = atom1.name
            
            i2 = str(atom2.index-1)
            a2 = atom2.name
            
            w = '1'
            vobject = atom1.vm_object
            self.vobject = vobject
            dist1 = get_distance( vobject, int(i1), int(i2) )
            
            if atom3 and not atom4:
                i3 = str(atom3.index-1)
                a3 = atom3.name
                
                w1, w2 = compute_sigma_a1_a3 (vobject = None, 
                              index1 = None, 
                              index3 = None,
                              atom1  = atom1,
                              atom3  = atom3,
                             )
                
                if w1 == -1*w2:
                    w1 = 1
                    w2 = -1
                
                dist2 = get_distance( vobject, int(i2), int(i3) )
                
                w1    = "{:.5f}".format(w1   )
                w2    = "{:.5f}".format(w2   )
                dist1 = "{:.5f}".format(dist1)
                dist2 = "{:.5f}".format(dist2)
                model.append(ReactionCoordinateRow([a1, i1, a2, i2, str(w1), str(dist1)]))
                model.append(ReactionCoordinateRow([a2, i2, a3, i3, str(w2), str(dist2)]))
            
            elif atom3 and atom4:
                i3 = str(atom3.index-1)
                a3 = atom3.name
                i4 = str(atom4.index-1)
                a4 = atom4.name
                w1 =  1.0
                w2 = -1.0
                
                dist2 = get_distance( vobject, int(i3), int(i4) )
                
                w1    = "{:.5f}".format(w1   )
                w2    = "{:.5f}".format(w2   )
                dist1 = "{:.5f}".format(dist1)
                dist2 = "{:.5f}".format(dist2)
                model.append(ReactionCoordinateRow([a1, i1, a2, i2, str(w1), str(dist1)]))
                model.append(ReactionCoordinateRow([a3, i3, a4, i4, str(w2), str(dist2)]))
            
            else:
                dist1 = "{:.5f}".format(dist1)
                model.append(ReactionCoordinateRow([a1, i1, a2, i2, w, str(dist1)]))
        

            
        
        
        #if atom1:
        #    self.vobject = atom1.vm_object
        #else:
        #    return None
        #        
        #
        #if atom1:
        #    self.builder.get_object('entry_atom1_index_coord1').set_text(str(atom1.index-1) )
        #    self.builder.get_object('entry_atom1_name_coord1' ).set_text(str(atom1.name) )
        #else: print('use picking selection to chose the central atom')            
        ##-------
        #if atom2:
        #    self.builder.get_object('entry_atom2_index_coord1').set_text(str(atom2.index-1) )
        #    self.builder.get_object('entry_atom2_name_coord1' ).set_text(str(atom2.name) )
        #else: print('use picking selection to chose the central atom')
        ##-------
        #if atom3:
        #    self.builder.get_object('entry_atom3_index_coord1').set_text(str(atom3.index-1) )
        #    self.builder.get_object('entry_atom3_name_coord1' ).set_text(str(atom3.name) )
        #    
        #    if atom3.symbol == atom1.symbol:
        #        self.builder.get_object('mass_restraints1').set_active(False)
        #    else:
        #        self.builder.get_object('mass_restraints1').set_active(True)
        #    
        #else: print('use picking selection to chose the central atom')
        # #-------
        #if atom4:
        #    self.builder.get_object('entry_atom4_index_coord1').set_text(str(atom4.index-1) )
        #    self.builder.get_object('entry_atom4_name_coord1' ).set_text(str(atom4.name) )
        #else: print('use picking selection to chose the central atom')
            
        self.refresh_dmininum( coord1 =  True)

    def set_rc_mode (self, rc_mode = 0):
        """ Chenges the mode:
             0 - default, RCs scan go in one directions

             1 - TS mode, Starts from TS coordenate guess and
                 RCs scan go forward and backward directions
        """

        if rc_mode == 0:
            self.builder.get_object('label_f').set_visible(False)
            self.builder.get_object('label_b').set_visible(False)
            self.builder.get_object('entry_nsteps2').set_visible(False)

        if rc_mode == 1:
            self.builder.get_object('label_f').set_visible(True)
            self.builder.get_object('label_b').set_visible(True)
            self.builder.get_object('entry_nsteps2').set_visible(True)

    def remove_selected_row (self, widget = None):
        """Remove the selected row from the reaction-coordinate table,
            so a wrongly picked atom pair can be discarded without
            having to redo the whole selection. """
        position = self.rc_selection.get_selected()
        if position != GTK_INVALID_LIST_POSITION:
            self.rc_model.remove(position)
            self.refresh_dmininum()
            return True

        dprint("No row selected to remove")
        return False

    def _on_rc_key_pressed(self, _controller, keyval, _keycode, _state):
        if keyval == Gdk.KEY_Delete:
            return self.remove_selected_row()
        return False

    def get_rc_data (self, _is_ts_mode = False):
        """ Function doc """
        parameters = { }
        model = self._reaction_coordinate_model()
        lines = [model.get_item(index).as_list()
                 for index in range(model.get_n_items())]
        
        parameters['RC'] = lines
        
        
        dmin = float( self.builder.get_object('entry_dmin_coord1').get_text( ))
        parameters["nsteps"] = int(self.builder.get_object('entry_nsteps1').get_text() )
        parameters['dminimum'] = dmin
        if _is_ts_mode:
            parameters["nsteps_back"] = int(self.builder.get_object('entry_nsteps2').get_text() )

        parameters["force_constant"] = float( self.builder.get_object('entry_FORCE_coord1').get_text() )
        try:
            parameters["dincre"] = float( self.builder.get_object('entry_step_size1').get_text() )
        except:                  
            parameters["dincre"] = 0.00
        
        pprint(parameters)
        return parameters
        
    def set_rc_data(self, parameters):
        """ Preenche os widgets da interface com os dados de parâmetros """
        
        rc_type = parameters.get("rc_type", "simple_distance")
        
        # Define o tipo de coordenação de reação no combobox
        type_map = {
            "simple_distance": 0,
            "multiple_distance": 1,
            "multiple_distance*4atoms": 2,
            "dihedral": 3
        }
        self.combobox_reaction_coord1.set_selected(type_map.get(rc_type, 0))
        self.change_cb_coordType1 (self.combobox_reaction_coord1)
        
        atoms = parameters.get("ATOMS", [])
        atom_names = parameters.get("ATOM_NAMES", [])
        
        # Preenche índices e nomes dos átomos
        for i, atom_index in enumerate(atoms, start=1):
            entry_index = self.builder.get_object(f'entry_atom{i}_index_coord1')
            if entry_index:
                entry_index.set_text(str(atom_index))
        
        for i, atom_name in enumerate(atom_names, start=1):
            entry_name = self.builder.get_object(f'entry_atom{i}_name_coord1')
            if entry_name:
                entry_name.set_text(str(atom_name))
        
        # Preenche dminimum
        dmin = parameters.get("dminimum", 0.0)
        entry_dmin = self.builder.get_object('entry_dmin_coord1')
        if entry_dmin:
            entry_dmin.set_text(str(dmin))
        
        # Preenche sigma_pk1pk3 e sigma_pk3pk1
        self.sigma_pk1_pk3 = parameters.get("sigma_pk1pk3", 1.0)
        self.sigma_pk3_pk1 = parameters.get("sigma_pk3pk1", -1.0)
        
        # Se houver widget de mass restraints, ativa
        mass_restraints = self.builder.get_object('mass_restraints1')
        if mass_restraints:
            mass_restraints.set_active(parameters.get("MC", False))
        
        # Preenche constantes de força, passos e incremento
        entry_force = self.builder.get_object('entry_FORCE_coord1')
        if entry_force:
            entry_force.set_text(str(parameters.get("force_constant", 0.0)))
        
        entry_nsteps1 = self.builder.get_object('entry_nsteps1')
        if entry_nsteps1:
            entry_nsteps1.set_text(str(parameters.get("nsteps", 0)))
        
        entry_step_size1 = self.builder.get_object('entry_step_size1')
        if entry_step_size1:
            entry_step_size1.set_text(str(parameters.get("dincre", 0.0)))
        
        entry_nsteps2 = self.builder.get_object('entry_nsteps2')
        if entry_nsteps2 and "nsteps_back" in parameters:
            entry_nsteps2.set_text(str(parameters["nsteps_back"]))

    def refresh_dmininum (self, coord1 =  False, coord2 = False):
        #self.get_rc_data()
        if not hasattr(self, "treeview"):
            return
        model = self._reaction_coordinate_model()
        lines = [model.get_item(index).as_list()
                 for index in range(model.get_n_items())]
        #parameters['RC'] = lines
        dminimum = 0.0
        for rc in lines:
            dist = float(rc[5])*float(rc[4])
            dminimum += dist
            #RC1.append([ int(rc[1]),  int(rc[3]), float(rc[4])])
        
        self.builder.get_object('entry_dmin_coord1').set_text(str(dminimum))

    def _reaction_coordinate_model(self):
        return self.rc_model

    def _setup_rc_cell(self, _factory, list_item):
        entry = Gtk.Entry()
        entry.set_width_chars(8)
        entry.connect("changed", self._rc_cell_changed, list_item)
        list_item.set_child(entry)

    @staticmethod
    def _bind_rc_cell(_factory, list_item, attribute):
        entry = list_item.get_child()
        entry._binding = True
        entry._attribute = attribute
        entry.set_text(str(getattr(list_item.get_item(), attribute)))
        entry._binding = False

    def _rc_cell_changed(self, entry, list_item):
        if getattr(entry, "_binding", False):
            return
        attribute = getattr(entry, "_attribute", None)
        if attribute is None:
            return
        setattr(list_item.get_item(), attribute, entry.get_text())
        self.refresh_dmininum()


class ReactionCoordinateBox(Gtk.Box):
    """ Class doc """
    
    def __init__ (self, main = None, mode = 0 ):
        """ Class initialiser """
        Gtk.Box.__init__(self)
        self.home = main.home
        
        if mode == 1:
            xml = '''

<interface>
  <requires lib="gtk" version="4.0" />
  <object class="GtkBox" id="reaction_coordinate_box">
    <property name="visible">True</property>
    <property name="focusable">False</property>
    <property name="orientation">vertical</property>
    <property name="spacing">4</property>
    <child>
      <object class="GtkBox">
        <property name="visible">True</property>
        <property name="focusable">False</property>
        <property name="spacing">6</property>
        <child>
          <object class="GtkLabel" id="label_RC_type">
            <property name="visible">True</property>
            <property name="focusable">False</property>
            <property name="label" translatable="yes">Coordinate Type:</property>
            <property name="xalign">1</property>
          </object>
        </child>
        <child>
          <object class="GtkDropDown" id="combobox_reaction_coord1">
            <property name="visible">True</property>
            <property name="focusable">False</property>
            <property name="hexpand">True</property>
          </object>
        </child>
      </object>
    </child>
    <child>
      <object class="GtkGrid">
        <property name="visible">True</property>
        <property name="focusable">False</property>
        <property name="row-spacing">5</property>
        <property name="column-spacing">10</property>
        <child>
          <object class="GtkLabel" id="label_atom4_coord1">
            <property name="visible">True</property>
            <property name="focusable">False</property>
            <property name="label" translatable="yes">Atom 4(index):</property>
            <property name="xalign">1</property>
            <layout>
              <property name="column">0</property>
              <property name="row">3</property>
            </layout>
          </object>
        </child>
        <child>
          <object class="GtkEntry" id="entry_atom3_index_coord1">
            <property name="visible">True</property>
            <property name="focusable">True</property>
            <property name="halign">start</property>
            <property name="valign">start</property>
            <property name="width-chars">8</property>
            <layout>
              <property name="column">1</property>
              <property name="row">2</property>
            </layout>
          </object>
        </child>
        <child>
          <object class="GtkLabel" id="label_atom2_coord1">
            <property name="visible">True</property>
            <property name="focusable">False</property>
            <property name="label" translatable="yes">Atom 2(index):</property>
            <property name="xalign">1</property>
            <layout>
              <property name="column">0</property>
              <property name="row">1</property>
            </layout>
          </object>
        </child>
        <child>
          <object class="GtkLabel" id="label_atom1_coord1">
            <property name="visible">True</property>
            <property name="focusable">False</property>
            <property name="label" translatable="yes">Atom 1(index):</property>
            <property name="xalign">1</property>
            <layout>
              <property name="column">0</property>
              <property name="row">0</property>
            </layout>
          </object>
        </child>
        <child>
          <object class="GtkLabel" id="label_atom3_coord1">
            <property name="visible">True</property>
            <property name="focusable">False</property>
            <property name="label" translatable="yes">Atom 3(index):</property>
            <property name="xalign">1</property>
            <layout>
              <property name="column">0</property>
              <property name="row">2</property>
            </layout>
          </object>
        </child>
        <child>
          <object class="GtkLabel" id="label_name3_coord1">
            <property name="visible">True</property>
            <property name="focusable">False</property>
            <property name="label" translatable="yes">Name:</property>
            <property name="xalign">1</property>
            <layout>
              <property name="column">2</property>
              <property name="row">2</property>
            </layout>
          </object>
        </child>
        <child>
          <object class="GtkLabel" id="label_name4_coord1">
            <property name="visible">True</property>
            <property name="focusable">False</property>
            <property name="label" translatable="yes">Name:</property>
            <property name="xalign">1</property>
            <layout>
              <property name="column">2</property>
              <property name="row">3</property>
            </layout>
          </object>
        </child>
        <child>
          <object class="GtkLabel" id="label_name2_coord1">
            <property name="visible">True</property>
            <property name="focusable">False</property>
            <property name="label" translatable="yes">Name:</property>
            <property name="xalign">1</property>
            <layout>
              <property name="column">2</property>
              <property name="row">1</property>
            </layout>
          </object>
        </child>
        <child>
          <object class="GtkLabel" id="label_name1_coord1">
            <property name="visible">True</property>
            <property name="focusable">False</property>
            <property name="label" translatable="yes">Name:</property>
            <property name="xalign">1</property>
            <layout>
              <property name="column">2</property>
              <property name="row">0</property>
            </layout>
          </object>
        </child>
        <child>
          <object class="GtkEntry" id="entry_atom3_name_coord1">
            <property name="visible">True</property>
            <property name="focusable">True</property>
            <property name="halign">start</property>
            <property name="valign">start</property>
            <property name="width-chars">8</property>
            <layout>
              <property name="column">3</property>
              <property name="row">2</property>
            </layout>
          </object>
        </child>
        <child>
          <object class="GtkEntry" id="entry_atom2_index_coord1">
            <property name="visible">True</property>
            <property name="focusable">True</property>
            <property name="halign">start</property>
            <property name="valign">start</property>
            <property name="width-chars">8</property>
            <layout>
              <property name="column">1</property>
              <property name="row">1</property>
            </layout>
          </object>
        </child>
        <child>
          <object class="GtkEntry" id="entry_atom1_index_coord1">
            <property name="visible">True</property>
            <property name="focusable">True</property>
            <property name="halign">start</property>
            <property name="valign">start</property>
            <property name="width-chars">8</property>
            <layout>
              <property name="column">1</property>
              <property name="row">0</property>
            </layout>
          </object>
        </child>
        <child>
          <object class="GtkEntry" id="entry_atom4_index_coord1">
            <property name="visible">True</property>
            <property name="focusable">True</property>
            <property name="halign">start</property>
            <property name="valign">start</property>
            <property name="width-chars">8</property>
            <layout>
              <property name="column">1</property>
              <property name="row">3</property>
            </layout>
          </object>
        </child>
        <child>
          <object class="GtkEntry" id="entry_atom4_name_coord1">
            <property name="visible">True</property>
            <property name="focusable">True</property>
            <property name="halign">start</property>
            <property name="valign">start</property>
            <property name="width-chars">8</property>
            <layout>
              <property name="column">3</property>
              <property name="row">3</property>
            </layout>
          </object>
        </child>
        <child>
          <object class="GtkEntry" id="entry_atom2_name_coord1">
            <property name="visible">True</property>
            <property name="focusable">True</property>
            <property name="halign">start</property>
            <property name="valign">start</property>
            <property name="width-chars">8</property>
            <layout>
              <property name="column">3</property>
              <property name="row">1</property>
            </layout>
          </object>
        </child>
        <child>
          <object class="GtkEntry" id="entry_atom1_name_coord1">
            <property name="visible">True</property>
            <property name="focusable">True</property>
            <property name="halign">start</property>
            <property name="valign">start</property>
            <property name="width-chars">8</property>
            <layout>
              <property name="column">3</property>
              <property name="row">0</property>
            </layout>
          </object>
        </child>
        <child>
          <object class="GtkLabel" id="label_step_size">
            <property name="visible">True</property>
            <property name="focusable">False</property>
            <property name="label" translatable="yes">Step Size:</property>
            <property name="xalign">1</property>
            <layout>
              <property name="column">4</property>
              <property name="row">0</property>
            </layout>
          </object>
        </child>
        <child>
          <object class="GtkLabel" id="label_num_of_steps">
            <property name="visible">True</property>
            <property name="focusable">False</property>
            <property name="label" translatable="yes">Number of Steps:</property>
            <property name="xalign">1</property>
            <layout>
              <property name="column">4</property>
              <property name="row">1</property>
            </layout>
          </object>
        </child>
        <child>
          <object class="GtkLabel" id="label_force">
            <property name="visible">True</property>
            <property name="focusable">False</property>
            <property name="label" translatable="yes">Force Constante:</property>
            <property name="xalign">1</property>
            <layout>
              <property name="column">4</property>
              <property name="row">2</property>
            </layout>
          </object>
        </child>
        <child>
          <object class="GtkLabel" id="label_initial_distance_angle_dihedral">
            <property name="visible">True</property>
            <property name="focusable">False</property>
            <property name="label" translatable="yes">Initial Distance:</property>
            <property name="xalign">1</property>
            <layout>
              <property name="column">4</property>
              <property name="row">3</property>
            </layout>
          </object>
        </child>
        <child>
          <object class="GtkEntry" id="entry_step_size1">
            <property name="visible">True</property>
            <property name="focusable">True</property>
            <property name="halign">start</property>
            <property name="valign">start</property>
            <property name="width-chars">8</property>
            <layout>
              <property name="column">5</property>
              <property name="row">0</property>
            </layout>
          </object>
        </child>
        <child>
          <object class="GtkEntry" id="entry_nsteps1">
            <property name="visible">True</property>
            <property name="focusable">True</property>
            <property name="halign">start</property>
            <property name="valign">start</property>
            <property name="width-chars">8</property>
            <property name="text" translatable="yes">10</property>
            <layout>
              <property name="column">5</property>
              <property name="row">1</property>
            </layout>
          </object>
        </child>
        <child>
          <object class="GtkEntry" id="entry_FORCE_coord1">
            <property name="visible">True</property>
            <property name="focusable">True</property>
            <property name="halign">start</property>
            <property name="valign">start</property>
            <property name="width-chars">8</property>
            <property name="text" translatable="yes">4000</property>
            <layout>
              <property name="column">5</property>
              <property name="row">2</property>
            </layout>
          </object>
        </child>
        <child>
          <object class="GtkEntry" id="entry_dmin_coord1">
            <property name="visible">True</property>
            <property name="focusable">True</property>
            <property name="halign">start</property>
            <property name="valign">start</property>
            <property name="width-chars">8</property>
            <layout>
              <property name="column">5</property>
              <property name="row">3</property>
            </layout>
          </object>
        </child>
        <property name="hexpand">True</property>
      </object>
    </child>
    <child>
      <object class="GtkButton" id="import_picking_selection_button">
        <property name="label" translatable="yes">Import from Picking Selection</property>
        <property name="visible">True</property>
        <property name="focusable">True</property>
      </object>
    </child>
    <child>
      <object class="GtkCheckButton" id="mass_restraints1">
        <property name="label" translatable="yes">Apply Mass Weighted Restraints</property>
        <property name="visible">True</property>
        <property name="focusable">True</property>
      </object>
    </child>
  </object>
</interface>
'''

        elif mode == 0:
            xml = open(os.path.join(self.home,'src/gui/widgets/RC_box_mode_0_new.glade'), 'r')
            xml = xml.read()

        self.main = main
        self.vm_session = main.vm_session
        self.p_session  = main.p_session
        
        #scan mode ON
        self.scan = True
        
        self.builder = Gtk.Builder()
        load_builder_string(self.builder, xml)
        #connect_builder_signals(self.builder, self)
        #self.glWidget = glWidget
        box = self.builder.get_object('reaction_coordinate_box')
        self.append(box)
        
        self.import_picking_selection_button = self.builder.get_object('import_picking_selection_button')
        self.import_picking_selection_button.connect( 'clicked',  self.import_picking_selection_data )
        
        
        self.mass_restraints1 = self.builder.get_object('mass_restraints1')
        self.mass_restraints1.connect( 'toggled',  self.toggle_mass_restraint1 )



        #-----------------------------------------------------------------------------------
        self.method_store = Gtk.StringList.new([])
        methods = ["simple distance", "multiple distance", "multiple distance *4 atoms", 'dihedral']

        for method in methods:
            self.method_store.append(method)
        self.combobox_reaction_coord1 = self.builder.get_object('combobox_reaction_coord1')
        self.combobox_reaction_coord1.set_model(self.method_store)
        self.combobox_reaction_coord1.connect('notify::selected', self.change_cb_coordType1)
        #-----------------------------------------------------------------------------------


        self.entry_step_size = self.builder.get_object('entry_step_size1')
        self.entry_nsteps    = self.builder.get_object('entry_nsteps1')
        self.entry_dmin_coord= self.builder.get_object('entry_dmin_coord1')
        
        self.label_step_size      = self.builder.get_object('label_step_size')
        self.label_nsteps         = self.builder.get_object('label_nsteps')
        self.label_force_constant = self.builder.get_object('label_force_constant')
        self.label_dmin           = self.builder.get_object('label_dmin')
        self.label_initial_dist_angle_dihedral = self.builder.get_object('label_initial_distance_angle_dihedral')
        
    def toggle_mass_restraint1 (self, widget):
        """ Function doc """
        self.refresh_dmininum(coord1 =  True)
   
    def set_rc_mode (self, rc_mode = 0):
        """ Chenges the mode:
             0 - default, RCs scan go in one directions
             
             1 - TS mode, Starts from TS coordenate guess and 
                 RCs scan go forward and backward directions
        """
        
        if rc_mode == 0:
            self.builder.get_object('label_f').set_visible(False)
            self.builder.get_object('label_b').set_visible(False)
            self.builder.get_object('entry_nsteps2').set_visible(False)
        
        if rc_mode == 1:
            self.builder.get_object('label_f').set_visible(True)
            self.builder.get_object('label_b').set_visible(True)
            self.builder.get_object('entry_nsteps2').set_visible(True)
            
    def refresh_dmininum (self, coord1 =  False, coord2 = False):
        """ Function doc """
        if hasattr(self, 'vobject'):
            pass
        else:
            return False
        
        _type = self.combobox_reaction_coord1.get_selected()
        if _type == 0:
            index1 = int(self.builder.get_object('entry_atom1_index_coord1').get_text() )
            index2 = int(self.builder.get_object('entry_atom2_index_coord1').get_text() )

            dist1 = get_distance(self.vobject, index1, index2 )
            self.builder.get_object('entry_dmin_coord1').set_text(str(dist1))
        
        elif _type == 1:
            index1 = int(self.builder.get_object('entry_atom1_index_coord1').get_text() )
            index2 = int(self.builder.get_object('entry_atom2_index_coord1').get_text() )
            index3 = int(self.builder.get_object('entry_atom3_index_coord1').get_text() )
            
            dist1 = get_distance(self.vobject, index1, index2 )
            dist2 = get_distance(self.vobject, index2, index3 )
            
            if self.builder.get_object('mass_restraints1').get_active():
                self.sigma_pk1_pk3, self.sigma_pk3_pk1  = compute_sigma_a1_a3(self.vobject, index1, index3)
                #print('distance a1 - a2:', dist1 - dist2)
                DMINIMUM =  (self.sigma_pk1_pk3 * dist1) -(self.sigma_pk3_pk1 * dist2*-1)
                self.builder.get_object('entry_dmin_coord1').set_text(str(DMINIMUM))
            else:
                DMINIMUM =  dist1- dist2
                self.builder.get_object('entry_dmin_coord1').set_text(str(DMINIMUM))
        
        elif _type == 2:
            index1 = int(self.builder.get_object('entry_atom1_index_coord1').get_text() )
            index2 = int(self.builder.get_object('entry_atom2_index_coord1').get_text() )
            index3 = int(self.builder.get_object('entry_atom3_index_coord1').get_text() )
            index4 = int(self.builder.get_object('entry_atom4_index_coord1').get_text() )
            
            dist1 = get_distance(self.vobject, index1, index2 )
            dist2 = get_distance(self.vobject, index3, index4 )
            
            #if self.builder.get_object('mass_restraints1').get_active():
            #    self.sigma_pk1_pk3, self.sigma_pk3_pk1  = compute_sigma_a1_a3(self.vobject, index1, index3)
            #    #print('distance a1 - a2:', dist1 - dist2)
            #    DMINIMUM =  (self.sigma_pk1_pk3 * dist1) -(self.sigma_pk3_pk1 * dist2*-1)
            #    self.builder.get_object('entry_dmin_coord1').set_text(str(DMINIMUM))
            #else:
            DMINIMUM =  dist1- dist2
            self.builder.get_object('entry_dmin_coord1').set_text(str(DMINIMUM))
        
        elif _type == 3:
            index1 = int(self.builder.get_object('entry_atom1_index_coord1').get_text() )
            index2 = int(self.builder.get_object('entry_atom2_index_coord1').get_text() )
            index3 = int(self.builder.get_object('entry_atom3_index_coord1').get_text() )
            index4 = int(self.builder.get_object('entry_atom4_index_coord1').get_text() )
            
            dihedral = get_dihedral(self.vobject, index1, index2, index3, index4)
            #dist2 = get_distance(self.vobject, index2, index3 )
            self.builder.get_object('entry_dmin_coord1').set_text(str(dihedral))
            
            #if self.builder.get_object('mass_restraints1').get_active():
            #    self.sigma_pk1_pk3, self.sigma_pk3_pk1  = compute_sigma_a1_a3(self.vobject, index1, index3)
            #    #print('distance a1 - a2:', dist1 - dist2)
            #    DMINIMUM =  (self.sigma_pk1_pk3 * dist1) -(self.sigma_pk3_pk1 * dist2*-1)
            #    self.builder.get_object('entry_dmin_coord1').set_text(str(DMINIMUM))
            #else:
            #    DMINIMUM =  dist1- dist2
            #    self.builder.get_object('entry_dmin_coord1').set_text(str(DMINIMUM))
        
        
        
        else:
            pass    
              
    def import_picking_selection_data (self, widget):
        """  
                   R                    R
                    \\                  /
                     A1--A2  . . . . A3
                    /                  \\ 
                   R                    R
                     ^   ^            ^
                     |   |            |
                    pk1-pk2  . . . . pk3
                       d1       d2	

                q1 =  1 / (mpk1 + mpk3)  =  [ mpk1 * r (pk3_pk2)  -   mpk3 * r (pk1_pk2) ]
              
          mpk1 = mass of pk1 atom  
          mpk2 = mass of pk2 atom  
          mpk3 = mass of pk3 atom  
                
        """       
        atom1 = self.vm_session.picking_selections.picking_selections_list[0]
        atom2 = self.vm_session.picking_selections.picking_selections_list[1]
        atom3 = self.vm_session.picking_selections.picking_selections_list[2]
        atom4 = self.vm_session.picking_selections.picking_selections_list[3]
        
        if atom1:
            self.vobject = atom1.vm_object
        else:
            return None
                

        if atom1:
            self.builder.get_object('entry_atom1_index_coord1').set_text(str(atom1.index-1) )
            self.builder.get_object('entry_atom1_name_coord1' ).set_text(str(atom1.name) )
        else: dprint('use picking selection to chose the central atom')            
        #-------
        if atom2:
            self.builder.get_object('entry_atom2_index_coord1').set_text(str(atom2.index-1) )
            self.builder.get_object('entry_atom2_name_coord1' ).set_text(str(atom2.name) )
        else: dprint('use picking selection to chose the central atom')
        #-------
        if atom3:
            self.builder.get_object('entry_atom3_index_coord1').set_text(str(atom3.index-1) )
            self.builder.get_object('entry_atom3_name_coord1' ).set_text(str(atom3.name) )
            
            if atom3.symbol == atom1.symbol:
                self.builder.get_object('mass_restraints1').set_active(False)
            else:
                self.builder.get_object('mass_restraints1').set_active(True)
            
        else: dprint('use picking selection to chose the central atom')
         #-------
        if atom4:
            self.builder.get_object('entry_atom4_index_coord1').set_text(str(atom4.index-1) )
            self.builder.get_object('entry_atom4_name_coord1' ).set_text(str(atom4.name) )
        else: dprint('use picking selection to chose the central atom')
            
        self.refresh_dmininum( coord1 =  True)
                
    def change_cb_coordType1 (self, combo_box, _pspec=None):
        """ Function doc """
        
        _type = self.combobox_reaction_coord1.get_selected()
        
        if _type == 0:
            self.builder.get_object('label_atom3_coord1').set_visible(False)
            self.builder.get_object('entry_atom3_index_coord1').set_visible(False)
            self.builder.get_object('label_name3_coord1').set_visible(False)
            self.builder.get_object('entry_atom3_name_coord1').set_visible(False)
            
            self.builder.get_object('label_atom4_coord1').set_visible(False)
            self.builder.get_object('entry_atom4_index_coord1').set_visible(False)
            self.builder.get_object('label_name4_coord1').set_visible(False)
            self.builder.get_object('entry_atom4_name_coord1').set_visible(False)
            self.builder.get_object('mass_restraints1').set_sensitive(False)
            self.label_initial_dist_angle_dihedral.set_text('Initial Distance:')

        if _type == 1:
            self.builder.get_object('label_atom3_coord1').set_visible(True)
            self.builder.get_object('entry_atom3_index_coord1').set_visible(True)
            self.builder.get_object('label_name3_coord1').set_visible(True)
            self.builder.get_object('entry_atom3_name_coord1').set_visible(True)
            
            self.builder.get_object('label_atom4_coord1').set_visible(False)
            self.builder.get_object('entry_atom4_index_coord1').set_visible(False)
            self.builder.get_object('label_name4_coord1').set_visible(False)
            self.builder.get_object('entry_atom4_name_coord1').set_visible(False)
            self.builder.get_object('mass_restraints1').set_sensitive(True)
            self.label_initial_dist_angle_dihedral.set_text('Initial Distance:')

        
        if _type == 2:
            self.builder.get_object('label_atom3_coord1').set_visible(True)
            self.builder.get_object('entry_atom3_index_coord1').set_visible(True)
            self.builder.get_object('label_name3_coord1').set_visible(True)
            self.builder.get_object('entry_atom3_name_coord1').set_visible(True)
            
            self.builder.get_object('label_atom4_coord1').set_visible(True)
            self.builder.get_object('entry_atom4_index_coord1').set_visible(True)
            self.builder.get_object('label_name4_coord1').set_visible(True)
            self.builder.get_object('entry_atom4_name_coord1').set_visible(True)
            self.builder.get_object('mass_restraints1').set_sensitive(False)
            #self.label_initial_dist_angle_dihedral.set_text('Initial Distance:')
            self.label_initial_dist_angle_dihedral.set_text('Initial Distance:')

        if _type == 3:
            self.builder.get_object('label_atom3_coord1').set_visible(True)
            self.builder.get_object('entry_atom3_index_coord1').set_visible(True)
            self.builder.get_object('label_name3_coord1').set_visible(True)
            self.builder.get_object('entry_atom3_name_coord1').set_visible(True)
            
            self.builder.get_object('label_atom4_coord1').set_visible(True)
            self.builder.get_object('entry_atom4_index_coord1').set_visible(True)
            self.builder.get_object('label_name4_coord1').set_visible(True)
            self.builder.get_object('entry_atom4_name_coord1').set_visible(True)
            self.builder.get_object('mass_restraints1').set_sensitive(False)
            #self.label_initial_dist_angle_dihedral.set_text('Initial Distance:')
            self.label_initial_dist_angle_dihedral.set_text('Initial Angle:')
        
        if _type == 4:
            self.label_initial_dist_angle_dihedral.set_text('Initial Angle:')
        
        
        
        if self.scan:
            try:
                self.refresh_dmininum ( coord1 = True)
            except Exception as e:
                # [EN] BUG FIX: este except tentava usar texto_d1/
                # texto_d2d1, duas variaveis que nunca existiram nesta
                # funcao -- se refresh_dmininum() alguma vez levantasse
                # uma excecao de verdade, este handler quebraria de novo
                # (NameError), mascarando o erro original. Tambem era um
                # 'except:' pelado (pega ate Ctrl+C/SystemExit) -- trocado
                # por 'except Exception', e logando a excecao real em vez
                # de referenciar nomes que nao existem.
                dprint("refresh_dmininum failed:", e)
    
    def set_rc_type (self, rc_type = 0):
        """ Chenges the type -  simple distance is default """
        self.combobox_reaction_coord1.set_selected(rc_type)

    def set_hide_scan_parameters (self):
        """ Function doc """
        self.builder.get_object('rc_grid').set_visible(False)
        self.builder.get_object('mass_restraints1').set_visible(False)
        self.builder.get_object('rc_aligment').set_visible(False)
        self.scan = False

    def get_rc_data (self, _is_ts_mode = False):
        """ Function doc """
        parameters = { }
        
        _type = self.combobox_reaction_coord1.get_selected()
        if _type == 0:
            parameters["rc_type"]     = "simple_distance"
            index1 = int( self.builder.get_object('entry_atom1_index_coord1').get_text() )
            index2 = int( self.builder.get_object('entry_atom2_index_coord1').get_text() )
            
            name1 = self.builder.get_object('entry_atom1_name_coord1').get_text()
            name2 = self.builder.get_object('entry_atom2_name_coord1').get_text()
            
            dmin   = float( self.builder.get_object('entry_dmin_coord1').get_text( ))
            parameters["ATOMS"]       = [ index1, index2 ] 
            parameters["ATOM_NAMES"] = [ name1 ,  name2 ] 
            parameters["dminimum"]  = dmin 
            parameters["sigma_pk1pk3"] = None
            parameters["sigma_pk3pk1"] = None
            
        elif _type == 1:
            parameters["rc_type"]     = "multiple_distance"
            index1 = int( self.builder.get_object('entry_atom1_index_coord1').get_text() )
            index2 = int( self.builder.get_object('entry_atom2_index_coord1').get_text() )
            index3 = int( self.builder.get_object('entry_atom3_index_coord1').get_text() )
            
            name1 = self.builder.get_object('entry_atom1_name_coord1').get_text() 
            name2 = self.builder.get_object('entry_atom2_name_coord1').get_text() 
            name3 = self.builder.get_object('entry_atom3_name_coord1').get_text() 
            
            dmin   = float( self.builder.get_object('entry_dmin_coord1').get_text( ))
            parameters["ATOMS"]       = [ index1, index2, index3 ] 
            parameters["ATOM_NAMES"] = [ name1,  name2,  name3 ] 
            parameters["dminimum"]  = dmin  
            
            if self.builder.get_object('mass_restraints1').get_active():
                parameters["MC"] = True
                #if self.sigma_pk1_pk3 and self.sigma_pk3_pk1:
                #    self.sigma_pk1_pk3, self.sigma_pk3_pk1  = compute_sigma_a1_a3(self.vobject, index1, index3)
                
                parameters["sigma_pk1pk3"] = self.sigma_pk1_pk3 
                parameters["sigma_pk3pk1"] = self.sigma_pk3_pk1 
            else:
                parameters["sigma_pk1pk3"] =  1.0 
                parameters["sigma_pk3pk1"] = -1.0 


        elif _type == 2:
            index1 = int( self.builder.get_object('entry_atom1_index_coord1').get_text() )
            index2 = int( self.builder.get_object('entry_atom2_index_coord1').get_text() )
            index3 = int( self.builder.get_object('entry_atom3_index_coord1').get_text() )
            index4 = int( self.builder.get_object('entry_atom4_index_coord1').get_text() )
            dmin   = float( self.builder.get_object('entry_dmin_coord1').get_text() )
            
            name1 = self.builder.get_object('entry_atom1_name_coord1').get_text() 
            name2 = self.builder.get_object('entry_atom2_name_coord1').get_text() 
            name3 = self.builder.get_object('entry_atom3_name_coord1').get_text() 
            name4 = self.builder.get_object('entry_atom4_name_coord1').get_text() 
            
            
            parameters["ATOMS"]      = [ index1,index2,index3,index4] 
            parameters["ATOM_NAMES"] = [ name1,  name2,  name3, name4] 

            parameters["dminimum"]  = dmin 
            parameters["rc_type"]     = "multiple_distance*4atoms"
            parameters["sigma_pk1pk3"] =   1.0
            parameters["sigma_pk3pk1"] =  -1.0
        
        elif _type == 3:
            index1 = int( self.builder.get_object('entry_atom1_index_coord1').get_text() )
            index2 = int( self.builder.get_object('entry_atom2_index_coord1').get_text() )
            index3 = int( self.builder.get_object('entry_atom3_index_coord1').get_text() )
            index4 = int( self.builder.get_object('entry_atom4_index_coord1').get_text() )
            dmin   = float( self.builder.get_object('entry_dmin_coord1').get_text() )
            parameters["ATOMS"]     = [ index1,index2,index3,index4] 
            parameters["dminimum"]  = dmin 
            parameters["rc_type"]     = "dihedral"
            parameters["sigma_pk1pk3"] = None
            parameters["sigma_pk3pk1"] = None
        
        try:
            parameters["nsteps"]         = int(self.builder.get_object('entry_nsteps1').get_text() )
        except:
            parameters["nsteps"]         = None
        if _is_ts_mode:
            parameters["nsteps_back"]= int(self.builder.get_object('entry_nsteps2').get_text() )
        
        
        parameters["force_constant"] = float( self.builder.get_object('entry_FORCE_coord1').get_text() )
        try:
            parameters["dincre"]         = float( self.builder.get_object('entry_step_size1').get_text() )
        except:
            parameters["dincre"]         = 0.00
        return (parameters)
        
    def set_rc_data(self, parameters):
        """ Preenche os widgets da interface com os dados de parâmetros """
        
        rc_type = parameters.get("rc_type", "simple_distance")
        
        # Define o tipo de coordenação de reação no combobox
        type_map = {
            "simple_distance": 0,
            "multiple_distance": 1,
            "multiple_distance*4atoms": 2,
            "dihedral": 3
        }
        self.combobox_reaction_coord1.set_selected(type_map.get(rc_type, 0))
        self.change_cb_coordType1 (self.combobox_reaction_coord1)
        
        atoms = parameters.get("ATOMS", [])
        atom_names = parameters.get("ATOM_NAMES", [])
        
        # Preenche índices e nomes dos átomos
        for i, atom_index in enumerate(atoms, start=1):
            entry_index = self.builder.get_object(f'entry_atom{i}_index_coord1')
            if entry_index:
                entry_index.set_text(str(atom_index))
        
        for i, atom_name in enumerate(atom_names, start=1):
            entry_name = self.builder.get_object(f'entry_atom{i}_name_coord1')
            if entry_name:
                entry_name.set_text(str(atom_name))
        
        # Preenche dminimum
        dmin = parameters.get("dminimum", 0.0)
        entry_dmin = self.builder.get_object('entry_dmin_coord1')
        if entry_dmin:
            entry_dmin.set_text(str(dmin))
        
        # Preenche sigma_pk1pk3 e sigma_pk3pk1
        self.sigma_pk1_pk3 = parameters.get("sigma_pk1pk3", 1.0)
        self.sigma_pk3_pk1 = parameters.get("sigma_pk3pk1", -1.0)
        
        # Se houver widget de mass restraints, ativa
        mass_restraints = self.builder.get_object('mass_restraints1')
        if mass_restraints:
            mass_restraints.set_active(parameters.get("MC", False))
        
        # Preenche constantes de força, passos e incremento
        entry_force = self.builder.get_object('entry_FORCE_coord1')
        if entry_force:
            entry_force.set_text(str(parameters.get("force_constant", 0.0)))
        
        entry_nsteps1 = self.builder.get_object('entry_nsteps1')
        if entry_nsteps1:
            entry_nsteps1.set_text(str(parameters.get("nsteps", 0)))
        
        entry_step_size1 = self.builder.get_object('entry_step_size1')
        if entry_step_size1:
            entry_step_size1.set_text(str(parameters.get("dincre", 0.0)))
        
        entry_nsteps2 = self.builder.get_object('entry_nsteps2')
        if entry_nsteps2 and "nsteps_back" in parameters:
            entry_nsteps2.set_text(str(parameters["nsteps_back"]))
