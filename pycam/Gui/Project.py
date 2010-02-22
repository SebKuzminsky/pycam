#!/usr/bin/env python

import OpenGL.GL as GL
import OpenGL.GLU as GLU
import OpenGL.GLUT as GLUT
import pycam.Importers.STLImporter
import pycam.Exporters.STLExporter
import pycam.Exporters.SimpleGCodeExporter
import pycam.Gui.Settings
import pycam.Gui.common as GuiCommon
import pycam.Cutters
import pycam.PathGenerators
import pycam.PathProcessors
import pycam.Gui.ode_objects as ode_objects
from pycam.Geometry.utils import INFINITE
import threading
import pygtk
import gtk
import os
import sys
import time
import math

GTKBUILD_FILE = os.path.join(os.path.dirname(__file__), "gtk-interface", "pycam-project.ui")

BUTTON_ROTATE = gtk.gdk.BUTTON1_MASK
BUTTON_ZOOM = gtk.gdk.BUTTON2_MASK
BUTTON_MOVE = gtk.gdk.BUTTON3_MASK

VIEWS = {
    "reset": {"distance": (0.0, 5.0, 5.0), "center": (0.0, 0.0, 0.0), "up": (0.0, 0.0, 1.0), "znear": 0.1, "zfar": 1000.0, "fovy": 30.0},
    "top": {"distance": (0.0, 0.0, 10.0), "center": (0.0, 0.0, 0.0), "up": (1.0, 0.0, 0.0), "znear": 0.1, "zfar": 1000.0, "fovy": 30.0},
    "bottom": {"distance": (0.0, 0.0, -10.0), "center": (0.0, 0.0, 0.0), "up": (1.0, 0.0, 0.0), "znear": 0.1, "zfar": 1000.0, "fovy": 30.0},
    "left": {"distance": (-10.0, 0.0, 0.0), "center": (0.0, 0.0, 0.0), "up": (0.0, 0.0, 1.0), "znear": 0.1, "zfar": 1000.0, "fovy": 30.0},
    "right": {"distance": (10.0, 0.0, 0.0), "center": (0.0, 0.0, 0.0), "up": (0.0, 0.0, 1.0), "znear": 0.1, "zfar": 1000.0, "fovy": 30.0},
    "front": {"distance": (0.0, -10.0, 0.0), "center": (0.0, 0.0, 0.0), "up": (0.0, 0.0, 1.0), "znear": 0.1, "zfar": 1000.0, "fovy": 30.0},
    "back": {"distance": (0.0, 10.0, 0.0), "center": (0.0, 0.0, 0.0), "up": (0.0, 0.0, 1.0), "znear": 0.1, "zfar": 1000.0, "fovy": 30.0},
}

def gtkgl_functionwrapper(function):
    def decorated(self, *args, **kwords):
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
    return decorated # TODO: make this a well behaved decorator (keeping name, docstring etc)


