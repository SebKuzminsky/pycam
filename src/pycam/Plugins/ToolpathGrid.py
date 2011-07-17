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


class ToolpathGrid(pycam.Plugins.PluginBase):

    UI_FILE = "toolpath_grid.ui"

    def update_toolpath_grid_window(self, widget=None):
        return False
        data = self._toolpath_for_grid_data
        x_dim = data["maxx"] - data["minx"]
        y_dim = data["maxy"] - data["miny"]
        x_count = self.gui.get_object("GridXCount").get_value()
        x_space = self.gui.get_object("GridXDistance").get_value()
        y_count = self.gui.get_object("GridYCount").get_value()
        y_space = self.gui.get_object("GridYDistance").get_value()
        x_width = x_dim * x_count + x_space * (x_count - 1)
        y_width = y_dim * y_count + y_space * (y_count - 1)
        self.gui.get_object("LabelGridXWidth").set_label("%g%s" % \
                (x_width, self.settings.get("unit")))
        self.gui.get_object("LabelGridYWidth").set_label("%g%s" % \
                (y_width, self.settings.get("unit")))
        for objname in ("GridYCount", "GridXCount", "GridYDistance",
                "GridXDistance"):
            self.gui.get_object(objname).connect("value-changed",
                    self.update_toolpath_grid_window)

    def create_toolpath_grid(self, toolpath):
        dialog = self.gui.get_object("ToolpathGridDialog")
        data = self._toolpath_for_grid_data
        data["minx"] = toolpath.minx()
        data["maxx"] = toolpath.maxx()
        data["miny"] = toolpath.miny()
        data["maxy"] = toolpath.maxy()
        self.gui.get_object("GridXCount").set_value(1)
        self.gui.get_object("GridYCount").set_value(1)
        self.update_toolpath_grid_window()
        result = dialog.run()
        if result == 1:
            # "OK" was pressed
            new_tp = []
            x_count = int(self.gui.get_object("GridXCount").get_value())
            y_count = int(self.gui.get_object("GridYCount").get_value())
            x_space = self.gui.get_object("GridXDistance").get_value()
            y_space = self.gui.get_object("GridYDistance").get_value()
            x_dim = data["maxx"] - data["minx"]
            y_dim = data["maxy"] - data["miny"]
            for x in range(x_count):
                for y in range(y_count):
                    shift = Point(x * (x_space + x_dim),
                            y * (y_space + y_dim), 0)
                    for path in toolpath.get_paths():
                        new_path = pycam.Geometry.Path.Path()
                        new_path.points = [shift.add(p) for p in path.points]
                        new_tp.append(new_path)
            new_toolpath = pycam.Toolpath.Toolpath(new_tp, toolpath.name,
                    toolpath.toolpath_settings)
            toolpath.visible = False
            new_toolpath.visible = True
            self.toolpath.append(new_toolpath)
            self.update_toolpath_table()
        dialog.hide()

