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
from pycam.Geometry.utils import INFINITE, epsilon
from pycam.PathGenerators import drop_cutter_test, get_free_horizontal_paths_ode, get_free_horizontal_paths_triangles
import math


class ProgressCounter:

    def __init__(self, max_value):
        self.max_value = max_value
        self.current_value = 0

    def next(self):
        self.current_value += 1

    def get_percent(self):
        return 100.0 * self.current_value / self.max_value


class PushCutter:

    def __init__(self, cutter, model, pathextractor=None, physics=None):
        self.cutter = cutter
        self.model = model
        self.pa = pathextractor
        self.physics = physics

    def GenerateToolPath(self, minx, maxx, miny, maxy, minz, maxz, dx, dy, dz, draw_callback=None):
        # calculate the number of steps
        num_of_layers = 1 + int(math.ceil(abs(maxz - minz) / dz))
        dz = abs(maxz - minz) / (num_of_layers - 1)

        lines_per_layer = 0
        if dx != 0:
            x_lines_per_layer = 1 + int(math.ceil(abs(maxx - minx) / dx))
            dx = abs(maxx - minx) / (x_lines_per_layer - 1)
            lines_per_layer += x_lines_per_layer
        if dy != 0:
            y_lines_per_layer = 1 + int(math.ceil(abs(maxy - miny) / dy))
            dy = abs(maxy - miny) / (y_lines_per_layer - 1)
            lines_per_layer += y_lines_per_layer

        progress_counter = ProgressCounter(num_of_layers * lines_per_layer)

        z = maxz

        paths = []

        current_layer = 0

        z_steps = [(maxz - i * dz) for i in range(num_of_layers)]
        for z in z_steps:
            # update the progress bar and check, if we should cancel the process
            if draw_callback and draw_callback(text="PushCutter: processing" \
                        + " layer %d/%d" % (current_layer, num_of_layers)):
                # cancel immediately
                break

            if dy > 0:
                self.pa.new_direction(0)
                self.GenerateToolPathSlice(minx, maxx, miny, maxy, z, 0, dy,
                        draw_callback, progress_counter)
                self.pa.end_direction()
            if dx > 0:
                self.pa.new_direction(1)
                self.GenerateToolPathSlice(minx, maxx, miny, maxy, z, dx, 0,
                        draw_callback, progress_counter)
                self.pa.end_direction()
            self.pa.finish()

            if self.pa.paths:
                paths += self.pa.paths

            current_layer += 1

        return paths

    def GenerateToolPathSlice(self, minx, maxx, miny, maxy, z, dx, dy,
            draw_callback=None, progress_counter=None):
        """ only dx or (exclusive!) dy may be bigger than zero
        """
        # max_deviation_x = dx/accuracy
        accuracy = 20
        max_depth = 20

        # calculate the required number of steps in each direction
        if dx > 0:
            depth_x = math.log(accuracy * abs(maxx-minx) / dx) / math.log(2)
            depth_x = max(int(math.ceil(depth_x)), 4)
            depth_x = min(depth_x, max_depth)
            num_of_x_lines = 1 + int(math.ceil(abs(maxx - minx) / dx))
            x_step = abs(maxx - minx) / (num_of_x_lines - 1)
            x_steps = [minx + i * x_step for i in range(num_of_x_lines)]
            y_steps = [miny] * num_of_x_lines
        else:
            depth_y = math.log(accuracy * (maxy-miny) / dy) / math.log(2)
            depth_y = max(int(math.ceil(depth_y)), 4)
            depth_y = min(depth_y, max_depth)
            num_of_y_lines = 1 + int(math.ceil(abs(maxy - miny) / dy))
            y_step = abs(maxy - miny) / (num_of_y_lines - 1)
            y_steps = [miny + i * y_step for i in range(num_of_y_lines)]
            x_steps = [minx] * num_of_y_lines

        for x, y in zip(x_steps, y_steps):
            self.pa.new_scanline()

            if dx > 0:
                if self.physics:
                    points = get_free_horizontal_paths_ode(self.physics, x, x, miny, maxy, z, depth=depth_x)
                else:
                    points = get_free_horizontal_paths_triangles(self.model, self.cutter, x, x, miny, maxy, z)
            else:
                if self.physics:
                    points = get_free_horizontal_paths_ode(self.physics, minx, maxx, y, y, z, depth=depth_y)
                else:
                    points = get_free_horizontal_paths_triangles(self.model, self.cutter, minx, maxx, y, y, z)

            if points:
                for p in points:
                    self.pa.append(p)
                self.cutter.moveto(p)
                if draw_callback:
                    draw_callback(tool_position=p)
            self.pa.end_scanline()

            # update the progress counter
            if not progress_counter is None:
                progress_counter.next()
                if draw_callback:
                    draw_callback(percent=progress_counter.get_percent())

