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
import pycam.workspace.data_models


class VisualizeSupportModelPreview(pycam.Plugins.PluginBase):

    DEPENDS = {"Visualization", "VisualizeModel"}
    CATEGORIES = {"Visualization", "Support bridges"}

    def setup(self):
        self.core.get("register_display_item")("show_support_preview",
                                               "Show Support Model Preview", 30)
        self.core.get("register_color")("color_support_preview", "Support model", 30)
        self.core.register_chain("generate_x3d", self.generate_x3d)
        self.core.emit_event("visual-item-updated")
        return True

    def teardown(self):
        self.core.unregister_chain("generate_x3d", self.generate_x3d)
        self.core.get("unregister_display_item")("show_support_preview")
        self.core.get("unregister_color")("color_support_preview")
        self.core.emit_event("visual-item-updated")

    def generate_x3d(self, tree):
        if not self.core.get("show_support_preview"):
            return
        color = self.core.get("color_support_preview")
        for model_object in (self.core.get("current_support_models") or []):
            model = model_object.get_model()
            if model:
                tree.add_data_source(model.to_x3d(color))
