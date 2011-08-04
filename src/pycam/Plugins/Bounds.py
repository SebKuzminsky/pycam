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
# TODO: move Toolpath.Bounds here?
import pycam.Toolpath


_RELATIVE_UNIT = ("%", "mm")
_BOUNDARY_MODES = ("inside", "along", "around")


class Bounds(pycam.Plugins.ListPluginBase):

    UI_FILE = "bounds.ui"
    DEPENDS = ["Models"]
    CATEGORIES = ["Bounds"]
    COLUMN_REF, COLUMN_NAME = range(2)
    LIST_ATTRIBUTE_MAP = {"ref": COLUMN_REF, "name": COLUMN_NAME}

    # mapping of boundary types and GUI control elements
    BOUNDARY_TYPES = {
            pycam.Toolpath.Bounds.TYPE_RELATIVE_MARGIN: "TypeRelativeMargin",
            pycam.Toolpath.Bounds.TYPE_CUSTOM: "TypeCustom"}
    CONTROL_BUTTONS = ("TypeRelativeMargin", "TypeCustom",
            "ToolLimit", "RelativeUnit", "BoundaryLowX",
            "BoundaryLowY", "BoundaryLowZ", "BoundaryHighX",
            "BoundaryHighY", "BoundaryHighZ")
    CONTROL_SIGNALS = ("toggled", "value-changed", "changed")
    CONTROL_GET = ("get_active", "get_value")
    CONTROL_SET = ("set_active", "set_value")

    def setup(self):
        if self.gui:
            import gtk
            bounds_box = self.gui.get_object("BoundsBox")
            bounds_box.unparent()
            self.core.register_ui("main", "Bounds", bounds_box, 30)
            self._boundsview = self.gui.get_object("BoundsEditTable")
            self._modelview = self.gui.get_object("BoundsModelsTable")
            model_selection = self._modelview.get_selection()
            model_selection.set_mode(gtk.SELECTION_MULTIPLE)
            self._detail_handlers = []
            handler = model_selection.connect("changed",
                    lambda widget: self.core.emit_event("bounds-changed"))
            self._detail_handlers.append((model_selection, handler))
            selection = self._boundsview.get_selection()
            selection.connect("changed",
                    lambda widget: self.core.emit_event("bounds-selection-changed"))
            self._treemodel = self._boundsview.get_model()
            self._treemodel.clear()
            def update_model():
                if not hasattr(self, "_model_cache"):
                    self._model_cache = {}
                cache = self._model_cache
                for row in self._treemodel:
                    cache[row[self.COLUMN_REF]] = list(row)
                self._treemodel.clear()
                for index, item in enumerate(self):
                    if not id(item) in cache:
                        cache[id(item)] = [id(item), "Bounds #%d" % index]
                    self._treemodel.append(cache[id(item)])
                self.core.emit_event("bounds-list-changed")
            self.register_model_update(update_model)
            for action, obj_name in ((self.ACTION_UP, "BoundsMoveUp"),
                    (self.ACTION_DOWN, "BoundsMoveDown"),
                    (self.ACTION_DELETE, "BoundsDelete")):
                self.register_list_action_button(action, self._boundsview,
                        self.gui.get_object(obj_name))
            self.gui.get_object("BoundsNew").connect("clicked",
                    self._bounds_new)
            # quickly adjust the bounds via buttons
            for obj_name in ("MarginIncreaseX", "MarginIncreaseY",
                    "MarginIncreaseZ", "MarginDecreaseX", "MarginDecreaseY",
                    "MarginDecreaseZ", "MarginResetX", "MarginResetY",
                    "MarginResetZ"):
                axis = obj_name[-1].lower()
                if "Increase" in obj_name:
                    args = "+"
                elif "Decrease" in obj_name:
                    args = "-"
                else:
                    args = "0"
                self.gui.get_object(obj_name).connect("clicked",
                        self._adjust_bounds, axis, args)
            # connect change handler for boundary settings
            for axis in "XYZ":
                for value in ("Low", "High"):
                    obj_name = "Boundary%s%s" % (value, axis)
                    obj = self.gui.get_object(obj_name)
                    handler = obj.connect("value-changed",
                            lambda widget: self.core.emit_event("bounds-changed"))
                    self._detail_handlers.append((obj, handler))
            # register all controls
            for obj_name in self.CONTROL_BUTTONS:
                obj = self.gui.get_object(obj_name)
                if obj_name == "TypeRelativeMargin":
                    handler = obj.connect("toggled",
                            self._switch_relative_custom)
                elif obj_name == "RelativeUnit":
                    handler = obj.connect("changed",
                            self._switch_percent_absolute)
                else:
                    for signal in self.CONTROL_SIGNALS:
                        try:
                            handler = obj.connect(signal, lambda *args: \
                                    self.core.emit_event(args[-1]),
                                    "bounds-changed")
                            break
                        except TypeError:
                            continue
                    else:
                        self.log.info("Failed to connect to widget '%s'" % str(obj_name))
                        continue
                self._detail_handlers.append((obj, handler))
            self.gui.get_object("NameCell").connect("edited",
                    self._edit_bounds_name)
            self.gui.get_object("ModelDescriptionColumn").set_cell_data_func(
                    self.gui.get_object("ModelNameCell"), self._render_model_name)
            self.core.register_event("bounds-selection-changed",
                    self._switch_bounds)
            self.core.register_event("bounds-changed",
                    self._store_bounds_settings)
            self.core.register_event("bounds-changed",
                    self._trigger_table_update)
            self.core.register_event("model-list-changed",
                    self._update_model_list)
            self._trigger_table_update()
            self._switch_bounds()
            self._update_model_list()
        self.core.set("bounds", self)
        self.core.register_event("bounds-changed",
                lambda: self.core.emit_event("visual-item-updated"))
        return True

    def teardown(self):
        if self.gui:
            self.core.unregister_ui("main", self.gui.get_object("BoundsBox"))
            self.core.unregister_event("bounds-selection-changed",
                    self._switch_bounds)
            self.core.unregister_event("bounds-changed",
                    self._store_bounds_settings)
            self.core.unregister_event("bounds-changed",
                    self._trigger_table_update)
            self.core.unregister_event("model-list-changed",
                    self._update_model_list)
        self.core.set("bounds", None)
        return True

    def get_selected(self, index=False):
        return self._get_selected(self._boundsview, index=index)

    def select(self, bounds):
        if bounds in self:
            selection = self._boundsview.get_selection()
            index = [id(b) for b in self].index(id(bounds))
            selection.unselect_all()
            selection.select_path((index,))

    def get_selected_models(self, index=False):
        return self._get_selected(self._modelview,
                content=self.core.get("models"), index=index,
                force_list=True)

    def select_models(self, models):
        selection = self._modelview.get_selection()
        remaining = models[:]
        for index, row in enumerate(self._modelview.get_model()):
            model_ids = [id(m) for m in remaining]
            path = (index, )
            if row[0] in model_ids:
                remaining.pop(model_ids.index(row[0]))
                if not selection.path_is_selected(path):
                    selection.select_path(path)
            else:
                if selection.path_is_selected(path):
                    selection.unselect_path(path)
        # remove all models that are not available anymore
        for not_found in remaining:
            models.remove(not_found)

    def _render_model_name(self, column, cell, model, m_iter):
        path = model.get_path(m_iter)
        all_models = self.core.get("models")
        model_id = model[path[0]][0]
        model_ids = [id(m) for m in all_models]
        if model_id in model_ids:
            this_model = all_models[model_ids.index(model_id)]
            cell.set_property("text", all_models.get_attr(this_model, "name"))

    def _render_bounds_size(self, column, cell, model, m_iter):
        path = model.get_path(m_iter)
        bounds = self[path[0]]
        low, high = bounds.get_absolute_limits()
        if None in low or None in high:
            text = ""
        else:
            text = "%g x %g x %g" % tuple([high[i] - low[i] for i in range(3)])
        cell.set_property("text", text)

    def _trigger_table_update(self):
        # trigger an update of the table - ugly!
        self.gui.get_object("SizeColumn").set_cell_data_func(
                self.gui.get_object("SizeCell"), self._render_bounds_size)

    def _update_model_list(self):
        model_ids = [id(m) for m in self.core.get("models")]
        model_list = self._modelview.get_model()
        for index, model_id in enumerate(model_ids):
            while (len(model_list) > index) and \
                    (model_list[index][0] != model_id):
                index_iter = model_list.get_iter((index, ))
                if model_list[index][0] in model_ids:
                    # move it to the end of the list
                    model_list.move_before(index_iter, None)
                else:
                    model_list.remove(index_iter)
            if len(model_list) <= index:
                model_list.append((model_id,))

    def _store_bounds_settings(self, widget=None):
        data = self.get_selected()
        control_box = self.gui.get_object("BoundsSettingsControlsBox")
        if data is None:
            control_box.hide()
            return
        else:
            for obj_name in self.CONTROL_BUTTONS:
                obj = self.gui.get_object(obj_name)
                for get_func in self.CONTROL_GET:
                    if hasattr(obj, get_func):
                        value = getattr(obj, get_func)()
                        data[obj_name] = value
                        break
                else:
                    self.log.info("Failed to update value of control %s" % obj_name)
            data["Models"] = self.get_selected_models()
            control_box.show()
        self._hide_and_show_controls()

    def _hide_and_show_controls(self):
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

    def _switch_relative_custom(self, widget=None):
        bounds = self.get_selected()
        if not bounds:
            return
        models = bounds["Models"]
        if self.gui.get_object("TypeRelativeMargin").get_active():
            # no models are currently selected
            func_low = lambda value, axis: 0
            func_high = func_low
        else:
            # relative margins -> absolute coordinates
            # calculate the model bounds
            low, high = pycam.Geometry.Model.get_combined_bounds(models)
            if None in low or None in high:
                # zero-sized models -> no action
                return
            dim = []
            for axis in range(3):
                dim.append(high[axis] - low[axis])
            if self._is_percent():
                func_low = lambda value, axis: low[axis] - (value / 100.0 * dim[axis])
                func_high = lambda value, axis: high[axis] + (value / 100.0 * dim[axis])
            else:
                func_low = lambda value, axis: low[axis] - value
                func_high = lambda value, axis: high[axis] + value
            # absolute mode -> no models may be selected
            self._modelview.get_selection().unselect_all()
        for axis in "XYZ":
            for func, name in ((func_low, "BoundaryLow"),
                    (func_high, "BoundaryHigh")):
                try:
                    result = func(bounds[name + axis], "XYZ".index(axis))
                except ZeroDivisionError:
                    # this happens for flat models
                    result = 0
                self.gui.get_object(name + axis).set_value(result)

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
        models = bounds["Models"]
        # calculate the model bounds
        low, high = pycam.Geometry.Model.get_combined_bounds(models)
        if None in low or None in high:
            # zero-sized models -> no action
            return
        dim = []
        for axis in range(3):
            dim.append(high[axis] - low[axis])
        if self._is_percent():
            # switched from absolute to percent
            func = lambda value, axis: value / dim[axis] * 100.0
        else:
            func = lambda value, axis: (value / 100.0) * dim[axis]
        for axis in "XYZ":
            for name in ("BoundaryLow", "BoundaryHigh"):
                try:
                    result = func(bounds[name + axis], "XYZ".index(axis))
                except ZeroDivisionError:
                    # this happens for flat models
                    result = 0
                self.gui.get_object(name + axis).set_value(result)
        # Make sure that the new state of %/mm is always stored - even if no
        # control value has really changed (e.g. if all margins were zero).
        self._store_bounds_settings()

    def _adjust_bounds(self, widget, axis, change):
        bounds = self.get_selected()
        if not bounds:
            return
        axis_index = "xyz".index(axis)
        change_factor = {"0": 0, "+": 1, "-": -1}[change]
        if change == "0":
            bounds["BoundaryLow%s" % axis.upper()] = 0
            bounds["BoundaryHigh%s" % axis.upper()] = 0
        elif self._is_percent():
            # % margin
            bounds["BoundaryLow%s" % axis.upper()] += change_factor * 10
            bounds["BoundaryHigh%s" % axis.upper()] += change_factor * 10
        else:
            # absolute margin
            models = self.get_selected_models()
            model_low, model_high = pycam.Geometry.Model.get_combined_bounds(models)
            if None in model_low or None in model_high:
                return
            change_value = (model_high[axis_index] - model_low[axis_index]) * 0.1
            bounds["BoundaryLow%s" % axis.upper()] += change_value * change_factor
            bounds["BoundaryHigh%s" % axis.upper()] += change_value * change_factor
        self._update_controls()
        self.core.emit_event("bounds-changed")

    def _is_percent(self):
        return _RELATIVE_UNIT[self.gui.get_object("RelativeUnit").get_active()] == "%"

    def _update_controls(self):
        bounds = self.get_selected()
        control_box = self.gui.get_object("BoundsSettingsControlsBox")
        if not bounds:
            control_box.hide()
        else:
            for obj, handler in self._detail_handlers:
                obj.handler_block(handler)
            for obj_name, value in bounds.iteritems():
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
                    self.log.info("Failed to set value of control %s" % obj_name)
            for obj, handler in self._detail_handlers:
                obj.handler_unblock(handler)
            self._hide_and_show_controls()
            control_box.show()

    def _switch_bounds(self, widget=None):
        self._update_controls()
        # update the sensitivity of the lower z margin for contour models
        self.core.emit_event("bounds-changed")

    def _bounds_new(self, *args):
        current_bounds_index = self.get_selected(index=True)
        if current_bounds_index is None:
            current_bounds_index = 0
        new_bounds = BoundsDict(self.core)
        self.append(new_bounds)
        self.select(new_bounds)

    def _edit_bounds_name(self, cell, path, new_text):
        path = int(path)
        if (new_text != self._treemodel[path][self.COLUMN_NAME]) and \
                new_text:
            self._treemodel[path][self.COLUMN_NAME] = new_text


