"""
Copyright 2011-2018 Lars Kruse <devel@sumpfralle.de>

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


class VisualizeBounds(pycam.Plugins.PluginBase):

    DEPENDS = {"Visualization", "Bounds"}
    CATEGORIES = {"Bounds", "Visualization"}

    def setup(self):
        self._event_handlers = []
        self.core.get("register_color")("color_bounding_box", "Bounding box", 40)
        self.core.get("register_display_item")("show_bounding_box", "Show Bounding Box", 40)
        self.core.register_chain("get_draw_dimension", self.get_draw_dimension)
        self.core.register_chain("generate_x3d", self.generate_x3d)
        self._event_handlers.extend((("bounds-list-changed", "visual-item-updated"),
                                     ("bounds-changed", "visual-item-updated")))
        self.register_event_handlers(self._event_handlers)
        self.core.emit_event("visual-item-updated")
        return True

    def teardown(self):
        self.unregister_event_handlers(self._event_handlers)
        self.core.unregister_chain("generate_x3d", self.generate_x3d)
        self.core.unregister_chain("get_draw_dimension", self.get_draw_dimension)
        self.core.get("unregister_color")("color_bounding_box")
        self.core.get("unregister_display_item")("show_bounding_box")
        self.core.emit_event("visual-item-updated")

    def get_draw_dimension(self, low, high):
        if not self.core.get("show_bounding_box"):
            return
        model_box = self._get_bounds()
        if model_box is None:
            return
        for index in range(3):
            if (low[index] is None) or (model_box.lower[index] < low[index]):
                low[index] = model_box.lower[index]
            if (high[index] is None) or (model_box.upper[index] > high[index]):
                high[index] = model_box.upper[index]

    def _get_bounds(self):
        bounds = self.core.get("bounds").get_selected()
        return bounds.get_absolute_limits() if bounds else None

    def generate_x3d(self, tree):
        if self.core.get("show_bounding_box"):
            box = self._get_bounds()
            if box is not None:
                color = self.core.get("color_bounding_box")
                tree.add_data_source(box.to_x3d(color))
