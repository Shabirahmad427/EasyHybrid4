#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  builder_sidebar.py
#
#  Copyright 2022-2026 Fernando Bachega <ferbachega@gmail.com>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
#  (at your option) any later version.
#
# ============================================================================
#  Builder editing sidebar -- small utility window with the controls for
#  everything built into gui/windows/builder/{atom_ops,click_mode}.py so
#  far: turning "placemode" (vm_session.builder_atom_mode) on/off,
#  picking the active tool (Add / Delete -- vm_session.builder_tool),
#  picking the element new atoms are placed as (vm_session.
#  builder_atom_symbol), and Undo (atom_ops.undo()).
#
#  [EN] DESIGN CHOICE: opening this window IS what puts EasyHybrid into
#  Builder editing mode (matching the request that this panel's
#  PRESENCE tracks whether placemode is active, rather than being an
#  always-visible panel with its own separate open/closed state) -- if
#  there's no vm_session.builder_target_object yet, one is created
#  automatically (empty_object.create_empty_vismol_object(), the exact
#  same helper the terminal's `new` command already uses). Closing the
#  window turns editing back off. The "Editing: ON/OFF" toggle INSIDE
#  the sidebar is a separate, lighter-weight PAUSE: it stops atom-
#  placement/deletion clicks from doing anything without closing the
#  window or losing your current tool/element selection -- handy for
#  just rotating/inspecting the molecule for a moment mid-edit.
#
#  Mirrors the exact open_window()/close_window() pattern already used
#  by setup/easyhybrid_terminal.py's TerminalWindow, including explicit
#  GtkBuilder signal hookup through the GTK4 helper used across the app.
# ============================================================================
import os
import gi
gi.require_version ( "Gtk", "4.0" )
from gi.repository import Gtk
from gui.gtk4_builder import connect_builder_signals, load_builder_file

from gui.windows.builder.empty_object import create_empty_vismol_object
from gui.windows.builder.atom_ops     import undo as atom_ops_undo
from gui.windows.builder.atom_ops     import clean_up_structure


