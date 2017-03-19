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

from pycam.Geometry import Box3D, Point3D
import pycam.Plugins
# TODO: move Toolpath.Bounds here?
import pycam.Toolpath
from pycam.Utils import get_non_conflicting_name


_RELATIVE_UNIT = ("%", "mm")
_BOUNDARY_MODES = ("inside", "along", "around")


class Bounds(pycam.Plugins.ListPluginBase):

    UI_FILE = "bounds.ui"
    DEPENDS = ["Models"]
    CATEGORIES = ["Bounds"]

    # mapping of boundary types and GUI control elements
    CONTROL_BUTTONS = ("TypeRelativeMargin", "TypeCustom",
                       "ToolLimit", "RelativeUnit", "BoundaryLowX",
                       "BoundaryLowY", "BoundaryLowZ", "BoundaryHighX",
                       "BoundaryHighY", "BoundaryHighZ")
    CONTROL_SIGNALS = ("toggled", "value-changed", "changed")
    CONTROL_GET = ("get_active", "get_value")
    CONTROL_SET = ("set_active", "set_value")

    def setup(self):
        self._event_handlers = []
        self.core.set("bounds", self)
        if self.gui:
            bounds_box = self.gui.get_object("BoundsBox")
            bounds_box.unparent()
            self.core.register_ui("main", "Bounds", bounds_box, 30)
            self._boundsview = self.gui.get_object("BoundsTable")
            self.set_gtk_modelview(self._boundsview)
            self.register_model_update(lambda: self.core.emit_event("bounds-list-changed"))
            for action, obj_name in ((self.ACTION_UP, "BoundsMoveUp"),
                                     (self.ACTION_DOWN, "BoundsMoveDown"),
                                     (self.ACTION_DELETE, "BoundsDelete")):
                self.register_list_action_button(action, self.gui.get_object(obj_name))
            self._treemodel = self._boundsview.get_model()
            self._treemodel.clear()
            self._gtk_handlers = []
            self._gtk_handlers.append((self._boundsview.get_selection(), "changed",
                                       "bounds-selection-changed"))
            self._gtk_handlers.append((self.gui.get_object("BoundsNew"), "clicked",
                                       self._bounds_new))
            # model selector
            self.models_control = pycam.Gui.ControlsGTK.InputTable(
                [], change_handler=lambda *args: self.core.emit_event("bounds-changed"))
            self.gui.get_object("ModelsViewPort").add(self.models_control.get_widget())
            # quickly adjust the bounds via buttons
            for obj_name in ("MarginIncreaseX", "MarginIncreaseY", "MarginIncreaseZ",
                             "MarginDecreaseX", "MarginDecreaseY", "MarginDecreaseZ",
                             "MarginResetX", "MarginResetY", "MarginResetZ"):
                axis = obj_name[-1]
                if "Increase" in obj_name:
                    args = "+"
                elif "Decrease" in obj_name:
                    args = "-"
                else:
                    args = "0"
                self._gtk_handlers.append((self.gui.get_object(obj_name), "clicked",
                                           self._adjust_bounds, axis, args))
            # connect change handler for boundary settings
            for axis in "XYZ":
                for value in ("Low", "High"):
                    obj_name = "Boundary%s%s" % (value, axis)
                    self._gtk_handlers.append((self.gui.get_object(obj_name), "value-changed",
                                               "bounds-changed"))
            # register all controls
            for obj_name in self.CONTROL_BUTTONS:
                obj = self.gui.get_object(obj_name)
                if obj_name == "TypeRelativeMargin":
                    self._gtk_handlers.append((obj, "toggled", self._switch_relative_custom))
                elif obj_name == "RelativeUnit":
                    self._gtk_handlers.append((obj, "changed", self._switch_percent_absolute))
                else:
                    for signal in self.CONTROL_SIGNALS:
                        try:
                            handler = obj.connect(signal, lambda *args: None)
                            obj.disconnect(handler)
                            self._gtk_handlers.append((obj, signal, "bounds-changed"))
                            break
                        except TypeError:
                            continue
                    else:
                        self.log.info("Failed to connect to widget '%s'", str(obj_name))
                        continue
            self._gtk_handlers.append((self.gui.get_object("NameCell"), "edited",
                                       self._edit_bounds_name))
            self._event_handlers.extend((
                ("bounds-selection-changed", self._update_controls),
                ("bounds-changed", self._store_bounds_settings),
                ("bounds-changed", self._trigger_table_update),
                ("model-list-changed", self._update_model_list)))
            self.register_gtk_handlers(self._gtk_handlers)
            self._trigger_table_update()
            self._update_model_list()
            self._update_controls()
        self._event_handlers.append(("bounds-changed", "visual-item-updated"))
        self.register_event_handlers(self._event_handlers)
        self.register_state_item("bounds-list", self)
        self.core.register_namespace("bounds", pycam.Plugins.get_filter(self))
        return True

    def teardown(self):
        self.clear_state_items()
        self.core.unregister_namespace("bounds")
        if self.gui:
            self.core.unregister_ui("main", self.gui.get_object("BoundsBox"))
            self.unregister_gtk_handlers(self._gtk_handlers)
        self.unregister_event_handlers(self._event_handlers)
        self.core.set("bounds", None)
        while len(self) > 0:
            self.pop()

    def get_selected_models(self, index=False):
        return self.models_control.get_value()

    def select_models(self, models):
        self.models_control.set_value(models)

    def _get_current_bounds_box(self):
        bounds = self.get_selected()
        models = [m.model for m in bounds["parameters"]["Models"]]
        if not models:
            models = [m.model for m in self.core.get("models").get_visible()]
        return pycam.Geometry.Model.get_combined_bounds(models)

    def _render_bounds_size(self, column, cell, model, m_iter):
        bounds = self.get_by_path(model.get_path(m_iter))
        if not bounds:
            return
        box = bounds.get_absolute_limits()
        if box is None:
            text = ""
        else:
            text = "%g x %g x %g" % tuple([box.upper[i] - box.lower[i] for i in range(3)])
        cell.set_property("text", text)

    def _render_bounds_name(self, column, cell, model, m_iter):
        bounds = self.get_by_path(model.get_path(m_iter))
        cell.set_property("text", bounds["name"])

    def _trigger_table_update(self):
        self.gui.get_object("SizeColumn").set_cell_data_func(self.gui.get_object("SizeCell"),
                                                             self._render_bounds_size)
        self.gui.get_object("NameColumn").set_cell_data_func(self.gui.get_object("NameCell"),
                                                             self._render_bounds_name)

    def _update_model_list(self):
        models = self.core.get("models")
        choices = []
        for model in models:
            choices.append((model["name"], model))
        self.models_control.update_choices(choices)
        self._update_controls()

    def _store_bounds_settings(self, widget=None):
        data = self.get_selected()
        control_box = self.gui.get_object("BoundsSettingsControlsBox")
        if data is not None:
            for obj_name in self.CONTROL_BUTTONS:
                obj = self.gui.get_object(obj_name)
                for get_func in self.CONTROL_GET:
                    if hasattr(obj, get_func):
                        value = getattr(obj, get_func)()
                        data["parameters"][obj_name] = value
                        break
                else:
                    self.log.info("Failed to update value of control %s", obj_name)
            data["parameters"]["Models"] = self.get_selected_models()
            control_box.show()
        self._update_controls()

    def _switch_relative_custom(self, widget=None):
        bounds = self.get_selected()
        if not bounds:
            return
        if self.gui.get_object("TypeRelativeMargin").get_active():
            # no models are currently selected
            func_low = lambda value, axis: 0
            func_high = func_low
        else:
            # relative margins -> absolute coordinates
            # calculate the model bounds
            box = self._get_current_bounds_box()
            if box is None:
                # zero-sized models -> no action
                return
            dim = box.get_diagonal()
            if self._is_percent():
                func_low = lambda value, axis: box.lower[axis] - (value / 100.0 * dim[axis])
                func_high = lambda value, axis: box.upper[axis] + (value / 100.0 * dim[axis])
            else:
                func_low = lambda value, axis: box.lower[axis] - value
                func_high = lambda value, axis: box.upper[axis] + value
            # absolute mode -> no models may be selected
            self.select_models([])
        for axis in "XYZ":
            for func, name in ((func_low, "BoundaryLow"), (func_high, "BoundaryHigh")):
                try:
                    result = func(bounds["parameters"][name + axis], "XYZ".index(axis))
                except ZeroDivisionError:
                    # this happens for flat models
                    result = 0
                self.gui.get_object(name + axis).set_value(result)
        self._update_controls()

    def _switch_percent_absolute(self, widget=None):
        """ re-calculate the values of the controls for the lower and upper
        margin of each axis. This is only necessary, if there are referenced
        models.
        Switching between percent and absolute values changes only numbers,
        but not the extend of margins.
        """
        bounds = self.get_selected()
        if not bounds:
            return
        # calculate the model bounds
        box = self._get_current_bounds_box()
        if box is None:
            # zero-sized models -> no action
            return
        dim = box.get_diagonal()
        if self._is_percent():
            # switched from absolute to percent
            func = lambda value, axis_index: value / dim[axis_index] * 100.0
        else:
            func = lambda value, axis_index: (value / 100.0) * dim[axis_index]
        for axis in "XYZ":
            axis_index = "XYZ".index(axis)
            for name in ("BoundaryLow", "BoundaryHigh"):
                try:
                    result = func(bounds["parameters"][name + axis], axis_index)
                except ZeroDivisionError:
                    # this happens for flat models
                    result = 0
                self.gui.get_object(name + axis).set_value(result)
        # Make sure that the new state of %/mm is always stored - even if no
        # control value has really changed (e.g. if all margins were zero).
        self._store_bounds_settings()
        self._update_controls()

    def _adjust_bounds(self, widget, axis, change):
        bounds = self.get_selected()
        if not bounds:
            return
        axis_index = "XYZ".index(axis)
        key_low = "BoundaryLow%s" % axis
        key_high = "BoundaryHigh%s" % axis
        change_factor = {"0": 0, "+": 1, "-": -1}[change]
        if change == "0":
            bounds["parameters"][key_low] = 0
            bounds["parameters"][key_high] = 0
        elif self._is_percent():
            # % margin
            percent_change_per_side = 10
            # reduce the change value, if the boundary would turn negative afterwards
            dim_percent = 100 + bounds["parameters"][key_low] + bounds["parameters"][key_high]
            if (change_factor < 0) and (dim_percent < 2 * percent_change_per_side):
                percent_change_per_side = dim_percent / 2
            bounds["parameters"][key_low] += change_factor * percent_change_per_side
            bounds["parameters"][key_high] += change_factor * percent_change_per_side
        else:
            # absolute margin
            model_box = self._get_current_bounds_box()
            if model_box is None:
                return
            change_value = model_box.get_dimensions()[axis_index] * 0.1
            dim = (model_box.get_dimensions()[axis_index]
                   + bounds["parameters"][key_low] + bounds["parameters"][key_high])
            if (change_factor < 0) and (dim < 2 * change_value):
                change_value = dim / 2
            bounds["parameters"][key_low] += change_value * change_factor
            bounds["parameters"][key_high] += change_value * change_factor
        self._update_controls()

    def _is_percent(self):
        return _RELATIVE_UNIT[self.gui.get_object("RelativeUnit").get_active()] == "%"

    def _validate_bounds(self):
        """ check if any dimensions is below zero and fix these problems """
        bounds = self.get_selected()
        if not bounds:
            return
        margins = bounds["parameters"]
        for axis_index, axis in enumerate("XYZ"):
            key_low = "BoundaryLow%s" % axis
            key_high = "BoundaryHigh%s" % axis
            if self._is_percent():
                # % margin
                dim_percent = margins[key_low] + margins[key_high]
                if dim_percent < -100:
                    # this dimension went below zero -> reduce the relative margins
                    margins[key_low] /= dim_percent / -100
                    margins[key_high] = 100 - margins[key_low]
            else:
                # absolute margin
                model_box = self._get_current_bounds_box()
                if model_box is None:
                    return
                dim = margins[key_low] + margins[key_high]
                if dim < -model_box.get_dimensions()[axis_index]:
                    if model_box.get_dimensions()[axis_index] > 0:
                        margins[key_low] /= dim / -model_box.get_dimensions()[axis_index]
                    else:
                        margins[key_low] += -dim / 2
                    margins[key_high] = -model_box.get_dimensions()[axis_index] - margins[key_low]

    def _update_controls(self, widget=None):
        bounds = self.get_selected()
        control_box = self.gui.get_object("BoundsSettingsControlsBox")
        if not bounds:
            control_box.hide()
        else:
            self._validate_bounds()
            self.unregister_gtk_handlers(self._gtk_handlers)
            for obj_name, value in bounds["parameters"].iteritems():
                if obj_name == "Models":
                    self.select_models(value)
                    continue
                obj = self.gui.get_object(obj_name)
                for set_func in self.CONTROL_SET:
                    if hasattr(obj, set_func):
                        if (value is False) and hasattr(obj, "get_group"):
                            # no "False" for radio buttons
                            pass
                        else:
                            getattr(obj, set_func)(value)
                        break
                else:
                    self.log.info("Failed to set value of control: %s", obj_name)
            self.register_gtk_handlers(self._gtk_handlers)
            control_box.show()
            # enable/disable margin controls for percent-style changes and zero-dimensions
            box = self._get_current_bounds_box()
            if box:
                dim = box.get_diagonal()
            for axis in "XYZ":
                axis_index = "XYZ".index(axis)
                for name in ("BoundaryLow", "BoundaryHigh"):
                    # disallow editing the controls if percent fails to work with zero dimension
                    percent_for_zero_dim = (self._is_percent()
                                            and (box is None or (dim[axis_index] == 0)))
                    self.gui.get_object(name + axis).set_sensitive(not percent_for_zero_dim)
        # show the proper descriptive label for the current margin type
        relative_label = self.gui.get_object("MarginTypeRelativeLabel")
        custom_label = self.gui.get_object("MarginTypeCustomLabel")
        model_list = self.gui.get_object("ModelsTableFrame")
        percent_switch = self.gui.get_object("RelativeUnit")
        controls_x = self.gui.get_object("MarginControlsX")
        controls_y = self.gui.get_object("MarginControlsY")
        controls_z = self.gui.get_object("MarginControlsZ")
        if self.gui.get_object("TypeRelativeMargin").get_active():
            relative_label.show()
            custom_label.hide()
            model_list.show()
            percent_switch.show()
            controls_x.show()
            controls_y.show()
            controls_z.show()
        else:
            relative_label.hide()
            custom_label.show()
            model_list.hide()
            percent_switch.hide()
            controls_x.hide()
            controls_y.hide()
            controls_z.hide()
        self.core.emit_event("bounds-changed")

    def _bounds_new(self, *args):
        name = get_non_conflicting_name("Bounds #%d", [bounds["name"] for bounds in self])
        new_bounds = BoundsEntity(self.core, name)
        self.append(new_bounds)
        self.select(new_bounds)

    def _edit_bounds_name(self, cell, path, new_text):
        bounds = self.get_by_path(path)
        if bounds and (new_text != bounds["name"]) and new_text:
            bounds["name"] = new_text
            self.core.emit_event("bounds-list-changed")


