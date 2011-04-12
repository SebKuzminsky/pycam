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


import math

import pycam.Plugins
import pycam.Utils.log


log = pycam.Utils.log.get_logger()

EXTRUSION_TYPES = (("radius_up", "Radius (bulge)", "ExtrusionRadiusUpIcon"),
        ("radius_down", "Radius (valley)", "ExtrusionRadiusDownIcon"),
        ("skewed", "Chamfer", "ExtrusionChamferIcon"),
        ("sine", "Sine", "ExtrusionSineIcon"),
        ("sigmoid", "Sigmoid", "ExtrusionSigmoidIcon"),
)


class ModelExtrusion(pycam.Plugins.PluginBase):

    UI_FILE = "model_extrusion.ui"

    def setup(self):
        if self.gui:
            extrusion_frame = self.gui.get_object("ModelExtrusionFrame")
            extrusion_frame.unparent()
            self.core.register_event("model-change-after",
                    self._update_extrude_widgets)
            self.core.register_ui("model_handling", "Extrusion",
                    extrusion_frame, 5)
            self.gui.get_object("ExtrudeButton").connect("clicked",
                    self._extrude_model)
            self.gui.get_object("ExtrusionHeight").set_value(1)
            self.gui.get_object("ExtrusionWidth").set_value(1)
            self.gui.get_object("ExtrusionGrid").set_value(0.5)
            extrusion_model = self.gui.get_object("ExtrusionTypeModel")
            for row in EXTRUSION_TYPES:
                extrusion_model.append((row[0], row[1],
                        self.gui.get_object(row[2]).get_pixbuf()))
            self.gui.get_object("ExtrusionTypeSelector").set_active(0)
        return True

    def teardown(self):
        if self.gui:
            self.core.unregister_ui("model_handling",
                    self.gui.get_object("ModelExtrusionFrame"))
            self.core.unregister_event("model-change-after",
                    self._update_extrude_widgets)

    def _update_extrude_widgets(self):
        model = self.core.get("model")
        is_extrudable = (not model is None) \
               and hasattr(model, "extrude")
        extrude_widget = self.gui.get_object("ModelExtrusionFrame")
        if is_extrudable:
            extrude_widget.show()
        else:
            extrude_widget.hide()

    def _extrude_model(self, widget=None):
        model = self.core.get("model")
        if not model:
            return
        self.core.get("update_progress")("Extruding model")
        extrusion_type_selector = self.gui.get_object("ExtrusionTypeSelector")
        type_model = extrusion_type_selector.get_model()
        type_active = extrusion_type_selector.get_active()
        if type_active >= 0:
            type_string = type_model[type_active][0]
            height = self.gui.get_object("ExtrusionHeight").get_value()
            width = self.gui.get_object("ExtrusionWidth").get_value()
            grid_size = self.gui.get_object("ExtrusionGrid").get_value()
            if type_string == "radius_up":
                func = lambda x: height * math.sqrt((width ** 2 - max(0, width - x) ** 2))
            elif type_string == "radius_down":
                func = lambda x: height * (1 - math.sqrt((width ** 2 - min(width, x) ** 2)) / width)
            elif type_string == "skewed":
                func = lambda x: height * min(1, x / width)
            elif type_string == "sine":
                func = lambda x: height * math.sin(min(x, width) / width * math.pi / 2)
            elif type_string == "sigmoid":
                func = lambda x: height * ((math.sin(((min(x, width) / width) - 0.5) * math.pi) + 1) / 2)
            else:
                log.error("Unknown extrusion type selected: %s" % type_string)
                return
            new_model = model.extrude(stepping=grid_size, func=func,
                    callback=self.core.get("update_progress"))
            if new_model:
                self.core.get("load_model")(new_model)

