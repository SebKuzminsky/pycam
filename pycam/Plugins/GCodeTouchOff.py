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


class GCodeTouchOff(pycam.Plugins.PluginBase):

    DEPENDS = ["ToolpathProcessors"]
    CATEGORIES = ["GCode"]
    UI_FILE = "gcode_touch_off.ui"

    def setup(self):
        if self.gui:
            self.box = self.gui.get_object("TouchOffBox")
            self.box.unparent()
            self.core.register_ui("gcode_preferences", "Touch Off",
                    self.box, weight=70)
            self._gtk_handlers = []
            for objname in ("GCodeTouchOffOnStartup",
                    "GCodeTouchOffOnToolChange"):
                obj = self.gui.get_object(objname)
                self._gtk_handlers.append((obj, "toggled", self.update_widgets))
            selector = self.gui.get_object("TouchOffLocationSelector")
            self._gtk_handlers.append((selector, "changed",
                    self.update_widgets))
            selector.set_active(0)
            self.register_gtk_handlers(self._gtk_handlers)
            self.update_widgets()
        return True

    def teardown(self):
        if self.gui:
            self.core.unregister_ui("gcode_preferences",
                    self.gui.get_object("TouchOffBox"))
            self.unregister_gtk_handlers(self._gtk_handlers)
            self.core.get("unregister_parameter")("toolpath_processor",
                    "touch_off", self.box)

    def update_widgets(self, widget=None):
        # tool change controls
        pos_control = self.gui.get_object("TouchOffLocationSelector")
        tool_change_pos_model = pos_control.get_model()
        active_pos_index = pos_control.get_active()
        if active_pos_index < 0:
            pos_key = None
        else:
            pos_key = tool_change_pos_model[active_pos_index][0]
        # disable/enable the touch off position controls
        position_controls_table = self.gui.get_object("TouchOffLocationTable")
        touch_off_enabled = any([self.gui.get_object(objname).get_active()
                for objname in ("GCodeTouchOffOnStartup",
                    "GCodeTouchOffOnToolChange")])
        position_controls_table.set_sensitive(touch_off_enabled)
        # show or hide the vbox containing the absolute tool change location
        absolute_pos_box = self.gui.get_object("AbsoluteToolChangePositionBox")
        if (pos_key == "absolute") and touch_off_enabled:
            absolute_pos_box.show()
        else:
            absolute_pos_box.hide()
        # disable/enable touch probe height
        if self.gui.get_object("GCodeTouchOffOnStartup").get_active():
            update_func = "show"
        else:
            update_func = "hide"
        for objname in ("TouchOffHeight", "TouchOffHeightLabel",
                "LengthUnitTouchOffHeight"):
            getattr(self.gui.get_object(objname), update_func)()

