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


class OpenGLViewDimension(pycam.Plugins.PluginBase):

    UI_FILE = "opengl_view_dimension.ui"
    DEPENDS = ["Models", "OpenGLWindow"]
    CATEGORIES = ["Model", "Visualization", "OpenGL"]

    def setup(self):
        if self.gui:
            import pango
            self.core.register_ui("opengl_window", "Dimension",
                    self.gui.get_object("DimensionTable"), weight=20)
            self.core.get("register_display_item")("show_dimensions",
                    "Show Dimensions", 60),
            # Color the dimension value according to the axes.
            # For "y" axis: 100% green is too bright on light background - we
            # reduce it a bit.
            for color, names in (
                    (pango.AttrForeground(65535, 0, 0, 0, 100),
                            ("model_dim_x_label", "model_dim_x", "ModelCornerXMax",
                                "ModelCornerXMin", "ModelCornerXSpaces")),
                    (pango.AttrForeground(0, 50000, 0, 0, 100),
                            ("model_dim_y_label", "model_dim_y", "ModelCornerYMax",
                                "ModelCornerYMin", "ModelCornerYSpaces")),
                    (pango.AttrForeground(0, 0, 65535, 0, 100),
                            ("model_dim_z_label", "model_dim_z", "ModelCornerZMax",
                                "ModelCornerZMin", "ModelCornerZSpaces"))):
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
            self.core.unregister_ui("opengl_window",
                    self.gui.get_object("DimensionTable"))
            self.core.get("unregister_display_item")("show_dimensions")

    def update_model_dimensions(self, widget=None):
        dimension_bar = self.gui.get_object("DimensionTable")
        models = [m.model for m in self.core.get("models").get_visible()]
        low, high = pycam.Geometry.Model.get_combined_bounds(models)
        if None in low or None in high:
            low, high = (0, 0, 0), (0, 0, 0)
        if self.core.get("show_dimensions"):
            for value, label_suffix in ((low[0], "XMin"), (low[1], "YMin"),
                    (low[2], "ZMin"), (high[0], "XMax"), (high[1], "YMax"),
                    (high[2], "ZMax")):
                label_name = "ModelCorner%s" % label_suffix
                value = "%.3f" % value
                self.gui.get_object(label_name).set_label(value)
            for name, size in (
                    ("model_dim_x", high[0] - low[0]),
                    ("model_dim_y", high[1] - low[1]),
                    ("model_dim_z", high[2] - low[2])):
                self.gui.get_object(name).set_text("%.3f %s" \
                        % (size, self.core.get("unit_string")))

            dimension_bar.show()
        else:
            dimension_bar.hide()
