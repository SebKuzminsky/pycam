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
            left_index = self.left[index] and self.triangles.index(self.left[index])
            right_index = self.right[index] and self.triangles.index(self.right[index])
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
        for index, wl in enumerate(self.waterlines):
            if waterline.p2 == wl.p1:
                if not right is None:
                    raise ValueError("Too many right neighbours:\n%s\n%s\n%s" % (triangle, right, self.triangles[index]))
                right = self.triangles[index]
                if not self.left[index] is None:
                    raise ValueError("Too many previous right neighbours:\n%s\n%s\n%s" % (triangle, self.left[index], self.triangles[index]))
                self.left[index] = triangle
            elif waterline.p1 == wl.p2:
                if not left is None:
                    raise ValueError("Too many left neighbours:\n%s\n%s\n%s" % (triangle, left, self.triangles[index]))
                left = self.triangles[index]
                if not self.right[index] is None:
                    raise ValueError("Too many previous left neighbours:\n%s\n%s\n%s" % (triangle, self.right[index], self.triangles[index]))
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
                raise ValueError("Missing intersection: %s / %s" % (shifted_line, right_shifted_line))
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

    def remove(self, index):
        # fix the connection to the left
        if not self.left[index] is None:
            left_index = self.triangles.index(self.left[index])
            self.right[left_index] = self.right[index]
        # fix the connection to the right
        if not self.right[index] is None:
            right_index = self.triangles.index(self.right[index])
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

    def get_raw_triangle_waterline(self, triangle, point, cutter_location):
        # TODO: waterline auch bei nur einem Punkt auf der Ebene!
        if (abs(triangle.maxz - triangle.minz) < epsilon) and (abs(triangle.maxz - point.z) < epsilon):
            # the triangle is on the plane
            min_d = None
            min_edge = None
            for edge in (triangle.e1, triangle.e2, triangle.e3):
                dist = edge.dist_to_point_sq(cutter_location)
                if (min_d is None) or (dist < min_d):
                    min_d = dist
                    min_edge = edge
            # Check the direction of the points. We want an anti-clockwise
            # direction along point, edge.p1 and edge.p2.
            dotcross = self._up_vector.dot(min_edge.p1.sub(cutter_location).cross(min_edge.p2.sub(cutter_location)))
            if dotcross > 0:
                real_waterline = min_edge
            else:
                real_waterline = Line(min_edge.p2, min_edge.p1)
        else:
            real_waterline = Plane(point, self._up_vector).intersect_triangle(triangle)
        return real_waterline

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
            cutter_location, ct, ctp, waterline = self.get_collision_waterline_of_triangle(triangle, z)
            if ct is None:
                continue
            shifted_waterline = self.get_waterline_extended(ct, waterline, cutter_location)
            projected_waterline = plane.get_line_projection(waterline)
            waterline_triangles.add(triangle, projected_waterline, shifted_waterline)
        waterline_triangles.extend_waterlines()
        for wl in waterline_triangles.get_shifted_lines():
            self.pa.new_scanline()
            self.pa.append(wl.p1)
            self.pa.append(wl.p2)
            self.pa.end_scanline()
            #print l
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
            return None, None, None, None
        # this vector is guaranteed to reach the outer limits
        direction_sized = direction_xy.mul(self.get_max_length())
        if str(triangle).startswith("Triangle8<"):
            debug = True
        else:
            debug = False
        cutter_location, triangle_collisions = self.find_next_outer_collision(start, direction_sized, preferred_triangle=triangle)
        if cutter_location is None:
            # no collision starting from this point
            #print "Unexpected: missing collision (%s)" % str(direction_sized)
            return None, None, None, None
        # ct: colliding triangle
        # ctp: collision point within colliding triangle
        # waterline: cut along the triangle at the height of ctp
        ct, ctp, waterline = self.pick_suitable_triangle(triangle_collisions, cutter_location)
        return cutter_location, ct, ctp, waterline

    def go_to_next_collision(self, triangle, triangle_cp, cutter_location, waterline):
        start_point = cutter_location
        end_point = self.get_waterline_endpoint(triangle, waterline, cutter_location)
        if start_point != end_point:
            collisions = get_free_paths_triangles(self.model, self.cutter,
                    start_point, end_point, return_triangles=True)
        else:
            collisions = []
        # remove references to the original triangle and ignore moves to the current position
        collisions = [coll for coll in collisions
                if (not coll[1] is triangle) and (not coll[1] is None) \
                    and ((coll[0] != start_point) and (coll[0] != end_point))]
        # remove leading dummy collisions
        if collisions:
            cl, ct, ctp = collisions.pop(0)
            coll_t_p = [(ct, ctp)]
            # collect all other collisions with the same distance
            while collisions and (collisions[0][0] == cl):
                coll_t_p.append(collisions.pop(0)[1:])
            # pick a random triangle (avoids deadlock)
            while len(coll_t_p) > 0:
                index = random.randint(0, len(coll_t_p) - 1)
                ct, ctp = coll_t_p[index]
                new_waterline = self.get_raw_triangle_waterline(ct, ctp, cl)
                if (new_waterline is None) or (new_waterline.len == 0):
                    new_waterline = None
                    coll_t_p.pop(index)
                else:
                    break
            # We ignore the part of the waterline from the beginning up to the
            # point of collision in the triangle.
            if not new_waterline is None:
                waterline = Line(ctp, new_waterline.p2)
                return (cl, ct, ctp, waterline)
        if True:
            # no collisions: continue with the next adjacent waterline
            t, waterline, angle = self.get_closest_adjacent_waterline(triangle,
                    waterline, end_point)
            return (end_point, t, waterline.p1, waterline)

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
        #print "Outer collision candidates: (%d) %s" % (len(coll_outer), collisions)
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
                # try the reverse direction
                pt_cl, pt_d, pt_cp = self.cutter.intersect(direction.mul(-1), preferred_triangle)
            if pt_cl == cutter_location:
                raw_waterline = self.get_raw_triangle_waterline(preferred_triangle, pt_cp, cutter_location)
                return cutter_location, [(preferred_triangle, pt_cp, raw_waterline)]
        while coll_outer and (abs(coll_outer[0][0].sub(cutter_location).norm) < epsilon):
            current_collision, t, cp = coll_outer.pop()
            raw_waterline = self.get_raw_triangle_waterline(t, cp, cutter_location)
            if (not raw_waterline is None) and (raw_waterline.len != 0):
                closest_triangles.append((t, cp, raw_waterline))
            else:
                print "No waterline found: %s / %s / %s" % (t, cp, cutter_location)
        #print "Outer collision selection: %s" % str(closest_triangles)
        if len(closest_triangles) > 0:
            return cutter_location, closest_triangles
        else:
            return None, None

    def get_closest_adjacent_waterline(self, triangle, waterline, wl_point, reference_point):
        # Find the adjacent triangles that share vertices with the end of the
        # waterline of the original triangle.
        edges = []
        for edge in (triangle.e1, triangle.e2, triangle.e3):
            if edge.is_point_in_line(wl_point):
                edges.append(edge)
                # also add the reverse to speed up comparisons
                edges.append(Line(edge.p2, edge.p1))
        triangles = []
        for t in self.model.triangles():
            if (not t is triangle) and ((t.e1 in edges) or (t.e2 in edges) \
                    or (t.e3 in edges)):
                t_waterline = self.get_raw_triangle_waterline(t, wl_point,
                        reference_point)
                if t_waterline is None:
                    # no waterline through this triangle
                    continue
                if t_waterline.len == 0:
                    # Ignore zero-length waterlines - there should be other -
                    # non-point-like waterlines in other triangles.
                    continue
                if t_waterline.p1 != wl_point:
                    if t_waterline.p2 == wl_point:
                        t_waterline = Line(t_waterline.p2, t_waterline.p1)
                    else:
                        raise ValueError("get_waterline_endpoint: invalid " \
                                + ("neighbouring waterline: %s (orig) / %s " \
                                + "(neighbour)") % (waterline, t_waterline))
                    angle = get_angle_pi(waterline.p2, waterline.p1,
                            t_waterline.p1, self._up_vector)
                else:
                    angle = get_angle_pi(t_waterline.p2, t_waterline.p1,
                            waterline.p1, self._up_vector)
                triangles.append((t, t_waterline, angle))
        # Find the waterline with the smallest angle between original waterline
        # and this triangle's waterline.
        triangles.sort(key=lambda (t, t_waterline, angle): angle)
        t, t_waterline, angle = triangles[0]
        return t, t_waterline, angle

    def get_waterline_extended(self, triangle, waterline, cutter_location):
        # Project the waterline and the cutter location down to the slice plane.
        # This is necessary for calculating the horizontal distance between the
        # cutter and the triangle waterline.
        plane = Plane(cutter_location, self._up_vector)
        wl_proj = plane.get_line_projection(waterline)
        if wl_proj.len < epsilon:
            #print "Waterline endpoint for zero sized line requested: %s" % str(waterline)
            return cutter_location
        offset = wl_proj.dist_to_point(cutter_location)
        if offset < epsilon:
            return cutter_location
        # shift both ends of the waterline towards the cutter location
        shift = cutter_location.sub(wl_proj.closest_point(cutter_location))
        shifted_waterline = Line(wl_proj.p1.add(shift), wl_proj.p2.add(shift))
        return shifted_waterline

        # Calculate the length of the vector change.
        t1, t1_waterline, angle1 = self.get_closest_adjacent_waterline(triangle, waterline, waterline.p1, cutter_location)
        t2, t2_waterline, angle2 = self.get_closest_adjacent_waterline(triangle, waterline, waterline.p2, cutter_location)
        #TODO1: check "get_closest_adjacent_waterline" for edge=waterline (don't take the triangle above/below)
        #TODO2: the extension does not work, if the "hit" triangles are above the cutter (e.g. lower sphere-half)
        #TODO3: same shift for both waterlines?
        def get_waterline_collision(t, default_location):
            next_cl, dummy1, dummy2, next_waterline = self.get_collision_waterline_of_triangle(t, cutter_location.z)
            if next_cl is None:
                print "Failed collision: %s / %s" % (t, cutter_location)
                return default_location
            next_wl_proj = plane.get_line_projection(next_waterline)
            next_shift = next_cl.sub(next_wl_proj.closest_point(next_cl))
            line = Line(next_wl_proj.p1.add(next_shift), next_wl_proj.p2.add(next_shift))
            if waterline.dir == line.dir:
                # both are on a straight line
                #print "STRAIGHT: %s / %s" % (line1, line2)
                return default_location
            cp, dist = shifted_waterline.get_intersection(line, infinite_lines=True)
            if cp is None:
                raise ValueError("Line going backward: %s / %s / %s / %s" % (triangle, t, waterline, next_waterline))
            else:
                if abs(dist) < epsilon:
                    # "dist" is almost zero: 
                    return default_location
                else:
                    return cp
        # alternative calculations - "waterline_collision" seems to be the best
        collision1 = get_waterline_collision(t1, shifted_waterline.p1)
        collision2 = get_waterline_collision(t2, shifted_waterline.p2)
        return Line(collision1, collision2)

