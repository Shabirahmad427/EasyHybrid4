#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  vismol_gtkwidget.py
#  
#  Copyright 2022 Carlos Eduardo Sequeiros Borja <casebor@gmail.com>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
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
#  

from vismol.utils.debug import dprint
import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk
from src.gtk4_compat import texture_from_pixbuf
from gui import file_dialogs
from gui.response_dialog import ResponseDialog
from src.gtk4_compat import (
    GTK_INVALID_LIST_POSITION,
    apply_legacy_win32_wgl_workaround,
    gl_area_required_version,
    get_scroll_unit,
    scroll_delta_to_steps,
    scroll_controller_flags,
    set_gl_area_allowed_apis,
    supports_scroll_unit,
    widget_to_framebuffer_coordinates,
)
from gi.repository import GdkPixbuf

from logging import getLogger
from vismol.libgl.vismol_glcore import VismolGLCore
from vismol.gui.filechooser import FileChooser
logger = getLogger(__name__)

from OpenGL.GL import *
import numpy as np
from PIL import Image, ImageFilter, ImageOps, ImageChops
import os
import json
import sys

_IS_MACOS = sys.platform == "darwin"
_HAS_SCROLL_UNIT_API = supports_scroll_unit(Gtk)
_WidgetBase = Gtk.GLArea

def _patch_gl_line_width():
    """ Apple's GL only guarantees glLineWidth(1.0) under a core profile
        (GL_ALIASED_LINE_WIDTH_RANGE is commonly just [1.0, 1.0]). The
        codebase calls glLineWidth() with wider values (2-5) in ~34
        places across glaxis.py, representations.py and selection_box.py
        for the axis gizmo, selection box and wire representations.
        Rather than edit every call site, patched centrally here: every
        one of those modules does "from OpenGL import GL" and calls
        GL.glLineWidth(...), i.e. they all look up the function by
        attribute on the *same shared* OpenGL.GL module object at call
        time rather than binding their own copy at import time -- so
        patching that one attribute once covers every call site. Not
        gated to macOS: it's purely defensive (clamps the requested
        width to whatever the driver actually reports), a no-op on
        Linux/Mesa/NVIDIA where the supported range is normally wide.
    """
    from OpenGL import GL

    if getattr(GL.glLineWidth, "_vismol_patched", False):
        return

    original_glLineWidth = GL.glLineWidth

    def _clamped_glLineWidth(width):
        try:
            lo, hi = GL.glGetFloatv(GL.GL_ALIASED_LINE_WIDTH_RANGE)
            width = min(max(width, lo), hi)
        except Exception:
            pass
        return original_glLineWidth(width)

    _clamped_glLineWidth._vismol_patched = True
    GL.glLineWidth = _clamped_glLineWidth