class BuilderSidebarWindow ( ):
    """ Builder editing sidebar. """

    def __init__ ( self, main = None ):
        """ Class initialiser """
        self.main       = main
        self.vm_session = main.vm_session
        self.visible    = False

    def open_window ( self ):
        """ Opens the sidebar -- and, per this module's own design note
        above, turns Builder editing mode ON, creating a fresh empty
        target object first if none exists yet. """
        if self.visible:
            self.window.present ( )
            return

        self.builder = Gtk.Builder ( )
        load_builder_file(self.builder, os.path.join(self.main.home, 'src/gui/windows/builder/builder_sidebar.glade'))
        connect_builder_signals(self.builder, self)

        self.window = self.builder.get_object ( 'window' )
        self.window.set_title ( 'Builder' )

        self.placemode_toggle  = self.builder.get_object ( 'placemode_toggle' )
        self.tool_add_radio    = self.builder.get_object ( 'tool_add_radio' )
        self.tool_delete_radio = self.builder.get_object ( 'tool_delete_radio' )
        self.tool_move_radio   = self.builder.get_object ( 'tool_move_radio' )
        self.tool_dihedral_radio = Gtk.CheckButton(label="Dihedral")
        self.tool_dihedral_radio.set_group(self.tool_add_radio)
        self.tool_dihedral_radio.connect("toggled", self.on_tool_changed)
        self.builder.get_object('tool_box').append(self.tool_dihedral_radio)
        self.tool_fragment_radio = Gtk.CheckButton(label="Fragment")
        self.tool_fragment_radio.set_group(self.tool_add_radio)
        self.tool_fragment_radio.connect("toggled", self.on_tool_changed)
        self.builder.get_object('tool_box').append(self.tool_fragment_radio)
        self.tool_add_structure_radio = Gtk.CheckButton(label="Add Structure")
        self.tool_add_structure_radio.set_group(self.tool_add_radio)
        self.tool_add_structure_radio.connect("toggled", self.on_tool_changed)
        self.builder.get_object('tool_box').append(self.tool_add_structure_radio)
        self.element_C_radio   = self.builder.get_object ( 'element_C_radio' )
        self.element_N_radio   = self.builder.get_object ( 'element_N_radio' )
        self.element_O_radio   = self.builder.get_object ( 'element_O_radio' )
        self.element_H_radio   = self.builder.get_object ( 'element_H_radio' )
        self.element_box        = self.builder.get_object ( 'element_box' )
        self.periodic_table_button = Gtk.Button ( label = "More elements…" )
        self.periodic_table_button.connect ( "clicked", self.on_periodic_table_button_clicked )
        self.element_box.append ( self.periodic_table_button )
        self.solvate_button = Gtk.Button ( label = "Solvate…" )
        self.solvate_button.connect ( "clicked", self.on_solvate_button_clicked )
        self.builder.get_object ( 'sidebar_root_box' ).append ( self.solvate_button )
        self.atom_types_button = Gtk.Button ( label = "Atom Types…" )
        self.atom_types_button.connect ( "clicked", self.on_atom_types_button_clicked )
        self.builder.get_object ( 'sidebar_root_box' ).append ( self.atom_types_button )
        self.dyff_parameters_button = Gtk.Button(label="DYFF Parameters…")
        self.dyff_parameters_button.connect("clicked", self.on_dyff_parameters_button_clicked)
        self.builder.get_object('sidebar_root_box').append(self.dyff_parameters_button)
        self.transform_selection_button = Gtk.Button ( label = "Transform Selection…" )
        self.transform_selection_button.connect ( "clicked", self.on_transform_selection_button_clicked )
        self.builder.get_object ( 'sidebar_root_box' ).append ( self.transform_selection_button )
        self.fragment_library_button = Gtk.Button(label="Fragment Library…")
        self.fragment_library_button.connect("clicked", self.on_fragment_library_button_clicked)
        self.builder.get_object('sidebar_root_box').append(self.fragment_library_button)
        self.structure_library_button = Gtk.Button(label="Structure Library…")
        self.structure_library_button.connect("clicked", self.on_structure_library_button_clicked)
        self.builder.get_object('sidebar_root_box').append(self.structure_library_button)
        self.undo_button       = self.builder.get_object ( 'undo_button' )
        self.clean_up_button   = self.builder.get_object ( 'clean_up_button' )

        if getattr ( self.vm_session, "builder_target_object", None ) is None:
            vismol_object = create_empty_vismol_object ( self.vm_session, name = "builder_molecule" )
            self.vm_session.builder_target_object = vismol_object

        self.vm_session.builder_atom_mode   = True
        self.vm_session.builder_tool        = "add"
        self.vm_session.builder_atom_symbol = "C"
        self.vm_session.builder_dihedral_pick_atoms = []
        self.vm_session.builder_dihedral_axis = None
        self.vm_session.builder_dihedral_subgroup = None

        # reflete o estado inicial nos widgets sem disparar os handlers
        # de "toggled" de novo (eles ja rodariam com os valores certos,
        # mas sinalizar aqui deixa explicito o que esta acontecendo)
        self.placemode_toggle.set_active ( True )
        self.placemode_toggle.set_label ( "Editing: ON" )
        self.tool_add_radio.set_active ( True )
        self.element_C_radio.set_active ( True )

        self.window.present()
        self.visible = True

    def close_window ( self, *args ):
        """ Closes the sidebar and turns Builder editing mode back OFF.
        Accepts *args so it can be connected directly to BOTH the
        "Close" button's clicked signal (button) and the window's
        own close-request signal (widget) -- see builder_sidebar.glade,
        both point at on_close_button_clicked() below, which just calls
        this. Returns True so, when triggered via close-request (the
        window's own close button), GTK doesn't also run its own
        default destroy handling on top of the explicit self.window.
        destroy() already done here. """
        self.vm_session.builder_atom_mode = False
        self.vm_session.builder_dihedral_pick_atoms = []
        self.vm_session.builder_dihedral_axis = None
        self.vm_session.builder_dihedral_subgroup = None
        dihedral_window = getattr(self.main, "dihedral_angle_window", None)
        if dihedral_window is not None and dihedral_window.visible:
            dihedral_window.close_window()
        atom_types_window = getattr ( self.main, "atom_types_window", None )
        if atom_types_window is not None and atom_types_window.visible:
            atom_types_window.close_window ( )
        dyff_window = getattr(self.main, "dyff_parameters_window", None)
        if dyff_window is not None and dyff_window.visible:
            dyff_window.close_window()
        transform_window = getattr ( self.main, "transform_selection_window", None )
        if transform_window is not None and transform_window.visible:
            transform_window.close_window ( )
        fragment_window = getattr ( self.main, "fragment_library_window", None )
        if fragment_window is not None and fragment_window.visible:
            fragment_window.close_window ( )
        structure_window = getattr(self.main, "structure_library_window", None)
        if structure_window is not None and structure_window.visible:
            structure_window.on_close_button_clicked()
        target = getattr(self.vm_session, "builder_target_object", None)
        if target is not None and getattr(target, "builder_edit_source_e_id", None) is not None:
            from gui.windows.builder.empty_object import finish_editing_existing_system
            finish_editing_existing_system(target)
            self.vm_session.builder_target_object = None
        if getattr ( self, "window", None ) is not None:
            self.window.destroy ( )
        self.visible = False
        return True

    # ------------------------------------------------------------------
    #  Signal handlers (referenced by name in builder_sidebar.glade)
    # ------------------------------------------------------------------

    def on_placemode_toggled ( self, button ):
        """ The lighter-weight PAUSE toggle -- see this module's design
        note at the top for how this differs from actually closing the
        window. """
        is_active = button.get_active ( )
        self.vm_session.builder_atom_mode = is_active
        button.set_label ( "Editing: ON" if is_active else "Editing: OFF" )
        if not is_active:
            self.vm_session.builder_dihedral_pick_atoms = []
            self.vm_session.builder_dihedral_axis = None
            self.vm_session.builder_dihedral_subgroup = None
            dihedral_window = getattr(self.main, "dihedral_angle_window", None)
            if dihedral_window is not None and dihedral_window.visible:
                dihedral_window.close_window()

    def on_tool_changed ( self, button ):
        """ GtkCheckButton groups fire "toggled" for both the button that
        just became active AND the one that just became inactive -- only
        act on the one reporting active=True, otherwise this runs TWICE
        per click, the second time with the (now wrong) previous tool. """
        if not button.get_active ( ):
            return
        if button is self.tool_add_radio:
            self.vm_session.builder_tool = "add"
        elif button is self.tool_delete_radio:
            self.vm_session.builder_tool = "delete"
        elif button is self.tool_move_radio:
            self.vm_session.builder_tool = "move"
        elif button is self.tool_dihedral_radio:
            self.vm_session.builder_tool = "rotate_dihedral"
        elif button is self.tool_fragment_radio:
            self.vm_session.builder_tool = "attach_fragment"
        elif button is self.tool_add_structure_radio:
            self.vm_session.builder_tool = "add_structure"
        if self.vm_session.builder_tool != "rotate_dihedral":
            self.vm_session.builder_dihedral_pick_atoms = []
            self.vm_session.builder_dihedral_axis = None
            self.vm_session.builder_dihedral_subgroup = None
            dihedral_window = getattr(self.main, "dihedral_angle_window", None)
            if dihedral_window is not None and dihedral_window.visible:
                dihedral_window.close_window()

    def on_element_changed ( self, button ):
        """ Same "only act on the newly-active one" reasoning as
        on_tool_changed() above. """
        if not button.get_active ( ):
            return
        symbol_by_button = {
            self.element_C_radio: "C",
            self.element_N_radio: "N",
            self.element_O_radio: "O",
            self.element_H_radio: "H",
        }
        symbol = symbol_by_button.get ( button )
        if symbol is not None:
            self.vm_session.builder_atom_symbol = symbol
            self.periodic_table_button.set_label ( "More elements…" )

    def on_periodic_table_button_clicked ( self, button ):
        """Choose any supported element for subsequent atom placement."""
        from gui.windows.builder.periodic_table_dialog import choose_element

        def selected ( symbol ):
            if symbol is None:
                return
            self.vm_session.builder_atom_symbol = symbol
            for radio in (self.element_C_radio, self.element_N_radio,
                          self.element_O_radio, self.element_H_radio):
                radio.set_active ( False )
            button.set_label ( f"{symbol}…" )

        choose_element ( self.main, self.window, selected )

    def on_solvate_button_clicked ( self, button ):
        """Open Builder solvation for the current molecule."""
        target = getattr ( self.vm_session, "builder_target_object", None )
        if target is None or not getattr ( target, "atoms", None ):
            return
        self.main.solvate_window.open_window ( target )

    def on_atom_types_button_clicked ( self, button ):
        """Inspect selected Builder atoms, or all of them when none are selected."""
        target = getattr ( self.vm_session, "builder_target_object", None )
        if target is None or not getattr ( target, "atoms", None ):
            return
        selection = self.vm_session.selections.get ( self.vm_session.current_selection )
        selected_atoms = getattr ( selection, "selected_atoms", None ) or set ( )
        atom_ids = {atom.atom_id for atom in selected_atoms if atom.vm_object is target}
        if not atom_ids:
            atom_ids = set ( target.atoms )
        self.main.atom_types_window.open_window ( target, atom_ids )

    def on_dyff_parameters_button_clicked(self, button):
        target = getattr(self.vm_session, "builder_target_object", None)
        if target is not None:
            selection = self.vm_session.selections.get(self.vm_session.current_selection)
            selected = getattr(selection, "selected_atoms", None) or set()
            ids = {atom.atom_id for atom in selected if atom.vm_object is target}
            self.main.dyff_parameters_window.open_window(target, ids)

    def on_transform_selection_button_clicked ( self, button ):
        """Open live translation and rotation controls for the viewing selection."""
        target = getattr ( self.vm_session, "builder_target_object", None )
        if target is None or not getattr ( target, "atoms", None ):
            return
        selection = self.vm_session.selections.get ( self.vm_session.current_selection )
        selected = getattr ( selection, "selected_atoms", None ) or set ( )
        atom_ids = {atom.atom_id for atom in selected if atom.vm_object is target}
        self.main.transform_selection_window.open_window ( target, atom_ids )

    def on_fragment_library_button_clicked(self, button):
        self.main.fragment_library_window.open_window()

    def on_structure_library_button_clicked(self, button):
        self.main.structure_library_window.open_window()

    def on_undo_button_clicked ( self, button ):
        """ Calls atom_ops.undo() on the CURRENT target object -- see
        that function's own docstring (and push_undo_snapshot()'s) for
        exactly which actions this can step back through (place/replace
        an atom, a whole drag-to-create-a-bonded-atom gesture, deleting
        an atom or bond, cycling a bond's order). """
        target_object = getattr ( self.vm_session, "builder_target_object", None )
        if target_object is None:
            return
        atom_ops_undo ( target_object )

    def on_clean_up_button_clicked ( self, button ):
        """ Runs atom_ops.clean_up_structure() on the WHOLE current
        target object (atom_ids=None -- see that function's own
        docstring for the difference between whole-molecule and
        localised modes; this button always uses whole-molecule, per
        explicit request). Pushes an undo snapshot first, same as every
        other Builder mutation, since this can move every atom in the
        object at once. """
        from gui.windows.builder.atom_ops import push_undo_snapshot
        target_object = getattr ( self.vm_session, "builder_target_object", None )
        if target_object is None:
            return
        push_undo_snapshot ( target_object )
        clean_up_structure ( target_object, atom_ids = None )

        from gui.windows.builder.empty_object import sync_pdynamo_system
        sync_pdynamo_system ( target_object )

    def on_close_button_clicked ( self, *args ):
        return self.close_window ( )
