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
        num_of_layers = 1 + math.ceil((maxz - minz) / dz)
        lines_per_layer = 0

        if dx != 0:
            lines_per_layer += 1 + math.ceil((maxx - minx) / dx)
            self.pa.dx = dx
        else:
            self.pa.dx = dy

        if dy != 0:
            lines_per_layer += 1 + math.ceil((maxy - miny) / dy)
            self.pa.dy = dy
        else:
            self.pa.dy = dx

        progress_counter = ProgressCounter(num_of_layers * lines_per_layer)

        z = maxz

        paths = []

        current_layer = 0

        if self.physics is None:
            GenerateToolPathSlice = self.GenerateToolPathSlice_triangles
        else:
            GenerateToolPathSlice = self.GenerateToolPathSlice_ode

        last_loop = False
        while z >= minz:
            # update the progress bar and check, if we should cancel the process
            if draw_callback and draw_callback(text="PushCutter: processing" \
                        + " layer %d/%d" % (current_layer, num_of_layers)):
                # cancel immediately
                z = minz - 1

            if dy > 0:
                self.pa.new_direction(0)
                GenerateToolPathSlice(minx, maxx, miny, maxy, z, 0, dy,
                        draw_callback, progress_counter)
                self.pa.end_direction()
            if dx > 0:
                self.pa.new_direction(1)
                GenerateToolPathSlice(minx, maxx, miny, maxy, z, dx, 0,
                        draw_callback, progress_counter)
                self.pa.end_direction()
            self.pa.finish()

            if self.pa.paths:
                paths += self.pa.paths
            z -= dz

            if (z < minz) and not last_loop:
                # never skip the outermost bounding limit - reduce the step size if required
                z = minz
                # stop after the next loop
                last_loop = True

            current_layer += 1

        return paths

    def GenerateToolPathSlice_ode(self, minx, maxx, miny, maxy, z, dx, dy,
            draw_callback=None, progress_counter=None):
        """ only dx or (exclusive!) dy may be bigger than zero
        """
        # max_deviation_x = dx/accuracy
        accuracy = 20
        max_depth = 20
        x = minx
        y = miny

        # calculate the required number of steps in each direction
        if dx > 0:
            depth_x = math.log(accuracy * (maxx-minx) / dx) / math.log(2)
            depth_x = max(math.ceil(int(depth_x)), 4)
            depth_x = min(depth_x, max_depth)
        else:
            depth_y = math.log(accuracy * (maxy-miny) / dy) / math.log(2)
            depth_y = max(math.ceil(int(depth_y)), 4)
            depth_y = min(depth_y, max_depth)

        last_loop = False
        while (x <= maxx) and (y <= maxy):
            points = []
            self.pa.new_scanline()

            if dx > 0:
                points = get_free_horizontal_paths_ode(self.physics, x, x, miny, maxy, z, depth=depth_x)
            else:
                points = get_free_horizontal_paths_ode(self.physics, minx, maxx, y, y, z, depth=depth_y)

            for p in points:
                self.pa.append(p)
            if points:
                self.cutter.moveto(points[-1])
                if draw_callback:
                    draw_callback(tool_position=points[-1])
            self.pa.end_scanline()

            if dx > 0:
                x += dx
                if (x > maxx) and not last_loop:
                    last_loop = True
                    x = maxx
            else:
                y += dy
                if (y > maxy) and not last_loop:
                    last_loop = True
                    y = maxy

            # update the progress counter
            if not progress_counter is None:
                progress_counter.next()
                if draw_callback:
                    draw_callback(percent=progress_counter.get_percent())


    def GenerateToolPathSlice_triangles(self, minx, maxx, miny, maxy, z, dx, dy,
            draw_callback=None, progress_counter=None):

        x = minx
        y = miny

        last_loop = False
        while x <= maxx and y <= maxy:
            self.pa.new_scanline()

            if dx > 0:
                points = get_free_horizontal_paths_triangles(self.model, self.cutter, x, x, miny, maxy, z)
            else:
                points = get_free_horizontal_paths_triangles(self.model, self.cutter, minx, maxx, y, y, z)
             
            if points:
                for p in points:
                    self.pa.append(p)
                self.cutter.moveto(p)
                if draw_callback:
                    draw_callback(tool_position=p)

            if dx != 0:
                x += dx
                # never skip the outermost bounding limit - reduce the step size if required
                if (x > maxx) and not last_loop:
                    x = maxx
                    last_loop = True
            else:
                x = minx
            if dy != 0:
                y += dy
                # never skip the outermost bounding limit - reduce the step size if required
                if (y > maxy) and not last_loop:
                    y = maxy
                    last_loop = True
            else:
                y = miny

            self.pa.end_scanline()

            # update the progress counter
            if not progress_counter is None:
                progress_counter.next()
                if draw_callback:
                    draw_callback(percent=progress_counter.get_percent())

