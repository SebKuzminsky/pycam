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

from pycam.Geometry.Point import Point
from pycam.PathGenerators import get_free_paths_ode, get_free_paths_triangles
from pycam.Utils import ProgressCounter
import math


class PushCutter:

    def __init__(self, cutter, model, path_processor, physics=None):
        self.cutter = cutter
        self.model = model
        self.pa = path_processor
        self.physics = physics

    def GenerateToolPath(self, minx, maxx, miny, maxy, minz, maxz, dx, dy, dz,
            draw_callback=None):
        # calculate the number of steps
        num_of_layers = 1 + int(math.ceil(abs(maxz - minz) / dz))
        z_step = abs(maxz - minz) / max(1, (num_of_layers - 1))

        lines_per_layer = 0
        if dx != 0:
            x_lines_per_layer = 1 + int(math.ceil(abs(maxx - minx) / dx))
            x_step = abs(maxx - minx) / max(1, (x_lines_per_layer - 1))
            lines_per_layer += x_lines_per_layer
        if dy != 0:
            y_lines_per_layer = 1 + int(math.ceil(abs(maxy - miny) / dy))
            y_step = abs(maxy - miny) / max(1, (y_lines_per_layer - 1))
            lines_per_layer += y_lines_per_layer

        progress_counter = ProgressCounter(num_of_layers * lines_per_layer,
                draw_callback)

        current_layer = 0

        z_steps = [(maxz - i * z_step) for i in range(num_of_layers)]
        for z in z_steps:
            # update the progress bar and check, if we should cancel the process
            if draw_callback and draw_callback(text="PushCutter: processing" \
                        + " layer %d/%d" % (current_layer, num_of_layers)):
                # cancel immediately
                break

            if dy > 0:
                self.pa.new_direction(0)
                self.GenerateToolPathSlice(minx, maxx, miny, maxy, z, 0, y_step,
                        draw_callback, progress_counter)
                self.pa.end_direction()
            if dx > 0:
                self.pa.new_direction(1)
                self.GenerateToolPathSlice(minx, maxx, miny, maxy, z, x_step, 0,
                        draw_callback, progress_counter)
                self.pa.end_direction()
            self.pa.finish()

            current_layer += 1

        return self.pa.paths

    def GenerateToolPathSlice(self, minx, maxx, miny, maxy, z, dx, dy,
            draw_callback=None, progress_counter=None):
        """ only dx or (exclusive!) dy may be bigger than zero
        """
        # max_deviation_x = dx/accuracy
        accuracy = 20
        max_depth = 20

        # calculate the required number of steps in each direction
        if dx > 0:
            depth_x = math.log(accuracy * abs(maxx - minx) / dx) / math.log(2)
            depth_x = max(int(math.ceil(depth_x)), 4)
            depth_x = min(depth_x, max_depth)
            num_of_x_lines = 1 + int(math.ceil(abs(maxx - minx) / dx))
            x_step = abs(maxx - minx) / max(1, (num_of_x_lines - 1))
            x_steps = [minx + i * x_step for i in range(num_of_x_lines)]
            y_steps = [None] * num_of_x_lines
        else:
            depth_y = math.log(accuracy * abs(maxy - miny) / dy) / math.log(2)
            depth_y = max(int(math.ceil(depth_y)), 4)
            depth_y = min(depth_y, max_depth)
            num_of_y_lines = 1 + int(math.ceil(abs(maxy - miny) / dy))
            y_step = abs(maxy - miny) / max(1, (num_of_y_lines - 1))
            y_steps = [miny + i * y_step for i in range(num_of_y_lines)]
            x_steps = [None] * num_of_y_lines

        for x, y in zip(x_steps, y_steps):
            self.pa.new_scanline()

            if dx > 0:
                p1, p2 = Point(x, miny, z), Point(x, maxy, z)
                if self.physics:
                    points = get_free_paths_ode(self.physics, p1, p2,
                            depth=depth_x)
                else:
                    points = get_free_paths_triangles(self.model, self.cutter,
                            p1, p2)
            else:
                p1, p2 = Point(minx, y, z), Point(maxx, y, z)
                if self.physics:
                    points = get_free_paths_ode(self.physics, p1, p2,
                            depth=depth_y)
                else:
                    points = get_free_paths_triangles(self.model, self.cutter,
                            p1, p2)

            if points:
                for p in points:
                    self.pa.append(p)
                self.cutter.moveto(p)
                if draw_callback:
                    draw_callback(tool_position=p)
            self.pa.end_scanline()

            # update the progress counter
            if not progress_counter is None:
                if progress_counter.increment():
                    # quit requested
                    break

