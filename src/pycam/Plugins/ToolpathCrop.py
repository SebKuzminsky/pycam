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
from pycam.Geometry.Point import Point
from pycam.Geometry.Plane import Plane


"""
TODO:
    - get the currently selected toolpath (from the table)
    - update the current crop-polygons instantly (3D)
    - update the ToolpathCropInfoLabel content if no polygons are found
"""

class ToolpathCrop(pycam.Plugins.PluginBase):

    UI_FILE = "toolpath_crop.ui"

    def setup(self):
        if self.gui:
            action_button = self.gui.get_object("ToolpathCropButton")
            action_button.unparent()
            self.core.register_ui("toolpath_crop", "Crop", action_button, -3)
            self.core.register_event("model-change-after",
                    self._update_model_type_controls)
        return True

    def teardown(self):
        if self.gui:
            self.core.unregister_ui("toolpath__crop",
                    self.gui.get_object("ToolpathCropButton"))

    def _update_model_type_controls(self):
        model = self.core.get("model")
        if not model:
            return
        # show or hide z-slice controls
        can_slice = hasattr(model, "get_waterline_contour")
        for name in "ToolpathCropZSliceLabel", "ToolpathCropZSlice":
            if can_slice:
                self.gui.get_object(name).show()
            else:
                self.gui.get_object(name).hide()
        # set lower and upper limit for z-slice
        z_slice_value = self.gui.get_object("ToolpathCropZSliceValue")
        z_slice_value.set_lower(model.minz)
        z_slice_value.set_upper(model.maxz)

    def crop_toolpath(self, widget=None):
        # TODO: how to get the currently selected toolpath???
        toolpath = self.core.get("toolpath")[0]
        model = self.core.get("model")
        if not model:
            return
        if hasattr(model, "get_polygons"):
            contour = model
        elif hasattr(model, "get_waterline_contour"):
            z_slice = self.gui.get_object("ToolpathCropZSlice").get_value()
            plane = Plane(Point(0, 0, z_slice))
            #self.update_progress_bar("Calculating the 2D projection")
            contour = model.get_waterline_contour(plane)
        else:
            self.log.warn(("The current model (%s) does not support " \
                    + "projections") % str(type(model)))
            return
        #self.update_progress_bar("Applying the tool diameter offset")
        margin = self.gui.get_object("ToolpathCropMargin").get_value()
        if margin:
            contour = contour.get_offset_model(margin)
        #self.update_progress_bar("Cropping the toolpath")
        #toolpath.crop(contour.get_polygons(), callback=self.update_progress_bar)
        if self.gui.get_object("ToolpathCropKeepOriginal").get_active():
            new_tp = toolpath.get_cropped_copy(contour.get_polygons(),
                    callback=self.update_progress_bar)
            new_tp.visible = True
            old_index = self.core.get("toolpath").index(toolpath)
            self.core.get("toolpath").insert(old_index + 1, new_tp)
        else:
            toolpath.crop(contour.get_polygons(), callback=self.update_progress_bar)

