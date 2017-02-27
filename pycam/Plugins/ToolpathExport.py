# -*- coding: utf-8 -*-
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

import pycam.Exporters.GCode.LinuxCNC
import pycam.Plugins


FILTER_GCODE = (("GCode files", ("*.ngc", "*.nc", "*.gc", "*.gcode")),)


class ToolpathExport(pycam.Plugins.PluginBase):

    UI_FILE = "toolpath_export.ui"
    DEPENDS = ["Toolpaths", "FilenameDialog", "ToolpathProcessors"]
    CATEGORIES = ["Toolpath", "Export"]

    def setup(self):
        self._last_toolpath_file = None
        if self.gui:
            self._frame = self.gui.get_object("ToolpathExportFrame")
            self._frame.unparent()
            self.core.register_ui("toolpath_handling", "Export", self._frame, -100)
            self._gtk_handlers = (
                (self.gui.get_object("ExportGCodeAll"), "clicked", self.export_all),
                (self.gui.get_object("ExportGCodeSelected"), "clicked", self.export_selected),
                (self.gui.get_object("ExportGCodeVisible"), "clicked", self.export_visible))
            self._event_handlers = (
                ("toolpath-list-changed", self._update_widgets),
                ("toolpath-selection-changed", self._update_widgets),
                ("toolpath-changed", self._update_widgets))
            self.register_gtk_handlers(self._gtk_handlers)
            self.register_event_handlers(self._event_handlers)
            self._update_widgets()
        return True

    def teardown(self):
        if self.gui:
            self.core.unregister_ui("toolpath_handling", self._frame)
            self.unregister_gtk_handlers(self._gtk_handlers)
            self.unregister_event_handlers(self._event_handlers)

    def _update_widgets(self):
        toolpaths = self.core.get("toolpaths")
        for name, filtered in (("ExportGCodeAll", toolpaths),
                               ("ExportGCodeVisible", toolpaths.get_visible()),
                               ("ExportGCodeSelected", toolpaths.get_selected())):
            self.gui.get_object(name).set_sensitive(bool(filtered))

    def export_all(self, widget=None):
        self._export_toolpaths(self.core.get("toolpaths"))

    def export_visible(self, widget=None):
        self._export_toolpaths(self.core.get("toolpaths").get_visible())

    def export_selected(self, widget=None):
        self._export_toolpaths(self.core.get("toolpaths").get_selected())

    def _export_toolpaths(self, toolpaths):
        # TODO: this is ugly copy'n'paste from pycam.Plugins.OpenGLViewToolpath (draw_toolpaths)
        # KEEP IN SYNC
        processor = self.core.get("toolpath_processors").get_selected()
        if not processor:
            self.log.warn("No toolpath processor selected")
            return
        filter_func = processor["func"]
        filter_params = self.core.get("get_parameter_values")("toolpath_processor")
        settings_filters = filter_func(filter_params)
        # TODO: get "public" filters (metric, ...)
        common_filters = []
        # we open a dialog
        if self.core.get("gcode_filename_extension"):
            filename_extension = self.core.get("gcode_filename_extension")
        else:
            filename_extension = None
        # TODO: separate this away from Gui/Project.py
        # TODO: implement "last_model_filename" in core
        filename = self.core.get("get_filename_func")(
            "Save toolpath to ...", mode_load=False, type_filter=FILTER_GCODE,
            filename_templates=(self._last_toolpath_file, self.core.get("last_model_filename")),
            filename_extension=filename_extension)
        if filename:
            self._last_toolpath_file = filename
        # no filename given -> exit
        if not filename:
            return
        try:
            destination = open(filename, "w")
            # TODO: implement "get_meta_data()"
#           meta_data = self.get_meta_data()
            machine_time = 0
            # calculate the machine time and store it in the GCode header
            for toolpath in toolpaths:
                machine_time += toolpath.get_machine_time()
            # TODO: use this description for the export
#           all_info = (meta_data + os.linesep
#                       + "Estimated machine time: %.0f minutes" % machine_time)
            generator = pycam.Exporters.GCode.LinuxCNC.LinuxCNC(destination)
            generator.add_filters(settings_filters)
            generator.add_filters(common_filters)
            # TODO: investigate, which code pieces we need (path_mode, ...)
            """
            minimum_steps = [self.core.get("gcode_minimum_step_x"),
                    self.core.get("gcode_minimum_step_y"),
                    self.core.get("gcode_minimum_step_z")]
            if self.core.get("touch_off_position_type") == "absolute":
                pos_x = self.core.get("touch_off_position_x")
                pos_y = self.core.get("touch_off_position_y")
                pos_z = self.core.get("touch_off_position_z")
                touch_off_pos = (pos_x, pos_y, pos_z)
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
                generator.set_path_mode(CORNER_STYLE_EXACT_PATH)
            elif path_mode == 1:
                generator.set_path_mode(CORNER_STYLE_EXACT_STOP)
            elif path_mode == 2:
                generator.set_path_mode(CORNER_STYLE_OPTIMIZE_SPEED)
            else:
                naive_tolerance = self.core.get("gcode_naive_tolerance")
                if naive_tolerance == 0:
                    naive_tolerance = None
                generator.set_path_mode(CORNER_STYLE_OPTIMIZE_TOLERANCE,
                        self.core.get("gcode_motion_tolerance"),
                        naive_tolerance)
            """
            for toolpath in toolpaths:
                # TODO: implement toolpath.get_meta_data()
                generator.add_moves(toolpath.path, toolpath.filters)
            generator.finish()
            destination.close()
            self.log.info("GCode file successfully written: %s", str(filename))
        except IOError as err_msg:
            self.log.error("Failed to save toolpath file: %s", err_msg)
        else:
            self.core.emit_event("notify-file-saved", filename)
