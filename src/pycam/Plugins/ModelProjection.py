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
from pycam.Geometry.Plane import Plane
from pycam.Geometry.Point import Point, Vector


class ModelProjection(pycam.Plugins.PluginBase):

    UI_FILE = "model_projection.ui"
    DEPENDS = ["Models"]

    def setup(self):
        if self.gui:
            projection_frame = self.gui.get_object("ModelProjectionFrame")
            projection_frame.unparent()
            self.core.register_ui("model_handling", "Projection",
                    projection_frame, 10)
            self.core.register_event("model-change-after",
                    self._update_controls)
            self.gui.get_object("ProjectionButton").connect("clicked",
                    self._projection)
        return True

    def teardown(self):
        if self.gui:
            self.core.unregister_ui("model_handling",
                    self.gui.get_object("ModelProjectionFrame"))
            self.core.unregister_event("model-change-after",
                    self._update_controls)

    def _update_controls(self):
        model = self.core.get("model")
        is_projectable = model and hasattr(model, "get_waterline_contour")
        control = self.gui.get_object("ModelProjectionFrame")
        if is_projectable:
            control.show()
        else:
            control.hide()

    def _projection(self, widget=None):
        model = self.core.get("model")
        if not model or not hasattr(model, "get_waterline_contour"):
            return
        self.core.get("update_progress")("Calculating 2D projection")
        for objname, z_level in (("ProjectionModelTop", model.maxz),
                ("ProjectionModelMiddle", (model.minz + model.maxz) / 2.0),
                ("ProjectionModelBottom", model.minz),
                ("ProjectionModelCustom",
                    self.gui.get_object("ProjectionZLevel").get_value())):
            if self.gui.get_object(objname).get_active():
                plane = Plane(Point(0, 0, z_level), Vector(0, 0, 1))
                self.log.info("Projecting 3D model at level z=%g" % plane.p.z)
                projection = model.get_waterline_contour(plane)
                if projection:
                    self.core.get("load_model")(projection)
                else:
                    self.log.warn("The 2D projection at z=%g is empty. Aborted." % \
                            plane.p.z)
                break

