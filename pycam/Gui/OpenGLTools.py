# -*- coding: utf-8 -*-
"""
$Id$

Copyright 2010 Lars Kruse <devel@sumpfralle.de>

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
import pycam.Geometry.Matrix as Matrix
import OpenGL.GL as GL
import OpenGL.GLU as GLU
import OpenGL.GLUT as GLUT
import gtk
import pango
import math
import time

# buttons for rotating, moving and zooming the model view window
BUTTON_ROTATE = gtk.gdk.BUTTON1_MASK
BUTTON_MOVE = gtk.gdk.BUTTON2_MASK
BUTTON_ZOOM = gtk.gdk.BUTTON3_MASK

# the length of the distance vector does not matter - it will be normalized and multiplied later anyway
VIEWS = {
    "reset": {"distance": (1.0, 1.0, 1.0), "center": (0.0, 0.0, 0.0), "up": (0.0, 0.0, 1.0), "znear": 0.1, "zfar": 1000.0, "fovy": 30.0},
    "top": {"distance": (0.0, 0.0, 1.0), "center": (0.0, 0.0, 0.0), "up": (1.0, 0.0, 0.0), "znear": 0.1, "zfar": 1000.0, "fovy": 30.0},
    "bottom": {"distance": (0.0, 0.0, -1.0), "center": (0.0, 0.0, 0.0), "up": (1.0, 0.0, 0.0), "znear": 0.1, "zfar": 1000.0, "fovy": 30.0},
    "left": {"distance": (-1.0, 0.0, 0.0), "center": (0.0, 0.0, 0.0), "up": (0.0, 0.0, 1.0), "znear": 0.1, "zfar": 1000.0, "fovy": 30.0},
    "right": {"distance": (1.0, 0.0, 0.0), "center": (0.0, 0.0, 0.0), "up": (0.0, 0.0, 1.0), "znear": 0.1, "zfar": 1000.0, "fovy": 30.0},
    "front": {"distance": (0.0, -1.0, 0.0), "center": (0.0, 0.0, 0.0), "up": (0.0, 0.0, 1.0), "znear": 0.1, "zfar": 1000.0, "fovy": 30.0},
    "back": {"distance": (0.0, 1.0, 0.0), "center": (0.0, 0.0, 0.0), "up": (0.0, 0.0, 1.0), "znear": 0.1, "zfar": 1000.0, "fovy": 30.0},
}


class Camera:

    def __init__(self, settings, get_dim_func, view=None):
        self.view = None
        self.settings = settings
        self._get_dim_func = get_dim_func
        self.set_view(view)

    def set_view(self, view=None):
        if view is None:
            self.view = VIEWS["reset"].copy()
        else:
            self.view = view.copy()
        self.center_view()
        self.auto_adjust_distance()

    def center_view(self):
        s = self.settings
        # center the view on the object
        self.view["center"] = ((s.get("maxx") + s.get("minx"))/2, (s.get("maxy") + s.get("miny"))/2, (s.get("maxz") + s.get("minz"))/2)

    def auto_adjust_distance(self):
        s = self.settings
        v = self.view
        # adjust the distance to get a view of the whole object
        dimx = s.get("maxx") - s.get("minx")
        dimy = s.get("maxy") - s.get("miny")
        dimz = s.get("maxz") - s.get("minz")
        max_dim = max(max(dimx, dimy), dimz)
        width, height = self._get_screen_dimensions()
        win_size = min(width, height)
        distv = Point(v["distance"][0], v["distance"][1], v["distance"][2]).normalize()
        # the multiplier "2.0" is based on: sqrt(2) + margin  -- the squre root makes sure, that the the diagonal fits
        distv = distv.mul((max_dim * 2.0) / math.sin(v["fovy"]/2))
        self.view["distance"] = (distv.x, distv.y, distv.z)
        # adjust the "far" distance for the camera to make sure, that huge models (e.g. x=1000) are still visible
        self.view["zfar"] = 100 * max_dim

    def scale_distance(self, scale):
        if scale != 0:
            dist = self.view["distance"]
            self.view["distance"] = (scale * dist[0], scale * dist[1], scale * dist[2])

    def get(self, key, default=None):
        if (not self.view is None) and self.view.has_key(key):
            return self.view[key]
        else:
            return default

    def set(self, key, value):
        self.view[key] = value

    def move_camera_by_screen(self, x_move, y_move, max_model_shift):
        """ move the camera acoording to a mouse movement
        @type x_move: int
        @value x_move: movement of the mouse along the x axis
        @type y_move: int
        @value y_move: movement of the mouse along the y axis
        @type max_model_shift: float
        @value max_model_shift: maximum shifting of the model view (e.g. for x_move == screen width)
        """
        factors_x, factors_y = self._get_axes_vectors()
        width, height = self._get_screen_dimensions()
        # relation of x/y movement to the respective screen dimension
        win_x_rel = ((-2.0 * x_move) / width) / math.sin(self.view["fovy"])
        win_y_rel = ((-2.0 * y_move) / height) / math.sin(self.view["fovy"])
        # update the model position that should be centered on the screen
        old_center = self.view["center"]
        new_center = []
        for i in range(3):
            new_center.append(old_center[i] + max_model_shift * (win_x_rel * factors_x[i] + win_y_rel * factors_y[i]))
        self.view["center"] = tuple(new_center)

    def rotate_camera_by_screen(self, start_x, start_y, end_x, end_y):
        factors_x, factors_y = self._get_axes_vectors()
        width, height = self._get_screen_dimensions()
        # calculate rotation factors - based on the distance to the center (between -1 and 1)
        rot_x_factor = (2.0 * start_x) / width - 1
        rot_y_factor = (2.0 * start_y) / height - 1
        # calculate rotation angles (between -90 and +90 degrees)
        xdiff = end_x - start_x
        ydiff = end_y - start_y
        # compensate inverse rotation left/right side (around x axis) and top/bottom (around y axis)
        if rot_x_factor < 0:
            ydiff = -ydiff
        if rot_y_factor > 0:
            xdiff = -xdiff
        rot_x_angle = rot_x_factor * math.pi * ydiff / height
        rot_y_angle = rot_y_factor * math.pi * xdiff / width
        # rotate around the "up" vector with the y-axis rotation
        original_distance = self.view["distance"]
        original_up = self.view["up"]
        y_rot_matrix = Matrix.get_rotation_matrix_axis_angle(factors_y, rot_y_angle)
        new_distance = Matrix.multiply_vector_matrix(original_distance, y_rot_matrix)
        new_up = Matrix.multiply_vector_matrix(original_up, y_rot_matrix)
        # rotate around the cross vector with the x-axis rotation
        x_rot_matrix = Matrix.get_rotation_matrix_axis_angle(factors_x, rot_x_angle)
        new_distance = Matrix.multiply_vector_matrix(new_distance, x_rot_matrix)
        new_up = Matrix.multiply_vector_matrix(new_up, x_rot_matrix)
        self.view["distance"] = new_distance
        self.view["up"] = new_up

    def position_camera(self):
        width, height = self._get_screen_dimensions()
        prev_mode = GL.glGetIntegerv(GL.GL_MATRIX_MODE)
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        v = self.view
        # position the light according to the current bounding box
        light_pos = range(3)
        light_pos[0] = 2 * self.settings.get("maxx") - self.settings.get("minx")
        light_pos[1] = 2 * self.settings.get("maxy") - self.settings.get("miny")
        light_pos[2] = 2 * self.settings.get("maxz") - self.settings.get("minz")
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_POSITION, (light_pos[0], light_pos[1], light_pos[2], 1.0))
        # position the camera
        camera_position = (v["center"][0] + v["distance"][0],
                v["center"][1] + v["distance"][1], v["center"][2] + v["distance"][2])
        GLU.gluPerspective(v["fovy"], (0.0 + width) / height, v["znear"], v["zfar"])
        GLU.gluLookAt(camera_position[0], camera_position[1], camera_position[2],
                v["center"][0], v["center"][1], v["center"][2], v["up"][0], v["up"][1], v["up"][2])
        GL.glMatrixMode(prev_mode)

    def _get_screen_dimensions(self):
        return self._get_dim_func()

    def _get_axes_vectors(self):
        """calculate the model vectors along the screen's x and y axes"""
        # the "up" vector defines, in what proportion each axis of the model is in line with the screen's y axis
        v_up = self.view["up"]
        factors_y = (v_up[0], v_up[1], v_up[2])
        # calculate the proportion of each model axis according to the x axis of the screen
        distv = self.view["distance"]
        distv = Point(distv[0], distv[1], distv[2]).normalize()
        factors_x = distv.cross(Point(v_up[0], v_up[1], v_up[2])).normalize()
        factors_x = (factors_x.x, factors_x.y, factors_x.z)
        return (factors_x, factors_y)


