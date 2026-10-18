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
from gi.repository import Gtk, Gdk
import cairo
import math


CATEGORY_LABELS = {
    "general": "General",
    "glycine": "Glycine",
    "proline": "Proline",
    "pre-proline": "Pre-proline",
}
CATEGORY_COLORS = {
    "general": (0.12, 0.34, 0.78),
    "glycine": (0.72, 0.18, 0.22),
    "proline": (0.12, 0.58, 0.34),
    "pre-proline": (0.65, 0.38, 0.08),
}


class RamachandranPlot(Gtk.DrawingArea):
    """GTK4 scatter plot for trajectory phi/psi results."""

    def __init__(self):
        super().__init__()
        self.data = []
        self.on_hover_callback = None
        self._hit_test_cache = []
        self.set_content_width(460)
        self.set_content_height(460)
        self.set_hexpand(True)
        self.set_vexpand(True)
        self.set_draw_func(self._on_draw)
        motion = Gtk.EventControllerMotion()
        motion.connect("motion", self._on_motion)
        motion.connect("leave", self._on_leave)
        self.add_controller(motion)

    def set_data(self, points):
        self.data = list(points)
        self.queue_draw()

    @staticmethod
    def _layout(width, height):
        left, right, top, bottom = 54, 18, 18, 48
        available_width = max(10, width - left - right)
        available_height = max(10, height - top - bottom)
        size = min(available_width, available_height)
        return (left + (available_width - size) / 2,
                top + (available_height - size) / 2, size)

    @staticmethod
    def _to_canvas(phi, psi, left, top, size):
        return (left + (phi + 180.0) * size / 360.0,
                top + size - (psi + 180.0) * size / 360.0)

    def render(self, cr, width, height, scale=1):
        """Draw the chart to any Cairo context, including export surfaces."""
        cr.save()
        cr.scale(scale, scale)
        cr.set_source_rgb(1, 1, 1)
        cr.paint()
        left, top, size = self._layout(width, height)
        right, bottom = left + size, top + size

        # Approximate allowed regions provide orientation, not a
        # statistical validation contour.
        cr.set_source_rgba(0.60, 0.82, 0.60, 0.35)
        for phi, psi, radius_x, radius_y in (
            (-63, -43, 42, 42), (-120, 130, 76, 56), (57, 40, 30, 30),
            (120, -130, 76, 56), (-60, 145, 22, 42),
        ):
            x, y = self._to_canvas(phi, psi, left, top, size)
            cr.save()
            cr.translate(x, y)
            cr.scale(radius_x * size / 360.0, radius_y * size / 360.0)
            cr.arc(0, 0, 1, 0, 2 * math.pi)
            cr.fill()
            cr.restore()

        # Grid and zero axes.
        for step in range(-180, 181, 30):
            x, _ = self._to_canvas(step, 0, left, top, size)
            _, y = self._to_canvas(0, step, left, top, size)
            cr.set_line_width(1)
            cr.set_source_rgb(0.86, 0.86, 0.86)
            cr.move_to(x, top); cr.line_to(x, bottom)
            cr.move_to(left, y); cr.line_to(right, y)
        cr.stroke()
        x0, y0 = self._to_canvas(0, 0, left, top, size)
        cr.set_source_rgb(0.25, 0.25, 0.25)
        cr.set_line_width(1.4)
        cr.move_to(x0, top); cr.line_to(x0, bottom)
        cr.move_to(left, y0); cr.line_to(right, y0)
        cr.stroke()
        cr.rectangle(left, top, size, size)
        cr.stroke()

        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(10)
        cr.set_source_rgb(0.15, 0.15, 0.15)
        for tick in range(-180, 181, 60):
            x, _ = self._to_canvas(tick, 0, left, top, size)
            _, y = self._to_canvas(0, tick, left, top, size)
            label = str(tick)
            extents = cr.text_extents(label)
            cr.move_to(x - extents.width / 2, bottom + 15)
            cr.show_text(label)
            cr.move_to(left - 32, y + extents.height / 2)
            cr.show_text(label)

        cr.set_font_size(12)
        label = "φ (degrees)"
        extents = cr.text_extents(label)
        cr.move_to(left + (size - extents.width) / 2, height - 5)
        cr.show_text(label)
        cr.save()
        cr.translate(14, top + size / 2)
        cr.rotate(-math.pi / 2)
        cr.move_to(-40, 0)
        cr.show_text("ψ (degrees)")
        cr.restore()

        by_category = {}
        for point in self.data:
            category = point.get("category", "general")
            by_category.setdefault(category, []).append(point)
        self._hit_test_cache = []
        for category, points in by_category.items():
            cr.set_source_rgb(*CATEGORY_COLORS.get(category, CATEGORY_COLORS["general"]))
            for point in points:
                x, y = self._to_canvas(point["phi"], point["psi"], left, top, size)
                cr.arc(x, y, 3.2, 0, 2 * math.pi)
                cr.fill()
                self._hit_test_cache.append((x, y, point))

        self._draw_legend(cr, by_category, left, bottom, width)
        cr.restore()

    def _on_draw(self, _widget, cr, width, height):
        self.render(cr, width, height)

    def _draw_legend(self, cr, by_category, left, bottom, width):
        present = [name for name in CATEGORY_LABELS if by_category.get(name)]
        if not present:
            return
        row_height = 15
        box_width = 112
        box_height = 8 + len(present) * row_height
        x = left + max(0, width - left - box_width - 22)
        y = bottom - box_height - 8
        cr.set_source_rgba(1, 1, 1, 0.86)
        cr.rectangle(x, y, box_width, box_height)
        cr.fill_preserve()
        cr.set_source_rgb(0.65, 0.65, 0.65)
        cr.stroke()
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(10)
        for index, name in enumerate(present):
            cy = y + 8 + index * row_height + 5
            cr.set_source_rgb(*CATEGORY_COLORS.get(name, CATEGORY_COLORS["general"]))
            cr.arc(x + 10, cy, 3.5, 0, 2 * math.pi)
            cr.fill()
            cr.set_source_rgb(0.15, 0.15, 0.15)
            cr.move_to(x + 20, cy + 3)
            cr.show_text(CATEGORY_LABELS[name])

    def _on_motion(self, _controller, x, y):
        nearest = None
        best_distance = 8.0 ** 2
        for point_x, point_y, point in self._hit_test_cache:
            distance = (point_x - x) ** 2 + (point_y - y) ** 2
            if distance <= best_distance:
                nearest, best_distance = point, distance
        if self.on_hover_callback is not None:
            self.on_hover_callback(nearest)

    def _on_leave(self, _controller):
        if self.on_hover_callback is not None:
            self.on_hover_callback(None)

class RamachandranWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Diagrama de Ramachandran")
        self.set_default_size(500, 500)

        self.drawing_area = Gtk.DrawingArea()
        self.drawing_area.set_draw_func(self.on_draw)
        self.drawing_area.set_margin_top(10)
        self.drawing_area.set_margin_bottom(10)
        self.drawing_area.set_margin_start(10)
        self.drawing_area.set_margin_end(10)
        self.set_child(self.drawing_area)
        self.present()
        
    def to_canvas_coords(self, phi, psi, origin_x, origin_y, size):
        """Converte coordenadas phi, psi (-180 a 180) para canvas (x, y)"""
        x = origin_x + ((phi + 180) / 360) * size
        y = origin_y + size - ((psi + 180) / 360) * size
        return x, y

    def draw_region(self, cr, region_points, origin_x, origin_y, size, color):
        cr.set_source_rgba(*color)
        cr.set_line_width(1.0)
        first = True
        for phi, psi in region_points:
            x, y = self.to_canvas_coords(phi, psi, origin_x, origin_y, size)
            if first:
                cr.move_to(x, y)
                first = False
            else:
                cr.line_to(x, y)
        cr.close_path()
        cr.fill()

    def on_draw(self, widget, cr, width, height):
        width = widget.get_width()
        height = widget.get_height()
        cr.set_source_rgb(1, 1, 1)  # fundo branco
        cr.paint()

        # Área de desenho
        margin = 40
        size = min(width, height) - 2 * margin
        origin_x = margin
        origin_y = margin
        step = size / 12  # 30° por passo

        # Grade
        cr.set_line_width(1)
        cr.set_source_rgb(0.8, 0.8, 0.8)
        for i in range(13):
            x = origin_x + i * step
            y = origin_y + i * step
            cr.move_to(x, origin_y)
            cr.line_to(x, origin_y + size)
            cr.move_to(origin_x, y)
            cr.line_to(origin_x + size, y)
        cr.stroke()

        # Eixos φ = 0 e ψ = 0
        cr.set_source_rgb(0, 0, 0)
        cr.set_line_width(2)
        cr.move_to(origin_x + size / 2, origin_y)
        cr.line_to(origin_x + size / 2, origin_y + size)
        cr.move_to(origin_x, origin_y + size / 2)
        cr.line_to(origin_x + size, origin_y + size / 2)
        cr.stroke()

        # Rótulos
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(10)
        for i in range(13):
            label = str(-180 + i * 30)
            x = origin_x + i * step
            y = origin_y + size + 15
            cr.move_to(x - 10, y)
            cr.show_text(label)
            cr.move_to(origin_x - 30, origin_y + size - i * step + 3)
            cr.show_text(label)

        # Regiões permitidas (dados aproximados)
        alpha_region = [
            (-80, -60), (-70, -40), (-60, -30), (-50, -40), (-40, -60),
            (-50, -70), (-60, -80), (-70, -70), (-80, -60),# ( 100,  111), ( 150,  151)
        ]
        beta_region = [
            (-160, 120), (-150, 130), (-140, 140), (-130, 135),
            (-120, 120), (-130, 110), (-140, 110), (-150, 115), (-160, 120)
        ]
        l_alpha_region = [
            (50, 30), (60, 40), (70, 30), (70, 20), (60, 10), (50, 20), (50, 30)
        ]

        self.draw_region(cr, alpha_region, origin_x, origin_y, size, (0.5, 1.0, 0.5, 0.5))  # verde
        self.draw_region(cr, beta_region, origin_x, origin_y, size, (0.5, 0.5, 1.0, 0.5))   # azul
        self.draw_region(cr, l_alpha_region, origin_x, origin_y, size, (1.0, 0.5, 0.5, 0.5))  # vermelho claro

        # Pontos de exemplo
        #pontos = [(-60, -45), (60, 120), (-135, 135), (0, 0)]
        pontos = [ ]
        cr.set_source_rgb(1, 0, 0)
        for phi, psi in pontos:
            x, y = self.to_canvas_coords(phi, psi, origin_x, origin_y, size)
            cr.arc(x, y, 4, 0, 2 * math.pi)
            cr.fill()
