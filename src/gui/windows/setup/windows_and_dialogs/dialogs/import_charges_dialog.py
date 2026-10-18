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
from gi.repository import Gtk, Gio, GObject
from gui.response_dialog import ResponseDialog


class ChargeTypeRow(GObject.Object):
    label = GObject.Property(type=str, default="")

    def __init__(self, label):
        super().__init__()
        self.label = str(label)


class ChargeTypeSelectionDialog(ResponseDialog):
    def __init__(self, parent, items):
        super().__init__(
            #title="Escolha um item",
            transient_for=parent
        )

        self.set_default_size(350, 300)

        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        self.add_button("OK", Gtk.ResponseType.OK)

        box = self.get_content_area()
        self.store = Gio.ListStore.new(ChargeTypeRow)
        for item in items:
            self.store.append(ChargeTypeRow(item))

        self.selection = Gtk.SingleSelection.new(self.store)
        self.selection.set_autoselect(False)
        self.selection.set_can_unselect(True)
        self.column_view = Gtk.ColumnView.new(self.selection)
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._setup_item)
        factory.connect("bind", self._bind_item)
        self.column_view.append_column(Gtk.ColumnViewColumn.new("Item", factory))

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_child(self.column_view)

        box.append(scrolled)

        self.present()

    @staticmethod
    def _setup_item(_factory, list_item):
        label = Gtk.Label(xalign=0)
        label.set_margin_start(6)
        label.set_margin_end(6)
        list_item.set_child(label)

    @staticmethod
    def _bind_item(_factory, list_item):
        list_item.get_child().set_text(list_item.get_item().label)

    def get_selected_item(self):
        row = self.selection.get_selected_item()
        return row.label if row is not None else None