class GLView:
    def __init__(self, gui, settings):
        # assume, that initialization will fail
        self.enabled = False
        try:
            import gtk.gtkgl
        except ImportError:
            return
        self.initialized = False
        self.busy = False
        self.mouse = {"start_pos": None, "button": None, "timestamp": 0}
        self.view = VIEWS["reset"].copy()
        self.enabled = True
        self.settings = settings
        self.gui = gui
        self.window = self.gui.get_object("view3dwindow")
        self.window.set_size_request(400,400)
        self.window.connect("destroy", self.destroy)
        self.container = self.gui.get_object("view3dbox")
        self.gui.get_object("Reset View").connect("clicked", self.rotate_view, VIEWS["reset"])
        self.gui.get_object("Left View").connect("clicked", self.rotate_view, VIEWS["left"])
        self.gui.get_object("Right View").connect("clicked", self.rotate_view, VIEWS["right"])
        self.gui.get_object("Front View").connect("clicked", self.rotate_view, VIEWS["front"])
        self.gui.get_object("Back View").connect("clicked", self.rotate_view, VIEWS["back"])
        self.gui.get_object("Top View").connect("clicked", self.rotate_view, VIEWS["top"])
        self.gui.get_object("Bottom View").connect("clicked", self.rotate_view, VIEWS["bottom"])
        # OpenGL stuff
        glconfig = gtk.gdkgl.Config(mode=gtk.gdkgl.MODE_RGB|gtk.gdkgl.MODE_DEPTH|gtk.gdkgl.MODE_DOUBLE)
        self.area = gtk.gtkgl.DrawingArea(glconfig)
        self.area.set_size_request(400, 400)
        # first run; might also be important when doing other fancy gtk/gdk stuff
        self.area.connect_after('realize', self.paint)
        # called when a part of the screen is uncovered
        self.area.connect('expose_event', self.paint) 
        # resize window
        self.area.connect('configure_event', self._resize_window)
        # catch mouse events
        self.area.set_events(gtk.gdk.MOUSE | gtk.gdk.BUTTON_PRESS_MASK)
        self.area.connect("button-press-event", self.mouse_handler)
        self.area.connect('motion-notify-event', self.mouse_handler)
        self.area.show()
        self.container.add(self.area)
        self.container.show()
        self.window.show()

    def check_busy(func):
        def busy_wrapper(self, *args, **kwargs):
            if self.busy:
                return
            self.busy = True
            func(self, *args, **kwargs)
            self.busy = False
        return busy_wrapper

    def gtkgl_refresh(func):
        def refresh_wrapper(self, *args, **kwargs):
            prev_mode = GL.glGetDoublev(GL.GL_MATRIX_MODE)
            GL.glMatrixMode(GL.GL_MODELVIEW)
            GL.glClear(GL.GL_COLOR_BUFFER_BIT|GL.GL_DEPTH_BUFFER_BIT)
            result = func(self, *args, **kwargs)
            self.restore_view_setting()
            self._paint_raw()
            GL.glMatrixMode(prev_mode)
            GL.glFlush()
            self.area.get_gl_drawable().swap_buffers()
            return result
        return refresh_wrapper

    def glsetup(self):
        if self.initialized:
            return
        GLUT.glutInit()
        GL.glShadeModel(GL.GL_FLAT)
        GL.glClearColor(0., 0., 0., 0.)
        GL.glClearDepth(1.)
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glDepthFunc(GL.GL_LEQUAL)
        GL.glHint(GL.GL_PERSPECTIVE_CORRECTION_HINT, GL.GL_NICEST)
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glMaterial(GL.GL_FRONT_AND_BACK, GL.GL_AMBIENT, (0.1, 0.1, 0.1, 1.0))
        GL.glMaterial(GL.GL_FRONT_AND_BACK, GL.GL_SPECULAR, (0.1, 0.1, 0.1, 1.0))
        GL.glMaterial(GL.GL_FRONT_AND_BACK, GL.GL_SHININESS, (0.5))
        GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_FILL)
        GL.glMatrixMode(GL.GL_PROJECTION)
        self.store_view_setting()

    def destroy(self, widget=None):
        self.area.destroy()
        self.window.destroy()

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
            if state == BUTTON_ZOOM:
                print "Zoom button pressed"
            elif state == BUTTON_ROTATE:
                print "Rotate button pressed"
            elif state == BUTTON_MOVE:
                print "Move button pressed"
            else:
                return
        else:
            if time.time() - last_timestamp < 0.04:
                return
            # a button was pressed before
            if state == self.mouse["button"] == BUTTON_ZOOM:
                # the start button is still active: update the view
                scale = 1 - 0.01 * (x - self.mouse["start_pos"][0])
                self.mouse["start_pos"][0] = x
                # do some sanity checks, scale no more than
                # 1:100 on any given click+drag
                if scale < 0.01:
                    scale = 0.01
                elif scale > 100:
                    scale = 100
                dist = self.view["distance"]
                self.view["distance"] = (dist[0] * scale, dist[1] * scale, dist[2] * scale)
                self._paint_ignore_busy()
            elif state == self.mouse["button"] == BUTTON_MOVE:
                start_x, start_y = self.mouse["start_pos"]
                self.mouse["start_pos"] = [x, y]
                self.restore_view_setting()
                prev_mode = GL.glGetDoublev(GL.GL_MATRIX_MODE)
                GL.glMatrixMode(GL.GL_MODELVIEW)
                GL.glPushMatrix()
                #GL.glLoadIdentity()
                height = self.area.allocation.height
                start_z = GL.glReadPixelsf(start_x, height - start_y, 1, 1, GL.GL_DEPTH_COMPONENT)[0][0]
                z = GL.glReadPixelsf(x, height - y, 1, 1, GL.GL_DEPTH_COMPONENT)[0][0]
                print "%d / %d / %d" % (x, y, z)
                print self.get_current_projection_matrix()
                #print "%f / %f / %f" % (x, y, z)
                print GLU.gluUnProject(x, y, z)
                GL.glPopMatrix()
                GL.glMatrixMode(prev_mode)
            else:
                # button was released
                self.mouse["button"] = None
        self.mouse["timestamp"] = time.time()

    def store_view_setting(self):
        prev_mode = GL.glGetDoublev(GL.GL_MATRIX_MODE)
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glPushMatrix()
        self.projection_matrix = GL.glGetDoublev(GL.GL_PROJECTION_MATRIX)[:]
        GL.glPopMatrix()
        GL.glMatrixMode(prev_mode)

    def restore_view_setting(self):
        prev_mode = GL.glGetDoublev(GL.GL_MATRIX_MODE)
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        v = self.view
        GLU.gluPerspective(v["fovy"], self.area.allocation.width/self.area.allocation.height, v["znear"], v["zfar"])
        GLU.gluLookAt(v["center"][0] + v["distance"][0], v["center"][1] + v["distance"][1], v["center"][2] + v["distance"][2],
                v["center"][0], v["center"][1], v["center"][2], v["up"][0], v["up"][1], v["up"][2])
        GL.glMatrixMode(prev_mode)

    @gtkgl_functionwrapper
    def get_current_projection_matrix(self):
        GL.glPushMatrix()
        prev_mode = GL.glGetDoublev(GL.GL_MATRIX_MODE)
        self.restore_view_setting()
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glPushMatrix()
        result = GL.glGetDoublev(GL.GL_PROJECTION_MATRIX)
        GL.glPopMatrix()
        GL.glMatrixMode(prev_mode)
        GL.glPopMatrix()
        return result

    @check_busy
    @gtkgl_functionwrapper
    @gtkgl_refresh
    def rotate_view(self, widget, data=None):
        self.view = data.copy()

    def reset_view(self):
        self.rotate_view(None, VIEWS["reset"].copy())

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
        GuiCommon.draw_complete_model_view(self.settings)