class ModelViewWindowGL:
    def __init__(self, gui, settings, notify_destroy=None, accel_group=None):
        # assume, that initialization will fail
        self.gui = gui
        self.window = self.gui.get_object("view3dwindow")
        if not accel_group is None:
            self.window.add_accel_group(accel_group)
        self.initialized = False
        self.busy = False
        self.settings = settings
        self.is_visible = False
        # check if the 3D view is available
        try:
            import gtk.gtkgl
            self.enabled = True
        except ImportError:
            show_error_dialog(self.window, "Failed to initialize the interactive 3D model view."
                    + "\nPlease install 'python-gtkglext1' to enable it.")
            self.enabled = False
            return
        self.mouse = {"start_pos": None, "button": None, "timestamp": 0}
        self.notify_destroy_func = notify_destroy
        self.window.connect("delete-event", self.destroy)
        self.window.set_default_size(560, 400)
        self._position = self.gui.get_object("ProjectWindow").get_position()
        self._position = (self._position[0] + 100, self._position[1] + 100)
        self.container = self.gui.get_object("view3dbox")
        self.gui.get_object("Reset View").connect("clicked", self.rotate_view, VIEWS["reset"])
        self.gui.get_object("Left View").connect("clicked", self.rotate_view, VIEWS["left"])
        self.gui.get_object("Right View").connect("clicked", self.rotate_view, VIEWS["right"])
        self.gui.get_object("Front View").connect("clicked", self.rotate_view, VIEWS["front"])
        self.gui.get_object("Back View").connect("clicked", self.rotate_view, VIEWS["back"])
        self.gui.get_object("Top View").connect("clicked", self.rotate_view, VIEWS["top"])
        self.gui.get_object("Bottom View").connect("clicked", self.rotate_view, VIEWS["bottom"])
        # key binding
        self.window.connect("key-press-event", self.key_handler)
        # OpenGL stuff
        glconfig = gtk.gdkgl.Config(mode=gtk.gdkgl.MODE_RGB|gtk.gdkgl.MODE_DEPTH|gtk.gdkgl.MODE_DOUBLE)
        self.area = gtk.gtkgl.DrawingArea(glconfig)
        # first run; might also be important when doing other fancy gtk/gdk stuff
        self.area.connect_after('realize', self.paint)
        # called when a part of the screen is uncovered
        self.area.connect('expose-event', self.paint)
        # resize window
        self.area.connect('configure-event', self._resize_window)
        # catch mouse events
        self.area.set_events(gtk.gdk.MOUSE | gtk.gdk.BUTTON_PRESS_MASK)
        self.area.connect("button-press-event", self.mouse_handler)
        self.area.connect('motion-notify-event', self.mouse_handler)
        self.area.show()
        self.container.add(self.area)
        self.camera = Camera(self.settings, lambda: (self.area.allocation.width, self.area.allocation.height))
        # color the dimension value according to the axes
        # for "y" axis: 100% green is too bright on light background - we reduce it a bit
        for color, names in (
                (pango.AttrForeground(65535, 0, 0, 0, 100), ("model_dim_x_label", "model_dim_x")),
                (pango.AttrForeground(0, 50000, 0, 0, 100), ("model_dim_y_label", "model_dim_y")),
                (pango.AttrForeground(0, 0, 65535, 0, 100), ("model_dim_z_label", "model_dim_z"))):
            attributes = pango.AttrList()
            attributes.insert(color)
            for name in names:
                self.gui.get_object(name).set_attributes(attributes)
        # show the window
        self.container.show()
        self.show()

    def show(self):
        self.is_visible = True
        self.window.move(*self._position)
        self.window.show()

    def hide(self):
        self.is_visible = False
        self._position = self.window.get_position()
        self.window.hide()

    def key_handler(self, widget=None, event=None):
        if event is None:
            return
        try:
            keyval = getattr(event, "keyval")
            get_state = getattr(event, "get_state")
        except AttributeError:
            return
        if not (0 <= keyval <= 255):
            # e.g. "shift" key
            return
        if chr(keyval) in ('l', 'm', 's'):
            if (chr(keyval) == 'l'):
                key = "view_light"
            elif (chr(keyval) == 'm'):
                key = "view_polygon"
            elif (chr(keyval) == 's'):
                key = "view_shadow"
            else:
                key = None
            # toggle setting
            self.settings.set(key, not self.settings.get(key))
            # re-init gl settings
            self.glsetup()
            self.paint()
        else:
            #print "Key pressed: %s (%s)" % (chr(keyval), get_state())
            pass

    def check_busy(func):
        def check_busy_wrapper(self, *args, **kwargs):
            if not self.enabled or self.busy:
                return
            self.busy = True
            result = func(self, *args, **kwargs)
            self.busy = False
            return result
        return check_busy_wrapper

    def gtkgl_refresh(func):
        def gtkgl_refresh_wrapper(self, *args, **kwargs):
            prev_mode = GL.glGetIntegerv(GL.GL_MATRIX_MODE)
            GL.glMatrixMode(GL.GL_MODELVIEW)
            # clear the background with the configured color
            bg_col = self.settings.get("color_background")
            GL.glClearColor(bg_col[0], bg_col[1], bg_col[2], 0.0)
            GL.glClear(GL.GL_COLOR_BUFFER_BIT|GL.GL_DEPTH_BUFFER_BIT)
            result = func(self, *args, **kwargs)
            self.camera.position_camera()
            self._paint_raw()
            GL.glMatrixMode(prev_mode)
            GL.glFlush()
            self.area.get_gl_drawable().swap_buffers()
            return result
        return gtkgl_refresh_wrapper

    def glsetup(self):
        GLUT.glutInit()
        if self.settings.get("view_shadow"):
            GL.glShadeModel(GL.GL_FLAT)
        else:
            GL.glShadeModel(GL.GL_SMOOTH)
        bg_col = self.settings.get("color_background")
        GL.glClearColor(bg_col[0], bg_col[1], bg_col[2], 0.0)
        GL.glClearDepth(1.)
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glDepthFunc(GL.GL_LEQUAL)
        GL.glDepthMask(GL.GL_TRUE)
        GL.glHint(GL.GL_PERSPECTIVE_CORRECTION_HINT, GL.GL_NICEST)
        GL.glMatrixMode(GL.GL_MODELVIEW)
        #GL.glMaterial(GL.GL_FRONT_AND_BACK, GL.GL_AMBIENT, (0.1, 0.1, 0.1, 1.0))
        GL.glMaterial(GL.GL_FRONT_AND_BACK, GL.GL_SPECULAR, (0.1, 0.1, 0.1, 1.0))
        #GL.glMaterial(GL.GL_FRONT_AND_BACK, GL.GL_SHININESS, (0.5))
        if self.settings.get("view_polygon"):
            GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_FILL)
        else:
            GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_LINE)
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        GL.glViewport(0, 0, self.area.allocation.width, self.area.allocation.height)
        # lightning
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_AMBIENT, (0.3, 0.3, 0.3, 3.))		# Setup The Ambient Light
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_DIFFUSE, (1., 1., 1., .0))		# Setup The Diffuse Light
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_SPECULAR, (.3, .3, .3, 1.0))		# Setup The SpecularLight
        GL.glEnable(GL.GL_LIGHT0)
        # Enable Light One
        if self.settings.get("view_light"):
            GL.glEnable(GL.GL_LIGHTING)
        else:
            GL.glDisable(GL.GL_LIGHTING)
        GL.glEnable(GL.GL_NORMALIZE)
        GL.glColorMaterial(GL.GL_FRONT_AND_BACK,GL.GL_AMBIENT_AND_DIFFUSE)
        #GL.glColorMaterial(GL.GL_FRONT_AND_BACK,GL.GL_SPECULAR)
        #GL.glColorMaterial(GL.GL_FRONT_AND_BACK,GL.GL_EMISSION)
        GL.glEnable(GL.GL_COLOR_MATERIAL)

    def destroy(self, widget=None, data=None):
        if self.notify_destroy_func:
            self.notify_destroy_func()
        # don't close the window
        return True

    def gtkgl_functionwrapper(function):
        def gtkgl_functionwrapper_function(self, *args, **kwords):
            gldrawable=self.area.get_gl_drawable()
            if not gldrawable:
                return
            glcontext=self.area.get_gl_context()
            if not gldrawable.gl_begin(glcontext):
                return
            if not self.initialized:
                self.glsetup()
                self.initialized = True
            result = function(self, *args, **kwords)
            gldrawable.gl_end()
            return result
        return gtkgl_functionwrapper_function

    @check_busy
    @gtkgl_functionwrapper
    def mouse_handler(self, widget, event):
        last_timestamp = self.mouse["timestamp"]
        x, y, state = event.x, event.y, event.state
        if self.mouse["button"] is None:
            if (state == BUTTON_ZOOM) or (state == BUTTON_ROTATE) or (state == BUTTON_MOVE):
                self.mouse["button"] = state
                self.mouse["start_pos"] = [x, y]
                self.area.set_events(gtk.gdk.MOUSE | gtk.gdk.BUTTON_PRESS_MASK)
        else:
            # not more than 25 frames per second (enough for decent visualization)
            if time.time() - last_timestamp < 0.04:
                return
            # a button was pressed before
            if state == self.mouse["button"] == BUTTON_ZOOM:
                # the start button is still active: update the view
                start_x, start_y = self.mouse["start_pos"]
                self.mouse["start_pos"] = [x, y]
                # move the mouse from lower left to top right corner for scale up
                scale = 1 - 0.01 * ((x - start_x) + (start_y - y))
                # do some sanity checks, scale no more than
                # 1:100 on any given click+drag
                if scale < 0.01:
                    scale = 0.01
                elif scale > 100:
                    scale = 100
                self.camera.scale_distance(scale)
                self._paint_ignore_busy()
            elif (state == self.mouse["button"] == BUTTON_MOVE) or (state == self.mouse["button"] == BUTTON_ROTATE):
                start_x, start_y = self.mouse["start_pos"]
                self.mouse["start_pos"] = [x, y]
                if (state == BUTTON_MOVE):
                    # determine the biggest dimension (x/y/z) for moving the screen's center in relation to this value
                    obj_dim = []
                    obj_dim.append(self.settings.get("maxx") - self.settings.get("minx"))
                    obj_dim.append(self.settings.get("maxy") - self.settings.get("miny"))
                    obj_dim.append(self.settings.get("maxz") - self.settings.get("minz"))
                    max_dim = max(max(obj_dim[0], obj_dim[1]), obj_dim[2])
                    self.camera.move_camera_by_screen(x - start_x, y - start_y, max_dim)
                else:
                    # BUTTON_ROTATE
                    # update the camera position according to the mouse movement
                    self.camera.rotate_camera_by_screen(start_x, start_y, x, y)
                self._paint_ignore_busy()
            else:
                # button was released
                self.mouse["button"] = None
                self._paint_ignore_busy()
        self.mouse["timestamp"] = time.time()

    @check_busy
    @gtkgl_functionwrapper
    @gtkgl_refresh
    def rotate_view(self, widget=None, view=None):
        self.camera.set_view(view)

    def reset_view(self):
        self.rotate_view(None, None)

    @check_busy
    @gtkgl_functionwrapper
    @gtkgl_refresh
    def _resize_window(self, widget, data=None):
        GL.glViewport(0, 0, self.area.allocation.width, self.area.allocation.height)

    @check_busy
    @gtkgl_functionwrapper
    @gtkgl_refresh
    def paint(self, widget=None, data=None):
        # the decorators take core for redraw
        pass

    @gtkgl_functionwrapper
    @gtkgl_refresh
    def _paint_ignore_busy(self, widget=None):
        pass

    def _paint_raw(self, widget=None):
        # draw the model
        draw_complete_model_view(self.settings)
        # update the dimension display
        s = self.settings
        dimension_bar = self.gui.get_object("view3ddimension")
        if s.get("show_dimensions"):
            for name, size in (
                    ("model_dim_x", s.get("maxx") - s.get("minx")),
                    ("model_dim_y", s.get("maxy") - s.get("miny")),
                    ("model_dim_z", s.get("maxz") - s.get("minz"))):
                self.gui.get_object(name).set_text("%.3f %s" % (size, s.get("unit")))
            dimension_bar.show()
        else:
            dimension_bar.hide()


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
def draw_string(x, y, z, p, s, scale=.01):
    GL.glPushMatrix()
    GL.glTranslatef(x, y, z)
    if p == 'xy':
        GL.glRotatef(90, 1, 0, 0)
        pass
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

