#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  filechooser.py
#  
#  Copyright 2021 Fernando <fernando@winter>
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

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk
from gui import file_dialogs


class FileChooser:
    """ Class doc """
    
    def __init__(self, main_window=None):
        """ Class initialiser """
        self.main_window = main_window
    
    def open(self, callback, select_multiple=False, filter_type=None):
        """Open a file chooser and deliver its selection asynchronously."""
        if select_multiple:
            filters = []
        else:
            filters = [filter_type or file_dialogs.file_filter("All files", "*")]
        file_dialogs.choose_file(
            self.main_window, callback, title="Open File...",
            mode=file_dialogs.OPEN_MULTIPLE if select_multiple else file_dialogs.OPEN,
            filters=filters,
        )
