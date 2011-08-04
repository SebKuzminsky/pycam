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


class OpenGLViewToolpath(pycam.Plugins.PluginBase):

    DEPENDS = ["OpenGLWindow", "Toolpaths"]
    CATEGORIES = ["Toolpath", "Visualization", "OpenGL"]

    def setup(self):
        import OpenGL.GL
        self._GL = OpenGL.GL
        self.core.register_event("visualize-items", self.draw_toolpath)
        self.core.emit_event("visual-item-updated")
        return True

    def teardown(self):
        self.core.unregister_event("visualize-items", self.draw_toolpath)
        self.core.emit_event("visual-item-updated")

    def draw_toolpath(self):
        if self.core.get("show_toolpath") \
                and not self.core.get("toolpath_in_progress") \
                and not (self.core.get("show_simulation") \
                        and self.core.get("simulation_toolpath_moves")):
            GL = self._GL
            for toolpath in self.core.get("toolpaths").get_visible():
                color_rapid = self.core.get("color_toolpath_return")
                color_cut = self.core.get("color_toolpath_cut")
                show_directions = self.core.get("show_directions")
                lighting = self.core.get("view_light")
                moves = toolpath.get_moves(self.core.get("gcode_safety_height"))
                GL.glMatrixMode(GL.GL_MODELVIEW)
                GL.glLoadIdentity()
                last_position = None
                last_rapid = None
                if lighting:
                    GL.glDisable(GL.GL_LIGHTING)
                GL.glBegin(GL.GL_LINE_STRIP)
                for position, rapid in moves:
                    if last_rapid != rapid:
                        GL.glEnd()
                        if rapid:
                            GL.glColor4f(*color_rapid)
                        else:
                            GL.glColor4f(*color_cut)
                        # we need to wait until the color change is active
                        GL.glFinish()
                        GL.glBegin(GL.GL_LINE_STRIP)
                        if not last_position is None:
                            GL.glVertex3f(last_position.x, last_position.y, last_position.z)
                        last_rapid = rapid
                    GL.glVertex3f(position.x, position.y, position.z)
                    last_position = position
                GL.glEnd()
                if lighting:
                    GL.glEnable(GL.GL_LIGHTING)
                if show_directions:
                    for index in range(len(moves) - 1):
                        p1 = moves[index][0]
                        p2 = moves[index + 1][0]
                        draw_direction_cone(p1, p2)

