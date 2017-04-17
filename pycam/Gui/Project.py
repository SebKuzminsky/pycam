#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
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


import datetime
import logging
import os
import sys
import webbrowser

import gobject
import gtk

from pycam import VERSION, DOC_BASE_URL
import pycam.Importers.CXFImporter
import pycam.Importers.TestModel
import pycam.Importers
import pycam.Gui
from pycam.Utils.locations import get_ui_file_location, get_external_program_location, \
        get_all_program_locations
import pycam.Utils
import pycam.Utils.log


GTKBUILD_FILE = "pycam-project.ui"
GTKMENU_FILE = "menubar.xml"
GTKRC_FILE_WINDOWS = "gtkrc_windows"

WINDOW_ICON_FILENAMES = ["logo_%dpx.png" % pixels for pixels in (16, 32, 48, 64, 128)]

FILTER_MODEL = (("All supported model filetypes",
                 ("*.stl", "*.dxf", "*.svg", "*.eps", "*.ps")),
                ("STL models", "*.stl"),
                ("DXF contours", "*.dxf"),
                ("SVG contours", "*.svg"),
                ("PS contours", ("*.eps", "*.ps")))

FILENAME_DRAG_TARGETS = ("text/uri-list", "text-plain")


log = pycam.Utils.log.get_logger()


def get_icons_pixbuffers():
    result = []
    for icon_filename in WINDOW_ICON_FILENAMES:
        abs_filename = get_ui_file_location(icon_filename, silent=True)
        if abs_filename:
            try:
                result.append(gtk.gdk.pixbuf_new_from_file(abs_filename))
            except gobject.GError as err_msg:
                # ignore icons that are not found
                log.debug("Failed to process window icon (%s): %s", abs_filename, err_msg)
        else:
            log.debug("Failed to locate window icon: %s", icon_filename)
    return result


