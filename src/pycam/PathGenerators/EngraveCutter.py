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

import pycam.PathProcessors.PathAccumulator
from pycam.Geometry.Point import Point
from pycam.Geometry.utils import INFINITE, ceil
from pycam.PathGenerators import get_max_height_triangles, get_max_height_ode, \
        get_free_paths_ode, get_free_paths_triangles
from pycam.Utils import ProgressCounter
import pycam.Utils.log

log = pycam.Utils.log.get_logger()


class EngraveCutter:

    def __init__(self, cutter, model, contour_model, path_processor,
            physics=None, safety_height=INFINITE):
        self.cutter = cutter
        self.model = model
        self.contour_model = contour_model
        self.pa_push = path_processor
        # We use a separated path processor for the last "drop" layer.
        # This path processor does not need to be configurable.
        self.pa_drop = pycam.PathProcessors.PathAccumulator()
        self.physics = physics
        self.safety_height = safety_height
        self._boundary_warning_already_shown = False

    def GenerateToolPath(self, minz, maxz, horiz_step, dz, draw_callback=None):
        quit_requested = False
        # calculate the number of steps
        num_of_layers = 1 + ceil(abs(maxz - minz) / dz)
        if num_of_layers > 1:
            z_step = abs(maxz - minz) / (num_of_layers - 1)
            z_steps = [(maxz - i * z_step) for i in range(num_of_layers)]
            # The top layer is treated as the current surface - thus it does not
            # require engraving.
            z_steps = z_steps[1:]
        else:
            z_steps = [minz]
        num_of_layers = len(z_steps)

        current_layer = 0
        num_of_lines = self.contour_model.get_num_of_lines()
        progress_counter = ProgressCounter(len(z_steps) * num_of_lines,
                draw_callback)

        line_groups = self.contour_model.get_polygons()
        # Sort the polygons according to their directions (first inside, then
        # outside. Smaller polygons are processed first.
        # This reduces the problem of break-away pieces.
        def polygon_priority(poly1, poly2):
            """ polygon priority comparison: first holes, then outlines
            (sorted by ascending area size)
            TODO: ordering according to the locations and groups of polygons
            would be even better.
            """
            area1 = poly1.get_area()
            area2 = poly2.get_area()
            if (area1 < 0) and (area2 > 0):
                return -1
            elif (area2 < 0) and (area1 > 0):
                return 1
            else:
                return cmp(abs(area1), abs(area2))
        line_groups.sort(cmp=polygon_priority)

        # push slices for all layers above ground
        for z in z_steps[:-1]:
            # update the progress bar and check, if we should cancel the process
            if draw_callback and draw_callback(text="Engrave: processing" \
                        + " layer %d/%d" % (current_layer, num_of_layers)):
                # cancel immediately
                break

            for line_group in line_groups:
                for line in line_group.get_lines():
                    self.GenerateToolPathLinePush(self.pa_push, line, z,
                            draw_callback)
                    if progress_counter.increment():
                        # cancel requested
                        quit_requested = True
                        # finish the current path
                        self.pa_push.finish()
                        break
            self.pa_push.finish()

            # break the outer loop if requested
            if quit_requested:
                break

            current_layer += 1


        if quit_requested:
            return self.pa_push.paths

        if draw_callback:
            draw_callback(text="Engrave: processing layer %d/%d" \
                    % (current_layer, num_of_layers))

        # process the final layer with a drop cutter
        for line_group in self.contour_model.get_polygons():
            self.pa_drop.new_direction(0)
            self.pa_drop.new_scanline()
            for line in line_group.get_lines():
                self.GenerateToolPathLineDrop(self.pa_drop, line, minz, maxz,
                        horiz_step, draw_callback=draw_callback)
                if progress_counter.increment():
                    # quit requested
                    quit_requested = True
                    break
            self.pa_drop.end_scanline()
            self.pa_drop.end_direction()
            # break the outer loop if requested
            if quit_requested:
                break
        self.pa_drop.finish()
        
        return self.pa_push.paths + self.pa_drop.paths

    def GenerateToolPathLinePush(self, pa, line, z, draw_callback=None):
        p1 = Point(line.p1.x, line.p1.y, z)
        p2 = Point(line.p2.x, line.p2.y, z)
        # no model -> no possible obstacles
        # model is completely below z (e.g. support bridges) -> no obstacles
        if not self.model or (self.model.maxz < z):
            points = [p1, p2]
        elif self.physics:
            points = get_free_paths_ode(self.physics, p1, p2)
        else:
            points = get_free_paths_triangles(self.model, self.cutter, p1, p2)
        if points:
            for p in points:
                pa.append(p)
            self.cutter.moveto(p)
            if draw_callback:
                draw_callback(tool_position=p, toolpath=pa.paths)


    def GenerateToolPathLineDrop(self, pa, line, minz, maxz, horiz_step,
            draw_callback=None):
        pa.new_direction(0)
        pa.new_scanline()
        p1 = Point(line.p1.x, line.p1.y, minz)
        p2 = Point(line.p2.x, line.p2.y, minz)
        distance = line.len
        # we want to have at least five steps each
        num_of_steps = max(5, 1 + ceil(distance / horiz_step))
        # steps may be negative
        x_step = (p2.x - p1.x) / (num_of_steps - 1)
        y_step = (p2.y - p1.y) / (num_of_steps - 1)
        x_steps = [(p1.x + i * x_step) for i in range(num_of_steps)]
        y_steps = [(p1.y + i * y_step) for i in range(num_of_steps)]
        step_coords = zip(x_steps, y_steps)

        last_position = None

        for x, y in step_coords:
            if not self.model:
                # no obstacle -> minimum height
                points = [Point(x, y, minz)]
            elif self.physics:
                points = get_max_height_ode(self.physics, x, y, minz, maxz)
            else:
                points = get_max_height_triangles(self.model, self.cutter,
                        x, y, minz, maxz, last_pos=last_position)

            if points:
                for p in points:
                    pa.append(p)
            else:
                p = Point(x, y, self.safety_height)
                pa.append(p)
                if not self._boundary_warning_already_shown:
                    log.warn("EngraveCutter: exceed the height " \
                            + "of the boundary box: using a safe height " \
                            + "instead. This warning is reported only once.")
                self._boundary_warning_already_shown = True
            self.cutter.moveto(p)
            # "draw_callback" returns true, if the user requested quitting via
            # the GUI.
            if draw_callback \
                    and draw_callback(tool_position=p, toolpath=pa.paths):
                break
        pa.end_scanline()
        pa.end_direction()

