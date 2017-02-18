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


class OpenGLViewBounds(pycam.Plugins.PluginBase):

    DEPENDS = ["OpenGLWindow", "Bounds"]
    CATEGORIES = ["Bounds", "Visualization", "OpenGL"]

    def setup(self):
        import OpenGL.GL
        self._GL = OpenGL.GL
        self.core.get("register_color")("color_bounding_box", "Bounding box", 40)
        self.core.get("register_display_item")("show_bounding_box", "Show Bounding Box", 40)
        self.core.register_chain("get_draw_dimension", self.get_draw_dimension)
        self.core.register_event("visualize-items", self.draw_bounds)
        self.core.emit_event("visual-item-updated")
        return True

    def teardown(self):
        self.core.unregister_event("visualize-items", self.draw_bounds)
        self.core.unregister_chain("get_draw_dimension", self.get_draw_dimension)
        self.core.get("unregister_color")("color_bounding_box")
        self.core.get("unregister_display_item")("show_bounding_box")
        self.core.emit_event("visual-item-updated")

    def get_draw_dimension(self, low, high):
        if not self.core.get("show_bounding_box"):
            return
        mlow, mhigh = self._get_bounds()
        if None in mlow or None in mhigh:
            return
        for index in range(3):
            if (low[index] is None) or (mlow[index] < low[index]):
                low[index] = mlow[index]
            if (high[index] is None) or (mhigh[index] > high[index]):
                high[index] = mhigh[index]

    def _get_bounds(self):
        bounds = self.core.get("bounds").get_selected()
        if not bounds:
            return ([None, None, None], [None, None, None])
        low, high = bounds.get_absolute_limits()
        return low, high

    def draw_bounds(self):
        GL = self._GL
        if not self.core.get("show_bounding_box"):
            return
        low, high = self._get_bounds()
        if None in low or None in high:
            return
        minx, miny, minz = low[0], low[1], low[2]
        maxx, maxy, maxz = high[0], high[1], high[2]
        p1 = [minx, miny, minz]
        p2 = [minx, maxy, minz]
        p3 = [maxx, maxy, minz]
        p4 = [maxx, miny, minz]
        p5 = [minx, miny, maxz]
        p6 = [minx, maxy, maxz]
        p7 = [maxx, maxy, maxz]
        p8 = [maxx, miny, maxz]
        if self.core.get("view_light"):
            GL.glDisable(GL.GL_LIGHTING)
        # lower rectangle
        color = self.core.get("color_bounding_box")
        GL.glColor4f(color["red"], color["green"], color["blue"], color["alpha"])
        GL.glFinish()
        GL.glBegin(GL.GL_LINES)
        # all combinations of neighbouring corners
        for corner_pair in [(p1, p2), (p1, p5), (p1, p4), (p2, p3), (p2, p6), (p3, p4), (p3, p7),
                            (p4, p8), (p5, p6), (p6, p7), (p7, p8), (p8, p5)]:
            GL.glVertex3f(*(corner_pair[0]))
            GL.glVertex3f(*(corner_pair[1]))
        GL.glEnd()
        if self.core.get("view_light"):
            GL.glEnable(GL.GL_LIGHTING)
