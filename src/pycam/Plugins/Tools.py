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

    UI_FILE = "tools.ui"
    COLUMN_REF, COLUMN_ID, COLUMN_NAME = range(3)
    LIST_ATTRIBUTE_MAP = {"id": COLUMN_ID, "name": COLUMN_NAME}
    SHAPE_MAP = {CylindricalCutter: ("CylindricalCutter", "Flat end"),
            SphericalCutter: ("SphericalCutter", "Ball nose"),
            ToroidalCutter: ("ToroidalCutter", "Bull nose")}

    def setup(self):
        if self.gui:
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
            selection = self._modelview.get_selection()
            selection.connect("changed", 
                    lambda widget, event: self.core.emit_event(event),
                    "tool-selection-changed")
            cell = self.gui.get_object("ToolTableShapeCell")
            self.gui.get_object("ToolTableShapeColumn").set_cell_data_func(
                    cell, self._visualize_tool_size)
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
                    cache[row[self.COLUMN_ID]] = list(row)
                self._treemodel.clear()
                for index, item in enumerate(self):
                    if not id(item) in cache:
                        cache[id(item)] = [id(item), index + 1,
                                "Tool #%d" % index]
                    self._treemodel.append(cache[id(item)])
                self.core.emit_event("tool-list-changed")
            self.register_model_update(update_model)
            # drill settings
            self._detail_handlers = []
            for objname in ("ToolDiameterControl", "TorusDiameterControl"):
                obj = self.gui.get_object(objname)
                handler = obj.connect("value-changed",
                        lambda *args: self.core.emit_event(args[-1]),
                        "tool-changed")
                self._detail_handlers.append((obj, handler))
            for objname in ("SphericalCutter", "CylindricalCutter",
                    "ToroidalCutter"):
                obj = self.gui.get_object(objname)
                handler = obj.connect("toggled",
                        lambda *args: self.core.emit_event(args[-1]),
                        "tool-changed")
                self._detail_handlers.append((obj, handler))
            self.core.register_event("tool-selection-changed",
                    self._tool_change)
            self.core.register_event("tool-changed",
                    self._update_tool_controls)
            self._update_tool_controls()
        self.core.set("tools", self)
        return True

    def teardown(self):
        if self.gui:
            self.core.unregister_ui("main", self.gui.get_object("ToolBox"))
            self.core.unregister_event("tool-selection-changed",
                    self._tool_change)
            self.core.unregister_event("tool-changed",
                    self._update_tool_controls)
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

    def _visualize_tool_size(self, column, cell, model, m_iter):
        path = model.get_path(m_iter)
        tool = self[path[0]]
        for cutter_class, (objname, desc) in self.SHAPE_MAP.iteritems():
            if isinstance(tool, cutter_class):
                break
        text = "%s (%g%s)" % (desc, 2 * tool.radius, self.core.get("unit"))
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
        if str(new_value) != self._treemodel[path][self.COLUMN_ID]:
            self._treemodel[path][self.COLUMN_ID] = new_value

    def _update_tool_controls(self):
        tool_index = self.get_selected(index=True)
        if tool_index is None:
            self.gui.get_object("ToolSettingsControlsBox").hide()
            return
        # disable the toroidal radius if the toroidal cutter is not enabled
        if self.gui.get_object("ToroidalCutter").get_active():
            self.gui.get_object("TorusDiameterControl").show()
            self.gui.get_object("TorusDiameterLabel").show()
        else:
            self.gui.get_object("TorusDiameterControl").hide()
            self.gui.get_object("TorusDiameterLabel").hide()
        for objname, default_value in (("ToolDiameterControl", 1.0),
                ("TorusDiameterControl", 0.25)):
            obj = self.gui.get_object(objname)
            if obj.get_value() == 0:
                # set the value to the configured minimum
                obj.set_value(default_value)
        # update the tool object
        for cutter_class, (objname, desc) in self.SHAPE_MAP.iteritems():
            if self.gui.get_object(objname).get_active():
                break
        radius = 0.5 * self.gui.get_object("ToolDiameterControl").get_value()
        if cutter_class is ToroidalCutter:
            args = [0.5 * self.gui.get_object("TorusDiameterControl").get_value()]
        else:
            args = []
        new_tool = cutter_class(radius, *args)
        old_tool = self.pop(tool_index)
        self.insert(tool_index, new_tool)
        if hasattr(self, "_model_cache"):
            # move the cache item
            cache = self._model_cache
            cache[id(new_tool)] = cache[id(old_tool)]
            del cache[id(old_tool)]
        self.select(new_tool)

    def _tool_change(self, widget=None, data=None):
        tool = self.get_selected()
        control_box = self.gui.get_object("ToolSettingsControlsBox")
        if not tool:
            control_box.hide()
        else:
            for obj, handler in self._detail_handlers:
                obj.handler_block(handler)
            # cutter shapes
            for cutter_class, (objname, desc) in self.SHAPE_MAP.iteritems():
                if isinstance(tool, cutter_class):
                    self.gui.get_object(objname).set_active(True)
            # radius -> diameter
            self.gui.get_object("ToolDiameterControl").set_value(2 * tool.radius)
            torus_control = self.gui.get_object("TorusDiameterControl")
            torus_label = self.gui.get_object("TorusDiameterLabel")
            if hasattr(tool, "minorradius"):
                torus_control.set_value(2 * tool.minorradius)
                torus_control.show()
                torus_label.show()
            else:
                torus_control.set_value(0.25)
                torus_control.hide()
                torus_label.hide()
            for obj, handler in self._detail_handlers:
                obj.handler_unblock(handler)
            control_box.show()
        
    def _tool_new(self, *args):
        current_tool_index = self.get_selected(index=True)
        if current_tool_index is None:
            current_tool_index = 0
        new_tool = CylindricalCutter(1.0)
        self.append(new_tool)
        self.select(new_tool)

