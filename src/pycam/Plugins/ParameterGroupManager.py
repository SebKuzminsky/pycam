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


class ParameterGroupManager(pycam.Plugins.PluginBase):

    def setup(self):
        self._groups = {}
        self.core.set("get_parameters", self.get_parameters)
        self.core.set("get_parameter_values", self.get_parameter_values)
        self.core.set("set_parameter_values", self.set_parameter_values)
        self.core.set("get_parameter_sets", self.get_parameter_sets)
        self.core.set("register_parameter_group", self.register_parameter_group)
        self.core.set("register_parameter_set", self.register_parameter_set)
        self.core.set("register_parameter_section", self.register_parameter_section)
        self.core.set("register_parameter", self.register_parameter)
        self.core.set("unregister_parameter_group",
                self.unregister_parameter_group)
        self.core.set("unregister_parameter_set",
                self.unregister_parameter_set)
        self.core.set("unregister_parameter_section",
                self.unregister_parameter_section)
        self.core.set("unregister_parameter",
                self.unregister_parameter)
        return True

    def teardown(self):
        for name in ("get_parameters", "set_parameter_values",
                "get_parameter_values", "get_parameter_sets",
                "register_parameter_section", "register_parameter_set",
                "register_parameter_group", "register_parameter",
                "unregister_parameter_section", "unregister_parameter_set",
                "unregister_parameter_group", "unregister_parameter"):
            self.core.set(name, None)

    def register_parameter_group(self, name, changed_set_event=None,
            changed_set_list_event=None, get_current_set_func=None):
        if name in self._groups:
            self.log.debug("Registering parameter group '%s' again" % name)
        self._groups[name] = {"changed_set_event": changed_set_event,
                "changed_set_list_event": changed_set_list_event,
                "get_current_set_func": get_current_set_func,
                "sets": {},
                "sections": {}}

    def register_parameter_set(self, group_name, name, label, func,
            parameters=None, weight=100):
        if not group_name in self._groups:
            self.log.info("Unknown parameter group: %s" % group_name)
            return
        group = self._groups[group_name]
        if name in group["sets"]:
            self.log.debug("Registering parameter set '%s' again" % name)
        if parameters is None:
            parameters = []
        group["sets"][name] = {"name": name,
                "label": label,
                "func": func,
                "parameters": parameters,
                "weight": weight,
        }
        event = group["changed_set_list_event"]
        if event:
            self.core.emit_event(event)

    def register_parameter_section(self, group_name, name):
        if not group_name in self._groups:
            self.log.info("Unknown parameter group: %s" % group_name)
            return
        group = self._groups[group_name]
        if name in group["sections"]:
            self.log.debug("Registering section '%s' in group '%s' again" % \
                    (name, group_name))
        widget = ParameterSectionGTK(self.core, group["changed_set_event"],
                lambda: self.get_parameters(group_name),
                group["get_current_set_func"])
        group["sections"][name] = {"widget": widget, "parameters": {}}
        return widget.widget

    def register_parameter(self, group_name, section_name, name, label,
            control, weight=100):
        if not group_name in self._groups:
            self.log.info("Unknown parameter group: %s" % group_name)
            return
        group = self._groups[group_name]
        if not section_name in group["sections"]:
            self.log.info("Unknown parameter section: %s->%s" % \
                    (group_name, section_name))
            return
        section = group["sections"][section_name]
        if name in section["parameters"]:
            self.log.debug("Registering parameter '%s' in group '%s' again" % \
                    (name, group_name))
        section["parameters"][name] = {"name": name, "label": label,
                "control": control, "weight": weight }
        section["widget"].update_widgets()

    def get_parameters(self, group_name):
        if not group_name in self._groups:
            self.log.info("Unknown parameter group: %s" % group_name)
            return []
        result = {}
        group = self._groups[group_name]
        for section in group["sections"].values():
            result.update(section["parameters"])
        return result

    def get_parameter_values(self, group_name):
        if not group_name in self._groups:
            self.log.info("Unknown parameter group: %s" % group_name)
            return {}
        result = {}
        group = self._groups[group_name]
        for section in group["sections"].values():
            for parameter in section["parameters"].values():
                result[parameter["name"]] = parameter["control"].get_value()
        return result

    def set_parameter_values(self, group_name, value_dict):
        if not group_name in self._groups:
            self.log.info("Unknown parameter group: %s" % group_name)
            return
        group = self._groups[group_name]
        for section in group["sections"].values():
            for parameter in section["parameters"].values():
                if parameter["name"] in value_dict:
                    parameter["control"].set_value(
                            value_dict[parameter["name"]])

    def get_parameter_sets(self, group_name):
        if not group_name in self._groups:
            self.log.info("Unknown parameter group: %s" % group_name)
            return
        group = self._groups[group_name]
        return dict(group["sets"])

    def unregister_parameter_group(self, group_name):
        if not group_name in self._groups:
            self.log.debug("Tried to unregister a non-existing parameter " + \
                    "group: %s" % group_name)
            return
        group = self._groups[group_name]
        if group["sections"]:
            self.log.debug(("Unregistering parameter group (%s), but it " + \
                    "still contains sections") % \
                    (group_name, ", ".join(group["sections"].keys())))
            for section_name in group["sections"]:
                self.unregister_parameter_section(group_name, section_name)
        if group["sets"]:
            self.log.debug(("Unregistering parameter group (%s), but it " + \
                    "still contains sets: %s") % \
                    (group_name, ", ".join(group["sets"].keys())))
            for set_name in group["sets"]:
                self.unregister_parameter_set(group_name, set_name)
        del self._groups[group_name]

    def unregister_parameter_section(self, group_name, section_name):
        if not group_name in self._groups:
            self.log.debug(("Tried to unregister section '%s' from a " + \
                    "non-existing parameter group: %s") % \
                    (section_name, group_name))
            return
        group = self._groups[group_name]
        if not section_name in group["sections"]:
            self.log.debug("Tried to unregister non-existing parameter " + \
                    "section '%s' from group '%s'" % (section_name, group_name))
            return
        section = group["sections"][section_name]
        if section["parameters"]:
            self.log.debug(("Unregistering parameter section (%s->%s), " + \
                    "but it still contains parameters") % (group_name,
                    section_name, ", ".join(group["parameters"].keys())))
            for parameter_name in section["parameters"]:
                self.unregister_parameter(group_name, section_name,
                        parameter_name)
        del group["sections"][section_name]

    def unregister_parameter_set(self, group_name, set_name):
        if not group_name in self._groups:
            self.log.debug(("Tried to unregister set '%s' from a " + \
                    "non-existing parameter group: %s") % \
                    (set_name, group_name))
            return
        group = self._groups[group_name]
        if not set_name in group["sets"]:
            self.log.debug("Tried to unregister non-existing parameter " + \
                    "set '%s' from group '%s'" % (set_name, group_name))
            return
        del group["sets"][set_name]
        event = group["changed_set_list_event"]
        if event:
            self.core.emit_event(event)

    def unregister_parameter(self, group_name, section_name, name):
        if not group_name in self._groups:
            self.log.debug(("Tried to unregister parameter '%s' in " + \
                    "section '%s' from a non-existing parameter group: %s") % \
                    (name, section_name, group_name))
            return
        group = self._groups[group_name]
        if not section_name in group["sections"]:
            self.log.debug(("Tried to unregister parameter '%s' from a " + \
                    "non-existing parameter section '%s' in group '%s'") % \
                    (name, section_name, group_name))
            return
        section = group["sections"][section_name]
        if name in section["parameters"]:
            del section["parameters"][name]
        else:
            self.log.debug("Tried to unregister the non-existing " + \
                    "parameter '%s' from '%s->%s'" % \
                    (name, group_name, section_name))
        

