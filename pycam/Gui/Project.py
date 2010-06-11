#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$

Copyright 2010 Lars Kruse <devel@sumpfralle.de>

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


import pycam.Importers.STLImporter
import pycam.Exporters.STLExporter
import pycam.Exporters.SimpleGCodeExporter
import pycam.Exporters.EMCToolExporter
import pycam.Gui.Settings
import pycam.Cutters
import pycam.Toolpath.Generator
import pycam.Toolpath
import pycam.Geometry.utils as utils
from pycam.Gui.OpenGLTools import ModelViewWindowGL
import pycam.Physics.ode_physics
# this requires ODE - we import it later, if necessary
#import pycam.Simulation.ODEBlocks
import gtk
import ConfigParser
import math
import time
import re
import os
import sys

DATA_DIR_ENVIRON_KEY = "PYCAM_DATA_DIR"
DATA_BASE_DIRS = [os.path.join(os.path.dirname(__file__), "gtk-interface"), os.path.join(sys.prefix, "share", "python-pycam", "ui")]
if DATA_DIR_ENVIRON_KEY in os.environ:
    DATA_BASE_DIRS.insert(0, os.environ[DATA_DIR_ENVIRON_KEY])

GTKBUILD_FILE = "pycam-project.ui"
GTKMENU_FILE = "menubar.xml"

FILTER_GCODE = ("GCode files", ("*.ngc", "*.nc", "*.gc", "*.gcode"))
FILTER_MODEL = (("STL models", "*.stl"), ("DXF contours", "*.dxf"))
FILTER_CONFIG = ("Config files", "*.conf")
FILTER_EMC_TOOL = ("EMC tool files", "*.tbl")

PREFERENCES_DEFAULTS = {
        "enable_ode": False,
        "boundary_mode": -1,
        "unit": "mm",
        "show_model": True,
        "show_support_grid": True,
        "show_axes": True,
        "show_dimensions": True,
        "show_bounding_box": True,
        "show_toolpath": True,
        "show_drill_progress": False,
        "color_background": (0.0, 0.0, 0.0),
        "color_model": (0.5, 0.5, 1.0),
        "color_support_grid": (0.8, 0.8, 0.3),
        "color_bounding_box": (0.3, 0.3, 0.3),
        "color_cutter": (1.0, 0.2, 0.2),
        "color_toolpath_cut": (1.0, 0.5, 0.5),
        "color_toolpath_return": (0.5, 1.0, 0.5),
        "color_material": (1.0, 0.5, 0.0),
        "view_light": True,
        "view_shadow": True,
        "view_polygon": True,
        "simulation_details_level": 3,
        "drill_progress_max_fps": 2,
}
""" the listed items will be loaded/saved via the preferences file in the
user's home directory on startup/shutdown"""

# floating point color values are only available since gtk 2.16
GTK_COLOR_MAX = 65535.0

def get_data_file_location(filename):
    for base_dir in DATA_BASE_DIRS:
        test_path = os.path.join(base_dir, filename)
        if os.path.exists(test_path):
            return test_path
    else:
        print >>sys.stderr, "Failed to locate a resource file (%s) in %s!" % (filename, DATA_BASE_DIRS)
        print >>sys.stderr, "You can extend the search path by setting the environment variable '%s'." % str(DATA_DIR_ENVIRON_KEY)
        return None

def show_error_dialog(window, message):
    warn_window = gtk.MessageDialog(window, type=gtk.MESSAGE_ERROR,
            buttons=gtk.BUTTONS_OK, message_format=str(message))
    warn_window.set_title("Error")
    warn_window.run()
    warn_window.destroy()


