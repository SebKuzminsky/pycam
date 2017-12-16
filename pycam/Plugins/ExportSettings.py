# -*- coding: utf-8 -*-
"""
Copyright 2017 Lars Kruse <devel@sumpfralle.de>

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


import pycam.Flow.data_models
import pycam.Plugins


class ExportSettings(pycam.Plugins.ListPluginBase):

    UI_FILE = "export_settings.ui"
    CATEGORIES = ["Export"]
    COLLECTION_ITEM_TYPE = pycam.Flow.data_models.ExportSettings

    def setup(self):
        if self.gui:
            self.list_box = self.gui.get_object("ExportSettingsBox")
            self.list_box.unparent()
            self.core.register_ui("main", "Export Settings", self.list_box, weight=50)
            self._gtk_handlers = []
            self._modelview = self.gui.get_object("ExportSettingTable")
            self.set_gtk_modelview(self._modelview)
            self.register_model_update(
                lambda: self.core.emit_event("export-settings-list-changed"))
            self._treemodel = self.gui.get_object("ExportSettingListModel")
            self._treemodel.clear()
            for action, obj_name in ((self.ACTION_UP, "ExportSettingMoveUp"),
                                     (self.ACTION_DOWN, "ExportSettingMoveDown"),
                                     (self.ACTION_DELETE, "ExportSettingDelete"),
                                     (self.ACTION_CLEAR, "ExportSettingDeleteAll")):
                self.register_list_action_button(action, self.gui.get_object(obj_name))
            self._gtk_handlers.append((self.gui.get_object("ExportSettingNew"), "clicked",
                                       self._export_setting_new))
            # details of export settings
            item_details_container = self.gui.get_object("ExportSettingHandlingNotebook")

            def clear_item_details_container():
                for index in range(item_details_container.get_n_pages()):
                    item_details_container.remove_page(0)

            def add_item_details_container(item, name):
                item_details_container.append_page(item, self._gtk.Label(name))

            self.core.register_ui_section("export_settings_handling", add_item_details_container,
                                          clear_item_details_container)
            # handle table changes
            self._gtk_handlers.extend((
                (self._modelview, "row-activated", "export-settings-changed"),
                (self.gui.get_object("ExportSettingNameCell"), "edited", self.edit_item_name)))
            # handle selection changes
            selection = self._modelview.get_selection()
            self._gtk_handlers.append((selection, "changed", "export-settings-selection-changed"))
            # define cell renderers
            self.gui.get_object("ExportSettingNameColumn").set_cell_data_func(
                self.gui.get_object("ExportSettingNameCell"), self.render_item_name)
            self._event_handlers = (
                ("export-settings-list-changed", self.force_gtk_modelview_refresh),
                ("export-settings-selection-changed", self.force_gtk_modelview_refresh),
                ("export-settings-changed", "visual-item-updated"),
                ("export-settings-list-changed", "visual-item-updated"))
            self.register_gtk_handlers(self._gtk_handlers)
            self.register_event_handlers(self._event_handlers)
        return True

    def teardown(self):
        if self.gui and self._gtk:
            self.core.unregister_ui("main", self.gui.get_object("ExportSettingsBox"))
            self.unregister_gtk_handlers(self._gtk_handlers)
            self.unregister_event_handlers(self._event_handlers)

    def _export_setting_new(self, *args):
        new_item = pycam.Flow.data_models.ExportSettings(None, data={})
        new_item.set_application_value("name", self.get_non_conflicting_name("Settings #%d"))
        self.select(new_item)
