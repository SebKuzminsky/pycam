# -*- coding: utf-8 -*-
"""
$Id$

Copyright 2010 Lars Kruse <devel@sumpfralle.de>
Copyright 2008-2009 Lode Leroy

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

from pycam.Geometry import Point
from pycam.Geometry.utils import INFINITE
from pycam.PathGenerators import get_max_height_triangles, get_max_height_ode
import math
import sys


class Dimension:
    def __init__(self, start, end):
        self.start = float(start)
        self.end = float(end)
        self.min = float(min(start, end))
        self.max = float(max(start, end))
        self.downward = start > end
        self.value = 0.0

    def check_bounds(self, value=None, tolerance=None):
        if value is None:
            value = self.value
        if tolerance is None:
            return (value >= self.min) and (value <= self.max)
        else:
            return (value > self.min - tolerance) and (value < self.max + tolerance)

    def shift(self, distance):
        if self.downward:
            self.value -= distance
        else:
            self.value += distance

    def set(self, value):
        self.value = float(value)

    def get(self):
        return self.value


class DropCutter:

    def __init__(self, cutter, model, path_processor, physics=None, safety_height=INFINITE):
        self.cutter = cutter
        self.model = model
        self.pa = path_processor
        self.physics = physics
        self.safety_height = safety_height
        # remember if we already reported an invalid boundary
        self._boundary_warning_already_shown = False

    def GenerateToolPath(self, minx, maxx, miny, maxy, minz, maxz, d0, d1, direction, draw_callback=None):
        dim_x = Dimension(minx, maxx)
        dim_y = Dimension(miny, maxy)
        dims = [None, None, None]
        # map the scales according to the order of direction
        if direction == 0:
            x, y = 0, 1
            dim_attrs = ["x", "y"]
        else:
            y, x = 0, 1
            dim_attrs = ["y", "x"]
        # order of the "dims" array: first dimension, second dimension
        dims[x] = dim_x
        dims[y] = dim_y

        z = maxz
        self.pa.new_direction(direction)
        dims[1].set(dims[1].start)

        finished_plane = False
        self._boundary_warning_already_shown = False
        last_outer_loop = False

        num_of_lines = math.ceil((dims[1].max - dims[1].min) / d1)
        current_line = 0

        while not finished_plane:
            last_inner_loop = False
            finished_line = False
            dims[0].set(dims[0].start)
            self.pa.new_scanline()
            last_position = None

            if draw_callback and draw_callback(text="DropCutter: processing line %d/%d" \
                        % (current_line, num_of_lines),
                        percent=(100.0 * current_line / num_of_lines)):
                # cancel requested
                finished_plane = True

            while not finished_line:
                if self.physics:
                    points = get_max_height_ode(self.physics, dims[x].get(),
                            dims[y].get(), minz, maxz, order=dim_attrs[:])
                else:
                    points = get_max_height_triangles(self.model, self.cutter,
                            dims[x].get(), dims[y].get(), minz, maxz,
                            order=dim_attrs[:], last_pos=last_position)

                if points:
                    for p in points:
                        self.pa.append(p)
                else:
                    p = Point(dims[x].get(), dims[y].get(), self.safety_height)
                    self.pa.append(p)
                    if not self._boundary_warning_already_shown:
                        print >>sys.stderr, "WARNING: DropCutter exceed the height" \
                                + " of the boundary box: using a safe height " \
                                + "instead. This warning is reported only once."
                    self._boundary_warning_already_shown = True
                self.cutter.moveto(p)
                # "draw_callback" returns true, if the user requested quitting via the GUI
                if draw_callback and draw_callback(tool_position=p):
                    finished_line = True

                dims[0].shift(d0)

                # make sure, that the we also handle the outmost border of the bounding box
                if dims[0].check_bounds(tolerance=d0):
                    if not dims[0].check_bounds() and not last_inner_loop:
                        dims[0].set(dims[0].end)
                        last_inner_loop = True
                else:
                    finished_line = True

            self.pa.end_scanline()
            dims[1].shift(d1)

            # make sure, that the we also handle the outmost border of the bounding box
            if dims[1].check_bounds(tolerance=d1):
                if not dims[1].check_bounds() and not last_outer_loop:
                    dims[1].set(dims[1].end)
                    last_outer_loop = True
            else:
                finished_plane = True

            # update progress
            current_line += 1

        self.pa.end_direction()

        self.pa.finish()
        return self.pa.paths

