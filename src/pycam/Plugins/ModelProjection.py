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
            self.core.register_event("model-selection-changed",
                    self._update_controls)
            self._update_controls()
        return True

    def teardown(self):
        if self.gui:
            self.core.unregister_ui("model_handling",
                    self.gui.get_object("ModelProjectionFrame"))
            self.core.unregister_event("model-selection-changed",
                    self._update_controls)
            self.core.unregister_event("model-change-after",
                    self._update_controls)

    def _get_projectable_models(self):
        models = self.core.get("models").get_selected()
        projectables = []
        for model in models:
            if (not model is None) and hasattr(model, "get_waterline_contour"):
                projectables.append(model)
        return projectables

    def _update_controls(self):
        models = self._get_projectable_models()
        control = self.gui.get_object("ModelProjectionFrame")
        if models:
            control.show()
        else:
            control.hide()

    def _projection(self, widget=None):
        models = self._get_projectable_models()
        if not models:
            return
        progress = self.core.get("progress")
        progress.update(text="Calculating 2D projection")
        progress.set_multiple(len(models), "Model")
        for model in models:
            for objname, z_level in (("ProjectionModelTop", model.maxz),
                    ("ProjectionModelMiddle", (model.minz + model.maxz) / 2.0),
                    ("ProjectionModelBottom", model.minz),
                    ("ProjectionModelCustom",
                        self.gui.get_object("ProjectionZLevel").get_value())):
                if self.gui.get_object(objname).get_active():
                    plane = Plane(Point(0, 0, z_level), Vector(0, 0, 1))
                    self.log.info("Projecting 3D model at level z=%g" % plane.p.z)
                    new_model = model.get_waterline_contour(plane,
                            callback=progress.update)
                    if new_model:
                        self.core.get("load_model")(new_model)
                        model_manager = self.core.get("models")
                        try:
                            # add the name of the original model to the new name
                            original_name = model_manager.get_attr(model,
                                    "name").split("(")[0].strip()
                            new_name = model_manager.get_attr(new_model, "name")
                            model_manager.set_attr(new_model, "name",
                                    "%s (projection of %s)" % \
                                    (new_name, original_name))
                        except LookupError:
                            pass
                    else:
                        self.log.warn("The 2D projection at z=%g is empty. Aborted." % \
                                plane.p.z)
                    break
            progress.update_multiple()
        progress.finish()