class ProjectGui(pycam.Gui.BaseUI):

    META_DATA_PREFIX = "PYCAM-META-DATA:"

    def __init__(self, event_manager, no_dialog=False):
        super(ProjectGui, self).__init__(event_manager)
        self.gui_is_active = False
        # during initialization any dialog (e.g. "Unit change") is not allowed
        # we set the final value later
        self.no_dialog = True
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
            # Error message: Gtk:ERROR:gtkrecentmanager.c:1942:get_icon_fallback:
            #    assertion failed: (retval != NULL)
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
                ("OpenModel", self.load_model_file, None, "<Control>o"),
                ("Quit", self.destroy, None, "<Control>q"),
                ("GeneralSettings", self.toggle_preferences_window, None, "<Control>p"),
                ("UndoButton", self.restore_undo_state, None, "<Control>z"),
                ("HelpIntroduction", self.show_help, "introduction", "F1"),
                ("HelpSupportedFormats", self.show_help, "supported-formats", None),
                ("HelpModelTransformations", self.show_help, "model-transformations", None),
                ("HelpProcessSettings", self.show_help, "process-settings", None),
                ("HelpBoundsSettings", self.show_help, "bounding-box", None),
                ("HelpTouchOff", self.show_help, "touch-off", None),
                ("Help3DView", self.show_help, "3d-view", None),
                ("HelpServerMode", self.show_help, "server-mode", None),
                ("HelpCommandLine", self.show_help, "cli-examples", None),
                ("HelpHotkeys", self.show_help, "keyboard-shortcuts", None),
                ("ProjectWebsite", self.show_help, "http://pycam.sourceforge.net", None),
                ("DevelopmentBlog", self.show_help, "http://fab.senselab.org/pycam", None),
                ("Forum", self.show_help, "http://sourceforge.net/projects/pycam/forums", None),
                ("BugTracker", self.show_help,
                 "https://github.com/SebKuzminsky/pycam/issues/", None),
                ("FeatureRequest", self.show_help,
                 "https://github.com/SebKuzminsky/pycam/issues/", None)):
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
        self.settings.register_event("undo-states-changed", self._update_undo_button)
        self.settings.register_event("model-change-after",
                                     lambda: self.settings.emit_event("visual-item-updated"))
        # configure drag-n-drop for config files and models
        self.settings.set("configure-drag-drop-func", self.configure_drag_and_drop)
        self.settings.get("configure-drag-drop-func")(self.window)
        # other events
        self.window.connect("destroy", self.destroy)
        self.window.connect("delete-event", self.destroy)
        # the settings window
        self.gui.get_object("CloseSettingsWindow").connect("clicked",
                                                           self.toggle_preferences_window, False)
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
        self.gui.get_object("AboutWindowButtons").get_children()[-1].connect(
            "clicked", self.toggle_about_window, False)
        self.about_window.connect("delete-event", self.toggle_about_window, False)
        # menu bar
        uimanager = gtk.UIManager()
        self.settings.set("gtk-uimanager", uimanager)
        self._accel_group = uimanager.get_accel_group()

        # send a "delete" event on "CTRL-w" for every window
        def handle_window_close(accel_group, window, *args):
            window.emit("delete-event", gtk.gdk.Event(gtk.gdk.DELETE))

        self._accel_group.connect_group(ord('w'), gtk.gdk.CONTROL_MASK, gtk.ACCEL_LOCKED,
                                        handle_window_close)
        self.settings.add_item("gtk-accel-group", lambda: self._accel_group)
        for obj in self.gui.get_objects():
            if isinstance(obj, gtk.Window):
                obj.add_accel_group(self._accel_group)
        # preferences tab
        preferences_book = self.gui.get_object("PreferencesNotebook")

        def clear_preferences():
            for child in preferences_book.get_children():
                preferences_book.remove(child)

        def add_preferences_item(item, name):
            preferences_book.append_page(item, gtk.Label(name))

        self.settings.register_ui_section("preferences", add_preferences_item, clear_preferences)
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

        self.settings.register_ui_section("preferences_general", add_general_prefs_item,
                                          clear_general_prefs)
        # defaults settings file
        obj = self.gui.get_object("TaskSettingsDefaultFileBox")
        obj.unparent()
        self.settings.register_ui("preferences_general", None, obj, 30)
        # set defaults
        main_tab = self.gui.get_object("MainTabs")

        def clear_main_tab():
            while main_tab.get_n_pages() > 0:
                main_tab.remove_page(0)

        def add_main_tab_item(item, name):
            main_tab.append_page(item, gtk.Label(name))

        # TODO: move these to plugins, as well
        self.settings.register_ui_section("main", add_main_tab_item, clear_main_tab)
        main_window = self.gui.get_object("WindowBox")

        def clear_main_window():
            main_window.foreach(main_window.remove)

        def add_main_window_item(item, name, **extra_args):
            # some widgets may want to override the defaults
            args = {"expand": False, "fill": False}
            args.update(extra_args)
            main_window.pack_start(item, **args)

        main_tab.unparent()
        self.settings.register_ui_section("main_window", add_main_window_item, clear_main_window)
        self.settings.register_ui("main_window", "Tabs", main_tab, -20,
                                  args_dict={"expand": True, "fill": True})

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
                ("ExternalProgramInkscapeAuto", "ExternalProgramInkscapeControl",
                 "ExternalProgramInkscapeBrowse", "inkscape"),
                ("ExternalProgramPstoeditAuto", "ExternalProgramPstoeditControl",
                 "ExternalProgramPstoeditBrowse", "pstoedit")):
            self.gui.get_object(auto_control_name).connect("clicked",
                                                           self._locate_external_program, key)
            location_control = self.gui.get_object(location_control_name)
            self.settings.add_item("external_program_%s" % key, location_control.get_text,
                                   location_control.set_text)
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
        for action in [aobj for aobj in self.gui.get_objects() if isinstance(aobj, gtk.Action)]:
            actiongroup.add_action(action)
        # the "pos" parameter is optional since 2.12 - we can remove it later
        uimanager.insert_action_group(actiongroup, pos=-1)
        # the "recent files" sub-menu
        if self.recent_manager is not None:
            recent_files_menu = gtk.RecentChooserMenu(self.recent_manager)
            recent_files_menu.set_name("RecentFilesMenu")
            recent_menu_filter = gtk.RecentFilter()
            case_converter = pycam.Utils.get_case_insensitive_file_pattern
            for filter_name, patterns in FILTER_MODEL:
                if not isinstance(patterns, (list, set, tuple)):
                    patterns = [patterns]
                # convert it into a mutable list (instead of set/tuple)
                patterns = list(patterns)
                for index in range(len(patterns)):
                    patterns[index] = case_converter(patterns[index])
                for pattern in patterns:
                    recent_menu_filter.add_pattern(pattern)
            recent_files_menu.add_filter(recent_menu_filter)
            recent_files_menu.set_show_numbers(True)
            # non-local files (without "file://") are not supported. yet
            recent_files_menu.set_local_only(False)
            # most recent files to the top
            recent_files_menu.set_sort_type(gtk.RECENT_SORT_MRU)
            # show only ten files
            recent_files_menu.set_limit(10)
            uimanager.get_widget("/MenuBar/FileMenu/OpenRecentModelMenu").set_submenu(
                recent_files_menu)
            recent_files_menu.connect("item-activated", self.load_recent_model_file)
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
                if action_group not in uimanager.get_action_groups():
                    uimanager.insert_action_group(action_group, -1)
                widget_name = widget.get_name()
                item_type = gtk.UI_MANAGER_MENUITEM
            else:
                widget_name = name
                item_type = gtk.UI_MANAGER_SEPARATOR
            uimanager.add_ui(merge_id, base_path, name, widget_name, item_type, False)
            if menu_key not in menu_merges:
                menu_merges[menu_key] = []
            menu_merges[menu_key].append(merge_id)

        def get_menu_funcs(menu_key, base_path):
            return (
                lambda widget, name: append_menu_item(menu_key, base_path, widget, name),
                lambda: clear_menu(menu_key)
            )

        for ui_name, base_path in (
                ("view_menu", "/MenuBar/ViewMenu"),
                ("file_menu", "/MenuBar/FileMenu"),
                ("edit_menu", "/MenuBar/EditMenu"),
                ("export_menu", "/MenuBar/FileMenu/ExportMenu")):
            append_func, clear_func = get_menu_funcs(ui_name, base_path)
            self.settings.register_ui_section(ui_name, append_func, clear_func)
        self.settings.register_ui("file_menu", "Quit", self.gui.get_object("Quit"), 100)
        self.settings.register_ui("file_menu", "QuitSeparator", None, 95)
        self.settings.register_ui("main_window", "Main", self.menubar, -100)
        self.settings.register_event("notify-file-saved", self.add_to_recent_file_list)
        self.settings.register_event("notify-file-opened", self.add_to_recent_file_list)
        # Without this "gkt.main_iteration" loop the task settings file
        # control would not be updated in time.
        while gtk.events_pending():
            gtk.main_iteration()
        self.no_dialog = no_dialog
        if not self.no_dialog:
            # register a logging handler for displaying error messages
            pycam.Utils.log.add_gtk_gui(self.window, logging.ERROR)
            self.window.show()

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
            return result
        return gui_activity_guard_wrapper

    def show_help(self, widget=None, page="Main_Page"):
        if not page.startswith("http"):
            url = DOC_BASE_URL % page
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
        title = "Select the executable for '%s'" % key
        location = self.settings.get("get_filename_func")(title=title, mode_load=True,
                                                          parent=self.preferences_window)
        if location is not None:
            self.settings.set("external_program_%s" % key, location)

    def _locate_external_program(self, widget=None, key=None):
        # the button was just activated
        location = get_external_program_location(key)
        if not location:
            log.error("Failed to locate the external program '%s'. Please install the program and "
                      "try again.%sOr maybe you need to specify the location manually.",
                      key, os.linesep)
        else:
            # store the new setting
            self.settings.set("external_program_%s" % key, location)

    @gui_activity_guard
    def toggle_about_window(self, widget=None, event=None, state=None):
        # only "delete-event" uses four arguments
        # TODO: unify all these "toggle" functions for different windows into one single function
        #       (including storing the position)
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

    def _update_undo_button(self):
        self.gui.get_object("UndoButton").set_sensitive(len(self._undo_states) > 0)

    def destroy(self, widget=None, data=None):
        gtk.main_quit()
        self.quit()

    def quit(self):
        pass
        # TODO: disabled until the format is stable
