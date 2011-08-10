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
    CATEGORIES = ["Process", "Parameter"]

    def setup(self):
        # configure the input/output converter
        self.control = pycam.Gui.ControlsGTK.InputNumber(lower=0, upper=99,
                digits=0, increment=10, change_handler=lambda widget=None: \
                    self.core.emit_event("process-changed"))
        self.control.set_conversion(
                set_conv=lambda float_value: int(float_value * 100.0),
                get_conv=lambda percent: percent / 100.0)
        self.core.get("register_parameter")("process", "overlap",
                self.control)
        self.core.register_ui("process_path_parameters", "Overlap [%]",
                self.control.get_widget(), weight=10)
        return True

    def teardown(self):
        self.core.unregister_ui("process_path_parameters", self.control.get_widget())
        self.core.get("unregister_parameter")("process", "overlap")


class PathParamStepDown(pycam.Plugins.PluginBase):

    DEPENDS = ["Processes"]
    CATEGORIES = ["Process", "Parameter"]

    def setup(self):
        self.control = pycam.Gui.ControlsGTK.InputNumber(lower=0.01,
                upper=1000, digits=2, start=1,
                change_handler=lambda widget=None: \
                    self.core.emit_event("process-changed"))
        self.core.get("register_parameter")("process", "step_down",
                self.control)
        self.core.register_ui("process_path_parameters", "Step down",
                self.control.get_widget(), weight=20)
        return True

    def teardown(self):
        self.core.unregister_ui("process_path_parameters", self.control.get_widget())
        self.core.get("unregister_parameter")("process", "step_down")


class PathParamMaterialAllowance(pycam.Plugins.PluginBase):

    DEPENDS = ["Processes"]
    CATEGORIES = ["Process", "Parameter"]

    def setup(self):
        self.control = pycam.Gui.ControlsGTK.InputNumber(start=0, lower=0,
                upper=100, digits=2, change_handler=lambda widget=None: \
                    self.core.emit_event("process-changed"))
        self.core.get("register_parameter")("process", "material_allowance",
                self.control)
        self.core.register_ui("process_path_parameters", "Material allowance",
                self.control.get_widget(), weight=30)
        return True

    def teardown(self):
        self.core.unregister_ui("process_path_parameters", self.control.get_widget())
        self.core.get("unregister_parameter")("process", "material_allowance")


class PathParamMillingStyle(pycam.Plugins.PluginBase):

    DEPENDS = ["Processes"]
    CATEGORIES = ["Process", "Parameter"]

    def setup(self):
        self.control = pycam.Gui.ControlsGTK.InputChoice(
                    (("ignore", pycam.Toolpath.MotionGrid.MILLING_STYLE_IGNORE),
                    ("climb / down", pycam.Toolpath.MotionGrid.MILLING_STYLE_CLIMB),
                    ("conventional / up", pycam.Toolpath.MotionGrid.MILLING_STYLE_CONVENTIONAL)),
                change_handler=lambda widget=None: self.core.emit_event(
                        "process-changed"))
        self.core.get("register_parameter")("process", "milling_style",
                self.control)
        self.core.register_ui("process_path_parameters", "Milling style",
                self.control.get_widget(), weight=50)
        return True

    def teardown(self):
        self.core.unregister_ui("process_path_parameters", self.control.get_widget())
        self.core.get("unregister_parameter")("process", "milling_style")


class PathParamGridDirection(pycam.Plugins.PluginBase):

    DEPENDS = ["Processes"]
    CATEGORIES = ["Process", "Parameter"]

    def setup(self):
        self.control = pycam.Gui.ControlsGTK.InputChoice(
                    (("x", pycam.Toolpath.MotionGrid.GRID_DIRECTION_X),
                    ("y", pycam.Toolpath.MotionGrid.GRID_DIRECTION_Y),
                    ("xy", pycam.Toolpath.MotionGrid.GRID_DIRECTION_XY)),
                change_handler=lambda widget=None: self.core.emit_event(
                        "process-changed"))
        self.core.get("register_parameter")("process", "grid_direction",
                self.control)
        self.core.register_ui("process_path_parameters", "Direction",
                self.control.get_widget(), weight=40)
        return True

    def teardown(self):
        self.core.unregister_ui("process_path_parameters", self.control.get_widget())
        self.core.get("unregister_parameter")("process", "grid_direction")


class PathParamPattern(pycam.Plugins.PluginBase):

    DEPENDS = ["Processes"]
    CATEGORIES = ["Process", "Parameter"]

    def setup(self):
        self.control = pycam.Gui.ControlsGTK.InputChoice(
                (("grid", pycam.Toolpath.MotionGrid.get_fixed_grid),
                    ("spiral", pycam.Toolpath.MotionGrid.get_spiral)),
                change_handler=lambda widget=None: self.core.emit_event(
                    "process-changed"))
        self.core.get("register_parameter")("process", "path_pattern",
                self.control)
        self.core.register_ui("process_path_parameters", "Pattern",
                self.control.get_widget(), weight=5)
        return True

    def teardown(self):
        self.core.unregister_ui("process_path_parameters", self.control.get_widget())
        self.core.get("unregister_parameter")("process", "path_pattern")


class PathParamRadiusCompensation(pycam.Plugins.PluginBase):

    DEPENDS = ["Processes"]
    CATEGORIES = ["Process", "Parameter"]

    def setup(self):
        self.control = pycam.Gui.ControlsGTK.InputCheckBox(
                change_handler=lambda widget=None: self.core.emit_event(
                    "process-changed"))
        self.core.get("register_parameter")("process", "radius_compensation",
                self.control)
        self.core.register_ui("process_path_parameters", "Radius compensation",
                self.control.get_widget(), weight=80)
        return True

    def teardown(self):
        self.core.unregister_ui("process_path_parameters", self.control.get_widget())
        self.core.get("unregister_parameter")("process", "radius_compensation")


class PathParamTraceModel(pycam.Plugins.PluginBase):

    DEPENDS = ["Processes", "Models"]
    CATEGORIES = ["Process", "Parameter"]

    def setup(self):
        self.control = pycam.Gui.ControlsGTK.InputTable([],
                change_handler=lambda widget=None: \
                    self.core.emit_event("process-changed"))
        # configure the input/output converter
        def get_converter(model_refs):
            models_dict = {}
            for model in self.core.get("models"):
                models_dict[id(model)] = model
            models = []
            for model_ref in model_refs:
                if model_ref in models_dict:
                    models.append(models_dict[model_ref])
            return models
        def set_converter(models):
            return [id(model) for model in models]
        self.control.set_conversion(set_conv=set_converter,
                get_conv=get_converter)
        self.core.get("register_parameter")("process", "trace_models",
                self.control)
        self.core.register_ui("process_path_parameters", "Trace models (2D)",
                self.control.get_widget(), weight=5)
        self.core.register_event("model-list-changed", self._update_models)
        return True

    def teardown(self):
        self.core.get("unregister_parameter")("process", "trace_models")
        self.core.unregister_ui("process_path_parameters", self.control.get_widget())
        self.core.unregister_event("model-list-changed", self._update_models)

    def _update_models(self):
        choices = []
        models = self.core.get("models")
        for model in models:
            if hasattr(model, "get_polygons"):
                choices.append((models.get_attr(model, "name"), model))
        self.control.update_choices(choices)

