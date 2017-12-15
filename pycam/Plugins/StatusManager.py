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

from pycam import FILTER_CONFIG
from pycam.Flow.parser import dump_yaml, parse_yaml
import pycam.Plugins
from pycam.Utils.locations import open_file_context


class StatusManager(pycam.Plugins.PluginBase):

    CATEGORIES = ["System"]

    def setup(self):
        if self.gui:
            # autoload task settings file on startup
            autoload_enable = self.gui.get_object("AutoLoadTaskFile")
            autoload_box = self.gui.get_object("StartupTaskFileBox")
            autoload_source = self.gui.get_object("StartupTaskFile")
            # TODO: fix the extension filter
#           for one_filter in get_filters_from_list(FILTER_CONFIG):
#               autoload_source.add_filter(one_filter)
#               autoload_source.set_filter(one_filter)

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

            autoload_enable.connect("toggled", autoload_enable_switched, autoload_box)
            self.core.settings.add_item("default_task_settings_file", get_autoload_task_file,
                                        set_autoload_task_file)
            autoload_task_filename = self.core.settings.get("default_task_settings_file")
            # TODO: use "startup" hook instead
            if autoload_task_filename:
                self.open_project_settings_file(autoload_task_filename, remember_uri=False)
            self._gtk_handlers = []
            for objname, callback, data, accel_key in (
                    ("LoadProjectSettings", self.load_project_settings_dialog, None, "<Control>t"),
                    ("SaveProjectSettings", self.save_task_settings_file,
                     lambda: self.last_project_settings_uri, None),
                    ("SaveAsProjectSettings", self.save_task_settings_file, None, None)):
                obj = self.gui.get_object(objname)
                self.register_gtk_accelerator("status_manager", obj, accel_key, objname)
                self._gtk_handlers.append((obj, "activate", callback))
            self.register_gtk_handlers(self._gtk_handlers)
        return True

    def teardown(self):
        if self.gui:
            self.unregister_gtk_handlers(self._gtk_handlers)

    def load_project_settings_dialog(self, widget=None, filename=None):
        if callable(filename):
            filename = filename()
        if not filename:
            filename = self.core.settings.get("get_filename_func")("Loading project settings ...",
                                                                   mode_load=True,
                                                                   type_filter=FILTER_CONFIG)
            remember_uri = True
        else:
            # we were called via "save" (instead of "save as ...") - no need to store the URI
            remember_uri = False
        if filename:
            self.log.info("Loading task settings file: %s", filename)
            self.load_project_setttings_from_file(filename, remember_uri=remember_uri)
            self.core.emit_event("notify-file-opened", filename)

    def load_project_setttings_from_file(self, filename, remember_uri=True):
        if remember_uri:
            self.last_project_settings_uri = pycam.Utils.URIHandler(filename)
        try:
            with open(filename, "r") as in_file:
                content = in_file.read()
        except OSError as exc:
            self.log.error("Failed to read project settings file (%s): %s", filename, exc)
        parse_yaml(content, reset=True)

    def save_task_settings_file(self, widget=None, filename=None):
        if callable(filename):
            filename = filename()
        if not hasattr(filename, "split") and not isinstance(filename, pycam.Utils.URIHandler):
            # we open a dialog
            filename = self.core.settings.get("get_filename_func")(
                "Save settings to ...", mode_load=False, type_filter=FILTER_CONFIG,
                filename_templates=(self.last_project_settings_uri, self.core.last_model_uri))
            if filename:
                self.last_project_settings_uri = pycam.Utils.URIHandler(filename)
        # no filename given -> exit
        if not filename:
            return
        try:
            with open_file_context(filename, "w", True) as out_file:
                dump_yaml(target=out_file,
                          sections={"models", "tools", "processes", "bounds", "tasks"})
        except OSError as exc:
            self.log.error("Failed to save project settings file: %s", exc)
            out_file.close()
            self.log.info("Project settings written to %s", filename)
            self.core.emit_event("notify-file-opened", filename)
