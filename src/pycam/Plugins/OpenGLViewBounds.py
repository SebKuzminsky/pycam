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


class OpenGLViewBounds(pycam.Plugins.PluginBase):

    DEPENDS = ["OpenGLWindow", "Bounds"]

    def setup(self):
        import OpenGL.GL
        self._GL = OpenGL.GL
        self.core.register_event("visualize-items", self.draw_bounds)
        return True

    def teardown(self):
        self.core.unregister_event("visualize-items", self.draw_bounds)

    def draw_bounds(self):
        GL = self._GL
        if not self.core.get("show_bounding_box"):
            return
        bounds = self.core.get("bounds").get_selected()
        if not bounds:
            return
        low, high = bounds.get_absolute_limits()
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
        GL.glColor4f(*self.core.get("color_bounding_box"))
        GL.glFinish()
        GL.glBegin(GL.GL_LINES)
        # all combinations of neighbouring corners
        for corner_pair in [(p1, p2), (p1, p5), (p1, p4), (p2, p3),
                    (p2, p6), (p3, p4), (p3, p7), (p4, p8), (p5, p6),
                    (p6, p7), (p7, p8), (p8, p5)]:
            GL.glVertex3f(*(corner_pair[0]))
            GL.glVertex3f(*(corner_pair[1]))
        GL.glEnd()
        if self.core.get("view_light"):
            GL.glEnable(GL.GL_LIGHTING)