class ProjectGui:

    BOUNDARY_MODES = {
            "inside": -1,
            "along": 0,
            "around": 1}

    def __init__(self, master=None, no_dialog=False):
        """ TODO: remove "master" above when the Tk interface is abandoned"""
        self.settings = pycam.Gui.Settings.Settings()
        self.gui_is_active = False
        self.view3d = None
        # during initialization any dialog (e.g. "Unit change") is not allowed
        # we set the final value later
        self.no_dialog = True
        self._batch_queue = []
        self._progress_running = False
        self._progress_cancel_requested = False
        self.gui = gtk.Builder()
        gtk_build_file = get_data_file_location(GTKBUILD_FILE)
        if gtk_build_file is None:
            sys.exit(1)
        self.gui.add_from_file(gtk_build_file)
        self.window = self.gui.get_object("ProjectWindow")
        # file loading
        self.last_task_settings_file = None
        self.last_model_file = None
        self.last_toolpath_file = None
        # define callbacks and accelerator keys for the menu actions
        for objname, callback, data, accel_key in (
                ("LoadTaskSettings", self.load_task_settings_file, None, "<Control>t"),
                ("SaveTaskSettings", self.save_task_settings_file, lambda: self.last_task_settings_file, None),
                ("SaveAsTaskSettings", self.save_task_settings_file, None, None),
                ("LoadModel", self.load_model_file, None, "<Control>l"),
                ("SaveModel", self.save_model, lambda: self.last_model_file, "<Control>s"),
                ("SaveAsModel", self.save_model, None, "<Control><Shift>s"),
                ("ExportGCode", self.save_toolpath, None, "<Control><Shift>e"),
                ("ExportEMCToolDefinition", self.export_emc_tools, None, None),
                ("Quit", self.destroy, None, "<Control>q"),
                ("GeneralSettings", self.toggle_preferences_window, None, "<Control>p"),
                ("Toggle3DView", self.toggle_3d_view, None, "<Control>v")):
            item = self.gui.get_object(objname)
            if objname == "Toggle3DView":
                action = "toggled"
            else:
                action = "activate"
            item.connect(action, callback, data)
            if accel_key:
                key, mod = gtk.accelerator_parse(accel_key)
                accel_path = "<pycam>/%s" % objname
                item.set_accel_path(accel_path)
                gtk.accel_map_change_entry(accel_path, key, mod, True)
        # other events
        self.window.connect("destroy", self.destroy)
        # the settings window
        self.gui.get_object("CloseSettingsWindow").connect("clicked", self.toggle_preferences_window, False)
        self.gui.get_object("ResetPreferencesButton").connect("clicked", self.reset_preferences)
        self.preferences_window = self.gui.get_object("GeneralSettingsWindow")
        self.preferences_window.connect("delete-event", self.toggle_preferences_window, False)
        self._preferences_window_position = None
        self._preferences_window_visible = False
        # "about" window
        self.about_window = self.gui.get_object("AboutWindow")
        self.gui.get_object("About").connect("activate", self.toggle_about_window, True)
        # "unit change" window
        self.unit_change_window = self.gui.get_object("UnitChangeDialog")
        self.gui.get_object("UnitChangeApply").connect("clicked", self.change_unit_apply)
        self.unit_change_window.connect("delete_event", self.change_unit_apply, False)
        # we assume, that the last child of the window is the "close" button
        # TODO: fix this ugly hack!
        self.gui.get_object("AboutWindowButtons").get_children()[-1].connect("clicked", self.toggle_about_window, False)
        self.about_window.connect("delete-event", self.toggle_about_window, False)
        # set defaults
        self.model = None
        self.toolpath = pycam.Toolpath.ToolPathList()
        self.cutter = None
        self.process_list = []
        self.tool_list = []
        self.task_list = []
        self._last_unit = None
        # add some dummies - to be implemented later ...
        self.settings.add_item("model", lambda: self.model)
        self.settings.add_item("toolpath", lambda: self.toolpath)
        self.settings.add_item("cutter", lambda: self.cutter)
        # unit control (mm/inch)
        unit_field = self.gui.get_object("unit_control")
        unit_field.connect("changed", self.change_unit_init)
        def set_unit(text):
            unit_field.set_active(0 if text == "mm" else 1)
            self._last_unit = text
        self.settings.add_item("unit", unit_field.get_active_text, set_unit)
        self.gui.get_object("UnitChangeSelectAll").connect("clicked", self.change_unit_set_selection, True)
        self.gui.get_object("UnitChangeSelectNone").connect("clicked", self.change_unit_set_selection, False)
        # boundary mode (move inside/along/around the boundaries)
        boundary_mode_control = self.gui.get_object("BoundaryModeControl")
        def set_boundary_mode(value):
            # we assume, that the items in the list are (-1, 0, +1)
            boundary_mode_control.set_active(value + 1)
        def get_boundary_mode():
            return boundary_mode_control.get_active() - 1
        self.settings.add_item("boundary_mode", get_boundary_mode, set_boundary_mode)
        # define the limit callback functions
        for limit in ["minx", "miny", "minz", "maxx", "maxy", "maxz"]:
            obj = self.gui.get_object(limit)
            self.settings.add_item(limit, obj.get_value, obj.set_value)
            obj.connect("value-changed", self.update_boundary_limits)
        # connect the "Bounds" action
        self.gui.get_object("Minimize bounds").connect("clicked", self.minimize_bounds)
        self.gui.get_object("Reset bounds").connect("clicked", self.reset_bounds)
        # Transformations
        self.gui.get_object("Rotate").connect("clicked", self.transform_model)
        self.gui.get_object("Flip").connect("clicked", self.transform_model)
        self.gui.get_object("Swap").connect("clicked", self.transform_model)
        self.gui.get_object("Shift Model").connect("clicked", self.shift_model, True)
        self.gui.get_object("Shift To Origin").connect("clicked", self.shift_model, False)
        # scale model
        self.gui.get_object("ScalePercent").set_value(100)
        self.gui.get_object("ScaleModelButton").connect("clicked", self.scale_model)
        # scale model to an axis dimension
        self.gui.get_object("ScaleDimensionAxis").connect("changed", self.switch_scale_axis)
        self.gui.get_object("ScaleDimensionButton").connect("clicked", self.scale_model_axis_fit)
        # support grid
        self.gui.get_object("SupportGridEnable").connect("clicked", self.update_support_grid_controls)
        grid_distance = self.gui.get_object("SupportGridDistance")
        grid_distance.connect("value-changed", self.update_support_grid_controls)
        self.settings.add_item("support_grid_distance",
                grid_distance.get_value, grid_distance.set_value)
        grid_thickness = self.gui.get_object("SupportGridThickness")
        grid_thickness.connect("value-changed", self.update_support_grid_controls)
        self.settings.add_item("support_grid_thickness",
                grid_thickness.get_value, grid_thickness.set_value)
        self.settings.set("support_grid_distance", 5.0)
        self.settings.set("support_grid_thickness", 0.5)
        # visual and general settings
        for name, objname in (("show_model", "ShowModelCheckBox"),
                ("show_support_grid", "ShowSupportGridCheckBox"),
                ("show_axes", "ShowAxesCheckBox"),
                ("show_dimensions", "ShowDimensionsCheckBox"),
                ("show_bounding_box", "ShowBoundingCheckBox"),
                ("show_toolpath", "ShowToolPathCheckBox"),
                ("show_drill_progress", "ShowDrillProgressCheckBox")):
            obj = self.gui.get_object(objname)
            self.settings.add_item(name, obj.get_active, obj.set_active)
            # all of the objects above should trigger redraw
            obj.connect("toggled", self.update_view)
        for name, objname in (
                ("view_light", "OpenGLLight"),
                ("view_shadow", "OpenGLShadow"),
                ("view_polygon", "OpenGLPolygon")):
            obj = self.gui.get_object(objname)
            self.settings.add_item(name, obj.get_active, obj.set_active)
            # send "True" to trigger a re-setup of GL settings
            obj.connect("toggled", self.update_view, True)
        # color selectors
        def get_color_wrapper(obj):
            def gtk_color_to_float():
                gtk_color = obj.get_color()
                return (gtk_color.red / GTK_COLOR_MAX, gtk_color.green / GTK_COLOR_MAX, gtk_color.blue / GTK_COLOR_MAX)
            return gtk_color_to_float
        def set_color_wrapper(obj):
            def set_gtk_color_by_float((red, green, blue)):
                obj.set_color(gtk.gdk.Color(int(red * GTK_COLOR_MAX),
                        int(green * GTK_COLOR_MAX), int(blue * GTK_COLOR_MAX)))
            return set_gtk_color_by_float
        for name, objname in (("color_background", "ColorBackground"),
                ("color_model", "ColorModel"),
                ("color_support_grid", "ColorSupportGrid"),
                ("color_bounding_box", "ColorBoundingBox"),
                ("color_cutter", "ColorDrill"),
                ("color_toolpath_cut", "ColorToolpathCut"),
                ("color_toolpath_return", "ColorToolpathReturn"),
                ("color_material", "ColorMaterial")):
            obj = self.gui.get_object(objname)
            self.settings.add_item(name, get_color_wrapper(obj), set_color_wrapper(obj))
            # repaint the 3d view after a color change
            obj.connect("color-set", self.update_view)
        # set the availability of ODE
        enable_ode_control = self.gui.get_object("SettingEnableODE")
        if pycam.Physics.ode_physics.is_ode_available():
            self.settings.add_item("enable_ode", enable_ode_control.get_active, enable_ode_control.set_active)
        else:
            enable_ode_control.set_sensitive(False)
            # bind dummy get/set functions to "enable_ode" (always return False)
            self.settings.add_item("enable_ode", lambda: False, lambda state: None)
        skip_obj = self.gui.get_object("DrillProgressFrameSkipControl")
        self.settings.add_item("drill_progress_max_fps", skip_obj.get_value, skip_obj.set_value)
        sim_detail_obj = self.gui.get_object("SimulationDetailsValue")
        self.settings.add_item("simulation_details_level", sim_detail_obj.get_value, sim_detail_obj.set_value)
        # drill settings
        for objname, key in (
                ("ToolRadiusControl", "tool_radius"),
                ("TorusRadiusControl", "torus_radius"),
                ("FeedrateControl", "feedrate"),
                ("SpeedControl", "speed")):
            self.gui.get_object(objname).connect("value-changed", self.handle_tool_settings_change)
        for name in ("SphericalCutter", "CylindricalCutter", "ToroidalCutter"):
            self.gui.get_object(name).connect("clicked", self.handle_tool_settings_change)
        self.gui.get_object("ToolName").connect("changed", self.handle_tool_settings_change)
        # speed and feedrate controls
        speed_control = self.gui.get_object("SpeedControl")
        feedrate_control = self.gui.get_object("FeedrateControl")
        # connect the "consistency check" and the update-handler with all toolpath settings
        for objname in ("PathAccumulator", "SimpleCutter", "ZigZagCutter", "PolygonCutter", "ContourCutter",
                "DropCutter", "PushCutter", "PathDirectionX", "PathDirectionY", "PathDirectionXY", "SettingEnableODE"):
            self.gui.get_object(objname).connect("toggled", self.update_process_controls)
            if objname != "SettingEnableODE":
                self.gui.get_object(objname).connect("toggled", self.handle_process_settings_change)
        for objname in ("SafetyHeightControl", "OverlapPercentControl",
                "MaterialAllowanceControl", "MaxStepDownControl"):
            self.gui.get_object(objname).connect("value-changed", self.handle_process_settings_change)
        self.gui.get_object("ProcessSettingName").connect("changed", self.handle_process_settings_change)
        # the process manager
        self.process_table = self.gui.get_object("ProcessListTable")
        self.process_editor_table = self.gui.get_object("ProcessEditorWindowTable")
        self.process_editor_table.get_selection().connect("changed", self.switch_process_table_selection)
        process_editor_window = self.gui.get_object("ProcessEditorWindow")
        process_editor_window.connect("delete-event", self.toggle_process_editor_window, False)
        # set a minimum size - otherwise the window is too small for an empty table
        process_editor_window.set_default_size(400, -1)
        self.gui.get_object("ProcessEditorWindowOpen").connect("clicked", self.toggle_process_editor_window, True)
        self.gui.get_object("ProcessEditorWindowClose").connect("clicked", self.toggle_process_editor_window, False)
        self.gui.get_object("ProcessListMoveUp").connect("clicked", self.handle_process_table_event, "move_up")
        self.gui.get_object("ProcessListMoveDown").connect("clicked", self.handle_process_table_event, "move_down")
        self.gui.get_object("ProcessListAdd").connect("clicked", self.handle_process_table_event, "add")
        self.gui.get_object("ProcessListDelete").connect("clicked", self.handle_process_table_event, "delete")
        # progress bar and task pane
        self.progress_bar = self.gui.get_object("ProgressBar")
        self.progress_widget = self.gui.get_object("ProgressWidget")
        self.task_pane = self.gui.get_object("MainTabs")
        self.gui.get_object("ProgressCancelButton").connect("clicked", self.cancel_progress)
        # make sure that the toolpath settings are consistent
        self.toolpath_table = self.gui.get_object("ToolPathTable")
        self.toolpath_table.get_selection().connect("changed", self.toolpath_table_event, "update_buttons")
        self.gui.get_object("toolpath_visible").connect("toggled", self.toolpath_table_event, "toggle_visibility")
        self.gui.get_object("toolpath_up").connect("clicked", self.toolpath_table_event, "move_up")
        self.gui.get_object("toolpath_down").connect("clicked", self.toolpath_table_event, "move_down")
        self.gui.get_object("toolpath_delete").connect("clicked", self.toolpath_table_event, "delete")
        self.gui.get_object("toolpath_simulate").connect("clicked", self.toolpath_table_event, "simulate")
        self.gui.get_object("ExitSimulationButton").connect("clicked", self.finish_toolpath_simulation)
        self.gui.get_object("UpdateSimulationButton").connect("clicked", self.update_toolpath_simulation)
        # store the original content (for adding the number of current toolpaths in "update_toolpath_table")
        self._original_toolpath_tab_label = self.gui.get_object("ToolPathTabLabel").get_text()
        # tool editor
        self.tool_table = self.gui.get_object("ToolListTable")
        self.tool_editor_table = self.gui.get_object("ToolEditorWindowTable")
        self.tool_editor_table.get_selection().connect("changed", self.switch_tool_editor_table_selection)
        tool_editor_window = self.gui.get_object("ToolEditorWindow")
        tool_editor_window.set_default_size(400, -1)
        tool_editor_window.connect("delete-event", self.toggle_tool_editor_window, False)
        self.gui.get_object("ToolEditorWindowOpen").connect("clicked", self.toggle_tool_editor_window, True)
        self.gui.get_object("ToolEditorWindowClose").connect("clicked", self.toggle_tool_editor_window, False)
        self.gui.get_object("ToolEditorMoveUp").connect("clicked", self._tool_editor_button_event, "move_up")
        self.gui.get_object("ToolEditorMoveDown").connect("clicked", self._tool_editor_button_event, "move_down")
        self.gui.get_object("ToolEditorAdd").connect("clicked", self._tool_editor_button_event, "add")
        self.gui.get_object("ToolEditorDelete").connect("clicked", self._tool_editor_button_event, "delete")
        # the task list manager
        self.tasklist_table = self.gui.get_object("TaskListTable")
        self.tasklist_table.get_selection().connect("changed", self.update_tasklist_controls)
        self.tool_table.get_selection().connect("changed", self.update_tasklist_controls)
        self.process_table.get_selection().connect("changed", self.update_tasklist_controls)
        self.gui.get_object("tasklist_enabled").connect("toggled", self._handle_tasklist_button_event, "toggle_enabled")
        self.gui.get_object("TaskListMoveUp").connect("clicked", self._handle_tasklist_button_event, "move_up")
        self.gui.get_object("TaskListMoveDown").connect("clicked", self._handle_tasklist_button_event, "move_down")
        self.gui.get_object("TaskListAdd").connect("clicked", self._handle_tasklist_button_event, "add")
        self.gui.get_object("TaskListDelete").connect("clicked", self._handle_tasklist_button_event, "delete")
        self.gui.get_object("GenerateToolPathButton").connect("clicked", self._handle_tasklist_button_event, "generate_one_toolpath")
        self.gui.get_object("GenerateAllToolPathsButton").connect("clicked", self._handle_tasklist_button_event, "generate_all_toolpaths")
        # menu bar
        uimanager = gtk.UIManager()
        self._accel_group = uimanager.get_accel_group()
        self.window.add_accel_group(self._accel_group)
        self.about_window.add_accel_group(self._accel_group)
        self.preferences_window.add_accel_group(self._accel_group)
        # load menu data
        gtk_menu_file = get_data_file_location(GTKMENU_FILE)
        if gtk_menu_file is None:
            sys.exit(1)
        uimanager.add_ui_from_file(gtk_menu_file)
        # make the actions defined in the GTKBUILD file available in the menu
        actiongroup = gtk.ActionGroup("menubar")
        for action in [action for action in self.gui.get_objects() if isinstance(action, gtk.Action)]:
            actiongroup.add_action(action)
        # the "pos" parameter is optional since 2.12 - we can remove it later
        uimanager.insert_action_group(actiongroup, pos=-1)
        # load the menubar and connect functions to its items
        self.menubar = uimanager.get_widget("/MenuBar")
        window_box = self.gui.get_object("WindowBox")
        window_box.pack_start(self.menubar, False)
        window_box.reorder_child(self.menubar, 0)
        # some more initialization
        self.reset_preferences()
        self.load_preferences()
        self.load_task_settings()
        self.update_all_controls()
        self.no_dialog = no_dialog
        if not self.no_dialog:
            self.window.show()

    def update_all_controls(self):
        self.update_toolpath_table()
        self.update_tool_table()
        self.update_process_controls()
        self.update_process_table()
        self.update_tasklist_table()
        self.update_tasklist_controls()
        self.update_save_actions()
        self.update_unit_labels()
        self.update_support_grid_controls()
        self.switch_scale_axis()

    def progress_activity_guard(func):
        def progress_activity_guard_wrapper(self, *args, **kwargs):
            if self._progress_running:
                return
            self._progress_running = True
            self._progress_cancel_requested = False
            self.toggle_progress_bar(True)
            result = func(self, *args, **kwargs)
            self.toggle_progress_bar(False)
            self._progress_running = False
            return result
        return progress_activity_guard_wrapper

    def gui_activity_guard(func):
        def gui_activity_guard_wrapper(self, *args, **kwargs):
            if self.gui_is_active:
                return
            self.gui_is_active = True
            result = func(self, *args, **kwargs)
            self.gui_is_active = False
            while self._batch_queue:
                batch_func, batch_args, batch_kwargs = self._batch_queue[0]
                del self._batch_queue[0]
                batch_func(*batch_args, **batch_kwargs)
            return result
        return gui_activity_guard_wrapper

    def update_view(self, widget=None, data=None):
        if self.view3d and self.view3d.is_visible and not self.no_dialog:
            if data:
                self.view3d.glsetup()
            self.view3d.paint()

    def update_save_actions(self):
        self.gui.get_object("SaveTaskSettings").set_sensitive(not self.last_task_settings_file is None)
        self.gui.get_object("SaveModel").set_sensitive(not self.last_model_file is None)

    @gui_activity_guard
    def update_support_grid_controls(self, widget=None):
        is_enabled = self.gui.get_object("SupportGridEnable").get_active()
        details_box = self.gui.get_object("SupportGridDetailsBox")
        if is_enabled:
            details_box.show()
        else:
            details_box.hide()
        self.update_support_grid_model()
        self.update_view()

    def update_support_grid_model(self):
        is_enabled = self.gui.get_object("SupportGridEnable").get_active()
        s = self.settings
        if is_enabled \
                and (s.get("support_grid_thickness") > 0) \
                and (s.get("support_grid_distance") > s.get("support_grid_thickness")):
            s.set("support_grid",
                    pycam.Toolpath.SupportGrid.get_support_grid(s.get("minx"),
                            s.get("maxx"), s.get("miny"), s.get("maxy"),
                            s.get("minz"), s.get("support_grid_distance"),
                            s.get("support_grid_distance"),
                            s.get("support_grid_thickness")))
        else:
            self.settings.set("support_grid", None)

    def update_boundary_limits(self, widget=None):
        # the support grid depends on the boundary
        self.update_support_grid_model()
        self.update_view()

    def update_tasklist_controls(self, widget=None, data=None):
        # check if both the tool and the process table have a selected row
        all_are_active = True
        for control in (self.tool_table, self.process_table):
            if control.get_selection().get_selected()[1] is None:
                all_are_active = False
        self.gui.get_object("TaskListAdd").set_sensitive(all_are_active)
        # en/disable some buttons
        index = self._treeview_get_active_index(self.tasklist_table, self.task_list)
        selection_active = not index is None
        self.gui.get_object("TaskListDelete").set_sensitive(selection_active)
        self.gui.get_object("TaskListMoveUp").set_sensitive(selection_active and index > 0)
        self.gui.get_object("TaskListMoveDown").set_sensitive(selection_active and index < len(self.task_list) - 1)
        self.gui.get_object("GenerateToolPathButton").set_sensitive(selection_active)
        # check if any of the tasks is marked as "enabled"
        enabled_count = len([True for task in self.task_list if task["enabled"]])
        self.gui.get_object("GenerateAllToolPathsButton").set_sensitive(enabled_count > 0)
        # update the task description
        lines = []
        task_index = self._treeview_get_active_index(self.tasklist_table, self.task_list)
        if (not task_index is None) and (task_index < len(self.task_list)):
            task = self.task_list[task_index]
            tool = task["tool"]
            process = task["process"]
            unit = self.settings.get("unit")
            tool_desc = "Tool: %s " % tool["shape"]
            if tool["shape"] != "ToroidalCutter":
                tool_desc += "(%.4f%s)" % (tool["tool_radius"], unit)
            else:
                tool_desc += "(%.4f%s / %.4f%s)" % (tool["tool_radius"], unit, tool["torus_radius"], unit)
            lines.append(tool_desc)
            lines.append("Speed: %d/minute / Feedrate: %d%s/minute" % (tool["speed"], tool["feedrate"], unit))
            lines.append("Path: %s / %s" % (process["path_generator"], process["path_postprocessor"]))
            lines.append("Overlap: %d%%" % process["overlap_percent"])
            lines.append("Material allowance: %.2f%s" % (process["material_allowance"], unit))
            if process["path_generator"] == "PushCutter":
                lines.append("Maximum step down: %.2f%s" % (process["step_down"], unit))
        else:
            lines.append("No task selected")
        self.gui.get_object("CurrentTaskSummary").set_text(os.linesep.join(lines))

    def update_tasklist_table(self, new_index=None, skip_model_update=False):
        tasklist_model = self.gui.get_object("TaskList")
        if new_index is None:
            # keep the old selection - this may return "None" if nothing is selected
            new_index = self._treeview_get_active_index(self.tasklist_table, self.task_list)
        if not skip_model_update:
            tasklist_model.clear()
            # remove broken tasks from the list (tool or process was deleted)
            self.task_list = [task for task in self.task_list
                    if (task["tool"] in self.tool_list) and (task["process"] in self.process_list)]
            counter = 0
            for task in self.task_list:
                tasklist_model.append((counter, task["tool"]["name"], task["process"]["name"], task["enabled"]))
                counter += 1
            if not new_index is None:
                self._treeview_set_active_index(self.tasklist_table, new_index)
        self.update_tasklist_controls()

    @gui_activity_guard
    def _handle_tasklist_button_event(self, widget, data, action=None):
        # "toggle" uses two parameters - all other actions have only one
        if action is None:
            action = data
        # get the index of the currently selected task
        try:
            current_task_index = self._treeview_get_active_index(self.tasklist_table, self.task_list)
        except ValueError:
            current_task_index = None
        self._treeview_button_event(self.tasklist_table, self.task_list, action, self.update_tasklist_table)
        if action == "add":
            tool_index = self._treeview_get_active_index(self.tool_table, self.tool_list)
            process_index = self._treeview_get_active_index(self.process_table, self.process_list)
            new_task = {}
            new_task["tool"] = self.tool_list[tool_index]
            new_task["process"] = self.process_list[process_index]
            new_task["enabled"] = True
            self.task_list.append(new_task)
            self.update_tasklist_table(self.task_list.index(new_task))
        elif action == "toggle_enabled":
            # "data" contains the row of the clicked checkbox
            if not data is None:
                current_task_index = int(data)
                if (not current_task_index is None) and (current_task_index < len(self.task_list)):
                    self.task_list[current_task_index]["enabled"] = not self.task_list[current_task_index]["enabled"]
                # update the table values
                self.update_tasklist_table(current_task_index)
        elif action == "generate_all_toolpaths":
            self.process_multiple_tasks()
        elif action == "generate_one_toolpath":
            self.process_one_task(current_task_index)
        else:
            pass

    def process_one_task(self, task_index):
        try:
            task = self.task_list[task_index]
        except IndexError:
            # this shoudl only happen, if we were called in batch mode (command line)
            print >>sys.stderr, "The given task ID (%d) does not exist. Valid values are: %s." % (task_index, range(len(self.task_list)))
            return
        self.generate_toolpath(task["tool"], task["process"])

    def process_multiple_tasks(self, task_list=None):
        if task_list is None:
            task_list = self.task_list[:]
        enabled_tasks = []
        for index in range(len(task_list)):
            task = task_list[index]
            if task["enabled"]:
                enabled_tasks.append(task)
        progress_bar = self.gui.get_object("MultipleProgressBar")
        progress_bar.show()
        for index in range(len(enabled_tasks)):
            progress_bar.set_fraction(float(index) / len(enabled_tasks))
            progress_bar.set_text("Toolpath %d/%d" % (index, len(enabled_tasks)))
            task = enabled_tasks[index]
            if not self.generate_toolpath(task["tool"], task["process"]):
                # break out of the loop, if cancel was requested
                break
        progress_bar.hide()

    def update_process_controls(self, widget=None, data=None):
        # possible dependencies of the DropCutter
        get_obj = lambda name: self.gui.get_object(name)
        cutter_name = None
        for one_cutter in ("DropCutter", "PushCutter", "EngraveCutter"):
            if get_obj(one_cutter).get_active():
                cutter_name = one_cutter
        if cutter_name == "DropCutter":
            if get_obj("PathDirectionXY").get_active():
                get_obj("PathDirectionX").set_active(True)
            if not (get_obj("PathAccumulator").get_active() or get_obj("ZigZagCutter").get_active()):
                get_obj("PathAccumulator").set_active(True)
            dropcutter_active = True
        elif cutter_name == "PushCutter":
            if not (get_obj("SimpleCutter").get_active() \
                    or get_obj("PolygonCutter").get_active() \
                    or get_obj("ContourCutter").get_active()):
                get_obj("SimpleCutter").set_active(True)
            dropcutter_active = False
        else:
            # engraving
            if not get_obj("PathAccumulator").get_active():
                get_obj("PathAccumulator").set_active(True)
        all_controls = ("PathDirectionX", "PathDirectionY", "PathDirectionXY",
                "SimpleCutter", "PolygonCutter", "ContourCutter",
                "PathAccumulator", "ZigZagCutter", "MaxStepDownControl",
                "MaterialAllowanceControl", "OverlapPercentControl")
        active_controls = {
            "DropCutter": ("PathAccumulator", "ZigZagCutter", "PathDirectionX",
                    "PathDirectionY", "MaterialAllowanceControl",
                    "OverlapPercentControl"),
            "PushCutter": ("SimpleCutter", "PolygonCutter", "ContourCutter",
                    "PathDirectionX", "PathDirectionY", "PathDirectionXY",
                    "MaxStepDownControl", "MaterialAllowanceControl",
                    "OverlapPercentControl"),
            "EngraveCutter": ("PathAccumulator", "MaxStepDownControl"),
        }
        for one_control in all_controls:
            get_obj(one_control).set_sensitive(one_control in active_controls[cutter_name])

    def update_tool_controls(self, widget=None, data=None):
        # disable the toroidal radius if the toroidal cutter is not enabled
        is_torus_shape = self.gui.get_object("ToroidalCutter").get_active()
        self.gui.get_object("TorusRadiusControl").set_sensitive(is_torus_shape)
        for objname, default_value in (("ToolRadiusControl", 1.0),
                ("TorusRadiusControl", 0.25),
                ("SpeedControl", 1000),
                ("FeedrateControl", 200)):
            obj = self.gui.get_object(objname)
            if obj.get_value() == 0:
                # set the value to the configured minimum
                obj.set_value(default_value)
        self.gui.get_object("ExportEMCToolDefinition").set_sensitive(len(self.tool_list) > 0)

    @gui_activity_guard
    def toggle_about_window(self, widget=None, event=None, state=None):
        # only "delete-event" uses four arguments
        # TODO: unify all these "toggle" functions for different windows into one single function (including storing the position)
        if state is None:
            state = event
        if state:
            self.about_window.show()
        else:
            self.about_window.hide()
        # don't close the window - just hide it (for "delete-event")
        return True

    @gui_activity_guard
    def toggle_preferences_window(self, widget=None, event=None, state=None):
        if state is None:
            # the "delete-event" issues the additional "event" argument
            state = event
        if state is None:
           state = not self._preferences_window_visible
        if state:
            if self._preferences_window_position:
                self.preferences_window.move(*self._preferences_window_position)
            self.preferences_window.show()
        else:
            self._preferences_window_position = self.preferences_window.get_position()
            self.preferences_window.hide()
        self._preferences_window_visible = state
        # don't close the window - just hide it (for "delete-event")
        return True

    def toggle_tool_editor_window(self, widget=None, event=None, state=None):
        # only "delete-event" uses four arguments
        if state is None:
            state = event
        if state:
            tool_index = self._treeview_get_active_index(self.tool_table, self.tool_list)
            if not tool_index is None:
                self._treeview_set_active_index(self.tool_editor_table, tool_index)
            self.gui.get_object("ToolEditorWindow").show()
        else:
            self.gui.get_object("ToolEditorWindow").hide()
        # don't close the window - just hide it (for "delete-event")
        return True

    def toggle_process_editor_window(self, widget=None, event=None, state=None):
        # only "delete-event" uses four arguments
        if state is None:
            state = event
        if state:
            process_index = self._treeview_get_active_index(self.process_table, self.process_list)
            if not process_index is None:
                self._treeview_set_active_index(self.process_editor_table, process_index)
            self.gui.get_object("ProcessEditorWindow").show()
        else:
            self.gui.get_object("ProcessEditorWindow").hide()
        # don't close the window - just hide it (for "delete-event")
        return True

    @gui_activity_guard
    def toggle_3d_view(self, widget=None, value=None):
        # no interactive mode
        if self.no_dialog:
            return
        if self.view3d and not self.view3d.enabled:
            # initialization failed - don't do anything
            return
        current_state = not ((self.view3d is None) or (not self.view3d.is_visible))
        if value is None:
            new_state = not current_state
        else:
            new_state = value
        if new_state == current_state:
            return
        elif new_state:
            if self.view3d is None:
                # do the gl initialization
                self.view3d = ModelViewWindowGL(self.gui, self.settings,
                        notify_destroy=self.toggle_3d_view,
                        accel_group=self._accel_group)
                if self.model and self.view3d.enabled:
                    self.reset_bounds()
                    self.view3d.reset_view()
                # disable the "toggle" button, if the 3D view does not work
                self.gui.get_object("Toggle3DView").set_sensitive(self.view3d.enabled)
            else:
                # the window is just hidden
                self.view3d.show()
            self.update_view()
        else:
            self.view3d.hide()
        self.gui.get_object("Toggle3DView").set_active(new_state)

    @gui_activity_guard
    def transform_model(self, widget):
        if widget is self.gui.get_object("Rotate"):
            controls = (("x-axis", "x"), ("y-axis", "y"), ("z-axis", "z"))
        elif widget is self.gui.get_object("Flip"):
            controls = (("xy-plane", "xy"), ("xz-plane", "xz"), ("yz-plane", "yz"))
        elif widget is self.gui.get_object("Swap"):
            controls = (("x <-> y", "x_swap_y"), ("x <-> z", "x_swap_z"), ("y <-> z", "y_swap_z"))
        else:
            # broken gui
            print >> sys.stderr, "Unknown button action: %s" % str(widget.get_name())
            return
        for obj, value in controls:
            if self.gui.get_object(obj).get_active():
                self.model.transform_by_template(value)
        self.update_view()

    def _treeview_get_active_index(self, table, datalist):
        if len(datalist) == 0:
            result = None
        else:
            treeselection = table.get_selection()
            (model, iteration) = treeselection.get_selected()
            # the first item in the model is the index within the list
            try:
                result = model[iteration][0]
            except TypeError:
                result = None
        return result

    def _treeview_set_active_index(self, table, index):
        treeselection = table.get_selection()
        treeselection.select_path((index,))

    def _treeview_button_event(self, table, datalist, action, update_func):
        future_selection_index = None
        index = self._treeview_get_active_index(table, datalist)
        skip_model_update = False
        if action == "update_buttons":
            skip_model_update = True
        elif action == "move_up":
            if index > 0:
                # move an item one position up the list
                selected = datalist[index]
                above = datalist[index-1]
                datalist[index] = above
                datalist[index-1] = selected
                future_selection_index = index - 1
        elif action == "move_down":
            if index + 1 < len(datalist):
                # move an item one position down the list
                selected = datalist[index]
                below = datalist[index+1]
                datalist[index] = below
                datalist[index+1] = selected
                future_selection_index = index + 1
        elif action == "delete":
            # delete one item from the list
            datalist.remove(datalist[index])
            # don't set a new index, if the list emptied
            if len(datalist) > 0:
                if index < len(datalist):
                    future_selection_index = index
                else:
                    # the last item was removed
                    future_selection_index = len(datalist) - 1
        else:
            pass
        update_func(new_index=future_selection_index, skip_model_update=skip_model_update)

    def _put_tool_settings_to_gui(self, settings):
        self.gui.get_object("ToolName").set_text(settings["name"])
        # cutter shapes
        def set_cutter_shape_name(value):
            self.gui.get_object(value).set_active(True)
        set_cutter_shape_name(settings["shape"])
        for objname, key in (
                ("ToolRadiusControl", "tool_radius"),
                ("TorusRadiusControl", "torus_radius"),
                ("FeedrateControl", "feedrate"),
                ("SpeedControl", "speed")):
            self.gui.get_object(objname).set_value(settings[key])

    def _load_tool_settings_from_gui(self, settings=None):
        if settings is None:
            settings = {}
        settings["name"] = self.gui.get_object("ToolName").get_text()
        def get_cutter_shape_name():
            for name in ("SphericalCutter", "CylindricalCutter", "ToroidalCutter"):
                if self.gui.get_object(name).get_active():
                    return name
        settings["shape"] = get_cutter_shape_name()
        for objname, key in (
                ("ToolRadiusControl", "tool_radius"),
                ("TorusRadiusControl", "torus_radius"),
                ("FeedrateControl", "feedrate"),
                ("SpeedControl", "speed")):
            settings[key] = self.gui.get_object(objname).get_value()
        return settings

    @gui_activity_guard
    def handle_tool_settings_change(self, widget=None, data=None):
        current_index = self._treeview_get_active_index(self.tool_editor_table, self.tool_list)
        if not current_index is None:
            self._load_tool_settings_from_gui(self.tool_list[current_index])
            self.update_tool_table()
        self.update_tool_controls()

    @gui_activity_guard
    def switch_tool_editor_table_selection(self, widget=None, data=None):
        new_index = self._treeview_get_active_index(self.tool_editor_table, self.tool_list)
        # hide all controls if no process is defined
        if not new_index is None:
            self.gui.get_object("ToolSettingsControlsBox").show()
            self._put_tool_settings_to_gui(self.tool_list[new_index])
            self.update_tool_table()
        else:
            self.gui.get_object("ToolSettingsControlsBox").hide()
        
    @gui_activity_guard
    def _tool_editor_button_event(self, widget, data, action=None):
        # "toggle" uses two parameters - all other actions have only one
        if action is None:
            action = data
        self._treeview_button_event(self.tool_editor_table, self.tool_list, action, self.update_tool_table)
        override_index = None
        if action == "add":
            # look for the first unused default name
            prefix = "New Tool "
            index = 1
            # loop while the current name is in use
            while [True for process in self.tool_list if process["name"] == "%s%d" % (prefix, index)]:
                index += 1
            new_settings = self._load_tool_settings_from_gui()
            new_settings["name"] = "%s%d" % (prefix, index)
            self.tool_list.append(new_settings)
            self.update_tool_table(self.tool_list.index(new_settings))
            self._put_tool_settings_to_gui(new_settings)

    def update_tool_table(self, new_index=None, skip_model_update=False):
        tool_model = self.gui.get_object("ToolList")
        if new_index is None:
            # keep the old selection - this may return "None" if nothing is selected
            new_index = self._treeview_get_active_index(self.tool_editor_table, self.tool_list)
        if not skip_model_update:
            tool_model.clear()
            counter = 0
            for tool in self.tool_list:
                tool_model.append((counter, counter + 1, tool["name"]))
                counter += 1
            if not new_index is None:
                self._treeview_set_active_index(self.tool_editor_table, new_index)
        # en/disable some buttons
        selection_active = not new_index is None
        self.gui.get_object("ToolEditorDelete").set_sensitive(selection_active)
        self.gui.get_object("ToolEditorMoveUp").set_sensitive(selection_active and new_index > 0)
        self.gui.get_object("ToolEditorMoveDown").set_sensitive(selection_active and new_index < len(self.tool_list) - 1)
        # hide all controls if no process is defined
        if new_index is None:
            self.gui.get_object("ToolSettingsControlsBox").hide()
        else:
            self.gui.get_object("ToolSettingsControlsBox").show()
        # remove any broken tasks and update changed names
        self.update_tool_controls()
        self.update_tasklist_table()

    def change_unit_init(self, widget=None):
        new_unit = self.gui.get_object("unit_control").get_active_text()
        if self._last_unit is None:
            # first initialization
            self._last_unit = new_unit
            return
        if self._last_unit == new_unit:
            # don't show the dialog if the conversion would make no sense
            return
        if self.no_dialog:
            # without the dialog we don't scale anything
            return
        # show a dialog asking for a possible model scaling due to the unit change
        self.unit_change_window.show()

    def change_unit_set_selection(self, widget, state):
        for key in ("UnitChangeModel", "UnitChangeProcesses", "UnitChangeTools"):
            self.gui.get_object(key).set_active(state)

    def change_unit_apply(self, widget=None, data=None, apply_scale=True):
        if self.no_dialog:
            # without the dialog we don't scale anything
            return
        new_unit = self.gui.get_object("unit_control").get_active_text()
        factors = {
                ("mm", "inch"): 1 / 25.4,
                ("inch", "mm"): 25.4,
        }
        conversion = (self._last_unit, new_unit)
        if conversion in factors.keys():
            factor = factors[conversion]
            if apply_scale:
                if self.gui.get_object("UnitChangeModel").get_active():
                    # transform the model if it is selected
                    # keep the original center of the model
                    old_center = self._get_model_center()
                    self.model.scale(factor)
                    self._set_model_center(old_center)
                if self.gui.get_object("UnitChangeProcesses").get_active():
                    # scale the boundaries and keep their center
                    s = self.settings
                    center_x = (s.get("maxx") + s.get("minx")) / 2.0
                    center_y = (s.get("maxy") + s.get("miny")) / 2.0
                    center_z = (s.get("maxz") + s.get("minz")) / 2.0
                    s.set("minx", center_x + (s.get("minx") - center_x) * factor)
                    s.set("maxx", center_x + (s.get("maxx") - center_x) * factor)
                    s.set("miny", center_y + (s.get("miny") - center_y) * factor)
                    s.set("maxy", center_y + (s.get("maxy") - center_y) * factor)
                    s.set("minz", center_z + (s.get("minz") - center_z) * factor)
                    s.set("maxz", center_z + (s.get("maxz") - center_z) * factor)
                    # scale the process settings
                    for process in self.process_list:
                        for key in ("safety_height", "material_allowance", "step_down"):
                            process[key] *= factor
                if self.gui.get_object("UnitChangeTools").get_active():
                    # scale all tool dimensions
                    for tool in self.tool_list:
                        for key in ("tool_radius", "torus_radius", "feedrate"):
                            tool[key] *= factor
        self.unit_change_window.hide()
        # store the current unit (for the next run of this function)
        self._last_unit = new_unit
        # update all labels containing the unit size
        self.update_unit_labels()
        # redraw the model
        self.update_view()

    def update_unit_labels(self, widget=None, data=None):
        # we can't just use the "unit" setting, since we need the plural of "inch"
        if self.settings.get("unit") == "mm":
            base_unit = "mm"
        else:
            base_unit = "inches"
        self.gui.get_object("SpeedLimitsUnitValue").set_text("%s/minute" % base_unit)

    def get_filename_with_suffix(self, filename, type_filter):
        # use the first extension provided by the filter as the default
        if isinstance(type_filter[0], (tuple, list)):
            filter_ext = type_filter[0][1]
        else:
            filter_ext = type_filter[1]
        if isinstance(filter_ext, (list, tuple)):
            filter_ext = filter_ext[0]
        if not filter_ext.startswith("*"):
            # weird filter content
            return filename
        else:
            filter_ext = filter_ext[1:]
        basename = os.path.basename(filename)
        splitted = basename.split(".")
        if len(splitted) > 1:
            # contains at least one dot
            return filename
        else:
            # the filename does not contain a dot
            return filename + filter_ext

    @gui_activity_guard
    def save_model(self, widget=None, filename=None):
        no_dialog = False
        if callable(filename):
            filename = filename()
        if isinstance(filename, basestring):
            no_dialog = True
        else:
            # we open a dialog
            filename = self.get_filename_via_dialog("Save model to ...",
                    mode_load=False, type_filter=FILTER_MODEL)
            if filename:
                self.last_model_file = filename
                self.update_save_actions()
        # no filename given -> exit
        if not filename:
            return
        try:
            fi = open(filename, "w")
            pycam.Exporters.STLExporter.STLExporter(self.model).write(fi)
            fi.close()
        except IOError, err_msg:
            if not no_dialog and not self.no_dialog:
                show_error_dialog(self.window, "Failed to save model file")

    @gui_activity_guard
    def reset_preferences(self, widget=None):
        """ reset all preferences to their default values """
        for key, value in PREFERENCES_DEFAULTS.items():
            self.settings.set(key, value)
        # redraw the model due to changed colors, display items ...
        self.update_view()

    def load_preferences(self):
        """ load all settings that are available in the Preferences window from
        a file in the user's home directory """
        config_filename = pycam.Gui.Settings.get_config_filename()
        if config_filename is None:
            # failed to create the personal preferences directory
            return
        config = ConfigParser.ConfigParser()
        if not config.read(config_filename):
            # no config file was read
            return
        # report any ignored (obsolete) preference keys present in the file
        for item, value in config.items("DEFAULT"):
            if not item in PREFERENCES_DEFAULTS.keys():
                print "Warning: skipping obsolete preference item: %s" % str(item)
        for item in PREFERENCES_DEFAULTS.keys():
            if not config.has_option("DEFAULT", item):
                # a new preference setting is missing in the (old) file
                continue
            value_raw = config.get("DEFAULT", item)
            old_value = self.settings.get(item)
            if isinstance(old_value, basestring):
                # keep strings as they are
                value = value_raw
            else:
                # parse tuples, integers, bools, ...
                value = eval(value_raw)
            self.settings.set(item, value)

    def save_preferences(self):
        """ save all settings that are available in the Preferences window to
        a file in the user's home directory """
        config_filename = pycam.Gui.Settings.get_config_filename()
        if config_filename is None:
            # failed to create the personal preferences directory
            print >>sys.stderr, "Warning: Failed to create a preferences directory your user home directory." 
            return
        config = ConfigParser.ConfigParser()
        for item in PREFERENCES_DEFAULTS.keys():
            config.set("DEFAULT", item, self.settings.get(item))
        try:
            config_file = file(config_filename, "w")
            config.write(config_file)
            config_file.close()
        except IOError, err_msg:
            print >>sys.stderr, "Warning: Failed to write preferences file (%s): %s" % (config_filename, err_msg)

    @gui_activity_guard
    def shift_model(self, widget, use_form_values=True):
        if use_form_values:
            shift_x = self.gui.get_object("shift_x").get_value()
            shift_y = self.gui.get_object("shift_y").get_value()
            shift_z = self.gui.get_object("shift_z").get_value()
        else:
            shift_x = -self.model.minx
            shift_y = -self.model.miny
            shift_z = -self.model.minz
        self.model.shift(shift_x, shift_y, shift_z)
        self.update_view()

    def _get_model_center(self):
        if self.model is None:
            return None
        else:
            return ((self.model.maxx + self.model.minx) / 2,
                    (self.model.maxy + self.model.miny) / 2,
                    (self.model.maxz + self.model.minz) / 2)

    def _set_model_center(self, center):
        new_x, new_y, new_z = center
        old_x, old_y, old_z = self._get_model_center()
        self.model.shift(new_x - old_x, new_y - old_y, new_z - old_z)

    @gui_activity_guard
    def scale_model(self, widget=None, percent=None):
        if percent is None:
            percent = self.gui.get_object("ScalePercent").get_value()
        factor = percent / 100.0
        if (factor <= 0) or (factor == 1):
            return
        old_center = self._get_model_center()
        self.model.scale(factor)
        self._set_model_center(old_center)
        self.update_view()

    @gui_activity_guard
    def switch_scale_axis(self, widget=None):
        if self.model is None:
            return
        index = self.gui.get_object("ScaleDimensionAxis").get_active()
        if index == 0:
            # x axis
            value = self.model.maxx - self.model.minx
        elif index == 1:
            # y axis
            value = self.model.maxy - self.model.miny
        elif index == 2:
            # z axis
            value = self.model.maxz - self.model.minz
        else:
            return
        self.gui.get_object("ScaleDimensionValue").set_value(value)

    @gui_activity_guard
    def scale_model_axis_fit(self, widget):
        proportionally = self.gui.get_object("ScaleDimensionsProportionally").get_active()
        value = self.gui.get_object("ScaleDimensionValue").get_value()
        index = self.gui.get_object("ScaleDimensionAxis").get_active()
        axes = "xyz"
        axis_suffix = axes[index]
        factor = value / (getattr(self.model, "max" + axis_suffix) - getattr(self.model, "min" + axis_suffix))
        # store the original center of the model
        old_center = self._get_model_center()
        if proportionally:
            self.model.scale(factor)
        else:
            factor_x, factor_y, factor_z = (1, 1, 1)
            if index == 0:
                factor_x = factor
            elif index == 1:
                factor_y = factor
            elif index == 2:
                factor_z = factor
            else:
                return
            self.model.scale(factor_x, factor_y, factor_z)
        # move the model to its previous center
        self._set_model_center(old_center)
        self.update_view()

    @gui_activity_guard
    def minimize_bounds(self, widget, data=None):
        # be careful: this depends on equal names of "settings" keys and "model" variables
        for limit in ["minx", "miny", "minz", "maxx", "maxy", "maxz"]:
            self.settings.set(limit, getattr(self.model, limit))
        self.update_view()

    @gui_activity_guard
    def reset_bounds(self, widget=None, data=None):
        xwidth = self.model.maxx - self.model.minx
        ywidth = self.model.maxy - self.model.miny
        zwidth = self.model.maxz - self.model.minz
        self.settings.set("minx", self.model.minx - 0.1 * xwidth)
        self.settings.set("miny", self.model.miny - 0.1 * ywidth)
        # don't go below ground
        self.settings.set("minz", self.model.minz)
        self.settings.set("maxx", self.model.maxx + 0.1 * xwidth)
        self.settings.set("maxy", self.model.maxy + 0.1 * ywidth)
        self.settings.set("maxz", self.model.maxz + 0.1 * zwidth)
        self.update_view()

    def destroy(self, widget=None, data=None):
        self.update_view()
        # check if there is a running process
        # BEWARE: this is useless without threading - but we keep it for now
        if self._progress_running:
            self.cancel_progress()
            # wait steps
            delay = 0.5
            # timeout in seconds
            timeout = 5
            # wait until if is finished
            while self._progress_running and (timeout > 0):
                time.sleep(delay)
                timeout -= delay
        gtk.main_quit()
        self.quit()

    def quit(self):
        self.save_preferences()

    def open(self, filename):
        """ This function is used by the commandline handler """
        self.last_model_file = filename
        self.load_model_file(filename=filename)
        self.update_save_actions()

    def append_to_queue(self, func, *args, **kwargs):
        # check if gui is currently active
        if self.gui_is_active:
            # queue the function call
            self._batch_queue.append((func, args, kwargs))
        else:
            # call the function right now
            func(*args, **kwargs)

    @gui_activity_guard
    def load_model_file(self, widget=None, filename=None):
        if callable(filename):
            filename = filename()
        if not filename:
            filename = self.get_filename_via_dialog("Loading model ...",
                    mode_load=True, type_filter=FILTER_MODEL)
            if filename:
                self.last_model_file = filename
                self.update_save_actions()
        if filename:
            file_type, importer = pycam.Importers.detect_file_type(filename)
            if file_type and callable(importer):
                self.load_model(importer(filename))
            else:
                show_error_dialog(self.window, "Failed to detect filetype!")

    @gui_activity_guard
    def export_emc_tools(self, widget=None, filename=None):
        if callable(filename):
            filename = filename()
        if not filename:
            filename = self.get_filename_via_dialog("Exporting EMC tool definition ...",
                    mode_load=False, type_filter=FILTER_EMC_TOOL)
        if filename:
            export = pycam.Exporters.EMCToolExporter.EMCToolExporter(self.tool_list)
            text = export.get_tool_definition_string()
            try:
                out = file(filename, "w")
                out.write(text)
                out.close()
            except IOError, err_msg:
                if not no_dialog and not self.no_dialog:
                    show_error_dialog(self.window, "Failed to save EMC tool file")

    def open_task_settings_file(self, filename):
        """ This function is used by the commandline handler """
        self.last_task_settings_file = filename
        self.load_task_settings_file(filename=filename)
        self.update_save_actions()

    @gui_activity_guard
    def load_task_settings_file(self, widget=None, filename=None):
        if callable(filename):
            filename = filename()
        if not filename:
            filename = self.get_filename_via_dialog("Loading settings ...",
                    mode_load=True, type_filter=FILTER_CONFIG)
            if filename:
                self.last_task_settings_file = filename
                self.update_save_actions()
        if filename:
            self.load_task_settings(filename)

    def load_model(self, model):
        # load the new model only if the import worked
        if not model is None:
            self.model = model
            # place the "safe height" clearly above the model's peak
            self.settings.set("safety_height", (2 * self.model.maxz - self.model.minz))
            # do some initialization
            self.append_to_queue(self.reset_bounds)
            self.append_to_queue(self.update_all_controls)
            self.append_to_queue(self.toggle_3d_view, value=True)
            self.append_to_queue(self.update_view)

    def load_task_settings(self, filename=None):
        settings = pycam.Gui.Settings.ProcessSettings()
        if not filename is None:
            settings.load_file(filename)
        self.tool_list = settings.get_tools()
        self.process_list = settings.get_processes()
        self.task_list = settings.get_tasks()
        self.update_tool_table()
        self.update_process_table()
        self.update_tasklist_table()

    def _load_process_settings_from_gui(self, settings=None):
        if settings is None:
            settings = {}
        settings["name"] = self.gui.get_object("ProcessSettingName").get_text()
        # path generator
        def get_path_generator():
            for name in ("DropCutter", "PushCutter"):
                if self.gui.get_object(name).get_active():
                    return name
        settings["path_generator"] = get_path_generator()
        # path direction
        def get_path_direction():
            for obj, value in (("PathDirectionX", "x"), ("PathDirectionY", "y"), ("PathDirectionXY", "xy")):
                if self.gui.get_object(obj).get_active():
                    return value
        settings["path_direction"] = get_path_direction()
        def get_path_postprocessor():
            for name in ("PathAccumulator", "SimpleCutter", "ZigZagCutter", "PolygonCutter", "ContourCutter"):
                if self.gui.get_object(name).get_active():
                    return name
        settings["path_postprocessor"] = get_path_postprocessor()
        for objname, key in (("SafetyHeightControl", "safety_height"),
                ("OverlapPercentControl", "overlap_percent"),
                ("MaterialAllowanceControl", "material_allowance"),
                ("MaxStepDownControl", "step_down")):
            settings[key] = self.gui.get_object(objname).get_value()
        return settings

    def _put_process_settings_to_gui(self, settings):
        self.gui.get_object("ProcessSettingName").set_text(settings["name"])
        def set_path_generator(value):
            self.gui.get_object(value).set_active(True)
        set_path_generator(settings["path_generator"])
        # path direction
        def set_path_direction(input):
            for obj, value in (("PathDirectionX", "x"), ("PathDirectionY", "y"), ("PathDirectionXY", "xy")):
                if value == input:
                    self.gui.get_object(obj).set_active(True)
                    return
        set_path_direction(settings["path_direction"])
        # path postprocessor
        def set_path_postprocessor(value):
            self.gui.get_object(value).set_active(True)
        set_path_postprocessor(settings["path_postprocessor"])
        for objname, key in (("SafetyHeightControl", "safety_height"),
                ("OverlapPercentControl", "overlap_percent"),
                ("MaterialAllowanceControl", "material_allowance"),
                ("MaxStepDownControl", "step_down")):
            self.gui.get_object(objname).set_value(settings[key])

    @gui_activity_guard
    def handle_process_settings_change(self, widget=None, data=None):
        current_index = self._treeview_get_active_index(self.process_editor_table, self.process_list)
        if not current_index is None:
            self._load_process_settings_from_gui(self.process_list[current_index])
            self.update_process_table()

    def update_process_table(self, new_index=None, skip_model_update=False):
        # reset the model data and the selection
        if new_index is None:
            # keep the old selection - this may return "None" if nothing is selected
            new_index = self._treeview_get_active_index(self.process_editor_table, self.process_list)
        if not skip_model_update:
            # update the TreeModel data
            model = self.gui.get_object("ProcessList")
            model.clear()
            # columns: index, description
            for index in range(len(self.process_list)):
                process = self.process_list[index]
                items = (index, process["name"])
                model.append(items)
            if not new_index is None:
                self._treeview_set_active_index(self.process_editor_table, new_index)
        # enable/disable the modification buttons
        self.gui.get_object("ProcessListMoveUp").set_sensitive((not new_index is None) and (new_index > 0))
        self.gui.get_object("ProcessListDelete").set_sensitive(not new_index is None)
        self.gui.get_object("ProcessListMoveDown").set_sensitive((not new_index is None) and (new_index + 1 < len(self.process_list)))
        # hide all controls if no process is defined
        if new_index is None:
            self.gui.get_object("ProcessSettingsControlsBox").hide()
        else:
            self.gui.get_object("ProcessSettingsControlsBox").show()
        # remove any broken tasks and update changed names
        self.update_tasklist_table()

    @gui_activity_guard
    def switch_process_table_selection(self, widget=None, data=None):
        new_index = self._treeview_get_active_index(self.process_editor_table, self.process_list)
        if not new_index is None:
            self.gui.get_object("ProcessSettingsControlsBox").show()
            self._put_process_settings_to_gui(self.process_list[new_index])
            self.update_process_table()
        else:
            self.gui.get_object("ProcessSettingsControlsBox").hide()
        
    @gui_activity_guard
    def handle_process_table_event(self, widget, data, action=None):
        # "toggle" uses two parameters - all other actions have only one
        if action is None:
            action = data
        self._treeview_button_event(self.process_editor_table, self.process_list, action, self.update_process_table)
        # do some post-processing ...
        if action == "add":
            # look for the first unused default name
            prefix = "New Process "
            index = 1
            # loop while the current name is in use
            while [True for process in self.process_list if process["name"] == "%s%d" % (prefix, index)]:
                index += 1
            new_settings = self._load_process_settings_from_gui()
            new_settings["name"] = "%s%d" % (prefix, index)
            self.process_list.append(new_settings)
            self.update_process_table(self.process_list.index(new_settings))
            self._put_process_settings_to_gui(new_settings)

    @gui_activity_guard
    def toolpath_table_event(self, widget, data, action=None):
        # "toggle" uses two parameters - all other actions have only one
        if action is None:
            action = data
        if action == "toggle_visibility":
            # get the id of the currently selected toolpath
            try:
                path = int(data)
            except ValueError:
                path = None
            if (not path is None) and (path < len(self.toolpath)):
                self.toolpath[path].visible = not self.toolpath[path].visible
                # hide/show toolpaths according to the new setting
                self.update_view()
        elif action == "simulate":
            index = self._treeview_get_active_index(self.toolpath_table, self.toolpath)
            if not index is None:
                self.show_toolpath_simulation(self.toolpath[index])
        self._treeview_button_event(self.toolpath_table, self.toolpath, action, self.update_toolpath_table)
        # do some post-processing ...
        if action == "delete":
            # hide the deleted toolpath immediately
            self.update_view()

    def update_toolpath_table(self, new_index=None, skip_model_update=False):
        def get_time_string(minutes):
            if minutes > 180:
                return "%d hours" % int(round(minutes / 60))
            elif minutes > 3:
                return "%d minutes" % int(round(minutes))
            else:
                return "%d seconds" % int(round(minutes * 60))
        # show or hide the "toolpath" tab
        toolpath_tab = self.gui.get_object("ToolPathTab")
        if not self.toolpath:
            toolpath_tab.hide()
        else:
            self.gui.get_object("ToolPathTabLabel").set_text(
                    "%s (%d)" % (self._original_toolpath_tab_label, len(self.toolpath)))
            toolpath_tab.show()
        # enable/disable the export menu item
        self.gui.get_object("ExportGCode").set_sensitive(len(self.toolpath) > 0)
        # reset the model data and the selection
        if new_index is None:
            # keep the old selection - this may return "None" if nothing is selected
            new_index = self._treeview_get_active_index(self.toolpath_table, self.toolpath)
        if not skip_model_update:
            # update the TreeModel data
            model = self.gui.get_object("ToolPathListModel")
            model.clear()
            # columns: name, visible, drill_size, drill_id, allowance, speed, feedrate
            for index in range(len(self.toolpath)):
                tp = self.toolpath[index]
                items = (index, tp.name, tp.visible, tp.tool_settings["radius"],
                        tp.tool_id, tp.material_allowance, tp.speed,
                        tp.feedrate, get_time_string(tp.get_machine_time()))
                model.append(items)
            if not new_index is None:
                self._treeview_set_active_index(self.toolpath_table, new_index)
        # enable/disable the modification buttons
        self.gui.get_object("toolpath_up").set_sensitive((not new_index is None) and (new_index > 0))
        self.gui.get_object("toolpath_delete").set_sensitive(not new_index is None)
        self.gui.get_object("toolpath_down").set_sensitive((not new_index is None) and (new_index + 1 < len(self.toolpath)))
        self.gui.get_object("toolpath_simulate").set_sensitive((not new_index is None) and pycam.Physics.ode_physics.is_ode_available())

    @gui_activity_guard
    def save_task_settings_file(self, widget=None, filename=None):
        no_dialog = False
        if callable(filename):
            filename = filename()
        if isinstance(filename, basestring):
            no_dialog = True
        else:
            # we open a dialog
            filename = self.get_filename_via_dialog("Save settings to ...",
                    mode_load=False, type_filter=FILTER_CONFIG)
            if filename:
                self.last_task_settings_file = filename
                self.update_save_actions()
        # no filename given -> exit
        if not filename:
            return
        settings = pycam.Gui.Settings.ProcessSettings()
        if not settings.write_to_file(filename, self.tool_list, self.process_list, self.task_list) and not no_dialog and not self.no_dialog:
            show_error_dialog(self.window, "Failed to save settings file")

    def toggle_progress_bar(self, status):
        if status:
            self.task_pane.set_sensitive(False)
            self.update_progress_bar("", 0)
            self.progress_widget.show()
        else:
            self.progress_widget.hide()
            self.task_pane.set_sensitive(True)

    def update_progress_bar(self, text=None, percent=None):
        if not percent is None:
            percent = min(max(percent, 0.0), 100.0)
            self.progress_bar.set_fraction(percent/100.0)
        if not text is None:
            self.progress_bar.set_text(text)

    def cancel_progress(self, widget=None):
        self._progress_cancel_requested = True

    def finish_toolpath_simulation(self, widget=None):
        # hide the simulation tab
        self.gui.get_object("SimulationTab").hide()
        # enable all other tabs again
        for objname in ("ModelTab", "ModelTabLabel", "TasksTab", "TasksTabLabel", "ToolPathTab", "ToolPathTabLabel"):
            self.gui.get_object(objname).set_sensitive(True)
        self.settings.set("simulate_object", None)
        self.settings.set("show_simulation", False)
        self.update_view()

    @progress_activity_guard
    def update_toolpath_simulation(self, widget=None, toolpath=None):
        import pycam.Simulation.ODEBlocks
        # get the currently selected toolpath, if none is give
        if toolpath is None:
            toolpath_index = self._treeview_get_active_index(self.toolpath_table, self.toolpath)
            if toolpath_index is None:
                return
            else:
                toolpath = self.toolpath[toolpath_index]
        paths = toolpath.get_path()
        # set the current cutter
        self.cutter = pycam.Cutters.get_tool_from_settings(toolpath.tool_settings)
        # calculate steps
        detail_level = self.gui.get_object("SimulationDetailsValue").get_value()
        grid_size = 100 * pow(2, detail_level - 1)
        proportion = (self.settings.get("maxx") - self.settings.get("minx")) \
                / (self.settings.get("maxy") - self.settings.get("miny"))
        x_steps = int(math.sqrt(grid_size) * proportion)
        y_steps = int(math.sqrt(grid_size) / proportion)
        simulation_backend = pycam.Simulation.ODEBlocks.ODEBlocks(
                toolpath.tool_settings, toolpath.bounding_box,
                x_steps=x_steps, y_steps=y_steps)
        self.settings.set("simulation_object", simulation_backend)
        # disable the simulation widget (avoids confusion regarding "cancel")
        if not widget is None:
            self.gui.get_object("SimulationTab").set_sensitive(False)
        # update the view
        self.update_view()
        # calculate the simulation and show it simulteneously
        for path_index, path in enumerate(paths):
            progress_text = "Simulating path %d/%d" % (path_index, len(paths))
            progress_value_percent = 100.0 * path_index / len(paths)
            self.update_progress_bar(progress_text, progress_value_percent)
            for index in range(len(path.points)):
                self.cutter.moveto(path.points[index])
                if index != 0:
                    start = path.points[index - 1]
                    end = path.points[index]
                    if start != end:
                        simulation_backend.process_cutter_movement(start, end)
                self.update_view()
                # update the GUI
                while gtk.events_pending():
                    gtk.main_iteration()
                # break the loop if someone clicked the "cancel" button
                if self._progress_cancel_requested:
                    break
            if self._progress_cancel_requested:
                break
        # enable the simulation widget again (if we were started from the GUI)
        if not widget is None:
            self.gui.get_object("SimulationTab").set_sensitive(True)

    def show_toolpath_simulation(self, toolpath):
        # disable the main controls
        for objname in ("ModelTab", "ModelTabLabel", "TasksTab", "TasksTabLabel", "ToolPathTab", "ToolPathTabLabel"):
            self.gui.get_object(objname).set_sensitive(False)
        # show the simulation controls
        self.gui.get_object("SimulationTab").show()
        # switch to the simulation tab
        self.gui.get_object("MainTabs").set_current_page(3)
        # start the simulation
        self.settings.set("show_simulation", True)
        self.update_toolpath_simulation(toolpath=toolpath)
        # hide the controls immediately, if the simulation was cancelled
        if self._progress_cancel_requested:
            self.finish_toolpath_simulation()

    @progress_activity_guard
    def generate_toolpath(self, tool_settings, process_settings):
        start_time = time.time()
        self.update_progress_bar("Preparing toolpath generation")
        parent = self
        class UpdateView:
            def __init__(self, func, max_fps=1):
                self.last_update = time.time()
                self.max_fps = max_fps
                self.func = func
            def update(self, text=None, percent=None, tool_position=None):
                if not tool_position is None:
                    parent.cutter.moveto(tool_position)
                parent.update_progress_bar(text, percent)
                if (time.time() - self.last_update) > 1.0/self.max_fps:
                    self.last_update = time.time()
                    if self.func:
                        self.func()
                # update the GUI
                while gtk.events_pending():
                    gtk.main_iteration()
                # break the loop if someone clicked the "cancel" button
                return parent._progress_cancel_requested
        if self.settings.get("show_drill_progress"):
            callback = self.update_view
        else:
            callback = None
        draw_callback = UpdateView(callback,
                max_fps=self.settings.get("drill_progress_max_fps")).update

        self.update_progress_bar("Generating collision model")

        if self.settings.get("enable_ode"):
            calculation_backend = "ODE"
        else:
            calculation_backend = None

        # this offset allows to cut a model with a minimal boundary box correctly
        offset = tool_settings["tool_radius"] / 2.0
        # check the configured direction of the offset (boundary mode)
        if self.settings.get("boundary_mode") == self.BOUNDARY_MODES["inside"]:
            # use the negative offset to stay inside the boundaries
            offset *= -1
        elif self.settings.get("boundary_mode") == self.BOUNDARY_MODES["along"]:
            # don't use any offset
            offset = 0
        elif self.settings.get("boundary_mode") == self.BOUNDARY_MODES["around"]:
            # just use the positive offset - no change required
            pass
        else:
            # this should never happen
            print >>sys.stderr, "Assertion failed: invalid boundary_mode (%s)" % str(self.settings.get("boundary_mode"))

        minx = float(self.settings.get("minx"))-offset
        maxx = float(self.settings.get("maxx"))+offset
        miny = float(self.settings.get("miny"))-offset
        maxy = float(self.settings.get("maxy"))+offset
        minz = float(self.settings.get("minz"))
        maxz = float(self.settings.get("maxz"))
        bounds = (minx, maxx, miny, maxy, minz, maxz)

        # check if the boundary limits are valid
        if (minx > maxx) or (miny > maxy) or (minz > maxz):
            # don't generate a toolpath if the area is too small (e.g. due to the tool size)
            if not self.no_dialog:
                show_error_dialog(self.window, "Processing boundaries are too small for this tool size.")
            return True

        self.update_progress_bar("Starting the toolpath generation")
        # put the tool settings together
        tool_dict = {"shape": tool_settings["shape"],
                "radius": tool_settings["tool_radius"],
                "torus_radius": tool_settings["torus_radius"],
        }
        self.cutter = pycam.Cutters.get_tool_from_settings(tool_dict)
        # get the support grid options
        if self.gui.get_object("SupportGridEnable").get_active():
            support_grid_distance = self.settings.get("support_grid_distance")
            support_grid_thickness = self.settings.get("support_grid_thickness")
        else:
            support_grid_distance = None
            support_grid_thickness = None
        # run the toolpath generation
        toolpath = pycam.Toolpath.Generator.generate_toolpath(self.model,
                tool_dict, bounds=bounds,
                direction=process_settings["path_direction"],
                path_generator=process_settings["path_generator"],
                path_postprocessor=process_settings["path_postprocessor"],
                material_allowance=process_settings["material_allowance"],
                safety_height=process_settings["safety_height"],
                overlap=process_settings["overlap_percent"] / 100.0,
                step_down=process_settings["step_down"],
                support_grid_distance=support_grid_distance,
                support_grid_thickness=support_grid_thickness,
                calculation_backend=calculation_backend, callback=draw_callback)

        print "Time elapsed: %f" % (time.time() - start_time)

        if isinstance(toolpath, basestring):
            # an error occoured - "toolpath" contains the error message
            message = "Failed to generate toolpath: %s" % toolpath
            if not self.no_dialog:
                show_error_dialog(self.window, message)
            else:
                print >>sys.stderr, message
            # we were not successful (similar to a "cancel" request)
            return False
        else:
            # hide the previous toolpath if it is the only visible one (automatic mode)
            if (len([True for path in self.toolpath if path.visible]) == 1) \
                    and self.toolpath[-1].visible:
                self.toolpath[-1].visible = False
            # add the new toolpath
            description = "%s / %s" % (tool_settings["name"], process_settings["name"])
            # the tool id numbering should start with 1 instead of zero
            tool_id = self.tool_list.index(tool_settings) + 1
            self.toolpath.add_toolpath(toolpath,
                    description, tool_dict, tool_id,
                    tool_settings["speed"],
                    tool_settings["feedrate"],
                    process_settings["material_allowance"],
                    process_settings["safety_height"],
                    self.settings.get("unit"),
                    minx, miny, process_settings["safety_height"],
                    bounds)
            self.update_toolpath_table()
            self.update_view()
            # return "False" if the action was cancelled
            return not self._progress_cancel_requested

    def get_filename_via_dialog(self, title, mode_load=False, type_filter=None):
        # we open a dialog
        if mode_load:
            dialog = gtk.FileChooserDialog(title=title,
                    parent=self.window, action=gtk.FILE_CHOOSER_ACTION_OPEN,
                    buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                        gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        else:
            dialog = gtk.FileChooserDialog(title=title,
                    parent=self.window, action=gtk.FILE_CHOOSER_ACTION_SAVE,
                    buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                        gtk.STOCK_SAVE, gtk.RESPONSE_OK))
        # add filter for files
        if type_filter:
            if not isinstance(type_filter[0], (list, tuple)):
                type_filter = [type_filter]
            for one_filter in type_filter:
                file_filter = gtk.FileFilter()
                file_filter.set_name(one_filter[0])
                file_extensions = one_filter[1]
                if not isinstance(file_extensions, (list, tuple)):
                    file_extensions = [file_extensions]
                for ext in file_extensions:
                    file_filter.add_pattern(ext)
                dialog.add_filter(file_filter)
        # add filter for all files
        filter = gtk.FileFilter()
        filter.set_name("All files")
        filter.add_pattern("*")
        dialog.add_filter(filter)
        done = False
        while not done:
            dialog.set_filter(dialog.list_filters()[0])
            response = dialog.run()
            filename = dialog.get_filename()
            dialog.hide()
            if response != gtk.RESPONSE_OK:
                dialog.destroy()
                return None
            if not mode_load and filename:
                # check if we want to add a default suffix
                filename = self.get_filename_with_suffix(filename, type_filter)
            if not mode_load and os.path.exists(filename):
                overwrite_window = gtk.MessageDialog(self.window, type=gtk.MESSAGE_WARNING,
                        buttons=gtk.BUTTONS_YES_NO,
                        message_format="This file exists. Do you want to overwrite it?")
                overwrite_window.set_title("Confirm overwriting existing file")
                response = overwrite_window.run()
                overwrite_window.destroy()
                done = (response == gtk.RESPONSE_YES)
            elif mode_load and not os.path.isfile(filename):
                not_found_window = gtk.MessageDialog(self.window, type=gtk.MESSAGE_ERROR,
                        buttons=gtk.BUTTONS_OK,
                        message_format="This file does not exist. Please choose a different filename.")
                not_found_window.set_title("Invalid filename selected")
                response = not_found_window.run()
                not_found_window.destroy()
                done = False
            else:
                done = True
        dialog.destroy()
        # add the file to the list of recently used ones
        if filename:
            try:
                recent = gtk.RecentManager()
                recent.add_item("file://%s" % str(filename))
            except AttributeError:
                # GTK 2.12.1 seems to have problems with "RecentManager" on Windows.
                # Sadly this is the version, that is shipped with the "appunti" GTK
                # packages for Windows (April 2010).
                pass
        return filename

    def setOutputFilename(self, filename):
        self.last_toolpath_file = filename

    @gui_activity_guard
    def save_toolpath(self, widget=None, data=None):
        if not self.toolpath:
            return
        if callable(widget):
            widget = widget()
        if isinstance(widget, basestring):
            filename = widget
            no_dialog = True
        elif self.no_dialog:
            filename = self.last_toolpath_file
            no_dialog = True
        else:
            # we open a dialog
            filename = self.get_filename_via_dialog("Save toolpath to ...",
                    mode_load=False, type_filter=FILTER_GCODE)
            if filename:
                self.last_toolpath_file = filename
                self.update_save_actions()
            no_dialog = False
        # no filename given -> exit
        if not filename:
            return
        try:
            destination = open(filename, "w")
            index = 0
            for index in range(len(self.toolpath)):
                tp = self.toolpath[index]
                # check if this is the last loop iteration
                # only the last toolpath of the list should contain the "M2"
                # ("end program") G-code
                if index + 1 == len(self.toolpath):
                    is_last_loop = True
                else:
                    is_last_loop = False
                pycam.Exporters.SimpleGCodeExporter.ExportPathList(destination,
                        tp.toolpath, tp.unit,
                        tp.start_x, tp.start_y, tp.start_z,
                        tp.feedrate, tp.speed, safety_height=tp.safety_height, tool_id=tp.tool_id,
                        finish_program=is_last_loop,
                        max_skip_safety_distance=2*tp.tool_settings["radius"])
            destination.close()
            if self.no_dialog:
                print "GCode file successfully written: %s" % str(filename)
        except IOError, err_msg:
            if not no_dialog and not self.no_dialog:
                show_error_dialog(self.window, "Failed to save toolpath file")

    def mainloop(self):
        # run the mainloop only if a GUI was requested
        if not self.no_dialog:
            try:
                gtk.main()
            except KeyboardInterrupt:
                self.quit()

if __name__ == "__main__":
    gui = ProjectGui()
    if len(sys.argv) > 1:
        gui.open(sys.argv[1])
    gui.mainloop()

