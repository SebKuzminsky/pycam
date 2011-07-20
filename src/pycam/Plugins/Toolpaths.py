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

class Toolpaths(pycam.Plugins.ListPluginBase):

    UI_FILE = "toolpaths.ui"
    COLUMN_REF, COLUMN_NAME, COLUMN_VISIBLE = range(3)
    LIST_ATTRIBUTE_MAP = {"name": COLUMN_NAME, "visible": COLUMN_VISIBLE}
    ICONS = {"visible": "visible.svg", "hidden": "visible_off.svg"}

    def setup(self):
        self.last_toolpath_file = None
        if self.gui:
            import gtk
            self.tp_box = self.gui.get_object("ToolpathsBox")
            self.tp_box.unparent()
            self.core.register_ui("main", "Toolpaths", self.tp_box, weight=50)
            self._modelview = self.gui.get_object("ToolpathTable")
            self._treemodel = self.gui.get_object("ToolpathListModel")
            self._treemodel.clear()
            for action, obj_name in ((self.ACTION_UP, "ToolpathMoveUp"),
                    (self.ACTION_DOWN, "ToolpathMoveDown"),
                    (self.ACTION_DELETE, "ToolpathDelete"),
                    (self.ACTION_CLEAR, "ToolpathDeleteAll")):
                self.register_list_action_button(action, self._modelview,
                        self.gui.get_object(obj_name))
            # handle table changes
            self._modelview.connect("row-activated",
                    self._list_action_toggle_custom, self.COLUMN_VISIBLE)
            self.gui.get_object("ToolpathVisibleColumn").set_cell_data_func(
                    self.gui.get_object("ToolpathVisibleSymbol"),
                    self._visualize_machine_time)
            self.gui.get_object("ToolpathNameCell").connect("edited",
                    self._edit_toolpath_name)
            self.gui.get_object("ToolpathTimeColumn").set_cell_data_func(
                    self.gui.get_object("ToolpathTimeCell"),
                    self._visualize_machine_time)
            # handle selection changes
            selection = self._modelview.get_selection()
            selection.connect("changed",
                    lambda widget, event: self.core.emit_event(event), 
                    "toolpath-selection-changed")
            selection.set_mode(gtk.SELECTION_MULTIPLE)
            # configure "export" actions
            export_all = self.gui.get_object("ExportGCodeAll")
            self.register_gtk_accelerator("toolpaths", export_all,
                    "<Control><Shift>e", "ExportGCodeAll")
            export_all.connect("activate", self.save_toolpath, False)
            export_visible = self.gui.get_object("ExportGCodeSelected")
            self.register_gtk_accelerator("toolpaths", export_visible,
                    None, "ExportGCodeSelected")
            export_visible.connect("activate", self.save_toolpath, True)
            # model handling
            def update_model():
                print "UPDATE"
                if not hasattr(self, "_model_cache"):
                    self._model_cache = {}
                cache = self._model_cache
                for row in self._treemodel:
                    cache[row[self.COLUMN_REF]] = list(row)
                self._treemodel.clear()
                for index, item in enumerate(self):
                    if id(item) in cache:
                        self._treemodel.append(cache[id(item)])
                    else:
                        self._treemodel.append((id(item),
                                "Toolpath #%d" % index, True))
                self.core.emit_event("toolpath-list-changed")
            self.register_model_update(update_model)
            self.core.register_event("toolpath-list-changed",
                    self._update_widgets)
            self._update_widgets()
        self.core.add_item("toolpaths", lambda: self)
        return True

    def teardown(self):
        self.core.set("toolpaths", None)
        return True

    def get_selected(self):
        return self._get_selected(self._modelview, force_list=True)

    def get_visible(self):
        return [self[index] for index, item in enumerate(self._treemodel)
                if item[self.COLUMN_VISIBLE]]

    def _update_widgets(self):
        toolpaths = self
        if not toolpaths:
            self.tp_box.hide()
        else:
            self.tp_box.show()
        # enable/disable the export menu item
        self.gui.get_object("ExportGCodeAll").set_sensitive(len(toolpaths) > 0)
        selected_toolpaths = self.get_selected()
        self.gui.get_object("ExportGCodeSelected").set_sensitive(
                len(selected_toolpaths) > 0)

    def _list_action_toggle_custom(self, treeview, path, clicked_column,
            force_column=None):
        if force_column is None:
            column = self._modelview.get_columns().index(clicked_column)
        else:
            column = force_column
        self._list_action_toggle(clicked_column, str(path[0]), column)

    def _list_action_toggle(self, widget, path, column):
        path = int(path)
        model = self._treemodel
        model[path][column] = not model[path][column]
        self.core.emit_event("visual-item-updated")

    def _edit_toolpath_name(self, cell, path, new_text):
        path = int(path)
        if (new_text != self._treemodel[path][self.COLUMN_NAME]) and \
                new_text:
            self._treemodel[path][self.COLUMN_NAME] = new_text

    def _visualize_machine_time(self, column, cell, model, m_iter):
        path = model.get_path(m_iter)
        toolpath = self[path[0]]
        def get_time_string(minutes):
            if minutes > 180:
                return "%d hours" % int(round(minutes / 60))
            elif minutes > 3:
                return "%d minutes" % int(round(minutes))
            else:
                return "%d seconds" % int(round(minutes * 60))
        text = get_time_string(toolpath.get_machine_time(
                self.core.get("gcode_safety_height")))
        cell.set_property("text", text)

    def save_toolpath(self, widget=None, only_visible=False):
        if only_visible:
            toolpaths = self.get_selected()
        else:
            toolpaths = self
        if not toolpaths:
            return
        if callable(widget):
            widget = widget()
        if isinstance(widget, basestring):
            filename = widget
        else:
            # we open a dialog
            if self.core.get("gcode_filename_extension"):
                filename_extension = self.core.get("gcode_filename_extension")
            else:
                filename_extension = None
            # TODO: separate this away from Gui/Project.py
            filename = self.get_filename_via_dialog("Save toolpath to ...",
                    mode_load=False, type_filter=FILTER_GCODE,
                    filename_templates=(self.last_toolpath_file, self.last_model_uri),
                    filename_extension=filename_extension)
            if filename:
                self.last_toolpath_file = filename
        self._update_widgets()
        # no filename given -> exit
        if not filename:
            return
        try:
            destination = open(filename, "w")
            safety_height = self.core.get("gcode_safety_height")
            meta_data = self.get_meta_data()
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
            generator = GCodeGenerator(destination,
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
                settings = toolpath.get_toolpath_settings()
                tool = settings.get_tool_settings()
                generator.set_speed(tool["feedrate"], tool["speed"])
                generator.add_moves(toolpath.get_moves(safety_height),
                        tool_id=tool["id"], comment=toolpath.get_meta_data())
            generator.finish()
            destination.close()
            log.info("GCode file successfully written: %s" % str(filename))
        except IOError, err_msg:
            log.error("Failed to save toolpath file: %s" % err_msg)
        else:
            self.add_to_recent_file_list(filename)

