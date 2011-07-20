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


import os
import sys
import re
import math
import time
import datetime
import gtk
import gobject
import webbrowser
import ConfigParser
import StringIO
import pickle
import logging

import pycam.Exporters.EMCToolExporter
import pycam.Gui.Settings
import pycam.Cutters
import pycam.Toolpath.Generator
import pycam.Toolpath
import pycam.Importers.CXFImporter
import pycam.Importers.TestModel
import pycam.Importers
from pycam.Geometry.Point import Point, Vector
from pycam.Geometry.Plane import Plane
import pycam.Geometry.Path
import pycam.Utils.log
from pycam.Utils.locations import get_data_file_location, \
        get_ui_file_location, get_external_program_location, \
        get_all_program_locations
import pycam.Utils
from pycam.Geometry.utils import sqrt
import pycam.Geometry.Model
from pycam.Toolpath import Bounds
import pycam.Plugins
from pycam import VERSION
import pycam.Physics.ode_physics

GTKBUILD_FILE = "pycam-project.ui"
GTKMENU_FILE = "menubar.xml"
GTKRC_FILE_WINDOWS = "gtkrc_windows"

WINDOW_ICON_FILENAMES = ["logo_%dpx.png" % pixels for pixels in (16, 32, 48, 64, 128)]

HELP_WIKI_URL = "http://sourceforge.net/apps/mediawiki/pycam/index.php?title=%s"

FILTER_GCODE = (("GCode files", ("*.ngc", "*.nc", "*.gc", "*.gcode")),)
FILTER_MODEL = (("All supported model filetypes",
                ("*.stl", "*.dxf", "*.svg", "*.eps", "*.ps")),
        ("STL models", "*.stl"), ("DXF contours", "*.dxf"),
        ("SVG contours", "*.svg"), ("PS contours", ("*.eps", "*.ps")))
FILTER_CONFIG = (("Config files", "*.conf"),)
FILTER_EMC_TOOL = (("EMC tool files", "*.tbl"),)

PREFERENCES_DEFAULTS = {
        "enable_ode": False,
        "unit": "mm",
        "default_task_settings_file": "",
        "show_model": True,
        "show_support_grid": True,
        "show_axes": True,
        "show_dimensions": True,
        "show_bounding_box": True,
        "show_toolpath": True,
        "show_drill": False,
        "show_directions": False,
        "color_background": (0.0, 0.0, 0.0, 1.0),
        "color_model": (0.5, 0.5, 1.0, 1.0),
        "color_support_grid": (0.8, 0.8, 0.3, 1.0),
        "color_bounding_box": (0.3, 0.3, 0.3, 1.0),
        "color_cutter": (1.0, 0.2, 0.2, 1.0),
        "color_toolpath_cut": (1.0, 0.5, 0.5, 1.0),
        "color_toolpath_return": (0.9, 1.0, 0.1, 0.4),
        "color_material": (1.0, 0.5, 0.0, 1.0),
        "view_light": True,
        "view_shadow": True,
        "view_polygon": True,
        "view_perspective": True,
        "drill_progress_max_fps": 2,
        "gcode_safety_height": 25.0,
        "gcode_minimum_step_x": 0.0001,
        "gcode_minimum_step_y": 0.0001,
        "gcode_minimum_step_z": 0.0001,
        "gcode_path_mode": 0,
        "gcode_motion_tolerance": 0,
        "gcode_naive_tolerance": 0,
        "gcode_start_stop_spindle": True,
        "gcode_filename_extension": "",
        "gcode_spindle_delay": 3,
        "external_program_inkscape": "",
        "external_program_pstoedit": "",
        "touch_off_on_startup": False,
        "touch_off_on_tool_change": False,
        "touch_off_position_type": "absolute",
        "touch_off_position_x": 0.0,
        "touch_off_position_y": 0.0,
        "touch_off_position_z": 0.0,
        "touch_off_rapid_move": 0.0,
        "touch_off_slow_move": 1.0,
        "touch_off_slow_feedrate": 20,
        "touch_off_height": 0.0,
        "touch_off_pause_execution": False,
}
""" the listed items will be loaded/saved via the preferences file in the
user's home directory on startup/shutdown"""

MAX_UNDO_STATES = 10
FILENAME_DRAG_TARGETS = ("text/uri-list", "text-plain")

# floating point color values are only available since gtk 2.16
GTK_COLOR_MAX = 65535.0

log = pycam.Utils.log.get_logger()

def get_filters_from_list(filter_list):
    result = []
    for one_filter in filter_list:
        current_filter = gtk.FileFilter()
        current_filter.set_name(one_filter[0])
        file_extensions = one_filter[1]
        if not isinstance(file_extensions, (list, tuple)):
            file_extensions = [file_extensions]
        for ext in file_extensions:
            current_filter.add_pattern(ext)
        result.append(current_filter)
    return result

def get_icons_pixbuffers():
    result = []
    for icon_filename in WINDOW_ICON_FILENAMES:
        abs_filename = get_ui_file_location(icon_filename, silent=True)
        if abs_filename:
            try:
                result.append(gtk.gdk.pixbuf_new_from_file(abs_filename))
            except gobject.GError, err_msg:
                # ignore icons that are not found
                log.debug("Failed to process window icon (%s): %s" \
                        % (abs_filename, err_msg))
        else:
            log.debug("Failed to locate window icon: %s" % icon_filename)
    return result


UI_FUNC_INDEX, UI_WIDGET_INDEX = range(2)
WIDGET_NAME_INDEX, WIDGET_OBJ_INDEX, WIDGET_WEIGHT_INDEX, WIDGET_ARGS_INDEX = \
        range(4)
HANDLER_FUNC_INDEX, HANDLER_ARG_INDEX = range(2)
EVENT_HANDLER_INDEX, EVENT_BLOCKER_INDEX = range(2)


