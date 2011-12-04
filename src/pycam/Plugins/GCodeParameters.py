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
            self._pref_items = []
            def clear_preferences():
                for child in notebook.get_children():
                    notebook.remove(child)
                    # we need to clear the whole path down to the "real" item
                    parent = notebook
                    while not child in self._pref_items:
                        parent.remove(child)
                        parent = child
                        try:
                            child = child.get_children()[0]
                        except (AttributeError, IndexError):
                            # We encountered an invalid item (e.g. a label
                            # without children) or an empty item.
                            break
                    else:
                        # we found a valid child -> remove it
                        parent.remove(child)
            def add_preferences_item(item, name):
                if not item in self._pref_items:
                    self._pref_items.append(item)
                item.unparent()
                if not isinstance(item, gtk.Frame):
                    # create a simple default frame if none was given
                    frame = gtk.Frame(name)
                    frame.get_label_widget().set_markup("<b>%s</b>" % name)
                    frame.set_shadow_type(gtk.SHADOW_NONE)
                    align = gtk.Alignment()
                    align.set_padding(3, 0, 12, 0)
                    frame.add(align)
                    frame.show()
                    align.add(item)
                    align.show()
                    item.show()
                    item = frame
                notebook.append_page(item, gtk.Label(name))
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
        # TODO: this should be done via parameter groups based on postprocessors
        self.safety_height.get_widget().show()
        self.core.register_ui("gcode_general_parameters", "Safety Height",
                self.safety_height.get_widget(), weight=20)
        self.core.add_item("gcode_safety_height",
                self.safety_height.get_value, self.safety_height.set_value)
        self.register_state_item("settings/gcode/gcode_safety_height",
                self.safety_height.get_value, self.safety_height.set_value)
        return True

    def teardown(self):
        self.clear_state_items()
        self.core.remove_item("gcode_safety_height")
        self.safety_height.destroy()


class GCodeFilenameExtension(pycam.Plugins.PluginBase):

    DEPENDS = ["GCodePreferences"]
    CATEGORIES = ["GCode"]

    def setup(self):
        self.filename_extension = pycam.Gui.ControlsGTK.InputString(
                max_length=6)
        # TODO: this should be done via parameter groups based on postprocessors
        self.filename_extension.get_widget().show()
        self.core.register_ui("gcode_general_parameters",
                "Custom GCode filename extension",
                self.filename_extension.get_widget(), weight=80)
        self.core.add_item("gcode_filename_extension",
                self.filename_extension.get_value,
                self.filename_extension.set_value)
        return True

    def teardown(self):
        self.core.remove_item("gcode_filename_extension")
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
        self.controls = []
        for key in "xyz":
            control = pycam.Gui.ControlsGTK.InputNumber(digits=8, start=0.0001,
                    increment=0.00005)
            # TODO: this should be done via parameter groups based on postprocessors
            name = "gcode_minimum_step_%s" % key
            control.get_widget().show()
            self.core.add_item(name, control.get_value, control.set_value)
            self.core.register_ui("gcode_step_width", key.upper(),
                    control.get_widget(), weight="xyz".index(key))
            self.register_state_item("settings/gcode/%s" % name,
                    control.get_value, control.set_value)
            self.controls.append(control)
        return True

    def teardown(self):
        self.clear_state_items()
        while self.controls:
            self.core.unregister_ui("gcode_step_width", self.controls.pop())
        for key in "xyz":
            self.core.remove_item("gcode_minimum_step_%s" % key)

class GCodeSpindle(pycam.Plugins.PluginBase):

    DEPENDS = ["GCodePreferences"]
    CATEGORIES = ["GCode"]

    def setup(self):
        self._table = pycam.Gui.ControlsGTK.ParameterSection()
        self.core.register_ui("gcode_preferences", "Spindle control",
                self._table.widget)
        self.core.register_ui_section("gcode_spindle",
                self._table.add_widget, self._table.clear_widgets)
        self.spindle_delay = pycam.Gui.ControlsGTK.InputNumber(digits=1)
        # TODO: this should be done via parameter groups based on postprocessors
        self.spindle_delay.get_widget().show()
        self.core.register_ui("gcode_spindle",
                "Delay (in seconds) after start/stop",
                self.spindle_delay.get_widget(), weight=50)
        self.core.add_item("gcode_spindle_delay",
                self.spindle_delay.get_value,
                self.spindle_delay.set_value)
        self.spindle_enable = pycam.Gui.ControlsGTK.InputCheckBox(
                change_handler=self.update_widgets)
        self.spindle_enable.get_widget().show()
        self.core.register_ui("gcode_spindle", "Start / Stop Spindle (M3/M5)",
                self.spindle_enable.get_widget(), weight=10)
        self.update_widgets()
        return True

    def teardown(self):
        self.core.remove_item("gcode_spindle_delay")
        self.core.unregister_ui("gcode_spindle",
                self.spindle_delay.get_widget())
        self.core.unregister_ui("gcode_spindle",
                self.spindle_enable.get_widget())
        self.core.unregister_ui_section("gcode_spindle")
        self.core.unregister_ui("gcode_preferences", self._table.widget)

    def update_widgets(self, widget=None):
        widget = self.spindle_delay.get_widget()
        widget.set_sensitive(self.spindle_enable.get_value())


class GCodeCornerStyle(pycam.Plugins.PluginBase):

    DEPENDS = ["GCodePreferences"]
    CATEGORIES = ["GCode"]

    def setup(self):
        table = pycam.Gui.ControlsGTK.ParameterSection()
        self.core.register_ui("gcode_preferences", "Corner style",
                table.widget)
        self.core.register_ui_section("gcode_corner_style",
                table.add_widget, table.clear_widgets)
        self.motion_tolerance = pycam.Gui.ControlsGTK.InputNumber(digits=3)
        # TODO: this should be done via parameter groups based on postprocessors
        self.motion_tolerance.get_widget().show()
        self.core.register_ui("gcode_corner_style", "Motion blending tolerance",
                self.motion_tolerance.get_widget(), weight=30)
        self.naive_tolerance = pycam.Gui.ControlsGTK.InputNumber(digits=3)
        self.naive_tolerance.get_widget().show()
        self.core.register_ui("gcode_corner_style", "Naive CAM tolerance",
                self.naive_tolerance.get_widget(), weight=50)
        self.path_mode = pycam.Gui.ControlsGTK.InputChoice((
                ("Exact path mode (G61)", "exact_path"),
                ("Exact stop mode (G61.1)", "exact_stop"),
                ("Continuous with maximum speed (G64)", "optimize_speed"),
                ("Continuous with tolerance (G64 P/Q)", "optimize_tolerance")))
        self.path_mode.get_widget().connect("changed", self.update_widgets)
        self.core.register_ui("gcode_corner_style", "Path mode",
                self.path_mode.get_widget(), weight=10)
        table.widget.show_all()
        self.update_widgets()
        return True

    def teardown(self):
        self.core.unregister_ui("gcode_corner_style",
                self.motion_tolerance.get_widget())
        self.core.unregister_ui("gcode_corner_style",
                self.naive_tolerance.get_widget())
        self.core.unregister_ui("gcode_corner_style",
                self.path_mode.get_widget())
        self.core.unregister_ui_section("gcode_corner_style")

    def update_widgets(self, widget=None):
        enable_tolerances = (self.path_mode.get_value() == "optimize_speed")
        controls = (self.motion_tolerance, self.naive_tolerance)
        for control in controls:
            control.get_widget().set_sensitive(enable_tolerances)

