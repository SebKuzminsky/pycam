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
from pycam.Geometry.Point import Point


class BaseFilter(object):

    def __ror__(self, toolpath):
        return self.filter_toolpath(toolpath)

    def filter_toolpath(self, toolpath):
        raise NotImplementedError("The filter class %s failed to " + \
                "implement the 'filter_toolpath' method" % str(type(self)))


class SafetyHeightFilter(BaseFilter):

    def __init__(self, safety_height):
        self.safety_height = safety_height

    def filter_toolpath(self, toolpath):
        last_pos = None
        new_path = []
        for move_type, args in toolpath:
            if move_type in (MOVE_STRAIGHT, MOVE_STRAIGHT_RAPID):
                if not last_pos:
                    # there was a safety move (or no move at all) before
                    # -> move sideways
                    safe_pos = Point(args.x, args.y, self.safety_height)
                    new_path.append((MOVE_STRAIGHT_RAPID, safe_pos))
                last_pos = args
                new_path.append((move_type, args))
            elif move_type == MOVE_SAFETY:
                if last_pos:
                    # safety move -> move straight up to safety height
                    next_pos = Point(last_pos.x, last_pos.y, self.safety_height)
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

    def __init__(self, tolerance):
        self.tolerance = tolerance

    def filter_toolpath(self, toolpath):
        new_path = []
        last_pos = None
        in_safety = False
        for move_type, args in toolpath:
            if move_type in (MOVE_STRAIGHT, MOVE_STRAIGHT_RAPID):
                if in_safety and last_pos:
                    # check if the last position was very close
                    if (last_pos.sub(args).norm < self.tolerance) and \
                            (last_pos.x == args.x) and (last_pos.y == args.y):
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

    def __init__(self, key, value):
        self.key = key
        self.value = value

    def filter_toolpath(self, toolpath):
        return [(MACHINE_SETTING, (self.key, self.value))] + toolpath

