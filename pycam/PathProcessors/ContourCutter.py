# -*- coding: utf-8 -*-
"""
$Id$

Copyright 2008-2010 Lode Leroy

This file is part of PyCAM.

PyCAM is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

PyCAM is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with PyCAM.  If not, see <http://www.gnu.org/licenses/>.
"""

from pycam.Geometry import *
from pycam.Geometry.PolygonExtractor import *

class ContourCutter:
    def __init__(self):
        self.paths = []
        self.curr_path = None
        self.scanline = None
        self.pe = None
        self.points = []

    def append(self, p):
        self.points.append(p)

    def new_direction(self, dir):
        if self.pe == None:
            self.pe = PolygonExtractor(PolygonExtractor.CONTOUR)

        self.pe.new_direction(dir)

    def end_direction(self):
        self.pe.end_direction()

    def new_scanline(self):
        self.pe.new_scanline()
        self.points = []

    def end_scanline(self):
        for i in range(1, len(self.points)-1):
            self.pe.append(self.points[i])
        self.pe.end_scanline()

    def finish(self):
        self.pe.finish()
        if self.pe.merge_path_list:
            self.paths = self.pe.merge_path_list
            for p in self.paths:
                p.append(p.points[0])
        else:
            if self.pe.hor_path_list:
                self.paths = self.pe.hor_path_list
            else:
                self.paths = self.pe.ver_path_list
            if self.paths:
                for p in self.paths:
                    p.append(p.points[0])
        self.pe = None

