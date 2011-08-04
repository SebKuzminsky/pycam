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


class TaskTypeMilling(pycam.Plugins.PluginBase):

    DEPENDS = ["Tasks", "TaskParamCollisionModels", "TaskParamTool",
            "TaskParamProcess", "TaskParamBounds"]

    def setup(self):
        parameters = {"collision_models": [],
                "tool": None,
                "process": None,
                "bounds": None,
        }
        self.core.get("register_parameter_set")("task", "milling",
                "Milling", self.run_task, parameters=parameters,
                weight=10)
        return True

    def teardown(self):
        self.core.get("unregister_parameter_set")("task", "milling")

    def run_task(self, task, callback=None):
        environment = {}
        for key in task["parameters"]:
            environment[key] = task["parameters"][key]
        funcs = {}
        for key, set_name in (("tool", "shape"), ("process", "strategy")):
            funcs[key] = self.core.get("get_parameter_sets")(
                    key)[environment[key][set_name]]["func"]
        tool = funcs["tool"](tool=environment["tool"], environment=environment)
        path_generator, motion_grid, (low, high) = funcs["process"](
                environment["process"], environment=environment)
        models = task["parameters"]["collision_models"]
        moves = path_generator.GenerateToolPath(tool, models, motion_grid,
                minz=low[2], maxz=high[2], draw_callback=callback)
        data = {}
        for item_name in ("tool", "process", "bounds"):
            self.core.call_chain("get_toolpath_information",
                    environment[item_name], data)
        tp = pycam.Toolpath.Toolpath(moves, parameters=data)
        return tp

