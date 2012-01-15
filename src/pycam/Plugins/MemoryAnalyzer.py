# -*- coding: utf-8 -*-
"""
$Id$

Copyright 2012 Lars Kruse <devel@sumpfralle.de>

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


import guppy

import pycam.Plugins


class MemoryAnalyzer(pycam.Plugins.PluginBase):

    UI_FILE = "memory_analyzer.ui"
    DEPENDS = []
    CATEGORIES = ["System"]

    def setup(self):
        if self.gui:
            import gtk
            self._gtk = gtk
            # menu item and shortcut
            self.toggle_action = self.gui.get_object("ToggleMemoryAnalyzerAction")
            self._gtk_handlers = []
            self._gtk_handlers.append((self.toggle_action, "toggled",
                    self.toggle_window))
            self.register_gtk_accelerator("memory_analyzer", self.toggle_action,
                    None, "ToggleMemoryAnalyzerAction")
            self.core.register_ui("view_menu", "ToggleMemoryAnalyzerAction",
                    self.toggle_action, 80)
            # the window
            self.window = self.gui.get_object("MemoryAnalyzerWindow")
            self.window.set_default_size(500, 400)
            hide_window = lambda *args: self.toggle_window(value=False)
            self._gtk_handlers.extend([
                    (self.window, "delete-event", hide_window),
                    (self.window, "destroy", hide_window),
                    (self.gui.get_object("MemoryAnalyzerCloseButton"),
                            "clicked", hide_window),
                    (self.gui.get_object("MemoryAnalyzerRefreshButton"),
                            "clicked", self.refresh_memory_analyzer)])
            self.model = self.gui.get_object("MemoryAnalyzerModel")
            # window state
            self._window_position = None
            self.register_gtk_handlers(self._gtk_handlers)
        return True

    def teardown(self):
        if self.gui:
            self.window.hide()
            self.core.unregister_ui("view_menu", self.toggle_action)
            self.unregister_gtk_accelerator("memory_analyzer",
                    self.toggle_action)
            self.core.unregister_ui("view_menu", self.toggle_action)
            self.unregister_gtk_handlers(self._gtk_handlers)

    def toggle_window(self, widget=None, value=None, action=None):
        checkbox_state = self.toggle_action.get_active()
        if value is None:
            new_state = checkbox_state
        elif action is None:
            new_state = value
        else:
            new_state = action
        if new_state:
            if self._window_position:
                self.window.move(*self._window_position)
            self.refresh_memory_analyzer()
            self.window.show()
        else:
            self._window_position = self.window.get_position()
            self.window.hide()
        self.toggle_action.set_active(new_state)
        # don't destroy the window with a "destroy" event
        return True

    def refresh_memory_analyzer(self, widget=None):
        memory_state = guppy.hpy().heap()
        self.model.clear()
        for row in memory_state.stat.get_rows():
            item = (row.name, row.count, row.size / 1024, row.size / row.count)
            self.model.append(item)

