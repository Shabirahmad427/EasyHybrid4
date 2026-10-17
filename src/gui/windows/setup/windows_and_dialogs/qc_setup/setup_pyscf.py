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
#      Setup dialog for the PySCF QC engine (pDynamo3 addOns.pySCF.QCModelPySCF).
#
from util.debug import dprint
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Pango
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gui.gtk4_builder import load_builder_file, load_builder_string
import cairo

import os


VISMOL_HOME      = os.environ.get('VISMOL_HOME')
HOME             = os.environ.get('HOME')
PDYNAMO3_SCRATCH = os.environ.get('PDYNAMO3_SCRATCH')

# . Named PySCF/Libxc exchange-correlation functionals, used only when Method
#   is RKS or UKS. Built from pyscf.dft.libxc.XC_ALIAS (PySCF's own curated
#   dict of named functional shortcuts) plus other well-known named hybrids/
#   range-separated functionals, all verified against
#   pyscf.dft.libxc.parse_xc() on pyscf 2.14.0. The combobox is editable, so
#   any other PySCF/Libxc-recognized functional string (not just the ones
#   listed here) can be typed in, including explicit "exchange,correlation"
#   combinations (e.g. "pbe,pbe").
COMMON_FUNCTIONALS = [
    'B3LYP'       , 'B3LYP5'      , 'B97-3'       , 'B97-D'       ,
    'BHANDH'      , 'BHANDHLYP'   , 'BLOC'        , 'BLYP'        ,
    'BOP'         , 'BP86'        , 'BPBE'        , 'CAM-B3LYP'   ,
    'CF22D'       , 'DLDF'        , 'GAM'         , 'HF'          ,
    'HFLYP'       , 'HFPW92'      , 'HSE03'       , 'HSE06'       ,
    'KT1'         , 'KT2'         , 'KT3'         , 'LDA'         ,
    'M05'         , 'M052X'       , 'M06'         , 'M062X'       ,
    'M06HF'       , 'M06L'        , 'M06_SX'      , 'M11L'        ,
    'MBEEF'       , 'MN12L'       , 'MN12SX'      , 'MN15'        ,
    'MN15L'       , 'MPW91'       , 'MS0'         , 'MS1'         ,
    'MS2'         , 'MS2H'        , 'MVS'         , 'MVSH'        ,
    'N12'         , 'N12SX'       , 'OLYP'        , 'OPBE'        ,
    'PBE'         , 'PBE0'        , 'PBEOP'       , 'PBESOL'      ,
    'PKZB'        , 'PW91'        , 'R2SCAN'      , 'R2SCANL'     ,
    'REVPBE'      , 'REVSCAN'     , 'REVSCAN_VV10', 'REVTPSS'     ,
    'RPBE'        , 'RSCAN'       , 'SCAN'        , 'SCAN0'       ,
    'SCANL'       , 'SCAN_RVV10'  , 'SCAN_VV10'   , 'SOGGA'       ,
    'SOGGA11'     , 'SOGGA11X'    , 'SPW92'       , 'SVWN'        ,
    'TPSS'        , 'TPSSH'       , 'WB97M-V'     , 'WB97X'       ,
    'WB97X-D'     , 'WB97X-V'     , 'X3LYP'       ,
]

# . Common PySCF-recognized basis set names. The combobox is editable, so any
#   other PySCF-recognized basis (not just the ones listed here) can be typed in.
COMMON_BASIS_SETS = [
    'STO-3G'    ,
    '3-21G'     ,
    '6-31G'     ,
    '6-31G*'    ,
    '6-31+G*'   ,
    '6-31G**'   ,
    '6-31+G**'  ,
    '6-311G'    ,
    '6-311G**'  ,
    '6-311+G**' ,
    'cc-pVDZ'   ,
    'cc-pVTZ'   ,
    'aug-cc-pVDZ',
    'def2-SVP'  ,
    'def2-SVPD' ,
    'def2-TZVP' ,
    'def2-TZVPP',
    'def2-QZVP' ,
]


