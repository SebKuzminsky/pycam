# -*- coding: utf-8 -*-
"""
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


import pycam.Gui.ControlsGTK
import pycam.Plugins
from pycam.Toolpath import CORNER_STYLE_EXACT_PATH
import pycam.Utils.log


class ToolpathProcessors(pycam.Plugins.ListPluginBase):

    DEPENDS = ["Toolpaths", "ParameterGroupManager"]
    CATEGORIES = ["Toolpath"]
    UI_FILE = "toolpath_processors.ui"

    def setup(self):
        if self._gtk and self._gtk:
            notebook = self.gui.get_object("GCodePrefsNotebook")
            self._pref_items = []

            def clear_preferences():
                for child in notebook.get_children():
                    notebook.remove(child)
                    # we need to clear the whole path down to the "real" item
                    parent = notebook
                    while child not in [entry[0] for entry in self._pref_items]:
                        if child.get_parent():
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
                        signals = [entry[1] for entry in self._pref_items if child is entry[0]][0]
                        while signals:
                            child.disconnect(signals.pop())
                        parent.remove(child)

            def update_preference_item_visibility(widget, *args):
                """ This function takes care for hiding empty pages of the
                    notebook.
                """
                parent = args[-1]
                if parent is widget:
                    return
                if widget.get_property("visible"):
                    parent.show()
                else:
                    parent.hide()

            def add_preferences_item(item, name):
                matching_entries = [obj for obj in self._pref_items if obj[0] is item]
                if matching_entries:
                    current_entry = matching_entries[0]
                else:
                    current_entry = (item, [])
                    self._pref_items.append(current_entry)
                item.unparent()
                if not isinstance(item, self._gtk.Frame):
                    # create a simple default frame if none was given
                    frame = self._gtk.Frame(name)
                    frame.get_label_widget().set_markup("<b>%s</b>" % name)
                    frame.set_shadow_type(self._gtk.SHADOW_NONE)
                    align = self._gtk.Alignment()
                    align.set_padding(3, 0, 12, 0)
                    frame.add(align)
                    frame.show()
                    align.add(item)
                    align.show()
                    parent = frame
                else:
                    parent = item
                if not current_entry[1]:
                    for signal in ("hide", "show"):
                        current_entry[1].append(
                            item.connect(signal, update_preference_item_visibility, parent))
                notebook.append_page(parent, self._gtk.Label(name))
                update_preference_item_visibility(item, parent)

            self.core.register_ui_section("gcode_preferences", add_preferences_item,
                                          clear_preferences)
            general_widget = pycam.Gui.ControlsGTK.ParameterSection()
            general_widget.get_widget().show()
            self.core.register_ui_section("gcode_general_parameters", general_widget.add_widget,
                                          general_widget.clear_widgets)
            self.core.register_ui("gcode_preferences", "General", general_widget.get_widget())
            self._frame = self.gui.get_object("SettingsFrame")
            self.core.register_ui("toolpath_handling", "Settings", self._frame)
            self.gui.get_object("PreferencesButton").connect("clicked",
                                                             self._set_window_visibility, True)
            self.gui.get_object("CloseButton").connect("clicked", self._set_window_visibility,
                                                       False)
            self.window = self.gui.get_object("GCodePreferencesWindow")
            self.window.connect("delete-event", self._set_window_visibility, False)
            self._proc_selector = pycam.Gui.ControlsGTK.InputChoice(
                [], change_handler=lambda widget=None: self.core.emit_event(
                    "toolpath-processor-selection-changed"))
            proc_widget = self._proc_selector.get_widget()
            self._settings_section = pycam.Gui.ControlsGTK.ParameterSection()
            self._settings_section.get_widget().show()
            self.gui.get_object("SelectorsContainer").add(self._settings_section.get_widget())
            self._settings_section.add_widget(proc_widget, "Toolpath processor", weight=10)
            # TODO: it is currently not possible to switch processors (invalid dict entries are
            #       not removed)
            proc_widget.hide()
#           proc_widget.show()
            self.core.get("register_parameter_group")(
                "toolpath_processor", changed_set_event="toolpath-processor-selection-changed",
                changed_set_list_event="toolpath-processor-list-changed",
                get_current_set_func=self.get_selected)
            self._event_handlers = (
                ("toolpath-processor-list-changed", self._update_processors),
                ("toolpath-selection-changed", self._update_visibility),
                ("notify-initialization-finished", self._select_first_processor))
            self.register_event_handlers(self._event_handlers)
            self._update_processors()
            self._update_visibility()
        self.core.set("toolpath_processors", self)
        return True

    def teardown(self):
        if self.gui and self._gtk:
            self._set_window_visibility(False)
        self.core.set("toolpath_processors", None)
        self.unregister_event_handlers(self._event_handlers)
        self.core.get("unregister_parameter_group")("toolpath_processor")

    def _select_first_processor(self):
        # run this action as soon as all processors are registered
        processors = self.core.get("get_parameter_sets")("toolpath_processor").values()
        processors.sort(key=lambda item: item["weight"])
        if processors:
            self.select(processors[0])

    def get_selected(self):
        all_processors = self.core.get("get_parameter_sets")("toolpath_processor")
        current_name = self._proc_selector.get_value()
        return all_processors.get(current_name, None)

    def select(self, item=None):
        if item is not None:
            item = item["name"]
        self._proc_selector.set_value(item)

    def _update_visibility(self):
        # TODO: the gcode settings are valid for _all_ toolpaths - thus it should always be visible
        if True or self.core.get("toolpaths").get_selected():
            self._frame.show()
        else:
            self._frame.hide()

    def _update_processors(self):
        selected = self.get_selected()
        processors = self.core.get("get_parameter_sets")("toolpath_processor").values()
        processors.sort(key=lambda item: item["weight"])
        choices = []
        for processor in processors:
            choices.append((processor["label"], processor["name"]))
        self._proc_selector.update_choices(choices)
        if selected:
            self.select(selected)
        elif len(processors) > 0:
            self.select(None)
        else:
            pass

    def _set_window_visibility(self, *args):
        status = args[-1]
        if status:
            self.window.show()
        else:
            self.window.hide()
        # don't destroy the window
        return True


def _get_processor_filters(core, parameters):
    filters = []
    core.call_chain("toolpath_filters", "settings", parameters, filters)
    return filters


class ToolpathProcessorMilling(pycam.Plugins.PluginBase):

    DEPENDS = ["Toolpaths", "GCodeSafetyHeight", "GCodePlungeFeedrate", "GCodeFilenameExtension",
               "GCodeStepWidth", "GCodeSpindle", "GCodeCornerStyle"]
    CATEGORIES = ["Toolpath"]

    def setup(self):
        parameters = {"safety_height": 25,
                      "plunge_feedrate": 100,
                      "filename_extension": "",
                      "step_width_x": 0.0001,
                      "step_width_y": 0.0001,
                      "step_width_z": 0.0001,
                      "path_mode": CORNER_STYLE_EXACT_PATH,
                      "motion_tolerance": 0.0,
                      "naive_tolerance": 0.0,
                      "spindle_enable": True,
                      "spindle_delay": 3,
                      "touch_off": None}
        self.core.get("register_parameter_set")(
            "toolpath_processor", "milling", "Milling",
            lambda params: _get_processor_filters(self.core, params), parameters=parameters,
            weight=10)
        # initialize all parameters
        self.core.get("set_parameter_values")("toolpath_processor", parameters)
        return True

    def teardown(self):
        self.core.get("unregister_parameter_set")("toolpath_processor", "milling")


class ToolpathProcessorLaser(pycam.Plugins.PluginBase):

    DEPENDS = ["Toolpaths", "GCodeFilenameExtension", "GCodeStepWidth", "GCodeCornerStyle"]
    CATEGORIES = ["Toolpath"]

    def setup(self):
        parameters = {"filename_extension": "",
                      "step_width_x": 0.0001,
                      "step_width_y": 0.0001,
                      "step_width_z": 0.0001,
                      "path_mode": CORNER_STYLE_EXACT_PATH,
                      "motion_tolerance": 0.0,
                      "naive_tolerance": 0.0}
        self.core.get("register_parameter_set")(
            "toolpath_processor", "laser", "Laser",
            lambda params: _get_processor_filters(self.core, params), parameters=parameters,
            weight=50)
        # initialize all parameters
        self.core.get("set_parameter_values")("toolpath_processor", parameters)
        return True

    def teardown(self):
        self.core.get("unregister_parameter_set")("toolpath_processor", "laser")
