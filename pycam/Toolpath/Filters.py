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


import decimal

from pycam.Toolpath import MOVE_STRAIGHT, MOVE_STRAIGHT_RAPID, MOVE_SAFETY, \
        MOVES_LIST, MACHINE_SETTING
from pycam.Geometry.PointUtils import padd, psub, pmul, pdist, \
        ptransform_by_matrix
from pycam.Geometry.Line import Line
from pycam.Geometry.utils import epsilon
import pycam.Utils.log

log = pycam.Utils.log.get_logger()


def toolpath_filter(our_category, key):
    """ decorator for toolpath filter functions
    """
    def toolpath_filter_inner(func):
        def get_filter_func(self, category, parameters, previous_filters):
            if (category == our_category) and (key in parameters):
                result = func(self, parameters[key])
                if result:
                    previous_filters.extend(result)
        return get_filter_func
    return toolpath_filter_inner


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
        # allow to use pycam.Toolpath.Toolpath instances (instead of a list)
        if hasattr(toolpath, "path") and hasattr(toolpath, "get_params"):
            toolpath = toolpath.path
        # use a copy of the list -> changes will be permitted
        return self.filter_toolpath(list(toolpath))

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
                    # check if we can skip a possible previous safety move
                    if (pdist(last_pos, args) < self.settings["tolerance"]) and \
                            (abs(last_pos[2] - args[2]) < epsilon):
                        # same height, within tolerance -> no safety move
                        new_path.pop(-1)
                    elif (abs(last_pos[0] - args[0]) < epsilon) and \
                            (abs(last_pos[1] - args[1]) < epsilon):
                        # same position, but different height
                        new_path.pop(-1)
                in_safety = False
                last_pos = args
            elif move_type == MOVE_SAFETY:
                in_safety = True
            else:
                # it is not safe to assume that we are still at safety height
                in_safety = False
            new_path.append((move_type, args))
        return new_path


class MachineSetting(BaseFilter):

    PARAMS = ("key", "value")

    def filter_toolpath(self, toolpath):
        result = []
        # move all previous machine settings
        while toolpath and toolpath[0][0] == MACHINE_SETTING:
            result.append(toolpath.pop(0))
        # add the new setting
        result.append((MACHINE_SETTING, (self.settings["key"], self.settings["value"])))
        return result + toolpath


class SelectTool(BaseFilter):

    PARAMS = ("tool_id", )

    def filter_toolpath(self, toolpath):
        result = []
        # move all previous machine settings
        while toolpath and \
                not toolpath[0][0] in MOVES_LIST:
            result.append(toolpath.pop(0))
        result.append((MACHINE_SETTING,
                ("select_tool", self.settings["tool_id"])))
        return result + toolpath


class TriggerSpindle(BaseFilter):

    PARAMS = ("delay", )

    def filter_toolpath(self, toolpath):
        def enable_spindle(path, index):
            path.insert(index, (MACHINE_SETTING, ("spindle_enabled", True)))
            if self.settings["delay"]:
                path.insert(index + 1,
                    (MACHINE_SETTING, ("delay", self.settings["delay"])))
        def disable_spindle(path, index):
            path.insert(index, (MACHINE_SETTING, ("spindle_enabled", True)))
        # move all previous machine settings
        tool_changes = [index for index, (move, args) in enumerate(toolpath)
                if (move == MACHINE_SETTING) and (args[0] == "select_tool")]
        if tool_changes:
            tool_changes.reverse()
            for index in tool_changes:
                enable_spindle(toolpath, index + 1)
        else:
            for index, (move, args) in enumerate(toolpath):
                if move_type in MOVES_LIST:
                    enable_spindle(toolpath, index)
                    break
        # add "stop spindle" just after the last move
        index = len(result) - 1
        while (not result[-index][0] in MOVES_LIST) and (index > 0):
            index -= 1
        if result[index][0] in MOVES_LIST:
            disable_spindle(toolpath, index + 1)
        return toolpath


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
    """ shift or rotate a toolpath based on a given 3x3 or 3x4 matrix
    """

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


class TimeLimit(BaseFilter):
    """ This filter is used for the toolpath simulation. It returns only a
    partial toolpath within a given duration limit.
    """

    PARAMS = ("timelimit", )

    def filter_toolpath(self, toolpath):
        feedrate = min_feedrate = 1
        new_path = []
        last_pos = None
        limit = self.settings["timelimit"]
        duration = 0
        for move_type, args in toolpath:
            if move_type in (MOVE_STRAIGHT, MOVE_STRAIGHT_RAPID):
                if last_pos:
                    new_distance = pdist(args, last_pos)
                    new_duration = new_distance / max(feedrate, min_feedrate)
                    if (new_duration > 0) and (duration + new_duration > limit):
                        partial = (limit - duration) / new_duration
                        destination = padd(last_pos, pmul(psub(args, last_pos), partial))
                        duration = limit
                    else:
                        destination = args
                        duration += new_duration
                else:
                    destination = args
                new_path.append((move_type, destination))
                last_pos = args
            if (move_type == MACHINE_SETTING) and (args[0] == "feedrate"):
                feedrate = args[1]
            if duration >= limit:
                break
        return new_path


class MovesOnly(BaseFilter):
    """ Use this filter for checking if a given toolpath is empty/useless
    (only machine settings, safety moves, ...).
    """

    def filter_toolpath(self, toolpath):
        return [item for item in toolpath
                if item[0] in (MOVE_STRAIGHT, MOVE_STRAIGHT_RAPID)]

class Copy(BaseFilter):

    def filter_toolpath(self, toolpath):
        return toolpath


def _get_num_of_significant_digits(number):
    """ Determine the number of significant digits of a float number. """
    # use only positive numbers
    number = abs(number)
    max_diff = 0.1 ** MAX_DIGITS
    if number <= max_diff:
        # input value is smaller than the smallest usable number
        return MAX_DIGITS
    elif number >= 1:
        # no negative number of significant digits
        return 0
    else:
        for digit in range(1, MAX_DIGITS):
            shifted = number * (10 ** digit)
            if shifted - int(shifted) < max_diff:
                return digit
        else:
            return MAX_DIGITS


def _get_num_converter(step_width):
    """ Return a float-to-decimal conversion function with a prevision suitable
    for the given step width.
    """
    digits = _get_num_of_significant_digits(step_width)
    format_string = "%%.%df" % digits
    conv_func = lambda number: decimal.Decimal(format_string % number)
    return conv_func, format_string
    

class StepWidth(BaseFilter):

    PARAMS = ("step_width_x", "step_width_y", "step_width_z")
    NUM_OF_AXES = 3

    def filter_toolpath(self, toolpath):
        minimum_steps = []
        axes_formatter = []
        for key in "xyz":
            minimum_steps.append(self.settings["step_width_%s" % key])
        for step_width in minimum_steps:
            conv, format_string = _get_num_converter(step_width)
            axes_formatter.append((conv(step_width), conv, format_string))
        last_pos = None
        path = []
        for move_type, args in toolpath:
            if move_type in (MOVE_STRAIGHT, MOVE_STRAIGHT_RAPID):
                if last_pos:
                    diff = [(abs(conv[i](last_pos[i]) - conv[i](args[i])))
                            for i in range(3)]
                    if all([d < lim for d, lim in zip(diff, minimum_steps)]):
                        # too close: ignore this move
                        continue
                destination = [conv[i](args[i]) for i in range(3)]
                path.append((move_type, destination))
                last_pos = args
            else:
                # forget "last_pos" - we don't know what happened in between
                last_pos = None
                path.append((move_type, args))
        return path

