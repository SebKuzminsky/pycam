# -*- coding: utf-8 -*-
"""
$Id$

Copyright 2010 Lars Kruse <devel@sumpfralle.de>

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

from pycam.Geometry.Point import Point, Vector
from pycam.Geometry.Line import Line
from pycam.Geometry.Plane import Plane
from pycam.PathGenerators import get_free_paths_ode, get_free_paths_triangles
from pycam.Geometry.utils import epsilon, ceil, sqrt
from pycam.Geometry import get_bisector, get_angle_pi
from pycam.Utils import ProgressCounter
import random
import math


class WaterlineTriangles:

    def __init__(self):
        self.triangles = []
        self.waterlines = []
        self.shifted_lines = []
        self.left = []
        self.right = []

    def __str__(self):
        lines = []
        for index, t in enumerate(self.triangles):
            lines.append("%d - %s" % (index, t))
            if self.left[index] is None:
                left_index = None
            else:
                try:
                    left_index = self.triangles.index(self.left[index])
                except ValueError:
                    left_index = "%s not found" % str(self.left[index])
            if self.right[index] is None:
                right_index = None
            else:
                try:
                    right_index = self.triangles.index(self.right[index])
                except ValueError:
                    right_index = "%s not found" % str(self.right[index])
            lines.append("\t%s / %s" % (left_index, right_index))
            lines.append("\t%s" % str(self.waterlines[index]))
            lines.append("\t%s" % str(self.shifted_lines[index]))
        return "\n".join(lines)

    def add(self, triangle, waterline, shifted_line):
        if triangle in self.triangles:
            raise ValueError("Processing a triangle twice: %s" % str(triangle))
        if waterline in self.waterlines:
            # ignore this triangle
            return
        left = None
        right = None
        removal_list = []
        # Try to combine the new waterline with all currently existing ones.
        # The three input parameters may be changed in this process.
        for index, wl in enumerate(self.waterlines):
            if waterline.dir == wl.dir:
                if wl.is_point_in_line(waterline.p1):
                    if wl.is_point_in_line(waterline.p2):
                        # waterline is completely within wl - ignore it
                        return
                    else:
                        # waterline is longer than wl (on the right side)
                        waterline = Line(wl.p1, waterline.p2)
                        old_shifted_line = self.shifted_lines[index]
                        shifted_line = Line(old_shifted_line.p1, shifted_line.p2)
                        # remove the item later
                        removal_list.append(index)
                elif waterline.is_point_in_line(wl.p1):
                    if waterline.is_point_in_line(wl.p2):
                        # wl is completely within waterline
                        removal_list.append(index)
                    else:
                        # wl is longer than wl (on the right side)
                        waterline = Line(waterline.p1, wl.p2)
                        old_shifted_line = self.shifted_lines[index]
                        shifted_line = Line(shifted_line.p1, old_shifted_line.p2)
                        removal_list.append(index)
        # remove all triangles that were scheduled for removal
        removal_list.reverse()
        for index in removal_list:
            # don't connect the possible left/right neighbours
            self.remove(index, reset_connections=True)
        for index, wl in enumerate(self.waterlines):
            if (waterline.p2 == wl.p1) and (waterline.p1 != wl.p2):
                if not right is None:
                    # this may happen for multiple overlapping lines
                    continue
                right = self.triangles[index]
                if not self.left[index] is None:
                    # this may happen for multiple overlapping lines
                    continue
                self.left[index] = triangle
            elif (waterline.p1 == wl.p2) and (waterline.p2 != wl.p1):
                if not left is None:
                    # this may happen for multiple overlapping lines
                    continue
                left = self.triangles[index]
                if not self.right[index] is None:
                    # this may happen for multiple overlapping lines
                    continue
                self.right[index] = triangle
            else:
                # no neighbour found
                pass
        self.triangles.append(triangle)
        self.waterlines.append(waterline)
        self.shifted_lines.append(shifted_line)
        self.left.append(left)
        self.right.append(right)

    def extend_waterlines(self):
        index = 0
        while index < len(self.triangles):
            if self.right[index] is None:
                index += 1
                continue
            shifted_line = self.shifted_lines[index]
            right_index = self.triangles.index(self.right[index])
            right_shifted_line = self.shifted_lines[right_index]
            if shifted_line.dir == right_shifted_line.dir:
                # straight lines - combine these lines
                self.shifted_lines[index] = Line(shifted_line.p1, right_shifted_line.p2)
                # the following update is not necessary but it is good for debugging
                self.waterlines[index] = Line(self.waterlines[index].p1, self.waterlines[right_index].p2)
                self.remove(right_index)
                index = 0
                continue
            if shifted_line.p2 == right_shifted_line.p1:
                # the lines intersect properly
                index += 1
                continue
            cp, dist = shifted_line.get_intersection(right_shifted_line, infinite_lines=True)
            cp2, dist2 = right_shifted_line.get_intersection(shifted_line, infinite_lines=True)
            if cp is None:
                raise ValueError("Missing intersection:%d / %d\n\t%s\n\t%s\n\t%s\n\t%s" % (index, right_index, shifted_line, right_shifted_line, self.waterlines[index], self.waterlines[right_index]))
            if dist < epsilon:
                # remove the current triangle
                self.remove(index)
                index = 0
            elif dist2 > 1 - epsilon:
                # remove the other triangle
                self.remove(right_index)
                index = 0
            else:
                # introduce the new intersection point
                self.shifted_lines[index] = Line(shifted_line.p1, cp)
                self.shifted_lines[right_index] = Line(cp, right_shifted_line.p2)
                index += 1

    def remove(self, index, reset_connections=False):
        # fix the connection to the left
        if not self.left[index] is None:
            left_index = self.triangles.index(self.left[index])
            # Avoid "right neighbour" == "myself" loops.
            if reset_connections or (self.left[index] is self.triangles[left_index]):
                self.right[left_index] = None
            else:
                self.right[left_index] = self.right[index]
        # fix the connection to the right
        if not self.right[index] is None:
            right_index = self.triangles.index(self.right[index])
            # Avoid "left neighbour" == "myself" loops.
            if reset_connections or (self.right[index] is self.triangles[right_index]):
                self.left[right_index] = None
            else:
                self.left[right_index] = self.left[index]
        # remove the item
        self.triangles.pop(index)
        self.waterlines.pop(index)
        self.shifted_lines.pop(index)
        self.left.pop(index)
        self.right.pop(index)

    def get_shifted_lines(self):
        finished = []
        queue = self.shifted_lines
        while len(queue) > 0:
            current = queue.pop()
            finished.append(current)
            match_found = True
            while match_found:
                match_found = False
                for other_index, other in enumerate(queue):
                    if current.p2 == other.p1:
                        finished.append(other)
                        queue.pop(other_index)
                        current = other
                        match_found = True
        return finished


class Waterline:

    def __init__(self, cutter, model, path_processor, physics=None):
        # TODO: implement ODE for physics
        self.cutter = cutter
        self.model = model
        self.pa = path_processor
        self._up_vector = Vector(0, 0, 1)

    def GenerateToolPath(self, minx, maxx, miny, maxy, minz, maxz, dz,
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

        progress_counter = ProgressCounter(num_of_layers, draw_callback)

        current_layer = 0

        z_steps = [(maxz - i * z_step) for i in range(num_of_layers)]
        for z in z_steps:
            # update the progress bar and check, if we should cancel the process
            if draw_callback and draw_callback(text="PushCutter: processing" \
                        + " layer %d/%d" % (current_layer + 1, num_of_layers)):
                # cancel immediately
                break

            self.pa.new_direction(0)
            self.GenerateToolPathSlice(minx, maxx, miny, maxy, z,
                    draw_callback, progress_counter)
            self.pa.end_direction()
            self.pa.finish()

            current_layer += 1

        return self.pa.paths

    def get_max_length(self):
        x_dim = abs(self.model.maxx - self.model.minx)
        y_dim = abs(self.model.maxy - self.model.miny)
        z_dim = abs(self.model.maxz - self.model.minz)
        return sqrt(x_dim ** 2 + y_dim ** 2 + z_dim ** 2)

    def GenerateToolPathSlice(self, minx, maxx, miny, maxy, z,
            draw_callback=None, progress_counter=None):
        #print "**** Starting new slice at %f ****" % z
        plane = Plane(Point(0, 0, z), self._up_vector)
        visited_triangles = []
        lines = []
        waterline_triangles = WaterlineTriangles()
        for triangle in self.model.triangles():
            # ignore triangles below the z level
            if (triangle.maxz < z) or (triangle in visited_triangles):
                continue
            #cutter_location, ct, ctp, waterline = self.get_collision_waterline_of_triangle(triangle, z)
            cutter_location, waterline = self.get_collision_waterline_of_triangle(triangle, z)
            if cutter_location is None:
                continue
            shifted_waterline = self.get_shifted_waterline(triangle, waterline, cutter_location)
            if shifted_waterline is None:
                continue
            projected_waterline = plane.get_line_projection(waterline)
            try:
                waterline_triangles.add(triangle, projected_waterline, shifted_waterline)
            except ValueError:
                print "Ignored:", triangle
        waterline_triangles.extend_waterlines()
        for wl in waterline_triangles.get_shifted_lines():
            self.pa.new_scanline()
            self.pa.append(wl.p1)
            self.pa.append(wl.p2)
            self.pa.end_scanline()
        return self.pa.paths

    def get_collision_waterline_of_triangle(self, triangle, z):
        points = []
        for edge in (triangle.e1, triangle.e2, triangle.e3):
            if edge.p1.z < z < edge.p2.z:
                points.append(edge.p1.add(edge.p2.sub(edge.p1).mul((z - edge.p1.z) / (edge.p2.z - edge.p1.z))))
            elif edge.p2.z < z < edge.p1.z:
                points.append(edge.p2.add(edge.p1.sub(edge.p2).mul((z - edge.p2.z) / (edge.p1.z - edge.p2.z))))
        sums = [0, 0, 0]
        for p in points:
            sums[0] += p.x
            sums[1] += p.y
            sums[2] += p.z
        if len(points) > 0:
            start = Point(sums[0] / len(points), sums[1] / len(points), sums[2] / len(points))
        else:
            start = Point(triangle.center.x, triangle.center.y, z)
        # use a projection upon a plane trough (0, 0, 0)
        direction_xy = Plane(Point(0, 0, 0), self._up_vector).get_point_projection(triangle.normal).normalized()
        # ignore triangles pointing upward or downward
        if direction_xy is None:
            return None, None
        # this vector is guaranteed to reach the outer limits
        direction_sized = direction_xy.mul(self.get_max_length())
        # calculate the collision point
        self.cutter.moveto(start)
        cl, d, cp = self.cutter.intersect(direction_xy.mul(-1), triangle)
        if cl is None:
            return None, None
        else:
            plane = Plane(cp, self._up_vector)
            waterline = plane.intersect_triangle(triangle)
            if waterline is None:
                return None, None
            else:
                return cl, waterline

    def get_collision_waterline_of_triangle_old(self, triangle, z):
        points = []
        for edge in (triangle.e1, triangle.e2, triangle.e3):
            if edge.p1.z < z < edge.p2.z:
                points.append(edge.p1.add(edge.p2.sub(edge.p1).mul((z - edge.p1.z) / (edge.p2.z - edge.p1.z))))
            elif edge.p2.z < z < edge.p1.z:
                points.append(edge.p2.add(edge.p1.sub(edge.p2).mul((z - edge.p2.z) / (edge.p1.z - edge.p2.z))))
        sums = [0, 0, 0]
        for p in points:
            sums[0] += p.x
            sums[1] += p.y
            sums[2] += p.z
        if len(points) > 0:
            start = Point(sums[0] / len(points), sums[1] / len(points), sums[2] / len(points))
        else:
            start = Point(triangle.center.x, triangle.center.y, z)
        # use a projection upon a plane trough (0, 0, 0)
        direction_xy = Plane(Point(0, 0, 0), self._up_vector).get_point_projection(triangle.normal).normalized()
        # ignore triangles pointing upward or downward
        if direction_xy is None:
            return None, None, None, None
        # this vector is guaranteed to reach the outer limits
        direction_sized = direction_xy.mul(self.get_max_length())
        cutter_location, triangle_collisions = self.find_next_outer_collision(
                start, direction_sized, preferred_triangle=triangle)
        if cutter_location is None:
            # no collision starting from this point
            #print "Unexpected: missing collision (%s)" % str(direction_sized)
            return None, None, None, None
        # ct: colliding triangle
        # ctp: collision point within colliding triangle
        # waterline: cut along the triangle at the height of ctp
        ct, ctp, waterline = self.pick_suitable_triangle(triangle_collisions, cutter_location)
        return cutter_location, ct, ctp, waterline

    def pick_suitable_triangle(self, triangle_list, cutter_location):
        # TODO: is the distance to the cutter location the proper sorting key?
        line_distance = lambda (t, cp, waterline): waterline.dist_to_point_sq(cutter_location)
        new_list = triangle_list[:]
        new_list.sort(key=line_distance)
        return new_list[0]

    def find_next_outer_collision(self, point, direction, preferred_triangle=None):
        collisions = get_free_paths_triangles(self.model, self.cutter,
                point, point.add(direction), return_triangles=True)
        # remove leading "None"
        coll_outer = []
        for index, coll in enumerate(collisions):
            # Check if the collision goes in the direction of inside->outside of
            # the material. We assume, that each item of the "collisions" list
            # with an even index satisfies this condition.
            # Additionally we don't want to care for "not-real" collisions (e.g.
            # on the edge of the bounding box.
            if (index % 2 == 0) and (not coll[1] is None) \
                    and (not coll[2] is None):
                coll_outer.append(coll)
        if not coll_outer:
            return None, None
        # find all triangles that cause the collision
        cutter_location = coll_outer[0][0]
        closest_triangles = []
        # check the collision with the preferred triangle
        if not preferred_triangle is None:
            self.cutter.moveto(point)
            pt_cl, pt_d, pt_cp = self.cutter.intersect(direction, preferred_triangle)
            if pt_cl != cutter_location:
                # Also try the reverse direction. The direction is not just used
                # for the movement, but also for choosing the side (front/back)
                # of the cutter for collision checks.
                pt_cl, pt_d, pt_cp = self.cutter.intersect(direction.mul(-1), preferred_triangle)
            if pt_cl == cutter_location:
                plane = Plane(pt_cp, self._up_vector)
                waterline = plane.intersect_triangle(preferred_triangle)
                if not waterline is None:
                    return (cutter_location,
                            [(preferred_triangle, pt_cp, waterline)])
                else:
                    # Don't return a result, if the triangle was flat. The
                    # other triangle (sharing the relevant edge) will return
                    # a valid result anyway.
                    return None, None
        while coll_outer and (abs(coll_outer[0][0].sub(cutter_location).norm) < epsilon):
            current_collision, t, cp = coll_outer.pop()
            plane = Plane(current_collision, self._up_vector)
            waterline = plane.intersect_triangle(t)
            if not waterline is None:
                closest_triangles.append((t, cp, waterline))
        if len(closest_triangles) > 0:
            return cutter_location, closest_triangles
        else:
            return None, None

    def get_shifted_waterline(self, triangle, waterline, cutter_location):
        # Project the waterline and the cutter location down to the slice plane.
        # This is necessary for calculating the horizontal distance between the
        # cutter and the triangle waterline.
        plane = Plane(cutter_location, self._up_vector)
        wl_proj = plane.get_line_projection(waterline)
        if wl_proj.len < epsilon:
            return None
        offset = wl_proj.dist_to_point(cutter_location)
        if offset < epsilon:
            return wl_proj
        # shift both ends of the waterline towards the cutter location
        shift = cutter_location.sub(wl_proj.closest_point(cutter_location))
        shifted_waterline = Line(wl_proj.p1.add(shift), wl_proj.p2.add(shift))
        return shifted_waterline

