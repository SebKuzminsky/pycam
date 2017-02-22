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


class OpenGLViewDimension(pycam.Plugins.PluginBase):

    UI_FILE = "opengl_view_dimension.ui"
    DEPENDS = ["Bounds", "Models", "OpenGLWindow"]
    CATEGORIES = ["Model", "Visualization", "OpenGL"]

    def setup(self):
        if self.gui:
            import pango
            self.core.register_ui("opengl_window", "Dimension",
                                  self.gui.get_object("DimensionTable"), weight=20)
            self.core.get("register_display_item")("show_dimensions", "Show Dimensions", 60)
            # Color the dimension value according to the axes.
            # For "y" axis: 100% green is too bright on light background - we
            # reduce it a bit.
            for color, names in (
                    (pango.AttrForeground(65535, 0, 0, 0, 100),
                     ("model_dim_x_label", "model_dim_x", "ModelCornerXMax", "ModelCornerXMin",
                      "ModelCornerXSpaces")),
                    (pango.AttrForeground(0, 50000, 0, 0, 100),
                     ("model_dim_y_label", "model_dim_y", "ModelCornerYMax", "ModelCornerYMin",
                      "ModelCornerYSpaces")),
                    (pango.AttrForeground(0, 0, 65535, 0, 100),
                     ("model_dim_z_label", "model_dim_z", "ModelCornerZMax", "ModelCornerZMin",
                      "ModelCornerZSpaces"))):
                attributes = pango.AttrList()
                attributes.insert(color)
                for name in names:
                    self.gui.get_object(name).set_attributes(attributes)
            self._event_handlers = (
                ("model-change-after", self.update_model_dimensions),
                ("visual-item-updated", self.update_model_dimensions),
                ("model-list-chaned", self.update_model_dimensions))
            self.register_event_handlers(self._event_handlers)
        return True

    def teardown(self):
        if self.gui:
            self.unregister_event_handlers(self._event_handlers)
            self.core.unregister_ui("opengl_window", self.gui.get_object("DimensionTable"))
            self.core.get("unregister_display_item")("show_dimensions")

    def update_model_dimensions(self, widget=None):
        dimension_bar = self.gui.get_object("DimensionTable")
        models = [m.model for m in self.core.get("models").get_visible()]
        model_low, model_high = pycam.Geometry.Model.get_combined_bounds(models)
        if None in model_low or None in model_high:
            model_low, model_high = (0, 0, 0), (0, 0, 0)
        bounds = self.core.get("bounds").get_selected()
        if self.core.get("show_dimensions"):
            for value, label_suffix in ((model_low[0], "XMin"), (model_high[0], "XMax"),
                                        (model_low[1], "YMin"), (model_high[1], "YMax"),
                                        (model_low[2], "ZMin"), (model_high[2], "ZMax")):
                label_name = "ModelCorner%s" % label_suffix
                value = "%.3f" % value
                self.gui.get_object(label_name).set_label(value)
            if bounds:
                bounds_low, bounds_high = bounds.get_absolute_limits()
                if None in bounds_low or None in bounds_high:
                    bounds_size = ("", "", "")
                else:
                    bounds_size = ["%.3f %s" % (high - low, self.core.get("unit_string"))
                                   for low, high in zip(bounds_low, bounds_high)]
                for axis, size_string in zip("xyz", bounds_size):
                    self.gui.get_object("model_dim_" + axis).set_text(size_string)
            dimension_bar.show()
        else:
            dimension_bar.hide()
