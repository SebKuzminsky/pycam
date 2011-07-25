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

import os
# imported later (on demand)
#import gtk

import pycam.Plugins


class PluginSelector(pycam.Plugins.PluginBase):

    UI_FILE = "plugin_selector.ui"

    COLUMN_NAME, COLUMN_DESCRIPTION, COLUMN_ENABLED, COLUMN_DEPENDS, \
            COLUMN_DEPENDS_OK, COLUMN_SOURCE = range(6)

    def setup(self):
        if self.gui:
            import gtk
            self.plugin_window = self.gui.get_object("PluginManagerWindow")
            self.plugin_window.connect("delete-event",
                    self.toggle_plugin_window, False)
            self.plugin_window.connect("destroy",
                    self.toggle_plugin_window, False)
            self.plugin_window.add_accel_group(
                    self.core.get("gtk-accel-group"))
            self.gui.get_object("ClosePluginManager").connect("clicked",
                    self.toggle_plugin_window, False)
            self._treemodel = self.gui.get_object("PluginsModel")
            self._treemodel.clear()
            action = self.gui.get_object("TogglePluginWindow")
            action.connect("toggled", self.toggle_plugin_window)
            self.register_gtk_accelerator("plugins", action, None,
                    "TogglePluginWindow")
            self.core.register_ui("view_menu", "TogglePluginWindow", action, 60)
            self.gui.get_object("PluginsEnabledCell").connect("toggled",
                    self.toggle_plugin_state)
            self.core.register_event("plugin-list-changed",
                    self._update_plugin_model)
            self._update_plugin_model()
        return True

    def teardown(self):
        if self.gui:
            self.plugin_window.hide()
            action = self.gui.get_object("TogglePluginWindow")
            self.core.register_ui("view_menu", action)
            self.core.unregister_event("plugin-list-changed",
                    self._update_plugin_model)

    def toggle_plugin_window(self, widget=None, value=None, action=None):
        toggle_plugin_button = self.gui.get_object("TogglePluginWindow")
        checkbox_state = toggle_plugin_button.get_active()
        if value is None:
            new_state = checkbox_state
        else:
            if action is None:
                new_state = value
            else:
                new_state = action
        if new_state:
            self.plugin_window.show()
        else:
            self.plugin_window.hide()
        toggle_plugin_button.set_active(new_state)
        # don't destroy the window with a "destroy" event
        return True

    def _update_plugin_model(self):
        manager = self.core.get("plugin-manager")
        names = manager.get_plugin_names()
        model = self._treemodel
        model.clear()
        for name in names:
            plugin = manager.get_plugin(name)
            enabled = manager.get_plugin_state(name)
            depends_missing = manager.get_plugin_missing_dependencies(name)
            is_required = manager.is_plugin_required(name)
            satisfied = not (bool(depends_missing) or is_required)
            # never disable the manager
            if plugin == self:
                satisfied = False
            depends_markup = []
            for depend in plugin.DEPENDS:
                if depend in depends_missing:
                    depends_markup.append(
                            '<span foreground="red">%s</span>' % depend)
                else:
                    depends_markup.append(depend)
            model.append((name, "Beschreibung", enabled,
                    os.linesep.join(depends_markup), satisfied,
                    "Hint"))
        self.gui.get_object("PluginsDescriptionColumn").queue_resize()
        self.gui.get_object("PluginsTable").queue_resize()

    def toggle_plugin_state(self, cell, path):
        plugin_name = self._treemodel[int(path)][self.COLUMN_NAME]
        manager = self.core.get("plugin-manager")
        enabled = manager.get_plugin_state(plugin_name)
        if enabled:
            manager.disable_plugin(plugin_name)
        else:
            manager.enable_plugin(plugin_name)
        self._update_plugin_model()

