"""
Copyright 2018 Lars Kruse <devel@sumpfralle.de>

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


class VisualizeTool(pycam.Plugins.PluginBase):

    DEPENDS = {"Visualization"}
    CATEGORIES = {"Visualization", "Tool"}

    def setup(self):
        self.core.register_chain("generate_x3d", self.generate_x3d)
        self.core.get("register_display_item")("show_tool", "Show Tool", 70)
        self.core.get("register_color")("color_tool", "Tool", 50)
        self.core.emit_event("visual-item-updated")
        return True

    def teardown(self):
        self.core.unregister_chain("generate_x3d", self.generate_x3d)
        self.core.get("unregister_display_item")("show_tool")
        self.core.get("unregister_color")("color_tool")
        self.core.emit_event("visual-item-updated")

    def generate_x3d(self, tree):
        if self.core.get("show_tool"):
            tool = self.core.get("current_tool")
            if tool is not None:
                color = self.core.get("color_tool")
                tool.to_x3d(color)