@keep_gl_mode
@keep_matrix
def draw_axes(settings):
    GL.glMatrixMode(GL.GL_MODELVIEW)
    GL.glLoadIdentity()
    #GL.glTranslatef(0, 0, -2)
    size_x = abs(settings.get("maxx"))
    size_y = abs(settings.get("maxy"))
    size_z = abs(settings.get("maxz"))
    size = 1.5 * max(max(size_x, size_y), size_z)
    # the divider is just based on playing with numbers
    scale = size/1500.0
    string_distance = 1.1 * size
    GL.glBegin(GL.GL_LINES)
    GL.glColor3f(1, 0, 0)
    GL.glVertex3f(0, 0, 0)
    GL.glVertex3f(size, 0, 0)
    GL.glEnd()
    draw_string(string_distance, 0, 0, 'xy', "X", scale=scale)
    GL.glBegin(GL.GL_LINES)
    GL.glColor3f(0, 1, 0)
    GL.glVertex3f(0, 0, 0)
    GL.glVertex3f(0, size, 0)
    GL.glEnd()
    draw_string(0, string_distance, 0, 'yz', "Y", scale=scale)
    GL.glBegin(GL.GL_LINES)
    GL.glColor3f(0, 0, 1)
    GL.glVertex3f(0, 0, 0)
    GL.glVertex3f(0, 0, size)
    GL.glEnd()
    draw_string(0, 0, string_distance, 'xz', "Z", scale=scale)

