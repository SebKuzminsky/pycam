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
import pycam.Gui.OpenGLTools


class OpenGLViewToolpath(pycam.Plugins.PluginBase):

    DEPENDS = ["OpenGLWindow", "Toolpaths"]
    CATEGORIES = ["Toolpath", "Visualization", "OpenGL"]

    def setup(self):
        import OpenGL.GL
        self._GL = OpenGL.GL
        self.core.register_event("visualize-items", self.draw_toolpath)
        self.core.get("register_color")("color_toolpath_cut", "Toolpath cut",
                60)
        self.core.get("register_color")("color_toolpath_return",
                "Toolpath rapid", 70)
        self.core.register_chain("get_draw_dimension", self.get_draw_dimension)
        self.core.get("register_display_item")("show_toolpath", "Show Toolpath", 30),
        self.core.emit_event("visual-item-updated")
        return True

    def teardown(self):
        self.core.unregister_chain("get_draw_dimension",
                self.get_draw_dimension)
        self.core.unregister_event("visualize-items", self.draw_toolpath)
        self.core.get("unregister_color")("color_toolpath_cut")
        self.core.get("unregister_color")("color_toolpath_return")
        self.core.get("unregister_display_item")("show_toolpath")
        self.core.emit_event("visual-item-updated")

    def get_draw_dimension(self, low, high):
        if self._is_visible():
            toolpaths = self.core.get("toolpaths").get_visible()
            for tp in toolpaths:
                mlow = tp.minx, tp.miny, tp.minz
                mhigh = tp.maxx, tp.maxy, tp.maxz
                if None in mlow or None in mhigh:
                    continue
                for index in range(3):
                    if (low[index] is None) or (mlow[index] < low[index]):
                        low[index] = mlow[index]
                    if (high[index] is None) or (mhigh[index] > high[index]):
                        high[index] = mhigh[index]

    def _is_visible(self):
        return self.core.get("show_toolpath") \
                and not self.core.get("toolpath_in_progress") \
                and not (self.core.get("show_simulation") \
                        and self.core.get("simulation_toolpath_moves"))

    def draw_toolpath(self):
        if self._is_visible():
            GL = self._GL
            GL.glDisable(GL.GL_LIGHTING)
            show_directions = self.core.get("show_directions")
            color_rapid = self.core.get("color_toolpath_return")
            color_cut = self.core.get("color_toolpath_cut")
            for toolpath in self.core.get("toolpaths").get_visible():
                moves = toolpath.get_moves(self.core.get("gcode_safety_height"))
                GL.glMatrixMode(GL.GL_MODELVIEW)
                GL.glLoadIdentity()
                last_position = None
                last_rapid = None
                GL.glBegin(GL.GL_LINE_STRIP)
                for position, rapid in moves:
                    if last_rapid != rapid:
                        GL.glEnd()
                        if rapid:
                            GL.glColor4f(color_rapid["red"], color_rapid["green"],
                                    color_rapid["blue"], color_rapid["alpha"])
                        else:
                            GL.glColor4f(color_cut["red"], color_cut["green"],
                                    color_cut["blue"], color_cut["alpha"])
                        # we need to wait until the color change is active
                        GL.glFinish()
                        GL.glBegin(GL.GL_LINE_STRIP)
                        if not last_position is None:
                            GL.glVertex3f(last_position.x, last_position.y, last_position.z)
                        last_rapid = rapid
                    GL.glVertex3f(position.x, position.y, position.z)
                    last_position = position
                GL.glEnd()
                if show_directions:
                    for index in range(len(moves) - 1):
                        p1 = moves[index][0]
                        p2 = moves[index + 1][0]
                        pycam.Gui.OpenGLTools.draw_direction_cone(p1, p2)

