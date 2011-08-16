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

    DEPENDS = ["GCodePreferences"]
    CATEGORIES = ["GCode"]
    UI_FILE = "gcode_touch_off.ui"

    def setup(self):
        if self.gui:
            box = self.gui.get_object("TouchOffBox")
            box.unparent()
            self.core.register_ui("gcode_preferences", "Touch Off",
                    box, weight=70)
            for objname, setting in (
                    ("GCodeTouchOffOnStartup", "touch_off_on_startup"),
                    ("GCodeTouchOffOnToolChange", "touch_off_on_tool_change")):
                self.gui.get_object(objname).connect("toggled",
                        self.update_widgets)
            self.gui.get_object("TouchOffLocationSelector").connect("changed",
                    self.update_widgets)
            self.gui.get_object("TouchOffLocationSelector").set_active(0)
            self.update_widgets()
        return True

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

