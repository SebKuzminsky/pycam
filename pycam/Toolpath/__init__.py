# -*- coding: utf-8 -*-
"""
$Id$

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

__all__ = ["ToolPathList", "ToolPath", "Generator"]

from pycam.Geometry.Point import Point
import random

class ToolPathList(list):

    def add_toolpath(self, toolpath, name, tool_settings, *args):
        self.append(ToolPath(toolpath, name, tool_settings, *args))

class ToolPath:

    def __init__(self, toolpath, name, tool_settings, tool_id, speed,
            feedrate, material_allowance, safety_height, unit, start_x,
            start_y, start_z, bounding_box):
        self.toolpath = toolpath
        self.name = name
        self.visible = True
        self.tool_id = tool_id
        self.tool_settings = tool_settings
        self.speed = speed
        self.feedrate = feedrate
        self.material_allowance = material_allowance
        self.safety_height = safety_height
        self.unit = unit
        self.start_x = start_x
        self.start_y = start_y
        self.start_z = start_z
        self.bounding_box = bounding_box
        self.color = None
        # generate random color
        self.set_color()

    def get_path(self):
        return self.toolpath

    def set_color(self, color=None):
        if color is None:
            self.color = (random.random(), random.random(), random.random())
        else:
            self.color = color

    def get_machine_time(self, start_position=None):
        """ calculate an estimation of the time required for processing the
        toolpath with the machine

        @value start_position: (optional) the position of the tool before the
                start
        @type start_position: pycam.Geometry.Point.Point
        @rtype: float
        @returns: the machine time used for processing the toolpath in minutes
        """
        if start_position is None:
            start_position = Point(0, 0, 0)
        def move(new_pos):
            move.result_time += new_pos.sub(move.current_position).norm() / self.feedrate
            move.current_position = new_pos
        move.current_position = start_position
        move.result_time = 0
        # move to safey height at the starting position
        move(Point(start_position.x, start_position.y, self.safety_height))
        for path in self.get_path():
            # go to safety height (horizontally from the previous x/y location)
            if len(path.points) > 0:
                move(Point(path.points[0].x, path.points[0].y, self.safety_height))
            # go through all points of the path
            for point in path.points:
                move(point)
            # go to safety height (vertically up from the current x/y location)
            if len(path.points) > 0:
                move(Point(path.points[-1].x, path.points[-1].y, self.safety_height))
        return move.result_time

