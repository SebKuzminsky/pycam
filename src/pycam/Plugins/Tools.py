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
from pycam.Cutters.CylindricalCutter import CylindricalCutter
from pycam.Cutters.SphericalCutter import SphericalCutter
from pycam.Cutters.ToroidalCutter import ToroidalCutter


class Tools(pycam.Plugins.ListPluginBase):

    DEPENDS = ["ParameterGroupManager"]
    UI_FILE = "tools.ui"
    COLUMN_REF, COLUMN_TOOL_ID, COLUMN_NAME = range(3)
    LIST_ATTRIBUTE_MAP = {"id": COLUMN_TOOL_ID, "name": COLUMN_NAME}

    def setup(self):
        if self.gui:
            import gtk
            tool_frame = self.gui.get_object("ToolBox")
            tool_frame.unparent()
            self.core.register_ui("main", "Tools", tool_frame, weight=10)
            self._modelview = self.gui.get_object("ToolEditorTable")
            for action, obj_name in ((self.ACTION_UP, "ToolMoveUp"),
                    (self.ACTION_DOWN, "ToolMoveDown"),
                    (self.ACTION_DELETE, "ToolDelete")):
                self.register_list_action_button(action, self._modelview,
                        self.gui.get_object(obj_name))
            self.gui.get_object("ToolNew").connect("clicked", self._tool_new)
            # parameters
            parameters_box = self.gui.get_object("ToolParameterBox")
            def clear_parameter_widgets():
                parameters_box.foreach(
                        lambda widget: parameters_box.remove(widget))
            def add_parameter_widget(item, name):
                # create a frame within an alignment and the item inside
                frame_label = gtk.Label()
                frame_label.set_markup("<b>%s</b>" % name)
                frame = gtk.Frame()
                frame.set_label_widget(frame_label)
                align = gtk.Alignment()
                frame.add(align)
                align.set_padding(0, 3, 12, 3)
                align.add(item)
                frame.show_all()
                parameters_box.pack_start(frame, expand=True)
            self.core.register_ui_section("tool_parameters",
                    add_parameter_widget, clear_parameter_widgets)
            self.core.get("register_parameter_group")("tool",
                    changed_set_event="tool-shape-changed",
                    changed_set_list_event="tool-shape-list-changed",
                    get_current_set_func=self._get_shape)
            size_parameter_widget = self.core.get("register_parameter_section")(
                    "tool", "size")
            self.core.register_ui("tool_parameters", "Size",
                    size_parameter_widget, weight=10)
            speed_parameter_widget = self.core.get("register_parameter_section")(
                    "tool", "speed")
            self.core.register_ui("tool_parameters", "Speed",
                    speed_parameter_widget, weight=20)
            # table updates
            cell = self.gui.get_object("ToolTableShapeCell")
            self.gui.get_object("ToolTableShapeColumn").set_cell_data_func(
                    cell, self._render_tool_shape)
            self.gui.get_object("ToolTableIDCell").connect("edited",
                    self._edit_tool_id)
            self.gui.get_object("ToolTableNameCell").connect("edited",
                    self._edit_tool_name)
            self._treemodel = self.gui.get_object("ToolList")
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
                        cache[id(item)] = [id(item), index + 1,
                                "Tool #%d" % index]
                    self._treemodel.append(cache[id(item)])
                self.core.emit_event("tool-list-changed")
            # selector
            selection = self._modelview.get_selection()
            selection.connect("changed", 
                    lambda widget, event: self.core.emit_event(event),
                    "tool-selection-changed")
            # shape selector
            shape_selector = self.gui.get_object("ToolShapeSelector")
            shape_selector.connect("changed", lambda widget: \
                    self.core.emit_event("tool-shape-changed"))
            self.core.register_event("tool-shape-list-changed",
                    self._update_widgets)
            self.core.register_event("tool-selection-changed",
                    self._tool_switch)
            self.core.register_event("tool-changed",
                    self._store_tool_settings)
            self.core.register_event("tool-shape-changed",
                    self._store_tool_settings)
            self.register_model_update(update_model)
            self._update_widgets()
            self._tool_switch()
        self.core.set("tools", self)
        return True

    def teardown(self):
        if self.gui:
            self.core.unregister_ui("main", self.gui.get_object("ToolBox"))
            self.core.unregister_event("tool-selection-changed",
                    self._tool_switch)
        self.core.set("tools", None)
        return True

    def get_selected(self, index=False):
        return self._get_selected(self._modelview, index=index)

    def select(self, tool):
        if tool in self:
            selection = self._modelview.get_selection()
            # check for identity instead of equality
            index = [id(t) for t in self].index(id(tool))
            selection.unselect_all()
            selection.select_path((index,))

    def _render_tool_shape(self, column, cell, model, m_iter):
        path = model.get_path(m_iter)
        tool = self[path[0]]
        parameters = tool["parameters"]
        if "radius" in parameters:
            text = "%g%s" % (2 * parameters["radius"], self.core.get("unit"))
        else:
            text = ""
        cell.set_property("text", text)

    def _edit_tool_name(self, cell, path, new_text):
        path = int(path)
        if (new_text != self._treemodel[path][self.COLUMN_NAME]) and \
                new_text:
            self._treemodel[path][self.COLUMN_NAME] = new_text

    def _edit_tool_id(self, cell, path, new_text):
        path = int(path)
        try:
            new_value = int(new_text)
        except ValueError:
            return
        if str(new_value) != self._treemodel[path][self.COLUMN_TOOL_ID]:
            self._treemodel[path][self.COLUMN_TOOL_ID] = new_value

    def _get_shape(self, name=None):
        shapes = self.core.get("get_parameter_sets")("tool")
        if name is None:
            # find the currently selected one
            selector = self.gui.get_object("ToolShapeSelector")
            model = selector.get_model()
            index = selector.get_active()
            if index < 0:
                return None
            shape_name = model[index][1]
        else:
            shape_name = name
        if shape_name in shapes:
            return shapes[shape_name]
        else:
            return None

    def select_shape(self, name):
        selector = self.gui.get_object("ToolShapeSelector")
        for index, row in enumerate(selector.get_model()):
            if row[1] == name:
                selector.set_active(index)
                break
        else:
            selector.set_active(-1)

    def _trigger_table_update(self):
        # trigger a table update - this is clumsy!
        cell = self.gui.get_object("ToolTableShapeColumn")
        renderer = self.gui.get_object("ToolTableShapeCell")
        cell.set_cell_data_func(renderer, self._render_tool_shape)

    def _update_widgets(self):
        selected = self._get_shape()
        model = self.gui.get_object("ToolShapeList")
        model.clear()
        shapes = self.core.get("get_parameter_sets")("tool").values()
        shapes.sort(key=lambda item: item["weight"])
        for shape in shapes:
            model.append((shape["label"], shape["name"]))
        # check if any on the processes became obsolete due to a missing plugin
        removal = []
        shape_names = [shape["name"] for shape in shapes]
        for index, tool in enumerate(self):
            if not tool["shape"] in shape_names:
                removal.append(index)
        removal.reverse()
        for index in removal:
            self.pop(index)
        # show "new" only if a strategy is available
        self.gui.get_object("ToolNew").set_sensitive(len(model) > 0)
        selector_box = self.gui.get_object("ToolSelectorBox")
        if len(model) < 2:
            selector_box.hide()
        else:
            selector_box.show()
        if selected:
            self.select_shape(selected["name"])

    def _store_tool_settings(self):
        tool = self.get_selected()
        control_box = self.gui.get_object("ToolSettingsControlsBox")
        shape = self._get_shape()
        if tool is None or shape is None:
            control_box.hide()
        else:
            tool["shape"] = shape["name"]
            parameters = tool["parameters"]
            parameters.update(self.core.get("get_parameter_values")("tool"))
            control_box.show()
            self._trigger_table_update()

    def _tool_switch(self, widget=None, data=None):
        tool = self.get_selected()
        control_box = self.gui.get_object("ToolSettingsControlsBox")
        if not tool:
            control_box.hide()
        else:
            self.core.block_event("tool-changed")
            self.core.block_event("tool-shape-changed")
            shape_name = tool["shape"]
            self.select_shape(shape_name)
            shape = self._get_shape(shape_name)
            self.core.get("set_parameter_values")("tool", tool["parameters"])
            control_box.show()
            self.core.unblock_event("tool-shape-changed")
            self.core.unblock_event("tool-changed")
            # trigger a widget update
            self.core.emit_event("tool-shape-changed")
        
    def _tool_new(self, *args):
        shapes = self.core.get("get_parameter_sets")("tool").values()
        shapes.sort(key=lambda item: item["weight"])
        shape = shapes[0]
        new_tool = {"shape": shape["name"],
                "parameters": shape["parameters"].copy(),
        }
        self.append(new_tool)
        self.select(new_tool)

