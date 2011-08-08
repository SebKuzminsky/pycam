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
import pycam.Exporters.EMCToolExporter

FILTER_EMC_TOOL = (("EMC tool files", "*.tbl"),)

class EMCToolExport(pycam.Plugins.PluginBase):

    UI_FILE = "emc_tool_export.ui"
    DEPENDS = ["Tools", "FilenameDialog"]
    CATEGORIES = ["Export"]

    def setup(self):
        self._last_emc_tool_file = None
        if self.gui:
            self.export_action = self.gui.get_object("ExportEMCToolDefinition")
            self.register_gtk_accelerator("export", self.export_action, None,
                    "ExportEMCToolDefinition")
            self._gtk_handlers = ((self.export_action, "activate",
                    self.export_emc_tools), )
            self.core.register_ui("export_menu", "ExportEMCToolDefinition",
                    self.export_action, 80)
            self._event_handlers = (("tool-selection-changed",
                    self._update_emc_tool_button), )
            self.register_gtk_handlers(self._gtk_handlers)
            self.register_event_handlers(self._event_handlers)
            self._update_emc_tool_button()
        return True
    
    def teardown(self):
        if self.gui:
            self.core.unregister_ui("export_menu", self.export_emc_tools)
            self.unregister_gtk_accelerator("fonts", self.export_emc_tools)
            self.unregister_gtk_handlers(self._gtk_handlers)
            self.unregister_event_handlers(self._event_handlers)

    def _update_emc_tool_button(self, widget=None):
        exportable = len(self.core.get("tools")) > 0
        self.export_action.set_sensitive(exportable)

    def export_emc_tools(self, widget=None, filename=None):
        if callable(filename):
            filename = filename()
        if not filename:
            # TODO: separate this away from Gui/Project.py
            # TODO: implement "last_model_filename" in core
            filename = self.core.get("get_filename_func")("Save toolpath to ...",
                    mode_load=False, type_filter=FILTER_EMC_TOOL,
                    filename_templates=(self._last_emc_tool_file,
                            self.core.get("last_model_filename")))
        if filename:
            self._last_emc_tool_file = filename
            tools_dict = []
            tools = self.core.get("tools")
            for tool in tools:
                tools_dict.append({"name": tools.get_attr(tool, "name"),
                        "id": tools.get_attr(tool, "id"),
                        "radius": tool["parameters"].get("radius", 1)})
            export = pycam.Exporters.EMCToolExporter.EMCToolExporter(tools_dict)
            text = export.get_tool_definition_string()
            try:
                out = file(filename, "w")
                out.write(text)
                out.close()
                self.log.info("EMC tool file written: %s" % filename)
            except IOError, err_msg:
                self.log.error("Failed to save EMC tool file: %s" % err_msg)
            else:
                self.core.emit_event("notify-file-saved", filename)

