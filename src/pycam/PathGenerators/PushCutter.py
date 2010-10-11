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
from pycam.Geometry.utils import epsilon, ceil
from pycam.Utils.threading import run_in_parallel
from pycam.Utils import ProgressCounter
import math


# We need to use a global function here - otherwise it does not work with
# the multiprocessing Pool.
def _process_one_line(p1, p2, depth, model, cutter, physics):
    if physics:
        points = get_free_paths_ode(physics, p1, p2, depth=depth)
    else:
        points = get_free_paths_triangles(model, cutter, p1, p2)
    return points


class PushCutter:

    def __init__(self, cutter, model, path_processor, physics=None):
        self.cutter = cutter
        self.model = model
        self.pa = path_processor
        self.physics = physics

    def GenerateToolPath(self, minx, maxx, miny, maxy, minz, maxz, dx, dy, dz,
            draw_callback=None):
        # calculate the number of steps
        # Sometimes there is a floating point accuracy issue: make sure
        # that only one layer is drawn, if maxz and minz are almost the same.
        if abs(maxz - minz) < epsilon:
            diff_z = 0
        else:
            diff_z = abs(maxz - minz)
        num_of_layers = 1 + ceil(diff_z / dz)
        z_step = diff_z / max(1, (num_of_layers - 1))

        lines_per_layer = 0
        if dx != 0:
            x_lines_per_layer = 1 + ceil(abs(maxx - minx) / dx)
            x_step = abs(maxx - minx) / max(1, (x_lines_per_layer - 1))
            lines_per_layer += x_lines_per_layer
        if dy != 0:
            y_lines_per_layer = 1 + ceil(abs(maxy - miny) / dy)
            y_step = abs(maxy - miny) / max(1, (y_lines_per_layer - 1))
            lines_per_layer += y_lines_per_layer

        progress_counter = ProgressCounter(num_of_layers * lines_per_layer,
                draw_callback)

        current_layer = 0

        z_steps = [(maxz - i * z_step) for i in range(num_of_layers)]
        for z in z_steps:
            # update the progress bar and check, if we should cancel the process
            if draw_callback and draw_callback(text="PushCutter: processing" \
                        + " layer %d/%d" % (current_layer + 1, num_of_layers)):
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
            depth = math.log(accuracy * abs(maxx - minx) / dx) / math.log(2)
            depth = max(ceil(depth), 4)
            depth = min(depth, max_depth)
            num_of_x_lines = 1 + ceil(abs(maxx - minx) / dx)
            x_step = abs(maxx - minx) / max(1, (num_of_x_lines - 1))
            x_steps = [minx + i * x_step for i in range(num_of_x_lines)]
            y_steps = [None] * num_of_x_lines
        elif dy != 0:
            depth = math.log(accuracy * abs(maxy - miny) / dy) / math.log(2)
            depth = max(ceil(depth), 4)
            depth = min(depth, max_depth)
            num_of_y_lines = 1 + ceil(abs(maxy - miny) / dy)
            y_step = abs(maxy - miny) / max(1, (num_of_y_lines - 1))
            y_steps = [miny + i * y_step for i in range(num_of_y_lines)]
            x_steps = [None] * num_of_y_lines
        else:
            # nothing to be done
            return

        args = []
        if dx > 0:
            depth = depth_
        for x, y in zip(x_steps, y_steps):
            if dx > 0:
                p1, p2 = Point(x, miny, z), Point(x, maxy, z)
            else:
                p1, p2 = Point(minx, y, z), Point(maxx, y, z)
            args.append((p1, p2, depth, self.model, self.cutter, self.physics))

        # ODE does not work with multi-threading
        disable_multiprocessing = not self.physics is None
        for points in run_in_parallel(_process_one_line, args,
                disable_multiprocessing=disable_multiprocessing):
            if points:
                self.pa.new_scanline()
                for p in points:
                    self.pa.append(p)
                if draw_callback:
                    draw_callback(tool_position=p, toolpath=self.pa.paths)
                self.pa.end_scanline()
            # update the progress counter
            if progress_counter and progress_counter.increment():
                # quit requested
                break