class VismolGTKWidget(_WidgetBase):
    """GTK4 GLArea that renders VisMol's OpenGL scene on every platform.

    It needs a vertex and shader to be created; a later extension could
    allow changing the shaders dynamically.
    """

    def __init__(self, vismol_session=None, width=640.0, height=420.0):
        """ Class initialiser
        """
        super(VismolGTKWidget, self).__init__()
        # [EN] BUG FIX (real-world report: the app crashes/quits silently
        # on macOS, with the actual GtkGLArea widget suspected as the
        # cause). This widget's GL context was never given an explicit
        # required version -- meaning it relied entirely on GTK's own
        # DEFAULT context-negotiation behaviour, which on Linux/Mesa
        # tends to hand back something recent enough to run our
        # #version 330 shaders (geometry shaders, needed for the double/
        # triple bond rendering worked on earlier -- require OpenGL 3.2+
        # core) without ever being asked explicitly. macOS has NO
        # compatibility profile for OpenGL 3+ at all (confirmed via
        # Apple's own developer forums/documentation: only a "Legacy"
        # profile capped at the pre-3.2 feature set, or a strict Core
        # profile, nothing in between) -- so without requesting the
        # right version/profile up front, GTK's quartz backend may
        # negotiate a context our shaders can't actually use, or fail to
        # realize a usable context at all. set_required_version(3, 3)
        # asks for exactly what #version 330 needs, on every platform,
        # instead of leaving it to a default that happens to work on
        # Linux by coincidence rather than by being explicitly correct.
        set_gl_area_allowed_apis(self, Gdk)
        self.set_required_version(*gl_area_required_version(Gtk))
        apply_legacy_win32_wgl_workaround(self, Gtk)
        self.connect("realize", self.initialize)
        self.connect("render", self.render)
        self.connect("resize", self.reshape)
        _patch_gl_line_width()
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self._on_key_pressed)
        key_controller.connect("key-released", self._on_key_released)
        self.add_controller(key_controller)

        click_gesture = Gtk.GestureClick()
        click_gesture.set_button(0)
        click_gesture.connect("pressed", self._on_mouse_pressed)
        click_gesture.connect("released", self._on_mouse_released)
        self.add_controller(click_gesture)

        motion_controller = Gtk.EventControllerMotion()
        motion_controller.connect("motion", self._on_mouse_motion)
        self.add_controller(motion_controller)

        # Surface-unit processing is used only where the caller handles
        # smooth deltas explicitly; other platforms get GTK-normalized steps.
        scroll_flags = scroll_controller_flags(
            Gtk, use_surface_units=_IS_MACOS and _HAS_SCROLL_UNIT_API
        )
        scroll_controller = Gtk.EventControllerScroll.new(scroll_flags)
        scroll_controller.connect("scroll", self._on_mouse_scroll)
        self.add_controller(scroll_controller)
        self._scroll_remainder = 0.0
        self._scroll_modifiers = None
        self._scroll_unit_mode = None

        self.set_focusable(True)
        self.grab_focus()
        self.vm_selection_modes_list_store = Gtk.StringList.new(
            ["atom", "residue", "chain", "molecule"]
        )
        self.vm_session = vismol_session
        self.vm_glcore = VismolGLCore(self, vismol_session, width, height)
        self.glmenu_bg = None
        self.glmenu_sele = None
        self.glmenu_obj = None
        self.glmenu_pick = None
        self.filechooser = None
        self.selection_box_frame = None
    
    def initialize(self, widget):
        """ Enables the buffers and other charasteristics of the OpenGL context.
            sets the initial projection and view matrix
            
            self.flag -- Needed to only create one OpenGL program, otherwise a bunch of
                         programs will be created and use system resources. If the OpenGL
                         program will be changed change this value to True
        """
        # The GL context is created during realization, but GTK does not
        # guarantee it is current merely because the realize signal fired.
        # Make it current before any PyOpenGL calls; otherwise older GTK4
        # runtimes can emit a render callback with no current GL context.
        self.make_current()
        if self.get_error() != None:
            # Report GLArea context errors visibly instead of failing
            # without an explanation.
            error = self.get_error()
            print("FATAL: OpenGL context could not be created -- EasyHybrid cannot start.")
            print("  args:   ", error.args if error is not None else None)
            print("  code:   ", error.code if error is not None else None)
            print("  domain: ", error.domain if error is not None else None)
            print("  message:", error.message if error is not None else None)
            print("The GTK4 GLArea could not negotiate an OpenGL 3.3+ core context "
                  "with this system's graphics driver.")
            self.quit()
            return
        self.vm_glcore.initialize()
    
    def reshape(self, widget, width, height):
        """ Resizing function, takes the widht and height of the widget
            and modifies the view in the camera acording to the new values
        
            Keyword arguments:
            widget -- The widget that is performing resizing
            width -- Actual width of the window
            height -- Actual height of the window
        """
        self.vm_glcore.resize_window(width, height)
        self.queue_draw()
    
    def render(self, area, context):
        """ This is the function that will be called everytime the window
            needs to be re-drawed.
        """
        self.vm_glcore.render()
        return True

    def mouse_pressed(self, widget, event):
        """ Function doc """
        x, y = self._framebuffer_coordinates(event.x, event.y)
        if _IS_MACOS:
            self.vm_glcore.mouse_pressed(event.button, x, y, event.state)
        else:
            self.vm_glcore.mouse_pressed(event.button, x, y)
    
    def mouse_released(self, widget, event):
        """ Function doc """
        x, y = self._framebuffer_coordinates(event.x, event.y)
        if _IS_MACOS:
            self.vm_glcore.mouse_released(
                event.button, x, y,
                button_state=event.state, event=event)
        else:
            self.vm_glcore.mouse_released(
                event.button, x, y, event=event)
    
    def mouse_motion(self, widget, event):
        """ Function doc """
        x, y = self._framebuffer_coordinates(event.x, event.y)
        if _IS_MACOS:
            self.vm_glcore.mouse_motion(x, y, event.state)
        else:
            self.vm_glcore.mouse_motion(x, y)
    
    def mouse_scroll(self, widget, event):
        """ Function doc
        """
        if event.direction == Gdk.ScrollDirection.UP:
            self.vm_glcore.mouse_scroll(1)
        if event.direction == Gdk.ScrollDirection.DOWN:
            self.vm_glcore.mouse_scroll(-1)

    def _on_mouse_pressed(self, gesture, _press_count, x, y):
        button = gesture.get_current_button()
        state = gesture.get_current_event_state()
        x, y = self._framebuffer_coordinates(x, y)
        self.vm_glcore.mouse_pressed(button, x, y, state)

    def _on_mouse_released(self, gesture, _press_count, x, y):
        button = gesture.get_current_button()
        state = gesture.get_current_event_state()
        # Do not request get_current_event(): some GTK/PyGObject combinations
        # cannot marshal GdkButtonEvent. The GL core only uses the event as
        # optional context-menu metadata; the gesture coordinates are saved
        # below and provide the menu position.
        self._menu_x, self._menu_y = int(x), int(y)
        x, y = self._framebuffer_coordinates(x, y)
        self.vm_glcore.mouse_released(button, x, y, button_state=state)

    def _on_mouse_motion(self, controller, x, y):
        x, y = self._framebuffer_coordinates(x, y)
        self.vm_glcore.mouse_motion(x, y, controller.get_current_event_state())

    def _framebuffer_coordinates(self, x, y):
        """Convert GTK logical pointer positions for VisMol's GL pixel space."""
        return widget_to_framebuffer_coordinates(
            x,
            y,
            widget_width=self.get_width(),
            widget_height=self.get_height(),
            framebuffer_width=self.vm_glcore.width,
            framebuffer_height=self.vm_glcore.height,
        )

    def _on_mouse_scroll(self, controller, _dx, dy):
        if not np.isfinite(dy):
            return True
        if not _IS_MACOS or not _HAS_SCROLL_UNIT_API:
            if self._scroll_unit_mode != "wheel":
                self._scroll_remainder = 0.0
                self._scroll_unit_mode = "wheel"
            steps, self._scroll_remainder = scroll_delta_to_steps(
                dy, surface=False, remainder=self._scroll_remainder
            )
            direction = 1 if steps < 0 else -1
            for _ in range(abs(steps)):
                self.vm_glcore.mouse_scroll(direction)
            return True

        if dy == 0:
            return True

        unit = get_scroll_unit(controller)
        if unit == Gdk.ScrollUnit.SURFACE:
            if self._scroll_unit_mode != "surface":
                self._scroll_remainder = 0.0
                self._scroll_unit_mode = "surface"
            # Quartz trackpads report surface pixels, often 1–20 per event.
            # Accumulate 30 pixels per wheel step to avoid runaway zoom and
            # the resulting loss of the molecule from the clipping volume.
            state = controller.get_current_event_state()
            ctrl = bool(state & Gdk.ModifierType.CONTROL_MASK)
            shift = bool(state & Gdk.ModifierType.SHIFT_MASK)
            modifiers = (ctrl, shift)
            if modifiers != self._scroll_modifiers:
                self._scroll_modifiers = modifiers
                self._scroll_remainder = 0.0
            steps, self._scroll_remainder = scroll_delta_to_steps(
                dy, surface=True, remainder=self._scroll_remainder
            )
            if steps == 0:
                return True

            saved_ctrl, saved_shift = self.vm_glcore.ctrl, self.vm_glcore.shift
            self.vm_glcore.ctrl, self.vm_glcore.shift = ctrl, shift
            try:
                direction = 1 if steps > 0 else -1
                for _ in range(abs(steps)):
                    self.vm_glcore.mouse_scroll(direction)
            finally:
                self.vm_glcore.ctrl, self.vm_glcore.shift = saved_ctrl, saved_shift
        else:
            # Wheel-unit deltas can still be fractional on some backends.
            # Preserve their remainder just like the older-runtime fallback.
            if self._scroll_unit_mode != "wheel":
                self._scroll_remainder = 0.0
                self._scroll_unit_mode = "wheel"
            self._scroll_modifiers = None
            steps, self._scroll_remainder = scroll_delta_to_steps(
                dy, surface=False, remainder=self._scroll_remainder
            )
            if steps:
                direction = 1 if steps < 0 else -1
                for _ in range(abs(steps)):
                    self.vm_glcore.mouse_scroll(direction)
        return True

    def _on_key_pressed(self, _controller, keyval, _keycode, _state):
        try:
            getattr(self, "_pressed_" + Gdk.keyval_name(keyval))()
        except AttributeError:
            logger.debug("Press key %s has not been assigned to a handler yet", Gdk.keyval_name(keyval))
        return False

    def _on_key_released(self, _controller, keyval, _keycode, _state):
        try:
            getattr(self, "_released_" + Gdk.keyval_name(keyval))()
        except AttributeError:
            logger.debug("Release key %s has not been assigned to a handler yet", Gdk.keyval_name(keyval))
    
    def _build_glmenu(self, bg_menu=None, sele_menu=None, obj_menu=None, pick_menu=None):
        """Build the four VisMol context menus with GTK4 popovers."""
        if bg_menu is not None:
            self.glmenu_bg, self.glmenu_bg_toplabel = self._new_glmenu(
                "background", bg_menu, show_heading=False
            )
        else:
            self.glmenu_bg = None

        if sele_menu is not None:
            self.glmenu_sele, self.glmenu_sele_toplabel = self._new_glmenu(
                "selection", sele_menu, show_heading=False
            )
        else:
            self.glmenu_sele = None

        if pick_menu is not None:
            self.glmenu_pick, self.glmenu_pick_toplabel = self._new_glmenu(
                "picking", pick_menu, show_heading=True
            )
        else:
            self.glmenu_pick = None

        if obj_menu is not None:
            self.glmenu_obj, self.glmenu_obj_toplabel = self._new_glmenu(
                "object", obj_menu, show_heading=True
            )
        else:
            self.glmenu_obj = None

    def _new_glmenu(self, heading, menu_dict, show_heading):
        popover = Gtk.Popover()
        popover.set_parent(self)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        content.set_margin_top(6)
        content.set_margin_bottom(6)
        content.set_margin_start(6)
        content.set_margin_end(6)
        heading_label = Gtk.Label(label=heading)
        heading_label.set_xalign(0.0)
        heading_label.add_css_class("heading")
        if show_heading:
            content.append(heading_label)
            content.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        self._build_glmenu_from_dicts(menu_dict, content)
        popover.set_child(content)
        return popover, heading_label
     
    def open_file(self, widget):
        """ Function doc """
        if self.filechooser is None:
            self.filechooser = FileChooser(self.get_root())
        self.filechooser.open(
            callback=lambda filename: self.vm_session.load_molecule(filename) if filename else None
        )
    
    def key_pressed(self, widget, event):
        """ The key_pressed function serves, as the names states, to catch
            events in the keyboard, e.g. letter "l" pressed, "backslash"
            pressed. Note that there is a difference between "A" and "a".
            Here I use a specific handler for each key pressed after
            discarding the CONTROL, ALT and SHIFT keys pressed (usefull
            for customized actions) and maintained, i.e. it"s the same as
            using Ctrl+Z to undo an action.
        """
        try:
            func = getattr(self, "_pressed_" + Gdk.keyval_name(event.keyval))
            func()
        except AttributeError as ae:
            logger.debug("Press key {} has not been assigned to a handler "\
                         "yet".format(Gdk.keyval_name(event.keyval)))
    
    def key_released(self, widget, event):
        """ Used to indicates a key has been released.
        """
        try:
            func = getattr(self, "_released_" + Gdk.keyval_name(event.keyval))
            func()
        except AttributeError as ae:
            logger.debug("Release key {} has not been assigned to a handler "\
                         "yet".format(Gdk.keyval_name(event.keyval)))
    
    def _pressed_Escape(self):
        """ Function doc """
        self.quit()
    
    def _pressed_Right(self):
        """ Function doc """
        self.vm_session.forward_frame()
        self.queue_draw()

    def _released_Right(self):
        """ Function doc """
        pass
    
    def _pressed_Left(self):
        """ Function doc """
        self.vm_session.reverse_frame()
        self.queue_draw()
    
    def _released_Left(self):
        """ Function doc """
        pass
    
    def _pressed_Control_L(self):
        """ Function doc """
        self.vm_glcore.ctrl = True
    
    def _released_Control_L(self):
        """ Function doc """
        self.vm_glcore.ctrl = False
    
    def _pressed_Shift_L(self):
        """ Function doc """
        self.vm_glcore.shift = True
    
    def _released_Shift_L(self):
        """ Function doc """
        self.vm_glcore.shift = False

    if _IS_MACOS:
        # [EN] macOS trackpad fix: camera panning is bound to a
        # middle-mouse-button drag (vismol_glcore.py), but MacBook
        # trackpads have no middle button and no default gesture that
        # emulates one -- panning was effectively unreachable from a
        # trackpad. Holding Cmd while right-dragging (Cmd + two-finger-
        # drag on a trackpad) now also triggers pan (see
        # VismolGLCore.mouse_pressed's "and not self.cmd"/"or (... and
        # self.cmd ...)" gating), matching PyMOL's own Cmd+Right =
        # translate convention on macOS. Which keyval GTK reports for the
        # Cmd key can vary by GTK version/backend/keymap (only Meta_L was
        # actually observed on the tested setup); all four are wired as
        # cheap insurance. Gated to macOS only -- Meta_L/Super_L are real,
        # occasionally-bound X11 keysyms on Linux, so leaving these
        # handlers undefined there guarantees zero behavior change.
        def _pressed_Meta_L(self):
            """ Function doc """
            self.vm_glcore.cmd = True

        def _released_Meta_L(self):
            """ Function doc """
            self.vm_glcore.cmd = False

        _pressed_Meta_R  = _pressed_Meta_L
        _released_Meta_R = _released_Meta_L
        _pressed_Super_L  = _pressed_Meta_L
        _released_Super_L = _released_Meta_L
        _pressed_Super_R  = _pressed_Meta_L
        _released_Super_R = _released_Meta_L

    # [EN] Builder keyboard shortcuts ('a'/'d'/'b') -- only act while
    # Builder editing mode is on (builder_atom_mode), so these letter
    # keys don't hijack anything when the Builder isn't in use (e.g. if
    # 'a'/'b'/'d' end up wanted for some other, non-Builder shortcut
    # later, or are just typed for an unrelated reason). See
    # gui/windows/builder/click_mode.py for what each one does.
    def _pressed_a(self):
        """ Builder: switch to the "add atom" tool (plain click places a
        new atom) -- also the default tool whenever Builder mode is
        first turned on. """
        if getattr ( self.vm_session, "builder_atom_mode", False ):
            from gui.windows.builder.click_mode import set_tool
            set_tool ( self.vm_session, "add" )
            dprint ( "Builder: tool = add atom" )

    def _pressed_d(self):
        """ Builder: switch to the "delete atom" tool (plain click
        removes the clicked atom). """
        if getattr ( self.vm_session, "builder_atom_mode", False ):
            from gui.windows.builder.click_mode import set_tool
            set_tool ( self.vm_session, "delete" )
            dprint ( "Builder: tool = delete atom" )

    def _pressed_b(self):
        """ Builder: one-shot action -- adds a bond between the two
        atoms currently selected (shift-click two atoms first; see
        click_mode.handle_bond_shortcut() for the exact requirements). """
        if getattr ( self.vm_session, "builder_atom_mode", False ):
            from gui.windows.builder.click_mode import handle_bond_shortcut
            msg = handle_bond_shortcut ( self.vm_session )
            dprint ( "Builder: {}".format ( msg ) )
            self.queue_draw ( )
    
    def _selection_type_picking(self, widget):
        if self.selection_box_frame:
            self.selection_box_frame.change_toggle_button_selecting_mode_status(True)
        else:
            self.vm_session.picking_selection_mode = True
        self.queue_draw()
    
    def _selection_type_viewing(self, widget):
        if self.selection_box_frame:
            self.selection_box_frame.change_toggle_button_selecting_mode_status(False)
        else:
            self.vm_session.picking_selection_mode = False
        self.queue_draw()
    
    def quit(self):
        logger.info("Thanks for using our software :). Quitting Vismol.")
        application = Gtk.Application.get_default()
        if application is not None:
            application.quit()
    
    def _viewing_selection_mode_atom(self, widget):
        self.vm_session.viewing_selection_mode(sel_type="atom")
    
    def _viewing_selection_mode_residue(self, widget):
        self.vm_session.viewing_selection_mode(sel_type="residue")
    
    def _viewing_selection_mode_chain(self, widget):
        self.vm_session.viewing_selection_mode(sel_type="chain")
    
    def menu_show_dots(self, widget):
        self.vm_session.show_or_hide(rep_type="dots", show=True)
    
    def menu_hide_dots(self, widget):
        self.vm_session.show_or_hide(rep_type="dots", show=False)
    
    def menu_show_lines(self, widget):
        self.vm_session.show_or_hide(rep_type="lines", show=True)
    
    def menu_hide_lines(self, widget):
        self.vm_session.show_or_hide(rep_type="lines", show=False)
    
    def menu_show_nonbonded(self, widget):
        self.vm_session.show_or_hide(rep_type="nonbonded", show=True)
    
    def menu_hide_nonbonded(self, widget):
        self.vm_session.show_or_hide(rep_type="nonbonded", show=False)
    
    def menu_show_impostor(self, widget):
        self.vm_session.show_or_hide(rep_type="impostor", show=True)
    
    def menu_hide_impostor(self, widget):
        self.vm_session.show_or_hide(rep_type="impostor", show=False)
    
    def menu_show_spheres(self, widget):
        self.vm_session.show_or_hide(rep_type="spheres", show=True)
    
    def menu_hide_spheres(self, widget):
        self.vm_session.show_or_hide(rep_type="spheres", show=False)
    
    def menu_show_sticks(self, widget):
        self.vm_session.show_or_hide(rep_type="sticks", show=True)
    
    def menu_hide_sticks(self, widget):
        self.vm_session.show_or_hide(rep_type="sticks", show=False)
    
    def invert_selection(self, widget):
        self.vm_session.selections[self.vm_session.current_selection].invert_selection()
    
    def insert_glmenu(self, bg_menu=None, sele_menu=None, obj_menu=None, pick_menu=None):
        """ Function doc """
        if bg_menu is None:
            """ Standard Bg Menu"""
            bg_menu = {"Open File": ["MenuItem", self.open_file],
                       "separator": ["separator", None],
                       "Selection Mode": ["submenu",
                                            {"by atom": ["MenuItem", self._viewing_selection_mode_atom],
                                             "by residue": ["MenuItem", self._viewing_selection_mode_residue],
                                             "by chain": ["MenuItem", self._viewing_selection_mode_chain],
                                            }
                                         ],
                       "Selection Type": ["submenu",
                                            {"viewing": ["MenuItem", self._selection_type_viewing],
                                             "picking": ["MenuItem", self._selection_type_picking],
                                            }
                                         ],
                       "separator": ["separator", None],
                       "Quit": ["MenuItem", self.quit],
                      }
        
        if sele_menu is None:
            """ Standard Sele Menu """
            sele_menu = {"Show": ["submenu",
                                    {"dots": ["MenuItem", self.menu_show_dots],
                                     "lines": ["MenuItem", self.menu_show_lines],
                                     "nonbonded": ["MenuItem", self.menu_show_nonbonded],
                                     "sticks": ["MenuItem", self.menu_show_sticks],
                                     "impostor": ["MenuItem", self.menu_show_impostor],
                                     "spheres": ["MenuItem", self.menu_show_spheres],
                                    }
                                 ],
                         "Hide": ["submenu",
                                    {"dots": ["MenuItem", self.menu_hide_dots],
                                     "lines": ["MenuItem", self.menu_hide_lines],
                                     "nonbonded": ["MenuItem", self.menu_hide_nonbonded],
                                     "sticks": ["MenuItem", self.menu_hide_sticks],
                                     "impostor": ["MenuItem", self.menu_hide_impostor],
                                     "spheres": ["MenuItem", self.menu_hide_spheres],
                                    }
                                 ],
                         "separator":["separator", None],
                         "Invert Selection": ["MenuItem", self.invert_selection],
                        }
        
        if obj_menu is None:
            """ Standard Obj Menu"""
            obj_menu = {"Show": ["submenu",
                                    {"dots": ["MenuItem", None],
                                     "lines": ["MenuItem", None],
                                     "nonbonded": ["MenuItem", None],
                                    }
                                ],
                        "Hide": ["submenu",
                                    {"dots": ["MenuItem", None],
                                     "lines": ["MenuItem", None],
                                     "nonbonded": ["MenuItem", None],
                                    }
                                ],
                        "separator":["separator", None],
                        "label": ["submenu",
                                    {"Atom": ["submenu",
                                                {"index": ["MenuItem", None],
                                                 "name": ["MenuItem", None],
                                                 "residue": ["MenuItem", None],
                                                 "chain": ["MenuItem", None],
                                                 }
                                             ],
                                     "Residue": ["submenu",
                                                    {"index": ["MenuItem", None],
                                                     "name": ["MenuItem", None],
                                                     "chain": ["MenuItem", None],
                                                     }
                                                ],
                                     "Chain": ["submenu",
                                                {"name": ["MenuItem", None],
                                                 }
                                              ],
                                    },
                                 ],
                        }
        
        if pick_menu is None:
            """ Standard Sele Menu """
            pick_menu = {"Show": ["submenu",
                                    {"dots": ["MenuItem", None],
                                     "lines": ["MenuItem", None],
                                     "nonbonded": ["MenuItem", None],
                                    }
                                  ],
                         "Hide": ["submenu",
                                    {"dots": ["MenuItem", None],
                                     "lines": ["MenuItem", None],
                                     "nonbonded": ["MenuItem", None],
                                    }
                                  ],
                        }
        
        self._build_glmenu(bg_menu=bg_menu, sele_menu=sele_menu, obj_menu=obj_menu, pick_menu=pick_menu)
    
    def show_gl_menu(self, signals=None, menu_type=None, info=None, event=None):
        """Open the requested context menu at the pointer position."""
        menus = {
            "bg_menu": self.glmenu_bg,
            "sele_menu": self.glmenu_sele,
            "pick_menu": self.glmenu_pick,
            "obj_menu": self.glmenu_obj,
        }
        menu = menus.get(menu_type)
        if menu is None:
            return
        if menu_type == "obj_menu":
            self.glmenu_obj_toplabel.set_label(info or "object")
        rectangle = Gdk.Rectangle()
        rectangle.x = getattr(self, "_menu_x", 0)
        rectangle.y = getattr(self, "_menu_y", 0)
        rectangle.width = 1
        rectangle.height = 1
        menu.set_pointing_to(rectangle)
        menu.popup()
    
    def _build_submenus_from_dicts(self, menu_dict):
        """Build and return the content box for a nested GTK4 popover."""
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self._build_glmenu_from_dicts(menu_dict, content)
        return content
    
    def _build_glmenu_from_dicts(self, menu_dict, content):
        """Translate the original menu dictionary without changing its actions."""
        for label, definition in menu_dict.items():
            item_type, payload = definition
            if item_type == "separator":
                content.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
            elif item_type == "submenu":
                submenu = Gtk.Popover()
                submenu.set_child(self._build_submenus_from_dicts(payload))
                menu_button = Gtk.MenuButton(label=label)
                menu_button.set_popover(submenu)
                content.append(menu_button)
            else:
                button = Gtk.Button(label=label)
                button.add_css_class("flat")
                if payload is not None:
                    button.connect("clicked", payload)
                else:
                    button.set_sensitive(False)
                content.append(button)
    
    def capture_screenshot(self, scale_factor=1):
        """ Renders a fresh frame and reads it back from the OpenGL
            framebuffer as a numpy RGBA array (height, width, 4), ready
            to be saved or further processed (e.g. the cartoon filter in
            PreviewWindow).

            Keyword arguments:
            scale_factor -- render at this multiple of the widget's
                             current on-screen resolution (e.g. 2 or 3
                             for a 2x/3x resolution export). Rendering at
                             a higher resolution - rather than upscaling
                             the captured image afterwards - actually
                             produces finer geometry (thinner/smoother
                             lines, circles, text), not just a blurrier
                             enlargement of the same pixels. Default 1
                             captures at the widget's current size.

            Returns:
            image -- np.uint8 array of shape (height*scale_factor,
                     width*scale_factor, 4), or None if the GL context
                     could not be made current or the offscreen
                     framebuffer (when scale_factor > 1) failed.
        """
        self.make_current()
        if self.get_error() is not None:
            dprint("Error in OpenGL context")
            return None

        if scale_factor != 1:
            # vm_glcore.render_to_image() handles the offscreen
            # framebuffer at the higher resolution, including rendering
            # into it and restoring every bit of state afterwards.
            return self.vm_glcore.render_to_image(scale_factor)

        # Render a fresh frame synchronously into this widget's GL
        # context right before reading pixels back, so the capture
        # reflects the current camera/scene state instead of whatever
        # was left in the backbuffer from a previous (possibly partial)
        # draw cycle.
        self.vm_glcore.render()

        width = self.get_width()
        height = self.get_height()

        # Mesma garantia de sincronizacao aplicada em vm_glcore.render_to_image
        # -- garante que o desenho terminou de verdade na GPU antes da leitura.
        glFinish()
        data = glReadPixels(0, 0, width, height, GL_RGBA, GL_UNSIGNED_BYTE)

        # Converter para numpy
        image = np.frombuffer(data, dtype=np.uint8)
        image = image.reshape((height, width, 4))

        # Inverter verticalmente (OpenGL tem origem no canto inferior
        # esquerdo; imagens/PNG tem origem no canto superior esquerdo)
        image = np.flip(image, axis=0)
        # np.flip returns a view with negative strides, which PIL/some
        # encoders can choke on - make it a normal contiguous array.
        image = np.ascontiguousarray(image)
        return image

    def save_image(self, filename, scale_factor=1):
        """ Captures the current OpenGL view and saves it as a PNG file.

            Keyword arguments:
            filename -- path (including ".png" extension) where the
                        screenshot will be saved.
            scale_factor -- see capture_screenshot(); 2 or 3 for a
                             2x/3x resolution export, 1 (default) for
                             the widget's current on-screen resolution.

            Returns:
            True on success, False if the capture failed (e.g. invalid
            GL context or offscreen framebuffer error).
        """
        image = self.capture_screenshot(scale_factor=scale_factor)
        if image is None:
            return False

        # Note: this keeps the alpha channel as read from the framebuffer.
        # The GLArea is created with set_has_alpha(True) (see
        # VismolGLCore.initialize()), so background pixels may come back
        # non-opaque depending on the configured background_color alpha.
        # That's preserved here rather than silently flattened, since a
        # transparent-background PNG may be exactly what's wanted (e.g.
        # to drop the molecule into another image/slide).
        img = Image.fromarray(image, mode="RGBA")
        img.save(filename)
        dprint("Imagem salva em {}".format(filename))
        return True

    def open_export_preview(self):
        """ Captures the current OpenGL view (at screen resolution, for
            a cheap live preview) and opens the interactive Preview/Export
            window (PreviewWindow). From there the user can toggle/tweak
            the cartoon filter, save/load named style presets, and export
            the final PNG at a chosen resolution multiplier - which
            re-captures the scene at full quality rather than upscaling
            this preview image.
        """
        image = self.capture_screenshot()
        if image is None:
            return
        open_preview(image, glwidget=self)



