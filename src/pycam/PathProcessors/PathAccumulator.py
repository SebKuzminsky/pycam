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

from pycam.Geometry.Path import Path

def _check_colinearity(p1, p2, p3):
    v1 = p2.sub(p1)
    v2 = p3.sub(p2)
    v1.normalize()
    v2.normalize()
    # compare if the normalized distances between p1-p2 and p2-p3 are equal
    return v1 == v2

class PathAccumulator:
    def __init__(self, zigzag=False):
        self.paths = []
        self.curr_path = None
        self.zigzag = zigzag
        self.scanline = None

    def append(self, p):
        if self.curr_path == None:
            self.curr_path = Path()
        if (len(self.curr_path.points) >= 2) and \
                (_check_colinearity(self.curr_path.points[-2],
                self.curr_path.points[-1], p)):
            # remove the previous point since it is in line with its
            # predecessor and the new point
            self.curr_path.points.pop()
        self.curr_path.append(p)

    def new_direction(self, direction):
        self.scanline = 0

    def end_direction(self):
        pass

    def new_scanline(self):
        self.scanline += 1
        if self.curr_path:
            print "ERROR: curr_path expected to be empty"
            self.curr_path = None

    def end_scanline(self):
        if self.curr_path:
            if self.zigzag and (self.scanline%2 == 0):
                self.curr_path.reverse()
            self.paths.append(self.curr_path)
            self.curr_path = None

    def finish(self):
        pass
