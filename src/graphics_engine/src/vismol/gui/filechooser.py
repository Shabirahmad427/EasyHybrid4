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


class FileChooser:
    """ Class doc """
    
    def __init__(self, main_window=None):
        """ Class initialiser """
        self.main_window = main_window
    
    def open(self, callback, select_multiple=False, filter_type=None):
        """Open a file chooser and deliver its selection asynchronously."""
        chooser = Gtk.FileChooserDialog(
            title="Open File...", transient_for=self.main_window,
            action=Gtk.FileChooserAction.OPEN)
        chooser.add_buttons("Cancel", Gtk.ResponseType.CANCEL,
                            "Open", Gtk.ResponseType.OK)
        if select_multiple:
            chooser.set_select_multiple(True)
        else:
            if filter_type:
                chooser.add_filter(filter_type)
            else:
                filter = Gtk.FileFilter()
                filter.set_name("All files")
                filter.add_pattern("*")
                chooser.add_filter(filter)

        def on_response(current_chooser, response):
            selected = []
            if response == Gtk.ResponseType.OK:
                selected = [item.get_path() for item in current_chooser.get_files()]
            current_chooser.destroy()
            callback(selected if select_multiple else (selected[0] if selected else None))

        chooser.connect("response", on_response)
        chooser.present()
