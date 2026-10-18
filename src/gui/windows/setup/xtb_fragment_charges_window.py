#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  EasyHybrid: Python interface for QM/MM and molecular simulations using pDynamo3
#  Module: xtb_fragment_charges_window
#
#  Copyright 2022-2025 Fernando Bachega
#
"""
xtb_fragment_charges_window
===========================

GTK window (Phase 2) for the self-consistent fragment-based MM charge tool
(engine in util/xtb_fragment_charges.py).

Usage flow:
  1. choose the level (residue/segment/chain) -> "Build fragments" populates the
     treeview with SUGGESTED formal charge and multiplicity;
  2. the user can edit charge/multiplicity of each fragment in the treeview
     (the treeview is the source of truth before running);
  3. choose method (GFN0/1/2), charge model (CM5/Mulliken), tolerance,
     boundary mode, xTB path and number of processes;
  4. "Run" -> runs the self-consistent loop in a separate THREAD (each fragment
     is a process, via multiprocessing.Pool); the progress bar updates per cycle;
  5. "Apply to system" -> writes the final charges into system.mmState.charges.

Integration: instantiate with (main, system) and call open_window(). E.g.:
    win = XtbFragmentChargesWindow(main=self.main, system=active_system)
    win.open_window()
"""

import os
import threading

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib, Gio, GObject, GdkPixbuf
from gui.message_dialogs import show_message
from src.gtk4_compat import GTK_INVALID_LIST_POSITION
from gui.gtk4_context_menu import ContextMenu

from util import xtb_fragment_charges as xfc


def _dropdown_text(dropdown):
    item = dropdown.get_selected_item()
    return item.get_string() if item is not None else None


# --------------------------------------------------------------------------- #
#  Clustal X color palette (by amino-acid type), RGB 0-255.                    #
#  Simplified "per-residue" version (without the column-dependent alignment    #
#  rules): each residue group gets a fixed color.                              #
#  [VERIFY: confirm these are the Clustal colors you want for the paper]        #
# --------------------------------------------------------------------------- #
CLUSTAL_COLORS = {
    # hydrophobic / blue
    "A": (128, 160, 240), "I": (128, 160, 240), "L": (128, 160, 240),
    "M": (128, 160, 240), "F": (128, 160, 240), "W": (128, 160, 240),
    "V": (128, 160, 240), "C": (128, 160, 240),
    # red
    "K": (240, 21, 5), "R": (240, 21, 5),
    # magenta
    "D": (192, 72, 192), "E": (192, 72, 192),
    # green
    "N": (21, 194, 194), "Q": (21, 194, 194),
    "S": (21, 194, 194), "T": (21, 194, 194),
    # orange
    "G": (240, 144, 72),
    # yellow
    "P": (192, 192, 0),
    # cyan
    "H": (21, 164, 164), "Y": (21, 164, 164),
}
DEFAULT_RESIDUE_COLOR = (200, 200, 200)  # gray for anything that does not match

# 3-letter -> 1-letter code (to match the palette from the residue name)
_THREE_TO_ONE = {
    "ALA": "A", "ARG": "R", "ASN": "N", "ASP": "D", "CYS": "C", "GLN": "Q",
    "GLU": "E", "GLY": "G", "HIS": "H", "ILE": "I", "LEU": "L", "LYS": "K",
    "MET": "M", "PHE": "F", "PRO": "P", "SER": "S", "THR": "T", "TRP": "W",
    "TYR": "Y", "VAL": "V",
    # common protonation variants -> same base residue
    "HID": "H", "HIE": "H", "HIP": "H", "CYX": "C", "CYM": "C",
    "ASH": "D", "GLH": "E", "LYN": "K",
}


def _residue_one_letter(fragment_key):
    """Extract the 1-letter residue code from the 'CHAIN/RESNAME/SEQ' key."""
    try:
        resname = fragment_key.split("/")[1].upper()
    except Exception:
        return None
    if len(resname) == 1:
        return resname
    return _THREE_TO_ONE.get(resname[:3])


def clustal_rgb(fragment_key):
    """Clustal RGB color (0-255) for the fragment key; gray if unknown."""
    one = _residue_one_letter(fragment_key)
    return CLUSTAL_COLORS.get(one, DEFAULT_RESIDUE_COLOR)


