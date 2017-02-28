# -*- coding: utf-8 -*-
"""
Copyright 2011-2012 Lars Kruse <devel@sumpfralle.de>

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
import pycam.Toolpath.Filters as Filters
from pycam.Toolpath import CORNER_STYLE_EXACT_PATH, CORNER_STYLE_EXACT_STOP, \
        CORNER_STYLE_OPTIMIZE_SPEED, CORNER_STYLE_OPTIMIZE_TOLERANCE


class GCodeSafetyHeight(pycam.Plugins.PluginBase):

    DEPENDS = ["ToolpathProcessors"]
    CATEGORIES = ["GCode"]

    def setup(self):
        # TODO: update the current filters after a change
        self.control = pycam.Gui.ControlsGTK.InputNumber(
            digits=1, change_handler=lambda *args: self.core.emit_event("visual-item-updated"))
        self.core.get("register_parameter")("toolpath_processor", "safety_height", self.control)
        self.core.register_ui("gcode_general_parameters", "Safety Height",
                              self.control.get_widget(), weight=20)
        self.core.register_chain("toolpath_filters", self.get_toolpath_filters)
        return True

    def teardown(self):
        self.core.unregister_chain("toolpath_filters", self.get_toolpath_filters)
        self.core.unregister_ui("gcode_general_parameters", self.control.get_widget())
        self.core.get("unregister_parameter")("toolpath_processor", "safety_height")

    @Filters.toolpath_filter("settings", "safety_height")
    def get_toolpath_filters(self, safety_height):
        return [Filters.SafetyHeight(safety_height)]


class GCodePlungeFeedrate(pycam.Plugins.PluginBase):

    DEPENDS = ["ToolpathProcessors"]
    CATEGORIES = ["GCode"]

    def setup(self):
        self.control = pycam.Gui.ControlsGTK.InputNumber(digits=1)
        self.core.get("register_parameter")("toolpath_processor", "plunge_feedrate", self.control)
        self.core.register_ui("gcode_general_parameters", "Plunge feedrate limit",
                              self.control.get_widget(), weight=25)
        self.core.register_chain("toolpath_filters", self.get_toolpath_filters)
        return True

    def teardown(self):
        self.core.unregister_chain("toolpath_filters", self.get_toolpath_filters)
        self.core.unregister_ui("gcode_general_parameters", self.control.get_widget())
        self.core.get("unregister_parameter")("toolpath_processor", "plunge_feedrate")

    @Filters.toolpath_filter("settings", "plunge_feedrate")
    def get_toolpath_filters(self, plunge_feedrate):
        return [Filters.PlungeFeedrate(plunge_feedrate)]


# TODO: move to settings for ToolpathOutputDialects
class GCodeFilenameExtension(pycam.Plugins.PluginBase):

    DEPENDS = ["ToolpathProcessors"]
    CATEGORIES = ["GCode"]

    def setup(self):
        self.control = pycam.Gui.ControlsGTK.InputString(max_length=6)
        self.core.get("register_parameter")("toolpath_processor", "filename_extension",
                                            self.control)
        self.core.register_ui("gcode_general_parameters", "Custom GCode filename extension",
                              self.control.get_widget(), weight=80)
        return True

    def teardown(self):
        self.core.unregister_ui("gcode_general_parameters", self.control.get_widget())
        self.core.get("unregister_parameter")("toolpath_processor", "filename_extension")

    @Filters.toolpath_filter("settings", "filename_extension")
    def get_toolpath_filters(self, safety_height):
        # TODO: see above - move to ToolpathOutputDialects
        return []


class GCodeStepWidth(pycam.Plugins.PluginBase):

    DEPENDS = ["ToolpathProcessors"]
    CATEGORIES = ["GCode"]

    def setup(self):
        self._table = pycam.Gui.ControlsGTK.ParameterSection()
        self.core.register_ui("gcode_preferences", "Step precision", self._table.get_widget())
        self.core.register_ui_section("gcode_step_width", self._table.add_widget,
                                      self._table.clear_widgets)
        self.controls = []
        for key in "xyz":
            control = pycam.Gui.ControlsGTK.InputNumber(digits=8, start=0.0001, increment=0.00005,
                                                        lower=0.00000001)
            self.core.register_ui("gcode_step_width", key.upper(), control.get_widget(),
                                  weight="xyz".index(key))
            self.core.get("register_parameter")("toolpath_processor", "step_width_%s" % key,
                                                control)
            self.controls.append((key, control))
        self.core.register_chain("toolpath_filters", self.get_toolpath_filters)
        return True

    def teardown(self):
        self.core.unregister_chain("toolpath_filters", self.get_toolpath_filters)
        for key, control in self.controls:
            self.core.unregister_ui("gcode_step_width", control)
            self.core.get("unregister_parameter")("toolpath_processor", "step_width_%s" % key)
        self.core.unregister_ui("gcode_general_parameters", self._table.get_widget())

    @Filters.toolpath_filter("settings", ("step_width_x", "step_width_y", "step_width_z"))
    def get_toolpath_filters(self, **kwargs):
        return [Filters.StepWidth(**kwargs)]


class GCodeSpindle(pycam.Plugins.PluginBase):

    DEPENDS = ["ToolpathProcessors"]
    CATEGORIES = ["GCode"]

    def setup(self):
        self._table = pycam.Gui.ControlsGTK.ParameterSection()
        self.core.register_ui("gcode_preferences", "Spindle control", self._table.get_widget())
        self.core.register_ui_section("gcode_spindle", self._table.add_widget,
                                      self._table.clear_widgets)
        self.spindle_delay = pycam.Gui.ControlsGTK.InputNumber(digits=1, lower=0)
        self.core.register_ui("gcode_spindle", "Delay (in seconds) after start/stop",
                              self.spindle_delay.get_widget(), weight=50)
        self.core.get("register_parameter")("toolpath_processor", "spindle_delay",
                                            self.spindle_delay)
        self.spindle_enable = pycam.Gui.ControlsGTK.InputCheckBox(
            change_handler=self.update_widgets)
        self.core.register_ui("gcode_spindle", "Start / Stop Spindle (M3/M5)",
                              self.spindle_enable.get_widget(), weight=10)
        self.core.get("register_parameter")("toolpath_processor", "spindle_enable",
                                            self.spindle_enable)
        self.core.register_chain("toolpath_filters", self.get_toolpath_filters)
        self.update_widgets()
        return True

    def teardown(self):
        self.core.unregister_chain("toolpath_filters", self.get_toolpath_filters)
        self.core.unregister_ui("gcode_spindle", self.spindle_delay.get_widget())
        self.core.unregister_ui("gcode_spindle", self.spindle_enable.get_widget())
        self.core.unregister_ui_section("gcode_spindle")
        self.core.unregister_ui("gcode_preferences", self._table.get_widget())
        self.core.get("unregister_parameter")("toolpath_processor", "spindle_enable")
        self.core.get("unregister_parameter")("toolpath_processor", "spindle_delay")

    def update_widgets(self, widget=None):
        widget = self.spindle_delay.get_widget()
        widget.set_sensitive(self.spindle_enable.get_value())

    @Filters.toolpath_filter("settings", ("spindle_enable", "spindle_delay"))
    def get_toolpath_filters(self, spindle_enable=False, spindle_delay=0):
        if spindle_enable:
            return [Filters.TriggerSpindle(spindle_delay)]
        else:
            return []


class GCodeCornerStyle(pycam.Plugins.PluginBase):

    DEPENDS = ["ToolpathProcessors"]
    CATEGORIES = ["GCode"]

    def setup(self):
        self._table = pycam.Gui.ControlsGTK.ParameterSection()
        self.core.register_ui("gcode_preferences", "Corner style", self._table.get_widget())
        self.core.register_ui_section("gcode_corner_style", self._table.add_widget,
                                      self._table.clear_widgets)
        self.motion_tolerance = pycam.Gui.ControlsGTK.InputNumber(digits=3, lower=0)
        self.core.register_ui("gcode_corner_style", "Motion blending tolerance",
                              self.motion_tolerance.get_widget(), weight=30)
        self.core.get("register_parameter")("toolpath_processor", "motion_tolerance",
                                            self.motion_tolerance)
        self.naive_tolerance = pycam.Gui.ControlsGTK.InputNumber(digits=3, lower=0)
        self.core.register_ui("gcode_corner_style", "Naive CAM tolerance",
                              self.naive_tolerance.get_widget(), weight=50)
        self.core.get("register_parameter")("toolpath_processor", "naive_tolerance",
                                            self.naive_tolerance)
        self.path_mode = pycam.Gui.ControlsGTK.InputChoice((
            ("Exact path mode (G61)", CORNER_STYLE_EXACT_PATH),
            ("Exact stop mode (G61.1)", CORNER_STYLE_EXACT_STOP),
            ("Continuous with maximum speed (G64)", CORNER_STYLE_OPTIMIZE_SPEED),
            ("Continuous with tolerance (G64 P/Q)", CORNER_STYLE_OPTIMIZE_TOLERANCE)))
        self.path_mode.get_widget().connect("changed", self.update_widgets)
        self.core.register_ui("gcode_corner_style", "Path mode", self.path_mode.get_widget(),
                              weight=10)
        self.core.get("register_parameter")("toolpath_processor", "path_mode", self.path_mode)
        self.core.register_chain("toolpath_filters", self.get_toolpath_filters)
        self.update_widgets()
        return True

    def teardown(self):
        self.core.unregister_chain("toolpath_filters", self.get_toolpath_filters)
        self.core.unregister_ui("gcode_corner_style", self.motion_tolerance.get_widget())
        self.core.unregister_ui("gcode_corner_style", self.naive_tolerance.get_widget())
        self.core.unregister_ui("gcode_corner_style", self.path_mode.get_widget())
        self.core.unregister_ui_section("gcode_corner_style")
        self.core.unregister_ui("gcode_preferences", self._table.get_widget())
        for name in ("motion_tolerance", "naive_tolerance", "path_mode"):
            self.core.get("unregister_parameter")("toolpath_processor", name)

    def update_widgets(self, widget=None):
        enable_tolerances = (self.path_mode.get_value() == CORNER_STYLE_OPTIMIZE_TOLERANCE)
        controls = (self.motion_tolerance, self.naive_tolerance)
        for control in controls:
            control.get_widget().set_sensitive(enable_tolerances)

    @Filters.toolpath_filter("settings", ("path_mode", "motion_tolerance", "naive_tolerance"))
    def get_toolpath_filters(self, path_mode=CORNER_STYLE_EXACT_PATH, motion_tolerance=0,
                             naive_tolerance=0):
        return [Filters.PathMode(path_mode, motion_tolerance, naive_tolerance)]
