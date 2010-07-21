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
from pycam.Geometry.Triangle import Triangle
from pycam.Geometry.Line import Line
from pycam.Geometry.Point import Point
from pycam.Geometry.TriangleKdtree import TriangleKdtree
from pycam.Toolpath import Bounds
from pycam.Geometry.utils import INFINITE
from pycam.Geometry import TransformableContainer


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


class BaseModel(TransformableContainer):
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
        self._t_kdtree = None

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
        self._cached_offset_models = {}

    def reset_cache(self):
        super(ContourModel, self).reset_cache()
        # reset the offset model cache
        self._cached_offset_models = {}

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

    def get_offset_model(self, offset, callback=None):
        """ calculate a contour model that surrounds the current model with
        a given offset.
        This is mainly useful for engravings that should not proceed _on_ the
        lines but besides these.
        @value offset: shifting distance; positive values enlarge the model
        @type offset: float
        @value callback: function to call after finishing a single line.
            It should return True if the user interrupted the operation.
        @type callback: callable
        @returns: the new shifted model
        @rtype: pycam.Geometry.Model.Model
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
        # use a cached offset model if it exists
        if offset in self._cached_offset_models:
            return self._cached_offset_models[offset]
        result = ContourModel()
        for group in self._line_groups:
            closed_group = (len(group) > 1) and (group[-1].p2 == group[0].p1)
            new_group = []
            for line in group:
                new_group.append(get_parallel_line(line, offset))
            # counter for the progress callback
            lines_to_be_processed = len(new_group)
            finished = False
            while not finished:
                if len(new_group) > 1:
                    # Calculate new intersections for each pair of adjacent
                    # lines.
                    for index in range(len(new_group)):
                        if (index == 0) and (not closed_group):
                            # skip the first line if the group is not closed
                            continue
                        # this also works for index==0 (closed groups)
                        l1 = new_group[index - 1]
                        l2 = new_group[index]
                        do_lines_intersection(l1, l2)
                        # Don't call the "progress" callback more times than the
                        # number of lines in this group.
                        if (lines_to_be_processed > 0) \
                                and callback and callback():
                            # the user requested "quit"
                            return None
                        lines_to_be_processed -= 1
                # Remove all lines that were marked as obsolete during
                # intersection calculation.
                clean_group = [line for line in new_group
                        if not line.p1 is None]
                finished = len(new_group) == len(clean_group)
                if (len(clean_group) == 1) and closed_group:
                    new_group = []
                    finished = True
                else:
                    new_group = clean_group
            # "fix" the progress counter (it expected as many lines as there
            # are items in the group. This causes small progress jumps.
            if callback:
                while lines_to_be_processed > 0:
                    if callback():
                        return None
                    lines_to_be_processed -= 1
            for line in new_group:
                result.append(line)
        # cache the result
        self._cached_offset_models[offset] = result
        return result

    def check_for_collisions(self, callback=None):
        """ check if lines in different line groups of this model collide

        Returns a pycam.Geometry.Point.Point instance in case of an
        intersection.
        Returns None if the optional "callback" returns True (e.g. the user
        interrupted the operation).
        Otherwise it returns False if no intersections were found.
        """
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
        def check_bounds_of_groups(bound1, bound2):
            if ((bound1[0] <= bound2[0] <= bound1[1]) \
                    or (bound1[0] <= bound2[1] <= bound1[1]) \
                    or (bound2[0] <= bound1[0] <= bound2[1]) \
                    or (bound2[0] <= bound1[1] <= bound2[1])):
                # the x boundaries overlap
                if ((bound1[2] <= bound2[2] <= bound1[3]) \
                        or (bound1[2] <= bound2[3] <= bound1[3]) \
                        or (bound2[2] <= bound1[2] <= bound2[3]) \
                        or (bound2[2] <= bound1[3] <= bound2[3])):
                    # also the y boundaries overlap
                    return True
            return False
        # check each pair of line groups for intersections
        # first: cache the bounds of each group
        bounds = {}
        for group in self._line_groups:
            bounds[id(group)] = get_bounds_of_group(group)
        # now start to look for intersections
        for group1 in self._line_groups:
            for group2 in self._line_groups:
                # don't compare a group with itself
                if group1 is group2:
                    continue
                # check if both groups overlap - otherwise skip this pair
                if check_bounds_of_groups(bounds[id(group1)],
                        bounds[id(group2)]):
                    # check each pair of lines for intersections
                    for line1 in group1:
                        for line2 in group2:
                            intersection = line1.get_intersection(line2)
                            if intersection:
                                return intersection
            # update the progress visualization and quit if requested
            if callback and callback():
                return None
        return False

