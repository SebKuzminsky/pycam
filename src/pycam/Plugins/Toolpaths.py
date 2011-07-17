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

    def setup(self):
        """
                ("ExportGCodeAll", self.save_toolpath, False, "<Control><Shift>e"),
                ("ExportGCodeVisible", self.save_toolpath, True, None),
        # store the original content (for adding the number of current toolpaths in "update_toolpath_table")
        self._original_toolpath_tab_label = self.gui.get_object("ToolpathsTabLabel").get_text()
        """
        self.core.add_item("toolpaths", lambda: self)
        return True

    def teardown(self):
        self.core.set("toolpaths", None)
        return True

    def _update_toolpath_related_controls(self):
        # show or hide the "toolpath" tab
        toolpath_tab = self.gui.get_object("ToolpathsTab")
        if not self.toolpath:
            toolpath_tab.hide()
        else:
            self.gui.get_object("ToolpathsTabLabel").set_text(
                    "%s (%d)" % (self._original_toolpath_tab_label, len(self.toolpath)))
            toolpath_tab.show()
        # enable/disable the export menu item
        self.gui.get_object("ExportGCodeAll").set_sensitive(len(self.toolpath) > 0)
        toolpaths_are_visible = any([tp.visible for tp in self.toolpath])
        self.gui.get_object("ExportGCodeVisible").set_sensitive(
                toolpaths_are_visible)
        self.gui.get_object("ExportVisibleToolpathsButton").set_sensitive(
                toolpaths_are_visible)

    def _update_toolpath_table(self, new_index=None, skip_model_update=False):
        def get_time_string(minutes):
            if minutes > 180:
                return "%d hours" % int(round(minutes / 60))
            elif minutes > 3:
                return "%d minutes" % int(round(minutes))
            else:
                return "%d seconds" % int(round(minutes * 60))
        self.update_toolpath_related_controls()
        # reset the model data and the selection
        if new_index is None:
            # keep the old selection - this may return "None" if nothing is selected
            new_index = self._treeview_get_active_index(self.toolpath_table, self.toolpath)
        if not skip_model_update:
            # update the TreeModel data
            model = self.gui.get_object("ToolPathListModel")
            model.clear()
            # columns: name, visible, drill_size, drill_id, allowance, speed, feedrate
            for index in range(len(self.toolpath)):
                tp = self.toolpath[index]
                toolpath_settings = tp.get_toolpath_settings()
                tool = toolpath_settings.get_tool_settings()
                process = toolpath_settings.get_process_settings()
                items = (index, tp.name, tp.visible, tool["tool_radius"],
                        tool["id"], process["material_allowance"],
                        tool["speed"], tool["feedrate"],
                        get_time_string(tp.get_machine_time(
                                self.settings.get("gcode_safety_height"))))
                model.append(items)
            if not new_index is None:
                self._treeview_set_active_index(self.toolpath_table, new_index)
        # enable/disable the modification buttons
        self.gui.get_object("toolpath_simulate").set_sensitive(not new_index is None)
        self.gui.get_object("ToolpathGrid").set_sensitive(not new_index is None)

