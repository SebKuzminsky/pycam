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


class PathParamOverlap(pycam.Plugins.PluginBase):

    DEPENDS = ["ProcessStrategyManager"]

    def setup(self):
        # TODO: check if gtk is in use
        self.core.get("register_pathgenerator_parameter")("overlap",
                "Overlap [%]", pycam.Gui.ControlsGTK.InputNumber(
                    lower=0, upper=99, digits=0,
                    change_handler=lambda widget=None: self.core.emit_event(
                            "pathgenerator-parameter-changed")),
                    weight=10)
        return True

    def teardown(self):
        self.core.get("unregister_pathgenerator_parameter")("overlap")


class PathParamStepDown(pycam.Plugins.PluginBase):

    DEPENDS = ["ProcessStrategyManager"]

    def setup(self):
        # TODO: check if gtk is in use
        self.core.get("register_pathgenerator_parameter")("step_down",
                "Step down", pycam.Gui.ControlsGTK.InputNumber(lower=0.01,
                upper=1000, digits=2, start=1,
                change_handler=lambda widget=None: \
                    self.core.emit_event("pathgenerator-parameter-changed")),
                weight=20)
        return True

    def teardown(self):
        self.core.get("unregister_pathgenerator_parameter")("step_down")


class PathParamMaterialAllowance(pycam.Plugins.PluginBase):

    DEPENDS = ["ProcessStrategyManager"]

    def setup(self):
        # TODO: check if gtk is in use
        self.core.get("register_pathgenerator_parameter")("material_allowance",
                "Material allowance", pycam.Gui.ControlsGTK.InputNumber(
                    start=0, lower=0, upper=100, digits=2,
                    change_handler=lambda widget=None: self.core.emit_event(
                            "pathgenerator-parameter-changed")),
                    weight=30)
        return True

    def teardown(self):
        self.core.get("unregister_pathgenerator_parameter")("overlap")


class PathParamMillingStyle(pycam.Plugins.PluginBase):

    DEPENDS = ["ProcessStrategyManager"]

    def setup(self):
        # TODO: check if gtk is in use
        input_control = pycam.Gui.ControlsGTK.InputChoice(
                    (("ignore", "ignore"),
                    ("climb / down", "climb"),
                    ("conventional / up", "conventional")),
                change_handler=lambda widget=None: self.core.emit_event(
                        "pathgenerator-parameter-changed"))
        self.core.get("register_pathgenerator_parameter")("milling_style",
                "Milling style", input_control, weight=50)
        return True

    def teardown(self):
        self.core.get("unregister_pathgenerator_parameter")("milling_style")


class PathParamGridDirection(pycam.Plugins.PluginBase):

    DEPENDS = ["ProcessStrategyManager"]

    def setup(self):
        # TODO: check if gtk is in use
        input_control = pycam.Gui.ControlsGTK.InputChoice(
                (("x", "x"), ("y", "y"), ("xy", "xy")),
                change_handler=lambda widget=None: self.core.emit_event(
                        "pathgenerator-parameter-changed"))
        self.core.get("register_pathgenerator_parameter")("grid_direction",
                "Direction", input_control, weight=40)
        return True

    def teardown(self):
        self.core.get("unregister_pathgenerator_parameter")("grid_direction")


class PathParamRadiusCompensation(pycam.Plugins.PluginBase):

    DEPENDS = ["ProcessStrategyManager"]

    def setup(self):
        # TODO: check if gtk is in use
        self.core.get("register_pathgenerator_parameter")("radius_compensation",
                "Radius compensation",
                pycam.Gui.ControlsGTK.InputCheckBox(
                    change_handler=lambda widget=None: self.core.emit_event(
                            "pathgenerator-parameter-changed")),
                weight=80)
        return True

    def teardown(self):
        self.core.get("unregister_pathgenerator_parameter")("radius_compensation")


class PathParamTraceModel(pycam.Plugins.PluginBase):

    DEPENDS = ["ProcessStrategyManager", "Models"]

    def setup(self):
        class InputModelSelection(pycam.Gui.ControlsGTK.InputChoice):
            def get_value(inner_self):
                ref = super(InputModelSelection, inner_self).get_value()
                for model in self.core.get("models"):
                    if id(model) == ref:
                        return model
                return None
        # TODO: check if gtk is in use
        self.input_control = InputModelSelection([], force_type=long,
                change_handler=lambda widget=None: self.core.emit_event(
                        "pathgenerator-parameter-changed"))
        self.input_control
        self.core.get("register_pathgenerator_parameter")("trace_model",
                "Trace model", self.input_control, weight=5)
        self.core.register_event("model-list-changed", self._update_models)
        return True

    def _update_models(self):
        choices = []
        models = self.core.get("models")
        for model in models:
            if hasattr(model, "get_polygons"):
                choices.append((models.get_attr(model, "name"), id(model)))
        self.input_control.update_choices(choices)

    def teardown(self):
        self.core.get("unregister_pathgenerator_parameter")("trace_model")

