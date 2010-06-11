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
from pycam.PathGenerators import drop_cutter_test, get_free_horizontal_paths_ode
import math


class Hit:
    def __init__(self, cl, t, d, dir):
        self.cl = cl
        self.t = t
        self.d = d
        self.dir = dir
        self.z = -INFINITE

    def cmp(a,b):
        return cmp(a.d, b.d)

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
        c = self.cutter
        model = self.model

        if dx==0:
            forward = Point(1,0,0)
            backward = Point(-1,0,0)
            forward_small = Point(epsilon,0,0)
            backward_small = Point(-epsilon,0,0)
        elif dy == 0:
            forward = Point(0,1,0)
            backward = Point(0,-1,0)
            forward_small = Point(0,epsilon,0)
            backward_small = Point(0,-epsilon,0)

        x = minx
        y = miny
        
        line = 0

        last_loop = False
        while x<=maxx and y<=maxy:
            self.pa.new_scanline()

            # find all hits along scan line
            hits = []
            prev = Point(x,y,z)
            hits.append(Hit(prev, None, 0, None))

            triangles = None
            if dx==0:
                triangles = model.triangles(minx-self.cutter.radius,y-self.cutter.radius,z,maxx+self.cutter.radius,y+self.cutter.radius,INFINITE)
            else:
                triangles = model.triangles(x-self.cutter.radius,miny-self.cutter.radius,z,x+self.cutter.radius,maxy+self.cutter.radius,INFINITE)

            for t in triangles:
                #if t.normal().z < 0: continue;
                # normals point outward... and we want to approach the model from the outside!
                n = t.normal().dot(forward)
                c.moveto(prev)
                if n>=0:
                    (cl,d) = c.intersect(backward, t)
                    if cl:
                        hits.append(Hit(cl,t,-d,backward))
                        hits.append(Hit(cl.sub(backward_small),t,-d+epsilon,backward))
                        hits.append(Hit(cl.add(backward_small),t,-d-epsilon,backward))
                if n<=0:
                    (cl,d) = c.intersect(forward, t)
                    if cl:
                        hits.append(Hit(cl,t,d,forward))
                        hits.append(Hit(cl.add(forward_small),t,d+epsilon,forward))
                        hits.append(Hit(cl.sub(forward_small),t,d-epsilon,forward))

            if dx == 0:
                x = maxx
            if dy == 0:
                y = maxy

            next = Point(x, y, z)
            hits.append(Hit(next, None, maxx-minx, None))


            # sort along the scan direction
            hits.sort(Hit.cmp)

            # remove duplicates (typically shared edges)
            i = 1
            while i < len(hits):
                while i<len(hits) and abs(hits[i].d - hits[i-1].d)<epsilon/2:
                    del hits[i]
                i += 1

            # determine height at each interesting point
            for h in hits:
                (zmax, tmax) = drop_cutter_test(self.cutter, h.cl, model)
                h.z = zmax


            # find first hit cutter location that is below z-level
            begin = hits[0].cl
            end = None
            for h in hits:
                if h.z >= z - epsilon/10:
                    if begin and end:
                        self.pa.append(begin)
                        self.pa.append(end)
                    begin = None
                    end = None
                if h.z <= z + epsilon/10:
                    if not begin:
                        begin = h.cl
                    else:
                        end = h.cl
                
            if begin and end:
                self.pa.append(begin)
                self.pa.append(end)
                self.cutter.moveto(begin)
                self.cutter.moveto(end)
                if draw_callback:
                    draw_callback(tool_position=end)

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

