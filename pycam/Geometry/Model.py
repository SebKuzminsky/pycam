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

from utils import *
from Point import *
from Line import *
from Triangle import *

try:
    import OpenGL.GL as GL
    GL_enabled = True
except:
    GL_enabled = False


MODEL_TRANSFORMATIONS = {
    "normal": ((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0)),
    "x": ((1, 0, 0, 0), (0, 0, 1, 0), (0, -1, 0, 0)),
    "y": ((0, 0, -1, 0), (0, 1, 0, 0), (1, 0, 0, 0)),
    "z": ((0, 1, 0, 0), (-1, 0, 0, 0), (0, 0, 1, 0)),
    "xy": ((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, -1, 0)),
    "xz": ((1, 0, 0, 0), (0, -1, 0, 0), (0, 0, 1, 0)),
    "yz": ((-1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0)),
    "x_swap_y": ((0, 1, 0, 0), (1, 0, 0, 0), (0, 0, 1, 0)),
    "x_swap_z": ((0, 0, 1, 0), (0, 1, 0, 0), (1, 0, 0, 0)),
    "y_swap_z": ((1, 0, 0, 0), (0, 0, 1, 0), (0, 1, 0, 0)),
}


class Model:
    id = 0

    def __init__(self):
        self.id = Model.id
        Model.id += 1
        self._triangles = []
        self.name = "model%d" % self.id
        self.minx = None
        self.miny = None
        self.minz = None
        self.maxx = None
        self.maxy = None
        self.maxz = None
        self._maxsize = None

    def __add__(self, other_model):
        """ combine two models """
        result = Model()
        for t in self._triangles:
            result.append(t)
        for t in other_model._triangles:
            result.append(t)
        return result

    def to_OpenGL(self):
        if not GL_enabled:
            return
        if True:
            GL.glBegin(GL.GL_TRIANGLES)
            for t in self._triangles:
                GL.glVertex3f(t.p1.x, t.p1.y, t.p1.z)
                GL.glVertex3f(t.p2.x, t.p2.y, t.p2.z)
                GL.glVertex3f(t.p3.x, t.p3.y, t.p3.z)
            GL.glEnd()
        else:
            for t in self._triangles:
                t.to_OpenGL()

    def _update_limits(self, t):
        if self.minx is None:
            self.minx = t.minx()
            self.miny = t.miny()
            self.minz = t.minz()
            self.maxx = t.maxx()
            self.maxy = t.maxy()
            self.maxz = t.maxz()
        else:
            self.minx = min(self.minx, t.minx())
            self.miny = min(self.miny, t.miny())
            self.minz = min(self.minz, t.minz())
            self.maxx = max(self.maxx, t.maxx())
            self.maxy = max(self.maxy, t.maxy())
            self.maxz = max(self.maxz, t.maxz())

    def append(self, t):
        self._update_limits(t)
        self._triangles.append(t)

    def maxsize(self):
        if self._maxsize is None:
            self._maxsize = max3(max(abs(self.maxx),abs(self.minx)),max(abs(self.maxy),abs(self.miny)),max(abs(self.maxz),abs(self.minz)))
        return self._maxsize

    def triangles(self, minx=-INFINITE,miny=-INFINITE,minz=-INFINITE,maxx=+INFINITE,maxy=+INFINITE,maxz=+INFINITE):
        if minx==-INFINITE and miny==-INFINITE and minz==-INFINITE and maxx==+INFINITE and maxy==+INFINITE and maxz==+INFINITE:
            return self._triangles
        if hasattr(self, "t_kdtree"):
            return self.t_kdtree.Search(minx,maxx,miny,maxy)
        return self._triangles

    def subdivide(self, depth):
        model = Model()
        for t in self._triangles:
            for s in t.subdivide(depth):
                model.append(s)
        return model

    def reset_cache(self):
        self.minx = None
        self.miny = None
        self.minz = None
        self.maxx = None
        self.maxy = None
        self.maxz = None
        for t in self._triangles:
            self._update_limits(t)
        self._maxsize = None

    def transform_by_matrix(self, matrix):
        processed = []
        for tr in self._triangles:
            for point in (tr.p1, tr.p2, tr.p3):
                if not point.id in processed:
                    processed.append(point.id)
                    x = point.x * matrix[0][0] + point.y * matrix[0][1] + point.z * matrix[0][2] + matrix[0][3]
                    y = point.x * matrix[1][0] + point.y * matrix[1][1] + point.z * matrix[1][2] + matrix[1][3]
                    z = point.x * matrix[2][0] + point.y * matrix[2][1] + point.z * matrix[2][2] + matrix[2][3]
                    point.x = x
                    point.y = y
                    point.z = z
            tr.reset_cache()
        self.reset_cache()

    def transform_by_template(self, direction="normal"):
        if direction in MODEL_TRANSFORMATIONS.keys():
            self.transform_by_matrix(MODEL_TRANSFORMATIONS[direction])

    def shift(self, shift_x, shift_y, shift_z):
        matrix = ((1, 0, 0, shift_x), (0, 1, 0, shift_y), (0, 0, 1, shift_z))
        self.transform_by_matrix(matrix)
        
    def scale(self, scale_x, scale_y=None, scale_z=None):
        if scale_y is None:
            scale_y = scale_x
        if scale_z is None:
            scale_z = scale_x
        matrix = ((scale_x, 0, 0, 0), (0, scale_y, 0, 0), (0, 0, scale_z, 0))
        self.transform_by_matrix(matrix)