class ParameterSectionGTK(object):

    def __init__(self, core, update_visibility_event=None,
            get_params_dict_func=None,
            get_current_set_func=None):
        import gtk
        self._gtk = gtk
        self.core = core
        self._table = gtk.Table(rows=1, columns=2)
        self._table.set_col_spacings(3)
        self._table.set_row_spacings(3)
        if update_visibility_event:
            self.core.register_event(update_visibility_event,
                    self._update_widgets_visibility)
        self._get_current_set_func = get_current_set_func
        self._get_params_dict_func = get_params_dict_func
        self.update_widgets()
        self._update_widgets_visibility()
        self._table.show()
        self.widget = self._table

    def update_widgets(self):
        gtk = self._gtk
        params = self._get_params_dict_func().values()
        params.sort(key=lambda item: item["weight"])
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
            elif not param["label"]:
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
        self._update_widgets_visibility()

    def _get_table_row_of_widget(self, widget):
        for child in self._table.get_children():
            if child is widget:
                return self._get_child_row(child)
        else:
            return -1

    def _get_child_row(self, widget):
        return self._gtk.Container.child_get_property(self._table, widget,
                "top-attach")

    def _update_widgets_visibility(self):
        params = self._get_params_dict_func()
        generator = self._get_current_set_func()
        if not generator:
            return
        for param in params.values():
            table_row = self._get_table_row_of_widget(
                    param["control"].get_widget())
            for child in self._table.get_children():
                if self._get_child_row(child) == table_row:
                    if param["name"] in generator["parameters"]:
                        child.show()
                    else:
                        child.hide()

