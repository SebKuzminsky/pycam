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
import datetime
import gtk
import gobject
import webbrowser
import ConfigParser
import StringIO
import pickle
import logging

import pycam.Gui.Settings
import pycam.Importers.CXFImporter
import pycam.Importers.TestModel
import pycam.Importers
import pycam.Utils.log
from pycam.Utils.locations import get_data_file_location, \
        get_ui_file_location, get_external_program_location, \
        get_all_program_locations
import pycam.Utils
import pycam.Plugins
from pycam import VERSION
import pycam.Physics.ode_physics

GTKBUILD_FILE = "pycam-project.ui"
GTKMENU_FILE = "menubar.xml"
GTKRC_FILE_WINDOWS = "gtkrc_windows"

WINDOW_ICON_FILENAMES = ["logo_%dpx.png" % pixels for pixels in (16, 32, 48, 64, 128)]

HELP_WIKI_URL = "http://sourceforge.net/apps/mediawiki/pycam/index.php?title=%s"

FILTER_MODEL = (("All supported model filetypes",
                ("*.stl", "*.dxf", "*.svg", "*.eps", "*.ps")),
        ("STL models", "*.stl"), ("DXF contours", "*.dxf"),
        ("SVG contours", "*.svg"), ("PS contours", ("*.eps", "*.ps")))
FILTER_CONFIG = (("Config files", "*.conf"),)

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
        "color_grid": (0.75, 1.0, 0.7, 0.55),
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


log = pycam.Utils.log.get_logger()

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
CHAIN_FUNC_INDEX, CHAIN_WEIGHT_INDEX = range(2)


