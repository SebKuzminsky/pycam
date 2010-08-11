# -*- coding: utf-8 -*-
"""
$Id$

Copyright 2008-2010 Lode Leroy
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


from pycam.Geometry.Point import Point
from pycam.Geometry.utils import number, epsilon


class BaseCutter(object):
    id = 0
    vertical = Point(0, 0, -1)

    def __init__(self, radius, location=None, height=None):
        if location is None:
            location = Point(0, 0, 0)
        if height is None:
            height = 10
        radius = number(radius)
        self.height = number(height)
        self.id = BaseCutter.id
        BaseCutter.id += 1
        self.radius = radius
        self.radiussq = radius ** 2
        self.required_distance = 0
        self.distance_radius = self.radius
        self.distance_radiussq = self.distance_radius ** 2
        # self.minx, self.maxx, self.miny and self.maxy are defined as
        # properties below
        self.shape = {}
        self.moveto(location)

    def _get_minx(self):
        return self.location.x - self.distance_radius
    minx = property(_get_minx)

    def _get_maxx(self):
        return self.location.x + self.distance_radius
    maxx = property(_get_maxx)

    def _get_miny(self):
        return self.location.y - self.distance_radius
    miny = property(_get_miny)

    def _get_maxy(self):
        return self.location.y + self.distance_radius
    maxy = property(_get_maxy)

    def __repr__(self):
        return "BaseCutter"

    def __cmp__(self, other):
        """ Compare Cutters by shape and size (ignoring the location)
        This function should be overridden by subclasses, if they describe
        cutters with a shape depending on more than just the radius.
        See the ToroidalCutter for an example.
        """
        if self.__class__ == other.__class__:
            return cmp(self.radius, other.radius)
        else:
            # just return a string comparison
            return cmp(str(self), str(other))

    def set_required_distance(self, value):
        if value >= 0:
            self.required_distance = number(value)
            self.distance_radius = self.radius + self.get_required_distance()
            self.distance_radiussq = self.distance_radius * self.distance_radius

    def get_required_distance(self):
        return self.required_distance

    def moveto(self, location):
        self.location = location
        for shape, set_pos_func in self.shape.values():
            set_pos_func(location.x, location.y, location.z)

    def intersect(self, direction, triangle):
        raise NotImplementedError("Inherited class of BaseCutter does not " \
                + "implement the required function 'intersect'.")

    def drop(self, triangle):
        # check bounding box collision
        if self.minx > triangle.maxx + epsilon:
            return None
        if self.maxx < triangle.minx - epsilon:
            return None
        if self.miny > triangle.maxy + epsilon:
            return None
        if self.maxy < triangle.miny - epsilon:
            return None

        # check bounding circle collision
        c = triangle.middle
        if (c.x - self.location.x) ** 2 + (c.y - self.location.y) ** 2 \
                > (self.distance_radiussq + 2 * self.distance_radius \
                    * triangle.radius + triangle.radiussq) + epsilon:
            return None

        (cl, d)= self.intersect(BaseCutter.vertical, triangle)
        return cl

