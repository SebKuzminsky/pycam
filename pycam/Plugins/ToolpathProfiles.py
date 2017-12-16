# -*- coding: utf-8 -*-
"""
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

import pycam.Gui.ControlsGTK
import pycam.Plugins
import pycam.Utils.log


def _get_profile_filters(core, parameters):
    filters = []
    core.call_chain("toolpath_filters", "settings", parameters, filters)
    return filters


class ToolpathProfileMilling(pycam.Plugins.PluginBase):

    DEPENDS = ["Toolpaths", "GCodeSafetyHeight", "GCodePlungeFeedrate", "GCodeFilenameExtension",
               "GCodeStepWidth", "GCodeSpindle", "GCodeCornerStyle"]
    CATEGORIES = ["Toolpath"]

    def setup(self):
        parameters = {"safety_height": 25,
                      "plunge_feedrate": 100,
                      "filename_extension": "",
                      "step_width_x": 0.0001,
                      "step_width_y": 0.0001,
                      "step_width_z": 0.0001,
                      # pick the first path mode
                      "path_mode": 0,
                      "motion_tolerance": 0.0,
                      "naive_tolerance": 0.0,
                      "spindle_enable": True,
                      "spindle_delay": 3,
                      "touch_off": None}
        self.core.get("register_parameter_set")(
            "toolpath_profile", "milling", "Milling",
            lambda params: _get_profile_filters(self.core, params), parameters=parameters,
            weight=10)
        # initialize all parameters
        self.core.get("set_parameter_values")("toolpath_profile", parameters)
        return True

    def teardown(self):
        self.core.get("unregister_parameter_set")("toolpath_profile", "milling")


class ToolpathProfileLaser(pycam.Plugins.PluginBase):

    DEPENDS = ["Toolpaths", "GCodeFilenameExtension", "GCodeStepWidth", "GCodeCornerStyle"]
    CATEGORIES = ["Toolpath"]

    def setup(self):
        parameters = {"filename_extension": "",
                      "step_width_x": 0.0001,
                      "step_width_y": 0.0001,
                      "step_width_z": 0.0001,
                      # pick the first path mode
                      "path_mode": 0,
                      "motion_tolerance": 0.0,
                      "naive_tolerance": 0.0}
        self.core.get("register_parameter_set")(
            "toolpath_profile", "laser", "Laser",
            lambda params: _get_profile_filters(self.core, params), parameters=parameters,
            weight=50)
        # initialize all parameters
        self.core.get("set_parameter_values")("toolpath_profile", parameters)
        return True

    def teardown(self):
        self.core.get("unregister_parameter_set")("toolpath_profile", "laser")
