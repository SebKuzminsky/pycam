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
import pycam.Gui.ControlsGTK


class ToolParamRadius(pycam.Plugins.PluginBase):

    DEPENDS = ["Tools"]

    def setup(self):
        control = pycam.Gui.ControlsGTK.InputNumber(lower=0, upper=99, digits=0,
                change_handler=lambda widget=None: self.core.emit_event(
                    "tool-parameter-changed"))
        control.set_conversion(set_conv=lambda value: value * 2.0,
                get_conv=lambda value: value / 2.0)
        self.core.get("register_parameter")("tool", "size", "radius",
                "Tool diameter", control, weight=10)
        return True

    def teardown(self):
        self.core.get("unregister_parameter")("tool", "size", "radius")


class ToolParamTorusRadius(pycam.Plugins.PluginBase):

    DEPENDS = ["Tools"]

    def setup(self):
        control = pycam.Gui.ControlsGTK.InputNumber(lower=0, upper=99, digits=0,
                change_handler=lambda widget=None: self.core.emit_event(
                    "tool-parameter-changed"))
        self.core.get("register_parameter")("tool", "size", "torus_radius",
                "Torus radius", control, weight=20)
        return True

    def teardown(self):
        self.core.get("unregister_parameter")("tool", "size", "torus_radius")


class ToolParamFeedrate(pycam.Plugins.PluginBase):

    DEPENDS = ["Tools"]

    def setup(self):
        control = pycam.Gui.ControlsGTK.InputNumber(lower=0, upper=10000,
                digits=0, change_handler=lambda widget=None: \
                    self.core.emit_event("tool-parameter-changed"))
        self.core.get("register_parameter")("tool", "speed", "feedrate",
                "Feedrate", control, weight=10)
        return True

    def teardown(self):
        self.core.get("unregister_parameter")("tool", "speed", "feedrate")


class ToolParamSpindleSpeed(pycam.Plugins.PluginBase):

    DEPENDS = ["Tools"]

    def setup(self):
        control = pycam.Gui.ControlsGTK.InputNumber(lower=0, upper=100000,
                digits=0, change_handler=lambda widget=None: \
                    self.core.emit_event("tool-parameter-changed"))
        self.core.get("register_parameter")("tool", "speed", "spindle_speed",
                "Spindle speed", control, weight=20)
        return True

    def teardown(self):
        self.core.get("unregister_parameter")("tool", "speed", "spindle_speed")

