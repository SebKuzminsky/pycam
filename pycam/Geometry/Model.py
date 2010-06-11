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

from pycam.Geometry import Triangle, Line
from utils import INFINITE

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


class BaseModel(object):
    id = 0

    def __init__(self):
        self.id = BaseModel.id
        BaseModel.id += 1
        self._item_groups = []
        self.name = "model%d" % self.id
        self.minx = None
        self.miny = None
        self.minz = None
        self.maxx = None
        self.maxy = None
        self.maxz = None

    def __add__(self, other_model):
        """ combine two models """
        result = self.__class__()
        for item_group in self._item_groups + other_model._item_groups:
            for item in item_group:
                result.append(item)
        return result

    def to_OpenGL(self):
        for item_group in self._item_groups:
            for item in item_group:
                item.to_OpenGL()

    def _update_limits(self, item):
        if self.minx is None:
            self.minx = item.minx()
            self.miny = item.miny()
            self.minz = item.minz()
            self.maxx = item.maxx()
            self.maxy = item.maxy()
            self.maxz = item.maxz()
        else:
            self.minx = min(self.minx, item.minx())
            self.miny = min(self.miny, item.miny())
            self.minz = min(self.minz, item.minz())
            self.maxx = max(self.maxx, item.maxx())
            self.maxy = max(self.maxy, item.maxy())
            self.maxz = max(self.maxz, item.maxz())

    def append(self, item):
        self._update_limits(item)

    def maxsize(self):
        return max(abs(self.maxx), abs(self.minx), abs(self.maxy),
                abs(self.miny), abs(self.maxz), abs(self.minz))

    def subdivide(self, depth):
        model = self.__class__()
        for item_group in self._item_groups:
            for item in item_group:
                for s in item.subdivide(depth):
                    model.append(s)
        return model

    def reset_cache(self):
        self.minx = None
        self.miny = None
        self.minz = None
        self.maxx = None
        self.maxy = None
        self.maxz = None
        for item_group in self._item_groups:
            for item in item_group:
                self._update_limits(item)

    def transform_by_matrix(self, matrix):
        processed = []
        for item_group in self._item_groups:
            for item in item_group:
                for point in item.get_points():
                    if not point.id in processed:
                        processed.append(point.id)
                        x = point.x * matrix[0][0] + point.y * matrix[0][1] + point.z * matrix[0][2] + matrix[0][3]
                        y = point.x * matrix[1][0] + point.y * matrix[1][1] + point.z * matrix[1][2] + matrix[1][3]
                        z = point.x * matrix[2][0] + point.y * matrix[2][1] + point.z * matrix[2][2] + matrix[2][3]
                        point.x = x
                        point.y = y
                        point.z = z
                if hasattr(item, "reset_cache"):
                    item.reset_cache()
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


class Model(BaseModel):

    def __init__(self):
        super(Model, self).__init__()
        self._triangles = []
        self._item_groups.append(self._triangles)

    def append(self, item):
        super(Model, self).append(item)
        if isinstance(item, Triangle):
            self._triangles.append(item)

    def triangles(self, minx=-INFINITE,miny=-INFINITE,minz=-INFINITE,maxx=+INFINITE,maxy=+INFINITE,maxz=+INFINITE):
        if minx==-INFINITE and miny==-INFINITE and minz==-INFINITE and maxx==+INFINITE and maxy==+INFINITE and maxz==+INFINITE:
            return self._triangles
        if hasattr(self, "t_kdtree"):
            return self.t_kdtree.Search(minx,maxx,miny,maxy)
        return self._triangles


class ContourModel(BaseModel):

    def __init__(self):
        super(ContourModel, self).__init__()
        self.name = "contourmodel%d" % self.id
        self._line_groups = []
        self._item_groups.append(self._lines)
    _lines = property(lambda self: sum(self._line_groups, []))

    def append(self, item):
        super(ContourModel, self).append(item)
        if isinstance(item, Line):
            for line_group in self._line_groups:
                if item.p2 == line_group[0].p1:
                    # the line fits to the start of this group
                    line_group.insert(0, item)
                    break
                elif item.p1 == line_group[-1].p2:
                    # the line fits to the end of this group
                    line_group.append(item)
                    break
            else:
                # add a new group with this single item
                self._line_groups.append([item])

    def get_lines(self):
        return self._lines

    def get_line_groups(self):
        return self._line_groups

