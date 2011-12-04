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


class Units(pycam.Plugins.PluginBase):

    UI_FILE = "units.ui"
    CATEGORIES = ["System"]

    def setup(self):
        if self.gui:
            self._gtk_handlers = []
            unit_pref_box = self.gui.get_object("UnitPrefBox")
            unit_pref_box.unparent()
            self.core.register_ui("preferences_general", "Units",
                    unit_pref_box, 20)
            # unit control (mm/inch)
            unit_field = self.gui.get_object("unit_control")
            self._gtk_handlers.append((unit_field, "changed",
                    self.change_unit_init))
            def set_unit(text):
                unit_field.set_active(0 if text == "mm" else 1)
                self._last_unit = text
            self.core.add_item("unit", unit_field.get_active_text, set_unit)
            # other plugins should use "unit_string" for human readable output
            self.core.add_item("unit_string", unit_field.get_active_text)
            self._gtk_handlers.extend((
                    (self.gui.get_object("UnitChangeSelectAll"), "clicked",
                        self.change_unit_set_selection, True),
                    (self.gui.get_object("UnitChangeSelectNone"), "clicked",
                        self.change_unit_set_selection, False)))
            # "unit change" window
            self.unit_change_window = self.gui.get_object("UnitChangeDialog")
            self._gtk_handlers.extend((
                    (self.gui.get_object("UnitChangeApply"), "clicked",
                        self.change_unit_apply),
                    (self.unit_change_window, "delete_event",
                        self.change_unit_apply, False)))
            self.register_gtk_handlers(self._gtk_handlers)
        self.register_state_item("settings/unit", lambda: self.core.get("unit"),
                lambda value: self.core.set("unit", value))
        return True

    def teardown(self):
        self.clear_state_items()
        if self.gui:
            self.core.unregister_ui("preferences_general",
                    self.gui.get_object("UnitPrefBox"))
            self.unregister_gtk_handlers(self._gtk_handlers)
            # TODO: reset setting "unit" back to a default value?

    def change_unit_init(self, widget=None):
        new_unit = self.gui.get_object("unit_control").get_active_text()
        if self._last_unit is None:
            # first initialization
            self._last_unit = new_unit
            return
        if self._last_unit == new_unit:
            # don't show the dialog if the conversion would make no sense
            return
        # show a dialog asking for a possible model scaling due to the unit change
        self.unit_change_window.show()

    def change_unit_set_selection(self, widget, state):
        for key in ("UnitChangeModel", "UnitChangeProcesses", "UnitChangeTools",
                "UnitChangeBounds"):
            self.gui.get_object(key).set_active(state)

    def change_unit_apply(self, widget=None, data=None, apply_scale=True):
        # TODO: move tool/process/task related code to these plugins
        new_unit = self.gui.get_object("unit_control").get_active_text()
        factors = {
                ("mm", "inch"): 1 / 25.4,
                ("inch", "mm"): 25.4,
        }
        conversion = (self._last_unit, new_unit)
        if conversion in factors.keys():
            factor = factors[conversion]
            if apply_scale:
                if self.gui.get_object("UnitChangeModel").get_active():
                    # transform the model if it is selected
                    # keep the original center of the model
                    self.core.emit_event("model-change-before")
                    models = self.core.get("models")
                    progress = self.core.get("progress")
                    progress.disable_cancel()
                    progress.set_multiple(len(models), "Scaling model")
                    for model in models:
                        new_x, new_y, new_z = ((model.maxx + model.minx) / 2,
                                (model.maxy + model.miny) / 2,
                                (model.maxz + model.minz) / 2)
                        model.scale(factor, callback=progress.update)
                        cur_x, cur_y, cur_z = self._get_model_center()
                        model.shift(new_x - cur_x, new_y - cur_y,
                                new_z - cur_z,
                                callback=progress.update)
                        progress.update_multiple()
                    progress.finish()
                if self.gui.get_object("UnitChangeProcesses").get_active():
                    # scale the process settings
                    for process in self.core.get("processes"):
                        for key in ("MaterialAllowanceControl",
                                "MaxStepDownControl",
                                "EngraveOffsetControl"):
                            process[key] *= factor
                if self.gui.get_object("UnitChangeBounds").get_active():
                    # scale the boundaries and keep their center
                    for bounds in self.core.get("bounds"):
                        low, high = bounds.get_bounds()
                        if bounds.get_type() == Bounds.TYPE_FIXED_MARGIN:
                            low[0] *= factor
                            high[0] *= factor
                            low[1] *= factor
                            high[1] *= factor
                            low[2] *= factor
                            high[2] *= factor
                            bounds.set_bounds(low, high)
                        elif bounds.get_type() == Bounds.TYPE_CUSTOM:
                            center = [0, 0, 0]
                            for i in range(3):
                                center[i] = (high[i] + low[i]) / 2
                            for i in range(3):
                                low[i] = center[i] + (low[i] - center[i]) * factor
                                high[i] = center[i] + (high[i] - center[i]) * factor
                            bounds.set_bounds(low, high)
                        elif bounds.get_type() == Bounds.TYPE_RELATIVE_MARGIN:
                            # no need to change relative margins
                            pass
                if self.gui.get_object("UnitChangeTools").get_active():
                    # scale all tool dimensions
                    for tool in self.core.get("tools"):
                        for key in ("tool_radius", "torus_radius"):
                            # TODO: fix this invalid access
                            tool[key] *= factor
        self.unit_change_window.hide()
        # store the current unit (for the next run of this function)
        self._last_unit = new_unit
        # update all labels containing the unit size
        self.update_unit_labels()
        # redraw the model
        self.core.emit_event("model-change-after")

    def update_unit_labels(self, widget=None, data=None):
        # don't use the "unit" setting, since we need the plural of "inch"
        if self.core.get("unit") == "mm":
            base_unit = "mm"
        else:
            base_unit = "inches"
        for key in ("SpeedUnit2", ):
            self.gui.get_object(key).set_text("%s/minute" % base_unit)
        for key in ("LengthUnit1", "LengthUnit2", "LengthUnitTouchOffHeight"):
            self.gui.get_object(key).set_text(base_unit)

