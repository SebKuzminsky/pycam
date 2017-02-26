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


class ParameterGroupManager(pycam.Plugins.PluginBase):

    CATEGORIES = ["Plugins"]

    def setup(self):
        self._groups = {}
        self.core.set("get_parameter_values", self.get_parameter_values)
        self.core.set("set_parameter_values", self.set_parameter_values)
        self.core.set("get_parameter_sets", self.get_parameter_sets)
        self.core.set("register_parameter_group", self.register_parameter_group)
        self.core.set("register_parameter_set", self.register_parameter_set)
        self.core.set("register_parameter", self.register_parameter)
        self.core.set("unregister_parameter_group", self.unregister_parameter_group)
        self.core.set("unregister_parameter_set", self.unregister_parameter_set)
        self.core.set("unregister_parameter", self.unregister_parameter)
        return True

    def teardown(self):
        for name in ("set_parameter_values", "get_parameter_values", "get_parameter_sets",
                     "register_parameter_set", "register_parameter_group", "register_parameter",
                     "unregister_parameter_set", "unregister_parameter_group",
                     "unregister_parameter"):
            self.core.set(name, None)

    def register_parameter_group(self, name, changed_set_event=None, changed_set_list_event=None,
                                 get_current_set_func=None):
        if name in self._groups:
            self.log.debug("Registering parameter group '%s' again", name)
        self._groups[name] = {"changed_set_event": changed_set_event,
                              "changed_set_list_event": changed_set_list_event,
                              "get_current_set_func": get_current_set_func,
                              "sets": {},
                              "parameters": {}}
        if changed_set_event:
            self.core.register_event(changed_set_event, self._update_widgets_visibility, name)

    def _update_widgets_visibility(self, group_name):
        group = self._groups[group_name]
        current_set_func = group["get_current_set_func"]
        if not current_set_func:
            return
        current_set = current_set_func()
        if current_set:
            active_parameters = current_set["parameters"]
        else:
            active_parameters = []
        for param in group["parameters"].values():
            is_visible = param["name"] in active_parameters
            control = param["control"]
            if control is None:
                pass
            elif hasattr(control, "set_visible"):
                control.set_visible(is_visible)
            elif is_visible:
                control.show()
            else:
                control.hide()

    def register_parameter_set(self, group_name, name, label, func, parameters=None, weight=100):
        if group_name not in self._groups:
            self.log.info("Unknown parameter group: %s", group_name)
            return
        group = self._groups[group_name]
        if name in group["sets"]:
            self.log.debug("Registering parameter set '%s' again", name)
        if parameters is None:
            parameters = []
        group["sets"][name] = {"name": name, "label": label, "func": func,
                               "parameters": parameters, "weight": weight}
        event = group["changed_set_list_event"]
        if event:
            self.core.emit_event(event)

    def register_parameter(self, group_name, name, control, get_func=None, set_func=None):
        if group_name not in self._groups:
            self.log.info("Unknown parameter group: %s", group_name)
            return
        group = self._groups[group_name]
        if name in group["parameters"]:
            self.log.debug("Registering parameter '%s' in group '%s' again", name, group_name)
        if not get_func:
            get_func = control.get_value
        if not set_func:
            set_func = control.set_value
        group["parameters"][name] = {"name": name, "control": control, "get_func": get_func,
                                     "set_func": set_func}

    def get_parameter_values(self, group_name):
        if group_name not in self._groups:
            self.log.info("Unknown parameter group: %s", group_name)
            return {}
        result = {}
        group = self._groups[group_name]
        for parameter in group["parameters"].values():
            result[parameter["name"]] = parameter["get_func"]()
        return result

    def set_parameter_values(self, group_name, value_dict):
        if group_name not in self._groups:
            self.log.info("Unknown parameter group: %s", group_name)
            return
        group = self._groups[group_name]
        for parameter in group["parameters"].values():
            if parameter["name"] in value_dict:
                parameter["set_func"](value_dict[parameter["name"]])

    def get_parameter_sets(self, group_name):
        if group_name not in self._groups:
            self.log.info("Unknown parameter group: %s", group_name)
            return
        group = self._groups[group_name]
        return dict(group["sets"])

    def unregister_parameter_group(self, group_name):
        if group_name not in self._groups:
            self.log.debug("Tried to unregister a non-existing parameter group: %s", group_name)
            return
        group = self._groups[group_name]
        if group["parameters"]:
            self.log.debug("Unregistering parameter from group '%s', but it still contains "
                           "parameters: %s", group_name, ", ".join(group["parameters"].keys()))
            for name in group["parameters"]:
                self.unregister_parameter(group_name, name)
        if group["sets"]:
            self.log.debug("Unregistering parameter group (%s), but it still contains sets: %s",
                           group_name, ", ".join(group["sets"].keys()))
            for set_name in group["sets"]:
                self.unregister_parameter_set(group_name, set_name)
        changed_set_event = group["changed_set_event"]
        if changed_set_event:
            self.core.register_event(changed_set_event, self._update_widgets_visibility,
                                     group_name)
        del self._groups[group_name]

    def unregister_parameter_set(self, group_name, set_name):
        if group_name not in self._groups:
            self.log.debug("Tried to unregister set '%s' from a non-existing parameter group: %s",
                           set_name, group_name)
            return
        group = self._groups[group_name]
        if set_name not in group["sets"]:
            self.log.debug("Tried to unregister non-existing parameter set '%s' from group '%s'",
                           set_name, group_name)
            return
        del group["sets"][set_name]
        event = group["changed_set_list_event"]
        if event:
            self.core.emit_event(event)

    def unregister_parameter(self, group_name, name):
        if group_name not in self._groups:
            self.log.debug("Tried to unregister parameter '%s' from a non-existing parameter "
                           "group: %s", name, group_name)
            return
        group = self._groups[group_name]
        if name in group["parameters"]:
            del group["parameters"][name]
        else:
            self.log.debug("Tried to unregister the non-existing parameter '%s' from group '%s'",
                           name, group_name)
