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

import math
def _is_near(x, y):
    return abs(x - y) < 1e-6


class Point:
    id = 0

    def __init__(self, x, y, z):
        self.id = Point.id
        Point.id += 1
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)
        self._norm = None
        self._normsq = None

    def __repr__(self):
        return "Point%d<%g,%g,%g>" % (self.id, self.x, self.y, self.z)

    def __cmp__(self, other):
        """ Two points are equal if all dimensions are identical.
        Otherwise the result is based on the individual x/y/z comparisons.
        """
        if self.__class__ == other.__class__:
            if (_is_near(self.x, other.x)) and (_is_near(self.y, other.y)) \
                    and (_is_near(self.z, other.z)):
                return 0
            elif not _is_near(self.x, other.x):
                return cmp(self.x, other.x)
            elif not _is_near(self.y, other.y):
                return cmp(self.y, other.y)
            else:
                return cmp(self.z, other.z)
        else:
            return cmp(str(self), str(other))

    def mul(self, c):
        return Point(self.x * c, self.y * c, self.z * c)

    def div(self, c):
        return Point(self.x / c, self.y / c, self.z / c)

    def add(self, p):
        return Point(self.x + p.x, self.y + p.y, self.z + p.z)

    def sub(self, p):
        return Point(self.x - p.x, self.y - p.y, self.z - p.z)

    def dot(self, p):
        return self.x * p.x + self.y * p.y + self.z * p.z

    def cross(self, p):
        return Point(self.y * p.z - p.y * self.z, p.x * self.z - self.x * p.z,
                self.x * p.y - p.x * self.y)

    def normsq(self):
        if self._normsq is None:
            self._normsq = self.dot(self)
        return self._normsq

    def norm(self):
        if self._norm is None:
            self._norm = math.sqrt(self.normsq())
        return self._norm

    def normalize(self):
        n = self.norm()
        if n != 0:
            self.x /= n
            self.y /= n
            self.z /= n
            self._norm = 1.0
            self._normsq = 1.0
        return self

