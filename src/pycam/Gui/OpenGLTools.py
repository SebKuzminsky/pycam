# -*- coding: utf-8 -*-
"""
$Id$

Copyright 2010-2011 Lars Kruse <devel@sumpfralle.de>

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

from pycam.Geometry.Point import Point
from pycam.Geometry.utils import sqrt
import pycam.Geometry.Model
import pycam.Utils.log

# careful import
try:
    import OpenGL.GL as GL
    import OpenGL.GLUT as GLUT
except (ImportError, RuntimeError):
    pass

import gtk
import math


log = pycam.Utils.log.get_logger()


def connect_button_handlers(signal, original_button, derived_button):
    """ Join two buttons (probably "toggle" buttons) to keep their values
    synchronized.
    """
    def derived_handler(widget, original_button=original_button):
        original_button.set_active(not original_button.get_active())
    derived_handler_id = derived_button.connect_object_after(
            signal, derived_handler, derived_button)
    def original_handler(original_button, derived_button=derived_button,
            derived_handler_id=derived_handler_id):
        derived_button.handler_block(derived_handler_id)
        # prevent any recursive handler-triggering
        if derived_button.get_active() != original_button.get_active():
            derived_button.set_active(not derived_button.get_active())
        derived_button.handler_unblock(derived_handler_id)
    original_button.connect_object_after(signal, original_handler,
            original_button)


def keep_gl_mode(func):
    def keep_gl_mode_wrapper(*args, **kwargs):
        prev_mode = GL.glGetIntegerv(GL.GL_MATRIX_MODE)
        result = func(*args, **kwargs)
        GL.glMatrixMode(prev_mode)
        return result
    return keep_gl_mode_wrapper

def keep_matrix(func):
    def keep_matrix_wrapper(*args, **kwargs):
        pushed_matrix_mode = GL.glGetIntegerv(GL.GL_MATRIX_MODE)
        GL.glPushMatrix()
        result = func(*args, **kwargs)
        final_matrix_mode = GL.glGetIntegerv(GL.GL_MATRIX_MODE)
        GL.glMatrixMode(pushed_matrix_mode)
        GL.glPopMatrix()
        GL.glMatrixMode(final_matrix_mode)
        return result
    return keep_matrix_wrapper

@keep_matrix
def draw_direction_cone(p1, p2):
    distance = p2.sub(p1)
    length = distance.norm
    direction = distance.normalized()
    if direction is None:
        # zero-length line
        return
    cone_radius = length / 30
    cone_length = length / 10
    # move the cone to the middle of the line
    GL.glTranslatef((p1.x + p2.x) / 2, (p1.y + p2.y) / 2, (p1.z + p2.z) / 2)
    # rotate the cone according to the line direction
    # The cross product is a good rotation axis.
    cross = direction.cross(Point(0, 0, -1))
    if cross.norm != 0:
        # The line direction is not in line with the z axis.
        try:
            angle = math.asin(sqrt(direction.x ** 2 + direction.y ** 2))
        except ValueError:
            # invalid angle - just ignore this cone
            return
        # convert from radians to degree
        angle = angle / math.pi * 180
        if direction.z < 0:
            angle = 180 - angle
        GL.glRotatef(angle, cross.x, cross.y, cross.z)
    elif direction.z == -1:
        # The line goes down the z axis - turn it around.
        GL.glRotatef(180, 1, 0, 0)
    else:
        # The line goes up the z axis - nothing to be done.
        pass
    # center the cone
    GL.glTranslatef(0, 0, -cone_length / 2)
    # draw the cone
    GLUT.glutSolidCone(cone_radius, cone_length, 12, 1)

@keep_gl_mode
@keep_matrix
def draw_complete_model_view(settings):
    GL.glMatrixMode(GL.GL_MODELVIEW)
    GL.glLoadIdentity()
    # draw the material (for simulation mode)
    if settings.get("show_simulation"):
        obj = settings.get("simulation_object")
        if not obj is None:
            GL.glColor4f(*settings.get("color_material"))
            # we need to wait until the color change is active
            GL.glFinish()
            obj.to_OpenGL()
    # draw the support grid
    if settings.get("show_support_grid") and settings.get("current_support_model"):
        GL.glColor4f(*settings.get("color_support_grid"))
        # we need to wait until the color change is active
        GL.glFinish()
        settings.get("current_support_model").to_OpenGL()
    # draw the toolpath simulation
    if settings.get("show_simulation"):
        moves = settings.get("simulation_toolpath_moves")
        if not moves is None:
            draw_toolpath(moves, settings.get("color_toolpath_cut"),
                    settings.get("color_toolpath_return"),
                    show_directions=settings.get("show_directions"),
                    lighting=settings.get("view_light"))
    # draw the toolpath
    # don't do it, if a new toolpath is just being calculated
    safety_height = settings.get("gcode_safety_height")
    if settings.get("toolpath") and settings.get("show_toolpath") \
            and not settings.get("toolpath_in_progress") \
            and not (settings.get("show_simulation") \
                    and settings.get("simulation_toolpath_moves")):
        for toolpath_obj in settings.get("toolpath"):
            if toolpath_obj.visible:
                draw_toolpath(toolpath_obj.get_moves(safety_height),
                        settings.get("color_toolpath_cut"),
                        settings.get("color_toolpath_return"),
                        show_directions=settings.get("show_directions"),
                        lighting=settings.get("view_light"))
    # draw the drill
    if settings.get("show_drill"):
        cutter = settings.get("cutter")
        if not cutter is None:
            GL.glColor4f(*settings.get("color_cutter"))
            GL.glFinish()
            cutter.to_OpenGL()
    if settings.get("show_drill_progress") \
            and settings.get("toolpath_in_progress"):
        # show the toolpath that is currently being calculated
        toolpath_in_progress = settings.get("toolpath_in_progress")
        # do a quick conversion from a list of Paths to a list of points
        moves = []
        for path in toolpath_in_progress:
            for point in path.points:
                moves.append((point, False))
        if not toolpath_in_progress is None:
            draw_toolpath(moves, settings.get("color_toolpath_cut"),
                    settings.get("color_toolpath_return"),
                    show_directions=settings.get("show_directions"),
                    lighting=settings.get("view_light"))

@keep_gl_mode
@keep_matrix
def draw_toolpath(moves, color_cut, color_rapid, show_directions=False, lighting=True):
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

