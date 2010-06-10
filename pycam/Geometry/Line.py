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
except:
    GL_enabled = False


import math


class Line:
    id=0
    def __init__(self,p1,p2):
        self.id = Line.id
        Line.id += 1
        self.p1 = p1
        self.p2 = p2

    def __repr__(self):
        return "Line<%g,%g,%g>-<%g,%g,%g>" % (self.p1.x,self.p1.y,self.p1.z,
                                              self.p2.x,self.p2.y,self.p2.z)

    def dir(self):
        if not hasattr(self,"_dir"):
            self._dir = self.p2.sub(self.p1)
            self._dir.normalize()
        return self._dir

    def len(self):
        if not hasattr(self,"_len"):
            self._len = self.p2.sub(self.p1).norm()
        return self._len

    def point(self, l):
        return self.p1.add(self.dir().mul(l*self.len()))

    def closest_point(self, p):
        v = self.dir()
        l = self.p1.dot(v)-p.dot(v)
        return self.p1.sub(v.mul(l))

    def dist_to_point_sq(self, p):
        return p.sub(self.closest_point(p)).normsq()

    def dist_to_point(self, p):
        return sqrt(self.dist_to_point_sq(p))
    
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
            GL.glVertex3f(p1.x, p1.y, p1.z)
            GL.glVertex3f(p2.x, p2.y, p2.z)
            GL.glEnd()

    def get_points(self):
        return (self.p1, self.p2)

