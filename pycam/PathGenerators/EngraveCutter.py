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
from pycam.PathGenerators import get_max_height_triangles, get_max_height_ode, get_free_horizontal_paths_ode, get_free_horizontal_paths_triangles, ProgressCounter
import math

class EngraveCutter:

    def __init__(self, cutter, model, contour_model, path_processor, physics=None,
            safety_height=INFINITE):
        self.cutter = cutter
        self.model = model
        self.contour_model = contour_model
        self.pa = path_processor
        self.physics = physics
        self.safety_height = safety_height

    def GenerateToolPath(self, minz, maxz, horiz_step, dz, draw_callback=None):
        # calculate the number of steps
        num_of_layers = 1 + int(math.ceil(abs(maxz - minz) / dz))
        if num_of_layers > 1:
            z_step = abs(maxz - minz) / (num_of_layers - 1)
            z_steps = [(maxz - i * dz) for i in range(num_of_layers)]
            # the top layer is treated as the surface - thus it does not require engraving
            z_steps = z_steps[1:]
        else:
            z_steps = [minz]
        num_of_layers = len(z_steps)

        paths = []
        current_layer = 0
        lines = self.contour_model.get_lines()
        progress_counter = ProgressCounter(len(z_steps) * len(lines),
                draw_callback)

        # push slices for all layers above ground
        for z in z_steps[:-1]:
            # update the progress bar and check, if we should cancel the process
            if draw_callback and draw_callback(text="Engrave: processing" \
                        + " layer %d/%d" % (current_layer, num_of_layers)):
                # cancel immediately
                break

            for line in lines:
                self.GenerateToolPathLinePush(line, z)
                progress_counter.increment()
            self.pa.finish()

            # the path accumulator will be reset for each slice - we need to store the result
            if self.pa.paths:
                paths += self.pa.paths

            current_layer += 1

        if draw_callback:
            draw_callback(text="Engrave: processing layer %d/%d" \
                    % (current_layer, num_of_layers))

        # process the final layer with a drop cutter
        for line in lines:
            self.GenerateToolPathLineDrop(line, minz, maxz, horiz_step,
                    draw_callback=draw_callback)
            progress_counter.increment()
        self.pa.finish()
        # the path accumulator will be reset for each slice - we need to store the result
        if self.pa.paths:
            paths += self.pa.paths
        
        return paths

    def GenerateToolPathLinePush(self, line, z, draw_callback=None):
        p1 = Point(line.p1.x, line.p1.y, z)
        p2 = Point(line.p2.x, line.p2.y, z)
        if not self.model:
            points = [p1, p2]
        elif self.physics:
            points = get_free_horizontal_paths_ode(self.physics, p1.x, p2.x,
                    p1.y, p2.y, z)
        else:
            points = get_free_horizontal_paths_triangles(self.model,
                    self.cutter, p1.x, p2.x, p1.y, p2.y, z)
        if points:
            for p in points:
                self.pa.append(p)
            self.cutter.moveto(p)
            if draw_callback:
                draw_callback(tool_position=p)


    def GenerateToolPathLineDrop(self, line, minz, maxz, horiz_step,
            draw_callback=None):
        p1 = Point(line.p1.x, line.p1.y, minz)
        p2 = Point(line.p2.x, line.p2.y, minz)
        distance = line.len()
        num_of_steps = 1 + int(math.ceil(distance / horiz_step))
        # steps may be negative
        x_step = (p2.x - p1.x) / (num_of_steps - 1)
        y_step = (p2.y - p1.y) / (num_of_steps - 1)
        x_steps = [(p1.x + i * x_step) for i in range(num_of_steps)]
        y_steps = [(p1.y + i * y_step) for i in range(num_of_steps)]
        step_coords = zip(x_steps, y_steps)

        last_position = None

        for x, y in step_coords:
            if not self.model:
                points = [p1, p2]
            elif self.physics:
                points = get_max_height_ode(self.physics, x, y, minz, maxz)
            else:
                points = get_max_height_triangles(self.model, self.cutter,
                        x, y, minz, maxz, last_pos=last_position)

            if points:
                for p in points:
                    self.pa.append(p)
            else:
                p = Point(x, y, self.safety_height)
                self.pa.append(p)
                if not self._boundary_warning_already_shown:
                    print >>sys.stderr, "WARNING: DropCutter exceed the height" \
                            + " of the boundary box: using a safe height " \
                            + "instead. This warning is reported only once."
                self._boundary_warning_already_shown = True
            self.cutter.moveto(p)
            # "draw_callback" returns true, if the user requested quitting via the GUI
            if draw_callback and draw_callback(tool_position=p):
                #print "Quit requested?"
                break


