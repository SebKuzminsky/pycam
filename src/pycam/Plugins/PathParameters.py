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
import pycam.Toolpath.MotionGrid


class PathParamOverlap(pycam.Plugins.PluginBase):

    DEPENDS = ["Processes"]

    def setup(self):
        # configure the input/output converter
        widget = pycam.Gui.ControlsGTK.InputNumber(lower=0, upper=99, digits=0,
                increment=10, change_handler=lambda widget=None: \
                    self.core.emit_event("process-changed"))
        widget.set_conversion(
                set_conv=lambda float_value: int(float_value * 100.0),
                get_conv=lambda percent: percent / 100.0)
        self.core.get("register_parameter")("process", "pathgenerator",
                "overlap", "Overlap [%]", widget, weight=10)
        return True

    def teardown(self):
        self.core.get("unregister_parameter")("process", "pathgenerator",
                "overlap")


class PathParamStepDown(pycam.Plugins.PluginBase):

    DEPENDS = ["Processes"]

    def setup(self):
        widget = pycam.Gui.ControlsGTK.InputNumber(lower=0.01, upper=1000,
                digits=2, start=1, change_handler=lambda widget=None: \
                    self.core.emit_event("process-changed"))
        self.core.get("register_parameter")("process", "pathgenerator",
                "step_down", "Step down", widget, weight=20)
        return True

    def teardown(self):
        self.core.get("unregister_parameter")("process", "pathgenerator",
                "step_down")


class PathParamMaterialAllowance(pycam.Plugins.PluginBase):

    DEPENDS = ["Processes"]

    def setup(self):
        widget = pycam.Gui.ControlsGTK.InputNumber(start=0, lower=0, upper=100,
                digits=2, change_handler=lambda widget=None: \
                    self.core.emit_event("process-changed"))
        self.core.get("register_parameter")("process", "pathgenerator",
                "material_allowance", "Material allowance", widget, weight=30)
        return True

    def teardown(self):
        self.core.get("unregister_parameter")("process", "pathgenerator",
                "material_allowance")


class PathParamMillingStyle(pycam.Plugins.PluginBase):

    DEPENDS = ["Processes"]

    def setup(self):
        input_control = pycam.Gui.ControlsGTK.InputChoice(
                    (("ignore", pycam.Toolpath.MotionGrid.MILLING_STYLE_IGNORE),
                    ("climb / down", pycam.Toolpath.MotionGrid.MILLING_STYLE_CLIMB),
                    ("conventional / up", pycam.Toolpath.MotionGrid.MILLING_STYLE_CONVENTIONAL)),
                change_handler=lambda widget=None: self.core.emit_event(
                        "process-changed"))
        self.core.get("register_parameter")("process", "pathgenerator",
                "milling_style", "Milling style", input_control, weight=50)
        return True

    def teardown(self):
        self.core.get("unregister_parameter")("process", "pathgenerator",
                "milling_style")


class PathParamGridDirection(pycam.Plugins.PluginBase):

    DEPENDS = ["Processes"]

    def setup(self):
        input_control = pycam.Gui.ControlsGTK.InputChoice(
                    (("x", pycam.Toolpath.MotionGrid.GRID_DIRECTION_X),
                    ("y", pycam.Toolpath.MotionGrid.GRID_DIRECTION_Y),
                    ("xy", pycam.Toolpath.MotionGrid.GRID_DIRECTION_XY)),
                change_handler=lambda widget=None: self.core.emit_event(
                        "process-changed"))
        self.core.get("register_parameter")("process", "pathgenerator",
                "grid_direction", "Direction", input_control, weight=40)
        return True

    def teardown(self):
        self.core.get("unregister_parameter")("process", "pathgenerator",
                "grid_direction")


class PathParamRadiusCompensation(pycam.Plugins.PluginBase):

    DEPENDS = ["Processes"]

    def setup(self):
        widget = pycam.Gui.ControlsGTK.InputCheckBox(
                change_handler=lambda widget=None: self.core.emit_event(
                    "process-changed"))
        self.core.get("register_parameter")("process", "pathgenerator",
                "radius_compensation", "Radius compensation", widget, weight=80)
        return True

    def teardown(self):
        self.core.get("unregister_parameter")("process", "pathgenerator",
                "radius_compensation")


class PathParamTraceModel(pycam.Plugins.PluginBase):

    DEPENDS = ["Processes", "Models"]

    def setup(self):
        self.input_control = pycam.Gui.ControlsGTK.InputTable([],
                force_type=long, change_handler=lambda widget=None: \
                    self.core.emit_event("process-changed"))
        # configure the input/output converter
        def get_converter(model_refs):
            models_dict = {}
            for model in self.core.get("models"):
                models_dict[id(model)] = model
            models = []
            for model_ref in model_refs:
                models.append(models_dict[model_ref])
            return models
        def set_converter(models):
            return [id(model) for model in models]
        self.input_control.set_conversion(set_conv=set_converter,
                get_conv=get_converter)
        self.core.get("register_parameter")("process", "pathgenerator",
                "trace_models", "Trace models (2D)", self.input_control, weight=5)
        self.core.register_event("model-list-changed", self._update_models)
        return True

    def _update_models(self):
        choices = []
        models = self.core.get("models")
        for model in models:
            if hasattr(model, "get_polygons"):
                choices.append((models.get_attr(model, "name"), model))
        self.input_control.update_choices(choices)

    def teardown(self):
        self.core.get("unregister_parameter")("process", "pathgenerator",
                "trace_models")

