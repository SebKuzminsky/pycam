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
import pycam.Plugins


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
        return True

    def teardown(self):
        pass
