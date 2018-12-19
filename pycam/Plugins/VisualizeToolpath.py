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
from pycam.Geometry.PointUtils import pdist
from pycam.Toolpath import MOVES_LIST, MOVE_STRAIGHT_RAPID
from pycam.Utils.x3d import get_x3d_cone, get_x3d_line


class VisualizeToolpath(pycam.Plugins.PluginBase):

    DEPENDS = {"Visualization", "Toolpaths", "ExportSettings"}
    CATEGORIES = {"Toolpath", "Visualization"}

    def setup(self):
        self.core.get("register_color")("color_toolpath_cut", "Toolpath cut", 60)
        self.core.get("register_color")("color_toolpath_return", "Toolpath rapid", 70)
        self.core.register_chain("get_draw_dimension", self.get_draw_dimension)
        self.core.register_chain("generate_x3d", self.generate_x3d)
        self.core.get("register_display_item")("show_toolpath", "Show Toolpath", 30)
        self._event_handlers = (
            ("toolpath-list-changed", "visual-item-updated"),
            ("toolpath-changed", "visual-item-updated"))
        self.register_event_handlers(self._event_handlers)
        self.core.emit_event("visual-item-updated")
        return True

    def teardown(self):
        self.core.unregister_chain("generate_x3d", self.generate_x3d)
        self.core.unregister_chain("get_draw_dimension", self.get_draw_dimension)
        self.unregister_event_handlers(self._event_handlers)
        self.core.get("unregister_color")("color_toolpath_cut")
        self.core.get("unregister_color")("color_toolpath_return")
        self.core.get("unregister_display_item")("show_toolpath")
        self.core.emit_event("visual-item-updated")

    def get_draw_dimension(self, low, high):
        if self._is_visible():
            toolpaths = self.core.get("toolpaths").get_visible()
            for toolpath_dict in toolpaths:
                tp = toolpath_dict.get_toolpath()
                if tp:
                    mlow = tp.minx, tp.miny, tp.minz
                    mhigh = tp.maxx, tp.maxy, tp.maxz
                    if None in mlow or None in mhigh:
                        continue
                    for index in range(3):
                        if (low[index] is None) or (mlow[index] < low[index]):
                            low[index] = mlow[index]
                        if (high[index] is None) or (mhigh[index] > high[index]):
                            high[index] = mhigh[index]

    def _is_visible(self):
        return self.core.get("show_toolpath") \
                and not self.core.get("toolpath_in_progress") \
                and not self.core.get("show_simulation")

    def generate_x3d(self, tree):
        toolpath_in_progress = self.core.get("toolpath_in_progress")
        if toolpath_in_progress is None and self.core.get("show_toolpath"):
            settings_filters = []
            # Use the currently selected export settings for an intuitive behaviour.
            selected_export_settings = self.core.get("export_settings").get_selected()
            if selected_export_settings:
                settings_filters.extend(selected_export_settings.get_toolpath_filters())
            for toolpath_dict in self.core.get("toolpaths").get_visible():
                toolpath = toolpath_dict.get_toolpath()
                if toolpath:
                    moves = toolpath.get_basic_moves(filters=settings_filters)
                    tree.add_data_source(self._get_x3d_moves(moves))
        elif toolpath_in_progress is not None:
            if self.core.get("show_simulation") or self.core.get("show_toolpath_progress"):
                tree.add_data_source(self._get_x3d_moves(toolpath_in_progress))

    # Simulate still depends on this pathway
    def _get_x3d_moves(self, moves):
        show_directions = self.core.get("show_directions")
        color_rapid = self.core.get("color_toolpath_return")
        color_cut = self.core.get("color_toolpath_cut")
        last_position = None
        transitions = []
        for step in moves:
            if step.action not in MOVES_LIST:
                continue
            is_rapid = step.action == MOVE_STRAIGHT_RAPID
            color = color_rapid if is_rapid else color_cut
            if last_position is not None:
                yield from get_x3d_line((last_position, step.position), color)
            if show_directions and (last_position is not None):
                transitions.append((last_position, step.position, color))
            last_position = step.position
        if show_directions:
            for p1, p2, color in transitions:
                line_length = pdist(p1, p2)
                if line_length > 0:
                    yield from get_x3d_cone(p1, p2, 0.5, 0.05 * line_length, 0.02 * line_length,
                                            color)
