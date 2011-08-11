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
from pycam.Geometry.utils import number


class OpenGLViewAxes(pycam.Plugins.PluginBase):

    DEPENDS = ["OpenGLWindow"]
    CATEGORIES = ["Visualization", "OpenGL"]

    def setup(self):
        import OpenGL.GL
        import OpenGL.GLUT
        self._GL = OpenGL.GL
        self._GLUT = OpenGL.GLUT
        self.core.register_event("visualize-items", self.draw_axes)
        self.core.get("register_display_item")("show_axes",
                "Show Coordinate System", 50)
        self.core.emit_event("visual-item-updated")
        return True

    def teardown(self):
        self.core.unregister_event("visualize-items", self.draw_axes)
        self.core.get("unregister_display_item")("show_axes")
        self.core.emit_event("visual-item-updated")

    def draw_axes(self):
        if not self.core.get("show_axes"):
            return
        GL = self._GL
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()
        low, high = [None, None, None], [None, None, None]
        self.core.call_chain("get_draw_dimension", low, high)
        if None in low or None in high:
            low, high = (0, 0, 0), (10, 10, 10)
        size_x = abs(high[0])
        size_y = abs(high[1])
        size_z = abs(high[2])
        size = number(1.7) * max(size_x, size_y, size_z)
        # the divider is just based on playing with numbers
        scale = size / number(1500.0)
        string_distance = number(1.1) * size
        # otherwise plain colors like the next glColor4f wouldn't work
        if self.core.get("view_light"):
            GL.glDisable(GL.GL_LIGHTING)
        GL.glBegin(GL.GL_LINES)
        GL.glColor4f(1, 0, 0, 1)
        GL.glVertex3f(0, 0, 0)
        GL.glVertex3f(size, 0, 0)
        GL.glEnd()
        self.draw_string(string_distance, 0, 0, 'xy', "X", scale=scale)
        GL.glBegin(GL.GL_LINES)
        GL.glColor3f(0, 1, 0)
        GL.glVertex3f(0, 0, 0)
        GL.glVertex3f(0, size, 0)
        GL.glEnd()
        self.draw_string(0, string_distance, 0, 'yz', "Y", scale=scale)
        GL.glBegin(GL.GL_LINES)
        GL.glColor3f(0, 0, 1)
        GL.glVertex3f(0, 0, 0)
        GL.glVertex3f(0, 0, size)
        GL.glEnd()
        self.draw_string(0, 0, string_distance, 'xz', "Z", scale=scale)
        if self.core.get("view_light"):
            GL.glEnable(GL.GL_LIGHTING)

    def draw_string(self, x, y, z, p, s, scale=.01):
        GL = self._GL
        GLUT = self._GLUT
        GL.glPushMatrix()
        GL.glTranslatef(x, y, z)
        if p == 'xy':
            GL.glRotatef(90, 1, 0, 0)
        elif p == 'yz':
            GL.glRotatef(90, 0, 1, 0)
            GL.glRotatef(90, 0, 0, 1)
        elif p == 'xz':
            GL.glRotatef(90, 0, 1, 0)
            GL.glRotatef(90, 0, 0, 1)
            GL.glRotatef(45, 0, 1, 0)
        GL.glScalef(scale, scale, scale)
        for c in str(s):
            GLUT.glutStrokeCharacter(GLUT.GLUT_STROKE_ROMAN, ord(c))
        GL.glPopMatrix()

