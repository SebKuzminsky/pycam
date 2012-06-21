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


import pycam.Plugins
import pycam.Gui.ControlsGTK
import pycam.Utils.log


_log = pycam.Utils.log.get_logger()


class ToolpathProcessors(pycam.Plugins.ListPluginBase):

    DEPENDS = ["ParameterGroupManager"]
    CATEGORIES = ["Toolpath"]
    UI_FILE = "toolpath_processors.ui"

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
            general_widget.get_widget().show()
            self.core.register_ui_section("gcode_general_parameters",
                    general_widget.add_widget, general_widget.clear_widgets)
            self.core.register_ui("gcode_preferences", "General",
                    general_widget.get_widget())
            self._controls_hbox = self.gui.get_object("PreferencesControls")
            self.core.register_ui("toolpath_handling", "Settings",
                    self._controls_hbox)
            self.gui.get_object("PreferencesButton").connect("clicked",
                    self._toggle_window, True)
            self.gui.get_object("CloseButton").connect("clicked",
                    self._toggle_window, False)
            self.window = self.gui.get_object("GCodePreferencesWindow")
            self.window.connect("delete-event", self._toggle_window, False)
            self._proc_selector = pycam.Gui.ControlsGTK.InputChoice([],
                    change_handler=lambda widget=None: \
                            self.core.emit_event(
                                "toolpath-processor-selection-changed"))
            proc_widget = self._proc_selector.get_widget()
            self._controls_hbox.pack_start(proc_widget, expand=False)
            self._controls_hbox.reorder_child(proc_widget, 0)
            proc_widget.show()
            self.core.get("register_parameter_group")("toolpath_processor",
                    changed_set_event="toolpath-processor-selection-changed",
                    changed_set_list_event="toolpath-processor-list-changed",
                    get_current_set_func=self.get_selected)
            self._event_handlers = (
                    ("toolpath-processor-list-changed", self._update_processors),
                    ("toolpath-processor-selection-changed", self._update_visibility),
            )
            self.register_event_handlers(self._event_handlers)
            self._update_processors()
        return True

    def teardown(self):
        if self.gui:
            self._toggle_window(False)
        self.unregister_event_handlers(self._event_handlers)
        self.core.get("unregister_parameter_group")("toolpath_processor")

    def get_selected(self):
        all_processors = self.core.get("get_parameter_sets")("toolpath_processor")
        current_name = self._proc_selector.get_value()
        return all_processors.get(current_name, None)

    def select(self, item=None):
        if not item is None:
            item = item["name"]
        self._proc_selector.set_value(item)

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

    def _update_visibility(self):
        # Go through all children and hide the respective containers
        # if all their children are invisible.
        #TODO: this is an ugly hack. It fails to re-enable checkboxes (spindle_enable).
        #      We should use another path ...
        import gtk
        notebook = self.gui.get_object("GCodePrefsNotebook")
        def hide_empty_container(container):
            found_visible = False
            for child in container.get_children():
                if isinstance(child, gtk.Label):
                    continue
                # check containers (except for tables, comboboxes, ...)
                if (hasattr(child, "get_children") and \
                        not hasattr(child, "get_model")):
                    hide_empty_container(child)
                if child.get_property("visible"):
                    found_visible = True
            if found_visible:
                container.show()
                return False
            else:
                container.hide()
                return True
        hide_empty_container(notebook)

    def _toggle_window(self, *args):
        status = args[-1]
        if status:
            self.window.show()
        else:
            self.window.hide()
        # don't destroy the window
        return True


class ToolpathProcessorMilling(pycam.Plugins.PluginBase):

    DEPENDS = ["Toolpaths", "GCodeSafetyHeight", "GCodeFilenameExtension",
            "GCodeStepWidth", "GCodeSpindle", "GCodeCornerStyle"]
    CATEGORIES = ["Toolpath"]

    def setup(self):
        parameters = {"safety_height": 25,
                "filename_extension": "",
                "step_width_x": 0.0001,
                "step_width_y": 0.0001,
                "step_width_z": 0.0001,
                "path_mode": "exact_path",
                "motion_tolerance": 0.0,
                "naive_tolerance": 0.0,
                "spindle_enable": True,
                "spindle_delay": 3,
        }
        self.core.get("register_parameter_set")("toolpath_processor",
                "milling", "Milling", self.get_filters, parameters=parameters,
                weight=10)
        return True

    def teardown(self):
        self.core.get("unregister_parameter_set")("toolpath_processor", 
                "milling")

    def get_filters(self):
        return []


class ToolpathProcessorLaser(pycam.Plugins.PluginBase):

    DEPENDS = ["Toolpaths", "GCodeFilenameExtension", "GCodeStepWidth",
            "GCodeCornerStyle"]
    CATEGORIES = ["Toolpath"]

    def setup(self):
        parameters = {"filename_extension": "",
                "step_width_x": 0.0001,
                "step_width_y": 0.0001,
                "step_width_z": 0.0001,
        }
        self.core.get("register_parameter_set")("toolpath_processor",
                "laser", "Laser", self.get_filters, parameters=parameters,
                weight=50)
        return True

    def teardown(self):
        self.core.get("unregister_parameter_set")("toolpath_processor",
                "laser")

    def get_filters(self):
        return []

