"""
Copyright 2018 Lars Kruse <devel@sumpfralle.de>

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

from pycam.errors import InvalidDataError
import pycam.Plugins


class VisualizeModel(pycam.Plugins.PluginBase):

    DEPENDS = {"Models", "Visualization"}
    CATEGORIES = {"Model", "Visualization"}

    def setup(self):
        self._event_handlers = (
            ("model-changed", "visual-item-updated"),
            ("model-list-changed", "visual-item-updated"),
        )
        self.core.get("register_display_item")("show_model", "Show Model", 10)
        self.core.get("register_color")("color_model", "Model", 10)
        self.core.register_chain("get_draw_dimension", self.get_draw_dimension)
        self.core.register_chain("generate_x3d", self.generate_x3d)
        self.register_event_handlers(self._event_handlers)
        self.core.emit_event("visual-item-updated")
        return super().setup()

    def teardown(self):
        self.unregister_event_handlers(self._event_handlers)
        self.core.unregister_chain("generate_x3d", self.generate_x3d)
        self.core.unregister_chain("get_draw_dimension", self.get_draw_dimension)
        self.core.get("unregister_display_item")("show_model")
        self.core.get("unregister_color")("color_model")
        self.core.emit_event("visual-item-updated")
        super().teardown()

    def _get_cache_key(self, model, *args, **kwargs):
        if hasattr(model, "uuid"):
            return "%s - %s - %s" % (model.uuid, repr(args), repr(kwargs))
        else:
            return None

    def _is_visible(self):
        return (self.core.get("show_model")
                and not (self.core.get("show_simulation")
                         and self.core.get("simulation_toolpath_moves")))

    def get_draw_dimension(self, low, high):
        if self._is_visible():
            for model_dict in self.core.get("models").get_visible():
                try:
                    model_box = model_dict.get_model().get_bounds().get_bounds()
                except InvalidDataError as exc:
                    self.log.warning("Failed to visualize model: %s", exc)
                    continue
                for index, (mlow, mhigh) in enumerate(zip(model_box.lower, model_box.upper)):
                    if (low[index] is None) or ((mlow is not None) and (mlow < low[index])):
                        low[index] = mlow
                    if (high[index] is None) or ((mhigh is not None) and (mhigh > high[index])):
                        high[index] = mhigh

    def generate_x3d(self, tree):
        if not self.core.get("show_model"):
            return
        if self.core.get("show_simulation") and self.core.get("simulation_toolpath_moves"):
            return
        fallback_color = self.core.get("models").FALLBACK_COLOR
        for model_dict in self.core.get("models").get_visible():
            try:
                model = model_dict.get_model()
            except InvalidDataError as exc:
                self.log.warning("Failed to visualize model: %s", exc)
                continue
            color = model_dict.get_application_value("color", default=fallback_color)
            tree.add_data_source(model.to_x3d(color))