class ProjectGui:

    def __init__(self, master=None):
        gtk.gdk.threads_init()
        self.settings = pycam.Gui.Settings.Settings()
        self.notify_visual = threading.Condition()
        self.gui_is_active = False
        self.view3d = None
        self._batch_queue = []
        self.gui = gtk.Builder()
        self.gui.add_from_file(GTKBUILD_FILE)
        self.window = self.gui.get_object("ProjectWindow")
        # file loading
        self.file_selector = self.gui.get_object("File chooser")
        self.file_selector.connect("file-set",
                self.load_model_file, self.file_selector.get_filename)
        self.window.connect("destroy", self.destroy)
        self.gui.get_object("SaveModel").connect("clicked", self.save_model)
        self.window.show()
        self.model = None
        self.toolpath = None
        self.physics = None
        # add some dummies - to be implemented later ...
        self.settings.add_item("model", lambda: getattr(self, "model"))
        self.settings.add_item("toolpath", lambda: getattr(self, "toolpath"))
        # TODO: replace hard-coded scale
        self.settings.add_item("scale", lambda: 0.9/getattr(getattr(self, "model"), "maxsize")())
        # create the unit field (the default content can't be defined via glade)
        scale_box = self.gui.get_object("scale_box")
        unit_field = gtk.combo_box_new_text()
        unit_field.append_text("mm")
        unit_field.append_text("inch")
        unit_field.set_active(0)
        unit_field.show()
        scale_box.add(unit_field)
        # move it to the top
        scale_box.reorder_child(unit_field, 0)
        def set_unit(text):
            unit_field.set_active((text == "mm") and 0 or 1)
        self.settings.add_item("unit", unit_field.get_active_text, set_unit)
        # define the limit callback functions
        for limit in ["minx", "miny", "minz", "maxx", "maxy", "maxz"]:
            obj = self.gui.get_object(limit)
            self.settings.add_item(limit, obj.get_value, obj.set_value)
        # connect the "Bounds" action
        self.gui.get_object("Minimize bounds").connect("clicked", self.minimize_bounds)
        self.gui.get_object("Reset bounds").connect("clicked", self.reset_bounds)
        # Transformations
        self.gui.get_object("Rotate").connect("clicked", self.transform_model)
        self.gui.get_object("Flip").connect("clicked", self.transform_model)
        self.gui.get_object("Swap").connect("clicked", self.transform_model)
        self.gui.get_object("Shift Model").connect("clicked", self.shift_model, True)
        self.gui.get_object("Shift To Origin").connect("clicked", self.shift_model, False)
        # scale model
        self.gui.get_object("Scale up").connect("clicked", self.scale_model, True)
        self.gui.get_object("Scale down").connect("clicked", self.scale_model, False)
        self.gui.get_object("Scale factor").set_value(2)
        # preset the numbers
        self.gui.get_object("LayersControl").set_value(1)
        self.gui.get_object("SamplesControl").set_value(50)
        self.gui.get_object("LinesControl").set_value(20)
        self.gui.get_object("ToolRadiusControl").set_value(1.0)
        self.gui.get_object("TorusRadiusControl").set_value(0.25)
        self.gui.get_object("FeedrateControl").set_value(200)
        self.gui.get_object("SpeedControl").set_value(1000)
        # connect buttons with activities
        self.gui.get_object("GenerateToolPathButton").connect("clicked", self.generate_toolpath)
        self.gui.get_object("SaveToolPathButton").connect("clicked", self.save_toolpath)
        self.gui.get_object("Toggle3dView").connect("toggled", self.toggle_3d_view)

    def gui_activity_guard(func):
        def wrapper(self, *args, **kwargs):
            if self.gui_is_active:
                return
            self.gui_is_active = True
            func(self, *args, **kwargs)
            self.gui_is_active = False
            while self._batch_queue:
                batch_func, batch_args, batch_kwargs = self._batch_queue[0]
                del self._batch_queue[0]
                batch_func(*batch_args, **batch_kwargs)
        return wrapper
        
    def update_view(self):
        if self.view3d:
            self.notify_visual.acquire()
            self.notify_visual.notify()
            self.notify_visual.release()
            self.view3d.reset_view()

    def reload_model(self):
        self.physics = GuiCommon.generate_physics(self.settings)
        if self.view3d:
            self.settings.set("model_view_request_reset", True)
            self.update_view()

    @gui_activity_guard
    def toggle_3d_view(self, widget=None, value=None):
        current_state = not (self.view3d is None)
        if value is None:
            new_state = not current_state
        else:
            new_state = value
        if new_state == current_state:
            return
        elif new_state:
            self.settings.set("model_view_request_quit", False)
            # do the gl initialization
            self.view3d = GLView(self.gui, self.settings)
            if self.model and self.view3d.enabled:
                self.reset_bounds(None)
                self.view3d.reset_view()
            #self.thread3d = VisualThread(self.notify_visual, self.settings)
            #self.thread3d.start()
            self.update_view()
        else:
            self.settings.set("model_view_request_quit", True)
            self.view3d.destroy()
            self.view3d = None
        self.gui.get_object("Toggle3dView").set_active(new_state)

    @gui_activity_guard
    def transform_model(self, widget):
        if widget.get_name() == "Rotate":
            controls = (("x-axis", "x"), ("y-axis", "y"), ("z-axis", "z"))
        elif widget.get_name() == "Flip":
            controls = (("xy-plane", "xy"), ("xz-plane", "xz"), ("yz-plane", "yz"))
        elif widget.get_name() == "Swap":
            controls = (("x <-> y", "x_swap_y"), ("x <-> z", "x_swap_z"), ("y <-> z", "y_swap_z"))
        else:
            # broken gui
            print sys.stderr, "Unknown button action: %s" % str(widget.get_name())
            return
        for obj, value in controls:
            if self.gui.get_object(obj).get_active():
                GuiCommon.transform_model(self.model, value)
        self.update_view()

    @gui_activity_guard
    def save_model(self, widget):
        no_dialog = False
        if isinstance(widget, basestring):
            filename = widget
            no_dialog = True
        else:
            # we open a dialog
            filename = self.get_save_filename("Save model to ...", ("STL models", "*.stl"))
        # no filename given -> exit
        if not filename:
            return
        try:
            fi = open(filename, "w")
            pycam.Exporters.STLExporter.STLExporter(self.model).write(fi)
            fi.close()
        except IOError, err_msg:
            if not no_dialog:
                self.show_error_dialog("Failed to save model file")

    @gui_activity_guard
    def shift_model(self, widget, use_form_values=True):
        if use_form_values:
            shift_x = self.gui.get_object("shift_x").get_value()
            shift_y = self.gui.get_object("shift_y").get_value()
            shift_z = self.gui.get_object("shift_z").get_value()
        else:
            shift_x = -self.model.minx
            shift_y = -self.model.miny
            shift_z = -self.model.minz
        GuiCommon.shift_model(self.model, shift_x, shift_y, shift_z)
        self.update_view()

    @gui_activity_guard
    def scale_model(self, widget, scale_up=True):
        value = self.gui.get_object("Scale factor").get_value()
        if (value == 0) or (value == 1):
            return
        if not scale_up:
            value = 1/value
        GuiCommon.scale_model(self.model, value)
        self.update_view()

    @gui_activity_guard
    def minimize_bounds(self, widget, data=None):
        # be careful: this depends on equal names of "settings" keys and "model" variables
        for limit in ["minx", "miny", "minz", "maxx", "maxy", "maxz"]:
            self.settings.set(limit, getattr(self.model, limit))
        self.update_view()

    @gui_activity_guard
    def reset_bounds(self, widget, data=None):
        xwidth = self.model.maxx - self.model.minx
        ywidth = self.model.maxy - self.model.miny
        zwidth = self.model.maxz - self.model.minz
        self.settings.set("minx", self.model.minx - 0.1 * xwidth)
        self.settings.set("miny", self.model.miny - 0.1 * ywidth)
        # don't go below ground
        self.settings.set("minz", self.model.minz)
        self.settings.set("maxx", self.model.maxx + 0.1 * xwidth)
        self.settings.set("maxy", self.model.maxy + 0.1 * ywidth)
        self.settings.set("maxz", self.model.maxz + 0.1 * zwidth)
        self.update_view()

    def destroy(self, widget=None, data=None):
        self.settings.set("model_view_request_quit", True)
        self.update_view()
        gtk.main_quit()
        
    def open(self, filename):
        self.file_selector.set_filename(filename)
        self.load_model_file(filename=filename)
        
    def append_to_queue(self, func, *args, **kwargs):
        self._batch_queue.append((func, args, kwargs))

    @gui_activity_guard
    def load_model_file(self, widget=None, filename=None):
        if not filename:
            return
        # evaluate "filename" after showing the dialog above - then we will get the new value
        if callable(filename):
            filename = filename()
        self.model = pycam.Importers.STLImporter.ImportModel(filename)
        self.append_to_queue(self.toggle_3d_view, True)
        self.append_to_queue(self.reload_model)

    @gui_activity_guard
    def generate_toolpath(self, widget, data=None):
        start_time = time.time()
        radius = float(self.gui.get_object("ToolRadiusControl").get_value())
        cuttername = None
        for name in ("SphericalCutter", "CylindricalCutter", "ToroidalCutter"):
            if self.gui.get_object(name).get_active():
                cuttername = name
        pathgenerator = None
        for name in ("DropCutter", "PushCutter"):
            if self.gui.get_object(name).get_active():
                pathgenerator = name
        pathprocessor = None
        for name in ("PathAccumulator", "SimpleCutter", "ZigZagCutter", "PolygonCutter", "ContourCutter"):
            if self.gui.get_object(name).get_active():
                pathprocessor = name
        direction = None
        for obj, value in [("PathDirectionX", "x"), ("PathDirectionY", "y"), ("PathDirectionXY", "xy")]:
            if self.gui.get_object(obj).get_active():
                direction = value
        if cuttername == "SphericalCutter":
            self.cutter = pycam.Cutters.SphericalCutter(radius)
        elif cuttername == "CylindricalCutter":
            self.cutter = pycam.Cutters.CylindricalCutter(radius)
        elif cuttername == "ToroidalCutter":
            toroid = float(self.gui.get_object("TorusRadiusControl").get_value())
            self.cutter = pycam.Cutters.ToroidalCutter(radius, toroid)

        offset = radius/2

        minx = float(self.settings.get("minx"))-offset
        maxx = float(self.settings.get("maxx"))+offset
        miny = float(self.settings.get("miny"))-offset
        maxy = float(self.settings.get("maxy"))+offset
        minz = float(self.settings.get("minz"))
        maxz = float(self.settings.get("maxz"))
        samples = float(self.gui.get_object("SamplesControl").get_value())
        lines = float(self.gui.get_object("LinesControl").get_value())
        layers = float(self.gui.get_object("LayersControl").get_value())
        if pathgenerator == "DropCutter":
            if pathprocessor == "ZigZagCutter":
                self.option = pycam.PathProcessors.PathAccumulator(zigzag=True)
            else:
                self.option = None
            self.pathgenerator = pycam.PathGenerators.DropCutter(self.cutter, self.model, self.option, physics=self.physics);
            if samples>1:
                dx = (maxx-minx)/(samples-1)
            else:
                dx = INFINITE
            if lines>1:
                dy = (maxy-miny)/(lines-1)
            else:
                dy = INFINITE
            if direction == "x":
                self.toolpath = self.pathgenerator.GenerateToolPath(minx, maxx, miny, maxy, minz, maxz, dx, dy, 0)
            elif direction == "y":
                self.toolpath = self.pathgenerator.GenerateToolPath(minx, maxx, miny, maxy, minz, maxz, dy, dx, 1)

        elif pathgenerator == "PushCutter":
            if pathprocessor == "PathAccumulator":
                self.option = pycam.PathProcessors.PathAccumulator()
            elif pathprocessor == "SimpleCutter":
                self.option = pycam.PathProcessors.SimpleCutter()
            elif pathprocessor == "ZigZagCutter":
                self.option = pycam.PathProcessors.ZigZagCutter()
            elif pathprocessor == "PolygonCutter":
                self.option = pycam.PathProcessors.PolygonCutter()
            elif pathprocessor == "ContourCutter":
                self.option = pycam.PathProcessors.ContourCutter()
            else:
                self.option = None
            self.pathgenerator = pycam.PathGenerators.PushCutter(self.cutter, self.model, self.option);
            if pathprocessor == "ContourCutter" and samples>1:
                dx = (maxx-minx)/(samples-1)
            else:
                dx = INFINITE
            if lines>1:
                dy = (maxy-miny)/(lines-1)
            else:
                dy = INFINITE
            if layers>1:
                dz = (maxz-minz)/(layers-1)
            else:
                dz = INFINITE
            if direction == "x":
                self.toolpath = self.pathgenerator.GenerateToolPath(minx, maxx, miny, maxy, minz, maxz, 0, dy, dz)
            elif direction == "y":
                self.toolpath = self.pathgenerator.GenerateToolPath(minx, maxx, miny, maxy, minz, maxz, dy, 0, dz)
            elif direction == "xy":
                self.toolpath = self.pathgenerator.GenerateToolPath(minx, maxx, miny, maxy, minz, maxz, dy, dy, dz)
        print "Time elapsed: %f" % (time.time() - start_time)
        self.update_view()

    def get_save_filename(self, title, type_filter=None):
        # we open a dialog
        dialog = gtk.FileChooserDialog(title=title,
                parent=self.window, action=gtk.FILE_CHOOSER_ACTION_SAVE,
                buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                    gtk.STOCK_SAVE, gtk.RESPONSE_OK))
        # add filter for stl files
        if type_filter:
            filter = gtk.FileFilter()
            filter.set_name(type_filter[0])
            file_extensions = type_filter[1]
            if not isinstance(file_extensions, list):
                file_extensions = [file_extensions]
            for ext in file_extensions:
                filter.add_pattern(ext)
            dialog.add_filter(filter)
        # add filter for all files
        filter = gtk.FileFilter()
        filter.set_name("All files")
        filter.add_pattern("*")
        dialog.add_filter(filter)
        done = False
        while not done:
            dialog.set_filter(dialog.list_filters()[0])
            response = dialog.run()
            filename = dialog.get_filename()
            dialog.hide()
            if response == gtk.RESPONSE_CANCEL:
                dialog.destroy()
                return None
            if os.path.exists(filename):
                overwrite_window = gtk.MessageDialog(self.window, type=gtk.MESSAGE_WARNING,
                        buttons=gtk.BUTTONS_YES_NO,
                        message_format="This file exists. Do you want to overwrite it?")
                overwrite_window.set_title("Confirm overwriting existing file")
                response = overwrite_window.run()
                overwrite_window.destroy()
                done = (response == gtk.RESPONSE_YES)
            else:
                done = True
        dialog.destroy()
        return filename

    def show_error_dialog(self, message):
        warn_window = gtk.MessageDialog(self.window, type=gtk.MESSAGE_ERROR,
                buttons=gtk.BUTTONS_OK, message_format=str(message))
        warn_window.set_title("Failed to save model file")
        warn_window.run()
        warn_window.destroy()

    @gui_activity_guard
    def save_toolpath(self, widget, data=None):
        if not self.toolpath:
            return
        offset = float(self.gui.get_object("ToolRadiusControl").get_value())/2
        minx = float(self.settings.get("minx"))-offset
        maxx = float(self.settings.get("maxx"))+offset
        miny = float(self.settings.get("miny"))-offset
        maxy = float(self.settings.get("maxy"))+offset
        minz = float(self.settings.get("minz"))-offset
        maxz = float(self.settings.get("maxz"))+offset
        no_dialog = False
        if isinstance(widget, basestring):
            filename = widget
            no_dialog = True
        else:
            # we open a dialog
            filename = self.get_save_filename("Save toolpath to ...", ("GCode files", ["*.gcode", "*.nc", "*.gc", "*.ngc"]))
        # no filename given -> exit
        if not filename:
            return
        try:
            fi = open(filename, "w")
            exporter = pycam.Exporters.SimpleGCodeExporter.ExportPathList(
                    filename, self.toolpath, self.settings.get("unit"),
                    minx, miny, maxz,
                    self.gui.get_object("FeedrateControl").get_value(),
                    self.gui.get_object("SpeedControl").get_value())
            fi.close()
        except IOError, err_msg:
            if not no_dialog:
                self.show_error_dialog("Failed to save toolpath file")

    def mainloop(self):
        gtk.main()

if __name__ == "__main__":
    gui = ProjectGui()
    if len(sys.argv) > 1:
        gui.open(sys.argv[1])
    gui.mainloop()