class EventCore(pycam.Gui.Settings.Settings):

    def __init__(self):
        super(EventCore, self).__init__()
        self.event_handlers = {}
        self.ui_sections = {}
        self.chains = {}

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
            handlers = self.event_handlers[event]
            for index, item in enumerate(handlers[EVENT_HANDLER_INDEX]):
                if func == item[HANDLER_FUNC_INDEX]:
                    removal_list.append(index)
            removal_list.reverse()
            for index in removal_list:
                handlers[EVENT_HANDLER_INDEX].pop(index)
        else:
            log.debug("Trying to unregister an unknown event: %s" % event)

    def emit_event(self, event, *args, **kwargs):
        log.debug2("Event emitted: %s" % str(event))
        if event in self.event_handlers:
            if self.event_handlers[event][EVENT_BLOCKER_INDEX] != 0:
                return
            # prevent infinite recursion
            self.block_event(event)
            for handler in self.event_handlers[event][EVENT_HANDLER_INDEX]:
                func = handler[HANDLER_FUNC_INDEX]
                data = handler[HANDLER_ARG_INDEX]
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

    def unregister_ui_section(self, section):
        if section in self.ui_sections:
            ui_section = self.ui_sections[section]
            while ui_section[UI_WIDGET_INDEX]:
                ui_section[UI_WIDGET_INDEX].pop()
            del self.ui_sections[section]
        else:
            log.debug("Trying to unregister a non-existent ui section: %s" % \
                    str(section))

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
        current_widgets = [item[1]
                for item in self.ui_sections[section][UI_WIDGET_INDEX]]
        if (not widget is None) and (widget in current_widgets):
            log.debug("Tried to register widget twice: %s -> %s" % \
                    (section, name))
            return
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
            self._rebuild_ui_section(section)
        else:
            log.debug("Trying to unregister unknown ui section: %s" % section)

    def register_chain(self, name, func, weight=100):
        if not name in self.chains:
            self.chains[name] = []
        self.chains[name].append((func, weight))
        self.chains[name].sort(key=lambda item: item[CHAIN_WEIGHT_INDEX])

    def unregister_chain(self, name, func):
        if name in self.chains:
            for index, data in enumerate(self.chains[name]):
                if data[CHAIN_FUNC_INDEX] == func:
                    self.chains[name].pop(index)
                    break
            else:
                log.debug("Trying to unregister unknown function from " + \
                        "%s: %s" % (name, func))
        else:
            log.debug("Trying to unregister from unknown chain: %s" % name)

    def call_chain(self, name, *args, **kwargs):
        if name in self.chains:
            for data in self.chains[name]:
                data[CHAIN_FUNC_INDEX](*args, **kwargs)
        else:
            log.debug("Called an unknown chain: %s" % name)


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
        self.settings.set("main_window", self.window)
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
                lambda: self.settings.emit_event("visual-item-updated"))
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
            for child in preferences_book.get_children():
                preferences_book.remove(child)
        def add_preferences_item(item, name):
            preferences_book.append_page(item, gtk.Label(name))
        self.settings.register_ui_section("preferences",
                add_preferences_item, clear_preferences)
        for obj_name, label, priority in (
                ("GeneralSettingsPrefTab", "General", -50),
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
            while main_tab.get_n_pages() > 0:
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
        # TODO: fix the extension filter
        #for one_filter in get_filters_from_list(FILTER_CONFIG):
        #    autoload_source.add_filter(one_filter)
        #    autoload_source.set_filter(one_filter)
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
        def disable_gui():
            self.menubar.set_sensitive(False)
            main_tab.set_sensitive(False)
        def enable_gui():
            self.menubar.set_sensitive(True)
            main_tab.set_sensitive(True)
        self.settings.register_event("gui-disable", disable_gui)
        self.settings.register_event("gui-enable", enable_gui)
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
        # dict of all merge-ids
        menu_merges = {}
        def clear_menu(menu_key):
            for merge in menu_merges.get(menu_key, []):
                uimanager.remove_ui(merge)
        def append_menu_item(menu_key, base_path, widget, name):
            merge_id = uimanager.new_merge_id()
            if widget:
                action_group = widget.props.action_group
                if not action_group in uimanager.get_action_groups():
                    uimanager.insert_action_group(action_group, -1)
                widget_name = widget.get_name()
                item_type = gtk.UI_MANAGER_MENUITEM
            else:
                widget_name = name
                item_type = gtk.UI_MANAGER_SEPARATOR
            uimanager.add_ui(merge_id, base_path, name, widget_name, item_type,
                    False)
            if not menu_key in menu_merges:
                menu_merges[menu_key] = []
            menu_merges[menu_key].append(merge_id)
        def get_menu_funcs(menu_key, base_path):
            append_func = lambda widget, name: \
                    append_menu_item(menu_key, base_path, widget, name)
            clear_func = lambda: clear_menu(menu_key)
            return append_func, clear_func
        for ui_name, base_path in (("view_menu", "/MenuBar/ViewMenu"),
                ("file_menu", "/MenuBar/FileMenu"),
                ("edit_menu", "/MenuBar/EditMenu"),
                ("export_menu", "/MenuBar/FileMenu/ExportMenu")):
            append_func, clear_func = get_menu_funcs(ui_name, base_path)
            self.settings.register_ui_section(ui_name, append_func, clear_func)
        self.settings.register_ui("file_menu", "Quit",
                self.gui.get_object("Quit"), 100)
        self.settings.register_ui("file_menu", "QuitSeparator", None, 95)
        self.settings.register_ui("main_window", "Main", self.menubar, -100)
        # initialize plugins
        self.plugin_manager = pycam.Plugins.PluginManager(core=self.settings)
        self.plugin_manager.import_plugins()
        # some more initialization
        self.reset_preferences()
        self.load_preferences()
        self.load_task_settings()
        self.settings.register_event("notify-file-saved",
                self.add_to_recent_file_list)
        self.settings.register_event("notify-file-opened",
                self.add_to_recent_file_list)
        # fallback - in case of a failure when opening a model file
        model = pycam.Importers.TestModel.get_test_model()
        self.settings.get("models").append(model)
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
        self.update_ode_settings()

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

    def _browse_external_program_location(self, widget=None, key=None):
        location = self.settings.get("get_filename_func")(title="Select the executable " \
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
            filename = self.settings.get("get_filename_func")("Loading model ...",
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

    @gui_activity_guard
    def load_task_settings_file(self, widget=None, filename=None):
        if callable(filename):
            filename = filename()
        if not filename:
            filename = self.settings.get("get_filename_func")("Loading settings ...",
                    mode_load=True, type_filter=FILTER_CONFIG)
            # Only update the last_task_settings attribute if the task file was
            # loaded interactively. E.g. ignore the initial task file loading.
            if filename:
                self.last_task_settings_uri = pycam.Utils.URIHandler(filename)
        if filename:
            log.info("Loading task settings file: %s" % str(filename))
            self.load_task_settings(filename)
            self.add_to_recent_file_list(filename)

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
            while one_list:
                one_list.pop()
        # TODO: load default tools/processes/bounds

    @gui_activity_guard
    def save_task_settings_file(self, widget=None, filename=None):
        if callable(filename):
            filename = filename()
        if not isinstance(filename, (basestring, pycam.Utils.URIHandler)):
            # we open a dialog
            filename = self.settings.get("get_filename_func")("Save settings to ...",
                    mode_load=False, type_filter=FILTER_CONFIG,
                    filename_templates=(self.last_task_settings_uri, self.last_model_uri))
            if filename:
                self.last_task_settings_uri = pycam.Utils.URIHandler(filename)
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

