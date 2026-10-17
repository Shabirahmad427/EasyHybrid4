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
import cairo

from util.easyplot.color_math import (
    interpolate_color,
    get_color,
    bilinear_interpolation,
    expand_array_size,
)


__all__ = [
    "interpolate_color",
    "get_color",
    "bilinear_interpolation",
    "expand_array_size",
    "ColorSquareBilinearInterpolation",
]



class ColorSquareBilinearInterpolation:
    def __init__(self, surface, x, y, size, c1, c2, c3, c4):
        self.ctx = cairo.Context(surface)
        self.x, self.y, self.size = x, y, size
        self.c1, self.c2, self.c3, self.c4 = c1, c2, c3, c4

    def draw(self):
        for i in range(self.size):
            for j in range(self.size):
                tx = j / (self.size - 1)
                ty = i / (self.size - 1)
                color = bilinear_interpolation(self.c1, self.c2, self.c3, self.c4, tx, ty)

                self.ctx.set_source_rgba(*[comp / 255.0 for comp in color])
                self.ctx.rectangle(self.x + j, self.y + i, 1, 1)
                self.ctx.fill()
