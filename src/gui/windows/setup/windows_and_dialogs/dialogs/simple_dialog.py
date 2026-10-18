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
from gi.repository import Gtk, Pango
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gui.message_dialogs import ask_yes_no, show_message


#---------------------------------------
from pBabel                    import*                                     
from pCore                     import*  
#---------------------------------------
from pMolecule                 import*                              
from pMolecule.MMModel         import*
from pMolecule.NBModel         import*                                     
from pMolecule.QCModel         import*
#---------------------------------------
from pScientific               import*                                     
from pScientific.Arrays        import*                                     
from pScientific.Geometry3     import*                                     
from pScientific.RandomNumbers import*                                     
from pScientific.Statistics    import*
from pScientific.Symmetry      import*
#---------------------------------------                              
from pSimulation               import*
#---------------------------------------

#import Pickle
from gui.widgets.custom_widgets import FolderChooserButton
from gui.widgets.custom_widgets import VismolTrajectoryFrame
from gui.widgets.custom_widgets import SystemComboBox
from gui.widgets.custom_widgets import CoordinatesComboBox
from gui.widgets.custom_widgets import get_colorful_square_pixel_buffer
from gui.widgets.custom_widgets import ReactionCoordinateBox

#from gui.widgets.custom_widgets import get_distance
from util.geometric_analysis            import get_distance 
from util.geometric_analysis            import get_dihedral 
from util.geometric_analysis            import get_angle 

from pdynamo.p_methods import LogFile


import util.orca_qc_keywords as orca_keys

from util.file_parser import get_file_type  
from util.file_parser import read_MOL2  
import pprint
import numpy as np
import gc
import os

import traceback


VISMOL_HOME      = os.environ.get('VISMOL_HOME')
HOME             = os.environ.get('HOME')
PDYNAMO3_SCRATCH = os.environ.get('PDYNAMO3_SCRATCH')


def call_message_dialog (text1 = '', text2 = '', transient_for = None):
    """ Show an information message (portable across all GTK4 minors). """
    return show_message(transient_for, text1, text2 or None)


class SimpleDialog:
    """ Simple message and question dialogs parented to the main window.

    Delegates to gui.message_dialogs, which works on every GTK4 minor
    (Gtk.MessageDialog is deprecated since GTK 4.10 and Gtk.AlertDialog is
    absent on GTK 4.8).
    """

    def __init__(self, main = None, is_on_top = True):
        """ 
        Class initializer. 
        Stores a reference to the main application instance (main), 
        which is expected to have a window attribute used as the parent for dialogs. 
        """
        self.main = main
        self.is_on_top = is_on_top

    def _parent(self, parent = None):
        if parent is not None:
            return parent
        return getattr(self.main, "window", None)

    def info(self, msg = None, modal = True, title = None):
        """ Show an information dialog with an OK button. """
        show_message(self._parent(), msg, kind="info", title=title, modal=modal)
        return None

    def error(self, msg):
        """ Show an error dialog with an OK button. """
        show_message(self._parent(), msg, kind="error")
        return None

    def error_details (self, parent = None, msg = '', details = None, title = 'Error!'):
        """
        Shows an error dialog with a short message plus an expandable
        "Show details" section containing the full technical details (e.g.
        a traceback), so the user isn't stuck with only a one-line summary
        when something goes wrong.
        """
        show_message(self._parent(parent), msg, kind="error", title=title,
                     details=details if details is not None else "")
        return None

    def question(self, msg, callback=None):
        """ 
        Show a question dialog with YES and NO buttons. 
        Calls callback(True/False) after the user responds.
        """
        return ask_yes_no(self._parent(), msg, callback)