class SetupPySCFWindow:
    """ Class doc """

    def __init__ (self, main, setup_QC_model_window):
        """ Class initialiser """
        self.main_session     = main
        self.vm_session       = main.vm_session
        self.home             = main.home
        self.Visible          = False
        self.vismol_object    = None
        self.window           = None

        self.parameters = {
                          'method'         : 'RHF' ,
                          'functional'     : 'b3lyp',
                          'orbitalBasis'   : '3-21G',
                          'deleteJobFiles' : True  ,
                          'useGPU'         : False ,
                          'scratch'        : None  , # os.path.join(scratch,'PySCFScratch')
                          }

        self.setup_QC_model_window = setup_QC_model_window

    def open_window (self, vismol_object = None):
        """ Function doc """
        if self.Visible  ==  False:
            self.builder = Gtk.Builder()
            load_builder_file(self.builder, os.path.join(self.home, 'src/gui/windows/setup/setup_qc_model_window.glade'))

            self.window = self.builder.get_object('window_setup_pyscf')
            self.window.set_default_size(450, 260)

            self.button_ok     = self.builder.get_object('btn_pyscf_ok')
            self.button_cancel = self.builder.get_object('btn_pyscf_cancel')
            self.button_ok.connect("clicked", self.on_button_ok)
            self.button_cancel.connect("clicked", self.close_window)

            self.box_method = self.builder.get_object('box_pyscf_method')

            #-----------------------------------------------------------
            self.method_model = Gtk.StringList.new([])
            for method in ('RHF', 'UHF', 'RKS', 'UKS', 'PM6'):
                self.method_model.append(method)
            self.method_cbox = Gtk.DropDown.new(
                self.method_model,
                Gtk.PropertyExpression.new(Gtk.StringObject, None, "string"),
            )
            self.method_cbox.connect("notify::selected", self.on_method_changed)
            self.box_method.append(self.method_cbox)

            self.box_basis = self.builder.get_object('box_pyscf_basis')

            #-----------------------------------------------------------
            self.basis_model = Gtk.StringList.new([])
            for basis in COMMON_BASIS_SETS:
                self.basis_model.append(basis)
            self.basis_cbox = Gtk.DropDown.new(
                self.basis_model,
                Gtk.PropertyExpression.new(Gtk.StringObject, None, "string"),
            )
            self.basis_entry = Gtk.Entry()
            self.basis_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            self.basis_box.append(self.basis_cbox)
            self.basis_box.append(self.basis_entry)
            self.basis_cbox.connect("notify::selected", self.on_basis_suggestion_selected)
            self.box_basis.append(self.basis_box)

            self.box_functional = self.builder.get_object('box_pyscf_functional')

            #-----------------------------------------------------------
            self.functional_model = Gtk.StringList.new([])
            for functional in COMMON_FUNCTIONALS:
                self.functional_model.append(functional)
            self.functional_cbox = Gtk.DropDown.new(
                self.functional_model,
                Gtk.PropertyExpression.new(Gtk.StringObject, None, "string"),
            )
            self.functional_entry = Gtk.Entry()
            self.functional_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            self.functional_box.append(self.functional_cbox)
            self.functional_box.append(self.functional_entry)
            self.functional_cbox.connect("notify::selected", self.on_functional_suggestion_selected)
            self.box_functional.append(self.functional_box)

            #.Interface Widgets
            self.entry_scratch        = self.builder.get_object('entry_pyscf_scratch')
            self.checkbox_delete_job_files = self.builder.get_object('checkbox_pyscf_delete_job_files')
            self.checkbox_use_gpu     = self.builder.get_object('checkbox_pyscf_use_gpu')

            #.Interface Show All
            self.window.connect("close-request", self.close_window)
            self.window.present()

            #.Assigning the previously adjusted parameters to the respective widgets.
            methods = ['RHF', 'UHF', 'RKS', 'UKS', 'PM6']
            self.method_cbox.set_selected(methods.index(self.parameters['method']))

            self.functional_entry.set_text(str(self.parameters['functional']))
            self.basis_entry.set_text(str(self.parameters['orbitalBasis']))
            self.checkbox_delete_job_files.set_active(self.parameters['deleteJobFiles'])
            self.checkbox_use_gpu.set_active(self.parameters['useGPU'])
            self.on_method_changed(self.method_cbox)

            _id    = self.main_session.p_session.active_id
            system = self.main_session.p_session.psystem[_id]

            scratch = self.parameters.get('scratch') or os.path.join(PDYNAMO3_SCRATCH, system.e_tag)
            self.entry_scratch.set_text(scratch)

            self.Visible  =  True

    def on_button_ok (self, widget):
        """ Function doc """
        methods = ['RHF', 'UHF', 'RKS', 'UKS', 'PM6']
        self.parameters['method'        ] = methods[self.method_cbox.get_selected()]
        self.parameters['functional'    ] = self.functional_entry.get_text()
        self.parameters['orbitalBasis'  ] = self.basis_entry.get_text()
        self.parameters['scratch'       ] = self.entry_scratch  .get_text()
        self.parameters['deleteJobFiles'] = self.checkbox_delete_job_files.get_active()
        self.parameters['useGPU'        ] = self.checkbox_use_gpu.get_active()

        dprint(self.parameters)
        dprint('on_button_ok')
        self.close_window (widget, None)

    def on_method_changed (self, widget, _pspec=None):
        """Keep the PM6 setup consistent with GPU4PySCF's SEM backend."""
        if not hasattr(self, 'checkbox_use_gpu'):
            return
        selected = widget.get_selected_item()
        isPM6 = selected is not None and selected.get_string() == 'PM6'
        if isPM6:
            self.checkbox_use_gpu.set_active(True)
        self.checkbox_use_gpu.set_sensitive(not isPM6)
        self.basis_cbox.set_sensitive(not isPM6)
        self.basis_entry.set_sensitive(not isPM6)
        self.functional_cbox.set_sensitive(not isPM6)
        self.functional_entry.set_sensitive(not isPM6)
        message = ('GPU4PySCF PM6 is experimental and currently supports pure-QM systems only; '
                   'basis and functional are not used.') if isPM6 else None
        self.method_cbox.set_tooltip_text(message)

    def on_basis_suggestion_selected(self, widget, _pspec=None):
        selected = widget.get_selected_item()
        if selected is not None:
            self.basis_entry.set_text(selected.get_string())

    def on_functional_suggestion_selected(self, widget, _pspec=None):
        selected = widget.get_selected_item()
        if selected is not None:
            self.functional_entry.set_text(selected.get_string())

    def close_window (self, button, data  = None):
        """ Function doc """
        if self.window:
            self.window.destroy()
        self.Visible    =  False
        return True
