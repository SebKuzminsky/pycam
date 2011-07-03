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


class ModelSupportDistributed(pycam.Plugins.PluginBase):

    UI_FILE = "model_support_distributed.ui"
    DEPENDS = ["Models"]

    def setup(self):
        if self.gui:
            support_expander = self.gui.get_object("DistributedSupportExpander")
            support_expander.unparent()
            self.core.register_ui("support_model_type_selector",
                    "Distributed (edges)", "distributed_edges", weight=0)
            self.core.register_ui("support_model_type_selector",
                    "Distributed (corners)", "distributed_corners", weight=10)
            self.core.register_ui("support_model_settings", "Grid settings",
                    support_expander)
            self.core.register_event("support-model-changed",
                    self.update_support_controls)
            self.core.register_event("support-model-changed",
                    self.update_support_model)
            grid_length = self.gui.get_object("SupportGridLength")
            grid_length.connect("value-changed", self.update_support_model)
            self.core.add_item("support_grid_length",
                    grid_length.get_value, grid_length.set_value)
            average_distance = self.gui.get_object("GridAverageDistance")
            average_distance.connect("value-changed", self.update_support_model)
            self.core.add_item("support_grid_average_distance",
                    average_distance.get_value, average_distance.set_value)
            minimum_bridges = self.gui.get_object("GridMinBridgesPerPolygon")
            minimum_bridges.connect("value-changed", self.update_support_model)
            self.core.add_item("support_grid_minimum_bridges",
                    minimum_bridges.get_value, minimum_bridges.set_value)
            self.core.set("support_grid_average_distance", 30)
            self.core.set("support_grid_minimum_bridges", 2)
            self.core.set("support_grid_length", 5)
        return True

    def update_support_controls(self):
        grid_type = self.core.get("support_model_type")
        if grid_type in ("distributed_edges", "distributed_corners"):
            self.gui.get_object("DistributedSupportExpander").show()
        else:
            self.gui.get_object("DistributedSupportExpander").hide()

    def update_support_model(self, widget=None):
        model = self.core.get("model")
        if not model:
            return
        grid_type = self.core.get("support_model_type")
        support_model = None
        if grid_type in ("distributed_edges", "distributed_corners"):
            s = self.core
            if (s.get("support_grid_thickness") > 0) \
                    and (s.get("support_grid_height") > 0) \
                    and (s.get("support_grid_average_distance") > 0) \
                    and (s.get("support_grid_minimum_bridges") > 0):
                # get the minimum z value of the bounding box
                bounds = s.get("current_bounds")
                if bounds:
                    minz = bounds.get_absolute_limits(
                            reference=model.get_bounds())[0][2]
                    corner_start = (grid_type == "distributed_corners")
                    support_model = pycam.Toolpath.SupportGrid.get_support_distributed(
                            s.get("model"), minz,
                            s.get("support_grid_average_distance"),
                            s.get("support_grid_minimum_bridges"),
                            s.get("support_grid_thickness"),
                            s.get("support_grid_height"),
                            s.get("support_grid_length"),
                            bounds.get_referenced_bounds(s.get("model").get_bounds()),
                            start_at_corners=corner_start)
        if support_model != self.core.get("current_support_model"):
            self.core.set("current_support_model", support_model)
            self.core.emit_event("visual-item-updated")