@keep_matrix
def draw_bounding_box(minx, miny, minz, maxx, maxy, maxz, color):
    p1 = [minx, miny, minz]
    p2 = [minx, maxy, minz]
    p3 = [maxx, maxy, minz]
    p4 = [maxx, miny, minz]
    p5 = [minx, miny, maxz]
    p6 = [minx, maxy, maxz]
    p7 = [maxx, maxy, maxz]
    p8 = [maxx, miny, maxz]
    # lower rectangle
    GL.glBegin(GL.GL_LINES)
    GL.glColor3f(*color)
    # all combinations of neighbouring corners
    for corner_pair in [(p1, p2), (p1, p5), (p1, p4), (p2, p3),
                (p2, p6), (p3, p4), (p3, p7), (p4, p8), (p5, p6),
                (p6, p7), (p7, p8), (p8, p5)]:
        GL.glVertex3f(*(corner_pair[0]))
        GL.glVertex3f(*(corner_pair[1]))
    GL.glEnd()

@keep_gl_mode
@keep_matrix
def draw_complete_model_view(settings):
    GL.glMatrixMode(GL.GL_MODELVIEW)
    GL.glLoadIdentity()
    # axes
    if settings.get("show_axes"):
        draw_axes(settings)
    # stock model
    if settings.get("show_bounding_box"):
        draw_bounding_box(float(settings.get("minx")), float(settings.get("miny")),
                float(settings.get("minz")), float(settings.get("maxx")),
                float(settings.get("maxy")), float(settings.get("maxz")),
                settings.get("color_bounding_box"))
    # draw the material (for simulation mode)
    if settings.get("show_simulation"):
        obj = settings.get("simulation_object")
        if not obj is None:
            GL.glColor3f(*settings.get("color_material"))
            obj.to_OpenGL()
    # draw the model
    if settings.get("show_model"):
        GL.glColor3f(*settings.get("color_model"))
        settings.get("model").to_OpenGL()
    # draw the toolpath
    if settings.get("show_toolpath"):
        for toolpath_obj in settings.get("toolpath"):
            if toolpath_obj.visible:
                draw_toolpath(toolpath_obj.get_path(),
                        settings.get("color_toolpath_cut"),
                        settings.get("color_toolpath_return"))
    # draw the drill
    if settings.get("show_drill_progress"):
        cutter = settings.get("cutter")
        if not cutter is None:
            GL.glColor3f(*settings.get("color_cutter"))
            cutter.to_OpenGL()

@keep_gl_mode
@keep_matrix
def draw_toolpath(toolpath, color_forward, color_backward):
    GL.glMatrixMode(GL.GL_MODELVIEW)
    GL.glLoadIdentity()
    if toolpath:
        last = None
        for path in toolpath:
            if last:
                GL.glColor3f(*color_backward)
                GL.glBegin(GL.GL_LINES)
                GL.glVertex3f(last.x, last.y, last.z)
                last = path.points[0]
                GL.glVertex3f(last.x, last.y, last.z)
                GL.glEnd()
            GL.glColor3f(*color_forward)
            GL.glBegin(GL.GL_LINE_STRIP)
            for point in path.points:
                GL.glVertex3f(point.x, point.y, point.z)
            GL.glEnd()
            last = path.points[-1]

