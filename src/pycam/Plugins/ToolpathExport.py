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

import os

import pycam.Plugins
from pycam.Exporters.GCodeExporter import PATH_MODES
from pycam.Geometry.Point import Point


FILTER_GCODE = (("GCode files", ("*.ngc", "*.nc", "*.gc", "*.gcode")),)


class ToolpathExport(pycam.Plugins.PluginBase):

    UI_FILE = "toolpath_export.ui"
    DEPENDS = ["Toolpaths", "FilenameDialog"]
    CATEGORIES = ["Toolpath", "Export"]

    def setup(self):
        self._postprocessors = {}
        self.core.set("register_postprocessor",
                self.register_postprocessor)
        self.core.set("unregister_postprocessor",
                self.unregister_postprocessor)
        self._last_toolpath_file = None
        if self.gui:
            self._frame = self.gui.get_object("ToolpathExportFrame")
            self._frame.unparent()
            self.core.register_ui("toolpath_handling", "Export",
                    self._frame, -100)
            self._postproc_model = self.gui.get_object("PostprocessorList")
            self._postproc_selector = self.gui.get_object(
                    "PostprocessorSelector")
            self.gui.get_object("ExportGCodeAll").connect("clicked",
                    self.export_all)
            self.gui.get_object("ExportGCodeSelected").connect("clicked",
                    self.export_selected)
            self.gui.get_object("ExportGCodeVisible").connect("clicked",
                    self.export_visible)
            self.core.register_event("postprocessors-list-changed",
                    self._update_postprocessors)
            self.core.register_event("toolpath-list-changed",
                    self._update_widgets)
            self.core.register_event("toolpath-selection-changed",
                    self._update_widgets)
            self.core.register_event("toolpath-changed",
                    self._update_widgets)
            self._update_postprocessors()
            self._update_widgets()
        return True

    def teardown(self):
        if self.gui:
            self.core.unregister_ui("toolpath_handling", self._frame)
            self.core.unregister_event("postprocessors-list-changed",
                    self._update_postprocessors)
            self.core.unregister_event("toolpath-list-changed",
                    self._update_widgets)
            self.core.unregister_event("toolpath-selection-changed",
                    self._update_widgets)
            self.core.unregister_event("toolpath-changed",
                    self._update_widgets)

    def register_postprocessor(self, name, label, func):
        if name in self._postprocessors:
            self.log.debug("Registering postprocessor '%s' again" % name)
        processor = {"name": name,
                "label": label,
                "func": func,
        }
        self._postprocessors[name] = processor
        self.core.emit_event("postprocessors-list-changed")

    def unregister_postprocessor(self, name):
        if not name in self._postprocessors:
            self.log.debug("Tried to unregister an unknown postprocessor: " + \
                    name)
        else:
            del self._postprocessors[name]
            self.core.emit_event("postprocessors-list-changed")

    def get_selected(self):
        index = self._postproc_selector.get_active()
        if index < 0:
            return None
        else:
            return self._postproc_model[index][1]

    def select(self, name):
        for index, row in enumerate(self._postproc_model):
            if row[1] == name:
                self._postproc_selector.set_active(index)
                break
        else:
            self._postproc_selector.set_active(-1)

    def _update_postprocessors(self):
        selected = self.get_selected()
        model = self._postproc_model
        model.clear()
        processors = self._postprocessors.values()
        processors.sort(key=lambda item: item["label"])
        for proc in processors:
            model.append((proc["label"], proc["name"]))
        if selected:
            self.select(selected)
        elif len(model) > 0:
            self._postproc_selector.set_active(0)
        else:
            pass

    def _update_widgets(self):
        toolpaths = self.core.get("toolpaths")
        for name, filtered in (("ExportGCodeAll", toolpaths),
                ("ExportGCodeVisible", toolpaths.get_visible()),
                ("ExportGCodeSelected", toolpaths.get_selected())):
            self.gui.get_object(name).set_sensitive(bool(filtered))

    def export_all(self, widget=None):
        self._export_toolpaths(self.core.get("toolpaths"))

    def export_visible(self, widget=None):
        self._export_toolpaths(self.core.get("toolpaths").get_visble())

    def export_selected(self, widget=None):
        self._export_toolpaths(self.core.get("toolpaths").get_selected())

    def _export_toolpaths(self, toolpaths):
        proc_name = self.get_selected()
        processor = self._postprocessors[proc_name]
        if not processor:
            self.log.warn("Unknown postprocessor: %s" % str(name))
            return
        generator_func = processor["func"]
        # we open a dialog
        if self.core.get("gcode_filename_extension"):
            filename_extension = self.core.get("gcode_filename_extension")
        else:
            filename_extension = None
        # TODO: separate this away from Gui/Project.py
        # TODO: implement "last_model_filename" in core
        filename = self.core.get("get_filename_func")("Save toolpath to ...",
                mode_load=False, type_filter=FILTER_GCODE,
                filename_templates=(self._last_toolpath_file, self.core.get("last_model_filename")),
                filename_extension=filename_extension)
        if filename:
            self._last_toolpath_file = filename
        # no filename given -> exit
        if not filename:
            return
        try:
            destination = open(filename, "w")
            safety_height = self.core.get("gcode_safety_height")
            # TODO: implement "get_meta_data()"
            #meta_data = self.get_meta_data()
            meta_data = ""
            machine_time = 0
            # calculate the machine time and store it in the GCode header
            for toolpath in toolpaths:
                machine_time += toolpath.get_machine_time(safety_height)
            all_info = meta_data + os.linesep \
                    + "Estimated machine time: %.0f minutes" % machine_time
            minimum_steps = [self.core.get("gcode_minimum_step_x"),  
                    self.core.get("gcode_minimum_step_y"),  
                    self.core.get("gcode_minimum_step_z")]
            if self.core.get("touch_off_position_type") == "absolute":
                pos_x = self.core.get("touch_off_position_x")
                pos_y = self.core.get("touch_off_position_y")
                pos_z = self.core.get("touch_off_position_z")
                touch_off_pos = Point(pos_x, pos_y, pos_z)
            else:
                touch_off_pos = None
            generator = generator_func(destination,
                    metric_units=(self.core.get("unit") == "mm"),
                    safety_height=safety_height,
                    toggle_spindle_status=self.core.get("gcode_start_stop_spindle"),
                    spindle_delay=self.core.get("gcode_spindle_delay"),
                    comment=all_info, minimum_steps=minimum_steps,
                    touch_off_on_startup=self.core.get("touch_off_on_startup"),
                    touch_off_on_tool_change=self.core.get("touch_off_on_tool_change"),
                    touch_off_position=touch_off_pos,
                    touch_off_rapid_move=self.core.get("touch_off_rapid_move"),
                    touch_off_slow_move=self.core.get("touch_off_slow_move"),
                    touch_off_slow_feedrate=self.core.get("touch_off_slow_feedrate"),
                    touch_off_height=self.core.get("touch_off_height"),
                    touch_off_pause_execution=self.core.get("touch_off_pause_execution"))
            path_mode = self.core.get("gcode_path_mode")
            if path_mode == 0:
                generator.set_path_mode(PATH_MODES["exact_path"])
            elif path_mode == 1:
                generator.set_path_mode(PATH_MODES["exact_stop"])
            elif path_mode == 2:
                generator.set_path_mode(PATH_MODES["continuous"])
            else:
                naive_tolerance = self.core.get("gcode_naive_tolerance")
                if naive_tolerance == 0:
                    naive_tolerance = None
                generator.set_path_mode(PATH_MODES["continuous"],
                        self.core.get("gcode_motion_tolerance"),
                        naive_tolerance)
            for toolpath in toolpaths:
                params = toolpath.get_params()
                tool_id = params.get("tool_id", 1)
                feedrate = params.get("tool_feedrate", 300)
                spindle_speed = params.get("spindle_speed", 1000)
                generator.set_speed(feedrate, spindle_speed)
                # TODO: implement toolpath.get_meta_data()
                generator.add_moves(toolpath.get_moves(safety_height),
                        tool_id=tool_id, comment="")
            generator.finish()
            destination.close()
            self.log.info("GCode file successfully written: %s" % str(filename))
        except IOError, err_msg:
            self.log.error("Failed to save toolpath file: %s" % err_msg)
        else:
            self.core.emit_event("notify-file-saved", filename)

