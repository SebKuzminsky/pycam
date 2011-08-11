# -*- coding: utf-8 -*-
"""
$Id$

Copyright 2011 Lars Kruse <devel@sumpfralle.de>

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


import pycam.Plugins
import pycam.Toolpath.MotionGrid


class PathPatternSpiral(pycam.Plugins.PluginBase):

    DEPENDS = ["ParameterGroupManager", "PathParamPattern",
            "PathParamMillingStyle", "PathParamSpiralDirection"]
    CATEGORIES = ["Process"]

    def setup(self):
        parameters = {
                "milling_style": pycam.Toolpath.MotionGrid.MILLING_STYLE_IGNORE,
                "spiral_direction": None,
        }
        self.core.get("register_parameter_set")("path_pattern", "spiral",
                "Spiral", self.get_grid_generator, parameters=parameters,
                weight=30)
        return True

    def teardown(self):
        self.core.get("unregister_parameter_set")("path_pattern", "spiral")

    def get_grid_generator(self, pattern):
        kwargs = pattern["parameters"]
        func = pycam.Toolpath.MotionGrid.get_spiral
        return func, kwargs


class PathPatternGrid(pycam.Plugins.PluginBase):

    DEPENDS = ["ParameterGroupManager", "PathParamPattern",
            "PathParamMillingStyle", "PathParamGridDirection"]
    CATEGORIES = ["Process"]

    def setup(self):
        parameters = {
                "milling_style": pycam.Toolpath.MotionGrid.MILLING_STYLE_IGNORE,
                "grid_direction": pycam.Toolpath.MotionGrid.GRID_DIRECTION_X,
        }
        self.core.get("register_parameter_set")("path_pattern", "grid",
                "Grid", self.get_grid_generator, parameters=parameters,
                weight=10)
        return True

    def teardown(self):
        self.core.get("unregister_parameter_set")("path_pattern", "grid")

    def get_grid_generator(self, pattern):
        kwargs = pattern["parameters"]
        func = pycam.Toolpath.MotionGrid.get_fixed_grid
        return func, kwargs

