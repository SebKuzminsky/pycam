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
import pycam.Gui.Settings
import random
import os


class ToolPathList(list):

    def add_toolpath(self, toolpath, name, toolpath_settings):
        self.append(ToolPath(toolpath, name, toolpath_settings))


class ToolPath:

    def __init__(self, toolpath, name, toolpath_settings):
        self.toolpath = toolpath
        self.name = name
        self.toolpath_settings = toolpath_settings
        self.visible = True
        self.color = None
        # generate random color
        self.set_color()

    def get_path(self):
        return self.toolpath

    def get_start_position(self):
        safety_height = self.toolpath_settings.get_process_settings()["safety_height"]
        for path in self.toolpath:
            if path.points:
                p = path.points[0]
                return Point(p.x, p.y, safety_height)
        else:
            return Point(0, 0, safety_height)

    def get_bounding_box(self):
        box = self.toolpath_settings.get_bounds()
        return (box["minx"], box["maxx"], box["miny"], box["maxy"], box["minz"],
                box["maxz"])

    def get_tool_settings(self):
        return self.toolpath_settings.get_tool_settings()

    def get_toolpath_settings(self):
        return self.toolpath_settings

    def get_meta_data(self):
        meta = self.toolpath_settings.get_string()
        start_marker = self.toolpath_settings.META_MARKER_START
        end_marker = self.toolpath_settings.META_MARKER_END
        return os.linesep.join((start_marker, meta, end_marker))

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
        feedrate = self.toolpath_settings.get_tool_settings()["feedrate"]
        def move(new_pos):
            move.result_time += new_pos.sub(move.current_position).norm() / feedrate
            move.current_position = new_pos
        move.current_position = start_position
        move.result_time = 0
        # move to safey height at the starting position
        safety_height = self.toolpath_settings.get_process_settings()["safety_height"]
        move(Point(start_position.x, start_position.y, safety_height))
        for path in self.get_path():
            # go to safety height (horizontally from the previous x/y location)
            if len(path.points) > 0:
                move(Point(path.points[0].x, path.points[0].y, safety_height))
            # go through all points of the path
            for point in path.points:
                move(point)
            # go to safety height (vertically up from the current x/y location)
            if len(path.points) > 0:
                move(Point(path.points[-1].x, path.points[-1].y, safety_height))
        return move.result_time

