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
from pycam.Geometry.Point import Point, Vector
from pycam.Geometry.Line import Line
from pycam.Geometry.Plane import Plane
from pycam.Geometry.utils import ceil
from pycam.PathGenerators import get_max_height_dynamic, get_free_paths_ode, \
        get_free_paths_triangles
from pycam.Utils import ProgressCounter
import pycam.Utils.log

log = pycam.Utils.log.get_logger()


class EngraveCutter:

    def __init__(self, cutter, trimesh_models, contour_model, path_processor,
            clockwise=False, physics=None):
        self.cutter = cutter
        self.models = trimesh_models
        # combine the models (if there is more than one)
        if self.models:
            self.combined_model = self.models[0]
            for model in self.models[1:]:
                self.combined_model += model
        else:
            self.combined_model = []
        if clockwise:
            self.contour_model = contour_model.get_reversed()
        else:
            self.contour_model = contour_model
        self.pa_push = path_processor
        # We use a separated path processor for the last "drop" layer.
        # This path processor does not need to be configurable.
        self.pa_drop = pycam.PathProcessors.PathAccumulator.PathAccumulator(
                reverse=self.pa_push.reverse)
        self.physics = physics

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
        # push slices for all layers above ground
        if maxz == minz:
            # only one layer - use PushCutter instead of DropCutter
            # put "last_z" clearly above the model plane
            last_z = maxz + 1
            push_steps = z_steps
            drop_steps = []
        else:
            # multiple layers
            last_z = maxz
            push_steps = z_steps[:-1]
            drop_steps = [z_steps[-1]]

        for z in push_steps:
            # update the progress bar and check, if we should cancel the process
            if draw_callback and draw_callback(text="Engrave: processing" \
                        + " layer %d/%d" % (current_layer, num_of_layers)):
                # cancel immediately
                break
            for line_group in line_groups:
                for line in line_group.get_lines():
                    self.GenerateToolPathLinePush(self.pa_push, line, z, last_z,
                            draw_callback=draw_callback)
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
            last_z = z

        if quit_requested:
            return self.pa_push.paths
        if draw_callback:
            draw_callback(text="Engrave: processing layer %d/%d" \
                    % (current_layer + 1, num_of_layers))

        # Sort the polygons according to their directions (first inside, then
        # outside.
        # This reduces the problem of break-away pieces.
        # We do the sorting just before the final layer (breakage does not
        # happen before).
        def polygon_priority(poly1, poly2):
            """ polygon priority comparison: first holes and open polygons, then
            outlines (roughly sorted by ascending area size)
            TODO: ordering according to the locations and groups of polygons
            would be even better.
            """
            area1 = poly1.get_area()
            area2 = poly2.get_area()
            if (area1 <= 0) and (area2 > 0):
                return -1
            elif (area2 <= 0) and (area1 > 0):
                return 1
            else:
                # do a "relaxed" sorting by size
                if abs(area1) < 2 * abs(area2):
                    return -1
                elif abs(area2) < 2 * abs(area1):
                    return 1
                else:
                    return 0
        line_groups.sort(cmp=polygon_priority)

        for z in drop_steps:
            # process the final layer with a drop cutter
            for line_group in self.contour_model.get_polygons():
                self.pa_drop.new_direction(0)
                self.pa_drop.new_scanline()
                for line in line_group.get_lines():
                    self.GenerateToolPathLineDrop(self.pa_drop, line, z, maxz,
                            horiz_step, last_z, draw_callback=draw_callback)
                    if progress_counter.increment():
                        # quit requested
                        quit_requested = True
                        break
                self.pa_drop.end_scanline()
                self.pa_drop.end_direction()
                # break the outer loop if requested
                if quit_requested:
                    break
            last_z = z
        self.pa_drop.finish()
        
        return self.pa_push.paths + self.pa_drop.paths

    def GenerateToolPathLinePush(self, pa, line, z, previous_z,
            draw_callback=None):
        if previous_z <= line.minz:
            # the line is completely above the previous level
            pass
        elif line.minz < z < line.maxz:
            # Split the line at the point at z level and do the calculation
            # for both point pairs.
            factor = (z - line.p1.z) / (line.p2.z - line.p1.z)
            plane_point = line.p1.add(line.vector.mul(factor))
            self.GenerateToolPathLinePush(pa, Line(line.p1, plane_point), z,
                    previous_z, draw_callback=draw_callback)
            self.GenerateToolPathLinePush(pa, Line(plane_point, line.p2), z,
                    previous_z, draw_callback=draw_callback)
        elif line.minz < previous_z < line.maxz:
            plane = Plane(Point(0, 0, previous_z), Vector(0, 0, 1))
            cp = plane.intersect_point(line.dir, line.p1)[0]
            # we can be sure that there is an intersection
            if line.p1.z > previous_z:
                p1, p2 = cp, line.p2
            else:
                p1, p2 = line.p1, cp
            self.GenerateToolPathLinePush(pa, Line(p1, p2), z, previous_z,
                    draw_callback=draw_callback)
        else:
            if line.maxz <= z:
                # the line is completely below z
                p1 = Point(line.p1.x, line.p1.y, z)
                p2 = Point(line.p2.x, line.p2.y, z)
            elif line.minz >= z:
                p1 = line.p1
                p2 = line.p2
            else:
                log.warn("Unexpected condition EC_GTPLP: %s / %s / %s / %s" % \
                        (line.p1, line.p2, z, previous_z))
                return
            # no model -> no possible obstacles
            # model is completely below z (e.g. support bridges) -> no obstacles
            relevant_models = [m for m in self.models if m.maxz >= z]
            if not relevant_models:
                points = [p1, p2]
            elif self.physics:
                points = get_free_paths_ode(self.physics, p1, p2)
            else:
                points = get_free_paths_triangles(relevant_models, self.cutter,
                        p1, p2)
            if points:
                for point in points:
                    pa.append(point)
                if draw_callback:
                    draw_callback(tool_position=points[-1], toolpath=pa.paths)


    def GenerateToolPathLineDrop(self, pa, line, minz, maxz, horiz_step,
            previous_z, draw_callback=None):
        if line.minz >= previous_z:
            # the line is not below maxz -> nothing to be done
            return
        pa.new_direction(0)
        pa.new_scanline()
        if not self.combined_model:
            # no obstacle -> minimum height
            # TODO: this "max(..)" is not correct for inclined lines
            points = [Point(line.p1.x, line.p1.y, max(minz, line.p1.z)),
                    Point(line.p2.x, line.p2.y, max(minz, line.p2.z))]
        else:
            # TODO: this "max(..)" is not correct for inclined lines.
            p1 = Point(line.p1.x, line.p1.y, max(minz, line.p1.z))
            p2 = Point(line.p2.x, line.p2.y, max(minz, line.p2.z))
            distance = line.len
            # we want to have at least five steps each
            num_of_steps = max(5, 1 + ceil(distance / horiz_step))
            # steps may be negative
            x_step = (p2.x - p1.x) / (num_of_steps - 1)
            y_step = (p2.y - p1.y) / (num_of_steps - 1)
            x_steps = [(p1.x + i * x_step) for i in range(num_of_steps)]
            y_steps = [(p1.y + i * y_step) for i in range(num_of_steps)]
            step_coords = zip(x_steps, y_steps)
            # TODO: this "min(..)" is not correct for inclided lines. This
            # should be fixed in "get_max_height".
            points = get_max_height_dynamic(self.combined_model, self.cutter,
                    step_coords, min(p1.z, p2.z), maxz, self.physics)
        for point in points:
            if point is None:
                # exceeded maxz - the cutter has to skip this point
                pa.end_scanline()
                pa.new_scanline()
                continue
            pa.append(point)
        if draw_callback and points:
            draw_callback(tool_position=points[-1], toolpath=pa.paths)
        pa.end_scanline()
        pa.end_direction()

