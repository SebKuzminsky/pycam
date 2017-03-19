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
from pycam.Utils import get_non_conflicting_name


class Processes(pycam.Plugins.ListPluginBase):

    DEPENDS = ["ParameterGroupManager"]
    CATEGORIES = ["Process"]
    UI_FILE = "processes.ui"

    def setup(self):
        self.core.set("processes", self)
        if self.gui and self._gtk:
            process_frame = self.gui.get_object("ProcessBox")
            process_frame.unparent()
            self._gtk_handlers = []
            self.core.register_ui("main", "Processes", process_frame, weight=20)
            self._modelview = self.gui.get_object("ProcessEditorTable")
            self.set_gtk_modelview(self._modelview)
            self.register_model_update(lambda: self.core.emit_event("process-list-changed"))
            for action, obj_name in ((self.ACTION_UP, "ProcessMoveUp"),
                                     (self.ACTION_DOWN, "ProcessMoveDown"),
                                     (self.ACTION_DELETE, "ProcessDelete")):
                self.register_list_action_button(action, self.gui.get_object(obj_name))
            self._gtk_handlers.append((self.gui.get_object("ProcessNew"), "clicked",
                                       self._process_new))
            # parameters
            parameters_box = self.gui.get_object("ProcessParametersBox")

            def clear_parameter_widgets():
                parameters_box.foreach(parameters_box.remove)

            def add_parameter_widget(item, name):
                # create a frame with an align and the item inside
                if item.get_parent():
                    item.unparent()
                frame_label = self._gtk.Label()
                frame_label.set_markup("<b>%s</b>" % name)
                frame = self._gtk.Frame()
                frame.set_label_widget(frame_label)
                align = self._gtk.Alignment()
                frame.add(align)
                align.set_padding(0, 3, 12, 3)
                align.add(item)
                frame.show_all()
                parameters_box.pack_start(frame, expand=False)

            self.core.register_ui_section("process_parameters", add_parameter_widget,
                                          clear_parameter_widgets)
            self.core.get("register_parameter_group")(
                "process", changed_set_event="process-strategy-changed",
                changed_set_list_event="process-strategy-list-changed",
                get_current_set_func=self._get_strategy)
            self.parameter_widget = pycam.Gui.ControlsGTK.ParameterSection()
            self.core.register_ui_section("process_path_parameters",
                                          self.parameter_widget.add_widget,
                                          self.parameter_widget.clear_widgets)
            self.core.register_ui("process_parameters", "Path parameters",
                                  self.parameter_widget.get_widget(), weight=10)
            self._gtk_handlers.append((self._modelview.get_selection(), "changed",
                                       "process-selection-changed"))
            self._gtk_handlers.append((self.gui.get_object("NameCell"), "edited",
                                       self._edit_process_name))
            self._treemodel = self.gui.get_object("ProcessList")
            self._treemodel.clear()
            self._gtk_handlers.append((self.gui.get_object("StrategySelector"), "changed",
                                       "process-strategy-changed"))
            self._event_handlers = (
                ("process-strategy-list-changed", self._update_widgets),
                ("process-list-changed", self._trigger_table_update),
                ("process-selection-changed", self._process_switch),
                ("process-changed", self._store_process_settings),
                ("process-strategy-changed", self._store_process_settings))
            self.register_gtk_handlers(self._gtk_handlers)
            self.register_event_handlers(self._event_handlers)
        self.register_state_item("processes", self)
        self.core.register_namespace("processes", pycam.Plugins.get_filter(self))
        return True

    def teardown(self):
        self.clear_state_items()
        self.core.unregister_namespace("processes")
        if self.gui and self._gtk:
            self.core.unregister_ui("main", self.gui.get_object("ProcessBox"))
            self.core.unregister_ui_section("process_path_parameters")
            self.core.unregister_ui("process_parameters", self.parameter_widget.get_widget())
            self.core.unregister_ui_section("process_parameters")
            self.unregister_gtk_handlers(self._gtk_handlers)
            self.unregister_event_handlers(self._event_handlers)
        self.core.set("processes", None)
        while len(self) > 0:
            self.pop()
        return True

    def _render_process_description(self, column, cell, model, m_iter):
        # TODO: describe the strategy
        text = "TODO"
