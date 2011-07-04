# -*- coding: utf-8 -*-
"""
$Id: __init__.py 1061 2011-04-12 13:14:12Z sumpfralle $

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

# imported later (on demand)
#import gtk

import pycam.Plugins


class Models(pycam.Plugins.ListPluginBase):

    UI_FILE = "models.ui"
    COLUMN_ID, COLUMN_NAME, COLUMN_VISIBLE = range(3)
    ICONS = {"visible": "visible.svg", "hidden": "visible_off.svg"}

    def setup(self):
        if self.gui:
            import gtk
            self._gtk = gtk
            model_frame = self.gui.get_object("ModelBox")
            model_frame.unparent()
            self.core.register_ui("main", "Models", model_frame, -50)
            model_handling_obj = self.gui.get_object("ModelHandlingNotebook")
            def clear_model_handling_obj():
                for index in range(model_handling_obj.get_n_pages()):
                    model_handling_obj.remove_page(0)
            def add_model_handling_item(item, name):
                model_handling_obj.append_page(item, self._gtk.Label(name))
            self.core.register_ui_section("model_handling",
                    add_model_handling_item, clear_model_handling_obj)
            self._modelview = self.gui.get_object("ModelView")
            for action, obj_name in ((self.ACTION_UP, "ModelMoveUp"),
                    (self.ACTION_DOWN, "ModelMoveDown"),
                    (self.ACTION_DELETE, "ModelDelete"),
                    (self.ACTION_CLEAR, "ModelDeleteAll")):
                self.register_list_action_button(action, self._modelview,
                        self.gui.get_object(obj_name))
            self._modelview.connect("row-activated",
                    self._list_action_toggle_custom, self.COLUMN_VISIBLE)
            self.gui.get_object("ModelVisibleColumn").set_cell_data_func(
                    self.gui.get_object("ModelVisibleSymbol"),
                    self._visualize_visible_state)
            self.gui.get_object("ModelNameColumn").connect("edited",
                    self._edit_model_name)
            selection = self._modelview.get_selection()
            selection.connect("changed",
                    lambda widget, event: self.core.emit_event(event), 
                    "model-selection-changed")
            selection.set_mode(gtk.SELECTION_MULTIPLE)
            self._treemodel = self.gui.get_object("ModelList")
            self._treemodel.clear()
            def update_model():
                if not hasattr(self, "_model_cache"):
                    self._model_cache = {}
                cache = self._model_cache
                for row in self._treemodel:
                    cache[row[0]] = list(row)
                self._treemodel.clear()
                for index, item in enumerate(self):
                    if id(item) in cache:
                        self._treemodel.append(cache[id(item)])
                    else:
                        self._treemodel.append((id(item), "Model #%d" % index, True))
            self.register_model_update(update_model)
        self.core.add_item("models", lambda: self)
        return True

    def _edit_model_name(self, cell, path, new_text):
        path = int(path)
        if new_text != self._treemodel[path][self.COLUMN_NAME]:
            self._treemodel[path][self.COLUMN_NAME] = new_text

    def _visualize_visible_state(self, column, cell, model, m_iter):
        visible = model.get_value(m_iter, self.COLUMN_VISIBLE)
        if visible:
            cell.set_property("pixbuf", self.ICONS["visible"])
        else:
            cell.set_property("pixbuf", self.ICONS["hidden"])

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

    def get_selected(self):
        return self._get_selected(self._modelview, force_list=True)

    def get_visible(self):
        return [self[index] for index, item in enumerate(self._treemodel)
                if item[self.COLUMN_VISIBLE]]

    def teardown(self):
        if self.gui:
            self.core.unregister_ui("main", self.gui.get_object("ModelBox"))
            self.core.unregister_ui_section("main", "model_handling")
        self.core.set("models", None)
        return True

