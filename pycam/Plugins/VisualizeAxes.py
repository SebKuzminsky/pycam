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
from pycam.Utils.x3d import get_x3d_cone, get_x3d_line


class VisualizeAxes(pycam.Plugins.PluginBase):

    DEPENDS = {"Visualization"}
    CATEGORIES = {"Visualization"}

    def setup(self):
        self.core.register_chain("generate_x3d", self.generate_x3d)
        self.core.get("register_display_item")("show_axes", "Show Coordinate System", 50)
        self.core.emit_event("visual-item-updated")
        return True

    def teardown(self):
        self.core.unregister_chain("generate_x3d", self.generate_x3d)
        self.core.get("unregister_display_item")("show_axes")
        self.core.emit_event("visual-item-updated")

    def generate_x3d(self, tree):
        if self.core.get("show_axes"):
            low, high = [None, None, None], [None, None, None]
            self.core.call_chain("get_draw_dimension", low, high)
            if None in low or None in high:
                low, high = (0, 0, 0), (10, 10, 10)
            length = 1.2 * max(max(high), abs(min(low)))
            origin = (0, 0, 0)
            axis_ends = (length, 0, 0), (0, length, 0), (0, 0, length)
            colors = ({"red": 0.8, "green": 0, "blue": 0, "alpha": 1},
                      {"red": 0, "green": 0.8, "blue": 0, "alpha": 1},
                      {"red": 0, "green": 0, "blue": 0.8, "alpha": 1})
            cone_length = 0.05 * length

            def axis_generator():
                for end, color in zip(axis_ends, colors):
                    yield from get_x3d_line((origin, end), color, thickness=2)
                    yield from get_x3d_cone((0, 0, 0), end, 1.0, cone_length, cone_length / 2,
                                            color)

            return tree.add_data_source(axis_generator())
