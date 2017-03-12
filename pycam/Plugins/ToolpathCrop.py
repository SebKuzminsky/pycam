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


from pycam.Geometry.Plane import Plane
import pycam.Gui.ControlsGTK
import pycam.Plugins
import pycam.Toolpath.Filters as Filters


class ToolpathCrop(pycam.Plugins.PluginBase):

    UI_FILE = "toolpath_crop.ui"
    DEPENDS = ["Models", "Toolpaths"]
    CATEGORIES = ["Toolpath"]

    def setup(self):
        if self.gui:
            self._frame = self.gui.get_object("ToolpathCropFrame")
            self.core.register_ui("toolpath_handling", "Crop", self._frame, 40)
            self._gtk_handlers = []
            for objname in ("ToolpathCropZSlice", "ToolpathCropMargin"):
                obj = self.gui.get_object(objname)
                obj.set_value(0)
                self._gtk_handlers.append((obj, "value-changed", self._update_widgets))
            self._gtk_handlers.append((self.gui.get_object("CropButton"), "clicked",
                                       self.crop_toolpath))
            # model selector
            self.models_widget = pycam.Gui.ControlsGTK.InputTable(
                [], change_handler=self._update_widgets)

            def get_converter(model_refs):
                models_dict = {}
                for model in self.core.get("models"):
                    models_dict[id(model)] = model
                models = []
                for model_ref in model_refs:
                    models.append(models_dict[model_ref])
                return models

            def set_converter(models):
                return [id(model) for model in models]

            self.models_widget.set_conversion(set_conv=set_converter, get_conv=get_converter)
            self.gui.get_object("ModelTableContainer").add(self.models_widget.get_widget())
            self._event_handlers = (
                ("model-list-changed", self._update_models_list),
                ("toolpath-selection-changed", self._update_visibility))
            self.register_gtk_handlers(self._gtk_handlers)
            self.register_event_handlers(self._event_handlers)
            self._update_widgets()
            self._update_visibility()
        return True

    def teardown(self):
        if self.gui:
            self.gui.get_object("ModelTableContainer").remove(self.models_widget.get_widget())
            self.core.unregister_ui("toolpath_handling", self._frame)
            self.unregister_gtk_handlers(self._gtk_handlers)
            self.unregister_event_handlers(self._event_handlers)

    def _update_models_list(self):
        choices = []
        models = self.core.get("models")
        for model in models:
            choices.append((model["name"], model))
        self.models_widget.update_choices(choices)

    def _update_visibility(self):
        if self.core.get("toolpaths").get_selected():
            self._frame.show()
        else:
            self._frame.hide()

    def _update_widgets(self, widget=None):
        models = [m.model for m in self.models_widget.get_value()]
        info_label = self.gui.get_object("ToolpathCropInfo")
        info_box = self.gui.get_object("ToolpathCropInfoBox")
        button = self.gui.get_object("CropButton")
        slicing_models = [model for model in models if hasattr(model, "get_waterline_contour")]
        # show or hide z-slice controls
        slice_controls = ("ToolpathCropZSliceLabel", "ToolpathCropZSlice")
        if slicing_models:
            # set lower and upper limit for z-slice
            z_slice = self.gui.get_object("ToolpathCropZSlice")
            minz = min([model.minz for model in slicing_models])
            maxz = max([model.maxz for model in slicing_models])
            z_slice.set_range(minz, maxz)
            if z_slice.get_value() > maxz:
                z_slice.set_value(maxz)
            elif z_slice.get_value() < minz:
                z_slice.set_value(minz)
            else:
                pass
            for name in slice_controls:
                self.gui.get_object(name).show()
        else:
            for name in slice_controls:
                self.gui.get_object(name).hide()
        # update info
        if not models:
            info_box.show()
            info_label.set_label("Hint: select a model")
            button.set_sensitive(False)
        else:
            polygons = self._get_waterlines()
            if polygons:
                info_box.hide()
                button.set_sensitive(True)
            else:
                info_label.set_label("Hint: there is no usable contour at this splice level")
                info_box.show()
                button.set_sensitive(False)

    def _get_waterlines(self):
        models = [m.model for m in self.models_widget.get_value()]
        polygons = []
        # get all waterlines and polygons
        for model in models:
            if hasattr(model, "get_polygons"):
                for poly in model.get_polygons():
                    polygons.append(poly.copy())
            elif hasattr(model, "get_waterline_contour"):
                z_slice = self.gui.get_object("ToolpathCropZSlice").get_value()
                plane = Plane((0, 0, z_slice))
                for poly in model.get_waterline_contour(plane).get_polygons():
                    polygons.append(poly.copy())
        # add an offset if requested
        margin = self.gui.get_object("ToolpathCropMargin").get_value()
        if margin != 0:
            shifted = []
            for poly in polygons:
                shifted.extend(poly.get_offset_polygons(margin))
            polygons = shifted
        return polygons

    def crop_toolpath(self, widget=None):
        selected = self.core.get("toolpaths").get_selected()
        polygons = self._get_waterlines()
        keep_original = self.gui.get_object("ToolpathCropKeepOriginal").get_active()
        for toolpath in self.core.get("toolpaths").get_selected():
            # Store the new toolpath first separately - otherwise we can't
            # revert the changes in case of an empty result.
            new_moves = toolpath | Filters.Crop(polygons)
            if new_moves | Filters.MovesOnly():
                if keep_original:
                    new_toolpath = toolpath.copy()
                    new_toolpath.path = new_moves
                    self.core.get("toolpaths").add_new(new_toolpath)
                else:
                    toolpath.path = new_moves
                    self.core.emit_event("toolpath-changed")
            else:
                self.log.info("Toolpath cropping: the result is empty")
        self.core.get("toolpaths").select(selected)
