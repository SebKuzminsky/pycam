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

from pycam.PathGenerators import get_free_paths_ode, get_free_paths_triangles
import pycam.PathProcessors
from pycam.Geometry.utils import ceil
from pycam.Utils.threading import run_in_parallel
from pycam.Utils import ProgressCounter
from pycam.Geometry.PointUtils import *
import pycam.Utils.log
import math


log = pycam.Utils.log.get_logger()


# We need to use a global function here - otherwise it does not work with
# the multiprocessing Pool.
def _process_one_line((p1, p2, depth, models, cutter, physics)):
    if physics:
        points = get_free_paths_ode(physics, p1, p2, depth=depth)
    else:
        points = get_free_paths_triangles(models, cutter, p1, p2)
    return points


class PushCutter(object):

    def __init__(self, path_processor, physics=None):
        if physics is None:
            log.debug("Starting PushCutter (without ODE)")
        else:
            log.debug("Starting PushCutter (with ODE)")
        self.pa = path_processor
        self.physics = physics
        # check if we use a PolygonExtractor
        self._use_polygon_extractor = hasattr(self.pa, "polygon_extractor")

    def GenerateToolPath(self, cutter, models, motion_grid, minz=None, maxz=None, draw_callback=None):
        # Transfer the grid (a generator) into a list of lists and count the
        # items.
        grid = []
        num_of_grid_positions = 0
        for layer in motion_grid:
            lines = []
            for line in layer:
                # convert the generator to a list
                lines.append(list(line))
            num_of_grid_positions += len(lines)
            grid.append(lines)

        num_of_layers = len(grid)

        progress_counter = ProgressCounter(num_of_grid_positions, draw_callback)

        current_layer = 0
        for layer_grid in grid:
            # update the progress bar and check, if we should cancel the process
            if draw_callback and draw_callback(text="PushCutter: processing" \
                        + " layer %d/%d" % (current_layer + 1, num_of_layers)):
                # cancel immediately
                break

            self.pa.new_direction(0)
            self.GenerateToolPathSlice(cutter, models, layer_grid, draw_callback,
                    progress_counter)
            self.pa.end_direction()
            self.pa.finish()

            current_layer += 1

        if self._use_polygon_extractor and (len(models) > 1):
            other_models = models[1:]
            # TODO: this is complicated and hacky :(
            # we don't use parallelism or ODE (for the sake of simplicity)
            final_pa = pycam.PathProcessors.SimpleCutter.SimpleCutter(
                    reverse=self.pa.reverse)
            for path in self.pa.paths:
                final_pa.new_scanline()
                pairs = []
                for index in range(len(path.points) - 1):
                    pairs.append((path.points[index], path.points[index + 1]))
                for p1, p2 in pairs:
                    free_points = get_free_paths_triangles(other_models,
                            cutter, p1, p2)
                    for point in free_points:
                        final_pa.append(point)
                final_pa.end_scanline()
            final_pa.finish()
            return final_pa.paths
        else:
            return self.pa.paths

    def GenerateToolPathSlice(self, cutter, models, layer_grid, draw_callback=None,
            progress_counter=None):
        # settings for calculation of depth
        accuracy = 20
        max_depth = 20
        min_depth = 4

        # the ContourCutter pathprocessor does not work with combined models
        if self._use_polygon_extractor:
            models = models[:1]
        else:
            models = models

        args = []
        for line in layer_grid:
            p1, p2 = line
            # calculate the required calculation depth (recursion)
            distance = pnorm(psub(p2, p1))
            # TODO: accessing cutter.radius here is slightly ugly
            depth = math.log(accuracy * distance / cutter.radius) / math.log(2)
            depth = min(max(ceil(depth), 4), max_depth)
            args.append((p1, p2, depth, models, cutter, self.physics))

        for points in run_in_parallel(_process_one_line, args,
                callback=progress_counter.update):
            if points:
                self.pa.new_scanline()
                for point in points:
                    self.pa.append(point)
                if draw_callback:
                    draw_callback(tool_position=points[-1], toolpath=self.pa.paths)
                self.pa.end_scanline()
            # update the progress counter
            if progress_counter and progress_counter.increment():
                # quit requested
                break

