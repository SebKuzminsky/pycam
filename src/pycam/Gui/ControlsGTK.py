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


import gtk
import gobject

import pycam.Utils.log


_log = pycam.Utils.log.get_logger()


def _input_conversion(func):
    def _input_conversion_wrapper(self, value):
        if hasattr(self, "_input_converter") and self._input_converter:
            new_value = self._input_converter(value)
        else:
            new_value = value
        return func(self, new_value)
    return _input_conversion_wrapper

def _output_conversion(func):
    def _output_conversion_wrapper(self):
        result = func(self)
        if not (result is None) and hasattr(self, "_output_converter") and \
                self._output_converter:
            result = self._output_converter(result)
        return result
    return _output_conversion_wrapper


class InputBaseClass(object):

    def get_widget(self):
        return self.control

    def set_visible(self, state):
        if state:
            self.control.show()
        else:
            self.control.hide()

    def set_conversion(self, set_conv=None, get_conv=None):
        self._input_converter = set_conv
        self._output_converter = get_conv


class InputNumber(InputBaseClass):

    def __init__(self, digits=0, start=0, lower=0, upper=100,
            increment=1, change_handler=None):
        adjustment = gtk.Adjustment(value=start, lower=lower, upper=upper,
                step_incr=increment)
        self.control = gtk.SpinButton(adjustment, digits=digits)
        self.control.set_value(start)
        if change_handler:
            self.control.connect("changed", change_handler)

    @_output_conversion
    def get_value(self):
        return self.control.get_value()

    @_input_conversion
    def set_value(self, value):
        self.control.set_value(value)


class InputChoice(InputBaseClass):

    def __init__(self, choices, change_handler=None):
        self.model = gtk.ListStore(gobject.TYPE_STRING)
        self._values = []
        for label, value in choices:
            self.model.append((label, ))
            self._values.append(value)
        renderer = gtk.CellRendererText()
        self.control = gtk.ComboBox(self.model)
        self.control.pack_start(renderer)
        self.control.set_attributes(renderer, text=0)
        self.control.set_active(0)
        if change_handler:
            self.control.connect("changed", change_handler)

    @_output_conversion
    def get_value(self):
        index = self.control.get_active()
        if index < 0:
            return None
        else:
            return self._values[index]

    @_input_conversion
    def set_value(self, value):
        if value is None:
            self.control.set_active(-1)
        else:
            if value in self._values:
                self.control.set_active(self._values.index(value))
            else:
                _log.debug("Unknown value: %s" % str(value))

    def update_choices(self, choices):
        selected = self.get_value()
        for choice_index, (label, value) in enumerate(choices):
            if not value in self._values:
                # this choice is new
                self.model.insert(choice_index, (label, ))
                self._values.insert(choice_index, value)
                continue
            index = self._values.index(value)
            row = self.model[index]
            # the current choice is preceded by some obsolete items
            while index > choice_index:
                m_iter = self.model.get_iter((index,))
                self.model.remove(m_iter)
                self._values.pop(index)
                index -= 1
            # update the label column
            row[0] = label
        # check if there are obsolete items after the last one
        while len(self.model) > len(choices):
            m_iter = self.model.get_iter((len(choices),))
            self.model.remove(m_iter)
            self._values.pop(-1)
        self.set_value(selected)


class InputTable(InputChoice):

    def __init__(self, choices, change_handler=None):
        self.model = gtk.ListStore(gobject.TYPE_STRING)
        self._values = []
        for label, value in choices:
            self.model.append((label,))
            self._values.append(value)
        renderer = gtk.CellRendererText()
        self.control = gtk.ScrolledWindow()
        self._treeview = gtk.TreeView(self.model)
        self.control.add(self._treeview)
        self.control.set_shadow_type(gtk.SHADOW_ETCHED_OUT)
        self.control.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        column = gtk.TreeViewColumn()
        column.pack_start(renderer, expand=False)
        column.set_attributes(renderer, text=0)
        self._treeview.append_column(column)
        self._treeview.set_headers_visible(False)
        self._selection = self._treeview.get_selection()
        self._selection.set_mode(gtk.SELECTION_MULTIPLE)
        self.control.show_all()
        if change_handler:
            self._selection.connect("changed", change_handler)

    def get_value(self):
        model, rows = self._selection.get_selected_rows()
        return [self._values[path[0]] for path in rows]

    def set_value(self, items):
        selection = self._selection
        if items is None:
            items = []
        for index, value in enumerate(self._values):
            if value in items:
                selection.select_path((index, ))
            else:
                selection.unselect_path((index, ))


class InputCheckBox(InputBaseClass):

    def __init__(self, start=False, change_handler=None):
        self.control = gtk.CheckButton()
        self.control.set_active(start)
        if change_handler:
            self.control.connect("toggled", change_handler)

    @_output_conversion
    def get_value(self):
        return self.control.get_active()

    @_input_conversion
    def set_value(self, value):
        self.control.set_active(value)


class ParameterSection(object):

    def __init__(self):
        self._widgets = []
        self._table = gtk.Table(rows=1, columns=2)
        self._table.set_col_spacings(3)
        self._table.set_row_spacings(3)
        self.update_widgets()
        self._update_widgets_visibility()
        self._table.show()
        self.widget = self._table

    def add_widget(self, widget, label, weight=100):
        item = (widget, label, weight, [])
        self._widgets.append(item)
        for signal in ("hide", "show"):
            item[3].append(widget.connect(signal,
                    self._update_widgets_visibility))
        self.update_widgets()

    def clear_widgets(self):
        while self._widgets:
            item = self._widgets.pop()
            for signal_handler in item[3]:
                item[0].disconnect(signal_handler)
        self.update_widgets()

    def update_widgets(self):
        widgets = list(self._widgets)
        widgets.sort(key=lambda item: item[2])
        # remove all widgets from the table
        for child in self._table.get_children():
            self._table.remove(child)
        # add the current controls
        for index, widget in enumerate(widgets):
            if hasattr(widget, "get_label"):
                # checkbox
                widget.set_label(widget[1])
                self._table.attach(widget, 0, 2, index, index + 1,
                        xoptions=gtk.FILL, yoptions=gtk.FILL)
            elif not widget[1]:
                self._table.attach(widget[0], 0, 2, index, index + 1,
                        xoptions=gtk.FILL, yoptions=gtk.FILL)
            else:
                # spinbutton, combobox, ...
                label = gtk.Label("%s:" % widget[1])
                label.set_alignment(0.0, 0.5)
                self._table.attach(label, 0, 1, index, index + 1,
                        xoptions=gtk.FILL, yoptions=gtk.FILL)
                self._table.attach(widget[0], 1, 2, index, index + 1,
                        xoptions=gtk.FILL, yoptions=gtk.FILL)
        self._update_widgets_visibility()

    def _get_table_row_of_widget(self, widget):
        for child in self._table.get_children():
            if child is widget:
                return self._get_child_row(child)
        else:
            return -1

    def _get_child_row(self, widget):
        return gtk.Container.child_get_property(self._table, widget,
                "top-attach")

    def _update_widgets_visibility(self, widget=None):
        for widget in self._widgets:
            table_row = self._get_table_row_of_widget(widget[0])
            is_visible = widget[0].props.visible
            for child in self._table.get_children():
                if widget == child:
                    continue
                if self._get_child_row(child) == table_row:
                    if is_visible:
                        child.show()
                    else:
                        child.hide()