class BoundsEntity(pycam.Plugins.ObjectWithAttributes):

    def __init__(self, core, name, *args, **kwargs):
        super(BoundsEntity, self).__init__("bounds", *args, **kwargs)
        self["name"] = name
        self["parameters"] = {}
        self.core = core
        self["parameters"].update({
            "BoundaryLowX": 0,
            "BoundaryLowY": 0,
            "BoundaryLowZ": 0,
            "BoundaryHighX": 0,
            "BoundaryHighY": 0,
            "BoundaryHighZ": 0,
            "TypeRelativeMargin": True,
            "TypeCustom": False,
            "RelativeUnit": _RELATIVE_UNIT.index("%"),
            "ToolLimit": _BOUNDARY_MODES.index("along"),
            "Models": [],
        })

    def get_absolute_limits(self, tool_radius=None, models=None):
        get_low_value = lambda axis: self["parameters"]["BoundaryLow%s" % "XYZ"[axis]]
        get_high_value = lambda axis: self["parameters"]["BoundaryHigh%s" % "XYZ"[axis]]
        if self["parameters"]["TypeRelativeMargin"]:
            # choose the appropriate set of models
            if self["parameters"]["Models"]:
                # configured models always take precedence
                models = self["parameters"]["Models"]
            elif models:
                # use the supplied models (e.g. for toolpath calculation)
                pass
            else:
                # use all visible models -> for live visualization
                models = self.core.get("models").get_visible()
            model_box = pycam.Geometry.Model.get_combined_bounds([model.model for model in models])
            if model_box is None:
                # zero-sized models -> no action
                return None
            is_percent = _RELATIVE_UNIT[self["parameters"]["RelativeUnit"]] == "%"
            low, high = [], []
            if is_percent:
                for axis in range(3):
                    dim = model_box.upper[axis] - model_box.lower[axis]
                    low.append(model_box.lower[axis] - (get_low_value(axis) / 100.0 * dim))
                    high.append(model_box.upper[axis] + (get_high_value(axis) / 100.0 * dim))
            else:
                for axis in range(3):
                    low.append(model_box.lower[axis] - get_low_value(axis))
                    high.append(model_box.upper[axis] + get_high_value(axis))
        else:
            low, high = [], []
            for axis in range(3):
                low.append(get_low_value(axis))
                high.append(get_high_value(axis))
        tool_limit = _BOUNDARY_MODES[self["parameters"]["ToolLimit"]]
        # apply inside/along/outside if a tool is given
        if tool_radius and (tool_limit != "along"):
            if tool_limit == "inside":
                offset = -tool_radius
            else:
                offset = tool_radius
            # apply offset only for x and y
            for index in range(2):
                low[index] -= offset
                high[index] += offset
        return Box3D(Point3D(*low), Point3D(*high))
