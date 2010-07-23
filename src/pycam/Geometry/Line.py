# -*- coding: utf-8 -*-
"""
$Id$

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

from pycam.Geometry import TransformableContainer
from pycam.Geometry.Point import Point
from pycam.Geometry.utils import epsilon
import pycam.Geometry.Matrix as Matrix
import math


try:
    import OpenGL.GL as GL
    GL_enabled = True
except ImportError:
    GL_enabled = False


class Line(TransformableContainer):
    id = 0

    def __init__(self, p1, p2):
        self.id = Line.id
        Line.id += 1
        self.p1 = p1
        self.p2 = p2
        self._dir = None
        self._len = None

    def __repr__(self):
        return "Line<%g,%g,%g>-<%g,%g,%g>" % (self.p1.x, self.p1.y, self.p1.z,
                self.p2.x, self.p2.y, self.p2.z)

    def __cmp__(self, other):
        """ Two lines are equal if both pairs of points are at the same
        locations.
        Otherwise the result is based on the comparison of the first and then
        the second point.
        """
        if self.__class__ == other.__class__:
            if (self.p1 == other.p1) and (self.p2 == other.p2):
                return 0
            elif self.p1 != other.p1:
                return cmp(self.p1, other.p1)
            else:
                return cmp(self.p2, other.p2)
        else:
            return cmp(str(self), str(other))

    def next(self):
        yield self.p1
        yield self.p2

    def reset_cache(self):
        self._dir = None
        self._len = None

    def dir(self):
        if self._dir is None:
            self._dir = self.p2.sub(self.p1)
            self._dir.normalize()
        return self._dir

    def len(self):
        if self._len is None:
            self._len = self.p2.sub(self.p1).norm()
        return self._len

    def point(self, l):
        return self.p1.add(self.dir().mul(l*self.len()))

    def closest_point(self, p):
        v = self.dir()
        l = self.p1.dot(v) - p.dot(v)
        return self.p1.sub(v.mul(l))

    def dist_to_point_sq(self, p):
        return p.sub(self.closest_point(p)).normsq()

    def dist_to_point(self, p):
        return math.sqrt(self.dist_to_point_sq(p))
    
    def is_point_in_line(self, p):
        return abs(p.sub(self.p1).norm() + p.sub(self.p2).norm() - self.len()) < epsilon

    def minx(self):
        return min(self.p1.x, self.p2.x)

    def miny(self):
        return min(self.p1.y, self.p2.y)

    def minz(self):
        return min(self.p1.z, self.p2.z)

    def maxx(self):
        return max(self.p1.x, self.p2.x)

    def maxy(self):
        return max(self.p1.y, self.p2.y)

    def maxz(self):
        return max(self.p1.z, self.p2.z)

    def to_OpenGL(self):
        if GL_enabled:
            GL.glBegin(GL.GL_LINES)
            GL.glVertex3f(self.p1.x, self.p1.y, self.p1.z)
            GL.glVertex3f(self.p2.x, self.p2.y, self.p2.z)
            # (optional) draw arrows for visualizing the direction of each line
            if False:
                line = (self.p2.x - self.p1.x, self.p2.y - self.p1.y)
                if line[0] == 0:
                    ortho = (1.0, 0.0)
                elif line[1] == 0:
                    ortho = (0.0, 1.0)
                else:
                    ortho = (1.0 / line[0], -1.0 / line[1])
                line_size = math.sqrt((line[0] ** 2) + (line[1] ** 2))
                ortho_size = math.sqrt((ortho[0] ** 2) + (ortho[1] ** 2))
                ortho_dest_size = line_size / 10.0
                ortho = (ortho[0] * ortho_dest_size / ortho_size,
                        ortho[1] * ortho_dest_size / ortho_size)
                line_back = (-line[0] * ortho_dest_size / line_size,
                        -line[1] * ortho_dest_size / line_size)
                p3 = (self.p2.x + ortho[0] + line_back[0],
                        self.p2.y + ortho[1] + line_back[1], self.p2.z)
                p4 = (self.p2.x - ortho[0] + line_back[0],
                        self.p2.y - ortho[1] + line_back[1], self.p2.z)
                GL.glVertex3f(p3[0], p3[1], p3[2])
                GL.glVertex3f(self.p2.x, self.p2.y, self.p2.z)
                GL.glVertex3f(p4[0], p4[1], p4[2])
                GL.glVertex3f(self.p2.x, self.p2.y, self.p2.z)
            GL.glEnd()

    def get_points(self):
        return (self.p1, self.p2)

    def get_intersection(self, line):
        """ Get the point of intersection between two lines. Intersections
        outside the length of these lines are ignored.
        Returns None if no valid intersection was found.
        """
        x1, x2, x3, x4 = self.p1, self.p2, line.p1, line.p2
        a = x2.sub(x1)
        b = x4.sub(x3)
        c = x3.sub(x1)
        # see http://mathworld.wolfram.com/Line-LineIntersection.html (24)
        try:
            factor = c.cross(b).dot(a.cross(b)) / a.cross(b).normsq()
        except ZeroDivisionError:
            # lines are parallel
            # check if they are _one_ line
            if a.cross(c).normsq() != 0:
                # the lines are parallel with a disctance
                return None
            # the lines are on one straight
            if self.is_point_in_line(x3):
                return x3
            elif self.is_point_in_line(x4):
                return x4
            elif line.is_point_in_line(x1):
                return x1
            elif line.is_point_in_line(x2):
                return x2
            else:
                return None
        if 0 <= factor <= 1:
            intersection = x1.add(a.mul(factor))
            # check if the intersection is between x3 and x4
            if (min(x3.x, x4.x) <= intersection.x <= max(x3.x, x4.x)) \
                    and (min(x3.y, x4.y) <= intersection.y <= max(x3.y, x4.y)) \
                    and (min(x3.z, x4.z) <= intersection.z <= max(x3.z, x4.z)):
                return intersection
            else:
                # intersection outside of the length of line(x3, x4)
                return None
        else:
            # intersection outside of the length of line(x1, x2)
            return None


class LineGroup(TransformableContainer):

    def __init__(self, offset_matrix=None):
        super(LineGroup, self).__init__()
        self._offset_matrix = offset_matrix
        self._lines = []
        self._line_offsets = None
        self._is_closed = False
        self.maxx = None
        self.minx = None
        self.maxy = None
        self.miny = None
        self.maxz = None
        self.minz = None

    def append(self, line):
        if not self.is_connectable(line):
            raise ValueError("This line does not fit to the line group")
        else:
            if not self._lines or (self._lines[-1].p2 == line.p1):
                self._lines.append(line)
            else:
                self._lines.insert(0, line)
            self._update_limits(line)
            self._is_closed = self._lines[0].p1 == self._lines[-1].p2

    def is_connectable(self, line):
        if self._is_closed:
            return False
        elif not self._lines:
            # empty line groups can be connected with any line
            return True
        elif line.p1 == self._lines[-1].p2:
            return True
        elif line.p2 == self._lines[0].p1:
            return True
        else:
            return False

    def next(self):
        for line in self._lines:
            yield line

    def _init_line_offsets(self):
        if self._lines and self._line_offsets is None:
            self._line_offsets = []
            offset_matrix = self.get_offset_matrix()
            # initialize all offset vectors (if necessary)
            for line in self._lines:
                line_dir = line.dir()
                vector = (line_dir.x, line_dir.y, line_dir.z)
                offset_vector = Matrix.multiply_vector_matrix(vector, offset_matrix)
                offset_point = Point(offset_vector[0], offset_vector[1], offset_vector[2])
                self._line_offsets.append(Line(line.p1, line.p1.add(offset_point)))

    def transform_by_matrix(self, matrix, transformed_list):
        if self._lines:
            offset_matrix = self.get_offset_matrix()
            # initialize all offset vectors (if necessary)
            self._init_line_offsets()
        super(LineGroup, self).transform_by_matrix(matrix, transformed_list)
        # transform all offset vectors
        if self._lines:
            for offset in self._line_offsets:
                if not id(offset) in transformed_list:
                    offset.transform_by_matrix(matrix, transformed_list)
            # transform the offset vector of this line group
            self._offset_matrix = Matrix.multiply_matrix_matrix(matrix, offset_matrix)

    def get_lines(self):
        return self._lines[:]

    def to_OpenGL(self):
        for line in self._lines:
            line.to_OpenGL()

    def get_offset_matrix(self):
        if not self._offset_matrix is None:
            return self._offset_matrix
        elif not self._lines:
            return None
        else:
            # assume that this line group forms a straight line
            offset_matrix = None
            # check if all lines are in one specific layer (z/y/x)
            # return the respective axis rotation matrix
            z_start_value = self._lines[0].minz()
            on_z_level = [True for line in self._lines
                    if line.minz() == line.maxz() == z_start_value]
            if len(on_z_level) == len(self._lines):
                offset_matrix = Matrix.TRANSFORMATIONS["z"]
            else:
                y_start_value = self._lines[0].y
                on_y_level = [True for line in self._lines
                        if line.miny() == line.maxy() == y_start_value]
                if len(on_y_level) == len(self._lines):
                    offset_matrix = Matrix.TRANSFORMATIONS["y"]
                else:
                    x_start_value = self._lines[0].x
                    on_x_level = [True for line in self._lines
                            if line.minx() == line.maxx() == x_start_value]
                    if len(on_x_level) == len(self._lines):
                        offset_matrix = Matrix.TRANSFORMATIONS["x"]
            # store the result to avoid re-calculation
            self._offset_matrix = offset_matrix
            return offset_matrix

    def _update_limits(self, line):
        if self.minx is None:
            self.minx = line.minx()
            self.maxx = line.maxx()
            self.miny = line.miny()
            self.maxy = line.maxy()
            self.minz = line.minz()
            self.maxz = line.maxz()
        else:
            self.minx = min(self.minx, line.minx())
            self.maxx = max(self.maxx, line.maxx())
            self.miny = min(self.miny, line.miny())
            self.maxy = max(self.maxy, line.maxy())
            self.minz = min(self.minz, line.minz())
            self.maxz = max(self.maxz, line.maxz())

    def reset_cache(self):
        if not self._lines:
            self.minx, self.miny, self.minz = None, None, None
            self.maxx, self.maxy, self.maxz = None, None, None
        else:
            first = self._lines[0]
            # initialize the start limit with valid values
            self.minx = first.minx()
            self.maxx = first.maxx()
            self.miny = first.miny()
            self.maxy = first.maxy()
            self.minz = first.minz()
            self.maxz = first.maxz()
            # update the limit for each line
            for line in self._lines:
                self._update_limits(line)

    def get_offset_line_group(self, offset):
        def get_parallel_line(line, line_offset, offset):
            if offset == 0:
                return Line(line.p1, line.p2)
            else:
                cross_offset = line_offset.dir().mul(offset)
                # Prolong the line at the beginning and at the end - to allow
                # overlaps.
                in_line = line.dir().mul(offset)
                return Line(line.p1.add(cross_offset).sub(in_line),
                        line.p2.add(cross_offset).add(in_line))
        def do_lines_intersection(l1, l2):
            """ calculate the new intersection between two neighbouring lines
            """
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
                factor = c.cross(b).dot(a.cross(b)) / a.cross(b).normsq()
            except ZeroDivisionError:
                l2.p1 = None
                return
            if not (0 <= factor < 1):
                # The intersection is always supposed to be within p1 and p2.
                l2.p1 = None
            else:
                intersection = x1.add(a.mul(factor))
                if Line(l1.p1, intersection).dir() != l1.dir():
                    # Remove lines that would change their direction due to the
                    # new intersection. These are usually lines that become
                    # obsolete due to a more favourable intersection of the two
                    # neighbouring lines. This appears at small corners.
                    l1.p1 = None
                elif Line(intersection, l2.p2).dir() != l2.dir():
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
        def simplify_line_group_intersections(lines):
            finished = False
            new_group = lines[:]
            while not finished:
                if len(new_group) > 1:
                    # Calculate new intersections for each pair of adjacent
                    # lines.
                    for index in range(len(new_group)):
                        if (index == 0) and (not self._is_closed):
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
                if (len(clean_group) == 1) and self._is_closed:
                    new_group = []
                    finished = True
                else:
                    new_group = clean_group
            return new_group
        if self.get_offset_matrix() is None:
            # we can't get an offset line group if the normal is invalid
            return self
        else:
            # initialize the line offsets if necessary
            self._init_line_offsets()
            new_lines = []
            for line, line_offset in zip(self._lines, self._line_offsets):
                new_lines.append(get_parallel_line(line, line_offset, offset))
            cleaned_line_group = simplify_line_group_intersections(new_lines)
            if len(cleaned_line_group) == 0:
                return None
            else:
                group = LineGroup(self.get_offset_matrix())
                for line in cleaned_line_group:
                    group.append(line)
                return group

