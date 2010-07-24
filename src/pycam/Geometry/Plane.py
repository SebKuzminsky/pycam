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

from pycam.Geometry.utils import INFINITE
from pycam.Geometry.Point import Point

class Plane:
    id = 0
    def __init__(self, p, n):
        self.id = Plane.id
        Plane.id += 1
        self.p = p
        self.n = n

    def __repr__(self):
        return "Plane<%s,%s>" % (self.p, self.n)

    def intersect_point(self, direction, point):
        if direction.norm() != 1:
            # calculations will go wrong, if the direction is not a unit vector
            direction = Point(direction.x, direction.y, direction.z).normalize()
        denom = self.n.dot(direction)
        if denom == 0:
            return (None, INFINITE)
        l = -(self.n.dot(point) - self.n.dot(self.p)) / denom
        cp = point.add(direction.mul(l))
        return (cp, l)

