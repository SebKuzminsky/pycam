# -*- coding: utf-8 -*-
"""
$Id$

Copyright 2010 Lars Kruse <devel@sumpfralle.de>
Copyright 2008 Lode Leroy

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

import pycam.PathProcessors
from pycam.Toolpath import simplify_toolpath
from pycam.Geometry.Path import Path


class PathAccumulator(pycam.PathProcessors.BasePathProcessor):
    def __init__(self, zigzag=False, reverse=False):
        super(PathAccumulator, self).__init__()
        self.curr_path = None
        self.zigzag = zigzag
        self.scanline = None
        self.reverse = reverse

    def append(self, point):
        if self.curr_path == None:
            self.curr_path = Path()
        if self.reverse:
            self.curr_path.insert(0, point)
        else:
            self.curr_path.append(point)

    def new_direction(self, direction):
        self.scanline = 0

    def new_scanline(self):
        self.scanline += 1
        if self.curr_path:
            print "ERROR: curr_path expected to be empty"
            self.curr_path = None

    def end_scanline(self):
        if self.curr_path:
            if self.zigzag and (self.scanline % 2 == 0):
                self.curr_path.reverse()
            simplify_toolpath(self.curr_path)
            if self.reverse:
                self.paths.insert(0, self.curr_path)
            else:
                self.paths.append(self.curr_path)
            self.curr_path = None