class BoundsDict(dict):

    def __init__(self, core, *args, **kwargs):
        super(BoundsDict, self).__init__(*args, **kwargs)
        self.core = core
        self.update({
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

    def get_absolute_limits(self, tool=None, models=None):
        default = (None, None, None), (None, None, None)
        get_low_value = lambda axis: self["BoundaryLow%s" % "XYZ"[axis]]
        get_high_value = lambda axis: self["BoundaryHigh%s" % "XYZ"[axis]]
        if self["TypeRelativeMargin"]:
            # choose the appropriate set of models
            if self["Models"]:
                # configured models always take precedence
                models = self["Models"]
            elif models:
                # use the supplied models (e.g. for toolpath calculation)
                pass
            else:
                # use all visible models -> for live visualization
                models = self.core.get("models").get_visible()
            low_model, high_model = pycam.Geometry.Model.get_combined_bounds(
                    models)
            if None in low_model or None in high_model:
                # zero-sized models -> no action
                return default
            is_percent = _RELATIVE_UNIT[self["RelativeUnit"]] == "%"
            low, high = [], []
            if is_percent:
                for axis in range(3):
                    dim = high_model[axis] - low_model[axis]
                    low.append(low_model[axis] - (get_low_value(axis) / 100.0 * dim))
                    high.append(high_model[axis] + (get_high_value(axis) / 100.0 * dim))
            else:
                for axis in range(3):
                    low.append(low_model[axis] - get_low_value(axis))
                    high.append(high_model[axis] + get_high_value(axis))
        else:
            low, high = [], []
            for axis in range(3):
                low.append(get_low_value(axis))
                high.append(get_high_value(axis))
        tool_limit = _BOUNDARY_MODES[self["ToolLimit"]]
        # apply inside/along/outside
        if tool_limit != "along":
            tool_radius = tool["parameters"]["radius"]
            if tool_limit == "inside":
                offset = -tool_radius
            else:
                offset = tool_radius
            # apply offset only for x and y
            for index in range(2):
                low[index] -= offset
                high[index] += offset
        return low, high

