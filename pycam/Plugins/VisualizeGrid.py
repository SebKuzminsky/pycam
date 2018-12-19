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

import math

import pycam.Plugins
from pycam.Utils.x3d import get_x3d_line


class VisualizeGrid(pycam.Plugins.PluginBase):

    UI_FILE = "visualize_grid.ui"
    DEPENDS = {"Visualization"}
    CATEGORIES = {"Visualization"}
    MINOR_LINES = 5
    MAJOR_LINES = 1

    def setup(self):
        if self.gui:
            self.box = self.gui.get_object("GridSizeBox")
            self.core.register_ui("visualization_window", "Grid", self.box, weight=30)
            self.core.register_event("visual-item-updated", self._update_widget_state)
        self.core.register_chain("generate_x3d", self.generate_x3d)
        self.core.get("register_display_item")("show_grid", "Show Base Grid", 80)
        self.core.get("register_color")("color_grid", "Base Grid", 80)
        self.core.emit_event("visual-item-updated")
        return True

    def teardown(self):
        if self.gui:
            self.core.unregister_event("visual-item-updated", self._update_widget_state)
            self.core.unregister_ui("visualization_window", self.box)
        self.core.unregister_chain("generate_x3d", self.generate_x3d)
        self.core.get("unregister_color")("color_grid")
        self.core.get("unregister_display_item")("show_grid")
        self.core.emit_event("visual-item-updated")

    def _update_widget_state(self):
        if self.core.get("show_grid"):
            self.box.show()
        else:
            self.box.hide()

    def generate_x3d(self, tree):
        if self.core.get("show_grid"):
            low, high = [None, None, None], [None, None, None]
            self.core.call_chain("get_draw_dimension", low, high)
            if None in low or None in high:
                low, high = (0, 0, 0), (10, 10, 10)
            max_value = max(abs(low[0]), abs(low[1]), high[0], high[1])
            base_size = 10 ** int(math.log(max_value, 10))
            grid_size = math.ceil(float(max_value) / base_size) * base_size
            minor_distance = float(base_size) / self.MINOR_LINES
            if grid_size / base_size > 5:
                minor_distance *= 5
            elif grid_size / base_size > 2.5:
                minor_distance *= 2.5
            major_skip = self.MINOR_LINES / self.MAJOR_LINES
            if self.gui:
                unit = self.core.get("unit_string")
                self.gui.get_object("MajorGridSizeLabel").set_text(
                    "%g%s" % (minor_distance * major_skip, unit))
                self.gui.get_object("MinorGridSizeLabel").set_text("%g%s" % (minor_distance, unit))
            line_counter = int(math.ceil(grid_size / minor_distance))
            # the grid should extend to the center of the scene, if all items are in one quadrant
            grid_low = [-grid_size, -grid_size]
            grid_high = [grid_size, grid_size]
            for index in range(2):
                if high[index] <= 0:
                    grid_high[index] = 0
                if low[index] >= 0:
                    grid_low[index] = 0
            z_layer = 0
            color = self.core.get("color_grid")
            # TODO: why could the color be undefined here?
            if color is None:
                color = {"red": 0.75, "green": 1.0, "blue": 0.7, "alpha": 0.55}

            def grid_generator():
                for index in range(-line_counter, line_counter + 1):
                    position = index * minor_distance
                    line_width = 3 if (index % major_skip == 0) else None
                    yield from get_x3d_line(
                        ((grid_low[0], position, z_layer), (grid_high[0], position, z_layer)),
                        color, thickness=line_width)
                    yield from get_x3d_line(
                        ((position, grid_low[1], z_layer), (position, grid_high[1], z_layer)),
                        color, thickness=line_width)

            tree.add_data_source(grid_generator())