#       process = self.get_by_path(model.get_path(m_iter))
        cell.set_property("text", text)

    def _render_process_name(self, column, cell, model, m_iter):
        process = self.get_by_path(model.get_path(m_iter))
        cell.set_property("text", process["name"])

    def _edit_process_name(self, cell, path, new_text):
        process = self.get_by_path(path)
        if process and (new_text != process["name"]) and new_text:
            process["name"] = new_text
            self.core.emit_event("process-list-changed")

    def _trigger_table_update(self):
        self.gui.get_object("NameColumn").set_cell_data_func(
            self.gui.get_object("NameCell"), self._render_process_name)
        self.gui.get_object("DescriptionColumn").set_cell_data_func(
            self.gui.get_object("DescriptionCell"), self._render_process_description)

    def _update_widgets(self):
        selected = self._get_strategy()
        model = self.gui.get_object("StrategyModel")
        model.clear()
        strategies = list(self.core.get("get_parameter_sets")("process").values())
        strategies.sort(key=lambda item: item["weight"])
        for strategy in strategies:
            model.append((strategy["label"], strategy["name"]))
        # check if any on the processes became obsolete due to a missing plugin
        removal = []
        strat_names = [strat["name"] for strat in strategies]
        for index, process in enumerate(self):
            if not process["strategy"] in strat_names:
                removal.append(index)
        removal.reverse()
        for index in removal:
            self.pop(index)
        # show "new" only if a strategy is available
        self.gui.get_object("ProcessNew").set_sensitive(len(model) > 0)
        selector_box = self.gui.get_object("ProcessSelectorBox")
        if len(model) < 2:
            selector_box.hide()
        else:
            selector_box.show()
        if selected:
            self.select_strategy(selected["name"])

    def _get_strategy(self, name=None):
        strategies = self.core.get("get_parameter_sets")("process")
        if name is None:
            # find the currently selected one
            selector = self.gui.get_object("StrategySelector")
            model = selector.get_model()
            index = selector.get_active()
            if index < 0:
                return None
            strategy_name = model[index][1]
        else:
            strategy_name = name
        if strategy_name in strategies:
            return strategies[strategy_name]
        else:
            return None

    def select_strategy(self, name):
        selector = self.gui.get_object("StrategySelector")
        for index, row in enumerate(selector.get_model()):
            if row[1] == name:
                selector.set_active(index)
                break
        else:
            selector.set_active(-1)

    def _store_process_settings(self):
        process = self.get_selected()
        control_box = self.gui.get_object("ProcessSettingsControlsBox")
        strategy = self._get_strategy()
        if process is None or strategy is None:
            control_box.hide()
        else:
            # Check if any of the relevant controls are still at their default
            # values for this process type. These values are overridden by the
            # default value of the new (changed) process type.
            # E.g. this changes the "overlap" value from 10 to 60 when
            # switching from slicing to surfacing.
            if process["strategy"] \
                    and process["strategy"] in self.core.get("get_parameter_sets")("process"):
                old_strategy = self.core.get("get_parameter_sets")("process")[process["strategy"]]
                if process["strategy"] != strategy["name"]:
                    changes = {}
                    common_keys = [key for key in old_strategy["parameters"]
                                   if key in strategy["parameters"]]
                    for key in common_keys:
                        if process["parameters"][key] == old_strategy["parameters"][key]:
                            changes[key] = strategy["parameters"][key]
                        self.core.get("set_parameter_values")("process", changes)
            process["strategy"] = strategy["name"]
            parameters = process["parameters"]
            parameters.update(self.core.get("get_parameter_values")("process"))
            control_box.show()
            self._trigger_table_update()

    def _process_switch(self, widget=None, data=None):
        process = self.get_selected()
        control_box = self.gui.get_object("ProcessSettingsControlsBox")
        if not process:
            control_box.hide()
        else:
            self.core.block_event("process-changed")
            self.core.block_event("process-strategy-changed")
            strategy_name = process["strategy"]
            self.select_strategy(strategy_name)
            self.core.get("set_parameter_values")("process", process["parameters"])
            control_box.show()
            self.core.unblock_event("process-strategy-changed")
            self.core.unblock_event("process-changed")
            self.core.emit_event("process-strategy-changed")
            self.core.emit_event("process-changed")

    def _process_new(self, *args):
        strategies = self.core.get("get_parameter_sets")("process").values()
        strategies.sort(key=lambda item: item["weight"])
        strategy = strategies[0]
        name = get_non_conflicting_name("Process #%d", [process["name"] for process in self])
        new_process = ProcessEntity({"strategy": strategy["name"],
                                     "parameters": strategy["parameters"].copy(),
                                     "name": name})
        self.append(new_process)
        self.select(new_process)


class ProcessEntity(pycam.Plugins.ObjectWithAttributes):

    def __init__(self, parameters):
        super(ProcessEntity, self).__init__("process", parameters)
