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


class ModelPolygons(pycam.Plugins.PluginBase):

    UI_FILE = "model_polygons.ui"

    def setup(self):
        if self.gui:
            polygon_frame = self.gui.get_object("ModelPolygonFrame")
            polygon_frame.unparent()
            self.core.register_ui("model_handling", "Polygons", polygon_frame, 0)
            self.core.register_event("model-change-after",
                    self._update_polygon_controls)
            self.gui.get_object("ToggleModelDirectionButton").connect("clicked",
                    self._toggle_direction)
            self.gui.get_object("DirectionsGuessButton").connect("clicked",
                    self._revise_directions)
        return True

    def teardown(self):
        if self.gui:
            self.core.unregister_ui("model_handling",
                    self.gui.get_object("ModelPolygonFrame"))

    def _update_polygon_controls(self):
        model = self.core.get("model")
        is_reversible = model and hasattr(model, "reverse_directions")
        frame = self.gui.get_object("ModelPolygonFrame")
        if is_reversible:
            frame.show()
        else:
            frame.hide()

    def _toggle_direction(self, widget=None):
        model = self.core.get("model")
        if not model or not hasattr(model, "reverse_directions"):
            return
        self.core.emit_event("model-change-before")
        self.core.get("update_progress")("Reversing directions of contour model")
        model.reverse_directions(callback=self.core.get("update_progress"))
        self.core.emit_event("model-change-after")

    def _revise_directions(self, widget=None):
        model = self.core.get("model")
        if not model or not hasattr(model, "revise_directions"):
            return
        self.core.emit_event("model-change-before")
        self.core.get("update_progress")("Analyzing directions of contour model")
        model.revise_directions(callback=self.core.get("update_progress"))
        self.core.emit_event("model-change-after")

