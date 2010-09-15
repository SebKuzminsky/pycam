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
        triangle_queue = self.model.triangles()[:]
        visited_triangles = []
        while len(triangle_queue) > 0:
            first_skipped = False
            #print "Triangles left: %d" % len(triangle_queue)
            triangle = triangle_queue.pop()
            # ignore triangles below the z level
            if triangle.maxz < z:
                continue
            cutter_location, ct, ctp, waterline = self.get_collision_waterline_of_triangle(triangle, z)
            if ct is None:
                continue
            if ct in visited_triangles:
                continue
            print "%s / %s / %s / %s" % (cutter_location, ct, ctp, waterline)
            self.pa.new_scanline()
            #print "**** new scanline ****"
            # start from the middle of the triangle to the end of the waterline
            waterline = Line(ctp, waterline.p2)
            cutter_location = waterline.p2
            cutter_location, ct, ctp, waterline = \
                    self.go_to_next_collision(ct, ctp, cutter_location, waterline)
            self.pa.append(cutter_location)
            self.cutter.moveto(cutter_location)
            while (not ct in visited_triangles) and (not math.isnan(cutter_location.x)):
                if first_skipped:
                    #print "New cutter location: %s" % str(cutter_location)
                    self.pa.append(cutter_location)
                    visited_triangles.append(ct)
                    self.cutter.moveto(cutter_location)
                else:
                    first_skipped = True
                if draw_callback:
                    draw_callback(tool_position=cutter_location, toolpath=self.pa.paths)
                cutter_location, ct, ctp, waterline = \
                        self.go_to_next_collision(ct, ctp, cutter_location, waterline)
                #print "cl, ct, ctp, waterline: %s\n\t%s\n\t%s\n\t%s" % (cutter_location, ct, ctp, waterline)
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
            return None, None, None, None
        # this vector is guaranteed to reach the outer limits
        direction_sized = direction_xy.mul(self.get_max_length())
        cutter_location, triangle_collisions = self.find_next_outer_collision(start, direction_sized)
        if cutter_location is None:
            # no collision starting from this point
            #print "Unexpected: missing collision"
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

    def find_next_outer_collision(self, point, direction):
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
            if (index % 2 == 0) and (not coll[1] is None):
                coll_outer.append(coll)
        #print "Outer collision candidates: %s" % str(coll_outer)
        if not coll_outer:
            return None, None
        # find all triangles that cause the collision
        cutter_location = coll_outer[0][0]
        closest_triangles = []
        while coll_outer and (abs(coll_outer[0][0].sub(cutter_location).norm) < epsilon):
            current_collision, t, cp = coll_outer.pop()
            raw_waterline = self.get_raw_triangle_waterline(t, cp, cutter_location)
            if (not raw_waterline is None) and (raw_waterline.len != 0):
                closest_triangles.append((t, cp, raw_waterline))
        #print "Outer collision selection: %s" % str(closest_triangles)
        if len(closest_triangles) > 0:
            return cutter_location, closest_triangles
        else:
            return None, None

    def get_closest_adjacent_waterline(self, triangle, waterline, reference_point):
        # Find the adjacent triangles that share vertices with the end of the
        # waterline of the original triangle.
        edges = []
        for edge in (triangle.e1, triangle.e2, triangle.e3):
            if edge.is_point_in_line(waterline.p2):
                edges.append(edge)
                # also add the reverse to speed up comparisons
                edges.append(Line(edge.p2, edge.p1))
        triangles = []
        for t in self.model.triangles():
            if (not t is triangle) and ((t.e1 in edges) or (t.e2 in edges) \
                    or (t.e3 in edges)):
                t_waterline = self.get_raw_triangle_waterline(t, waterline.p2,
                        reference_point)
                if t_waterline is None:
                    # no waterline through this triangle
                    continue
                if t_waterline.len == 0:
                    # Ignore zero-length waterlines - there should be other -
                    # non-point-like waterlines in other triangles.
                    continue
                if t_waterline.p1 != waterline.p2:
                    if t_waterline.p2 == waterline.p2:
                        t_waterline = Line(t_waterline.p2, t_waterline.p1)
                    else:
                        raise ValueError("get_waterline_endpoint: invalid " \
                                + ("neighbouring waterline: %s (orig) / %s " \
                                + "(neighbour)") % (waterline, t_waterline))
                angle = get_angle_pi(t_waterline.p2, t_waterline.p1,
                        waterline.p1, self._up_vector)
                triangles.append((t, t_waterline, angle))
        # Find the waterline with the smallest angle between original waterline
        # and this triangle's waterline.
        triangles.sort(key=lambda (t, t_waterline, angle): angle)
        t, t_waterline, angle = triangles[0]
        return t, t_waterline, angle

    def get_waterline_endpoint(self, triangle, waterline, cutter_location):
        strategy = "waterline"
        reference_point = cutter_location.add(waterline.p2.sub(waterline.p1))
        # Project the waterline and the cutter location down to the slice plane.
        # This is necessary for calculating the horizontal distance between the
        # cutter and the triangle waterline.
        plane = Plane(cutter_location, self._up_vector)
        wl_proj_p1 = plane.get_point_projection(waterline.p1)
        wl_proj_p2 = plane.get_point_projection(waterline.p2)
        wl_proj = Line(wl_proj_p1, wl_proj_p2)
        if wl_proj.len < epsilon:
            #print "Waterline endpoint for zero sized line requested: %s" % str(waterline)
            return reference_point
        offset = wl_proj.dist_to_point(cutter_location)
        if offset < epsilon:
            return reference_point
        # Calculate the length of the vector change.
        t, t_waterline, angle = self.get_closest_adjacent_waterline(triangle, waterline, reference_point)
        def get_waterline_collision():
            # TODO: same height as before?
            next_cl, dummy1, dummy2, next_waterline = self.get_collision_waterline_of_triangle(t, reference_point.z)
            if next_cl is None:
                raise ValueError("Failed collision: %s / %s" % (t, reference_point))
            line1 = Line(cutter_location, cutter_location.add(waterline.p2.sub(waterline.p1)))
            line2 = Line(next_cl, next_cl.add(next_waterline.p2.sub(next_waterline.p1)))
            if line1.dir == line2.dir:
                # both are on a straight line
                #print "STRAIGHT: %s / %s" % (line1, line2)
                return line1.p2
            cp, dist = line1.get_intersection(line2, infinite_lines=True)
            if cp is None:
                raise ValueError("Line going backward: %s / %s" % (waterline, t_waterline))
            else:
                if abs(dist) < epsilon:
                    # "dist" is almost zero: 
                    return cutter_location
                elif dist < 0:
                    raise ValueError("Waterline endpoint backwards: %s / %s" % (cp, dist))
                else:
                    # safety distance is required to avoid any collision due to float inaccuracies
                    safety_distance = cp.sub(cutter_location).normalized().mul(epsilon)
                    return cp.add(safety_distance)
        def get_bisector_collision():
            # bisector based code
            bisector_dir = get_bisector(waterline.p1, waterline.p2, t_waterline.p2, self._up_vector)
            bisector = Line(waterline.p2, waterline.p2.add(bisector_dir))
            waterline_dir = waterline.p2.sub(waterline.p1)
            cp, dist = Line(cutter_location, cutter_location.add(
                    waterline_dir)).get_intersection(bisector, infinite_lines=True)
            if cp is None:
                raise ValueError("Line going backward: %s / %s" % (waterline, t_waterline))
            else:
                if abs(dist) < epsilon:
                    # "dist" is almost zero: 
                    return cutter_location
                elif dist < 0:
                    raise ValueError("Waterline endpoint backwards: %s / %s" % (cp, dist))
                else:
                    return cp
        def get_angle_collision():
            # angle based code
            if abs(angle - math.pi) < epsilon:
                # The two waterlines (waterline and t_waterline) are on a straight
                # line. Thus we need to add the length of the t_waterline (incl.
                # its extension) as the extension of "waterline".
                # This sounds like a possible recursion trap, but it should be
                # of finite depth.
                #print "Waterline extension: straight line (%s / %s)" % (waterline, t_waterline)
                endpoint = t_waterline.p2.sub(t_waterline.p1).add(
                        self.get_waterline_endpoint(t, t_waterline,
                        reference_point))
            if abs(angle - 2 * math.pi) < epsilon:
                raise ValueError("Line going backward: %s / %s" % (waterline, t_waterline))
            else:
                # this waterline and the next are _not_ on a straight line
                change_vector_length = offset / math.tan(angle / 2)
                change_vector = waterline.dir.mul(change_vector_length)
                endpoint = cutter_location.add(waterline.p2.sub(waterline.p1)).add(change_vector)
            #print "Waterline extension: %s (%f)" % (change_vector, change_vector.norm)
            return endpoint
        # alternative calculations - "waterline_collision" seems to be the best
        waterline_collision = get_waterline_collision()
        #bisector_collision = get_bisector_collision()
        #angle_collision = get_angle_collision()
        #print "Endpoints: %s / %s / %s" % (waterline_collision, bisector_collision, angle_collision)
        collision = waterline_collision
        return Point(collision.x, collision.y, collision.z)

