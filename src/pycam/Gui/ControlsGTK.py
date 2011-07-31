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

# gtk and gobject are imported later (to avoid plugin load failures)

import pycam.Utils.log


_log = pycam.Utils.log.get_logger()


def _input_conversion(func):
    def _input_conversion_wrapper(self, value):
        if value is None:
            new_value = None
        elif hasattr(self, "_input_converter") and self._input_converter:
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

    @_input_conversion
    def _get_input_conversion_result(self, value):
        # a simple dummy replicating the behaviour of _input_conversion
        return value


class InputNumber(InputBaseClass):

    def __init__(self, digits=0, start=0, lower=0, upper=100,
            increment=1, change_handler=None):
        import gtk
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

    def __init__(self, choices, force_type=None, change_handler=None):
        import gtk
        import gobject
        g_type = self._get_column_type(choices, force_type=force_type)
        self.model = gtk.ListStore(gobject.TYPE_STRING, g_type)
        for label, value in choices:
            self.model.append((label,
                    self._get_input_conversion_result(value)))
        renderer = gtk.CellRendererText()
        self.control = gtk.ComboBox(self.model)
        self.control.pack_start(renderer)
        self.control.set_attributes(renderer, text=0)
        self.control.set_active(0)
        if change_handler:
            self.control.connect("changed", change_handler)

    def _get_column_type(self, choices, force_type=None):
        import gobject
        type_mapper = {int: gobject.TYPE_INT,
                long: gobject.TYPE_INT64,
                basestring: gobject.TYPE_STRING,
                bool: gobject.TYPE_BOOLEAN
        }
        if force_type is None:
            value_sample = choices[0][1]
            for key, g_type in type_mapper.iteritems():
                if isinstance(value_sample, key):
                    break
            else:
                raise TypeError("Invalid sample type give: %s - %s" % \
                        (sample_value, type(sample_value)))
        elif force_type in type_mapper:
            g_type = type_mapper[force_type]
        else:
            raise TypeError("Invalid type forced: %s" % str(force_type))
        return g_type

    @_output_conversion
    def get_value(self):
        index = self.control.get_active()
        if index < 0:
            return None
        else:
            return self.model[index][1]

    @_input_conversion
    def set_value(self, value):
        if value is None:
            self.control.set_active(-1)
        else:
            for index, row in enumerate(self.model):
                if row[1] == value:
                    self.control.set_active(index)
                    break
            else:
                _log.debug("Unknown value: %s" % str(value))

    def update_choices(self, choices):
        # TODO: selection restore does not work currently; there seems to be a glitch during "delete model"
        selected = self.get_value()
        for choice_index, (label, value) in enumerate(choices):
            for index, row in enumerate(self.model):
                if row[1] == value:
                    break
            else:
                # this choice is new
                self.model.insert(choice_index, (label,
                        self._get_input_conversion_result(value)))
                continue
            # the current choice is preceded by some obsolete items
            while index > choice_index:
                m_iter = self.model.get_iter((index,))
                self.model.remove(m_iter)
                index -= 1
            # update the label column
            row[0] = label
        # check if there are obsolete items after the last one
        while len(self.model) > len(choices):
            m_iter = self.model.get_iter((len(choices),))
            self.model.remove(m_iter)
        self.set_value(selected)


class InputTable(InputChoice):

    def __init__(self, choices, force_type=None, change_handler=None):
        import gtk
        import gobject
        g_type = self._get_column_type(choices, force_type=force_type)
        self.model = gtk.ListStore(gobject.TYPE_STRING, g_type)
        for label, value in choices:
            self.model.append((label,
                    self._get_input_conversion_result(value)))
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

    def _get_input_conversion_result(self, value):
        # handle a list instead of single items
        return super(InputTable, self)._get_input_conversion_result([value])[0]

    @_output_conversion
    def get_value(self):
        model, rows = self._selection.get_selected_rows()
        return [self.model[path[0]][1] for path in rows]

    @_input_conversion
    def set_value(self, items):
        self._selection.unselect_all()
        if items is None:
            items = []
        for item in items:
            for index, row in enumerate(self.model):
                if row[1] == item:
                    self._selection.select_path((index, ))
                    break


class InputCheckBox(InputBaseClass):

    def __init__(self, start=False, change_handler=None):
        import gtk
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

