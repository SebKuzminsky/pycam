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

import pycam.Plugins


class Units(pycam.Plugins.PluginBase):

    UI_FILE = "units.ui"
    CATEGORIES = ["System"]

    def setup(self):
        if self.gui:
            self._gtk_handlers = []
            unit_pref_box = self.gui.get_object("UnitPrefBox")
            unit_pref_box.unparent()
            self.core.register_ui("preferences_general", "Units", unit_pref_box, 20)
            # unit control (mm/inch)
            unit_field = self.gui.get_object("unit_control")
            self._gtk_handlers.append((unit_field, "changed", self.change_unit_init))

            def set_unit(text):
                unit_field.set_active(0 if text == "mm" else 1)
                self._last_unit = text

            self.core.add_item("unit", unit_field.get_active_text, set_unit)
            # other plugins should use "unit_string" for human readable output
            self.core.add_item("unit_string", unit_field.get_active_text)
            self.register_gtk_handlers(self._gtk_handlers)
        self.register_state_item("settings/unit", lambda: self.core.get("unit"),
                                 lambda value: self.core.set("unit", value))
        return True

    def teardown(self):
        self.clear_state_items()
        if self.gui:
            self.core.unregister_ui("preferences_general", self.gui.get_object("UnitPrefBox"))
            self.unregister_gtk_handlers(self._gtk_handlers)
            # TODO: reset setting "unit" back to a default value?

    def change_unit_init(self, widget=None):
        self.gui.get_object("unit_control").get_active_text()
        # redraw the model
        self.core.emit_event("model-change-after")
