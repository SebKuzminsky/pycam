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


class ProcessStrategyManager(pycam.Plugins.PluginBase):

    def setup(self):
        self.strategies = []
        self.parameters = []
        self.core.set("process-strategies", self.strategies)
        self.core.set("pathgenerator_parameters", self.parameters)
        self.core.set("register_strategy", self.register_strategy)
        self.core.set("unregister_strategy", self.unregister_strategy)
        self.core.set("register_pathgenerator_parameter",
                self.register_generator_parameter)
        self.core.set("unregister_pathgenerator_parameter",
                self.unregister_generator_parameter)
        self.core.set("get_pathgenerator_parameter_value",
                self.get_parameter_value)
        self.core.set("set_pathgenerator_parameter_value",
                self.set_parameter_value)
        return True

    def teardown(self):
        for name in ("strategies", "pathgenerator_parameters",
                "register_strategy", "register_pathgenerator_parameter",
                "unregister_strategy", "unregister_pathgenerator_parameter",
                "get_pathgenerator_parameter_value",
                "set_pathgenerator_parameter_value"):
            self.core.set(name, None)

    def register_strategy(self, name, label, func, parameters=None,
                model_filter=None, weight=100):
        if self.get_by_name(name):
            self.log.debug("Registering an existing path generator again: " + \
                    name)
        generator = {}
        generator["name"] = name
        generator["label"] = label
        generator["func"] = func
        generator["parameters"] = parameters or []
        generator["model_filter"] = model_filter
        generator["weight"] = weight
        self.strategies.append(generator)
        self.strategies.sort(key=lambda item: item["weight"])
        self.core.emit_event("process-strategy-list-changed")

    def unregister_strategy(self, name):
        index = self.get_by_name(name, force_index=True)
        if index < 0:
            self.log.debug("Tried to unregister a non-existing path " + \
                    "generator: %s" % name)
        else:
            self.strategies.pop(index)
            self.core.emit_event("process-strategy-list-changed")

    def register_generator_parameter(self, name, label, control, weight=100):
        if self.get_parameter_by_name(name):
            self.log.debug("Registering an existing path generator parameter " + \
                    "again: %s" % name)
        parameter = {}
        parameter["name"] = name
        parameter["label"] = label
        parameter["control"] = control
        parameter["weight"] = weight
        self.parameters.append(parameter)
        self.parameters.sort(key=lambda param: param["weight"])
        self.core.emit_event("pathgenerator-parameter-list-changed")

    def unregister_generator_parameter(self, name):
        index = self.get_parameter_by_name(name, force_index=True)
        if index < 0:
            self.log.debug("Tried to unregister a non-existing path " + \
                    "generator parameter: %s" % name)
        else:
            self.parameters.pop(index)
            self.core.emit_event("pathgenerator-parameter-list-changed")

    def _get_by_name(self, name, force_index=False, data_list=None):
        for index, generator in enumerate(data_list):
            if generator["name"] == name:
                if force_index:
                    return index
                else:
                    return generator
        else:
            if force_index:
                return -1
            else:
                return None

    def get_by_name(self, *args, **kwargs):
        merged_kw = kwargs.copy()
        merged_kw.update({"data_list": self.strategies})
        return self._get_by_name(*args, **merged_kw)

    def get_parameter_by_name(self, *args, **kwargs):
        merged_kw = kwargs.copy()
        merged_kw.update({"data_list": self.parameters})
        return self._get_by_name(*args, **merged_kw)

    def get_parameter_value(self, name):
        parameter = self.get_parameter_by_name(name)
        if parameter:
            return parameter["control"].get_value()
        else:
            self.log.debug("Unknown path parameter requested: %s" % name)
            return None

    def set_parameter_value(self, name, value):
        parameter = self.get_parameter_by_name(name)
        if parameter:
            parameter["control"].set_value(value)
        else:
            self.log.debug("Unknown path parameter requested: %s" % name)

    def run_path_generator(self, name, parameters):
        generator = self.get_by_name(name)
        if generator:
            args = {}
            for key in parameters:
                if not key in generator["parameters"]:
                    continue
                args[key] = parameters[key]
            generator["func"](**parameters)
        else:
            self.log.debug("Tried to run a non-existing path generator:" + \
                    name)


#TODO: merge with ProcessStrategyManager
class PathParameterGTK(pycam.Plugins.PluginBase):

    DEPENDS = ["ProcessStrategyManager", "Processes"]

    def setup(self):
        # TODO: check for gtk
        if True:
            import gtk
            self._gtk = gtk
            self._table = gtk.Table(rows=1, columns=2)
            self._table.set_col_spacings(3)
            self._table.set_row_spacings(3)
            self.core.register_ui("process_parameters", "Path parameters", self._table, 30)
            self.core.register_event("pathgenerator-parameter-changed",
                    lambda: self.core.emit_event("process-changed"))
            self.core.register_event("process-changed",
                    self._update_parameter_widgets)
            self.core.register_event("process-strategy-changed",
                    self._update_parameter_widgets)
            self.core.register_event("pathgenerator-parameter-list-changed",
                    self._update_parameter_widgets_table)
            self._update_parameter_widgets_table()
            self._table.show()
        return True

    def teardown(self):
        if self.gui:
            self.core.unregister_ui("process_parameters", self._table)

    def _update_parameter_widgets_table(self):
        # TODO: check for gtk
        if True:
            gtk = self._gtk
            params = self.core.get("pathgenerator_parameters")
            # remove all widgets from the table
            for child in self._table.get_children():
                self._table.remove(child)
            # add the current controls
            for index, param in enumerate(params):
                widget = param["control"].get_widget()
                if hasattr(widget, "get_label"):
                    # checkbox
                    widget.set_label(param["label"])
                    self._table.attach(widget, 0, 2, index, index + 1,
                            xoptions=gtk.FILL, yoptions=gtk.FILL)
                else:
                    # spinbutton, combobox, ...
                    label = gtk.Label("%s:" % param["label"])
                    label.set_alignment(0.0, 0.5)
                    self._table.attach(label, 0, 1, index, index + 1,
                            xoptions=gtk.FILL, yoptions=gtk.FILL)
                    self._table.attach(widget, 1, 2, index, index + 1,
                            xoptions=gtk.FILL, yoptions=gtk.FILL)
            self._update_parameter_widgets()

    def _get_table_row_of_widget(self, widget):
        for child in self._table.get_children():
            if child is widget:
                return self._get_child_row(child)
        else:
            return -1

    def _get_child_row(self, widget):
        return self._gtk.Container.child_get_property(self._table, widget,
                "top-attach")

    def _update_parameter_widgets(self):
        params = self.core.get("pathgenerator_parameters")
        generator = self.core.get("current-strategy")
        if not generator:
            return
        for param in params:
            table_row = self._get_table_row_of_widget(
                    param["control"].get_widget())
            for child in self._table.get_children():
                if self._get_child_row(child) == table_row:
                    if param["name"] in generator["parameters"]:
                        child.show()
                    else:
                        child.hide()

