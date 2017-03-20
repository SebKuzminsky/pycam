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


import pycam.Plugins
import pycam.Toolpath
from pycam.Utils import get_non_conflicting_name


class Toolpaths(pycam.Plugins.ListPluginBase):

    UI_FILE = "toolpaths.ui"
    CATEGORIES = ["Toolpath"]
    ICONS = {"visible": "visible.svg", "hidden": "visible_off.svg"}

    def setup(self):
        self.last_toolpath_file = None
        if self.gui and self._gtk:
            self.tp_box = self.gui.get_object("ToolpathsBox")
            self.tp_box.unparent()
            self.core.register_ui("main", "Toolpaths", self.tp_box, weight=50)
            self._gtk_handlers = []
            self._modelview = self.gui.get_object("ToolpathTable")
            self.set_gtk_modelview(self._modelview)
            self.register_model_update(lambda: self.core.emit_event("toolpath-list-changed"))
            self._treemodel = self.gui.get_object("ToolpathListModel")
            self._treemodel.clear()
            for action, obj_name in ((self.ACTION_UP, "ToolpathMoveUp"),
                                     (self.ACTION_DOWN, "ToolpathMoveDown"),
                                     (self.ACTION_DELETE, "ToolpathDelete"),
                                     (self.ACTION_CLEAR, "ToolpathDeleteAll")):
                self.register_list_action_button(action, self.gui.get_object(obj_name))
            # toolpath operations
            toolpath_handling_obj = self.gui.get_object("ToolpathHandlingNotebook")

            def clear_toolpath_handling_obj():
                for index in range(toolpath_handling_obj.get_n_pages()):
                    toolpath_handling_obj.remove_page(0)

            def add_toolpath_handling_item(item, name):
                toolpath_handling_obj.append_page(item, self._gtk.Label(name))

            self.core.register_ui_section("toolpath_handling", add_toolpath_handling_item,
                                          clear_toolpath_handling_obj)
            # handle table changes
            self._gtk_handlers.extend((
                (self._modelview, "row-activated", self._toggle_visibility),
                (self._modelview, "row-activated", "toolpath-changed"),
                (self.gui.get_object("ToolpathNameCell"), "edited", self._edit_toolpath_name)))
            # handle selection changes
            selection = self._modelview.get_selection()
            self._gtk_handlers.append((selection, "changed", "toolpath-selection-changed"))
            selection.set_mode(self._gtk.SELECTION_MULTIPLE)
            self._event_handlers = (
                ("toolpath-changed", self._update_widgets),
                ("toolpath-list-changed", self._update_widgets),
                ("toolpath-changed", "visual-item-updated"),
                ("toolpath-list-changed", "visual-item-updated"))
            self.register_gtk_handlers(self._gtk_handlers)
            self.register_event_handlers(self._event_handlers)
            self._trigger_table_update()
            self._update_widgets()
        self.core.set("toolpaths", self)
        self.core.register_namespace("toolpaths", pycam.Plugins.get_filter(self))
        return True

    def teardown(self):
        self.core.unregister_namespace("toolpaths")
        if self.gui and self._gtk:
            self.core.unregister_ui("main", self.gui.get_object("ToolpathsBox"))
            self.unregister_gtk_handlers(self._gtk_handlers)
            self.unregister_event_handlers(self._event_handlers)
        self.core.set("toolpaths", None)

    def get_visible(self):
        return [tp for tp in self if tp["visible"]]

    def _update_widgets(self):
        toolpaths = self
        if not toolpaths:
            self.tp_box.hide()
        else:
            self.tp_box.show()
            self._trigger_table_update()

    def _trigger_table_update(self):
        self.gui.get_object("ToolpathNameColumn").set_cell_data_func(
            self.gui.get_object("ToolpathNameCell"), self._visualize_toolpath_name)
        self.gui.get_object("ToolpathTimeColumn").set_cell_data_func(
            self.gui.get_object("ToolpathTimeCell"), self._visualize_machine_time)
        self.gui.get_object("ToolpathVisibleColumn").set_cell_data_func(
            self.gui.get_object("ToolpathVisibleSymbol"), self._visualize_visible_state)

    def _toggle_visibility(self, treeview, path, column):
        toolpath = self.get_by_path(path)
        if toolpath:
            toolpath["visible"] = not toolpath["visible"]
        self.core.emit_event("visual-item-updated")

    def _edit_toolpath_name(self, cell, path, new_text):
        toolpath = self.get_by_path(path)
        if toolpath and (new_text != toolpath["name"]) and new_text:
            toolpath["name"] = new_text

    def _visualize_toolpath_name(self, column, cell, model, m_iter):
        toolpath = self.get_by_path(model.get_path(m_iter))
        cell.set_property("text", toolpath["name"])

    def _visualize_visible_state(self, column, cell, model, m_iter):
        toolpath = self.get_by_path(model.get_path(m_iter))
        if toolpath["visible"]:
            cell.set_property("pixbuf", self.ICONS["visible"])
        else:
            cell.set_property("pixbuf", self.ICONS["hidden"])

    def _visualize_machine_time(self, column, cell, model, m_iter):
        def get_time_string(minutes):
            if minutes > 180:
                return "%d hours" % int(round(minutes / 60))
            elif minutes > 3:
                return "%d minutes" % int(round(minutes))
            else:
                return "%d seconds" % int(round(minutes * 60))

        toolpath = self.get_by_path(model.get_path(m_iter))
        text = get_time_string(toolpath.get_machine_time())
        cell.set_property("text", text)

    def add_new(self, new_tp, name=None):
        assert isinstance(new_tp, pycam.Toolpath.Toolpath), \
                "Invalid type: %s (%s)" % (type(new_tp), new_tp)
        moves = new_tp.path
        tool = new_tp.tool
        filters = new_tp.filters
        if name is None:
            name = get_non_conflicting_name("Toolpath #%d", [tp["name"] for tp in self])
        attributes = {"visible": True, "name": name}
        new_tp = ToolpathEntity(toolpath_path=moves, attributes=attributes,
                                toolpath_filters=filters, tool=tool)
        self.append(new_tp)


class ToolpathEntity(pycam.Toolpath.Toolpath, pycam.Plugins.ObjectWithAttributes):

    def __init__(self, **kwargs):
        super(ToolpathEntity, self).__init__(node_key="toolpath", **kwargs)
