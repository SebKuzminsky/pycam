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


class ModelSwapAxes(pycam.Plugins.PluginBase):

    UI_FILE = "model_swap_axes.ui"

    def setup(self):
        if self.gui:
            swap_box = self.gui.get_object("ModelSwapBox")
            swap_box.unparent()
            self.core.register_ui("model_handling", "Swap axes", swap_box, 0)
            self.gui.get_object("SwapAxesButton").connect("clicked",
                    self._swap_axes)
        return True

    def teardown(self):
        if self.gui:
            self.core.unregister_ui("model_handling",
                    self.gui.get_object("ModelSwapBox"))

    def _swap_axes(self, widget=None):
        model = self.core.get("model")
        if not model:
            return
        self.core.emit_event("model-change-before")
        self.core.get("update_progress")("Swap axes of model")
        self.core.get("disable_progress_cancel_button")()
        for axes, template in (("XY", "x_swap_y"), ("XZ", "x_swap_z"),
                ("YZ", "y_swap_z")):
            if self.gui.get_object("SwapAxes%s" % axes).get_active():
                break
        model.transform_by_template(template,
                callback=self.core.get("update_progress"))
        self.core.emit_event("model-change-after")



