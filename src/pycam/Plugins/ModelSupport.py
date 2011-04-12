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


GRID_TYPES = {"none": 0, "grid": 1, "automatic_edge": 2, "automatic_corner": 3}

# TODO: manual_adjust_slider is stuck; automatic distribution does now show up

class ModelSupport(pycam.Plugins.PluginBase):

    UI_FILE = "model_support.ui"

    def setup(self):
        if self.gui:
            support_frame = self.gui.get_object("ModelExtensionsFrame")
            support_frame.unparent()
            self.core.register_ui("model_handling", "Support", support_frame, 0)
            self.core.set("get_support_model", self.support_model_factory)
            self.core.register_event("model-change-after", self.update_support_model)
            self.core.register_event("model-change-after", self.update_support_controls)
            self.core.register_event("boundary-updated",
                    self.update_support_grid_manual_adjust)
            # support grid
            self.grid_adjustments_x = []
            self.grid_adjustments_y = []
            support_grid_type_control = self.gui.get_object(
                    "SupportGridTypesControl")
            support_grid_type_control.connect("changed",
                    self.update_support_controls)
            self.core.add_item("support_grid_type",
                    support_grid_type_control.get_active,
                    support_grid_type_control.set_active)
            self.core.set("support_grid_type", GRID_TYPES["none"])
            grid_distance_x = self.gui.get_object("SupportGridDistanceX")
            grid_distance_x.connect("value-changed", self.update_support_controls)
            self.core.add_item("support_grid_distance_x",
                    grid_distance_x.get_value, grid_distance_x.set_value)
            grid_distance_square = self.gui.get_object("SupportGridDistanceSquare")
            grid_distance_square.connect("clicked", self.update_support_controls)
            grid_distance_y = self.gui.get_object("SupportGridDistanceY")
            grid_distance_y.connect("value-changed", self.update_support_controls)
            def get_support_grid_distance_y():
                if grid_distance_square.get_active():
                    return self.core.get("support_grid_distance_x")
                else:
                    return grid_distance_y.get_value()
            self.core.add_item("support_grid_distance_y",
                    get_support_grid_distance_y, grid_distance_y.set_value)
            grid_thickness = self.gui.get_object("SupportGridThickness")
            grid_thickness.connect("value-changed", self.update_support_model)
            self.core.add_item("support_grid_thickness",
                    grid_thickness.get_value, grid_thickness.set_value)
            grid_height = self.gui.get_object("SupportGridHeight")
            grid_height.connect("value-changed", self.update_support_model)
            self.core.add_item("support_grid_height",
                    grid_height.get_value, grid_height.set_value)
            grid_length = self.gui.get_object("SupportGridLength")
            grid_length.connect("value-changed", self.update_support_model)
            self.core.add_item("support_grid_length",
                    grid_length.get_value, grid_length.set_value)
            grid_offset_x = self.gui.get_object("SupportGridOffsetX")
            grid_offset_x.connect("value-changed", self.update_support_model)
            self.core.add_item("support_grid_offset_x",
                    grid_offset_x.get_value, grid_offset_x.set_value)
            grid_offset_y = self.gui.get_object("SupportGridOffsetY")
            grid_offset_y.connect("value-changed", self.update_support_model)
            self.core.add_item("support_grid_offset_y",
                    grid_offset_y.get_value, grid_offset_y.set_value)
            grid_average_distance = self.gui.get_object("GridAverageDistance")
            grid_average_distance.connect("value-changed",
                    self.update_support_model)
            self.core.add_item("support_grid_average_distance",
                    grid_average_distance.get_value,
                    grid_average_distance.set_value)
            grid_minimum_bridges = self.gui.get_object("GridMinBridgesPerPolygon")
            grid_minimum_bridges.connect("value-changed", self.update_support_model)
            self.core.add_item("support_grid_minimum_bridges",
                    grid_minimum_bridges.get_value, grid_minimum_bridges.set_value)
            # manual grid adjustments
            self.grid_adjustment_axis_x = self.gui.get_object("SupportGridPositionManualAxisX")
            self.grid_adjustment_axis_x.connect("toggled",
                    self.switch_support_grid_manual_selector)
            self.gui.get_object("SupportGridPositionManualResetOne").connect(
                    "clicked", self.reset_support_grid_manual, False)
            self.gui.get_object("SupportGridPositionManualResetAll").connect(
                    "clicked", self.reset_support_grid_manual, True)
            self.grid_adjustment_model = self.gui.get_object(
                    "SupportGridPositionManualList")
            self.grid_adjustment_selector = self.gui.get_object(
                    "SupportGridPositionManualSelector")
            self.grid_adjustment_selector.connect("changed",
                    self.switch_support_grid_manual_selector)
            self.grid_adjustment_value = self.gui.get_object(
                    "SupportGridPositionManualAdjustment")
            self.grid_adjustment_value_control = self.gui.get_object(
                    "SupportGridPositionManualShiftControl")
            self.grid_adjustment_value_control.connect("move-slider",
                    self.update_support_grid_manual_adjust)
            self.grid_adjustment_value_control.connect("value-changed",
                    self.update_support_grid_manual_adjust)
            self.gui.get_object("SupportGridPositionManualShiftControl2").connect(
                    "value-changed", self.update_support_grid_manual_adjust)
            def get_set_grid_adjustment_value(value=None):
                if self.grid_adjustment_axis_x.get_active():
                    adjustments = self.grid_adjustments_x
                else:
                    adjustments = self.grid_adjustments_y
                index = self.grid_adjustment_selector.get_active()
                if value is None:
                    if 0 <= index < len(adjustments):
                        return adjustments[index]
                    else:
                        return 0
                else:
                    while len(adjustments) <= index:
                        adjustments.append(0)
                    adjustments[index] = value
            self.core.add_item("support_grid_adjustment_value",
                    get_set_grid_adjustment_value, get_set_grid_adjustment_value)
            # support grid defaults
            grid_distance_square.set_active(True)
            self.core.set("support_grid_distance_x", 10.0)
            self.core.set("support_grid_thickness", 0.5)
            self.core.set("support_grid_height", 0.5)
            self.core.set("support_grid_average_distance", 30)
            self.core.set("support_grid_minimum_bridges", 2)
            self.core.set("support_grid_length", 5)
            self.grid_adjustment_axis_x_last = True
            # refresh everything
            self.update_support_controls()
        return True

    def teardown(self):
        if self.gui:
            self.core.unregister_ui("model_handling",
                    self.gui.get_object("ModelExtensionsFrame"))

    def update_support_controls(self, widget=None):
        controls = {"GridProfileExpander": ("grid", "automatic_edge",
                    "automatic_corner"),
                "GridPatternExpander": ("grid", ),
                "GridPositionExpander": ("grid", ),
                "GridManualShiftExpander": ("grid", ),
                "GridAverageDistanceExpander": ("automatic_edge",
                    "automatic_corner"),
        }
        grid_type = self.core.get("support_grid_type")
        if grid_type == GRID_TYPES["grid"]:
            grid_square = self.gui.get_object("SupportGridDistanceSquare")
            distance_y = self.gui.get_object("SupportGridDistanceYControl")
            distance_y.set_sensitive(not grid_square.get_active())
            if grid_square.get_active():
                # We let "distance_y" track the value of "distance_x".
                self.core.set("support_grid_distance_y",
                        self.core.get("support_grid_distance_x"))
            self.update_support_grid_manual_model()
            self.switch_support_grid_manual_selector()
        elif grid_type in (GRID_TYPES["automatic_edge"],
                GRID_TYPES["automatic_corner"], GRID_TYPES["none"]):
            pass
        elif grid_type < 0:
            # not initialized
            pass
        else:
            log.error("Invalid grid type: %d" % grid_type)
        # show and hide all controls according to the current type
        for key, grid_types in controls.iteritems():
            obj = self.gui.get_object(key)
            if grid_type in [GRID_TYPES[allowed] for allowed in grid_types]:
                obj.show()
            else:
                obj.hide()
        self.core.emit_event("model-change-after")

    def update_support_model(self, widget=None):
        model = self.core.get("model")
        if not model:
            return
        grid_type = self.core.get("support_grid_type")
        s = self.core
        support_grid = None
        if grid_type == GRID_TYPES["grid"]: 
            if (s.get("support_grid_thickness") > 0) \
                    and ((s.get("support_grid_distance_x") > 0) \
                        or (s.get("support_grid_distance_y") > 0)) \
                    and ((s.get("support_grid_distance_x") == 0) \
                        or (s.get("support_grid_distance_x") \
                            > s.get("support_grid_thickness"))) \
                    and ((s.get("support_grid_distance_y") == 0) \
                        or (s.get("support_grid_distance_y") \
                            > s.get("support_grid_thickness"))) \
                    and (s.get("support_grid_height") > 0):
                support_grid = pycam.Toolpath.SupportGrid.get_support_grid(
                        s.get("minx"), s.get("maxx"), s.get("miny"), s.get("maxy"),
                        s.get("minz"), s.get("support_grid_distance_x"),
                        s.get("support_grid_distance_y"),
                        s.get("support_grid_thickness"),
                        s.get("support_grid_height"),
                        offset_x=s.get("support_grid_offset_x"),
                        offset_y=s.get("support_grid_offset_y"),
                        adjustments_x=self.grid_adjustments_x,
                        adjustments_y=self.grid_adjustments_y)
        elif grid_type in (GRID_TYPES["automatic_edge"],
                GRID_TYPES["automatic_corner"]):
            if (s.get("support_grid_thickness") > 0) \
                    and (s.get("support_grid_height") > 0) \
                    and (s.get("support_grid_average_distance") > 0) \
                    and (s.get("support_grid_minimum_bridges") > 0):
                # get the minimum z value of the bounding box
                bounds = self.core.get("current_bounds")
                if not bounds is None:
                    minz = bounds.get_absolute_limits(
                            reference=model.get_bounds())[0][2]
                    corner_start = (grid_type == GRID_TYPES["automatic_corner"])
                    support_grid = pycam.Toolpath.SupportGrid.get_support_distributed(
                            s.get("model"), minz,
                            s.get("support_grid_average_distance"),
                            s.get("support_grid_minimum_bridges"),
                            s.get("support_grid_thickness"),
                            s.get("support_grid_height"),
                            s.get("support_grid_length"),
                            bounds.get_referenced_bounds(s.get("model").get_bounds()),
                            start_at_corners=corner_start)
        elif grid_type == GRID_TYPES["none"]:
            pass
        s.set("support_grid", support_grid)
        self.core.emit_event("model-change-after")

    def switch_support_grid_manual_selector(self, widget=None):
        old_axis_was_x = self.grid_adjustment_axis_x_last
        self.grid_adjustment_axis_x_last = \
                self.grid_adjustment_axis_x.get_active()
        if self.grid_adjustment_axis_x.get_active():
            # x axis is selected
            if not old_axis_was_x:
                self.update_support_grid_manual_model()
            max_distance = self.core.get("support_grid_distance_x")
        else:
            # y axis
            if old_axis_was_x:
                self.update_support_grid_manual_model()
            max_distance = self.core.get("support_grid_distance_y")
        # we allow an individual adjustment of 66% of the distance
        max_distance /= 1.5
        if hasattr(self.grid_adjustment_value, "set_lower"):
            # gtk 2.14 is required for "set_lower" and "set_upper"
            self.grid_adjustment_value.set_lower(-max_distance)
            self.grid_adjustment_value.set_upper(max_distance)
        if self.grid_adjustment_value.get_value() \
                != self.core.get("support_grid_adjustment_value"):
            self.grid_adjustment_value.set_value(self.core.get(
                    "support_grid_adjustment_value"))
        self.gui.get_object("SupportGridPositionManualShiftBox").set_sensitive(
                self.grid_adjustment_selector.get_active() >= 0)
        
    def update_support_grid_manual_adjust(self, widget=None, data1=None,
            data2=None):
        new_value = self.grid_adjustment_value.get_value()
        self.core.set("support_grid_adjustment_value", new_value)
        tree_iter = self.grid_adjustment_selector.get_active_iter()
        if not tree_iter is None:
            value_string = "(%+.1f)" % new_value
            self.grid_adjustment_model.set(tree_iter, 1, value_string)
        self.core.emit_event("model-change-after")

    def reset_support_grid_manual(self, widget=None, reset_all=False):
        if reset_all:
            self.grid_adjustments_x = []
            self.grid_adjustments_y = []
        else:
            self.core.set("support_grid_adjustment_value", 0)
        self.update_support_grid_manual_model()
        self.switch_support_grid_manual_selector()
        self.core.emit_event("model-change-after")

    def update_support_grid_manual_model(self):
        old_index = self.grid_adjustment_selector.get_active()
        model = self.grid_adjustment_model
        model.clear()
        s = self.core
        # get the toolpath without adjustments
        base_x, base_y = pycam.Toolpath.SupportGrid.get_support_grid_locations(
                s.get("minx"), s.get("maxx"), s.get("miny"), s.get("maxy"),
                s.get("support_grid_distance_x"),
                s.get("support_grid_distance_y"),
                offset_x=s.get("support_grid_offset_x"),
                offset_y=s.get("support_grid_offset_y"))
        # fill the adjustment lists
        while len(self.grid_adjustments_x) < len(base_x):
            self.grid_adjustments_x.append(0)
        while len(self.grid_adjustments_y) < len(base_y):
            self.grid_adjustments_y.append(0)
        # select the currently active list
        if self.grid_adjustment_axis_x.get_active():
            base = base_x
            adjustments = self.grid_adjustments_x
        else:
            base = base_y
            adjustments = self.grid_adjustments_y
        # generate the model content
        for index, base_value in enumerate(base):
            position = "%.2f%s" % (base_value, s.get("unit"))
            if (0 <= index < len(adjustments)) and (adjustments[index] != 0):
                diff = "(%+.1f)" % adjustments[index]
            else:
                diff = ""
            model.append((position, diff))
        if old_index < len(base):
            self.grid_adjustment_selector.set_active(old_index)
        else:
            self.grid_adjustment_selector.set_active(-1)

    def support_model_factory(self, tp_settings):
        # get the support grid options
        grid_type = self.core.get("support_grid_type")
        if grid_type == GRID_TYPES["grid"]:
            tp_settings.set_support_grid(
                    self.core.get("support_grid_distance_x"),
                    self.core.get("support_grid_distance_y"),
                    self.core.get("support_grid_thickness"),
                    self.core.get("support_grid_height"),
                    offset_x=self.core.get("support_grid_offset_x"),
                    offset_y=self.core.get("support_grid_offset_y"),
                    adjustments_x=self.grid_adjustments_x,
                    adjustments_y=self.grid_adjustments_y)
        elif grid_type in (GRID_TYPES["automatic_edge"],
                GRID_TYPES["automatic_corner"]):
            corner_start = (grid_type == GRID_TYPES["automatic_corner"])
            tp_settings.set_support_distributed(
                    self.core.get("support_grid_average_distance"),
                    self.core.get("support_grid_minimum_bridges"),
                    self.core.get("support_grid_thickness"),
                    self.core.get("support_grid_height"),
                    self.core.get("support_grid_length"),
                    start_at_corners=corner_start)
        elif grid_type == GRID_TYPES["none"]:
            pass
        else:
            log.error("Invalid support grid type: %d" % grid_type)
        