class EventCore(pycam.Gui.Settings.Settings):

    def __init__(self):
        super(EventCore, self).__init__()
        self.event_handlers = {}
        self.ui_sections = {}

    def register_event(self, event, func, *args):
        if not event in self.event_handlers:
            assert EVENT_HANDLER_INDEX == 0
            assert EVENT_BLOCKER_INDEX == 1
            self.event_handlers[event] = [[], 0]
        assert HANDLER_FUNC_INDEX == 0
        assert HANDLER_ARG_INDEX == 1
        self.event_handlers[event][EVENT_HANDLER_INDEX].append((func, args))

    def unregister_event(self, event, func):
        if event in self.event_handlers:
            removal_list = []
            for index, item in enumerate(self.event_handlers[event][EVENT_HANDLER_INDEX]):
                if func == item[HANDLER_FUNC_INDEX]:
                    removal_list.append(index)
            removal_list.reverse()
            for index in removal_list:
                self.event_handlers[event].pop(index)
        else:
            log.debug("Trying to unregister an unknown event: %s" % event)

    def emit_event(self, event, *args, **kwargs):
        log.debug("Event emitted: %s" % str(event))
        if event in self.event_handlers:
            if self.event_handlers[event][EVENT_BLOCKER_INDEX] != 0:
                return
            self.block_event(event)
            for handler in self.event_handlers[event][EVENT_HANDLER_INDEX]:
                func = handler[HANDLER_FUNC_INDEX]
                data = handler[HANDLER_ARG_INDEX]
                # prevent infinite recursion
                func(*(data + args), **kwargs)
            self.unblock_event(event)
        else:
            log.debug("No events registered for event '%s'" % str(event))

    def block_event(self, event):
        if event in self.event_handlers:
            self.event_handlers[event][EVENT_BLOCKER_INDEX] += 1
        else:
            log.debug("Trying to block an unknown event: %s" % str(event))

    def unblock_event(self, event):
        if event in self.event_handlers:
            if self.event_handlers[event][EVENT_BLOCKER_INDEX] > 0:
                self.event_handlers[event][EVENT_BLOCKER_INDEX] -= 1
            else:
                log.debug("Trying to unblock non-blocked event '%s'" % \
                        str(event))
        else:
            log.debug("Trying to unblock an unknown event: %s" % str(event))

    def register_ui_section(self, section, add_action, clear_action):
        if not section in self.ui_sections:
            self.ui_sections[section] = [None, None]
            self.ui_sections[section][UI_WIDGET_INDEX] = []
        self.ui_sections[section][UI_FUNC_INDEX] = (add_action, clear_action)
        self._rebuild_ui_section(section)

    def _rebuild_ui_section(self, section):
        if section in self.ui_sections:
            ui_section = self.ui_sections[section]
            if ui_section[UI_FUNC_INDEX]:
                add_func, clear_func = ui_section[UI_FUNC_INDEX]
                ui_section[UI_WIDGET_INDEX].sort(
                        key=lambda x: x[WIDGET_WEIGHT_INDEX])
                clear_func()
                for item in ui_section[UI_WIDGET_INDEX]:
                    if item[WIDGET_ARGS_INDEX]:
                        args = item[WIDGET_ARGS_INDEX]
                    else:
                        args = {}
                    add_func(item[WIDGET_OBJ_INDEX], item[WIDGET_NAME_INDEX],
                            **args)
        else:
            log.debug("Failed to rebuild unknown ui section: %s" % str(section))

    def register_ui(self, section, name, widget, weight=0, args_dict=None):
        if not section in self.ui_sections:
            self.ui_sections[section] = [None, None]
            self.ui_sections[section][UI_WIDGET_INDEX] = []
        assert WIDGET_NAME_INDEX == 0
        assert WIDGET_OBJ_INDEX == 1
        assert WIDGET_WEIGHT_INDEX == 2
        assert WIDGET_ARGS_INDEX == 3
        self.ui_sections[section][UI_WIDGET_INDEX].append((name, widget,
                weight, args_dict))
        self._rebuild_ui_section(section)

    def unregister_ui(self, section, widget):
        if (section in self.ui_sections) or (None in self.ui_sections):
            if not section in self.ui_sections:
                section = None
            ui_section = self.ui_sections[section]
            removal_list = []
            for index, item in enumerate(ui_section[UI_WIDGET_INDEX]):
                if item[WIDGET_OBJ_INDEX] == widget:
                    removal_list.append(index)
            removal_list.reverse()
            for index in removal_list:
                ui_section[UI_WIDGET_INDEX].pop(index)
        else:
            log.debug("Trying to unregister unknown ui section: %s" % \
                    str(section))


