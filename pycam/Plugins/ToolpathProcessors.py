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


class ToolpathProcessors(pycam.Plugins.PluginBase):

    DEPENDS = ["Toolpaths", "ParameterGroupManager"]
    CATEGORIES = ["ExportSettings", "Toolpath"]

    def setup(self):
        if self._gtk:
            self.core.register_ui_section(
                "gcode_preferences",
                lambda item, name: self.core.register_ui("export_settings_handling", name, item),
                lambda: self.core.clear_ui_section("export_settings_handling"))
            general_widget = pycam.Gui.ControlsGTK.ParameterSection()
            general_widget.get_widget().show()
            self.core.register_ui_section("gcode_general_parameters", general_widget.add_widget,
                                          general_widget.clear_widgets)
            self.core.register_ui("gcode_preferences", "General", general_widget.get_widget())
            self._proc_selector = pycam.Gui.ControlsGTK.InputChoice(
                [], change_handler=lambda widget=None: self.core.emit_event(
                    "toolpath-processor-selection-changed"))
            proc_widget = self._proc_selector.get_widget()
            self.core.register_ui("gcode_general_parameters", "GCode Profile", proc_widget)
            proc_widget.show()
            self.core.get("register_parameter_group")(
                "toolpath_processor", changed_set_event="toolpath-processor-selection-changed",
                changed_set_list_event="toolpath-processor-list-changed",
                get_current_set_func=self.get_selected)
            self._event_handlers = (
                ("toolpath-processor-list-changed", self._update_processors),
                ("notify-initialization-finished", self._select_first_processor))
            self.register_event_handlers(self._event_handlers)
            self._update_processors()
        self.core.set("toolpath_processors", self)
        return True

    def teardown(self):
        self.core.set("toolpath_processors", None)
        self.unregister_event_handlers(self._event_handlers)
        self.core.get("unregister_parameter_group")("toolpath_processor")

    def _select_first_processor(self):
        # run this action as soon as all processors are registered
        processors = list(self.core.get("get_parameter_sets")("toolpath_processor").values())
        if processors:
            first = sorted(processors, key=lambda item: item["weight"])[0]
            self.select(first)

    def get_selected(self):
        all_processors = self.core.get("get_parameter_sets")("toolpath_processor")
        current_name = self._proc_selector.get_value()
        return all_processors.get(current_name, None)

    def select(self, item=None):
        if item is not None:
            item = item["name"]
        self._proc_selector.set_value(item)

    def _update_processors(self):
        selected = self.get_selected()
        processors = list(self.core.get("get_parameter_sets")("toolpath_processor").values())
        choices = []
        for processor in sorted(processors, key=lambda item: item["weight"]):
            choices.append((processor["label"], processor["name"]))
        self._proc_selector.update_choices(choices)
        if selected:
            self.select(selected)
        elif processors:
            self.select(None)
        else:
            pass


def _get_processor_filters(core, parameters):
    filters = []
    core.call_chain("toolpath_filters", "settings", parameters, filters)
    return filters


class ToolpathProcessorMilling(pycam.Plugins.PluginBase):

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
            "toolpath_processor", "milling", "Milling",
            lambda params: _get_processor_filters(self.core, params), parameters=parameters,
            weight=10)
        # initialize all parameters
        self.core.get("set_parameter_values")("toolpath_processor", parameters)
        return True

    def teardown(self):
        self.core.get("unregister_parameter_set")("toolpath_processor", "milling")


class ToolpathProcessorLaser(pycam.Plugins.PluginBase):

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
            "toolpath_processor", "laser", "Laser",
            lambda params: _get_processor_filters(self.core, params), parameters=parameters,
            weight=50)
        # initialize all parameters
        self.core.get("set_parameter_values")("toolpath_processor", parameters)
        return True

    def teardown(self):
        self.core.get("unregister_parameter_set")("toolpath_processor", "laser")
