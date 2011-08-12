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

class Toolpaths(pycam.Plugins.ListPluginBase):

    UI_FILE = "toolpaths.ui"
    CATEGORIES = ["Toolpath"]
    COLUMN_REF, COLUMN_NAME, COLUMN_VISIBLE = range(3)
    LIST_ATTRIBUTE_MAP = {"name": COLUMN_NAME, "visible": COLUMN_VISIBLE}
    ICONS = {"visible": "visible.svg", "hidden": "visible_off.svg"}

    def setup(self):
        self.last_toolpath_file = None
        if self.gui:
            import gtk
            self.tp_box = self.gui.get_object("ToolpathsBox")
            self.tp_box.unparent()
            self.core.register_ui("main", "Toolpaths", self.tp_box, weight=50)
            self._gtk_handlers = []
            self._modelview = self.gui.get_object("ToolpathTable")
            self._treemodel = self.gui.get_object("ToolpathListModel")
            self._treemodel.clear()
            for action, obj_name in ((self.ACTION_UP, "ToolpathMoveUp"),
                    (self.ACTION_DOWN, "ToolpathMoveDown"),
                    (self.ACTION_DELETE, "ToolpathDelete"),
                    (self.ACTION_CLEAR, "ToolpathDeleteAll")):
                self.register_list_action_button(action, self._modelview,
                        self.gui.get_object(obj_name))
            # toolpath operations
            toolpath_handling_obj = self.gui.get_object(
                    "ToolpathHandlingNotebook")
            def clear_toolpath_handling_obj():
                for index in range(toolpath_handling_obj.get_n_pages()):
                    toolpath_handling_obj.remove_page(0)
            def add_toolpath_handling_item(item, name):
                toolpath_handling_obj.append_page(item, gtk.Label(name))
            self.core.register_ui_section("toolpath_handling",
                    add_toolpath_handling_item, clear_toolpath_handling_obj)
            # handle table changes
            self._gtk_handlers.extend((
                    (self._modelview, "row-activated",
                        self._list_action_toggle_custom, self.COLUMN_VISIBLE),
                    (self._modelview, "row-activated", "toolpath-changed"),
                    (self.gui.get_object("ToolpathNameCell"), "edited",
                        self._edit_toolpath_name)))
            self.gui.get_object("ToolpathVisibleColumn").set_cell_data_func(
                    self.gui.get_object("ToolpathVisibleSymbol"),
                    self._visualize_visible_state)
            # handle selection changes
            selection = self._modelview.get_selection()
            self._gtk_handlers.append((selection, "changed",
                    "toolpath-selection-changed"))
            selection.set_mode(gtk.SELECTION_MULTIPLE)
            # model handling
            def update_model():
                if not hasattr(self, "_model_cache"):
                    self._model_cache = {}
                cache = self._model_cache
                for row in self._treemodel:
                    cache[row[self.COLUMN_REF]] = list(row)
                self._treemodel.clear()
                for index, item in enumerate(self):
                    if id(item) in cache:
                        self._treemodel.append(cache[id(item)])
                    else:
                        self._treemodel.append((id(item),
                                "Toolpath #%d" % index, True))
                self.core.emit_event("toolpath-list-changed")
            self.register_model_update(update_model)
            self._event_handlers = (
                    ("toolpath-changed", self._update_widgets),
                    ("toolpath-list-changed", self._update_widgets),
                    ("toolpath-changed", "visual-item-updated"),
                    ("toolpath-list-changed", "visual-item-updated"))
            self.register_gtk_handlers(self._gtk_handlers)
            self.register_event_handlers(self._event_handlers)
            self._trigger_toolpath_time_update()
            self._update_widgets()
        self.core.set("toolpaths", self)
        return True

    def teardown(self):
        if self.gui:
            self.core.unregister_ui("main", self.gui.get_object("ToolpathsBox"))
            self.unregister_gtk_handlers(self._gtk_handlers)
            self.unregister_event_handlers(self._event_handlers)
        self.core.set("toolpaths", None)

    def get_selected(self):
        return self._get_selected(self._modelview, force_list=True)

    def get_visible(self):
        return [self[index] for index, item in enumerate(self._treemodel)
                if item[self.COLUMN_VISIBLE]]

    def select(self, toolpaths):
        selection = self._modelview.get_selection()
        model = self._modelview.get_model()
        if not isinstance(toolpaths, (list, tuple)):
            toolpaths = [toolpaths]
        tp_refs = [id(tp) for tp in toolpaths]
        for index, row in enumerate(model):
            if row[self.COLUMN_REF] in tp_refs:
                selection.select_path((index,))
            else:
                selection.unselect_path((index,))

    def _update_widgets(self):
        toolpaths = self
        if not toolpaths:
            self.tp_box.hide()
        else:
            self.tp_box.show()
            self._trigger_toolpath_time_update()

    def _trigger_toolpath_time_update(self):
        self.gui.get_object("ToolpathTimeColumn").set_cell_data_func(
                self.gui.get_object("ToolpathTimeCell"),
                self._visualize_machine_time)

    def _list_action_toggle_custom(self, treeview, path, clicked_column,
            force_column=None):
        if force_column is None:
            column = self._modelview.get_columns().index(clicked_column)
        else:
            column = force_column
        self._list_action_toggle(clicked_column, str(path[0]), column)

    def _list_action_toggle(self, widget, path, column):
        path = int(path)
        model = self._treemodel
        model[path][column] = not model[path][column]
        self.core.emit_event("visual-item-updated")

    def _edit_toolpath_name(self, cell, path, new_text):
        path = int(path)
        if (new_text != self._treemodel[path][self.COLUMN_NAME]) and \
                new_text:
            self._treemodel[path][self.COLUMN_NAME] = new_text

    def _visualize_visible_state(self, column, cell, model, m_iter):
        visible = model.get_value(m_iter, self.COLUMN_VISIBLE)
        if visible:
            cell.set_property("pixbuf", self.ICONS["visible"])
        else:
            cell.set_property("pixbuf", self.ICONS["hidden"])

    def _visualize_machine_time(self, column, cell, model, m_iter):
        path = model.get_path(m_iter)
        toolpath = self[path[0]]
        def get_time_string(minutes):
            if minutes > 180:
                return "%d hours" % int(round(minutes / 60))
            elif minutes > 3:
                return "%d minutes" % int(round(minutes))
            else:
                return "%d seconds" % int(round(minutes * 60))
        text = get_time_string(toolpath.get_machine_time(
                self.core.get("gcode_safety_height")))
        cell.set_property("text", text)

