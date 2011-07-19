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


GTK_COLOR_MAX = 65535.0


class OpenGLViewModel(pycam.Plugins.PluginBase):

    DEPENDS = ["OpenGLWindow", "Models"]

    def setup(self):
        import gtk
        import OpenGL.GL
        self._gtk = gtk
        self._GL = OpenGL.GL
        self.core.register_event("visualize-items", self.draw_model)
        return True

    def teardown(self):
        self.core.unregister_event("visualize-items", self.draw_model)
        return True

    def draw_model(self):
        if self.core.get("show_model") \
                and not (self.core.get("show_simulation") \
                    and self.core.get("simulation_toolpath_moves")):
            for model in self.core.get("models").get_visible():
                color_str = self.core.get("models").get_attr(model, "color")
                alpha = self.core.get("models").get_attr(model, "alpha")
                col = self._gtk.gdk.color_parse(color_str)
                self._GL.glColor4f(col.red / GTK_COLOR_MAX, col.green / GTK_COLOR_MAX,
                        col.blue / GTK_COLOR_MAX, alpha / GTK_COLOR_MAX)
                # we need to wait until the color change is active
                self._GL.glFinish()
                model.to_OpenGL(show_directions=self.core.get("show_directions"))

