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


class ModelPosition(pycam.Plugins.PluginBase):

    UI_FILE = "model_position.ui"
    DEPENDS = ["Models"]
    CATEGORIES = ["Model"]

    def setup(self):
        if self.gui:
            position_box = self.gui.get_object("ModelPositionBox")
            position_box.unparent()
            self._gtk_handlers = []
            self.core.register_ui("model_handling", "Position", position_box, -20)
            shift_button = self.gui.get_object("ShiftModelButton")
            self._gtk_handlers.append((shift_button, "clicked", self._shift_model))
            align_button = self.gui.get_object("AlignPositionButton")
            self._gtk_handlers.append((align_button, "clicked", self._align_model))
            # grab default button for shift/align controls
            for axis in "XYZ":
                obj = self.gui.get_object("ShiftPosition%s" % axis)
                self._gtk_handlers.extend((
                    (obj, "focus-in-event", lambda widget, data: shift_button.grab_default()),
                    (obj, "focus-out-event",
                     lambda widget, data: shift_button.get_toplevel().set_default(None))))
            for axis in "XYZ":
                for name_template in ("AlignPosition%s", "AlignPosition%sMin",
                                      "AlignPosition%sCenter", "AlignPosition%sMax"):
                    obj = self.gui.get_object(name_template % axis)
                    self._gtk_handlers.extend((
                        (obj, "focus-in-event", lambda widget, data: align_button.grab_default()),
                        (obj, "focus-out-event",
                         lambda widget, data: align_button.get_toplevel().set_default(None))))
            self._event_handlers = (("model-selection-changed", self._update_position_widgets), )
            self.register_gtk_handlers(self._gtk_handlers)
            self.register_event_handlers(self._event_handlers)
            self._update_position_widgets()
        return True

    def teardown(self):
        if self.gui:
            self.core.unregister_ui("model_handling", self.gui.get_object("ModelPositionBox"))
            self.unregister_gtk_handlers(self._gtk_handlers)
            self.unregister_event_handlers(self._event_handlers)

    def _update_position_widgets(self):
        widget = self.gui.get_object("ModelPositionBox")
        if self.core.get("models").get_selected():
            widget.show()
        else:
            widget.hide()

    def _shift_model(self, widget=None):
        models = self.core.get("models").get_selected()
        if not models:
            return
        self.core.emit_event("model-change-before")
        progress = self.core.get("progress")
        progress.update(text="Aligning model")
        progress.disable_cancel()
        progress.set_multiple(len(models), "Model")
        shift = [self.gui.get_object("ShiftPosition%s" % axis).get_value() for axis in "XYZ"]
        for model in models:
            model.model.shift(shift[0], shift[1], shift[2], callback=progress.update)
            progress.update_multiple()
        progress.finish()
        self.core.emit_event("model-change-after")

    def _align_model(self, widget=None):
        models = self.core.get("models").get_selected()
        if not models:
            return
        self.core.emit_event("model-change-before")
        dest = [self.gui.get_object("AlignPosition%s" % axis).get_value() for axis in "XYZ"]
        progress = self.core.get("progress")
        progress.update(text="Shifting model")
        progress.disable_cancel()
        progress.set_multiple(len(models), "Model")
        for model_dict in models:
            model = model_dict.model
            shift_values = []
            for axis in "XYZ":
                dest = self.gui.get_object("AlignPosition%s" % axis).get_value()
                alignments = ("Min", "Center", "Max")
                for alignment in alignments:
                    objname = "AlignPosition%s%s" % (axis, alignment)
                    min_axis = getattr(model, "min%s" % axis.lower())
                    max_axis = getattr(model, "max%s" % axis.lower())
                    if self.gui.get_object(objname).get_active():
                        if alignment == "Min":
                            shift = dest - min_axis
                        elif alignment == "Center":
                            shift = dest - (min_axis + max_axis) / 2.0
                        else:
                            shift = dest - max_axis
                        shift_values.append(shift)
            model.shift(shift_values[0], shift_values[1], shift_values[2],
                        callback=progress.update)
            progress.update_multiple()
        progress.finish()
        self.core.emit_event("model-change-after")
