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


class TaskParamCollisionModels(pycam.Plugins.PluginBase):

    DEPENDS = ["Models", "Tasks"]
    CATEGORIES = ["Model", "Task", "Parameter"]

    def setup(self):
        self.input_control = pycam.Gui.ControlsGTK.InputTable([],
                change_handler=lambda widget=None: \
                    self.core.emit_event("task-changed"))
        self.input_control.get_widget().set_size_request(240, -1)
        self.core.get("register_parameter")("task", "models",
                "collision_models", "", self.input_control,
                weight=5)
        self.core.register_event("model-list-changed", self._update_models)
        return True

    def teardown(self):
        self.core.get("unregister_parameter")("task", "models",
                "collision_models")
        self.core.unregister_event("model-list-changed", self._update_models)

    def _update_models(self):
        choices = []
        models = self.core.get("models")
        for model in models:
            if hasattr(model, "triangles"):
                choices.append((models.get_attr(model, "name"), model))
        self.input_control.update_choices(choices)


class TaskParamTool(pycam.Plugins.PluginBase):

    DEPENDS = ["Tools", "Tasks"]
    CATEGORIES = ["Tool", "Task", "Parameter"]

    def setup(self):
        self.input_control = pycam.Gui.ControlsGTK.InputChoice([],
                change_handler=lambda widget=None: \
                    self.core.emit_event("task-changed"))
        self.core.get("register_parameter")("task", "components", "tool",
                "Tool", self.input_control, weight=10)
        self.core.register_event("tool-list-changed", self._update_tools)
        return True

    def teardown(self):
        self.core.get("unregister_parameter")("task", "components", "tool")
        self.core.unregister_event("tool-list-changed", self._update_tools)

    def _update_tools(self):
        choices = []
        tools = self.core.get("tools")
        for tool in tools:
            choices.append((tools.get_attr(tool, "name"), tool))
        self.input_control.update_choices(choices)


class TaskParamProcess(pycam.Plugins.PluginBase):

    DEPENDS = ["Processes", "Tasks"]
    CATEGORIES = ["Process", "Task", "Parameter"]

    def setup(self):
        self.input_control = pycam.Gui.ControlsGTK.InputChoice([],
                change_handler=lambda widget=None: \
                    self.core.emit_event("task-changed"))
        self.core.get("register_parameter")("task", "components", "process",
                "Process", self.input_control, weight=20)
        self.core.register_event("process-list-changed", self._update_processes)
        return True

    def teardown(self):
        self.core.get("unregister_parameter")("task", "components", "process")
        self.core.unregister_event("process-list-changed", self._update_processes)

    def _update_processes(self):
        choices = []
        processes = self.core.get("processes")
        for process in processes:
            choices.append((processes.get_attr(process, "name"), process))
        self.input_control.update_choices(choices)


class TaskParamBounds(pycam.Plugins.PluginBase):

    DEPENDS = ["Bounds", "Tasks"]
    CATEGORIES = ["Bounds", "Task", "Parameter"]

    def setup(self):
        self.input_control = pycam.Gui.ControlsGTK.InputChoice([],
                change_handler=lambda widget=None: \
                    self.core.emit_event("task-changed"))
        self.core.get("register_parameter")("task", "components", "bounds",
                "Bounds", self.input_control, weight=30)
        self.core.register_event("bounds-list-changed", self._update_bounds)
        return True

    def teardown(self):
        self.core.get("unregister_parameter")("task", "components", "bounds")
        self.core.unregister_event("bounds-list-changed", self._update_bounds)

    def _update_bounds(self):
        choices = []
        bounds = self.core.get("bounds")
        for bound in bounds:
            choices.append((bounds.get_attr(bound, "name"), bound))
        self.input_control.update_choices(choices)

