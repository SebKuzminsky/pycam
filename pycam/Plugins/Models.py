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
from pycam.Utils import get_non_conflicting_name


_GTK_COLOR_MAX = 65535.0


class Models(pycam.Plugins.ListPluginBase):

    UI_FILE = "models.ui"
    CATEGORIES = ["Model"]
    ICONS = {"visible": "visible.svg", "hidden": "visible_off.svg"}
    FALLBACK_COLOR = {"red": 0.5, "green": 0.5, "blue": 1.0, "alpha": 1.0}

    def setup(self):
        if self.gui and self._gtk:
            self.model_frame = self.gui.get_object("ModelBox")
            self.model_frame.unparent()
            self.core.register_ui("main", "Models", self.model_frame, weight=-50)
            model_handling_obj = self.gui.get_object("ModelHandlingNotebook")

            def clear_model_handling_obj():
                for index in range(model_handling_obj.get_n_pages()):
                    model_handling_obj.remove_page(0)

            def add_model_handling_item(item, name):
                model_handling_obj.append_page(item, self._gtk.Label(name))

            self.core.register_ui_section("model_handling", add_model_handling_item,
                                          clear_model_handling_obj)
            self._modelview = self.gui.get_object("ModelView")
            self.set_gtk_modelview(self._modelview)
            self.register_model_update(lambda: self.core.emit_event("model-list-changed"))
            for action, obj_name in ((self.ACTION_UP, "ModelMoveUp"),
                                     (self.ACTION_DOWN, "ModelMoveDown"),
                                     (self.ACTION_DELETE, "ModelDelete"),
                                     (self.ACTION_CLEAR, "ModelDeleteAll")):
                self.register_list_action_button(action, self.gui.get_object(obj_name))
            self._gtk_handlers = []
            self._gtk_handlers.extend((
                (self.gui.get_object("ModelColorButton"), "color-set",
                 self._set_colors_of_selected_models),
                (self._modelview, "row-activated", self._toggle_visibility),
                (self.gui.get_object("NameCell"), "edited", self._edit_model_name)))
            self._treemodel = self.gui.get_object("ModelList")
            self._treemodel.clear()
            selection = self._modelview.get_selection()
            selection.set_mode(self._gtk.SELECTION_MULTIPLE)
            self._gtk_handlers.append((selection, "changed", "model-selection-changed"))
            self._event_handlers = (
                ("model-selection-changed", self._get_colors_of_selected_models),
                ("model-list-changed", self._trigger_table_update))
            self.register_gtk_handlers(self._gtk_handlers)
            self.register_event_handlers(self._event_handlers)
            self._get_colors_of_selected_models()
            # update the model list
            self.core.emit_event("model-list-changed")
        self.core.register_namespace("models", pycam.Plugins.get_filter(self))
        self.core.set("models", self)
        self.register_state_item("models", self)
        return True

    def teardown(self):
        self.clear_state_items()
        self.core.unregister_namespace("models")
        if self.gui and self._gtk:
            self.core.unregister_ui_section("model_handling")
            self.core.unregister_ui("main", self.gui.get_object("ModelBox"))
            self.core.unregister_ui("main", self.model_frame)
            self.unregister_gtk_handlers(self._gtk_handlers)
            self.unregister_event_handlers(self._event_handlers)
        self.core.set("models", None)
        while len(self) > 0:
            self.pop()
        return True

    def _get_colors_of_selected_models(self, widget=None):
        color_button = self.gui.get_object("ModelColorButton")
        models = self.get_selected()
        color_button.set_sensitive(bool(models))
        if models:
            # use the color of the first model
            col = models[0]["color"]
            color_button.set_color(self._gtk.gdk.Color(
                red=int(col["red"] * _GTK_COLOR_MAX),
                green=int(col["green"] * _GTK_COLOR_MAX),
                blue=int(col["blue"] * _GTK_COLOR_MAX)))
            color_button.set_alpha(int(col["alpha"] * _GTK_COLOR_MAX))

    def _set_colors_of_selected_models(self, widget=None):
        color_button = self.gui.get_object("ModelColorButton")
        color = color_button.get_color()
        models = self.get_selected()
        for model in models:
            model["color"] = {"red": color.red / _GTK_COLOR_MAX,
                              "green": color.green / _GTK_COLOR_MAX,
                              "blue": color.blue / _GTK_COLOR_MAX,
                              "alpha": color_button.get_alpha() / _GTK_COLOR_MAX}
        self.core.emit_event("visual-item-updated")

    def _trigger_table_update(self):
        self.gui.get_object("NameColumn").set_cell_data_func(
            self.gui.get_object("NameCell"), self._visualize_model_name)
        self.gui.get_object("VisibleColumn").set_cell_data_func(
            self.gui.get_object("VisibleSymbol"), self._visualize_visible_state)

    def _edit_model_name(self, cell, path, new_text):
        model = self.get_by_path(path)
        if model and (new_text != model["name"]) and new_text:
            model["name"] = new_text
            self.core.emit_event("model-list-changed")

    def _visualize_model_name(self, column, cell, model, m_iter):
        model_obj = self.get_by_path(model.get_path(m_iter))
        cell.set_property("text", model_obj["name"])

    def _visualize_visible_state(self, column, cell, model, m_iter):
        model_dict = self.get_by_path(model.get_path(m_iter))
        visible = model_dict["visible"]
        if visible:
            cell.set_property("pixbuf", self.ICONS["visible"])
        else:
            cell.set_property("pixbuf", self.ICONS["hidden"])
        color = model_dict["color"]
        cell.set_property("cell-background-gdk", self._gtk.gdk.Color(
            red=int(color["red"] * _GTK_COLOR_MAX),
            green=int(color["green"] * _GTK_COLOR_MAX),
            blue=int(color["blue"] * _GTK_COLOR_MAX)))

    def _toggle_visibility(self, treeview, path, clicked_column):
        model = self.get_by_path(path)
        model["visible"] = not model["visible"]
        self.core.emit_event("visual-item-updated")

    def get_visible(self):
        return [model for model in self if model["visible"]]

    def get_by_uuid(self, uuid):
        for model in self:
            if model["uuid"] == uuid:
                return model
        return None

    def add_model(self, model, name=None, name_template="Model #%d", color=None):
        model_dict = ModelEntity(model)
        if not name:
            name = get_non_conflicting_name(name_template, [m["name"] for m in self])
        model_dict["name"] = name
        if not color:
            color = self.core.get("color_model")
        if not color:
            color = self.FALLBACK_COLOR.copy()
        model_dict["color"] = color
        model_dict["visible"] = True
        self.append(model_dict)


class ModelEntity(pycam.Plugins.ObjectWithAttributes):

    def __init__(self, model):
        super(ModelEntity, self).__init__("model")
        self.model = model
