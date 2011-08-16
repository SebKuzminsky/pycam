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
import pycam.Gui.ControlsGTK


class GCodePreferences(pycam.Plugins.PluginBase):

    DEPENDS = []
    CATEGORIES = ["GCode"]
    UI_FILE = "gcode_preferences.ui"

    def setup(self):
        if self.gui:
            import gtk
            notebook = self.gui.get_object("GCodePrefsNotebook")
            def clear_preferences():
                for child in notebook.get_children():
                    notebook.remove(child)
            def add_preferences_item(item, name):
                if not isinstance(item, gtk.Frame):
                    # create a simple default frame if none was given
                    frame = gtk.Frame(name)
                    frame.get_label_widget().set_markup("<b>%s</b>" % name)
                    frame.set_shadow_type(gtk.SHADOW_NONE)
                    align = gtk.Alignment()
                    align.set_padding(5, 0, 12, 0)
                    frame.add(align)
                    frame.show()
                    item.unparent()
                    align.add(item)
                    align.show()
                    item = frame
                notebook.append_page(item, gtk.Label(name))
                notebook.show_all()
            self.core.register_ui_section("gcode_preferences",
                    add_preferences_item, clear_preferences)
            general_widget = pycam.Gui.ControlsGTK.ParameterSection()
            general_widget.widget.show()
            self.core.register_ui_section("gcode_general_parameters",
                    general_widget.add_widget, general_widget.clear_widgets)
            self.core.register_ui("gcode_preferences", "General",
                    general_widget.widget)
            self.core.register_ui("toolpath_handling", "Settings",
                    self.gui.get_object("PreferencesControls"))
            self.gui.get_object("PreferencesButton").connect("clicked",
                    self._toggle_window, True)
            self.gui.get_object("CloseButton").connect("clicked",
                    self._toggle_window, False)
            self.window = self.gui.get_object("GCodePreferencesWindow")
            self.window.connect("delete-event", self._toggle_window, False)
        return True

    def teardown(self):
        if self.gui:
            self._toggle_window(False)

    def _toggle_window(self, *args):
        status = args[-1]
        if status:
            self.window.show()
        else:
            self.window.hide()
        # don't destroy the window
        return True


class GCodeSafetyHeight(pycam.Plugins.PluginBase):

    DEPENDS = ["GCodePreferences"]
    CATEGORIES = ["GCode"]

    def setup(self):
        self.safety_height = pycam.Gui.ControlsGTK.InputNumber(digits=0,
                change_handler=lambda *args: \
                    self.core.emit_event("visual-item-updated"))
        self.core.register_ui("gcode_general_parameters", "Safety Height",
                self.safety_height.get_widget(), weight=20)
        # TODO: this should be done via parameter groups based on postprocessors
        self.safety_height.get_widget().show()
        self.core.add_item("gcode_safety_height",
                self.safety_height.get_value, self.safety_height.set_value)
        return True

    def teardown(self):
        self.core.add_item("gcode_safety_height", lambda value: None,
                lambda: None)
        self.safety_height.destroy()


class GCodeFilenameExtension(pycam.Plugins.PluginBase):

    DEPENDS = ["GCodePreferences"]
    CATEGORIES = ["GCode"]

    def setup(self):
        self.filename_extension = pycam.Gui.ControlsGTK.InputString(
                max_length=6)
        self.core.register_ui("gcode_general_parameters",
                "Custom GCode filename extension",
                self.filename_extension.get_widget(), weight=80)
        # TODO: this should be done via parameter groups based on postprocessors
        self.filename_extension.get_widget().show()
        self.core.add_item("gcode_filename_extension",
                self.filename_extension.get_value,
                self.filename_extension.set_value)
        return True

    def teardown(self):
        self.core.add_item("gcode_filename_extension", lambda value: None,
                lambda: None)
        self.filename_extension.destroy()


class GCodeStepWidth(pycam.Plugins.PluginBase):

    DEPENDS = ["GCodePreferences"]
    CATEGORIES = ["GCode"]

    def setup(self):
        table = pycam.Gui.ControlsGTK.ParameterSection()
        self.core.register_ui("gcode_preferences", "Step precision",
                table.widget)
        self.core.register_ui_section("gcode_step_width",
                table.add_widget, table.clear_widgets)
        for key in "xyz":
            control = pycam.Gui.ControlsGTK.InputNumber(digits=8, start=0.0001,
                    increment=0.00005)
            self.core.add_item("gcode_minimum_step_%s" % key,
                    control.get_value, control.set_value)
            self.core.register_ui("gcode_step_width", key.upper(),
                    control.get_widget(), weight="xyz".index(key))
            # TODO: this should be done via parameter groups based on postprocessors
            control.get_widget().show()
        return True


class GCodeSpindle(pycam.Plugins.PluginBase):

    DEPENDS = ["GCodePreferences"]
    CATEGORIES = ["GCode"]

    def setup(self):
        table = pycam.Gui.ControlsGTK.ParameterSection()
        self.core.register_ui("gcode_preferences", "Spindle control",
                table.widget)
        self.core.register_ui_section("gcode_spindle",
                table.add_widget, table.clear_widgets)
        self.spindle_delay = pycam.Gui.ControlsGTK.InputNumber(digits=1)
        self.core.register_ui("gcode_spindle",
                "Delay (in seconds) after start/stop",
                self.spindle_delay.get_widget(), weight=20)
        # TODO: this should be done via parameter groups based on postprocessors
        self.spindle_delay.get_widget().show()
        self.core.add_item("gcode_spindle_delay",
                self.spindle_delay.get_value,
                self.spindle_delay.set_value)

