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


class ModelSupport(pycam.Plugins.PluginBase):

    UI_FILE = "model_support.ui"
    DEPENDS = ["Models"]
    CATEGORIES = ["Model", "Support bridges"]

    def setup(self):
        if self.gui:
            self._support_frame = self.gui.get_object("ModelExtensionsFrame")
            self._support_frame.unparent()
            self.core.register_ui("model_handling", "Support",
                    self._support_frame, 0)
            self.core.register_event("model-change-after",
                    self._support_model_changed)
            self.core.register_event("bounds-changed",
                    self._support_model_changed)
            self.core.register_event("model-selection-changed",
                    self._update_widgets)
            self.core.register_event("support-model-changed",
                    self.update_support_model)
            support_model_type_selector = self.gui.get_object(
                    "SupportGridTypesControl")
            support_model_type_selector.connect("changed",
                    self._support_model_changed)
            def add_support_type(obj, name):
                types_model = support_model_type_selector.get_model()
                types_model.append((obj, name))
                # enable the first item by default
                if len(types_model) == 1:
                    support_model_type_selector.set_active(0)
            self.core.register_ui_section("support_model_type_selector",
                    add_support_type,
                    lambda: support_model_type_selector.get_model().clear())
            self.core.register_ui("support_model_type_selector", "none",
                    "none", weight=-100)
            container = self.gui.get_object("SupportAddOnContainer")
            def clear_support_model_settings():
                children = container.get_children()
                for child in children:
                    container.remove(child)
            self.core.register_ui_section("support_model_settings",
                    lambda obj, name: container.pack_start(obj, expand=False),
                    clear_support_model_settings)
            def get_support_model_type():
                index = support_model_type_selector.get_active()
                if index < 0:
                    return None
                else:
                    selector_model = support_model_type_selector.get_model()
                    return selector_model[index][0]
            def set_support_model_type(model_type):
                selector_model = support_model_type_selector.get_model()
                for index, row in enumerate(selector_model):
                    if row[0] == model_type:
                        support_model_type_selector.set_active(index)
                        break
                else:
                    support_model_type_selector.set_active(-1)
            # TODO: remove public settings
            self.core.add_item("support_model_type",
                    get_support_model_type,
                    set_support_model_type)
            grid_thickness = self.gui.get_object("SupportGridThickness")
            grid_thickness.connect("value-changed", self._support_model_changed)
            self.core.add_item("support_grid_thickness",
                    grid_thickness.get_value, grid_thickness.set_value)
            grid_height = self.gui.get_object("SupportGridHeight")
            grid_height.connect("value-changed", self._support_model_changed)
            self.core.add_item("support_grid_height",
                    grid_height.get_value, grid_height.set_value)
            # support grid defaults
            self.core.set("support_grid_thickness", 0.5)
            self.core.set("support_grid_height", 0.5)
            self.core.set("support_grid_type", "none")
            # prepare GUI
            self._update_widgets()
        return True

    def teardown(self):
        if self.gui:
            self.core.unregister_ui("model_handling",
                    self.gui.get_object("ModelExtensionsFrame"))
            self.core.unregister_ui("support_model_type_selector", "none")
            self.core.unregister_event("model-change-after",
                    self._support_model_changed)
            self.core.unregister_event("bounds-changed",
                    self._support_model_changed)
            self.core.unregister_event("support-model-changed",
                    self.update_support_model)

    def _update_widgets(self):
        if self.core.get("models").get_selected():
            self._support_frame.show()
        else:
            self._support_frame.hide()

    def _support_model_changed(self, widget=None):
        self.core.emit_event("support-model-changed")

    def update_support_model(self, widget=None):
        grid_type = self.core.get("support_model_type")
        if grid_type == "none":
            self.core.set("current_support_model", None)
            self.core.emit_event("visual-item-updated")