class ProjectGui(object):

    META_DATA_PREFIX = "PYCAM-META-DATA:"

    def __init__(self, no_dialog=False):
        self.settings = EventCore()
        self.gui_is_active = False
        # during initialization any dialog (e.g. "Unit change") is not allowed
        # we set the final value later
        self.no_dialog = True
        self._batch_queue = []
        self._undo_states = []
        self.gui = gtk.Builder()
        gtk_build_file = get_ui_file_location(GTKBUILD_FILE)
        if gtk_build_file is None:
            gtk.main_quit()
        self.gui.add_from_file(gtk_build_file)
        if pycam.Utils.get_platform() == pycam.Utils.PLATFORM_WINDOWS:
            gtkrc_file = get_ui_file_location(GTKRC_FILE_WINDOWS)
            if gtkrc_file:
                gtk.rc_add_default_file(gtkrc_file)
                gtk.rc_reparse_all_for_settings(gtk.settings_get_default(), True)
        self.window = self.gui.get_object("ProjectWindow")
        # show stock items on buttons
        # increase the initial width of the window (due to hidden elements)
        self.window.set_default_size(400, -1)
        # initialize the RecentManager (TODO: check for Windows)
        if False and pycam.Utils.get_platform() == pycam.Utils.PLATFORM_WINDOWS:
            # The pyinstaller binary for Windows fails mysteriously when trying
            # to display the stock item.
            # Error message: Gtk:ERROR:gtkrecentmanager.c:1942:get_icon_fallback: assertion failed: (retval != NULL)
            self.recent_manager = None
        else:
            try:
                self.recent_manager = gtk.recent_manager_get_default()
            except AttributeError:
                # GTK 2.12.1 seems to have problems with "RecentManager" on
                # Windows. Sadly this is the version, that is shipped with the
                # "appunti" GTK packages for Windows (April 2010).
                # see http://www.daa.com.au/pipermail/pygtk/2009-May/017052.html
                self.recent_manager = None
        # file loading
        self.last_dirname = None
        self.last_task_settings_uri = None
        self.last_model_uri = None
        # define callbacks and accelerator keys for the menu actions
        for objname, callback, data, accel_key in (
                ("LoadTaskSettings", self.load_task_settings_file, None, "<Control>t"),
                ("SaveTaskSettings", self.save_task_settings_file, lambda: self.last_task_settings_uri, None),
                ("SaveAsTaskSettings", self.save_task_settings_file, None, None),
                ("OpenModel", self.load_model_file, None, "<Control>o"),
                ("SaveModel", self.save_model, lambda: self.last_model_uri, "<Control>s"),
                ("SaveAsModel", self.save_model, None, "<Control><Shift>s"),
                ("ExportEMCToolDefinition", self.export_emc_tools, None, None),
                ("Quit", self.destroy, None, "<Control>q"),
                ("GeneralSettings", self.toggle_preferences_window, None, "<Control>p"),
                ("UndoButton", self._restore_undo_state, None, "<Control>z"),
                ("HelpUserManual", self.show_help, "User_Manual", "F1"),
                ("HelpIntroduction", self.show_help, "Introduction", None),
                ("HelpSupportedFormats", self.show_help, "SupportedFormats", None),
                ("HelpModelTransformations", self.show_help, "ModelTransformations", None),
                ("HelpToolTypes", self.show_help, "ToolTypes", None),
                ("HelpProcessSettings", self.show_help, "ProcessSettings", None),
                ("HelpBoundsSettings", self.show_help, "BoundsSettings", None),
                ("HelpTaskSetup", self.show_help, "TaskSetup", None),
                ("HelpGCodeExport", self.show_help, "GCodeExport", None),
                ("HelpTouchOff", self.show_help, "TouchOff", None),
                ("HelpSimulation", self.show_help, "Simulation", None),
                ("Help3DView", self.show_help, "3D_View", None),
                ("HelpServerMode", self.show_help, "ServerMode", None),
                ("HelpCommandLine", self.show_help, "CommandlineExamples", None),
                ("HelpHotkeys", self.show_help, "KeyboardShortcuts", None),
                ("ProjectWebsite", self.show_help, "http://pycam.sourceforge.net", None),
                ("DevelopmentBlog", self.show_help, "http://fab.senselab.org/pycam", None),
                ("Forum", self.show_help, "http://sourceforge.net/projects/pycam/forums", None),
                ("BugTracker", self.show_help, "http://sourceforge.net/tracker/?group_id=237831&atid=1104176", None),
                ("FeatureRequest", self.show_help, "http://sourceforge.net/tracker/?group_id=237831&atid=1104179", None)):
            item = self.gui.get_object(objname)
            action = "activate"
            if data is None:
                item.connect(action, callback)
            else:
                item.connect(action, callback, data)
            if accel_key:
                key, mod = gtk.accelerator_parse(accel_key)
                accel_path = "<pycam>/%s" % objname
                item.set_accel_path(accel_path)
                gtk.accel_map_change_entry(accel_path, key, mod, True)
        # LinkButton does not work on Windows: https://bugzilla.gnome.org/show_bug.cgi?id=617874
        if pycam.Utils.get_platform() == pycam.Utils.PLATFORM_WINDOWS:
            def open_url(widget, data=None):
                webbrowser.open(widget.get_uri())
            gtk.link_button_set_uri_hook(open_url)
        # no undo is allowed at the beginning
        self.gui.get_object("UndoButton").set_sensitive(False)
        self.settings.register_event("model-change-before",
                self._store_undo_state)
        self.settings.register_event("model-change-after",
                self.update_save_actions)
        self.settings.register_event("model-selection-changed",
                self.update_save_actions)
        self.settings.register_event("model-change-after",
                lambda: self.settings.emit_event("visual-item-updated"))
        def update_emc_tool_button():
            tool_num = len(self.settings.get("tools"))
            self.gui.get_object("ExportEMCToolDefinition").set_sensitive(tool_num > 0)
        self.settings.register_event("tool-selection-changed", update_emc_tool_button)
        self.settings.set("load_model", self.load_model)
        # set the availability of ODE
        self.enable_ode_control = self.gui.get_object("SettingEnableODE")
        self.settings.add_item("enable_ode", self.enable_ode_control.get_active,
                self.enable_ode_control.set_active)
        self.settings.register_event("parallel-processing-changed",
                self.update_ode_settings)
        # configure drag-n-drop for config files and models
        self.settings.set("configure-drag-drop-func",
                self.configure_drag_and_drop)
        self.settings.get("configure-drag-drop-func")(self.window)
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
        self.about_window.set_version(VERSION)
        self.gui.get_object("About").connect("activate", self.toggle_about_window, True)
        # we assume, that the last child of the window is the "close" button
        # TODO: fix this ugly hack!
        self.gui.get_object("AboutWindowButtons").get_children()[-1].connect("clicked", self.toggle_about_window, False)
        self.about_window.connect("delete-event", self.toggle_about_window, False)
        # menu bar
        uimanager = gtk.UIManager()
        self.settings.set("gtk-uimanager", uimanager)
        self._accel_group = uimanager.get_accel_group()
        self.settings.add_item("gtk-accel-group", lambda: self._accel_group)
        for window in (self.window, self.about_window, self.preferences_window):
            window.add_accel_group(self._accel_group)
        # preferences tab
        preferences_book = self.gui.get_object("PreferencesNotebook")
        def clear_preferences():
            for index in range(preferences_book.get_n_pages()):
                preferences_book.remove_page(0)
        def add_preferences_item(item, name):
            preferences_book.append_page(item, gtk.Label(name))
        self.settings.register_ui_section("preferences",
                add_preferences_item, clear_preferences)
        for obj_name, label, priority in (
                ("GeneralSettingsPrefTab", "General", -50),
                ("GCodePrefTab", "GCode", 10),
                ("DisplayItemsPrefTab", "Display Items", 20),
                ("ColorPrefTab", "Colors", 30),
                ("OpenGLPrefTab", "OpenGL", 40),
                ("ProgramsPrefTab", "Programs", 50)):
            obj = self.gui.get_object(obj_name)
            obj.unparent()
            self.settings.register_ui("preferences", label, obj, priority)
        # general preferences
        general_prefs = self.gui.get_object("GeneralPreferencesBox")
        def clear_general_prefs():
            for item in general_prefs.get_children():
                general_prefs.remove(item)
        def add_general_prefs_item(item, name):
            general_prefs.pack_start(item, expand=False, padding=3)
        self.settings.register_ui_section("preferences_general",
                add_general_prefs_item, clear_general_prefs)
        for obj_name, priority in (("SettingEnableODE", 10),
                ("TaskSettingsDefaultFileBox", 30)):
            obj = self.gui.get_object(obj_name)
            obj.unparent()
            self.settings.register_ui("preferences_general", None,
                    obj, priority)
        # set defaults
        self.cutter = None
        # add some dummies - to be implemented later ...
        self.settings.add_item("cutter", lambda: self.cutter)
        main_tab = self.gui.get_object("MainTabs")
        def clear_main_tab():
            for index in range(main_tab.get_n_pages()):
                main_tab.remove_page(0)
        def add_main_tab_item(item, name):
            main_tab.append_page(item, gtk.Label(name))
        # TODO: move these to plugins, as well
        self.settings.register_ui_section("main", add_main_tab_item,
                clear_main_tab)
        main_window = self.gui.get_object("WindowBox")
        def clear_main_window():
            main_window.foreach(lambda x: main_window.remove(x))
        def add_main_window_item(item, name, **extra_args):
            # some widgets may want to override the defaults
            args = {"expand": False, "fill": False}
            args.update(extra_args)
            main_window.pack_start(item, **args)
        main_tab.unparent()
        self.settings.register_ui_section("main_window", add_main_window_item,
                clear_main_window)
        self.settings.register_ui("main_window", "Tabs", main_tab, -20,
                args_dict={"expand": True, "fill": True})
        # autoload task settings file on startup
        autoload_enable = self.gui.get_object("AutoLoadTaskFile")
        autoload_box = self.gui.get_object("StartupTaskFileBox")
        autoload_source = self.gui.get_object("StartupTaskFile")
        for one_filter in get_filters_from_list(FILTER_CONFIG):
            autoload_source.add_filter(one_filter)
            autoload_source.set_filter(one_filter)
        def get_autoload_task_file(autoload_source=autoload_source):
            if autoload_enable.get_active():
                return autoload_source.get_filename()
            else:
                return ""
        def set_autoload_task_file(filename):
            if filename:
                autoload_enable.set_active(True)
                autoload_box.show()
                autoload_source.set_filename(filename)
            else:
                autoload_enable.set_active(False)
                autoload_box.hide()
                autoload_source.unselect_all()
        def autoload_enable_switched(widget, box):
            if not widget.get_active():
                set_autoload_task_file(None)
            else:
                autoload_box.show()
        autoload_enable.connect("toggled", autoload_enable_switched,
                autoload_box)
        self.settings.add_item("default_task_settings_file",
                get_autoload_task_file, set_autoload_task_file)
        # visual and general settings
        for name, objname in (("show_model", "ShowModelCheckBox"),
                ("show_axes", "ShowAxesCheckBox"),
                ("show_support_grid", "ShowSupportGridCheckBox"),
                ("show_dimensions", "ShowDimensionsCheckBox"),
                ("show_bounding_box", "ShowBoundingCheckBox"),
                ("show_toolpath", "ShowToolPathCheckBox"),
                ("show_drill", "ShowDrillCheckBox"),
                ("show_directions", "ShowDirectionsCheckBox")):
            obj = self.gui.get_object(objname)
            self.settings.add_item(name, obj.get_active, obj.set_active)
            # all of the objects above should trigger redraw
            obj.connect("toggled", lambda widget: \
                    self.settings.emit_event("model-change-after"))
        def disable_gui():
            self.menubar.set_sensitive(False)
            main_tab.set_sensitive(False)
        def enable_gui():
            self.menubar.set_sensitive(True)
            main_tab.set_sensitive(True)
        self.settings.register_event("gui-disable", disable_gui)
        self.settings.register_event("gui-enable", enable_gui)
        for name, objname in (
                ("view_light", "OpenGLLight"),
                ("view_shadow", "OpenGLShadow"),
                ("view_polygon", "OpenGLPolygon"),
                ("view_perspective", "OpenGLPerspective")):
            obj = self.gui.get_object(objname)
            self.settings.add_item(name, obj.get_active, obj.set_active)
            # send "True" to trigger a re-setup of GL settings
            obj.connect("toggled", lambda widget: \
                    self.settings.emit_event("visual-item-updated"))
        # color selectors
        def get_color_wrapper(obj):
            def gtk_color_to_float():
                gtk_color = obj.get_color()
                alpha = obj.get_alpha()
                return (gtk_color.red / GTK_COLOR_MAX,
                        gtk_color.green / GTK_COLOR_MAX,
                        gtk_color.blue / GTK_COLOR_MAX,
                        alpha / GTK_COLOR_MAX)
            return gtk_color_to_float
        def set_color_wrapper(obj):
            def set_gtk_color_by_float(components):
                # use alpha if it was given
                if len(components) == 3:
                    alpha = 1.0
                else:
                    alpha = components[3]
                red, green, blue = components[:3]
                obj.set_color(gtk.gdk.Color(int(red * GTK_COLOR_MAX),
                        int(green * GTK_COLOR_MAX), int(blue * GTK_COLOR_MAX)))
                obj.set_alpha(int(alpha * GTK_COLOR_MAX))
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
            obj.connect("color-set", lambda widget: \
                    self.settings.emit_event("visual-item-updated"))
        skip_obj = self.gui.get_object("DrillProgressFrameSkipControl")
        self.settings.add_item("drill_progress_max_fps", skip_obj.get_value, skip_obj.set_value)
        # gcode settings
        gcode_minimum_step_x = self.gui.get_object("GCodeMinimumStep_x")
        self.settings.add_item("gcode_minimum_step_x",
                gcode_minimum_step_x.get_value, gcode_minimum_step_x.set_value)
        gcode_minimum_step_y = self.gui.get_object("GCodeMinimumStep_y")
        self.settings.add_item("gcode_minimum_step_y",
                gcode_minimum_step_y.get_value, gcode_minimum_step_y.set_value)
        gcode_minimum_step_z = self.gui.get_object("GCodeMinimumStep_z")
        self.settings.add_item("gcode_minimum_step_z",
                gcode_minimum_step_z.get_value, gcode_minimum_step_z.set_value)
        gcode_safety_height = self.gui.get_object("SafetyHeightControl")
        self.settings.add_item("gcode_safety_height",
                gcode_safety_height.get_value, gcode_safety_height.set_value)
        gcode_spindle_delay = self.gui.get_object("GCodeSpindleDelay")
        self.settings.add_item("gcode_spindle_delay",
                gcode_spindle_delay.get_value, gcode_spindle_delay.set_value)
        for objname, setting in (
                ("GCodeTouchOffOnStartup", "touch_off_on_startup"),
                ("GCodeTouchOffOnToolChange", "touch_off_on_tool_change")):
            obj = self.gui.get_object(objname)
            obj.connect("toggled", self.update_gcode_controls)
            self.settings.add_item(setting, obj.get_active, obj.set_active)
        touch_off_pos_selector = self.gui.get_object("TouchOffLocationSelector")
        def get_touch_off_position_type():
            index = touch_off_pos_selector.get_active()
            if index < 0:
                return PREFERENCES_DEFAULTS["touch_off_position_type"]
            else:
                return touch_off_pos_selector.get_model()[index][0]
        def set_touch_off_position_type(new_key):
            model = touch_off_pos_selector.get_model()
            for index, (key, value) in enumerate(model):
                if key == new_key:
                    touch_off_pos_selector.set_active(index)
                    break
            else:
                touch_off_pos_selector.set_active(-1)
        touch_off_pos_selector.connect("changed", self.update_gcode_controls)
        self.settings.add_item("touch_off_position_type",
                get_touch_off_position_type, set_touch_off_position_type)
        for axis in "XYZ":
            obj = self.gui.get_object("ToolChangePos%s" % axis.upper())
            self.settings.add_item("touch_off_position_%s" % axis.lower(),
                    obj.get_value, obj.set_value)
        for objname, setting in (
                ("ToolChangeRapidMoveDown", "touch_off_rapid_move"),
                ("ToolChangeSlowMoveDown", "touch_off_slow_move"),
                ("ToolChangeSlowMoveSpeed", "touch_off_slow_feedrate"),
                ("TouchOffHeight", "touch_off_height")):
            obj = self.gui.get_object(objname)
            self.settings.add_item(setting, obj.get_value, obj.set_value)
        touch_off_pause = self.gui.get_object("TouchOffPauseExecution")
        self.settings.add_item("touch_off_pause_execution",
                touch_off_pause.get_active, touch_off_pause.set_active)
        # redraw the toolpath if safety height changed
        gcode_safety_height.connect("value-changed", lambda widget:
                self.settings.emit_event("visual-item-updated"))
        gcode_path_mode = self.gui.get_object("GCodeCornerStyleControl")
        self.settings.add_item("gcode_path_mode", gcode_path_mode.get_active,
                gcode_path_mode.set_active)
        gcode_path_mode.connect("changed", self.update_gcode_controls)
        gcode_motion_tolerance = self.gui.get_object(
                "GCodeCornerStyleMotionTolerance")
        self.settings.add_item("gcode_motion_tolerance",
                gcode_motion_tolerance.get_value,
                gcode_motion_tolerance.set_value)
        gcode_naive_tolerance = self.gui.get_object(
                "GCodeCornerStyleCAMTolerance")
        self.settings.add_item("gcode_naive_tolerance",
                gcode_naive_tolerance.get_value,
                gcode_naive_tolerance.set_value)
        gcode_start_stop_spindle = self.gui.get_object("GCodeStartStopSpindle")
        self.settings.add_item("gcode_start_stop_spindle",
                gcode_start_stop_spindle.get_active,
                gcode_start_stop_spindle.set_active)
        gcode_start_stop_spindle.connect("toggled", self.update_gcode_controls)
        gcode_filename_extension = self.gui.get_object("GCodeFilenameExtension")
        self.settings.add_item("gcode_filename_extension",
                gcode_filename_extension.get_text,
                gcode_filename_extension.set_text)
        # configure locations of external programs
        for auto_control_name, location_control_name, browse_button, key in (
                ("ExternalProgramInkscapeAuto",
                "ExternalProgramInkscapeControl",
                "ExternalProgramInkscapeBrowse", "inkscape"),
                ("ExternalProgramPstoeditAuto",
                "ExternalProgramPstoeditControl",
                "ExternalProgramPstoeditBrowse", "pstoedit")):
            self.gui.get_object(auto_control_name).connect("clicked",
                    self._locate_external_program, key)
            location_control = self.gui.get_object(location_control_name)
            self.settings.add_item("external_program_%s" % key,
                    location_control.get_text, location_control.set_text)
            self.gui.get_object(browse_button).connect("clicked",
                    self._browse_external_program_location, key)
        # set the icons (in different sizes) for all windows
        gtk.window_set_default_icon_list(*get_icons_pixbuffers())
        # load menu data
        gtk_menu_file = get_ui_file_location(GTKMENU_FILE)
        if gtk_menu_file is None:
            gtk.main_quit()
        uimanager.add_ui_from_file(gtk_menu_file)
        # make the actions defined in the GTKBUILD file available in the menu
        actiongroup = gtk.ActionGroup("menubar")
        for action in [action for action in self.gui.get_objects()
                if isinstance(action, gtk.Action)]:
            actiongroup.add_action(action)
        # the "pos" parameter is optional since 2.12 - we can remove it later
        uimanager.insert_action_group(actiongroup, pos=-1)
        # the "recent files" sub-menu
        if not self.recent_manager is None:
            recent_files_menu = gtk.RecentChooserMenu(self.recent_manager)
            recent_files_menu.set_name("RecentFilesMenu")
            recent_menu_filter = gtk.RecentFilter()
            for filter_name, filter_patterns in FILTER_MODEL:
                if not isinstance(filter_patterns, (list, set, tuple)):
                    filter_patterns = [filter_patterns]
                for pattern in filter_patterns:
                    recent_menu_filter.add_pattern(pattern)
            recent_files_menu.add_filter(recent_menu_filter)
            recent_files_menu.set_show_numbers(True)
            # non-local files (without "file://") are not supported. yet
            recent_files_menu.set_local_only(False)
            # most recent files to the top
            recent_files_menu.set_sort_type(gtk.RECENT_SORT_MRU)
            # show only ten files
            recent_files_menu.set_limit(10)
            uimanager.get_widget("/MenuBar/FileMenu/OpenRecentModelMenu").set_submenu(recent_files_menu)
            recent_files_menu.connect("item-activated",
                    self.load_recent_model_file)
        else:
            self.gui.get_object("OpenRecentModel").set_visible(False)
        # load the menubar and connect functions to its items
        self.menubar = uimanager.get_widget("/MenuBar")
        self.settings.register_ui("main_window", "Main", self.menubar, -100)
        # initialize plugins
        self.plugin_manager = pycam.Plugins.PluginManager(core=self.settings)
        self.plugin_manager.import_plugins()
        # fallback - in case of a failure when opening a model file
        model = pycam.Importers.TestModel.get_test_model()
        self.settings.get("models").append(model)
        # some more initialization
        self.reset_preferences()
        self.load_preferences()
        self.load_task_settings()
        # Without this "gkt.main_iteration" loop the task settings file
        # control would not be updated in time.
        while gtk.events_pending():
            gtk.main_iteration()
        autoload_task_filename = self.settings.get("default_task_settings_file")
        if autoload_task_filename:
            self.open_task_settings_file(autoload_task_filename)
        self.update_all_controls()
        self.no_dialog = no_dialog
        if not self.no_dialog:
            # register a logging handler for displaying error messages
            pycam.Utils.log.add_gtk_gui(self.window, logging.ERROR)
            self.window.show()

    def update_all_controls(self):
        self.update_save_actions()
        self.update_gcode_controls()
        self.update_ode_settings()

    def update_gcode_controls(self, widget=None):
        # path mode
        path_mode = self.settings.get("gcode_path_mode")
        self.gui.get_object("GCodeToleranceTable").set_sensitive(path_mode == 3)
        # spindle delay
        sensitive = self.settings.get("gcode_start_stop_spindle")
        self.gui.get_object("GCodeSpindleDelayLabel").set_sensitive(sensitive)
        self.gui.get_object("GCodeSpindleDelay").set_sensitive(sensitive)
        # tool change controls
        pos_control = self.gui.get_object("TouchOffLocationSelector")
        tool_change_pos_model = pos_control.get_model()
        active_pos_index = pos_control.get_active()
        if active_pos_index < 0:
            pos_key = None
        else:
            pos_key = tool_change_pos_model[active_pos_index][0]
        # show or hide the vbox containing the absolute tool change location
        absolute_pos_box = self.gui.get_object("AbsoluteToolChangePositionBox")
        if pos_key == "absolute":
            absolute_pos_box.show()
        else:
            absolute_pos_box.hide()
        # disable/enable the touch off position controls
        position_controls_table = self.gui.get_object("TouchOffLocationTable")
        touch_off_enabled = any([self.gui.get_object(objname).get_active()
                for objname in ("GCodeTouchOffOnStartup",
                    "GCodeTouchOffOnToolChange")])
        position_controls_table.set_sensitive(touch_off_enabled)
        # disable/enable touch probe height
        if self.gui.get_object("GCodeTouchOffOnStartup").get_active():
            update_func = "show"
        else:
            update_func = "hide"
        for objname in ("TouchOffHeight", "TouchOffHeightLabel",
                "LengthUnitTouchOffHeight"):
            getattr(self.gui.get_object(objname), update_func)()

    def update_ode_settings(self, widget=None):
        if pycam.Utils.threading.is_multiprocessing_enabled() \
                or not pycam.Physics.ode_physics.is_ode_available():
            self.enable_ode_control.set_sensitive(False)
            self.enable_ode_control.set_active(False)
        else:
            self.enable_ode_control.set_sensitive(True)

    def gui_activity_guard(func):
        def gui_activity_guard_wrapper(self, *args, **kwargs):
            if self.gui_is_active:
                return
            self.gui_is_active = True
            try:
                result = func(self, *args, **kwargs)
            except Exception:
                # Catch possible exceptions (except system-exit ones) and
                # report them.
                log.error(pycam.Utils.get_exception_report())
                result = None
            self.gui_is_active = False
            while self._batch_queue:
                batch_func, batch_args, batch_kwargs = self._batch_queue[0]
                del self._batch_queue[0]
                batch_func(*batch_args, **batch_kwargs)
            return result
        return gui_activity_guard_wrapper

    def _store_undo_state(self):
        # for now we only store the model
        if not self.settings.get("models"):
            return
        # TODO: store all models
        self._undo_states.append(pickle.dumps(self.settings.get("models")[0]))
        log.debug("Stored the current state of the model for undo")
        while len(self._undo_states) > MAX_UNDO_STATES:
            self._undo_states.pop(0)
        self.gui.get_object("UndoButton").set_sensitive(True)

    def _restore_undo_state(self, widget=None, event=None):
        if len(self._undo_states) > 0:
            latest = StringIO.StringIO(self._undo_states.pop(-1))
            model = pickle.Unpickler(latest).load()
            self.load_model(model)
            self.gui.get_object("UndoButton").set_sensitive(
                    len(self._undo_states) > 0)
            log.info("Restored the previous state of the model")
            self.settings.emit_event("model-change-after")
        else:
            log.info("No previous undo state available - request ignored")

    def show_help(self, widget=None, page="Main_Page"):
        if not page.startswith("http"):
            url = HELP_WIKI_URL % page
        else:
            url = page
        webbrowser.open(url)

    def set_model_filename(self, filename):
        """ Store the given filename for a possible later "save model" action.
        Additionally the window's title is adjusted and the "save" buttons are
        updated.
        """
        uri = pycam.Utils.URIHandler(filename)
        self.last_model_uri = uri
        if not self.last_model_uri:
            self.window.set_title("PyCAM")
        else:
            short_name = os.path.basename(uri.get_path())
            self.window.set_title("%s - PyCAM" % short_name)
        self.settings.emit_event("model-change-after")

    def update_save_actions(self):
        self.gui.get_object("SaveTaskSettings").set_sensitive(
            bool(self.last_task_settings_uri and \
                self.last_task_settings_uri.is_writable()))
        # TODO: choose all models
        models = self.settings.get("models").get_selected()
        save_as_possible = bool(models) and models[0].is_export_supported()
        self.gui.get_object("SaveAsModel").set_sensitive(save_as_possible)
        save_possible = bool(self.last_model_uri and save_as_possible and \
                self.last_model_uri.is_writable())
        #TODO: fix this dirty hack to avoid silent overwrites of PS/DXF files as SVG
        if save_possible:
            extension = os.path.splitext(self.last_model_uri.get_path(
                    ))[-1].lower()
            # TODO: fix these hard-coded file extensions
            if extension[1:] in ("eps", "ps", "dxf"):
                # can't save 2D formats except SVG
                save_possible = False
        self.gui.get_object("SaveModel").set_sensitive(save_possible)

    def _browse_external_program_location(self, widget=None, key=None):
        location = self.get_filename_via_dialog(title="Select the executable " \
                + "for '%s'" % key, mode_load=True,
                parent=self.preferences_window)
        if not location is None:
            self.settings.set("external_program_%s" % key, location)


    def _locate_external_program(self, widget=None, key=None):
        # the button was just activated
        location = get_external_program_location(key)
        if not location:
            log.error("Failed to locate the external program '%s'. " % key \
                    + "Please install the program and try again." \
                    + os.linesep \
                    + "Or maybe you need to specify the location manually.")
        else:
            # store the new setting
            self.settings.set("external_program_%s" % key, location)

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
        if (basename.rfind(".") == -1) or (basename[-6:].rfind(".") == -1):
            # The filename does not contain a dot or the dot is not within the
            # last five characters. Dots within the start of the filename are
            # ignored.
            return filename + filter_ext
        else:
            # contains at least one dot
            return filename

    @gui_activity_guard
    def save_model(self, widget=None, filename=None, model=None,
            store_filename=True):
        if model is None:
            # TODO: merge multiple models
            model = self.settings.get("models").get_selected()[0]
        if not model.is_export_supported():
            log.warn(("Saving this type of model (%s) is currently not " \
                    + "implemented!") % str(type(model)))
            return
        # get the filename
        if callable(filename):
            filename = filename()
        uri = None
        if not isinstance(filename, (basestring, pycam.Utils.URIHandler)):
            # we open a dialog
            # determine the file type
            # TODO: this needs to be decided by the exporter code
            if isinstance(model, pycam.Geometry.Model.Model):
                # TODO: fix this extremely fragile filter
                type_filter = [(name, patterns)
                        for name, patterns in FILTER_MODEL
                        if "STL" in name.upper()]
            elif isinstance(model, pycam.Geometry.Model.ContourModel):
                type_filter = [(name, patterns)
                        for name, patterns in FILTER_MODEL
                        if "SVG" in name.upper()]
            filename = self.get_filename_via_dialog("Save model to ...",
                    mode_load=False, type_filter=type_filter,
                    filename_templates=(self.last_model_uri,))
            if filename:
                uri = pycam.Utils.URIHandler(filename)
                if uri.is_local() and store_filename:
                    self.set_model_filename(filename)
        else:
            uri = pycam.Utils.URIHandler(filename)
        # no filename given -> exit
        if not uri:
            return
        if not uri.is_local():
            log.error("Unable to write file to a non-local " + \
                    "destination: %s" % uri)
        else:
            try:
                file_in = open(uri.get_local_path(), "w")
                model.export(comment=self.get_meta_data(),
                        unit=self.settings.get("unit")).write(file_in)
                file_in.close()
            except IOError, err_msg:
                log.error("Failed to save model file: %s" % err_msg)
            else:
                log.info("Successfully stored the current model as '%s'." % \
                        str(filename))
                self.update_save_actions()
                self.add_to_recent_file_list(filename)

    @gui_activity_guard
    def reset_preferences(self, widget=None):
        """ reset all preferences to their default values """
        for key, value in PREFERENCES_DEFAULTS.items():
            self.settings.set(key, value)
        # redraw the model due to changed colors, display items ...
        self.settings.emit_event("model-change-after")

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
                log.warn("Skipping obsolete preference item: %s" % str(item))
        for item in PREFERENCES_DEFAULTS.keys():
            if not config.has_option("DEFAULT", item):
                # a new preference setting is missing in the (old) file
                continue
            value_raw = config.get("DEFAULT", item)
            old_value = self.settings.get(item)
            value_type = type(PREFERENCES_DEFAULTS[item])
            if isinstance(value_type(), basestring):
                # keep strings as they are
                value = str(value_raw)
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
            log.warn("Failed to create a preferences directory in " \
                    + "your user's home directory.")
            return
        config = ConfigParser.ConfigParser()
        for item in PREFERENCES_DEFAULTS.keys():
            config.set("DEFAULT", item, self.settings.get(item))
        try:
            config_file = file(config_filename, "w")
            config.write(config_file)
            config_file.close()
        except IOError, err_msg:
            log.warn("Failed to write preferences file (%s): %s" % (config_filename, err_msg))

    def destroy(self, widget=None, data=None):
        gtk.main_quit()
        self.quit()

    def quit(self):
        self.save_preferences()

    def configure_drag_and_drop(self, obj):
        obj.connect("drag-data-received", self.handle_data_drop)
        flags = gtk.DEST_DEFAULT_ALL
        targets = [(key, gtk.TARGET_OTHER_APP, index)
                for index, key in enumerate(FILENAME_DRAG_TARGETS)]
        actions = gtk.gdk.ACTION_COPY | gtk.gdk.ACTION_LINK | \
                gtk.gdk.ACTION_DEFAULT | gtk.gdk.ACTION_PRIVATE | \
                gtk.gdk.ACTION_ASK
        obj.drag_dest_set(flags, targets, actions)

    def handle_data_drop(self, widget, drag_context, x, y, selection_data, info,
            timestamp):
        if info != 0:
            uris = [str(selection_data.data)]
        elif pycam.Utils.get_platform() == pycam.Utils.PLATFORM_WINDOWS:
            uris = selection_data.data.splitlines()
        else:
            uris = selection_data.get_uris()
        if not uris:
            # empty selection
            return True
        for uri in uris:
            if not uri or (uri == chr(0)):
                continue
            uri = pycam.Utils.URIHandler(uri)
            file_type, importer = pycam.Importers.detect_file_type(uri,
                    quiet=True)
            if importer:
                # looks like the file can be loaded
                if self.load_model_file(filename=uri):
                    return True
        if len(uris) > 1:
            log.error("Failed to open any of the given models: %s" % \
                    str(uris))
        else:
            log.error("Failed to open the model: %s" % str(uris[0]))
        return False

    def append_to_queue(self, func, *args, **kwargs):
        # check if gui is currently active
        if self.gui_is_active:
            # queue the function call
            self._batch_queue.append((func, args, kwargs))
        else:
            # call the function right now
            func(*args, **kwargs)

    def load_recent_model_file(self, widget):
        uri = widget.get_current_uri()
        self.load_model_file(filename=uri)

    @gui_activity_guard
    def load_model_file(self, widget=None, filename=None, store_filename=True):
        if callable(filename):
            filename = filename()
        if not filename:
            filename = self.get_filename_via_dialog("Loading model ...",
                    mode_load=True, type_filter=FILTER_MODEL)
        if filename:
            file_type, importer = pycam.Importers.detect_file_type(filename)
            if file_type and callable(importer):
                progress = self.settings.get("progress")
                progress.update(text="Loading model ...")
                # "cancel" is not allowed
                progress.disable_cancel()
                if self.load_model(importer(filename,
                        program_locations=get_all_program_locations(self.settings),
                        unit=self.settings.get("unit"),
                        fonts_cache=self.settings.get("fonts"),
                        callback=progress.update)):
                    if store_filename:
                        self.set_model_filename(filename)
                    self.add_to_recent_file_list(filename)
                    result = True
                else:
                    result = False
                progress.finish()
                return result
            else:
                log.error("Failed to detect filetype!")
                return False

    def export_emc_tools(self, widget=None, filename=None):
        if callable(filename):
            filename = filename()
        if not filename:
            filename = self.get_filename_via_dialog("Exporting EMC tool definition ...",
                    mode_load=False, type_filter=FILTER_EMC_TOOL,
                    filename_templates=(self.last_model_uri,))
        if filename:
            export = pycam.Exporters.EMCToolExporter.EMCToolExporter(self.settings.get("tools"))
            text = export.get_tool_definition_string()
            try:
                out = file(filename, "w")
                out.write(text)
                out.close()
            except IOError, err_msg:
                log.error("Failed to save EMC tool file: %s" % err_msg)
            else:
                self.add_to_recent_file_list(filename)

    def finish_startup(self):
        """ This function is called by the pycam script after everything is
        set up properly.
        """
        # empty the "undo" states (accumulated by loading the defualt model)
        while self._undo_states:
            self._undo_states.pop(0)

    def open_task_settings_file(self, filename):
        """ This function is used by the commandline handler """
        self.last_task_settings_uri = pycam.Utils.URIHandler(filename)
        self.load_task_settings_file(filename=filename)
        self.update_save_actions()

    @gui_activity_guard
    def load_task_settings_file(self, widget=None, filename=None):
        if callable(filename):
            filename = filename()
        if not filename:
            filename = self.get_filename_via_dialog("Loading settings ...",
                    mode_load=True, type_filter=FILTER_CONFIG)
            # Only update the last_task_settings attribute if the task file was
            # loaded interactively. E.g. ignore the initial task file loading.
            if filename:
                self.last_task_settings_uri = pycam.Utils.URIHandler(filename)
        if filename:
            log.info("Loading task settings file: %s" % str(filename))
            self.load_task_settings(filename)
            self.add_to_recent_file_list(filename)
        self.update_save_actions()

    def load_model(self, model):
        # load the new model only if the import worked
        if model:
            self.settings.emit_event("model-change-before")
            self.settings.get("models").append(model)
            self.last_model_uri = None
            return True
        else:
            return False

    def load_task_settings(self, filename=None):
        settings = pycam.Gui.Settings.ProcessSettings()
        if not filename is None:
            settings.load_file(filename)
        # flush all tables (without re-assigning new objects)
        for one_list_name in ("tools", "processes", "bounds", "tasks"):
            one_list = self.settings.get(one_list_name)
            while len(one_list) > 0:
                one_list.pop()
        # TODO: load default tools/processes/bounds

    @gui_activity_guard
    def save_task_settings_file(self, widget=None, filename=None):
        if callable(filename):
            filename = filename()
        if not isinstance(filename, (basestring, pycam.Utils.URIHandler)):
            # we open a dialog
            filename = self.get_filename_via_dialog("Save settings to ...",
                    mode_load=False, type_filter=FILTER_CONFIG,
                    filename_templates=(self.last_task_settings_uri, self.last_model_uri))
            if filename:
                self.last_task_settings_uri = pycam.Utils.URIHandler(filename)
                self.update_save_actions()
        # no filename given -> exit
        if not filename:
            return
        settings = pycam.Gui.Settings.ProcessSettings()
        if not settings.write_to_file(filename, self.settings.get("tools"),
                self.settings.get("processes"), self.settings.get("bounds"),
                self.settings.get("tasks")):
            log.error("Failed to save settings file")
        else:
            log.info("Task settings written to %s" % filename)
            self.add_to_recent_file_list(filename)
        self.update_save_actions()

    def get_filename_via_dialog(self, title, mode_load=False, type_filter=None,
            filename_templates=None, filename_extension=None, parent=None):
        if parent is None:
            parent = self.window
        # we open a dialog
        if mode_load:
            dialog = gtk.FileChooserDialog(title=title,
                    parent=parent, action=gtk.FILE_CHOOSER_ACTION_OPEN,
                    buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                        gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        else:
            dialog = gtk.FileChooserDialog(title=title,
                    parent=self.window, action=gtk.FILE_CHOOSER_ACTION_SAVE,
                    buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                        gtk.STOCK_SAVE, gtk.RESPONSE_OK))
        # set the initial directory to the last one used
        if self.last_dirname and os.path.isdir(self.last_dirname):
            dialog.set_current_folder(self.last_dirname)
        # add filter for files
        if type_filter:
            for file_filter in get_filters_from_list(type_filter):
                dialog.add_filter(file_filter)
        # guess the export filename based on the model's filename
        valid_templates = []
        if filename_templates:
            for template in filename_templates:
                if not template:
                    continue
                elif hasattr(template, "get_path"):
                    valid_templates.append(template.get_path())
                else:
                    valid_templates.append(template)
        if valid_templates:
            filename_template = valid_templates[0]
            # remove the extension
            default_filename = os.path.splitext(filename_template)[0]
            if filename_extension:
                default_filename += os.path.extsep + filename_extension
            elif type_filter:
                for one_type in type_filter:
                    extension = one_type[1]
                    if isinstance(extension, (list, tuple, set)):
                        extension = extension[0]
                    # use only the extension of the type filter string
                    extension = os.path.splitext(extension)[1]
                    if extension:
                        default_filename += extension
                        # finish the loop
                        break
            dialog.select_filename(default_filename)
            try:
                dialog.set_current_name(
                        os.path.basename(default_filename).encode("utf-8"))
            except UnicodeError:
                # ignore
                pass
        # add filter for all files
        ext_filter = gtk.FileFilter()
        ext_filter.set_name("All files")
        ext_filter.add_pattern("*")
        dialog.add_filter(ext_filter)
        done = False
        while not done:
            dialog.set_filter(dialog.list_filters()[0])
            response = dialog.run()
            filename = dialog.get_filename()
            uri = pycam.Utils.URIHandler(filename)
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
            elif mode_load and not uri.exists():
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
            self.add_to_recent_file_list(filename)
        return filename

    def add_to_recent_file_list(self, filename):
        # Add the item to the recent files list - if it already exists.
        # Otherwise it will be added later after writing the file.
        uri = pycam.Utils.URIHandler(filename)
        if uri.exists():
            # skip this, if the recent manager is not available (e.g. GTK 2.12.1 on Windows)
            if self.recent_manager:
                if self.recent_manager.has_item(uri.get_url()):
                    try:
                        self.recent_manager.remove_item(uri.get_url())
                    except gobject.GError:
                        pass
                self.recent_manager.add_item(uri.get_url())
            # store the directory of the last loaded file
            if uri.is_local():
                self.last_dirname = os.path.dirname(uri.get_local_path())

    def get_meta_data(self):
        filename = "Filename: %s" % str(self.last_model_uri)
        timestamp = "Timestamp: %s" % str(datetime.datetime.now())
        version = "Version: %s" % VERSION
        result = []
        for text in (filename, timestamp, version):
            result.append("%s %s" % (self.META_DATA_PREFIX, text))
        return os.linesep.join(result)

    def mainloop(self):
        # run the mainloop only if a GUI was requested
        if not self.no_dialog:
            gtk_settings = gtk.settings_get_default()
            # force the icons to be displayed
            gtk_settings.props.gtk_menu_images = True
            gtk_settings.props.gtk_button_images = True
            try:
                gtk.main()
            except KeyboardInterrupt:
                self.quit()

if __name__ == "__main__":
    GUI = ProjectGui()
    if len(sys.argv) > 1:
        GUI.load_model_file(sys.argv[1])
    GUI.mainloop()

