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
import pycam.Toolpath


class TaskTypeMilling(pycam.Plugins.PluginBase):

    DEPENDS = ["Tasks", "TaskParamCollisionModels", "TaskParamTool", "TaskParamProcess",
               "TaskParamBounds"]
    CATEGORIES = ["Task"]

    def setup(self):
        parameters = {"collision_models": [], "tool": None, "process": None, "bounds": None}
        self.core.get("register_parameter_set")("task", "milling", "Milling", self.run_task,
                                                parameters=parameters, weight=10)
        return True

    def teardown(self):
        self.core.get("unregister_parameter_set")("task", "milling")

    def run_task(self, task, callback=None):
        environment = {}
        for key in task["parameters"]:
            environment[key] = task["parameters"][key]
        if environment["tool"] is None:
            self.log.error("You need to assign a tool to this task.")
            return
        if environment["process"] is None:
            self.log.error("You need to assign a process to this task.")
            return
        if environment["bounds"] is None:
            self.log.error("You need to assign bounds to this task.")
            return
        funcs = {}
        for key, set_name in (("tool", "shape"), ("process", "strategy")):
            funcs[key] = self.core.get("get_parameter_sets")(
                key)[environment[key][set_name]]["func"]
        tool, tool_filters = funcs["tool"](environment["tool"]["parameters"])
        box = environment["bounds"].get_absolute_limits(tool_radius=tool.radius,
                                                        models=environment["collision_models"])
        path_generator, motion_grid = funcs["process"](environment["process"], tool.radius, box)
        if path_generator is None:
            # we assume that an error message was given already
            return
        models = [m.model for m in task["parameters"]["collision_models"]]
        if not models:
            # issue a warning - and go ahead ...
            self.log.warn("No collision model was selected. This can be intentional, but maybe "
                          "you simply forgot it.")
        moves = path_generator.GenerateToolPath(tool, models, motion_grid, minz=box.lower.z,
                                                maxz=box.upper.z, draw_callback=callback)
        if not moves:
            self.log.info("No valid moves found")
            return None
        return pycam.Toolpath.Toolpath(toolpath_path=moves, tool=tool,
                                       toolpath_filters=tool_filters)
