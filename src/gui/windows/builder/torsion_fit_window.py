#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  EasyHybrid: Python interface for QM/MM and molecular simulations using pDynamo3
#  Module: torsion fit window (DYFF Parameters and OPLS Parameters windows)
#
#  Copyright 2022-2026 Fernando Bachega
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
#  (at your option) any later version.
#
#  Description:
#      Scans the dihedral shown in a parameters window (the row's term picked
#      with the previous/next buttons) with xTB, fits the dihedral parameter
#      of that row to the scan (pdynamo/torsion_fit.py) and plots, with
#      EasyPlot, the xTB profile and the MM profiles with the current and the
#      fitted parameter. The force field side is a "target" object:
#        dyff_parameters.DYFFTorsionTarget  (Builder molecule; Apply = an
#                                            undoable DYFF parameter edit)
#        opls.torsion_fit.OPLSTorsionTarget (the molecule holding the
#                                            dihedral, cut out of the system;
#                                            Apply = editor.apply_edits)
#      with: force_field, key, key_text, symbols, coordinates, bonds, quad,
#      instances, atom_names, default_charge, current_text, notes(),
#      energies_for ( pairs, geometries ), format_value ( pairs ), changed(),
#      apply ( pairs ) -> message.
#
#      xtb runs in a worker thread (cancellable); the MM energies and the
#      fit run in the GTK thread when the scan is done.
#

import os
import threading
import traceback

import gi
gi.require_version ( "Gtk", "4.0" )
from gi.repository import Gtk, GLib, Gio

from pdynamo import torsion_fit as F
from gui.choice_dropdown import new_choice_dropdown, selected_choice_value

# (value, label): values are passed to xTB unchanged (--gfn N, --alpb NAME).
XTB_METHOD_CHOICES = (("2", "GFN2-xTB"), ("1", "GFN1-xTB"))
XTB_SOLVENT_CHOICES = (("none", "none (gas phase)"), ("water", "water"), ("methanol", "methanol"))

_COLORS = { "qm": ( 0.0, 0.0, 0.0 ), "before": ( 0.85, 0.33, 0.30 ), "after": ( 0.20, 0.45, 0.85 ) }


def _hex ( rgb ):
    return "#{:02x}{:02x}{:02x}".format ( *[ int ( 255 * c ) for c in rgb ] )


