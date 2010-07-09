# -*- coding: utf-8 -*-
"""
$Id$

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

from pycam.Geometry import *

class ZigZagCutter:
    def __init__(self):
        self.paths = []
        self.curr_path = None
        self.scanline = None

    def append(self, p):
        curr_path = None
        if self.curr_path == None:
            curr_path = Path()
            self.curr_path = curr_path
        else:
            curr_path = self.curr_path
            self.curr_path = None

        curr_path.append(p)

        if self.curr_path == None:
            if (self.scanline % 2) == 0:
                self.curr_scanline.append(curr_path)
            else:
                curr_path.reverse()
                self.curr_scanline.insert(0, curr_path)

    def new_direction(self, dir):
        self.scanline = 0

    def end_direction(self):
        pass

    def new_scanline(self):
        self.scanline += 1
        self.curr_scanline = []

    def end_scanline(self):
        self.paths += self.curr_scanline
        self.curr_scanline = None

    def finish(self):
        pass