# ---------------------------------------------------------------------------
# Pure image-processing / preset logic (no GTK), so it's testable on its
# own and reusable both for the cheap live preview and the final export.
# ---------------------------------------------------------------------------

FILTER_DEFAULTS = {
    "blur": 1.2,
    "colors": 16,
    "edge_threshold": 50,
    "blend": 0.8,
}
# Kept as an alias for backwards compatibility with any saved presets
# that still reference the old name.
CARTOON_FILTER_DEFAULTS = FILTER_DEFAULTS

FILTER_MODES = ("none", "outline", "cartoon")

RENDER_PRESETS_DIR = os.path.join(os.environ.get("HOME", "."), ".VisMol", "render_presets")


def apply_outline_filter(img, params, posterize):
    """ PyMOL-style outline post-processing. Mirrors PyMOL's
        ray_trace_mode: mode 1 ("normal color + black outline") is
        posterize=False here, mode 3 ("quantized color + black outline",
        the more cartoon-ish look) is posterize=True.

        Detecting the outline from the source image directly (rather
        than from PyMOL's real depth/normal buffers, which this 2D
        post-process doesn't have access to) means smooth shading
        gradients on a sphere can register as faint false edges. Two
        things keep that under control without needing depth data:
        blurring before edge detection (smooths out the gradual
        shading gradient while keeping the sharp true silhouette), and
        a high enough edge_threshold (the true silhouette's contrast is
        much higher than the residual shading gradient's). Detecting
        edges from the posterized image instead of the blurred original
        was tried and rejected: posterization itself splits each
        sphere's shading into a few flat bands, which then show up as
        extra concentric false-edge rings - worse than the residual
        gradient noise it was meant to fix.

        Keyword arguments:
        img       -- PIL.Image (RGB or RGBA) to process.
        params    -- dict with keys "blur", "colors", "edge_threshold",
                     "blend" (see FILTER_DEFAULTS for ranges/defaults).
                     "colors" is only used when posterize is True.
        posterize -- if True, quantize colors first (PyMOL mode 3 /
                     cartoon look). If False, keep full original colors
                     and shading, just add the outline (PyMOL mode 1).

        Returns:
        A new PIL.Image (RGB) with the effect applied.
    """
    blur = float(params.get("blur", FILTER_DEFAULTS["blur"]))
    colors = int(params.get("colors", FILTER_DEFAULTS["colors"]))
    edge_th = int(params.get("edge_threshold", FILTER_DEFAULTS["edge_threshold"]))
    blend_val = float(params.get("blend", FILTER_DEFAULTS["blend"]))

    base = img.convert("RGB")
    smooth = base.filter(ImageFilter.GaussianBlur(blur))

    if posterize:
        # MAXCOVERAGE preserves saturated, distinct colors much better
        # than the default MEDIANCUT method, which tends to compromise
        # between a sphere's lit/shaded gradient and washes the result
        # out towards gray. dither=0 (Dither.NONE) avoids a visible
        # checkerboard-like speckle pattern that Floyd-Steinberg
        # dithering (the default) leaves in smooth gradient areas like
        # a sphere's shading.
        colored = smooth.quantize(colors=colors, method=Image.MAXCOVERAGE, dither=0).convert("RGB")
    else:
        colored = base

    # Edge mask, detected from the blurred (not posterized - see
    # docstring) image. FIND_EDGES produces HIGH values exactly where
    # there's an edge and LOW (near 0) on flat areas. We want a mask
    # where EDGE pixels are BLACK (0, so they darken via multiply below)
    # and everything else is WHITE (255, neutral under multiply) -
    # getting this polarity backwards (e.g. inverting before
    # thresholding) makes the flat background end up white instead of
    # the edges, which then washes the entire image towards gray in the
    # final blend instead of just outlining the edges.
    edges_raw = smooth.convert("L").filter(ImageFilter.FIND_EDGES)
    edge_mask = edges_raw.point(lambda x: 0 if x >= edge_th else 255).convert("RGB")

    # multiply only darkens where the mask is black (the detected
    # edges), leaving flat/background areas exactly as they were in
    # `colored`. blend_val then controls how strong that outline is,
    # from 0 (no outline) to 1 (fully black outline where detected).
    outlined = ImageChops.multiply(colored, edge_mask)
    return Image.blend(colored, outlined, blend_val)


