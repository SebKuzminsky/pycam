# -*- coding: utf-8 -*-
"""
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
import pycam.Gui.ControlsGTK
from pycam.Toolpath.Filters import toolpath_filter


class ToolParamRadius(pycam.Plugins.PluginBase):

    DEPENDS = ["Tools"]
    CATEGORIES = ["Tool", "Parameter"]

    def setup(self):
        self.control = pycam.Gui.ControlsGTK.InputNumber(
            lower=0.001, digits=4,
            change_handler=lambda widget=None: self.core.emit_event("tool-changed"))
        self.control.set_conversion(set_conv=lambda value: value * 2.0,
                                    get_conv=lambda value: value / 2.0)
        self.core.get("register_parameter")("tool", "radius", self.control)
        self.core.register_ui("tool_size", "Tool Diameter", self.control.get_widget(), weight=10)
        return True

    def teardown(self):
        self.core.get("unregister_parameter")("tool", "radius")
        self.core.unregister_ui("tool_size", self.control.get_widget())


class ToolParamTorusRadius(pycam.Plugins.PluginBase):

    DEPENDS = ["Tools"]
    CATEGORIES = ["Tool", "Parameter"]

    def setup(self):
        self.control = pycam.Gui.ControlsGTK.InputNumber(
            lower=0.001, digits=4,
            change_handler=lambda widget=None: self.core.emit_event("tool-changed"))
        self.core.get("register_parameter")("tool", "torus_radius", self.control)
        self.core.register_ui("tool_size", "Torus Radius", self.control.get_widget(), weight=50)
        return True

    def teardown(self):
        self.core.unregister_ui("tool_size", self.control.get_widget())
        self.core.get("unregister_parameter")("tool", "torus_radius")


class ToolParamFeedrate(pycam.Plugins.PluginBase):

    DEPENDS = ["Tools"]
    CATEGORIES = ["Tool", "Parameter"]

    def setup(self):
        self.control = pycam.Gui.ControlsGTK.InputNumber(
            lower=1, digits=0,
            change_handler=lambda widget=None: self.core.emit_event("tool-changed"))
        self.core.get("register_parameter")("tool", "feedrate", self.control)
        self.core.register_ui("tool_speed", "Feedrate", self.control.get_widget(), weight=10)
        self.core.register_chain("toolpath_filters", self.get_toolpath_filters)
        return True

    def teardown(self):
        self.core.unregister_ui("tool_speed", self.control.get_widget())
        self.core.get("unregister_parameter")("tool", "feedrate")
        self.core.unregister_chain("toolpath_filters", self.get_toolpath_filters)

    @toolpath_filter("tool", "feedrate")
    def get_toolpath_filters(self, feedrate):
        return [pycam.Toolpath.Filters.MachineSetting("feedrate", feedrate)]


class ToolParamSpindleSpeed(pycam.Plugins.PluginBase):

    DEPENDS = ["Tools"]
    CATEGORIES = ["Tool", "Parameter"]

    def setup(self):
        self.control = pycam.Gui.ControlsGTK.InputNumber(
            lower=1, digits=0,
            change_handler=lambda widget=None: self.core.emit_event("tool-changed"))
        self.core.get("register_parameter")("tool", "spindle_speed", self.control)
        self.core.register_ui("tool_speed", "Spindle Speed", self.control.get_widget(), weight=50)
        self.core.register_chain("toolpath_filters", self.get_toolpath_filters)
        return True

    def teardown(self):
        self.core.unregister_ui("tool_speed", self.control.get_widget())
        self.core.get("unregister_parameter")("tool", "spindle_speed")
        self.core.unregister_chain("toolpath_filters", self.get_toolpath_filters)

    @toolpath_filter("tool", "spindle_speed")
    def get_toolpath_filters(self, spindle_speed):
        return [pycam.Toolpath.Filters.MachineSetting("spindle_speed", spindle_speed)]
