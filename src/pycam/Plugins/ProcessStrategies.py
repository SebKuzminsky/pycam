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
import pycam.PathGenerators.PushCutter
import pycam.PathProcessors.PathAccumulator
import pycam.Toolpath.MotionGrid


class ProcessStrategySlicing(pycam.Plugins.PluginBase):

    DEPENDS = ["ParameterGroupManager", "PathParamOverlap",
            "PathParamStepDown", "PathParamMaterialAllowance",
            "PathParamMillingStyle", "PathParamGridDirection"]
    CATEGORIES = ["Process"]

    def setup(self):
        parameters = {"overlap": 0.1,
                "step_down": 1.0,
                "material_allowance": 0,
                "milling_style": pycam.Toolpath.MotionGrid.MILLING_STYLE_IGNORE,
                "grid_direction": pycam.Toolpath.MotionGrid.GRID_DIRECTION_X,
        }
        self.core.get("register_parameter_set")("process", "slicing",
                "Slice removal", self.run_process, parameters=parameters,
                weight=10)
        return True

    def teardown(self):
        self.core.get("unregister_parameter_set")("process", "slicing")

    def run_process(self, process, environment=None):
        tool = environment["tool"]
        tool_params = tool["parameters"]
        low, high = environment["bounds"].get_absolute_limits(
                tool=tool, models=environment["collision_models"])
        line_distance = 2 * tool_params["radius"] * \
                (1.0 - process["parameters"]["overlap"])
        path_generator = pycam.PathGenerators.PushCutter.PushCutter(
                pycam.PathProcessors.PathAccumulator.PathAccumulator())
        motion_grid = pycam.Toolpath.MotionGrid.get_fixed_grid(
                (low, high), process["parameters"]["step_down"],
                line_distance=line_distance,
                grid_direction=process["parameters"]["grid_direction"],
                milling_style=process["parameters"]["milling_style"])
        return path_generator, motion_grid, (low, high)


class ProcessStrategyContour(pycam.Plugins.PluginBase):

    DEPENDS = ["Processes", "PathParamStepDown",
            "PathParamMaterialAllowance", "PathParamMillingStyle"]
    CATEGORIES = ["Process"]

    def setup(self):
        parameters = {"step_down": 1.0,
                "material_allowance": 0,
                "milling_style": pycam.Toolpath.MotionGrid.MILLING_STYLE_IGNORE,
        }
        self.core.get("register_parameter_set")("process", "contour",
                "Waterline", self.run_process, parameters=parameters,
                weight=20)
        return True

    def teardown(self):
        self.core.get("unregister_parameter_set")("process", "contour")

    def run_process(self, strategy, environment=None):
        pass


class ProcessStrategySurfacing(pycam.Plugins.PluginBase):

    DEPENDS = ["ParameterGroupManager", "PathParamOverlap",
            "PathParamMaterialAllowance", "PathParamMillingStyle",
            "PathParamGridDirection"]
    CATEGORIES = ["Process"]

    def setup(self):
        parameters = {"overlap": 0.6,
                "material_allowance": 0,
                "milling_style": pycam.Toolpath.MotionGrid.MILLING_STYLE_IGNORE,
                "grid_direction": pycam.Toolpath.MotionGrid.GRID_DIRECTION_X,
        }
        self.core.get("register_parameter_set")("process", "surfacing",
                "Surfacing", self.run_process, parameters=parameters,
                weight=50)
        return True

    def teardown(self):
        self.core.get("unregister_parameter_set")("process", "surfacing")

    def run_process(self, process, environment=None):
        tool = environment["tool"]
        tool_params = tool["parameters"]
        low, high = environment["bounds"].get_absolute_limits(
                tool=tool, models=environment["collision_models"])
        line_distance = 2 * tool_params["radius"] * \
                (1.0 - process["parameters"]["overlap"])
        path_generator = pycam.PathGenerators.DropCutter.DropCutter(
                pycam.PathProcessors.PathAccumulator.PathAccumulator())
        motion_grid = pycam.Toolpath.MotionGrid.get_fixed_grid(
                (low, high), process["parameters"]["step_down"],
                line_distance=line_distance,
                step_width=(tool_params["radius"] / 4.0),
                grid_direction=process["parameters"]["grid_direction"],
                milling_style=process["parameters"]["milling_style"])
        return path_generator, motion_grid, (low, high)


class ProcessStrategyEngraving(pycam.Plugins.PluginBase):

    DEPENDS = ["ParameterGroupManager", "PathParamStepDown",
            "PathParamMillingStyle", "PathParamRadiusCompensation",
            "PathParamTraceModel"]
    CATEGORIES = ["Process"]

    def setup(self):
        parameters = {"step_down": 1.0,
                "milling_style": pycam.Toolpath.MotionGrid.MILLING_STYLE_IGNORE,
                "radius_compensation": False,
                "trace_models": [],
        }
        self.core.get("register_parameter_set")("process", "engraving",
                "Engraving", self.run_process, parameters=parameters,
                weight=80)
        return True

    def teardown(self):
        self.core.get("unregister_parameter_set")("process", "engraving")

    def run_process(self, process, environment=None):
        tool = environment["tool"]
        tool_params = tool["parameters"]
        low, high = environment["bounds"].get_absolute_limits(
                tool=tool, models=environment["collision_models"])
        path_generator = pycam.PathGenerators.EngraveCutter.EngraveCutter(
                pycam.PathProcessors.SimpleCutter.SimpleCutter())
        models = list(process["parameters"]["trace_models"])
        progress = self.core.get("progress")
        if process["parameters"]["radius_compensation"]:
            progress.update(text="Offsetting models")
            progress.set_multiple(len(models), "Model")
            compensated_models = []
            for index in range(len(models)):
                models[index] = models[index].get_offset_model(
                        tool_params["radius"], callback=progress.update)
                progress.update_multiple()
            progress.finish()
        progress.update(text="Calculating moves")
        motion_grid = pycam.Toolpath.MotionGrid.get_lines_grid(models,
                (low, high), process["parameters"]["step_down"],
                step_width=(tool_params["radius"] / 4.0),
                milling_style=process["parameters"]["milling_style"],
                callback=progress.update)
        progress.finish()
        return path_generator, motion_grid, (low, high)

