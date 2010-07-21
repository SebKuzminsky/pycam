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
from pycam.Utils import ProgressCounter
import pycam.Utils.log
import math

log = pycam.Utils.log.get_logger()


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
            return (value > self.min - tolerance) \
                    and (value < self.max + tolerance)

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

    def __init__(self, cutter, model, path_processor, physics=None,
            safety_height=INFINITE):
        self.cutter = cutter
        self.model = model
        self.pa = path_processor
        self.physics = physics
        self.safety_height = safety_height
        # remember if we already reported an invalid boundary
        self._boundary_warning_already_shown = False

    def GenerateToolPath(self, minx, maxx, miny, maxy, minz, maxz, d0, d1,
            direction, draw_callback=None):
        quit_requested = False
        # determine step size
        num_of_x_lines = 1 + int(math.ceil(abs(maxx - minx) / d0))
        num_of_y_lines = 1 + int(math.ceil(abs(maxy - miny) / d1))
        x_step = abs(maxx - minx) / max(1, (num_of_x_lines - 1))
        y_step = abs(maxy - miny) / max(1, (num_of_y_lines - 1))
        x_steps = [(minx + i * x_step) for i in range(num_of_x_lines)]
        y_steps = [(miny + i * y_step) for i in range(num_of_y_lines)]

        # map the scales according to the order of direction
        grid = []
        if direction == 0:
            # first x, then y
            for x in x_steps:
                grid.append(zip([x] * (len(y_steps) + 1), y_steps))
            dim_attrs = ["x", "y"]
        else:
            # first y, then x
            for y in y_steps:
                grid.append(zip(x_steps, [y] * (len(x_steps) + 1)))
            dim_attrs = ["y", "x"]

        num_of_lines = len(grid) + 1
        num_of_grid_positions = num_of_x_lines * num_of_y_lines
        progress_counter = ProgressCounter(num_of_grid_positions, draw_callback)
        current_line = 0

        self.pa.new_direction(direction)

        self._boundary_warning_already_shown = False

        for one_grid_line in grid:
            self.pa.new_scanline()
            # for now only used for triangular collision detection
            last_position = None

            if draw_callback and draw_callback(text="DropCutter: processing " \
                        + "line %d/%d" % (current_line, num_of_lines),
                        percent=(100.0 * current_line / num_of_lines)):
                # cancel requested
                quit_requested = True
                break

            for x, y in one_grid_line:
                if self.physics:
                    points = get_max_height_ode(self.physics, x, y, minz, maxz,
                            order=dim_attrs[:])
                else:
                    points = get_max_height_triangles(self.model, self.cutter,
                            x, y, minz, maxz, order=dim_attrs[:],
                            last_pos=last_position)

                if points:
                    for p in points:
                        self.pa.append(p)
                else:
                    p = Point(x, y, self.safety_height)
                    self.pa.append(p)
                    if not self._boundary_warning_already_shown:
                        log.warn("DropCutter: exceed the height of the " \
                                + "boundary box: using a safe height instead." \
                                + " This warning is reported only once.")
                    self._boundary_warning_already_shown = True
                self.cutter.moveto(p)
                # "draw_callback" returns true, if the user requested to quit
                # via the GUI.
                # The progress counter may return True, if cancel was requested.
                if (draw_callback and draw_callback(tool_position=p)) \
                        or (progress_counter.increment()):
                    quit_requested = True
                    break

            self.pa.end_scanline()

            # update progress
            current_line += 1

            if quit_requested:
                break

        self.pa.end_direction()

        self.pa.finish()
        return self.pa.paths