#       self.save_preferences()

    def configure_drag_and_drop(self, obj):
        obj.connect("drag-data-received", self.handle_data_drop)
        flags = gtk.DEST_DEFAULT_ALL
        targets = [(key, gtk.TARGET_OTHER_APP, index)
                   for index, key in enumerate(FILENAME_DRAG_TARGETS)]
        actions = (gtk.gdk.ACTION_COPY | gtk.gdk.ACTION_LINK | gtk.gdk.ACTION_DEFAULT
                   | gtk.gdk.ACTION_PRIVATE | gtk.gdk.ACTION_ASK)
        obj.drag_dest_set(flags, targets, actions)

    def handle_data_drop(self, widget, drag_context, x, y, selection_data, info, timestamp):
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
            detected_filetype = pycam.Importers.detect_file_type(uri, quiet=True)
            if detected_filetype:
                # looks like the file can be loaded
                if self.load_model_file(filename=detected_filetype.uri):
                    return True
        if len(uris) > 1:
            log.error("Failed to open any of the given models: %s", str(uris))
        else:
            log.error("Failed to open the model: %s", str(uris[0]))
        return False

    def load_recent_model_file(self, widget):
        uri = widget.get_current_uri()
        self.load_model_file(filename=uri)

    @gui_activity_guard
    def load_model_file(self, widget=None, filename=None, store_filename=True):
        if callable(filename):
            filename = filename()
        if not filename:
            filename = self.settings.get("get_filename_func")("Loading model ...", mode_load=True,
                                                              type_filter=FILTER_MODEL)
        if filename:
            detected_filetype = pycam.Importers.detect_file_type(filename)
            if detected_filetype:
                progress = self.settings.get("progress")
                progress.update(text="Loading model ...")
                # "cancel" is not allowed
                progress.disable_cancel()
                model = detected_filetype.importer(
                    detected_filetype.uri,
                    program_locations=get_all_program_locations(self.settings),
                    unit=self.settings.get("unit"), fonts_cache=self.settings.get("fonts"),
                    callback=progress.update)
                if self.load_model(model):
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

    def load_model(self, model):
        # load the new model only if the import worked
        if model:
            self.settings.emit_event("model-change-before")
            self.settings.get("models").add_model(model)
            self.last_model_uri = None
            return True
        else:
            return False

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
