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
import pycam.Cutters.SphericalCutter
import pycam.Cutters.ToroidalCutter
import pycam.Cutters.CylindricalCutter


class ToolTypeBallNose(pycam.Plugins.PluginBase):

    DEPENDS = ["Tools", "ToolParamRadius", "ToolParamFeedrate"]

    def setup(self):
        parameters = {"radius": 1.0,
                "feedrate": 300,
                "spindle_speed": 1000,
        }
        self.core.get("register_parameter_set")("tool", "ballnose",
                "Ball nose", self.get_tool, parameters=parameters,
                weight=20)
        return True

    def teardown(self):
        self.core.get("unregister_parameter_set")("tool", "ballnose")

    def get_tool(self, tool, environment=None):
        return pycam.Cutters.SphericalCutter(tool["parameters"]["radius"])


class ToolTypeBullNose(pycam.Plugins.PluginBase):

    DEPENDS = ["Tools", "ToolParamRadius", "ToolParamTorusRadius",
            "ToolParamFeedrate"]

    def setup(self):
        parameters = {"radius": 1.0,
                "torus_radius": 0.25,
                "feedrate": 300,
                "spindle_speed": 1000,
        }
        self.core.get("register_parameter_set")("tool", "bullnose",
                "Bull nose", self.get_tool, parameters=parameters,
                weight=30)
        return True

    def teardown(self):
        self.core.get("unregister_parameter_set")("tool", "bullnose")

    def get_tool(self, tool, environment=None):
        return pycam.Cutters.ToroidalCutter(
                tool["parameters"]["radius"],
                tool["parameters"]["torus_radius"])


class ToolTypeFlat(pycam.Plugins.PluginBase):

    DEPENDS = ["Tools", "ToolParamRadius", "ToolParamFeedrate"]

    def setup(self):
        parameters = {"radius": 1.0,
                "feedrate": 300,
                "spindle_speed": 1000,
        }
        self.core.get("register_parameter_set")("tool", "flat", "Flat bottom",
                self.get_tool, parameters=parameters, weight=10)
        return True

    def teardown(self):
        self.core.get("unregister_parameter_set")("tool", "flat")

    def get_tool(self, tool, environment=None):
        return pycam.Cutters.CylindricalCutter(tool["parameters"]["radius"])