def apply_cartoon_filter(img, params):
    """ Backwards-compatible alias for apply_outline_filter(img, params,
        posterize=True) - the "cartoon" look (PyMOL ray_trace_mode 3).
    """
    return apply_outline_filter(img, params, posterize=True)


class RenderStylePreset:
    """ A named, JSON-serializable bundle of render/filter parameters.

        This is what lets a user style one frame in the preview window,
        save the preset by name, and later apply that exact same style
        to other frames/screenshots without redoing the sliders by hand.
    """

    def __init__(self, name="default", filter_mode="none", filter_params=None):
        """
        filter_mode -- one of FILTER_MODES:
                       "none"    - no post-processing (raw screenshot).
                       "outline" - PyMOL ray_trace_mode 1 style: original
                                   colors/shading + a black outline.
                       "cartoon" - PyMOL ray_trace_mode 3 style: quantized
                                   ("posterized") colors + a black outline.
        """
        self.name = name
        self.filter_mode = filter_mode if filter_mode in FILTER_MODES else "none"
        self.filter_params = dict(FILTER_DEFAULTS)
        if filter_params:
            self.filter_params.update(filter_params)

    @property
    def cartoon_enabled(self):
        """ Backwards-compatible view of the old boolean flag. """
        return self.filter_mode == "cartoon"

    def to_dict(self):
        return {
            "name": self.name,
            "filter_mode": self.filter_mode,
            "filter_params": self.filter_params,
        }

    @classmethod
    def from_dict(cls, data):
        # Back-compat: presets saved before filter_mode existed only
        # had a "cartoon_enabled" boolean and "cartoon_params".
        if "filter_mode" not in data and "cartoon_enabled" in data:
            mode = "cartoon" if data.get("cartoon_enabled") else "none"
            params = data.get("cartoon_params")
        else:
            mode = data.get("filter_mode", "none")
            params = data.get("filter_params")
        return cls(name=data.get("name", "default"), filter_mode=mode, filter_params=params)

    def apply(self, img):
        """ Returns img with this preset's effect applied (or img
            untouched, converted to RGB, if filter_mode is "none").
        """
        if self.filter_mode == "none":
            return img.convert("RGB")
        return apply_outline_filter(img, self.filter_params,
                                     posterize=(self.filter_mode == "cartoon"))

    @staticmethod
    def _safe_filename(name):
        keep = "-_ "
        cleaned = "".join(c for c in name if c.isalnum() or c in keep).strip()
        return (cleaned or "preset") + ".json"

    def save(self, presets_dir=RENDER_PRESETS_DIR):
        """ Saves this preset as <presets_dir>/<name>.json (name is
            sanitized for use as a filename). Creates presets_dir if it
            doesn't exist yet.
        """
        os.makedirs(presets_dir, exist_ok=True)
        path = os.path.join(presets_dir, self._safe_filename(self.name))
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
        return path

    @classmethod
    def load(cls, path):
        with open(path, "r") as f:
            data = json.load(f)
        return cls.from_dict(data)

    @staticmethod
    def list_presets(presets_dir=RENDER_PRESETS_DIR):
        """ Returns a sorted list of preset names available in
            presets_dir (the .json extension is stripped). Returns an
            empty list if the directory doesn't exist yet.
        """
        if not os.path.isdir(presets_dir):
            return []
        names = [os.path.splitext(f)[0] for f in os.listdir(presets_dir)
                  if f.endswith(".json")]
        return sorted(names)


