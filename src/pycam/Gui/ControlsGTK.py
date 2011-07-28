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


class InputBaseClass(object):

    def get_widget(self):
        return self.control

    def set_visible(self, state):
        if state:
            self.control.show()
        else:
            self.control.hide()


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

    def get_value(self):
        return self.control.get_value()

    def set_value(self, value):
        self.control.set_value(value)


class InputChoice(InputBaseClass):

    def __init__(self, choices, force_type=None, change_handler=None):
        import gtk
        import gobject
        type_mapper = {int: gobject.TYPE_INT,
                long: gobject.TYPE_LONG,
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
        self.model = gtk.ListStore(gobject.TYPE_STRING, g_type)
        self.control = gtk.ComboBox(self.model)
        renderer = gtk.CellRendererText()
        self.control.pack_start(renderer)
        self.control.set_attributes(renderer, text=0)
        for label, value in choices:
            self.model.append((label, value))
        self.control.set_active(0)
        if change_handler:
            self.control.connect("changed", change_handler)

    def get_value(self):
        index = self.control.get_active()
        if index < 0:
            return None
        else:
            return self.model[index][1]

    def set_value(self, value):
        if value is None:
            self.control.set_active(-1)
        else:
            for index, row in enumerate(self.model):
                if row[1] == value:
                    self.control.set_active(index)
                    break
            else:
                _log.debug("Tried to set an invalid value: %s" % str(value))

    def update_choices(self, choices):
        # TODO: selection restore does not work currently; there seems to be a glitch during "delete model"
        old_selection_index = self.control.get_active()
        if old_selection_index < 0:
            old_selection = None
        else:
            old_selection = self.model[old_selection_index][1]
        for choice_index, (label, value) in enumerate(choices):
            for index, row in enumerate(self.model):
                if row[1] == value:
                    break
            else:
                # this choice is new
                self.model.insert(choice_index, (label, value))
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
        # restore the previous selection
        for index, row in enumerate(self.model):
            if row[1] == old_selection:
                self.control.set_active(index)
                print "Restored: %d" % index
                break
        else:
            self.control.set_active(-1)

class InputCheckBox(InputBaseClass):

    def __init__(self, start=False, change_handler=None):
        import gtk
        self.control = gtk.CheckButton()
        self.control.set_active(start)
        if change_handler:
            self.control.connect("toggled", change_handler)

    def get_value(self):
        return self.control.get_active()

    def set_value(self, value):
        self.control.set_active(value)

