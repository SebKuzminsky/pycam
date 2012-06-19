# -*- coding: utf-8 -*-
"""
$Id$

Copyright 2012 Lars Kruse <devel@sumpfralle.de>

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


from pycam.Toolpath import MOVE_STRAIGHT, MOVE_STRAIGHT_RAPID, MOVE_SAFETY, MACHINE_SETTING
from pycam.Geometry.PointUtils import psub, pdist, ptransform_by_matrix
from pycam.Geometry.Line import Line
from pycam.Geometry.utils import epsilon
import pycam.Utils.log

log = pycam.Utils.log.get_logger()


class BaseFilter(object):

    PARAMS = []

    def __init__(self, *args, **kwargs):
        self.settings = dict(kwargs)
        # fail if too many arguments (without names) are given
        if len(args) > len(self.PARAMS):
            raise ValueError("Too many parameters: " + \
                    "%d (expected: %d)" % (len(args), len(self.PARAMS)))
        # fail if too fee arguments (without names) are given
        for index, key in enumerate(self.PARAMS):
            if len(args) > index:
                self.settings[key] = args[index]
            elif key in self.settings:
                # named parameter are ok, as well
                pass
            else:
                raise ValueError("Missing parameter: %s" % str(key))

    def clone(self):
        return self.__class__(**self.settings)

    def __ror__(self, toolpath):
        return self.filter_toolpath(toolpath)

    def filter_toolpath(self, toolpath):
        raise NotImplementedError("The filter class %s failed to " + \
                "implement the 'filter_toolpath' method" % str(type(self)))


class SafetyHeightFilter(BaseFilter):

    PARAMS = ("safety_height", )

    def filter_toolpath(self, toolpath):
        last_pos = None
        new_path = []
        for move_type, args in toolpath:
            if move_type in (MOVE_STRAIGHT, MOVE_STRAIGHT_RAPID):
                if not last_pos:
                    # there was a safety move (or no move at all) before
                    # -> move sideways
                    safe_pos = (args[0], args[1],
                            self.settings["safety_height"])
                    new_path.append((MOVE_STRAIGHT_RAPID, safe_pos))
                last_pos = args
                new_path.append((move_type, args))
            elif move_type == MOVE_SAFETY:
                if last_pos:
                    # safety move -> move straight up to safety height
                    next_pos = (last_pos[0], last_pos[1],
                            self.settings["safety_height"])
                    new_path.append((MOVE_STRAIGHT_RAPID, next_pos))
                    last_pos = None
                else:
                    # this looks like a duplicate safety move -> ignore
                    pass
            else:
                # unknown move -> keep it
                new_path.append((move_type, args))
        return new_path


class TinySidewaysMovesFilter(BaseFilter):

    PARAMS = ("tolerance", )

    def filter_toolpath(self, toolpath):
        new_path = []
        last_pos = None
        in_safety = False
        for move_type, args in toolpath:
            if move_type in (MOVE_STRAIGHT, MOVE_STRAIGHT_RAPID):
                if in_safety and last_pos:
                    # check if the last position was very close and at the
                    # same height
                    if (pdist(last_pos, args) < self.settings["tolerance"]) and \
                            (abs(last_pos[2] - args[2]) < epsilon):
                        # within tolerance -> remove previous safety move
                        new_path.pop(-1)
                in_safety = False
                last_pos = args
            elif move_type == MOVE_SAFETY:
                in_safety = True
            else:
                pass
            new_path.append((move_type, args))
        return new_path


class MachineSetting(BaseFilter):

    PARAMS = ("key", "value")

    def filter_toolpath(self, toolpath):
        result = []
        # prepare a copy
        toolpath = list(toolpath)
        # move all previous machine settings
        while toolpath and toolpath[0][0] == MACHINE_SETTING:
            result.append(toolpath.pop(0))
        # add the new setting
        result.append((MACHINE_SETTING, (self.settings["key"], self.settings["value"])))
        return result + toolpath


class Crop(BaseFilter):

    PARAMS = ("polygons", )

    def filter_toolpath(self, toolpath):
        new_path = []
        last_pos = None
        optional_moves = []
        for move_type, args in toolpath:
            if move_type in (MOVE_STRAIGHT, MOVE_STRAIGHT_RAPID):
                if last_pos:
                    # find all remaining pieces of this line
                    inner_lines = []
                    for polygon in self.settings["polygons"]:
                        inner, outer = polygon.split_line(Line(last_pos, args))
                        inner_lines.extend(inner)
                    # turn these lines into moves
                    for line in inner_lines:
                        if pdist(line.p1, last_pos) > epsilon:
                            new_path.append((MOVE_SAFETY, None))
                            new_path.append((move_type, line.p1))
                        else:
                            # we continue were we left
                            if optional_moves:
                                new_path.extend(optional_moves)
                                optional_moves = []
                        new_path.append((move_type, line.p2))
                        last_pos = line.p2
                    optional_moves = []
                    # finish the line by moving to its end (if necessary)
                    if pdist(last_pos, args) > epsilon:
                        optional_moves.append((MOVE_SAFETY, None))
                        optional_moves.append((move_type, args))
                last_pos = args
            elif move_type == MOVE_SAFETY:
                optional_moves = []
            else:
                new_path.append((move_type, args))
        return new_path


class TransformPosition(BaseFilter):

    PARAMS = ("matrix", )

    def filter_toolpath(self, toolpath):
        new_path = []
        for move_type, args in toolpath:
            if move_type in (MOVE_STRAIGHT, MOVE_STRAIGHT_RAPID):
                new_pos = ptransform_by_matrix(args, self.settings["matrix"])
                new_path.append((move_type, new_pos))
            else:
                new_path.append((move_type, args))
        return new_path

