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


class Processes(pycam.Plugins.ListPluginBase):

    DEPENDS = ["ParameterGroupManager"]

    UI_FILE = "processes.ui"
    COLUMN_REF, COLUMN_NAME = range(2)
    LIST_ATTRIBUTE_MAP = {"ref": COLUMN_REF, "name": COLUMN_NAME}

    def setup(self):
        if self.gui:
            import gtk
            self._gtk = gtk
            process_frame = self.gui.get_object("ProcessBox")
            process_frame.unparent()
            self.core.register_ui("main", "Processs", process_frame, weight=20)
            self._modelview = self.gui.get_object("ProcessEditorTable")
            for action, obj_name in ((self.ACTION_UP, "ProcessMoveUp"),
                    (self.ACTION_DOWN, "ProcessMoveDown"),
                    (self.ACTION_DELETE, "ProcessDelete")):
                self.register_list_action_button(action, self._modelview,
                        self.gui.get_object(obj_name))
            self.gui.get_object("ProcessNew").connect("clicked",
                    self._process_new)
            # parameters
            parameters_box = self.gui.get_object("ProcessParametersBox")
            def clear_parameter_widgets():
                parameters_box.foreach(
                        lambda widget: parameters_box.remove(widget))
            def add_parameter_widget(item, name):
                # create a frame with an align and the item inside
                frame_label = gtk.Label()
                frame_label.set_markup("<b>%s</b>" % name)
                frame = gtk.Frame()
                frame.set_label_widget(frame_label)
                align = gtk.Alignment()
                frame.add(align)
                align.set_padding(0, 3, 12, 3)
                align.add(item)
                frame.show_all()
                parameters_box.pack_start(frame, expand=False)
            self.core.register_ui_section("process_parameters",
                    add_parameter_widget, clear_parameter_widgets)
            self.core.get("register_parameter_group")("process",
                    changed_set_event="process-strategy-changed",
                    changed_set_list_event="process-strategy-list-changed",
                    get_current_set_func=self._get_strategy)
            parameter_widget = self.core.get("register_parameter_section")(
                    "process", "pathgenerator")
            self.core.register_ui("process_parameters", "Path parameters",
                    parameter_widget, weight=10)
            selection = self._modelview.get_selection()
            selection.connect("changed", 
                    lambda widget, event: self.core.emit_event(event),
                    "process-selection-changed")
            self.gui.get_object("NameCell").connect("edited",
                    self._edit_process_name)
            self._treemodel = self.gui.get_object("ProcessList")
            self._treemodel.clear()
            def update_model():
                if not hasattr(self, "_model_cache"):
                    self._model_cache = {}
                cache = self._model_cache
                for row in self._treemodel:
                    cache[row[self.COLUMN_REF]] = list(row)
                self._treemodel.clear()
                for index, item in enumerate(self):
                    if not id(item) in cache:
                        cache[id(item)] = [id(item), "Process #%d" % index]
                    self._treemodel.append(cache[id(item)])
                self.core.emit_event("process-list-changed")
            strategy_selector = self.gui.get_object("StrategySelector")
            strategy_selector.connect("changed", lambda widget: \
                    self.core.emit_event("process-strategy-changed"))
            self.core.register_event("process-strategy-list-changed",
                    self._update_widgets)
            self.register_model_update(update_model)
            self.core.register_event("process-selection-changed",
                    self._process_switch)
            self.core.register_event("process-changed",
                    self._store_process_settings)
            self.core.register_event("process-strategy-changed",
                    self._store_process_settings)
        self.core.set("processes", self)
        return True

    def teardown(self):
        if self.gui:
            self.core.unregister_ui("main", self.gui.get_object("ProcessBox"))
            self.core.unregister_event("process-selection-changed",
                    self._process_switch)
            self.core.unregister_event("process-changed",
                    self._store_process_settings)
        self.core.set("processes", None)
        return True

    def get_selected(self, index=False):
        return self._get_selected(self._modelview, index=index)

    def select(self, process):
        if process in self:
            selection = self._modelview.get_selection()
            index = [id(p) for p in self].index(id(p))
            selection.unselect_all()
            selection.select_path((index,))

    def _render_process_description(self, column, cell, model, m_iter):
        path = model.get_path(m_iter)
        data = self[path[0]]
        # find the current strategy
        text = "TODO"
        cell.set_property("text", text)

    def _edit_process_name(self, cell, path, new_text):
        path = int(path)
        if (new_text != self._treemodel[path][self.COLUMN_NAME]) and \
                new_text:
            self._treemodel[path][self.COLUMN_NAME] = new_text

    def _trigger_table_update(self):
        # trigger a table update - this is clumsy!
        cell = self.gui.get_object("DescriptionColumn")
        renderer = self.gui.get_object("DescriptionCell")
        cell.set_cell_data_func(renderer, self._render_process_description)

    def _update_widgets(self):
        # TODO: keep the current selection
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
            strategy = self._get_strategy(strategy_name)
            self.core.get("set_parameter_values")("process", process["parameters"])
            control_box.show()
            self.core.unblock_event("process-strategy-changed")
            self.core.unblock_event("process-changed")
            self.core.emit_event("process-strategy-changed")
        
    def _process_new(self, *args):
        strategies = self.core.get("get_parameter_sets")("process").values()
        strategies.sort(key=lambda item: item["weight"])
        strategy = strategies[0]
        new_process = {"strategy": strategy["name"],
                "parameters": strategy["parameters"].copy(),
        }
        self.append(new_process)
        self.select(new_process)

