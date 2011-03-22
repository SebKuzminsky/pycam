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

from pycam.Geometry.Line import Line
from pycam.Geometry.Point import Point, Vector
from pycam.Geometry.Plane import Plane
from pycam.Geometry import TransformableContainer, get_bisector
from pycam.Geometry.utils import number, epsilon
import pycam.Utils.log
# import later to avoid circular imports
#from pycam.Geometry.Model import ContourModel

try:
    import OpenGL.GL as GL
    GL_enabled = True
except ImportError:
    GL_enabled = False


log = pycam.Utils.log.get_logger()


class Polygon(TransformableContainer):

    def __init__(self, plane=None):
        super(Polygon, self).__init__()
        if plane is None:
            # the default plane points upwards along the z axis
            plane = Plane(Point(0, 0, 0), Vector(0, 0, 1))
        self.plane = plane
        self._points = []
        self.is_closed = False
        self.maxx = None
        self.minx = None
        self.maxy = None
        self.miny = None
        self.maxz = None
        self.minz = None
        self._lines_cache = None
        self._area_cache = None
        self._cached_offset_polygons = {}

    def append(self, line):
        if not self.is_connectable(line):
            raise ValueError("This line does not fit to the polygon")
        elif line.len < epsilon:
            raise ValueError("A line with zero length may not be part of a " \
                    + "polygon")
        else:
            if not self._points:
                self._points.append(line.p1)
                self._update_limits(line.p1)
                self._points.append(line.p2)
                self._update_limits(line.p2)
            elif self._points[-1] == line.p1:
                # the new Line can be added to the end of the polygon
                if line.dir == self._points[-1].sub(
                        self._points[-2]).normalized():
                    # Remove the last point, if the previous point combination
                    # is in line with the new Line. This avoids unnecessary
                    # points on straight lines.
                    self._points.pop(-1)
                if line.p2 != self._points[0]:
                    self._points.append(line.p2)
                    self._update_limits(line.p2)
                else:
                    self.is_closed = True
                # take care that the line_cache is flushed
                self.reset_cache()
            else:
                # the new Line can be added to the beginning of the polygon
                if (len(self._points) > 1) \
                        and (line.dir == self._points[1].sub(
                            self._points[0]).normalized()):
                    # Avoid points on straight lines - see above.
                    self._points.pop(0)
                if line.p1 != self._points[-1]:
                    self._points.insert(0, line.p1)
                    self._update_limits(line.p1)
                else:
                    self.is_closed = True
                # take care that the line_cache is flushed
                self.reset_cache()

    def __len__(self):
        return len(self._points)

    def __str__(self):
        if self.is_closed:
            status = "closed"
        else:
            status = "open"
        return "Polygon (%s) %s" % (status, [point for point in self._points])

    def reverse_direction(self):
        self._points.reverse()
        self.reset_cache()

    def get_reversed(self):
        result = Polygon(plane=self.plane)
        result._points = self._points[:]
        result.is_closed = self.is_closed
        result.reverse_direction()
        return result

    def is_connectable(self, line_or_point):
        if self.is_closed:
            return False
        elif not self._points:
            # empty polygons can be connected with any line
            return True
        if hasattr(line_or_point, "get_length_line"):
            # it is a line
            line = line_or_point
            if line.p1 == self._points[-1]:
                return True
            elif line.p2 == self._points[0]:
                return True
            else:
                return False
        else:
            # it is a point
            point = line_or_point
            if (point == self._points[-1]) or (point == self._points[0]):
                return True
            else:
                return False

    def next(self):
        for point in self._points:
            yield point
        yield self.plane

    def get_children_count(self):
        return len(self._points) + self.plane.get_children_count()

    def get_area(self):
        """ calculate the area covered by a line group
        Currently this works only for line groups in an xy-plane.
        Returns zero for empty line groups or for open line groups.
        Returns negative values for inner hole.
        """
        if not self._points:
            return 0
        if not self.is_closed:
            return 0
        if self._area_cache is None:
            # calculate the area for the first time
            value = [0, 0, 0]
            # taken from: http://www.wikihow.com/Calculate-the-Area-of-a-Polygon
            # and: http://softsurfer.com/Archive/algorithm_0101/algorithm_0101.htm#3D%20Polygons
            for index in range(len(self._points)):
                p1 = self._points[index]
                p2 = self._points[(index + 1) % len(self._points)]
                value[0] += p1.y * p2.z - p1.z * p2.y
                value[1] += p1.z * p2.x - p1.x * p2.z
                value[2] += p1.x * p2.y - p1.y * p2.x
            result = self.plane.n.x * value[0] + self.plane.n.y * value[1] \
                    + self.plane.n.z * value[2]
            self._area_cache = result / 2
        return self._area_cache

    def get_barycenter(self):
        area = self.get_area()
        if not area:
            return None
        # see: http://stackoverflow.com/questions/2355931/compute-the-centroid-of-a-3d-planar-polygon/2360507
        # first: calculate cx and y
        cxy, cxz, cyx, cyz, czx, czy = (0, 0, 0, 0, 0, 0)
        for index in range(len(self._points)):
            p1 = self._points[index]
            p2 = self._points[(index + 1) % len(self._points)]
            cxy += (p1.x + p2.x) * (p1.x * p2.y - p1.y * p2.x)
            cxz += (p1.x + p2.x) * (p1.x * p2.z - p1.z * p2.x)
            cyx += (p1.y + p2.y) * (p1.x * p2.y - p1.y * p2.x)
            cyz += (p1.y + p2.y) * (p1.y * p2.z - p1.z * p2.y)
            czx += (p1.z + p2.z) * (p1.z * p2.x - p1.x * p2.z)
            czy += (p1.z + p2.z) * (p1.y * p2.z - p1.z * p2.y)
        if abs(self.maxz - self.minz) < epsilon:
            return Point(cxy / (6 * area), cyx / (6 * area), self.minz)
        elif abs(self.maxy - self.miny) < epsilon:
            return Point(cxz / (6 * area), self.miny, czx / (6 * area))
        elif abs(self.maxx - self.minx) < epsilon:
            return Point(self.minx, cyz / (6 * area), czy / (6 * area))
        else:
            # calculate area of xy projection
            poly_xy = self.get_plane_projection(Plane(Point(0, 0, 0),
                    Point(0, 0, 1)))
            poly_xz = self.get_plane_projection(Plane(Point(0, 0, 0),
                    Point(0, 1, 0)))
            poly_yz = self.get_plane_projection(Plane(Point(0, 0, 0),
                    Point(1, 0, 0)))
            if (poly_xy is None) or (poly_xz is None) or (poly_yz is None):
                log.warn("Invalid polygon projection for barycenter: %s" \
                        % str(self))
                return None
            area_xy = poly_xy.get_area()
            area_xz = poly_xz.get_area()
            area_yz = poly_yz.get_area()
            if 0 in (area_xy, area_xz, area_yz):
                log.info("Failed assumtion: zero-sized projected area - " + \
                        "%s / %s / %s" % (area_xy, area_xz, area_yz))
                return None
            if abs(cxy / area_xy - cxz / area_xz) > epsilon:
                log.info("Failed assumption: barycenter xy/xz - %s / %s" % \
                        (cxy / area_xy, cxz / area_xz))
            if abs(cyx / area_xy - cyz / area_yz) > epsilon:
                log.info("Failed assumption: barycenter yx/yz - %s / %s" % \
                        (cyx / area_xy, cyz / area_yz))
            if abs(czx / area_xz - czy / area_yz) > epsilon:
                log.info("Failed assumption: barycenter zx/zy - %s / %s" % \
                        (czx / area_xz, cyz / area_yz))
            return Point(cxy / (6 * area_xy), cyx / (6 * area_xy),
                    czx / (6 * area_xz))

    def get_length(self):
        """ add the length of all lines within the polygon
        """
        return sum(self.get_lengths())

    def get_middle_of_line(self, index):
        if (index >= len(self._points)) \
                or (not self.is_closed and index == len(self._points) - 1):
            return None
        else:
            return self._points[index].add(self._points[(index + 1) % \
                    len(self._points)]).div(2)

    def get_lengths(self):
        result = []
        for index in range(len(self._points) - 1):
            result.append(self._points[index + 1].sub(
                    self._points[index]).norm)
        if self.is_closed:
            result.append(self._points[0].sub(self._points[-1]).norm)
        return result

    def get_max_inside_distance(self):
        """ calculate the maximum distance between two points of the polygon
        """
        if len(self._points) < 2:
            return None
        distance = self._points[1].sub(self._points[0]).norm
        for p1 in self._points:
            for p2 in self._points:
                if p1 is p2:
                    continue
                distance = max(distance, p2.sub(p1).norm)
        return distance

    def is_outer(self):
        return self.get_area() > 0

    def is_polygon_inside(self, polygon):
        for point in polygon._points:
            if not self.is_point_inside(point):
                return False
        return True

    def is_point_on_outline(self, p):
        for line in self.get_lines():
            if line.is_point_inside(p):
                return True
        return False

    def is_point_inside(self, p):
        """ Test if a given point is inside of the polygon.
        The result is True if the point is on a line (or very close to it).
        """
        # First: check if the point is within the boundary of the polygon.
        if not p.is_inside(self.minx, self.maxx, self.miny, self.maxy,
                self.minz, self.maxz):
            # the point is outside the rectangle boundary
            return False
        # see http://www.alienryderflex.com/polygon/
        # Count the number of intersections of a ray along the x axis through
        # all polygon lines.
        # Odd number -> point is inside
        intersection_count_left = 0
        intersection_count_right = 0
        for index in range(len(self._points)):
            p1 = self._points[index]
            p2 = self._points[(index + 1) % len(self._points)]
            # Only count intersections with lines that are partly below
            # the y level of the point. This solves the problem of intersections
            # through shared vertices or lines that go along the y level of the
            # point.
            if ((p1.y < p.y) and (p.y <= p2.y)) \
                    or ((p2.y < p.y) and (p.y <= p1.y)):
                part_y = (p.y - p1.y) / (p2.y - p1.y)
                intersection_x = p1.x + part_y * (p2.x - p1.x)
                if intersection_x < p.x + epsilon:
                    # count intersections to the left
                    intersection_count_left += 1
                if intersection_x > p.x - epsilon:
                    # count intersections to the right
                    intersection_count_right += 1
        # odd intersection count -> inside
        left_odd = intersection_count_left % 2 == 1
        right_odd = intersection_count_right % 2 == 1
        if left_odd and right_odd:
            # clear decision: we are inside
            return True
        elif not left_odd and not right_odd:
            # clear decision: we are outside
            return False
        else:
            # it seems like we are on the line -> inside
            log.debug("polygon.is_point_inside: unclear decision")
            return True

    def get_points(self):
        return self._points[:]

    def get_lines(self):
        """ Caching is necessary to avoid constant recalculation due to
        the "to_OpenGL" method.
        """
        if self._lines_cache is None:
            # recalculate the line cache
            lines = []
            for index in range(len(self._points) - 1):
                lines.append(Line(self._points[index], self._points[index + 1]))
            # Connect the last point with the first only if the polygon is
            # closed.
            if self.is_closed:
                lines.append(Line(self._points[-1], self._points[0]))
            self._lines_cache = lines
        return self._lines_cache[:]

    def to_OpenGL(self, **kwords):
        if not GL_enabled:
            return
        if self.is_closed:
            is_outer = self.is_outer()
            if not is_outer:
                color = GL.glGetFloatv(GL.GL_CURRENT_COLOR)
                GL.glColor(color[0], color[1], color[2], color[3] / 2)
            GL.glBegin(GL.GL_LINE_LOOP)
            for point in self._points:
                GL.glVertex3f(point.x, point.y, point.z)
            GL.glEnd()
            if not is_outer:
                GL.glColor(*color)
        else:
            for line in self.get_lines():
                line.to_OpenGL(**kwords)

    def _update_limits(self, point):
        if self.minx is None:
            self.minx = point.x
            self.maxx = point.x
            self.miny = point.y
            self.maxy = point.y
            self.minz = point.z
            self.maxz = point.z
        else:
            self.minx = min(self.minx, point.x)
            self.maxx = max(self.maxx, point.x)
            self.miny = min(self.miny, point.y)
            self.maxy = max(self.maxy, point.y)
            self.minz = min(self.minz, point.z)
            self.maxz = max(self.maxz, point.z)
        self._lines_cache = None
        self._area_cache = None

    def reset_cache(self):
        self._cached_offset_polygons = {}
        self._lines_cache = None
        self._area_cache = None
        self.minx, self.miny, self.minz = None, None, None
        self.maxx, self.maxy, self.maxz = None, None, None
        # update the limit for each line
        for point in self._points:
            self._update_limits(point)

    def get_bisector(self, index):
        p1 = self._points[index - 1]
        p2 = self._points[index]
        p3 = self._points[(index + 1) % len(self._points)]
        return get_bisector(p1, p2, p3, self.plane.n)

    def get_offset_polygons_validated(self, offset):
        def get_shifted_vertex(index, offset):
            p1 = self._points[index]
            p2 = self._points[(index + 1) % len(self._points)]
            cross_offset = p2.sub(p1).cross(self.plane.n).normalized()
            bisector_normalized = self.get_bisector(index)
            factor = cross_offset.dot(bisector_normalized)
            if factor != 0:
                bisector_sized = bisector_normalized.mul(offset / factor)
                return p1.add(bisector_sized)
            else:
                return p2
        if offset * 2 >= self.get_max_inside_distance():
            # no polygons will be left
            return []
        points = []
        for index in range(len(self._points)):
            points.append(get_shifted_vertex(index, offset))
        max_dist = 1000 * epsilon
        def test_point_near(p, others):
            for o in others:
                if p.sub(o).norm < max_dist:
                    return True
            return False
        reverse_lines = []
        shifted_lines = []
        for index in range(len(points)):
            next_index = (index + 1) % len(points)
            p1 = points[index]
            p2 = points[next_index]
            diff = p2.sub(p1)
            old_dir = self._points[next_index].sub(
                    self._points[index]).normalized()
            if diff.normalized() != old_dir:
                # the direction turned around
                if diff.norm > max_dist:
                    # the offset was too big
                    return None
                else:
                    reverse_lines.append(index)
                shifted_lines.append((True, Line(p1, p2)))
            else:
                shifted_lines.append((False, Line(p1, p2)))
        # look for reversed lines
        index = 0
        while index < len(shifted_lines):
            line_reverse, line = shifted_lines[index]
            if line_reverse:
                prev_index = (index - 1) % len(shifted_lines)
                next_index = (index + 1) % len(shifted_lines)
                prev_reverse, prev_line = shifted_lines[prev_index]
                while prev_reverse and (prev_index != next_index):
                    prev_index = (prev_index - 1) % len(shifted_lines)
                    prev_reverse, prev_line = shifted_lines[prev_index]
                if prev_index == next_index:
                    # no lines are left
                    print "out 1"
                    return []
                next_reverse, next_line = shifted_lines[next_index]
                while next_reverse and (prev_index != next_index):
                    next_index = (next_index + 1) % len(shifted_lines)
                    next_reverse, next_line = shifted_lines[next_index]
                if prev_index == next_index:
                    # no lines are left
                    print "out 2"
                    return []
                if prev_line.p2.sub(next_line.p1).norm > max_dist:
                    cp, dist = prev_line.get_intersection(next_line)
                else:
                    cp = prev_line.p2
                if cp:
                    shifted_lines[prev_index] = (False, Line(prev_line.p1, cp))
                    shifted_lines[next_index] = (False, Line(cp, next_line.p2))
                else:
                    cp, dist = prev_line.get_intersection(next_line,
                            infinite_lines=True)
                    raise BaseException("Expected intersection not found: " + \
                            "%s - %s - %s(%d) / %s(%d)" % \
                            (cp, shifted_lines[prev_index+1:next_index],
                                prev_line, prev_index, next_line, next_index))
                if index > next_index:
                    # we wrapped around the end of the list
                    break
                else:
                    index = next_index + 1
            else:
                index += 1
        non_reversed = [line for reverse, line in shifted_lines
                if not reverse and line.len > 0]
        # split the list of lines into groups (based on intersections)
        split_points = []
        index = 0
        while index < len(non_reversed):
            other_index = 0
            while other_index < len(non_reversed):
                other_line = non_reversed[other_index]
                if (other_index == index) \
                        or (other_index == ((index - 1) % len(non_reversed))) \
                        or (other_index == ((index + 1) % len(non_reversed))):
                    # skip neighbours
                    other_index += 1
                    continue
                line = non_reversed[index]
                cp, dist = line.get_intersection(other_line)
                if cp:
                    if not test_point_near(cp,
                            (line.p1, line.p2, other_line.p1, other_line.p2)):
                        # the collision is not close to an end of the line
                        return None
                    elif (cp == line.p1) or (cp == line.p2):
                        # maybe we have been here before
                        if not cp in split_points:
                            split_points.append(cp)
                    elif (cp.sub(line.p1).norm < max_dist) \
                            or (cp.sub(line.p2).norm < max_dist):
                        if cp.sub(line.p1).norm < cp.sub(line.p2).norm:
                            non_reversed[index] = Line(cp, line.p2)
                        else:
                            non_reversed[index] = Line(line.p1, cp)
                        non_reversed.pop(other_index)
                        non_reversed.insert(other_index,
                                Line(other_line.p1, cp))
                        non_reversed.insert(other_index + 1,
                                Line(cp, other_line.p2))
                        split_points.append(cp)
                        if other_index < index:
                            index += 1
                        # skip the second part of this line
                        other_index += 1
                    else:
                        # the split of 'other_line' will be handled later
                        pass
                other_index += 1
            index += 1
        groups = [[]]
        current_group = 0
        split_here = False
        for line in non_reversed:
            if line.p1 in split_points:
                split_here = True
            if split_here:
                split_here = False
                # check if any preceeding group fits to the point
                for index, group in enumerate(groups):
                    if not group:
                        continue
                    if index == current_group:
                        continue
                    if group[0].p1 == group[-1].p2:
                        # the group is already closed
                        continue
                    if line.p1 == group[-1].p2:
                        current_group = index
                        groups[current_group].append(line)
                        break
                else:
                    current_group = len(groups)
                    groups.append([line])
            else:
                groups[current_group].append(line)
            if line.p2 in split_points:
                split_here = True
        def is_joinable(g1, g2):
            if g1 and g2 and (g1[0].p1 != g1[-1].p2):
                if g1[0].p1 == g2[-1].p2:
                    return g2 + g1
                if g2[0].p1 == g1[-1].p2:
                    return g1 + g2
            return None
        # try to combine open groups
        for index1, group1 in enumerate(groups):
            if not group1:
                continue
            for index2, group2 in enumerate(groups):
                if not group2:
                    continue
                if index2 <= index1:
                    continue
                if (group1[-1].p2 == group2[0].p1) \
                        and (group1[0].p1 == group2[-1].p2):
                    group1.extend(group2)
                    groups[index2] = []
                    break
        result_polygons = []
        print "********** GROUPS **************"
        for a in groups:
            print a
        for group in groups:
            if len(group) <= 2:
                continue
            poly = Polygon(self.plane)
            #print "**************************************"
            for line in group:
                try:
                    poly.append(line)
                except ValueError:
                    print "NON_REVERSED"
                    for a in non_reversed:
                        print a
                    print groups
                    print split_points
                    print poly
                    print line
                    raise
            if self.is_closed and ((not poly.is_closed) \
                    or (self.is_outer() != poly.is_outer())):
                continue
            elif (not self.is_closed) and (poly.get_area() != 0):
                continue
            else:
                result_polygons.append(poly)
        return result_polygons

    def get_offset_polygons_incremental(self, offset, depth=20):
        if offset == 0:
            return [self]
        if self._cached_offset_polygons.has_key(offset):
            return self._cached_offset_polygons[offset]
        def is_better_offset(previous_offset, alternative_offset):
            return ((offset < alternative_offset < 0) \
                    or (0 < alternative_offset < offset)) \
                    and (abs(alternative_offset) > abs(previous_offset))
        # check the cache for a good starting point
        best_offset = 0
        best_offset_polygons = [self]
        for cached_offset in self._cached_offset_polygons:
            if is_better_offset(best_offset, cached_offset):
                best_offset = cached_offset
                best_offset_polygons = \
                        self._cached_offset_polygons[cached_offset]
        remaining_offset = offset - best_offset
        result_polygons = []
        for poly in best_offset_polygons:
            result = poly.get_offset_polygons_validated(remaining_offset)
            if not result is None:
                result_polygons.extend(result)
            else:
                lower = number(0)
                upper = remaining_offset
                loop_limit = 90
                while (loop_limit > 0):
                    middle = (upper + lower) / 2
                    result = poly.get_offset_polygons_validated(middle)
                    if result is None:
                        upper = middle
                    else:
                        if depth > 0:
                            # the original polygon was splitted or modified
                            print "Next level: %s" % str(middle)
                            shifted_sub_polygons = []
                            for sub_poly in result:
                                shifted_sub_polygons.extend(
                                        sub_poly.get_offset_polygons(
                                            remaining_offset - middle,
                                            depth=depth-1))
                            result_polygons.extend(shifted_sub_polygons)
                            break
                        else:
                            print "Maximum recursion level reached"
                            break
                    loop_limit -= 1
                else:
                    # no split event happened -> no valid shifted polygon
                    pass
        self._cached_offset_polygons[offset] = result_polygons
        return result_polygons

    def get_offset_polygons(self, offset, callback=None):
        def get_shifted_vertex(index, offset):
            p1 = self._points[index]
            p2 = self._points[(index + 1) % len(self._points)]
            cross_offset = p2.sub(p1).cross(self.plane.n).normalized()
            bisector_normalized = self.get_bisector(index)
            factor = cross_offset.dot(bisector_normalized)
            if factor != 0:
                bisector_sized = bisector_normalized.mul(offset / factor)
                return p1.add(bisector_sized)
            else:
                return p2
        def simplify_polygon_intersections(lines):
            new_group = lines[:]
            # remove all non-adjacent intersecting lines (this splits the group)
            if len(new_group) > 0:
                group_starts = []
                index1 = 0
                while index1 < len(new_group):
                    index2 = 0
                    while index2 < len(new_group):
                        index_distance = min(abs(index2 - index1), \
                                abs(len(new_group) - (index2 - index1))) 
                        # skip neighbours
                        if index_distance > 1:
                            line1 = new_group[index1]
                            line2 = new_group[index2]
                            intersection, factor = line1.get_intersection(line2)
                            if intersection and (intersection != line1.p1) \
                                    and (intersection != line1.p2):
                                del new_group[index1]
                                new_group.insert(index1,
                                        Line(line1.p1, intersection))
                                new_group.insert(index1 + 1,
                                        Line(intersection, line1.p2))
                                # Shift all items in "group_starts" by one if
                                # they reference a line whose index changed.
                                for i in range(len(group_starts)):
                                    if group_starts[i] > index1:
                                        group_starts[i] += 1
                                if not index1 + 1 in group_starts:
                                    group_starts.append(index1 + 1)
                                # don't update index2 -> maybe there are other hits
                            elif intersection and (intersection == line1.p1):
                                if not index1 in group_starts:
                                    group_starts.append(index1)
                                index2 += 1
                            else:
                                index2 += 1
                        else:
                            index2 += 1
                    index1 += 1
                # The lines intersect each other
                # We need to split the group.
                if len(group_starts) > 0:
                    group_starts.sort()
                    groups = []
                    last_start = 0
                    for group_start in group_starts:
                        groups.append(new_group[last_start:group_start])
                        last_start = group_start
                    # Add the remaining lines to the first group or as a new
                    # group.
                    if groups[0][0].p1 == new_group[-1].p2:
                        groups[0] = new_group[last_start:] + groups[0]
                    else:
                        groups.append(new_group[last_start:])
                    # try to find open groups that can be combined
                    combined_groups = []
                    for index, current_group in enumerate(groups):
                        # Check if the group is not closed: try to add it to
                        # other non-closed groups.
                        if current_group[0].p1 == current_group[-1].p2:
                            # a closed group
                            combined_groups.append(current_group)
                        else:
                            # the current group is open
                            for other_group in groups[index + 1:]:
                                if other_group[0].p1 != other_group[-1].p2:
                                    # This group is also open - a candidate
                                    # for merging?
                                    if other_group[0].p1 == current_group[-1].p2:
                                        current_group.reverse()
                                        for line in current_group:
                                            other_group.insert(0, line)
                                        break
                                    if other_group[-1].p2 == current_group[0].p1:
                                        other_group.extend(current_group)
                                        break
                            else:
                                # not suitable open group found
                                combined_groups.append(current_group)
                    return combined_groups
                else:
                    # just return one group without intersections
                    return [new_group]
            else:
                return None
        offset = number(offset)
        if offset == 0:
            return [self]
        if offset * 2 >= self.get_max_inside_distance():
            # This offset will not create a valid offset polygon.
            # Sadly there is currently no other way to detect a complete flip of
            # something like a circle.
            log.debug("Skipping offset polygon: polygon is too small")
            return []
        points = []
        for index in range(len(self._points)):
            points.append(get_shifted_vertex(index, offset))
        new_lines = []
        for index in range(len(points)):
            p1 = points[index]
            p2 = points[(index + 1) % len(points)]
            new_lines.append(Line(p1, p2))
        if callback and callback():
            return None
        cleaned_line_groups = simplify_polygon_intersections(new_lines)
        if cleaned_line_groups is None:
            log.debug("Skipping offset polygon: intersections could not be " \
                    + "simplified")
            return None
        else:
            if not cleaned_line_groups:
                log.debug("Skipping offset polygon: no polygons left after " \
                        + "intersection simplification")
            # remove all groups with a toggled direction
            self_is_outer = self.is_outer()
            groups = []
            for lines in cleaned_line_groups:
                if callback and callback():
                    return None
                group = Polygon(self.plane)
                for line in lines:
                    group.append(line)
                if group.is_outer() != self_is_outer:
                    # We ignore groups that changed the direction. These
                    # parts of the original group are flipped due to the
                    # offset.
                    log.debug("Ignoring reversed polygon: %s / %s" % \
                            (self.get_area(), group.get_area()))
                    continue
                # Remove polygons that should be inside the original,
                # but due to float inaccuracies they are not.
                if ((self.is_outer() and (offset < 0)) \
                        or (not self.is_outer() and (offset > 0))) \
                        and (not self.is_polygon_inside(group)):
                    log.debug("Ignoring inaccurate polygon: %s / %s" \
                            % (self.get_area(), group.get_area()))
                    continue
                groups.append(group)
            if not groups:
                log.debug("Skipping offset polygon: toggled polygon removed")
            # remove all polygons that are within other polygons
            result = []
            for group in groups:
                inside = False
                for group_test in groups:
                    if callback and callback():
                        return None
                    if group_test is group:
                        continue
                    if group_test.is_polygon_inside(group):
                        inside = True
                if not inside:
                    result.append(group)
            if not result:
                log.debug("Skipping offset polygon: polygon is inside of " \
                        + "another one")
            return result

    def get_offset_polygons_old(self, offset):
        def get_parallel_line(line, offset):
            if offset == 0:
                return Line(line.p1, line.p2)
            else:
                cross_offset = line.dir.cross(self.plane.n).normalized().mul(offset)
                # Prolong the line at the beginning and at the end - to allow
                # overlaps. Use factor "2" to take care for star-like structure
                # where a complete convex triangle would get cropped (two lines
                # get lost instead of just one). Use the "abs" value to
                # compensate negative offsets.
                in_line = line.dir.mul(2 * abs(offset))
                return Line(line.p1.add(cross_offset).sub(in_line),
                        line.p2.add(cross_offset).add(in_line))
        def do_lines_intersection(l1, l2):
            """ calculate the new intersection between two neighbouring lines
            """
            # TODO: use Line.get_intersection instead of the code below
            if l1.p2 == l2.p1:
                # intersection is already fine
                return
            if (l1.p1 is None) or (l2.p1 is None):
                # one line was already marked as obsolete
                return
            x1, x2, x3, x4 = l2.p1, l2.p2, l1.p1, l1.p2
            a = x2.sub(x1)
            b = x4.sub(x3)
            c = x3.sub(x1)
            # see http://mathworld.wolfram.com/Line-LineIntersection.html (24)
            try:
                factor = c.cross(b).dot(a.cross(b)) / a.cross(b).normsq
            except ZeroDivisionError:
                l2.p1 = None
                return
            if not (0 <= factor < 1):
                # The intersection is always supposed to be within p1 and p2.
                l2.p1 = None
            else:
                intersection = x1.add(a.mul(factor))
                if Line(l1.p1, intersection).dir != l1.dir:
                    # Remove lines that would change their direction due to the
                    # new intersection. These are usually lines that become
                    # obsolete due to a more favourable intersection of the two
                    # neighbouring lines. This appears at small corners.
                    l1.p1 = None
                elif Line(intersection, l2.p2).dir != l2.dir:
                    # see comment above
                    l2.p1 = None
                elif l1.p1 == intersection:
                    # remove invalid lines (zero length)
                    l1.p1 = None
                elif l2.p2 == intersection:
                    # remove invalid lines (zero length)
                    l2.p1 = None
                else:
                    # shorten both lines according to the new intersection
                    l1.p2 = intersection
                    l2.p1 = intersection
        def simplify_polygon_intersections(lines):
            finished = False
            new_group = lines[:]
            while not finished:
                if len(new_group) > 1:
                    # Calculate new intersections for each pair of adjacent
                    # lines.
                    for index in range(len(new_group)):
                        if (index == 0) and (not self.is_closed):
                            # skip the first line if the group is not closed
                            continue
                        # this also works for index==0 (closed groups)
                        l1 = new_group[index - 1]
                        l2 = new_group[index]
                        do_lines_intersection(l1, l2)
                # Remove all lines that were marked as obsolete during
                # intersection calculation.
                clean_group = [line for line in new_group
                        if not line.p1 is None]
                finished = len(new_group) == len(clean_group)
                if (len(clean_group) == 1) and self.is_closed:
                    new_group = []
                    finished = True
                else:
                    new_group = clean_group
            # remove all non-adjacent intersecting lines (this splits the group)
            if len(new_group) > 0:
                group_starts = []
                index1 = 0
                while index1 < len(new_group):
                    index2 = 0
                    while index2 < len(new_group):
                        index_distance = min(abs(index2 - index1), \
                                abs(len(new_group) - (index2 - index1))) 
                        # skip neighbours
                        if index_distance > 1:
                            line1 = new_group[index1]
                            line2 = new_group[index2]
                            intersection, factor = line1.get_intersection(line2)
                            if intersection and (intersection != line1.p1) \
                                    and (intersection != line1.p2):
                                del new_group[index1]
                                new_group.insert(index1,
                                        Line(line1.p1, intersection))
                                new_group.insert(index1 + 1,
                                        Line(intersection, line1.p2))
                                # Shift all items in "group_starts" by one if
                                # they reference a line whose index changed.
                                for i in range(len(group_starts)):
                                    if group_starts[i] > index1:
                                        group_starts[i] += 1
                                if not index1 + 1 in group_starts:
                                    group_starts.append(index1 + 1)
                                # don't update index2 -> maybe there are other hits
                            elif intersection and (intersection == line1.p1):
                                if not index1 in group_starts:
                                    group_starts.append(index1)
                                index2 += 1
                            else:
                                index2 += 1
                        else:
                            index2 += 1
                    index1 += 1
                # The lines intersect each other
                # We need to split the group.
                if len(group_starts) > 0:
                    group_starts.sort()
                    groups = []
                    last_start = 0
                    for group_start in group_starts:
                        groups.append(new_group[last_start:group_start])
                        last_start = group_start
                    # Add the remaining lines to the first group or as a new
                    # group.
                    if groups[0][0].p1 == new_group[-1].p2:
                        groups[0] = new_group[last_start:] + groups[0]
                    else:
                        groups.append(new_group[last_start:])
                    # try to find open groups that can be combined
                    combined_groups = []
                    for index, current_group in enumerate(groups):
                        # Check if the group is not closed: try to add it to
                        # other non-closed groups.
                        if current_group[0].p1 == current_group[-1].p2:
                            # a closed group
                            combined_groups.append(current_group)
                        else:
                            # the current group is open
                            for other_group in groups[index + 1:]:
                                if other_group[0].p1 != other_group[-1].p2:
                                    # This group is also open - a candidate
                                    # for merging?
                                    if other_group[0].p1 == current_group[-1].p2:
                                        current_group.reverse()
                                        for line in current_group:
                                            other_group.insert(0, line)
                                        break
                                    if other_group[-1].p2 == current_group[0].p1:
                                        other_group.extend(current_group)
                                        break
                            else:
                                # not suitable open group found
                                combined_groups.append(current_group)
                    return combined_groups
                else:
                    # just return one group without intersections
                    return [new_group]
            else:
                return None
        new_lines = []
        for line in self.get_lines():
            new_lines.append(get_parallel_line(line, offset))
        cleaned_line_groups = simplify_polygon_intersections(new_lines)
        if cleaned_line_groups is None:
            return None
        else:
            # remove all groups with a toggled direction
            self_is_outer = self.is_outer()
            groups = []
            for lines in cleaned_line_groups:
                group = Polygon(self.plane)
                for line in lines:
                    group.append(line)
                if group.is_outer() == self_is_outer:
                    # We ignore groups that changed the direction. These
                    # parts of the original group are flipped due to the
                    # offset.
                    groups.append(group)
            return groups

    def get_cropped_polygons(self, minx, maxx, miny, maxy, minz, maxz):
        """ crop a line group according to a 3d bounding box

        The result is a list of Polygons, since the bounding box can possibly
        break the original line group into several non-connected pieces.
        """
        new_groups = []
        for line in self.get_lines():
            new_line = None
            if line.is_completely_inside(minx, maxx, miny, maxy, minz, maxz):
                new_line = line
            else:
                cropped_line = line.get_cropped_line(minx, maxx, miny, maxy,
                        minz, maxz)
                if not cropped_line is None:
                    new_line = cropped_line
            # add the new line to one of the line groups
            if not new_line is None:
                # try to find a suitable line group
                for new_group in new_groups:
                    try:
                        new_group.append(new_line)
                        break
                    except ValueError:
                        # the line did not fit to this group (segment is broken)
                        pass
                else:
                    # no suitable group was found - we create a new one
                    new_group = Polygon(self.plane)
                    new_group.append(new_line)
                    new_groups.append(new_group)
        if len(new_groups) > 0:
            return new_groups
        else:
            return None

    def get_plane_projection(self, plane):
        if plane == self.plane:
            return self
        elif plane.n.dot(self.plane.n) == 0:
            log.warn("Polygon projection onto plane: orthogonal projection " \
                    + "is not possible")
            return None
        else:
            result = Polygon(plane)
            for line in self.get_lines():
                p1 = plane.get_point_projection(line.p1)
                p2 = plane.get_point_projection(line.p2)
                result.append(Line(p1, p2))
            # check if the projection would revert the direction of the polygon
            if plane.n.dot(self.plane.n) < 0:
                result.reverse_direction()
            return result

    def is_overlap(self, other):
        for line1 in self.get_lines():
            for line2 in other.get_lines():
                cp, dist = line1.get_intersection(line2)
                if not cp is None:
                    return True
        return False

    def union(self, other):
        """ This "union" of two polygons only works for polygons without
        shared edges. TODO: fix the issues of shared edges!
        """
        # don't import earlier to avoid circular imports
        from pycam.Geometry.Model import ContourModel
        # check if one of the polygons is completely inside of the other
        if self.is_polygon_inside(other):
            return [self]
        if other.is_polygon_inside(self):
            return [other]
        # check if there is any overlap at all
        if not self.is_overlap(other):
            # no changes
            return [self, other]
        contour = ContourModel(self.plane)
        def get_outside_lines(poly1, poly2):
            result = []
            for line in poly1.get_lines():
                collisions = []
                for o_line in poly2.get_lines():
                    cp, dist = o_line.get_intersection(line)
                    if (not cp is None) and (0 < dist < 1):
                        collisions.append((cp, dist))
                # sort the collisions according to the distance
                collisions.append((line.p1, 0))
                collisions.append((line.p2, 1))
                collisions.sort(key=lambda (cp, dist): dist)
                for index in range(len(collisions) - 1):
                    p1 = collisions[index][0]
                    p2 = collisions[index + 1][0]
                    if p1.sub(p2).norm < epsilon:
                        # ignore zero-length lines
                        continue
                    # Use the middle between p1 and p2 to check the
                    # inner/outer state.
                    p_middle = p1.add(p2).div(2)
                    p_inside = poly2.is_point_inside(p_middle) \
                            and not poly2.is_point_on_outline(p_middle)
                    if not p_inside:
                        result.append(Line(p1, p2))
            return result
        outside_lines = []
        outside_lines.extend(get_outside_lines(self, other))
        outside_lines.extend(get_outside_lines(other, self))
        for line in outside_lines:
            contour.append(line)
        # fix potential overlapping at the beginning and end of each polygon
        result = []
        for poly in contour.get_polygons():
            if not poly.is_closed:
                lines = poly.get_lines()
                line1 = lines[-1]
                line2 = lines[0]
                if (line1.dir == line2.dir) \
                        and (line1.is_point_inside(line2.p1)):
                    # remove the last point and define the polygon as closed
                    poly._points.pop(-1)
                    poly.is_closed = True
            result.append(poly)
        return result

    def split_line(self, line):
        outer = []
        inner = []
        # project the line onto the polygon's plane
        proj_line = self.plane.get_line_projection(line)
        intersections = []
        for pline in self.get_lines():
            cp, d = proj_line.get_intersection(pline)
            if cp:
                intersections.append((cp, d))
        # sort the intersections
        intersections.sort(key=lambda (cp, d): d)
        intersections.insert(0, (proj_line.p1, 0))
        intersections.append((proj_line.p2, 1))
        get_original_point = lambda d: line.p1.add(line.vector.mul(d))
        for index in range(len(intersections) - 1):
            p1, d1 = intersections[index]
            p2, d2 = intersections[index + 1]
            if p1 != p2:
                middle = p1.add(p2).div(2)
                new_line = Line(get_original_point(d1), get_original_point(d2))
                if self.is_point_inside(middle):
                    inner.append(new_line)
                else:
                    outer.append(new_line)
        return (inner, outer)

