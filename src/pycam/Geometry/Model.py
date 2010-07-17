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

import pycam.Exporters.STLExporter
from pycam.Geometry import Triangle, Line, Point
from pycam.Geometry.TriangleKdtree import TriangleKdtree
from pycam.Toolpath import Bounds
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
        # derived classes should override this
        self._export_function = None

    def __add__(self, other_model):
        """ combine two models """
        result = self.__class__()
        for item in self.next():
            result.append(item)
        for item in other_model.next():
            result.append(item)
        return result

    def __iter__(self):
        return self

    def next(self):
        for item_group in self._item_groups:
            for item in item_group:
                if isinstance(item, list):
                    for subitem in item:
                        yield subitem
                else:
                    yield item

    def to_OpenGL(self):
        for item in self.next():
            item.to_OpenGL()

    def is_export_supported(self):
        return not self._export_function is None

    def export(self, comment=None):
        if self.is_export_supported():
            return self._export_function(self, comment=comment)
        else:
            raise NotImplementedError(("This type of model (%s) does not " \
                    + "support the 'export' function.") % str(type(self)))

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
        for item in self.next():
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
        for item in self.next():
            self._update_limits(item)

    def transform_by_matrix(self, matrix):
        processed = []
        for item in self.next():
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

    def get_bounds(self):
        return Bounds(Bounds.TYPE_CUSTOM, (self.minx, self.miny, self.minz),
                (self.maxx, self.maxy, self.maxz))


class Model(BaseModel):

    def __init__(self, use_kdtree=True):
        super(Model, self).__init__()
        self._triangles = []
        self._item_groups.append(self._triangles)
        self._export_function = pycam.Exporters.STLExporter.STLExporter
        # marker for state of kdtree
        self._kdtree_dirty = True
        # enable/disable kdtree
        self._use_kdtree = use_kdtree

    def append(self, item):
        super(Model, self).append(item)
        if isinstance(item, Triangle):
            self._triangles.append(item)
            # we assume, that the kdtree needs to be rebuilt again
            self._kdtree_dirty = True

    def reset_cache(self):
        super(Model, self).reset_cache()
        # the triangle kdtree needs to be reset after transforming the model
        self._update_kdtree()

    def _update_kdtree(self):
        if self._use_kdtree:
            self._t_kdtree = TriangleKdtree(self.triangles())
        # the kdtree is up-to-date again
        self._kdtree_dirty = False

    def triangles(self, minx=-INFINITE, miny=-INFINITE, minz=-INFINITE,
            maxx=+INFINITE, maxy=+INFINITE, maxz=+INFINITE):
        if (minx == miny == minz == -INFINITE) \
                and (maxx == maxy == maxz == +INFINITE):
            return self._triangles
        if self._use_kdtree:
            # update the kdtree, if new triangles were added meanwhile
            if self._kdtree_dirty:
                self._update_kdtree()
            return self._t_kdtree.Search(minx, maxx, miny, maxy)
        return self._triangles


class ContourModel(BaseModel):

    def __init__(self):
        super(ContourModel, self).__init__()
        self.name = "contourmodel%d" % self.id
        self._line_groups = []
        self._item_groups.append(self._line_groups)

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
        return sum(self._line_groups, [])

    def get_line_groups(self):
        return self._line_groups

    def get_offset_model(self, offset):
        """ calculate a contour model that surrounds the current model with
        a given offset.
        This is mainly useful for engravings that should not proceed _on_ the
        lines but besides these.
        """
        def get_parallel_line(line, offset):
            if offset == 0:
                return Line(line.p1, line.p2)
            else:
                cross = line.p2.sub(line.p1).cross(Point(0, 0, 1))
                cross_offset = cross.mul(offset / cross.norm())
                in_line = line.p2.sub(line.p1).normalize().mul(offset)
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
            factor = c.cross(b).dot(a.cross(b)) / a.cross(b).normsq()
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
        result = ContourModel()
        for group in self._line_groups:
            closed_group = (len(group) > 1) and (group[-1].p2 == group[0].p1)
            new_group = []
            for line in group:
                new_group.append(get_parallel_line(line, offset))
            finished = False
            while not finished:
                if len(new_group) > 1:
                    # calculate new intersections for each pair of adjacent lines
                    for index in range(len(new_group)):
                        if (index == 0) and (not closed_group):
                            # skip the first line if the group is not closed
                            continue
                        # this also works for index==0 (closed groups)
                        l1 = new_group[index - 1]
                        l2 = new_group[index]
                        do_lines_intersection(l1, l2)
                # Remove all lines that were marked as obsolete during
                # intersection calculation.
                clean_group = [line for line in new_group if not line.p1 is None]
                finished = len(new_group) == len(clean_group)
                if (len(clean_group) == 1) and closed_group:
                    new_group = []
                    finished = True
                else:
                    new_group = clean_group
            for line in new_group:
                result.append(line)
        return result

    def check_for_collisions(self):
        def get_bounds_of_group(group):
            minx, maxx, miny, maxy = None, None, None, None
            for line in group:
                lminx = min(line.p1.x, line.p2.x)
                lmaxx = max(line.p1.x, line.p2.x)
                lminy = min(line.p1.y, line.p2.y)
                lmaxy = max(line.p1.y, line.p2.y)
                if (minx is None) or (minx > lminx):
                    minx = lminx
                if (maxx is None) or (maxx > lmaxx):
                    maxx = lmaxx
                if (miny is None) or (miny > lminy):
                    miny = lminy
                if (maxy is None) or (maxy > lmaxy):
                    maxy = lmaxy
            return (minx, maxx, miny, maxy)
        def check_bounds_of_groups(group1, group2):
            bound1 = get_bounds_of_group(group1)
            bound2 = get_bounds_of_group(group2)
            if ((bound1[0] < bound2[0]) and not (bound1[1] > bound2[1])) or \
                    ((bound2[0] < bound1[0]) and not (bound2[1] > bound1[1])):
                # the x boundaries overlap
                if ((bound1[2] < bound2[2]) and not (bound1[3] > bound2[3])) \
                        or ((bound2[2] < bound1[2]) \
                        and not (bound2[3] > bound1[3])):
                    # y also overlap
                    return True
            return False
        # check each pair of line groups for intersections
        for group1 in self._line_groups:
            for group2 in self._line_groups:
                # check if both groups overlap - otherwise skip this pair
                if check_bounds_of_groups(group1, group2):
                    # check each pair of lines for intersections
                    for line1 in group1:
                        for line2 in group2:
                            if line1.get_intersection(line2):
                                return True
        return False

