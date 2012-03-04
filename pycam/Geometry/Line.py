# -*- coding: utf-8 -*-
"""
$Id$

Copyright 2008-2009 Lode Leroy
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

from pycam.Geometry import TransformableContainer, IDGenerator
from pycam.Geometry.PointUtils import *
from pycam.Geometry.Plane import Plane
from pycam.Geometry.utils import epsilon, sqrt
# OpenGLTools will be imported later, if necessary
#import pycam.Gui.OpenGLTools


try:
    import OpenGL.GL as GL
    GL_enabled = True
except ImportError:
    GL_enabled = False


class Line(IDGenerator, TransformableContainer):

    __slots__ = ["id", "p1", "p2", "_vector", "_minx", "_maxx", "_miny",
            "_maxy", "_minz", "_maxz"]

    def __init__(self, p1, p2):
        super(Line, self).__init__()
        self.p1 = p1
        self.p2 = p2
        self.reset_cache()

    def copy(self):
        return self.__class__(self.p1, self.p2)

    @property
    def vector(self):
        if self._vector is None:
            self._vector = psub(self.p2, self.p1)
            #self._vector = self.p2.sub(self.p1)
        return self._vector

    @property
    def dir(self):
        return pnormalized(self.vector)
        #return self.vector.normalized()

    @property
    def len(self):
        return pnorm(self.vector)
        #return self.vector.norm

    @property
    def minx(self):
        if self._minx is None:
            self._minx = min(self.p1[0], self.p2[0])
        return self._minx

    @property
    def maxx(self):
        if self._maxx is None:
            self._maxx = max(self.p1[0], self.p2[0])
        return self._maxx

    @property
    def miny(self):
        if self._miny is None:
            self._miny = min(self.p1[1], self.p2[1])
        return self._miny

    @property
    def maxy(self):
        if self._maxy is None:
            self._maxy = max(self.p1[1], self.p2[1])
        return self._maxy

    @property
    def minz(self):
        if self._minz is None:
            self._minz = min(self.p1[2], self.p2[2])
        return self._minz

    @property
    def maxz(self):
        if self._maxz is None:
            self._maxz = max(self.p1[2], self.p2[2])
        return self._maxz

    def __repr__(self):
        return "Line<%g,%g,%g>-<%g,%g,%g>" % (self.p1[0], self.p1[1], self.p1[2],
                self.p2[0], self.p2[1], self.p2[2])

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
        yield "p1"
        #yield self.p1
        #yield lambda x: self.p2 = x
        yield "p2"

    def get_children_count(self):
        # a line always contains two points
        return 2

    def reset_cache(self):
        self._vector = None
        self._minx = None
        self._maxx = None
        self._miny = None
        self._maxy = None
        self._minz = None
        self._maxz = None

    def get_points(self):
        return (self.p1, self.p2)

    def point_with_length_multiply(self, l):
        return padd(self.p1, pmul(self.dir, l*self.len))
        #return self.p1.add(self.dir.mul(l*self.len))

    def get_length_line(self, length):
        """ return a line with the same direction and the specified length
        """
        return Line(self.p1, padd(self.p1, pmul(self.dir, length)))
        #return Line(self.p1, self.p1.add(self.dir.mul(length)))

    def closest_point(self, p):
        v = self.dir
        if v is None:
            # for zero-length lines
            return self.p1
        l = pdot(self.p1, v) - pdot(p, v)
        #l = self.p1.dot(v) - p.dot(v)
        return psub(self.p1, pmul(v, l))
        #return self.p1.sub(v.mul(l))

    def dist_to_point_sq(self, p):
        return pnormsq(psub(p, self.closes_point(p)))
        #return p.sub(self.closest_point(p)).normsq

    def dist_to_point(self, p):
        return sqrt(self.dist_to_point_sq(p))
    
    def is_point_inside(self, p):
        if (p == self.p1) or (p == self.p2):
            # these conditions are not covered by the code below
            return True
            
        dir1 = pnormalized(psub(p, self.p1))
        #dir1 = p.sub(self.p1).normalized()
        dir2 = pnormalized(psub(self.p2, p))
        #dir2 = self.p2.sub(p).normalized()
        # True if the two parts of the line have the same direction or if the
        # point is self.p1 or self.p2.
        return (dir1 == dir2 == self.dir) or (dir1 is None) or (dir2 is None)

    def to_OpenGL(self, color=None, show_directions=False):
        if not GL_enabled:
            return
        if not color is None:
            GL.glColor4f(*color)
        GL.glBegin(GL.GL_LINES)
        GL.glVertex3f(self.p1[0], self.p1[1], self.p1[2])
        GL.glVertex3f(self.p2[0], self.p2[1], self.p2[2])
        GL.glEnd()
        # (optional) draw a cone for visualizing the direction of each line
        if show_directions and (self.len > 0):
            # We can't import OpenGLTools in the header - otherwise server
            # mode without GTK will break.
            import pycam.Gui.OpenGLTools
            pycam.Gui.OpenGLTools.draw_direction_cone(self.p1, self.p2)

    def get_intersection(self, line, infinite_lines=False):
        """ Get the point of intersection between two lines. Intersections
        outside the length of these lines are ignored.
        Returns (None, None) if no valid intersection was found.
        Otherwise the result is (CollisionPoint, distance). Distance is between
        0 and 1.
        """
        x1, x2, x3, x4 = self.p1, self.p2, line.p1, line.p2
        a = psub(x2, x1)
        #a = x2.sub(x1)
        b = psub(x4, x3)
        #b = x4.sub(x3)
        c = psub(x3, x1)
        #c = x3.sub(x1)
        # see http://mathworld.wolfram.com/Line-LineIntersection.html (24)
        try:
            factor = pdot(pcross(c, b), pcross(a, b)) / pnormsq(pcross(a, b))
            #factor = c.cross(b).dot(a.cross(b)) / a.cross(b).normsq
        except ZeroDivisionError:
            # lines are parallel
            # check if they are _one_ line
            #if a.cross(c).norm != 0:
            if pnorm(pcross(a,c)) != 0:
                # the lines are parallel with a distance
                return None, None
            # the lines are on one straight
            candidates = []
            if self.is_point_inside(x3):
                candidates.append((x3, pnorm(c) / pnorm(a)))
            elif self.is_point_inside(x4):
                candidates.append((x4, pnorm(psub(line.p2, self.p1)) / pnorm(a)))
                #candidates.append((x4, line.p2.sub(self.p1).norm / a.norm))
            elif line.is_point_inside(x1):
                candidates.append((x1, 0))
            elif line.is_point_inside(x2):
                candidates.append((x2, 1))
            else:
                return None, None
            # return the collision candidate with the lowest distance
            candidates.sort(key=lambda (cp, dist): dist)
            return candidates[0]
        if infinite_lines or (-epsilon <= factor <= 1 + epsilon):
            intersection = padd(x1, pmul(a, factor))
            #intersection = x1.add(a.mul(factor))
            # check if the intersection is between x3 and x4
            if infinite_lines:
                return intersection, factor
            elif (min(x3[0], x4[0]) - epsilon <= intersection[0] <= max(x3[0], x4[0]) + epsilon) \
                    and (min(x3[1], x4[1]) - epsilon <= intersection[1] <= max(x3[1], x4[1]) + epsilon) \
                    and (min(x3[2], x4[2]) - epsilon <= intersection[2] <= max(x3[2], x4[2]) + epsilon):
                return intersection, factor
            else:
                # intersection outside of the length of line(x3, x4)
                return None, None
        else:
            # intersection outside of the length of line(x1, x2)
            return None, None

    def get_cropped_line(self, minx, maxx, miny, maxy, minz, maxz):
        if self.is_completely_inside(minx, maxx, miny, maxy, minz, maxz):
            return self
        elif self.is_completely_outside(minx, maxx, miny, maxy, minz, maxz):
            return None
        else:
            # the line needs to be cropped
            # generate the six planes of the cube for possible intersections
            minp = (minx, miny, minz)
            maxp = (maxx, maxy, maxz)
            planes = [
                    Plane(minp, (1, 0, 0)),
                    Plane(minp, (0, 1, 0)),
                    Plane(minp, (0, 0, 1)),
                    Plane(maxp, (1, 0, 0)),
                    Plane(maxp, (0, 1, 0)),
                    Plane(maxp, (0, 0, 1)),
            ]
            # calculate all intersections
            intersections = [plane.intersect_point(self.dir, self.p1)
                    for plane in planes]
            # remove all intersections outside the box and outside the line
            valid_intersections = [(cp, dist) for cp, dist in intersections
                    if cp and (-epsilon <= dist <= self.len + epsilon) and \
                            cp.is_inside(minx, maxx, miny, maxy, minz, maxz)]
            # sort the intersections according to their distance to self.p1
            valid_intersections.sort(
                    cmp=lambda (cp1, l1), (cp2, l2): cmp(l1, l2))
            # Check if p1 is within the box - otherwise use the closest
            # intersection. The check for "valid_intersections" is necessary
            # to prevent an IndexError due to floating point inaccuracies.
            if self.p1.is_inside(minx, maxx, miny, maxy, minz, maxz) \
                    or not valid_intersections:
                new_p1 = self.p1
            else:
                new_p1 = valid_intersections[0][0]
            # Check if p2 is within the box - otherwise use the intersection
            # most distant from p1.
            if self.p2.is_inside(minx, maxx, miny, maxy, minz, maxz) \
                    or not valid_intersections:
                new_p2 = self.p2
            else:
                new_p2 = valid_intersections[-1][0]
            if new_p1 == new_p2:
                # no real line
                return None
            else:
                return Line(new_p1, new_p2)