class TorsionFitWindow:
    """ xTB scan + fit of one dihedral parameter (DYFF or OPLS target).
        on_applied ( message ): called after Apply (refresh of the caller). """

    def __init__ ( self, main = None, on_applied = None ):
        self.main = main
        self.vm_session = main.vm_session
        self.on_applied = on_applied
        self.visible = False
        self.runner = None
        self.result = None
        self.plot = None
        self.target = None

    #-------------------------------------------------------------------------
    def open_window ( self, target ):
        if self.runner is not None:
            self.window.present ( )
            self.label_status.set_text ( "A scan is running: cancel it before starting another one." )
            return
        self.target = target
        self.result = None
        if not self.visible:
            self._build_window()
        else:
            self.window.present ( )
        ff = target.force_field
        self.window.set_title ( "{} Torsion Fit (xTB scan)".format ( ff ) )
        self.label_legend.set_markup ( "   ".join ( '<span foreground="{}" weight="bold">━━</span> {}'.format ( _hex ( _COLORS[k] ), t )
                                                   for k, t in ( ( "qm", "xTB" ), ( "before", ff + " (current)" ),
                                                                 ( "after", ff + " (fitted)" ) ) ) )
        self.check_show_before.set_label ( "Show {} (current)".format ( ff ) )
        self.spin_charge.set_value ( target.default_charge )
        self.label_title.set_markup ( "<b>{} {}</b>\nScanned dihedral: <b>{}</b>, {:.1f} deg now.  "
                                      "Terms with this parameter in the molecule: {}.".format (
            ff, GLib.markup_escape_text ( target.key_text ), GLib.markup_escape_text ( "-".join ( target.atom_names ) ),
            F.dihedral_angle ( target.coordinates, target.quad ), len ( target.instances ) ) )
        self.label_note.set_markup ( self._note ( ) )
        self._clear_result ( )
        self.label_status.set_text ( "Current parameter ({}): {}".format ( target.units_note, target.current_text ) )

    def _note ( self ):
        t = self.target
        notes = [ GLib.markup_escape_text ( n ) for n in t.notes ( ) ]
        around = sum ( 1 for q in t.instances if { q[1], q[2] } == { t.quad[1], t.quad[2] } )
        if around < len ( t.instances ):
            notes.append ( "{} of the {} terms with this parameter in the molecule are on other bonds: the fitted parameter "
                           "changes them too.".format ( len ( t.instances ) - around, len ( t.instances ) ) )
        notes.append ( "Fitted: E = sum c<sub>n</sub> cos(n phi) to E<sub>xTB</sub> - E<sub>{0} without this parameter</sub> "
                       "at the scan geometries{1}; the {0} curves use the real MM energies.".format (
                       t.force_field, " (written back as k (1 + cos(n phi - delta)), delta 0/180)" if t.force_field == "OPLS" else "" ) )
        return "\n".join ( notes )

    def _clear_result ( self ):
        self.result = None
        self.label_result.set_text ( "" )
        self.button_apply.set_sensitive ( False )
        self.button_save.set_sensitive ( False )
        self.progressbar.set_fraction ( 0.0 )
        self.progressbar.set_text ( "" )
        child = self.box_plot.get_first_child()
        while child is not None:
            following = child.get_next_sibling()
            # A plot widget may have been reparented while its previous plot
            # was being replaced. Gtk.Box.remove() requires the widget to
            # still belong to this box.
            if child.get_parent() == self.box_plot:
                self.box_plot.remove(child)
            child = following
        self.plot = None

    def on_delete ( self, *args ):
        self.close_window ( )
        return True

    def close_window ( self, *args ):
        if self.runner is not None: self.runner.cancel ( )
        if self.visible:
            self.window.destroy ( )
            self.visible = False

    def on_button_close_clicked ( self, widget ):
        self.close_window ( )

    def on_radio_scan_toggled ( self, widget ):
        self.check_both_directions.set_sensitive ( self.radio_relaxed.get_active ( ) )

    #-------------------------------------------------------------------------
    #  R U N
    #-------------------------------------------------------------------------
    def on_button_run_clicked ( self, widget ):
        self._clear_result ( )
        t = self.target
        symbols, coordinates, bonds, quad = t.symbols, t.coordinates, t.bonds, t.quad
        try:
            F.moving_side ( F.adjacency_from_bonds ( len ( symbols ), bonds ), quad[1], quad[2] )
            xtb = self.vm_session.vm_config.gl_parameters.get ( 'xtb_command' ) or None
            solvent = selected_choice_value ( self.combo_solvent )
            self.runner = F.XTBRunner ( xtb = xtb, gfn = int ( selected_choice_value ( self.combo_method ) or 2 ),
                                        charge = int ( self.spin_charge.get_value ( ) ),
                                        multiplicity = int ( self.spin_multiplicity.get_value ( ) ),
                                        solvent = None if solvent in ( None, "none" ) else solvent,
                                        threads = max ( 1, min ( 8, ( os.cpu_count ( ) or 2 ) // 2 ) ) )
            n_electrons = sum ( _atomic_number ( s ) for s in symbols ) - self.runner.charge
            if ( n_electrons + self.runner.multiplicity - 1 ) % 2:
                raise ValueError ( "{} electrons and multiplicity {} are incompatible.".format ( n_electrons, self.runner.multiplicity ) )
        except Exception as error:
            self.runner = None
            self.label_status.set_text ( str ( error ) )
            return
        settings = dict ( step = self.spin_step.get_value ( ), relaxed = self.radio_relaxed.get_active ( ),
                          both_directions = self.radio_relaxed.get_active ( ) and self.check_both_directions.get_active ( ) )
        self._set_running ( True )
        runner = self.runner
        def progress ( fraction, text ):
            GLib.idle_add ( self._progress, fraction, text )
        def work ( ):
            try:
                scan = F.run_scan ( symbols, coordinates, bonds, quad, runner = runner, progress = progress, **settings )
                GLib.idle_add ( self._scan_done, runner, scan, None )
            except F.ScanCancelled:
                GLib.idle_add ( self._scan_done, runner, None, "Cancelled." )
            except Exception as error:
                traceback.print_exc ( )
                GLib.idle_add ( self._scan_done, runner, None, str ( error ) )
        threading.Thread ( target = work, daemon = True ).start ( )

    def on_button_cancel_clicked ( self, widget ):
        if self.runner is not None:
            self.runner.cancel ( )
            self.label_status.set_text ( "Cancelling..." )

    def _set_running ( self, running ):
        for widget in ( self.button_run, self.grid_options ):
            widget.set_sensitive ( not running )
        self.button_cancel.set_sensitive ( running )

    def _progress ( self, fraction, text ):
        if self.visible:
            self.progressbar.set_fraction ( max ( 0.0, min ( 1.0, fraction ) ) )
            self.progressbar.set_text ( text )
        return False

    def _scan_done ( self, runner, scan, error ):
        if runner is not self.runner: return False
        self.runner = None
        if not self.visible: return False
        self._set_running ( False )
        if error:
            self.progressbar.set_text ( "" )
            self.label_status.set_text ( error if error == "Cancelled." else "Scan failed: " + error.split ( "\n" )[0] )
            if error != "Cancelled.":
                self.main.simple_dialog.error ( msg = "xTB scan failed:\n{}".format ( error[-1200:] ) )
            return False
        t = self.target
        changed = t.changed ( )
        if changed:
            self.label_status.set_text ( changed )
            return False
        self.progressbar.set_text ( "Fitting..." )
        try:
            self.result = F.fit_dihedral_key ( scan, t.key_text, t.instances,
                                               lambda pairs: t.energies_for ( pairs, scan["geometries"] ),
                                               current_text = t.current_text, format_value = t.format_value,
                                               max_period = int ( self.spin_max_period.get_value ( ) ), force_field = t.force_field )
        except Exception as error:
            traceback.print_exc ( )
            self.progressbar.set_text ( "" )
            self.label_status.set_text ( "Fit failed: {}".format ( error ) )
            return False
        self.progressbar.set_fraction ( 1.0 )
        self.progressbar.set_text ( "Done: {} points".format ( len ( self.result["phi"] ) ) )
        self._show_result ( )
        return False

    #-------------------------------------------------------------------------
    #  R E S U L T
    #-------------------------------------------------------------------------
    def _show_result ( self ):
        r = self.result
        new, old = r["new_text"], r["old_text"]
        better = r["rmse_after"] < r["rmse_before"]
        text = ( "Current: <tt>{}</tt>\nFitted:  <tt><b>{}</b></tt>   ({})\n"
                 "RMSE vs xTB: {:.2f} → <b>{:.2f}</b> kJ/mol (weighted {:.2f} → {:.2f});  xTB barrier {:.2f} kJ/mol" ).format (
                 GLib.markup_escape_text ( old ), GLib.markup_escape_text ( new ), self.target.units_note, r["rmse_before"], r["rmse_after"],
                 r["wrmse_before"], r["wrmse_after"], r["barrier_qm"] )
        if r["warnings"]:
            text += "\n" + "\n".join ( '<span foreground="#b07000">{}</span>'.format ( GLib.markup_escape_text ( w ) ) for w in r["warnings"] )
        self.label_result.set_markup ( text )
        self.button_apply.set_sensitive ( True )
        self.button_save.set_sensitive ( True )
        self.label_status.set_text ( "Fit done." if better else "The fit did not improve on the current parameter." )
        self._draw_plot ( )

    def _draw_plot ( self ):
        from util.easyplot import XYPlot
        child = self.box_plot.get_first_child()
        while child is not None:
            following = child.get_next_sibling()
            if child.get_parent() == self.box_plot:
                self.box_plot.remove(child)
            child = following
        if self.result is None: return
        r = self.result
        plot = XYPlot ( sel_color = list ( _COLORS["qm"] ) )      # XYPlot draws every marker in sel_color
        plot.x_major_ticks = 8
        curves = [ ( "qm", r["qm"], "dot" ) ]
        if self.check_show_before.get_active ( ): curves.append ( ( "before", r["before"], None ) )
        curves.append ( ( "after", r["after"], None ) )
        for name, values, symbol in curves:
            plot.add ( X = list ( r["phi"] ), Y = list ( values ), symbol = symbol, sym_color = list ( _COLORS[name] ),
                       sym_fill = True, line = "solid", line_color = list ( _COLORS[name] ), label = name )
        plot.RC_label = self.label_hover
        self.box_plot.append(plot)
        self.plot = plot

    def on_check_show_before_toggled ( self, widget ):
        if self.result is not None: self._draw_plot ( )

    def on_button_apply_clicked ( self, widget ):
        if self.result is None: return
        try:
            message = self.target.apply ( self.result["pairs"] )
        except Exception as error:
            traceback.print_exc ( )
            self.main.simple_dialog.error ( msg = "The fitted parameter was not applied:\n{}".format ( error ) )
            return
        self.button_apply.set_sensitive ( False )
        self.label_status.set_text ( message )
        if self.on_applied is not None:
            self.on_applied ( "dihedral {}: fitted to the xTB scan. {}".format ( self.result["key"], message ) )

    def on_button_save_clicked ( self, widget ):
        if self.result is None: return
        dialog = Gtk.FileChooserDialog ( title = "Save torsion fit", transient_for = self.window,
                                         action = Gtk.FileChooserAction.SAVE )
        dialog.add_buttons ( "Cancel", Gtk.ResponseType.CANCEL, "Save", Gtk.ResponseType.OK )
        dialog.set_do_overwrite_confirmation ( True )
        folder = getattr ( self.target, "working_folder", None ) or os.getcwd ( )
        if os.path.isdir ( folder ): dialog.set_current_folder ( Gio.File.new_for_path(folder) )
        dialog.set_current_name ( "torsion_fit_{}_{}.txt".format ( self.target.force_field,
                                  "-".join ( self.target.atom_names ).replace ( " ", "" ).replace ( "/", "_" ) ) )
        dialog.connect("response", self._save_response)
        dialog.present()

    def _save_response(self, dialog, response):
        selected = dialog.get_file() if response == Gtk.ResponseType.OK else None
        path = selected.get_path() if selected is not None else None
        dialog.destroy()
        if not path:
            return
        base = os.path.splitext ( path )[0]
        with open ( base + ".txt", "w" ) as handle:
            handle.write ( F.report_text ( self.result ) + "\n" )
        written = [ base + ".txt" ]
        if self.plot is not None:
            try:
                from util.easyplot.export_utils import export_plot_to_png
                export_plot_to_png ( self.plot, base + ".png" )
                written.append ( base + ".png" )
            except Exception as error:
                traceback.print_exc ( )
        self.label_status.set_text ( "Saved: " + ", ".join ( os.path.basename ( p ) for p in written ) )

    def _build_window(self):
        self.window = Gtk.Window(title="Torsion Fit", transient_for=self.main.window)
        self.window.set_default_size(900, 700)
        self.window.connect("close-request", self.on_delete)
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        for side in ("top", "bottom", "start", "end"):
            getattr(root, f"set_margin_{side}")(10)
        self.window.set_child(root)
        self.label_title = Gtk.Label(xalign=0); self.label_title.set_use_markup(True); self.label_title.set_wrap(True)
        root.append(self.label_title)
        self.grid_options = Gtk.Grid(column_spacing=8, row_spacing=6)
        root.append(self.grid_options)
        self.combo_method = new_choice_dropdown(XTB_METHOD_CHOICES, "2")
        self.combo_solvent = new_choice_dropdown(XTB_SOLVENT_CHOICES, "none")
        for col, label, widget in ((0,"Method:",self.combo_method),(2,"Solvent (ALPB):",self.combo_solvent)):
            self.grid_options.attach(Gtk.Label(label=label, xalign=0), col, 0, 1, 1)
            self.grid_options.attach(widget, col+1, 0, 1, 1)
        self.spin_charge = self._spin(-20,20,1,0)
        self.spin_multiplicity = self._spin(1,9,1,1)
        self.spin_step = self._spin(5,60,5,15)
        self.spin_max_period = self._spin(1,6,1,4)
        for col, label, widget in ((0,"Charge:",self.spin_charge),(2,"Multiplicity:",self.spin_multiplicity),
                                   (0,"Step (degrees):",self.spin_step),(2,"Max period:",self.spin_max_period)):
            row = 1 if label in ("Charge:","Multiplicity:") else 2
            self.grid_options.attach(Gtk.Label(label=label, xalign=0), col, row, 1, 1)
            self.grid_options.attach(widget, col+1, row, 1, 1)
        mode_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.radio_relaxed = Gtk.CheckButton(label="Relaxed scan")
        self.radio_rigid = Gtk.CheckButton(label="Rigid scan")
        self.radio_rigid.set_group(self.radio_relaxed)
        self.radio_relaxed.set_active(True)
        self.radio_relaxed.connect("toggled", self.on_radio_scan_toggled)
        mode_box.append(self.radio_relaxed); mode_box.append(self.radio_rigid)
        self.check_both_directions = Gtk.CheckButton(label="Scan both directions (hysteresis)")
        self.check_show_before = Gtk.CheckButton(label="Show current parameter")
        self.check_show_before.set_active(True); self.check_show_before.connect("toggled", self.on_check_show_before_toggled)
        self.grid_options.attach(mode_box, 0, 3, 2, 1)
        self.grid_options.attach(self.check_both_directions, 2, 3, 2, 1)
        self.grid_options.attach(self.check_show_before, 0, 4, 2, 1)
        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        root.append(actions)
        self.button_run = Gtk.Button(label="Run xTB scan"); self.button_run.connect("clicked", self.on_button_run_clicked)
        self.button_cancel = Gtk.Button(label="Cancel"); self.button_cancel.set_sensitive(False); self.button_cancel.connect("clicked", self.on_button_cancel_clicked)
        self.button_save = Gtk.Button(label="Save data…"); self.button_save.set_sensitive(False); self.button_save.connect("clicked", self.on_button_save_clicked)
        self.button_apply = Gtk.Button(label="Apply fitted parameter"); self.button_apply.set_sensitive(False); self.button_apply.connect("clicked", self.on_button_apply_clicked)
        close = Gtk.Button(label="Close"); close.connect("clicked", self.on_button_close_clicked)
        for button in (self.button_run,self.button_cancel,self.button_save,self.button_apply,close): actions.append(button)
        self.progressbar = Gtk.ProgressBar(show_text=True); root.append(self.progressbar)
        self.label_legend = Gtk.Label(xalign=0); root.append(self.label_legend)
        self.label_result = Gtk.Label(xalign=0); self.label_result.set_use_markup(True); self.label_result.set_wrap(True); root.append(self.label_result)
        self.label_status = Gtk.Label(xalign=0); self.label_status.set_wrap(True); root.append(self.label_status)
        self.label_note = Gtk.Label(xalign=0); self.label_note.set_use_markup(True); self.label_note.set_wrap(True); root.append(self.label_note)
        self.label_hover = Gtk.Label(xalign=0); root.append(self.label_hover)
        self.box_plot = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True); root.append(self.box_plot)
        self.visible = True
        self.window.present()

    @staticmethod
    def _spin(lower, upper, step, value):
        adjustment = Gtk.Adjustment(value=value, lower=lower, upper=upper, step_increment=step, page_increment=step*5)
        return Gtk.SpinButton(adjustment=adjustment, digits=0)


def _atomic_number ( symbol ):
    from pScientific import PeriodicTable
    return PeriodicTable.AtomicNumber ( symbol )