# ---------------------------------------------------------------------------
# GTK preview window
# ---------------------------------------------------------------------------

class PreviewWindow(Gtk.Window):
    """ Shows a small live preview of the current OpenGL view with an
        optional cartoon filter, lets the user tweak the filter with
        sliders, save/load named style presets, and export the result at
        a chosen resolution.

        Unlike a quick "process the already-captured image" approach,
        Export re-captures the scene through glwidget at the requested
        scale_factor (via VismolGTKWidget.capture_screenshot /
        VismolGLCore.render_to_image) so the exported PNG is rendered at
        full quality, not an upscaled/blurred copy of the small preview.
    """

    def __init__(self, image_array, glwidget):
        super().__init__(title="Preview / Export")
        self.glwidget = glwidget

        self.set_default_size(640, 420)
        # Independent top-level window, not a nested mainloop: closing it
        # only destroys this window, it doesn't quit the application.
        self.connect("close-request", lambda *_: False)

        # imagem original (PIL) - this is just the cheap on-screen-res
        # capture used for the live preview, not what gets exported.
        self.original = Image.fromarray(image_array)
        #self.preview_base = self.original.resize(
        #    (max(1, self.original.width // 4), max(1, self.original.height // 4))
        #)
        self.preview_base = self.original

        # layout principal
        self.general_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.general_box.set_margin_top(10)
        self.general_box.set_margin_bottom(10)
        self.general_box.set_margin_start(10)
        self.general_box.set_margin_end(10)
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.general_box.append(box)
        box.set_vexpand(True)
        
        self.set_child(self.general_box)

        self.image_widget = Gtk.Image()
        box.append(self.image_widget)
        self.image_widget.set_hexpand(True)
        self.image_widget.set_vexpand(True)

        controls = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.append(controls)

        # modo de filtro: nenhum, contorno (cor original, estilo PyMOL
        # ray_trace_mode 1), ou cartoon (cor posterizada + contorno,
        # estilo PyMOL ray_trace_mode 3).
        mode_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        
        self.btn_refresh = Gtk.Button(label="Refresh")
        self.btn_refresh.connect("clicked", self.on_refresh_image)
        
        controls.append(self.btn_refresh)
        
        mode_box.append(Gtk.Label(label="Style:"))
        
        mode_box.append(Gtk.Label(label="Style:"))
        self._mode_labels = [
            #("none", "Sem efeito"),
            #("outline", "Contorno (cor original)"),
            #("cartoon", "Cartoon (posterizado)"),
            
            ("none"   , "No effect"), 
            ("outline", 'Outline (original color)'), 
            ("cartoon", "Cartoon (posterized)"),
        ]
        self.mode_labels = [label for _, label in self._mode_labels]
        self.mode_combo = Gtk.DropDown.new(
            Gtk.StringList.new(self.mode_labels), None
        )
        self.mode_combo.set_selected(0)
        self.mode_combo.connect("notify::selected", self.on_change)
        mode_box.append(self.mode_combo)
        controls.append(mode_box)

        self.blur = self._create_slider("Blur", 0.0, 5.0,
                                         FILTER_DEFAULTS["blur"], controls)
        self.colors = self._create_slider("Color (cartoon mode only)", 2, 64,
                                           FILTER_DEFAULTS["colors"], controls)
        self.edge = self._create_slider("Borders", 0, 255,
                                         FILTER_DEFAULTS["edge_threshold"], controls)
        self.blend = self._create_slider("Contour Intensity", 0.0, 1.0,
                                          FILTER_DEFAULTS["blend"], controls)

        controls.append(Gtk.Separator())

        # --- presets: salvar/carregar o conjunto de parâmetros acima ---
        preset_label = Gtk.Label(label="Style Preset:")
        preset_label.set_halign(Gtk.Align.START)
        controls.append(preset_label)

        self.preset_combo = Gtk.DropDown.new(Gtk.StringList.new([]), None)
        self._refresh_preset_list()
        controls.append(self.preset_combo)

        preset_btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        load_btn = Gtk.Button(label="load")
        load_btn.connect("clicked", self.on_load_preset)
        preset_btn_box.append(load_btn)
        load_btn.set_hexpand(True)
        save_btn = Gtk.Button(label="Save as...")
        save_btn.connect("clicked", self.on_save_preset)
        preset_btn_box.append(save_btn)
        save_btn.set_hexpand(True)
        controls.append(preset_btn_box)

        controls.append(Gtk.Separator())

        # --- export: escala + caminho do arquivo ---
        scale_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        scale_box.append(Gtk.Label(label="Resolution:"))
        self.scale_options = ["1x (screen)", "2x", "3x", "4x"]
        self.scale_combo = Gtk.DropDown.new(
            Gtk.StringList.new(self.scale_options), None
        )
        self.scale_combo.set_selected(1)  # default 2x, já que é o motivo de ter essa janela
        scale_box.append(self.scale_combo)
        controls.append(scale_box)

        export_btn = Gtk.Button(label="Export PNG...")
        export_btn.connect("clicked", self.on_export)
        controls.append(export_btn)

        self.status_label = Gtk.Label(label="")
        self.status_label.set_halign(Gtk.Align.START)
        self.general_box.append(self.status_label)

        self.update_preview()

    def _create_slider(self, label, minv, maxv, default, parent):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        parent.append(box)

        lbl = Gtk.Label(label=label)
        lbl.set_halign(Gtk.Align.START)
        box.append(lbl)

        adj = Gtk.Adjustment(default, minv, maxv, 0.1, 1, 0)
        scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adj)
        scale.connect("value-changed", self.on_change)
        box.append(scale)
        return scale

    def _current_preset(self, name="default"):
        """ Builds a RenderStylePreset from the current state of every
            control in the window.
        """
        mode_index = self.mode_combo.get_selected()
        mode = (self._mode_labels[mode_index][0]
                if mode_index != GTK_INVALID_LIST_POSITION else "none")
        return RenderStylePreset(
            name=name,
            filter_mode=mode,
            filter_params={
                "blur": self.blur.get_value(),
                "colors": int(self.colors.get_value()),
                "edge_threshold": int(self.edge.get_value()),
                "blend": self.blend.get_value(),
            },
        )

    def _apply_preset_to_controls(self, preset):
        """ Pushes a RenderStylePreset's values into the sliders/mode
            combo (the reverse of _current_preset), then refreshes the
            preview.
        """
        mode_to_index = {mode: i for i, (mode, _) in enumerate(self._mode_labels)}
        self.mode_combo.set_selected(mode_to_index.get(preset.filter_mode, 0))
        self.blur.set_value(preset.filter_params.get("blur", FILTER_DEFAULTS["blur"]))
        self.colors.set_value(preset.filter_params.get("colors", FILTER_DEFAULTS["colors"]))
        self.edge.set_value(preset.filter_params.get("edge_threshold", FILTER_DEFAULTS["edge_threshold"]))
        self.blend.set_value(preset.filter_params.get("blend", FILTER_DEFAULTS["blend"]))
        self.update_preview()

    def update_preview(self):
        preset = self._current_preset()
        img = preset.apply(self.preview_base)

        data = np.array(img)
        height, width, _ = data.shape

        pixbuf = GdkPixbuf.Pixbuf.new_from_data(
            data.tobytes(),
            GdkPixbuf.Colorspace.RGB,
            False,
            8,
            width,
            height,
            width * 3
        )
        # keep a reference alive for the lifetime of the pixbuf - GTK
        # doesn't copy the buffer, only holds this Python object's data
        self._preview_pixbuf_data = data
        self.image_widget.set_from_paintable(texture_from_pixbuf(pixbuf))

    def on_change(self, widget, _pspec=None):
        self.update_preview()

    def _refresh_preset_list(self):
        self.preset_names = RenderStylePreset.list_presets()
        self.preset_combo.set_model(Gtk.StringList.new(self.preset_names))

    def on_refresh_image (self, widget):
        """ Function doc """
        dprint('Refresh image')
        image = self.glwidget.capture_screenshot()
        self.preview_base =  Image.fromarray(image)
        self.update_preview()
        
    def on_save_preset(self, widget):
        dialog = ResponseDialog(title="Save Preset", transient_for=self, modal=True)
        dialog.add_buttons("Cancel", Gtk.ResponseType.CANCEL,
                            "Save", Gtk.ResponseType.OK)
        entry = Gtk.Entry()
        entry.set_text("my style")
        entry.set_activates_default(True)
        dialog.get_content_area().append(Gtk.Label(label="Preset name:"))
        dialog.get_content_area().append(entry)
        dialog.set_default_response(Gtk.ResponseType.OK)
        def on_response(current_dialog, response):
            name = entry.get_text().strip()
            current_dialog.destroy()
            if response == Gtk.ResponseType.OK and name:
                preset = self._current_preset(name=name)
                path = preset.save()
                self._refresh_preset_list()
                self.status_label.set_text("Preset saved: {}".format(path))

        dialog.connect("response", on_response)
        dialog.present()

    def on_load_preset(self, widget):
        preset_index = self.preset_combo.get_selected()
        if preset_index == GTK_INVALID_LIST_POSITION:
            self.status_label.set_text("No preset selected.")
            return
        name = self.preset_names[preset_index]
        path = os.path.join(RENDER_PRESETS_DIR, RenderStylePreset._safe_filename(name))
        try:
            preset = RenderStylePreset.load(path)
        except (OSError, json.JSONDecodeError) as e:
            self.status_label.set_text("Failed to load preset: {}".format(e))
            return
        self._apply_preset_to_controls(preset)
        self.status_label.set_text("Preset loaded: {}".format(name))

    def on_export_old(self, widget):
        scale_factor = int(self.scale_options[self.scale_combo.get_selected()][0])

        self._choose_export_path(scale_factor, "export.png")

    def on_export(self, widget):
        scale_factor = int(self.scale_options[self.scale_combo.get_selected()][0])

        if getattr(self, 'last_export_file', False):
            filename = self._get_unique_filename(self.last_export_file)
        else:
            filename = self._get_unique_filename("export.png")
        self._choose_export_path(scale_factor, filename)

    def _choose_export_path(self, scale_factor, filename):
        folder = getattr(self, "last_export_dir", None) or os.getcwd()

        def on_selected(path):
            self.last_export_file = path
            if path:
                self._export_image(path, scale_factor)

        file_dialogs.choose_file(
            self, on_selected, title="Export PNG", mode=file_dialogs.SAVE,
            initial_path=os.path.join(folder, filename),
            filters=[file_dialogs.file_filter("PNG image (*.png)", "*.png")],
        )

    def _export_image(self, filename, scale_factor):
        if not filename.lower().endswith(".png"):
            filename += ".png"
        self.last_export_dir = os.path.dirname(filename)

        # Render at the chosen resolution, then apply the selected style.
        full_res_array = self.glwidget.capture_screenshot(
            scale_factor=scale_factor
        )

        if full_res_array is None:
            self.status_label.set_text(
                "Failed to capture the scene in high resolution."
            )
            return

        full_res_img = Image.fromarray(full_res_array)
        preset = self._current_preset()
        final = preset.apply(full_res_img)
        final.save(filename)

        self.status_label.set_text(
            "Exported: {} ({}x)".format(filename, scale_factor)
        )
        
    def _get_unique_filename(self, filepath):
        """
        Se filepath já existir, gera:
        export.png
        export_1.png
        export_2.png
        ...
        """
        if not os.path.exists(filepath):
            return filepath

        folder, filename = os.path.split(filepath)
        base, ext = os.path.splitext(filename)

        counter = 1
        while True:
            new_name = f"{base}_{counter}{ext}"
            new_path = os.path.join(folder, new_name)

            if not os.path.exists(new_path):
                return new_path

            counter += 1



# ---- USO ----
def open_preview(image_array, glwidget):
    win = PreviewWindow(image_array, glwidget)
    win.present()
