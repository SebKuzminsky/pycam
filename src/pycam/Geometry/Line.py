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

try:
    import OpenGL.GL as GL
    GL_enabled = True
except ImportError:
    GL_enabled = False


import math


class Line:
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

