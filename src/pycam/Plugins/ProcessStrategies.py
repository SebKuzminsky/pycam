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


class ProcessStrategySlicing(pycam.Plugins.PluginBase):

    DEPENDS = ["ParameterGroupManager", "PathParamOverlap",
            "PathParamStepDown", "PathParamMaterialAllowance",
            "PathParamMillingStyle", "PathParamGridDirection"]

    def setup(self):
        parameters = {"overlap": 0.1,
                "step_down": 1.0,
                "material_allowance": 0,
                "milling_style": "ignore",
                "grid_direction": "x",
        }
        self.core.get("register_parameter_set")("process", "slicing",
                "Slice removal", self.run_strategy, parameters=parameters,
                weight=10)
        return True

    def teardown(self):
        self.core.get("unregister_strategy")("slicing")

    def run_strategy(self):
        pass


class ProcessStrategyContour(pycam.Plugins.PluginBase):

    DEPENDS = ["Processes", "PathParamStepDown",
            "PathParamMaterialAllowance", "PathParamMillingStyle"]

    def setup(self):
        parameters = {"step_down": 1.0,
                "material_allowance": 0,
                "milling_style": "ignore",
        }
        self.core.get("register_parameter_set")("process", "contour",
                "Waterline", self.run_strategy, parameters=parameters,
                weight=20)
        return True

    def teardown(self):
        self.core.get("unregister_parameter_set")("process", "contour")

    def run_strategy(self):
        pass


class ProcessStrategySurfacing(pycam.Plugins.PluginBase):

    DEPENDS = ["ParameterGroupManager", "PathParamOverlap",
            "PathParamMaterialAllowance", "PathParamMillingStyle",
            "PathParamGridDirection"]

    def setup(self):
        parameters = {"overlap": 0.6,
                "material_allowance": 0,
                "milling_style": "ignore",
                "grid_direction": "x",
        }
        self.core.get("register_parameter_set")("process", "surfacing",
                "Surfacing", self.run_strategy, parameters=parameters,
                weight=50)
        return True

    def teardown(self):
        self.core.get("unregister_strategy")("surfacing")

    def run_strategy(self):
        pass


class ProcessStrategyEngraving(pycam.Plugins.PluginBase):

    DEPENDS = ["ParameterGroupManager", "PathParamStepDown",
            "PathParamMillingStyle", "PathParamRadiusCompensation",
            "PathParamTraceModel"]

    def setup(self):
        parameters = {"step_down": 1.0,
                "milling_style": "ignore",
                "radius_compensation": False,
                "trace_models": [],
        }
        self.core.get("register_parameter_set")("process", "engraving",
                "Engraving", self.run_strategy, parameters=parameters,
                weight=80)
        return True

    def teardown(self):
        self.core.get("unregister_strategy")("engraving")

    def run_strategy(self):
        pass