def make_color_swatch(rgb, width=18, height=18):
    """Create a GdkPixbuf.Pixbuf filled with the rgb color (0-255)."""
    from gi.repository import GdkPixbuf
    r, g, b = int(rgb[0]), int(rgb[1]), int(rgb[2])
    a = 255
    swatch = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, width, height)
    swatch.fill((r << 24) | (g << 16) | (b << 8) | a)  # RGBA
    return swatch


class FragmentChargeRow(GObject.Object):
    """Editable fragment data displayed by the GTK4 ColumnView."""

    color = GObject.Property(type=GdkPixbuf.Pixbuf)
    include = GObject.Property(type=bool, default=True)
    key = GObject.Property(type=str, default="")
    atom_count = GObject.Property(type=int, default=0)
    charge = GObject.Property(type=int, default=0)
    multiplicity = GObject.Property(type=int, default=1)
    status = GObject.Property(type=str, default="")

    def __init__(self, color, include, key, atom_count, charge, multiplicity, status=""):
        super().__init__()
        self.color = color
        self.include = include
        self.key = key
        self.atom_count = atom_count
        self.charge = charge
        self.multiplicity = multiplicity
        self.status = status


class XtbFragmentChargesWindow:
    """Window for the fragment-based charge tool (xTB)."""

    def __init__(self, main=None, system=None):
        self.main = main.window
        self.easy_session = main
        self.system = system
        self.window = None
        self.fragments = []          # lista de xfc.Fragment
        self.result = None           # dict returned by the engine
        self._running = False
        self._selection_counter = 0  # numbers the fragments imported from selection

    # ------------------------------------------------------------------ #
    #  Construcao da UI                                                    #
    # ------------------------------------------------------------------ #
    def _on_choose_tmpdir(self, _button):
        """Open a FOLDER chooser for the xTB temporary files."""
        dialog = Gtk.FileChooserDialog(
            title="Select temporary folder",
            transient_for=self.window,
            action=Gtk.FileChooserAction.SELECT_FOLDER)
        dialog.add_buttons(
            "Cancel", Gtk.ResponseType.CANCEL,
            "Select", Gtk.ResponseType.OK)
        def on_response(chooser, response):
            if response == Gtk.ResponseType.OK:
                selected = chooser.get_file()
                if selected is not None:
                    self.entry_tmpdir.set_text(selected.get_path())
            chooser.destroy()

        dialog.connect("response", on_response)
        dialog.present()

    def _system_color_swatch(self):
        """Pixbuf of the small color square that identifies the system.

        Reuses the SAME function as the main window
        (get_colorful_square_pixel_buffer), so the square matches exactly the one
        shown in the main treeview. The color comes from system.e_color_palette['C'].
        Returns None if not possible (import failed or system without palette),
        in which case the window shows text only.
        """
        if self.system is None:
            return None
        try:
            from gui.windows.setup.setup_interface import get_colorful_square_pixel_buffer
            return get_colorful_square_pixel_buffer(self.system)
        except Exception:
            # fallback: build directly from the palette, without relying on the import
            try:
                from gi.repository import GdkPixbuf
                color = self.system.e_color_palette["C"]
                r, g, b = (int(color[0] * 255), int(color[1] * 255), int(color[2] * 255))
                sw = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, 20, 20)
                sw.fill((r << 24) | (g << 16) | (b << 8) | 255)
                return sw
            except Exception:
                return None

    def _system_name(self):
        """Name/identification of the active system, shown at the top of the window.

        Uses system.label (the system name in EasyHybrid); adds e_tag when
        available. Falls back to a generic text if nothing exists.
        """
        if self.system is None:
            return "(no system)"
        label = getattr(self.system, "label", None)
        tag = getattr(self.system, "e_tag", None)
        if label and tag:
            return "{} ({})".format(label, tag)
        if label:
            return str(label)
        return "(unnamed system)"

    def open_window(self):
        if self.window is not None:
            self.window.present()
            return

        self.window = Gtk.Window(title="xTB fragment charges")
        self.window.set_default_size(640, 560)
        self.window.set_margin_top(8)
        self.window.set_margin_bottom(8)
        self.window.set_margin_start(8)
        self.window.set_margin_end(8)
        self.window.connect("close-request", self._on_destroy)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.window.set_child(vbox)

        # ---- active system identification (color swatch + name) ----
        # shows which system is being worked on, with the SAME small color
        # square used in the main-window treeview, for quick visual
        # recognition when several systems are loaded.
        row_sys = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        swatch = self._system_color_swatch()
        if swatch is not None:
            self.img_system = Gtk.Image.new_from_pixbuf(swatch)
            row_sys.append(self.img_system)
        self.label_system = Gtk.Label()
        self.label_system.set_xalign(0.0)
        self.label_system.set_markup(
            "<b>System:</b> {}".format(self._system_name()))
        row_sys.append(self.label_system)
        vbox.append(row_sys)

        # ---- row 1: level + build / import selection ----
        row1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        row1.append(Gtk.Label(label="Fragment level:"))
        self.combo_level = self._make_dropdown(
            ("residue", "segment", "chain", "selection")
        )
        self.combo_level.connect("notify::selected", self._on_level_changed)
        row1.append(self.combo_level)

        self.btn_build = Gtk.Button(label="Build fragments")
        self.btn_build.connect("clicked", self.on_build_fragments)
        row1.append(self.btn_build)

        # button to import the current vismol selection as a fragment
        # (visible only in 'selection' mode)
        self.btn_import_sel = Gtk.Button(label="Import selection fragment")
        self.btn_import_sel.connect("clicked", self.on_import_selection)
        row1.append(self.btn_import_sel)
        vbox.append(row1)

        # ---- GTK4 fragment ColumnView with model-backed editors ----
        self.store = Gio.ListStore.new(FragmentChargeRow)
        self.selection = Gtk.NoSelection.new(self.store)
        self.treeview = Gtk.ColumnView.new(self.selection)
        self.treeview.append_column(self._make_column("", "color", self._setup_color, self._bind_color))
        include_factory = Gtk.SignalListItemFactory()
        include_factory.connect("setup", self._setup_include)
        include_factory.connect("bind", self._bind_include)
        include_factory.connect("unbind", self._unbind_include)
        self.treeview.append_column(Gtk.ColumnViewColumn.new("Use", include_factory))
        self.treeview.append_column(self._make_column("Fragment", "key", self._setup_label, self._bind_label))
        self.treeview.append_column(self._make_column("Atoms", "atom_count", self._setup_label, self._bind_label))
        self.treeview.append_column(self._make_column("Charge", "charge", self._setup_charge, self._bind_charge))
        self.treeview.append_column(self._make_column("Mult", "multiplicity", self._setup_multiplicity, self._bind_multiplicity))
        self.treeview.append_column(self._make_column("Status", "status", self._setup_label, self._bind_label))

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_child(self.treeview)
        scroll.set_vexpand(True)
        vbox.append(scroll)

        # context menu (right-click) to (de)select all
        click = Gtk.GestureClick()
        click.set_button(3)
        click.connect("pressed", self._on_treeview_button_press)
        self.treeview.add_controller(click)

        # ---- calculation options ----
        grid = Gtk.Grid(column_spacing=8, row_spacing=6)

        grid.attach(Gtk.Label(label="Method:"), 0, 0, 1, 1)
        self.combo_method = self._make_dropdown(("gfn1", "gfn2", "gfn0"))
        grid.attach(self.combo_method, 1, 0, 1, 1)

        grid.attach(Gtk.Label(label="Charge model:"), 2, 0, 1, 1)
        self.combo_charge = self._make_dropdown(("cm5", "mulliken"))
        grid.attach(self.combo_charge, 3, 0, 1, 1)

        grid.attach(Gtk.Label(label="Boundary:"), 0, 1, 1, 1)
        self.combo_boundary = self._make_dropdown(
            ("redistribute", "discard", "keep_on_boundary")
        )
        grid.attach(self.combo_boundary, 1, 1, 1, 1)

        grid.attach(Gtk.Label(label="Tolerance:"), 2, 1, 1, 1)
        self.entry_tol = Gtk.Entry()
        self.entry_tol.set_text("0.01")
        self.entry_tol.set_width_chars(8)
        grid.attach(self.entry_tol, 3, 1, 1, 1)

        grid.attach(Gtk.Label(label="Processes:"), 0, 2, 1, 1)
        self.entry_nproc = Gtk.Entry()
        self.entry_nproc.set_text("4")
        self.entry_nproc.set_width_chars(8)
        grid.attach(self.entry_nproc, 1, 2, 1, 1)
        

        grid.attach(Gtk.Label(label="Max cycles:"), 2, 2, 1, 1)
        self.entry_maxcyc = Gtk.Entry()
        self.entry_maxcyc.set_text("25")
        self.entry_maxcyc.set_width_chars(8)
        grid.attach(self.entry_maxcyc, 3, 2, 1, 1)

        grid.attach(Gtk.Label(label="Factor:"), 0, 3, 1, 1)
        self.entry_factor = Gtk.Entry()
        self.entry_factor.set_text("1.0")
        self.entry_factor.set_width_chars(8)
        grid.attach(self.entry_factor, 1, 3, 1, 1)

        grid.attach(Gtk.Label(label="xTB path:"), 0, 4, 1, 1)
        self.entry_xtb = Gtk.Entry()
        self.entry_xtb.set_text("xtb")
        self.entry_xtb.set_hexpand(True)
        grid.attach(self.entry_xtb, 1, 4, 3, 1)
        
        try:
            _XTBCommand = "PDYNAMO3_XTBCOMMAND"
            command = os.getenv ( _XTBCommand )
            self.entry_xtb.set_text(command)
        except:
            pass

        # ---- temporary files folder ----
        # where each fragment's xTB inputs/outputs are written.
        # Empty => use a system temporary folder (tempfile).
        grid.attach(Gtk.Label(label="Temp folder:"), 0, 5, 1, 1)
        self.entry_tmpdir = Gtk.Entry()
        self.entry_tmpdir.set_placeholder_text("(default: system temp)")
        self.entry_tmpdir.set_hexpand(True)
        grid.attach(self.entry_tmpdir, 1, 5, 2, 1)

        self.btn_tmpdir = Gtk.Button(label="Browse...")
        self.btn_tmpdir.connect("clicked", self._on_choose_tmpdir)
        grid.attach(self.btn_tmpdir, 3, 5, 1, 1)

        vbox.append(grid)

        # ---- progress bar ----
        self.progress = Gtk.ProgressBar()
        self.progress.set_show_text(True)
        self.progress.set_text("idle")
        vbox.append(self.progress)

        # ---- buttons ----
        row_btn = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.btn_run = Gtk.Button(label="Run")
        self.btn_run.connect("clicked", self.on_run)
        self.btn_run.set_sensitive(False)
        row_btn.append(self.btn_run)

        self.btn_apply = Gtk.Button(label="Apply to system")
        self.btn_apply.connect("clicked", self.on_apply)
        self.btn_apply.set_sensitive(False)
        row_btn.append(self.btn_apply)

        self.btn_close = Gtk.Button(label="Close")
        self.btn_close.connect("clicked", lambda *_: self.window.destroy())
        row_btn.append(self.btn_close)

        vbox.append(row_btn)

        self._setup_tooltips()
        self.window.present()
        self._on_level_changed(self.combo_level)  # set initial visibility

    def _setup_tooltips(self):
        """Attach explanatory tooltips to the controls.

        Kept in one place so the help text is easy to review and translate. The
        tooltips summarize the scientific meaning of each option (e.g. that CM5
        is only available with GFN1, or what each boundary mode does).
        """
        tips = {
            self.combo_level:
                "How the system is split into fragments:\n"
                "- residue / segment / chain: automatic grouping;\n"
                "- selection: build fragments manually from the current "
                "viewer selection (use 'Import selection fragment').",
            self.btn_build:
                "Split the active system into fragments at the chosen level and "
                "fill the table with a suggested formal charge and multiplicity "
                "for each fragment.",
            self.btn_import_sel:
                "Add the atoms currently selected in the 3D viewer as one "
                "fragment. Can be used several times to add multiple selection "
                "fragments (only in 'selection' level).",
            self.treeview:
                "One row per fragment. 'Use' toggles whether the fragment is "
                "recomputed (unchecked = keeps its MM charges but still enters "
                "the embedding). Charge and Mult are editable and override the "
                "suggested values. Right-click for select/deselect all.",
            self.combo_method:
                "xTB parametrization: GFN1, GFN2 or GFN0. Note: CM5 charges are "
                "only available with GFN1.",
            self.combo_charge:
                "Atomic charge model read from xTB output:\n"
                "- CM5: only with GFN1;\n"
                "- Mulliken: available with any GFN.\n"
                "If CM5 is chosen with GFN2/GFN0 the tool adjusts automatically.",
            self.combo_boundary:
                "How the charge of each capping hydrogen (link atom) is handled:\n"
                "- redistribute: add it onto the heavy atom it caps;\n"
                "- discard: drop it (removed by renormalization);\n"
                "- keep_on_boundary: keep it on the boundary heavy atom.",
            self.entry_tol:
                "Convergence threshold on the maximum atomic-charge change "
                "between cycles (max |dq|), in elementary charges. Default 0.01.",
            self.entry_nproc:
                "Number of fragments computed in parallel (one xTB process each) "
                "within a cycle. Higher = faster, up to your CPU core count.",
            self.entry_maxcyc:
                "Safety cap on the number of self-consistent cycles, in case "
                "convergence is not reached.",
            self.entry_factor:
                "Optional multiplier applied to the final charges when writing "
                "them to the system (1.0 = unchanged).",
            self.entry_xtb:
                "Path to the xTB executable. Prefilled from the "
                "PDYNAMO3_XTBCOMMAND environment variable when available.",
            self.entry_tmpdir:
                "Folder where each fragment's xTB input/output files are written. "
                "Leave empty to use a system temporary folder.",
            self.btn_tmpdir:
                "Choose the temporary folder.",
            self.btn_run:
                "Run the self-consistent calculation in the background. The "
                "progress bar updates once per cycle.",
            self.btn_apply:
                "Write the converged charges into the system's MM charges "
                "(system.mmState.charges). Only enabled after a successful run.",
        }
        for widget, text in tips.items():
            try:
                widget.set_tooltip_text(text)
            except Exception:
                pass

    def _on_level_changed(self, combo, _pspec=None):
        """Show 'Build fragments' for residue/segment/chain and
        'Import selection fragment' for 'selection' mode."""
        level = _dropdown_text(combo)
        is_sel = (level == "selection")
        # in selection mode: hide Build, show Import
        self.btn_build.set_visible(not is_sel)
        self.btn_import_sel.set_visible(is_sel)

    @staticmethod
    def _make_dropdown(options):
        model = Gtk.StringList.new(list(options))
        dropdown = Gtk.DropDown.new(model, None)
        dropdown.set_selected(0 if model.get_n_items() else GTK_INVALID_LIST_POSITION)
        return dropdown

    def _make_column(self, title, attribute, setup, bind):
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", setup)
        factory.connect("bind", bind, attribute)
        column = Gtk.ColumnViewColumn.new(title, factory)
        column.set_resizable(True)
        return column

    @staticmethod
    def _setup_color(_factory, list_item):
        picture = Gtk.Picture()
        picture.set_size_request(18, 18)
        list_item.set_child(picture)

    @staticmethod
    def _bind_color(_factory, list_item, _attribute):
        list_item.get_child().set_pixbuf(list_item.get_item().color)

    @staticmethod
    def _setup_label(_factory, list_item):
        label = Gtk.Label(xalign=0)
        label.set_margin_start(5)
        label.set_margin_end(5)
        list_item.set_child(label)

    @staticmethod
    def _bind_label(_factory, list_item, attribute):
        value = getattr(list_item.get_item(), attribute)
        list_item.get_child().set_text(str(value))

    @staticmethod
    def _setup_include(_factory, list_item):
        check = Gtk.CheckButton()
        check.connect("toggled", XtbFragmentChargesWindow._include_changed, list_item)
        list_item.set_child(check)

    @staticmethod
    def _bind_include(_factory, list_item):
        check = list_item.get_child()
        row = list_item.get_item()
        list_item._include_handler = row.connect(
            "notify::include", XtbFragmentChargesWindow._update_include_check, check
        )
        XtbFragmentChargesWindow._update_include_check(row, None, check)

    @staticmethod
    def _unbind_include(_factory, list_item):
        handler = getattr(list_item, "_include_handler", None)
        if handler is not None:
            list_item.get_item().disconnect(handler)
            list_item._include_handler = None

    @staticmethod
    def _update_include_check(row, _pspec, check):
        check._binding = True
        check.set_active(row.include)
        check._binding = False

    @staticmethod
    def _include_changed(check, list_item):
        if not getattr(check, "_binding", False):
            list_item.get_item().include = check.get_active()

    @staticmethod
    def _setup_spin(list_item, lower, upper):
        spin = Gtk.SpinButton.new_with_range(lower, upper, 1)
        spin.set_numeric(True)
        spin.connect("value-changed", XtbFragmentChargesWindow._spin_changed, list_item)
        list_item.set_child(spin)

    @staticmethod
    def _spin_changed(spin, list_item):
        if not getattr(spin, "_binding", False):
            property_name = spin._property_name
            setattr(list_item.get_item(), property_name, spin.get_value_as_int())

    @staticmethod
    def _setup_charge(_factory, list_item):
        XtbFragmentChargesWindow._setup_spin(list_item, -100, 100)
        list_item.get_child()._property_name = "charge"

    @staticmethod
    def _bind_charge(_factory, list_item, _attribute):
        spin = list_item.get_child()
        spin._binding = True
        spin.set_value(list_item.get_item().charge)
        spin._binding = False

    @staticmethod
    def _setup_multiplicity(_factory, list_item):
        XtbFragmentChargesWindow._setup_spin(list_item, 1, 20)
        list_item.get_child()._property_name = "multiplicity"

    @staticmethod
    def _bind_multiplicity(_factory, list_item, _attribute):
        spin = list_item.get_child()
        spin._binding = True
        spin.set_value(list_item.get_item().multiplicity)
        spin._binding = False

    # ------------------------------------------------------------------ #
    #  Callbacks                                                          #
    # ------------------------------------------------------------------ #
    def on_build_fragments(self, _button):
        level = _dropdown_text(self.combo_level)
        if level == "selection":
            # in selection mode fragments come from "Import selection fragment"
            return
        try:
            self.fragments = xfc.build_fragments(self.system, level=level)
        except Exception as e:
            self._error("Failed to build fragments: {}".format(e))
            return

        self.store.remove_all()
        for frag in self.fragments:
            swatch = make_color_swatch(clustal_rgb(frag.key))
            self.store.append(FragmentChargeRow(
                swatch, True, frag.key, len(frag.atom_indexes),
                frag.formal_charge, frag.multiplicity, ""
            ))
        self.btn_run.set_sensitive(len(self.fragments) > 0)
        self.btn_apply.set_sensitive(False)
        self.progress.set_text("{} fragments".format(len(self.fragments)))

    # ------------------------------------------------------------------ #
    #  Context menu: (de)select all                                       #
    # ------------------------------------------------------------------ #
    def _on_treeview_button_press(self, gesture, _n_press, x, y):
        menu = ContextMenu(gesture.get_widget())
        menu.add_item("Select all", self._select_all)
        menu.add_item("Deselect all", self._deselect_all)
        menu.add_item("Invert selection", self._invert_selection)
        menu.present(x=x, y=y)

    def _select_all(self, _item):
        self._set_all_included(True)

    def _deselect_all(self, _item):
        self._set_all_included(False)

    def _invert_selection(self, _item):
        for index in range(self.store.get_n_items()):
            row = self.store.get_item(index)
            row.include = not row.include

    def _set_all_included(self, include):
        for index in range(self.store.get_n_items()):
            self.store.get_item(index).include = include

    # ------------------------------------------------------------------ #
    #  Import the current vismol selection as a fragment                  #
    # ------------------------------------------------------------------ #
    def on_import_selection(self, _button):
        """Add the current vismol selection as a new fragment in the treeview.

        Can be called multiple times: each call adds a new selection as an
        independent fragment (editable charge/multiplicity).
        """
        indexes = self._get_current_selection_indexes()
        if not indexes:
            self._error("No atoms selected in the viewer.")
            return

        self._selection_counter += 1
        key = "SEL/{}".format(self._selection_counter)
        frag = xfc.Fragment(key, indexes)

        # suggested formal charge = rounded sum of the selection's MM charges
        acc = xfc.SystemAccessor(self.system)
        qsum = sum(acc.mm_charge(i) for i in indexes)
        frag.formal_charge = int(round(qsum))
        frag.multiplicity = 1
        self.fragments.append(frag)

        swatch = make_color_swatch(DEFAULT_RESIDUE_COLOR)  # custom selection: gray
        self.store.append(FragmentChargeRow(
            swatch, True, key, len(indexes), frag.formal_charge,
            frag.multiplicity, ""
        ))
        self.btn_run.set_sensitive(True)
        self.progress.set_text("{} fragment(s)".format(len(self.fragments)))

    def _get_current_selection_indexes(self):
        """GLOBAL indices (0-based) of the atoms currently selected in vismol.

        NOTE: the vismol atom has a 1-based .index; the engine uses 0-based. Here
        we convert (index - 1). Adjust if your mapping is different.
        """
        try:
            vm = self.easy_session.vm_session
            sel = vm.selections[vm.current_selection]
            indexes = []
            for atom in sel.selected_atoms:
                # atom.index is 1-based in vismol -> 0-based for the engine/pDynamo
                indexes.append(atom.index - 1)
            return sorted(set(indexes))
        except Exception as e:
            self._error("Could not read the current selection: {}".format(e))
            return []

    def on_run(self, _button):
        if self._running:
            return
        # transfer charge/mult/include from the treeview to the fragments (source of truth)
        for i, frag in enumerate(self.fragments):
            row = self.store.get_item(i)
            frag.formal_charge = row.charge
            frag.multiplicity = row.multiplicity
            frag.include = row.include

        if not any(f.include for f in self.fragments):
            self._error("No fragments selected for calculation.")
            return

        try:
            tmpdir = self.entry_tmpdir.get_text().strip()
            params = {
                "method": _dropdown_text(self.combo_method),
                "charge_model": _dropdown_text(self.combo_charge),
                "boundary_mode": _dropdown_text(self.combo_boundary),
                "tolerance": float(self.entry_tol.get_text()),
                "nprocs": int(self.entry_nproc.get_text()),
                "max_cycles": int(self.entry_maxcyc.get_text()),
                "xtb_path": self.entry_xtb.get_text().strip(),
                # temp folder: None => the engine uses the default tempfile
                "workroot": tmpdir if tmpdir else None,
            }
        except ValueError as e:
            self._error("Invalid option: {}".format(e))
            return

        # validate the temp folder, if provided
        if params["workroot"]:
            if not os.path.isdir(params["workroot"]):
                try:
                    os.makedirs(params["workroot"], exist_ok=True)
                except Exception as e:
                    self._error("Cannot create temp folder: {}".format(e))
                    return

        self._running = True
        self.btn_run.set_sensitive(False)
        self.btn_build.set_sensitive(False)
        self.btn_apply.set_sensitive(False)
        self.progress.set_fraction(0.0)
        self.progress.set_text("running...")

        thread = threading.Thread(target=self._run_worker, args=(params,), daemon=True)
        thread.start()

    def _run_worker(self, params):
        """Run the engine in a separate thread; update the UI via GLib.idle_add."""
        def cycle_cb(cycle, max_dq):
            frac = min(cycle / float(params["max_cycles"]), 1.0)
            GLib.idle_add(self._update_progress, frac,
                          "cycle {}: max |dq| = {:.5f}".format(cycle, max_dq))

        try:
            result = xfc.run_self_consistent_parallel(
                self.system, self.fragments, params["xtb_path"],
                method=params["method"], charge_model=params["charge_model"],
                boundary_mode=params["boundary_mode"],
                tolerance=params["tolerance"], max_cycles=params["max_cycles"],
                nprocs=params["nprocs"], workroot=params["workroot"],
                verbose=False, cycle_cb=cycle_cb)
            GLib.idle_add(self._run_done, result, None)
        except Exception as e:
            GLib.idle_add(self._run_done, None, str(e))

    def _update_progress(self, fraction, text):
        self.progress.set_fraction(fraction)
        self.progress.set_text(text)
        return False

    def _run_done(self, result, error):
        self._running = False
        self.btn_build.set_sensitive(True)
        self.btn_run.set_sensitive(True)
        if error:
            self.progress.set_text("error")
            self._error("Run failed: {}".format(error))
            return
        self.result = result
        conv = "converged" if result["converged"] else "NOT converged"
        self.progress.set_fraction(1.0)
        self.progress.set_text("{} in {} cycles (max|dq|={:.5f})".format(
            conv, result["cycles"], result["max_dq"]))
        self.btn_apply.set_sensitive(True)
        return False

    def on_apply(self, _button):
        
        try:
            factor = float(self.entry_factor.get_text())
        except:
            print('Invalid factor value! Using factor = 1.0.')
            factor = 1.0
        
        
        if not self.result:
            return
        try:
            xfc.apply_charges_to_system(self.system, self.result["charges_by_index"], factor)
            total = sum(self.result["charges_by_index"].values())
            self.progress.set_text("applied (total charge = {:.4f})".format(total))
            
        except Exception as e:
            self._error("Failed to apply charges: {}".format(e))

    def _on_destroy(self, *_):
        self.window = None

    def _error(self, message):
        show_message(self.window, message, kind='error', modal=True)
