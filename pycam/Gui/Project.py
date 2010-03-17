#!/usr/bin/env python

import pycam.Importers.STLImporter
import pycam.Exporters.STLExporter
import pycam.Exporters.SimpleGCodeExporter
import pycam.Gui.Settings
import pycam.Gui.common as GuiCommon
import pycam.Cutters
import pycam.PathGenerators
import pycam.PathProcessors
import pycam.Geometry.utils as utils
import pycam.Gui.OpenGLTools as ogl_tools
import OpenGL.GL as GL
import OpenGL.GLU as GLU
import OpenGL.GLUT as GLUT
# gtk.gtkgl is imported in the constructor of "GLView" below
#import gtk.gtkgl
import gtk
import pango
import time
import os
import sys

DATA_DIR_ENVIRON_KEY = "PYCAM_DATA_DIR"
DATA_BASE_DIRS = [os.path.join(os.path.dirname(__file__), "gtk-interface"), os.path.join(sys.prefix, "share", "python-pycam", "ui")]
if DATA_DIR_ENVIRON_KEY in os.environ:
    DATA_BASE_DIRS.insert(0, os.environ[DATA_DIR_ENVIRON_KEY])

GTKBUILD_FILE = "pycam-project.ui"
GTKMENU_FILE = "menubar.xml"

FILTER_GCODE = ("GCode files", ("*.ngc", "*.nc", "*.gc", "*.gcode"))
FILTER_MODEL = ("STL models", "*.stl")
FILTER_CONFIG = ("Config files", "*.conf")

BUTTON_ROTATE = gtk.gdk.BUTTON1_MASK
BUTTON_MOVE = gtk.gdk.BUTTON2_MASK
BUTTON_ZOOM = gtk.gdk.BUTTON3_MASK

COLORS = {
    "color_background": (0.0, 0.0, 0.0),
    "color_model": (0.5, 0.5, 1.0),
    "color_bounding_box": (0.3, 0.3, 0.3),
    "color_cutter": (1.0, 0.2, 0.2),
    "color_toolpath_cut": (1.0, 0.5, 0.5),
    "color_toolpath_return": (0.5, 1.0, 0.5),
}

# floating point color values are only available since gtk 2.16
GTK_COLOR_MAX = 65535.0

def get_data_file_location(filename):
    for base_dir in DATA_BASE_DIRS:
        test_path = os.path.join(base_dir, filename)
        if os.path.exists(test_path):
            return test_path
    else:
        print >>sys.stderr, "Failed to locate a resource file (%s) in %s!" % (filename, DATA_BASE_DIRS)
        print >>sys.stderr, "You can extend the search path by setting the environment variable '%s'." % str(DATA_DIR_ENVIRON_KEY)
        return None


def show_error_dialog(window, message):
    warn_window = gtk.MessageDialog(window, type=gtk.MESSAGE_ERROR,
            buttons=gtk.BUTTONS_OK, message_format=str(message))
    warn_window.set_title("Error")
    warn_window.run()
    warn_window.destroy()


class GLView:
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
        self.gui.get_object("Reset View").connect("clicked", self.rotate_view, ogl_tools.VIEWS["reset"])
        self.gui.get_object("Left View").connect("clicked", self.rotate_view, ogl_tools.VIEWS["left"])
        self.gui.get_object("Right View").connect("clicked", self.rotate_view, ogl_tools.VIEWS["right"])
        self.gui.get_object("Front View").connect("clicked", self.rotate_view, ogl_tools.VIEWS["front"])
        self.gui.get_object("Back View").connect("clicked", self.rotate_view, ogl_tools.VIEWS["back"])
        self.gui.get_object("Top View").connect("clicked", self.rotate_view, ogl_tools.VIEWS["top"])
        self.gui.get_object("Bottom View").connect("clicked", self.rotate_view, ogl_tools.VIEWS["bottom"])
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
        self.camera = ogl_tools.Camera(self.settings, lambda: (self.area.allocation.width, self.area.allocation.height))
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
        def busy_wrapper(self, *args, **kwargs):
            if not self.enabled or self.busy:
                return
            self.busy = True
            func(self, *args, **kwargs)
            self.busy = False
        return busy_wrapper

    def gtkgl_refresh(func):
        def refresh_wrapper(self, *args, **kwargs):
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
        return refresh_wrapper

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

    def keyboard_handler(self, widget, event):
        print "KEY:", event

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
        GuiCommon.draw_complete_model_view(self.settings)
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


class ProjectGui:

    def __init__(self, master=None, no_dialog=False):
        """ TODO: remove "master" above when the Tk interface is abandoned"""
        self.settings = pycam.Gui.Settings.Settings()
        self.gui_is_active = False
        self.view3d = None
        self.no_dialog = no_dialog
        self._batch_queue = []
        self._progress_running = False
        self._progress_cancel_requested = False
        self.gui = gtk.Builder()
        gtk_build_file = get_data_file_location(GTKBUILD_FILE)
        if gtk_build_file is None:
            sys.exit(1)
        self.gui.add_from_file(gtk_build_file)
        self.window = self.gui.get_object("ProjectWindow")
        # file loading
        self.last_config_file = None
        self.last_model_file = None
        self.last_toolpath_file = None
        # define callbacks and accelerator keys for the menu actions
        for objname, callback, data, accel_key in (
                ("LoadProcessingTemplates", self.load_processing_file, None, "<Control>t"),
                ("SaveProcessingTemplates", self.save_processing_settings_file, lambda: self.last_config_file, None),
                ("LoadModel", self.load_model_file, None, "<Control>l"),
                ("SaveModel", self.save_model, lambda: self.last_model_file, "<Control>s"),
                ("SaveAsModel", self.save_model, None, "<Control><Shift>s"),
                ("ExportGCode", self.save_toolpath, None, "<Control><Shift>e"),
                ("Quit", self.destroy, None, "<Control>q"),
                ("GeneralSettings", self.toggle_settings_window, None, "<Control>p"),
                ("Toggle3DView", self.toggle_3d_view, None, "<Control>v")):
            item = self.gui.get_object(objname)
            if objname == "Toggle3DView":
                action = "toggled"
            else:
                action = "activate"
            item.connect(action, callback, data)
            if accel_key:
                key, mod = gtk.accelerator_parse(accel_key)
                accel_path = "<pycam>/%s" % objname
                item.set_accel_path(accel_path)
                gtk.accel_map_change_entry(accel_path, key, mod, True)
        # other events
        self.window.connect("destroy", self.destroy)
        self.gui.get_object("GenerateToolPathButton").connect("clicked", self.generate_toolpath)
        # the settings window
        self.gui.get_object("CloseSettingsWindow").connect("clicked", self.toggle_settings_window, False)
        self.settings_window = self.gui.get_object("GeneralSettingsWindow")
        self.settings_window.connect("delete-event", self.toggle_settings_window, False)
        self._settings_window_position = None
        self._settings_window_visible = False
        # "about" window
        self.about_window = self.gui.get_object("AboutWindow")
        self.gui.get_object("About").connect("activate", self.toggle_about_window, True)
        # we assume, that the last child of the window is the "close" button
        # TODO: fix this ugly hack!
        self.gui.get_object("AboutWindowButtons").get_children()[-1].connect("clicked", self.toggle_about_window, False)
        self.about_window.connect("delete-event", self.toggle_about_window, False)
        # set defaults
        self.model = None
        self.toolpath = GuiCommon.ToolPathList()
        self.physics = None
        self.cutter = None
        # add some dummies - to be implemented later ...
        self.settings.add_item("model", lambda: self.model)
        self.settings.add_item("toolpath", lambda: self.toolpath)
        self.settings.add_item("cutter", lambda: self.cutter)
        # unit control (mm/inch)
        unit_field = self.gui.get_object("unit_control")
        unit_field.connect("changed", self.update_view)
        unit_field.connect("changed", self.update_unit_labels)
        def set_unit(text):
            unit_field.set_active((text == "mm") and 0 or 1)
        self.settings.add_item("unit", unit_field.get_active_text, set_unit)
        unit_field.set_active(0)
        # define the limit callback functions
        for limit in ["minx", "miny", "minz", "maxx", "maxy", "maxz"]:
            obj = self.gui.get_object(limit)
            self.settings.add_item(limit, obj.get_value, obj.set_value)
            obj.connect("value-changed", self.update_view)
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
        # drill, path and processing settings
        for objname, key in (("MaterialAllowanceControl", "material_allowance"),
                ("MaxStepDownControl", "step_down"),
                ("OverlapPercentControl", "overlap"),
                ("ToolRadiusControl", "tool_radius"),
                ("TorusRadiusControl", "torus_radius"),
                ("FeedrateControl", "feedrate"),
                ("SpeedControl", "speed"),
                ("SafetyHeightControl", "safety_height")):
            obj = self.gui.get_object(objname)
            self.settings.add_item(key, obj.get_value, obj.set_value)
        # visual and general settings
        for name, objname in (("show_model", "ShowModelCheckBox"),
                ("show_axes", "ShowAxesCheckBox"),
                ("show_dimensions", "ShowDimensionsCheckBox"),
                ("show_bounding_box", "ShowBoundingCheckBox"),
                ("show_toolpath", "ShowToolPathCheckBox"),
                ("show_drill_progress", "ShowDrillProgressCheckBox"),
                ("enable_ode", "SettingEnableODE")):
            obj = self.gui.get_object(objname)
            self.settings.add_item(name, obj.get_active, obj.set_active)
            # all of the objects above should trigger redraw
            if name != "enable_ode":
                obj.connect("toggled", self.update_view)
        for name, objname in (
                ("view_light", "OpenGLLight"),
                ("view_shadow", "OpenGLShadow"),
                ("view_polygon", "OpenGLPolygon")):
            obj = self.gui.get_object(objname)
            self.settings.add_item(name, obj.get_active, obj.set_active)
            # send "True" to trigger a re-setup of GL settings
            obj.connect("toggled", self.update_view, True)
        # color selectors
        def get_color_wrapper(obj):
            def gtk_color_to_float():
                gtk_color = obj.get_color()
                return (gtk_color.red / GTK_COLOR_MAX, gtk_color.green / GTK_COLOR_MAX, gtk_color.blue / GTK_COLOR_MAX)
            return gtk_color_to_float
        def set_color_wrapper(obj):
            def set_gtk_color_by_float((red, green, blue)):
                obj.set_color(gtk.gdk.Color(int(red * GTK_COLOR_MAX),
                        int(green * GTK_COLOR_MAX), int(blue * GTK_COLOR_MAX)))
            return set_gtk_color_by_float
        for name, objname in (("color_background", "ColorBackground"),
                ("color_model", "ColorModel"),
                ("color_bounding_box", "ColorBoundingBox"),
                ("color_cutter", "ColorDrill"),
                ("color_toolpath_return", "ColorToolpathReturn")):
            obj = self.gui.get_object(objname)
            self.settings.add_item(name, get_color_wrapper(obj), set_color_wrapper(obj))
            # repaint the 3d view after a color change
            obj.connect("color-set", self.update_view)
        # pre-define the colors
        for name in COLORS.keys():
            self.settings.set(name, COLORS[name])
        # set the availability of ODE
        if GuiCommon.is_ode_available():
            self.settings.set("enable_ode", True)
            self.gui.get_object("SettingEnableODE").set_sensitive(True)
            self.gui.get_object("MaterialAllowanceControl").set_sensitive(True)
        else:
            self.settings.set("enable_ode", False)
            self.gui.get_object("SettingEnableODE").set_sensitive(False)
            # TODO: remove this as soon as non-ODE toolpath generation respects material allowance
            self.gui.get_object("MaterialAllowanceControl").set_sensitive(False)
        # preconfigure some values
        self.settings.set("show_model", True)
        self.settings.set("show_toolpath", True)
        self.settings.set("show_bounding_box", True)
        self.settings.set("show_axes", True)
        self.settings.set("show_dimensions", True)
        self.settings.set("view_light", True)
        self.settings.set("view_shadow", True)
        self.settings.set("view_polygon", True)
        skip_obj = self.gui.get_object("DrillProgressFrameSkipControl")
        self.settings.add_item("drill_progress_max_fps", skip_obj.get_value, skip_obj.set_value)
        self.settings.set("drill_progress_max_fps", 2)
        # cutter shapes
        def get_cutter_shape_name():
            for name in ("SphericalCutter", "CylindricalCutter", "ToroidalCutter"):
                if self.gui.get_object(name).get_active():
                    return name
        def set_cutter_shape_name(value):
            self.gui.get_object(value).set_active(True)
        self.settings.add_item("cutter_shape", get_cutter_shape_name, set_cutter_shape_name)
        # path generator
        def get_path_generator():
            for name in ("DropCutter", "PushCutter"):
                if self.gui.get_object(name).get_active():
                    return name
        def set_path_generator(value):
            self.gui.get_object(value).set_active(True)
        self.settings.add_item("path_generator", get_path_generator, set_path_generator)
        # path postprocessor
        def get_path_postprocessor():
            for name in ("PathAccumulator", "SimpleCutter", "ZigZagCutter", "PolygonCutter", "ContourCutter"):
                if self.gui.get_object(name).get_active():
                    return name
        def set_path_postprocessor(value):
            self.gui.get_object(value).set_active(True)
        self.settings.add_item("path_postprocessor", get_path_postprocessor, set_path_postprocessor)
        # path direction (combined get/set function)
        def set_get_path_direction(input=None):
            for obj, value in (("PathDirectionX", "x"), ("PathDirectionY", "y"), ("PathDirectionXY", "xy")):
                if value == input:
                    self.gui.get_object(obj).set_active(True)
                    return
                if self.gui.get_object(obj).get_active():
                    return value
        self.settings.add_item("path_direction", set_get_path_direction, set_get_path_direction)
        # connect the "consistency check" with all toolpath settings
        for objname in ("PathAccumulator", "SimpleCutter", "ZigZagCutter", "PolygonCutter", "ContourCutter",
                "DropCutter", "PushCutter", "SphericalCutter", "CylindricalCutter", "ToroidalCutter",
                "PathDirectionX", "PathDirectionY", "PathDirectionXY", "SettingEnableODE"):
            self.gui.get_object(objname).connect("toggled", self.disable_invalid_toolpath_settings)
        # load a processing configuration object
        self.processing_settings = pycam.Gui.Settings.ProcessingSettings(self.settings)
        self.processing_config_selection = self.gui.get_object("ProcessingTemplatesList")
        self.processing_config_selection.connect("changed",
                self.switch_processing_config, self.processing_config_selection.get_active)
        self.gui.get_object("ProcessingTemplateDelete").connect("clicked",
                self.delete_processing_config, lambda: self.processing_config_selection.get_child().get_text())
        self.gui.get_object("ProcessingTemplateSave").connect("clicked",
                self.save_processing_config, lambda: self.processing_config_selection.get_child().get_text())
        # progress bar and task pane
        self.progress_bar = self.gui.get_object("ProgressBar")
        self.progress_widget = self.gui.get_object("ProgressWidget")
        self.task_pane = self.gui.get_object("Tasks")
        self.gui.get_object("ProgressCancelButton").connect("clicked", self.cancel_progress)
        # make sure that the toolpath settings are consistent
        self.toolpath_table = self.gui.get_object("ToolPathTable")
        self.toolpath_model = self.gui.get_object("ToolPathListModel")
        self.toolpath_table.get_selection().connect("changed", self.toolpath_table_event, "update_buttons")
        self.gui.get_object("toolpath_visible").connect("toggled", self.toolpath_table_event, "toggle_visibility")
        self.gui.get_object("toolpath_up").connect("clicked", self.toolpath_table_event, "move_up")
        self.gui.get_object("toolpath_delete").connect("clicked", self.toolpath_table_event, "delete")
        self.gui.get_object("toolpath_down").connect("clicked", self.toolpath_table_event, "move_down")
        # store the original content (for adding the number of current toolpaths in "update_toolpath_table")
        self._original_toolpath_tab_label = self.gui.get_object("ToolPathTabLabel").get_text()
        # speed and feedrate controls
        speed_control = self.gui.get_object("SpeedControl")
        self.settings.add_item("speed", speed_control.get_value, speed_control.set_value)
        feedrate_control = self.gui.get_object("FeedrateControl")
        self.settings.add_item("feedrate", feedrate_control.get_value, feedrate_control.set_value)
        # menu bar
        uimanager = gtk.UIManager()
        self._accel_group = uimanager.get_accel_group()
        self.window.add_accel_group(self._accel_group)
        self.about_window.add_accel_group(self._accel_group)
        self.settings_window.add_accel_group(self._accel_group)
        # load menu data
        gtk_menu_file = get_data_file_location(GTKMENU_FILE)
        if gtk_menu_file is None:
            sys.exit(1)
        uimanager.add_ui_from_file(gtk_menu_file)
        # make the actions defined in the GTKBUILD file available in the menu
        actiongroup = gtk.ActionGroup("menubar")
        for action in [action for action in self.gui.get_objects() if isinstance(action, gtk.Action)]:
            actiongroup.add_action(action)
        # the "pos" parameter is optional since 2.12 - we can remove it later
        uimanager.insert_action_group(actiongroup, pos=-1)
        # load the menubar and connect functions to its items
        self.menubar = uimanager.get_widget("/MenuBar")
        window_box = self.gui.get_object("WindowBox")
        window_box.pack_start(self.menubar, False)
        window_box.reorder_child(self.menubar, 0)
        # some more initialization
        self.update_toolpath_table()
        self.disable_invalid_toolpath_settings()
        self.load_processing_settings()
        self.update_save_actions()
        self.update_unit_labels()
        if not self.no_dialog:
            self.window.show()

    def progress_activity_guard(func):
        def wrapper(self, *args, **kwargs):
            if self._progress_running:
                return
            self._progress_running = True
            self._progress_cancel_requested = False
            self.toggle_progress_bar(True)
            func(self, *args, **kwargs)
            self.toggle_progress_bar(False)
            self._progress_running = False
        return wrapper

    def gui_activity_guard(func):
        def wrapper(self, *args, **kwargs):
            if self.gui_is_active:
                return
            self.gui_is_active = True
            result = func(self, *args, **kwargs)
            self.gui_is_active = False
            while self._batch_queue:
                batch_func, batch_args, batch_kwargs = self._batch_queue[0]
                del self._batch_queue[0]
                batch_func(*batch_args, **batch_kwargs)
            return result
        return wrapper

    def update_view(self, widget=None, data=None):
        if self.view3d and self.view3d.is_visible and not self.no_dialog:
            if data:
                self.view3d.glsetup()
            self.view3d.paint()

    def update_physics(self, cutter):
        if self.settings.get("enable_ode"):
            self.physics = GuiCommon.generate_physics(self.settings, cutter, self.physics)
        else:
            self.physics = None

    def update_save_actions(self):
        self.gui.get_object("SaveProcessingTemplates").set_sensitive(not self.last_config_file is None)
        self.gui.get_object("SaveModel").set_sensitive(not self.last_model_file is None)

    def disable_invalid_toolpath_settings(self, widget=None, data=None):
        # possible dependencies of the DropCutter
        if self.settings.get("path_generator") == "DropCutter":
            if self.settings.get("path_direction") == "xy":
                self.settings.set("path_direction", "x")
            if not self.settings.get("path_postprocessor") in ("PathAccumulator", "ZigZagCutter"):
                self.settings.set("path_postprocessor", "PathAccumulator")
            dropcutter_active = True
        else:
            dropcutter_active = False
        for objname in ("PathDirectionXY", "SimpleCutter", "PolygonCutter", "ContourCutter"):
            self.gui.get_object(objname).set_sensitive(not dropcutter_active)
        self.gui.get_object("PathDirectionXY").set_sensitive(not dropcutter_active)
        # disable the dropcutter, if "xy" or one of "SimpleCutter", "PolygonCutter", "ContourCutter" is enabled
        if (self.settings.get("path_postprocessor") in ("SimpleCutter", "PolygonCutter", "ContourCutter")) \
                or (self.settings.get("path_direction") == "xy"):
            self.gui.get_object("DropCutter").set_sensitive(False)
        else:
            self.gui.get_object("DropCutter").set_sensitive(True)
        # disable the toroidal radius if the toroidal cutter is not enabled
        self.gui.get_object("TorusRadiusControl").set_sensitive(self.settings.get("cutter_shape") == "ToroidalCutter")
        # disable "step down" control, if PushCutter is not active
        self.gui.get_object("MaxStepDownControl").set_sensitive(self.settings.get("path_generator") == "PushCutter")
        # "material allowance" requires ODE support
        self.gui.get_object("MaterialAllowanceControl").set_sensitive(self.settings.get("enable_ode"))

    @gui_activity_guard
    def toggle_about_window(self, widget=None, event=None, state=None):
        if state is None:
            # the "delete-event" issues the additional "event" argument
            state = event
        if state:
            self.about_window.show()
        else:
            self.about_window.hide()
        # don't close the window - just hide it
        return True

    @gui_activity_guard
    def toggle_settings_window(self, widget=None, event=None, state=None):
        if state is None:
            # the "delete-event" issues the additional "event" argument
            state = event
        if state is None:
           state = not self._settings_window_visible
        if state:
            if self._settings_window_position:
                self.settings_window.move(*self._settings_window_position)
            self.settings_window.show()
        else:
            self._settings_window_position = self.settings_window.get_position()
            self.settings_window.hide()
        self._settings_window_visible = state
        # don't close the window - just hide it
        return True

    @gui_activity_guard
    def toggle_3d_view(self, widget=None, value=None):
        # no interactive mode
        if self.no_dialog:
            return
        if self.view3d and not self.view3d.enabled:
            # initialization failed - don't do anything
            return
        current_state = not ((self.view3d is None) or (not self.view3d.is_visible))
        if value is None:
            new_state = not current_state
        else:
            new_state = value
        if new_state == current_state:
            return
        elif new_state:
            if self.view3d is None:
                # do the gl initialization
                self.view3d = GLView(self.gui, self.settings,
                        notify_destroy=self.toggle_3d_view,
                        accel_group=self._accel_group)
                if self.model and self.view3d.enabled:
                    self.reset_bounds()
                    self.view3d.reset_view()
                # disable the "toggle" button, if the 3D view does not work
                self.gui.get_object("Toggle3DView").set_sensitive(self.view3d.enabled)
            else:
                # the window is just hidden
                self.view3d.show()
            self.update_view()
        else:
            self.view3d.hide()
        self.gui.get_object("Toggle3DView").set_active(new_state)

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
            print >> sys.stderr, "Unknown button action: %s" % str(widget.get_name())
            return
        for obj, value in controls:
            if self.gui.get_object(obj).get_active():
                GuiCommon.transform_model(self.model, value)
        self.update_view()

    def update_unit_labels(self, widget=None, data=None):
        # we can't just use the "unit" setting, since we need the plural of "inch"
        if self.settings.get("unit") == "mm":
            base_unit = "mm"
        else:
            base_unit = "inches"
        self.gui.get_object("SpeedLimitsUnitValue").set_text("%s/minute" % base_unit)

    def get_filename_with_suffix(self, filename, type_filter):
        # use the first extension provided by the filter as the default
        filter_ext = type_filter[1]
        if isinstance(filter_ext, (list, tuple)):
            filter_ext = filter_ext[0]
        if not filter_ext.startswith("*"):
            # weird filter content
            return filename
        else:
            filter_ext = filter_ext[1:]
        basename = os.path.basename(filename)
        splitted = basename.split(".")
        if len(splitted) > 1:
            # contains at least one dot
            return filename
        else:
            # the filename does not contain a dot
            return filename + filter_ext

    @gui_activity_guard
    def save_model(self, widget=None, filename=None):
        no_dialog = False
        if callable(filename):
            filename = filename()
        if isinstance(filename, basestring):
            no_dialog = True
        else:
            # we open a dialog
            filename = self.get_filename_via_dialog("Save model to ...",
                    mode_load=False, type_filter=FILTER_MODEL)
            if filename:
                self.last_model_file = filename
                self.update_save_actions()
        # no filename given -> exit
        if not filename:
            return
        try:
            fi = open(filename, "w")
            pycam.Exporters.STLExporter.STLExporter(self.model).write(fi)
            fi.close()
        except IOError, err_msg:
            if not no_dialog:
                show_error_dialog(self.window, "Failed to save model file")

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
    def reset_bounds(self, widget=None, data=None):
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
        self.update_view()
        # check if there is a running process
        if self._progress_running:
            self.cancel_progress()
            # wait until if is finished
            while self._progress_running:
                time.sleep(0.5)
        gtk.main_quit()

    def open(self, filename):
        """ This function is used by the commandline handler """
        self.last_model_file = filename
        self.load_model_file(filename=filename)
        self.update_save_actions()

    def append_to_queue(self, func, *args, **kwargs):
        # check if gui is currently active
        if self.gui_is_active:
            # queue the function call
            self._batch_queue.append((func, args, kwargs))
        else:
            # call the function right now
            func(*args, **kwargs)

    @gui_activity_guard
    def load_model_file(self, widget=None, filename=None):
        if callable(filename):
            filename = filename()
        if not filename:
            filename = self.get_filename_via_dialog("Loading model ...",
                    mode_load=True, type_filter=FILTER_MODEL)
            if filename:
                self.last_model_file = filename
                self.update_save_actions()
        if filename:
            self.load_model(pycam.Importers.STLImporter.ImportModel(filename))

    def open_processing_settings_file(self, filename):
        """ This function is used by the commandline handler """
        self.last_toolpath_file = filename
        self.load_processing_file(filename=filename)
        self.update_save_actions()

    @gui_activity_guard
    def load_processing_file(self, widget=None, filename=None):
        if callable(filename):
            filename = filename()
        if not filename:
            filename = self.get_filename_via_dialog("Loading processing settings ...",
                    mode_load=True, type_filter=FILTER_CONFIG)
            if filename:
                self.last_config_file = filename
                self.update_save_actions()
        if filename:
            self.load_processing_settings(filename)

    def load_model(self, model):
        self.model = model
        # place the "safe height" clearly above the model's peak
        self.settings.set("safety_height", (2 * self.model.maxz - self.model.minz))
        # do some initialization
        self.append_to_queue(self.reset_bounds)
        self.append_to_queue(self.toggle_3d_view, value=True)
        self.append_to_queue(self.update_view)

    def load_processing_settings(self, filename=None):
        if not filename is None:
            self.processing_settings.reset("")
            self.processing_settings.load_file(filename)
            # load the default config
            self.processing_settings.enable_config()
        # reset the combobox
        self.processing_config_selection.get_model().clear()
        for config_name in self.processing_settings.get_config_list():
            self.processing_config_selection.append_text(config_name)

    def switch_processing_config(self, widget=None, section=None):
        if callable(section):
            section = section()
        if section is None:
            return
        if isinstance(section, basestring):
            # a template may be choosen as a string via the commandline
            if not section in self.processing_settings.get_config_list():
                section = None
        elif section == -1:
            section = None
        else:
            section = self.processing_settings.get_config_list()[section]
        if not section is None:
            self.processing_settings.enable_config(section)
            self._visually_enable_specific_processing_config(section)

    def delete_processing_config(self, widget=None, section=None):
        if callable(section):
            section = section()
        if section is None:
            return
        if section in self.processing_settings.get_config_list():
            self.processing_settings.delete_config(section)
            self.load_processing_settings()
            self._visually_enable_specific_processing_config("")

    def save_processing_config(self, widget=None, section=None):
        if callable(section):
            section = section()
        if section is None:
            return
        self.processing_settings.store_config(section)
        self.load_processing_settings()
        self._visually_enable_specific_processing_config(section)

    def _visually_enable_specific_processing_config(self, section):
        # select the requested section in the drop-down list
        # don't change the setting if not required - otherwise we will loop
        current_text = self.processing_config_selection.get_child().get_text()
        if section != current_text:
            self.processing_config_selection.get_child().set_text(section)

    def _toolpath_table_get_active_index(self):
        if len(self.toolpath) == 0:
            result = None
        else:
            treeselection = self.toolpath_table.get_selection()
            (model, iteration) = treeselection.get_selected()
            # the first item in the model is the index within the toolpath list
            try:
                result = model[iteration][0]
            except TypeError:
                result = None
        return result

    def _toolpath_table_set_active_index(self, index):
        treeselection = self.toolpath_table.get_selection()
        treeselection.select_path((index,))

    @gui_activity_guard
    def toolpath_table_event(self, widget, data, action=None):
        # "toggle" uses two parameters - all other actions have only one
        if action is None:
            action = data
        future_selection_index = None
        skip_model_update = False
        if action == "toggle_visibility":
            try:
                path = int(data)
            except ValueError:
                path = None
            if (not path is None) and (path < len(self.toolpath)):
                self.toolpath[path].visible = not self.toolpath[path].visible
                # hide/show toolpaths according to the new setting
                self.update_view()
        elif action == "update_buttons":
            skip_model_update = True
        elif action in ("move_up", "move_down", "delete"):
            index = self._toolpath_table_get_active_index()
            if action == "move_up":
                if index > 0:
                    # move a toolpath one position up the list
                    selected = self.toolpath[index]
                    above = self.toolpath[index-1]
                    self.toolpath[index] = above
                    self.toolpath[index-1] = selected
                    future_selection_index = index - 1
            elif action == "move_down":
                if index + 1 < len(self.toolpath):
                    # move a toolpath one position down the list
                    selected = self.toolpath[index]
                    below = self.toolpath[index+1]
                    self.toolpath[index] = below
                    self.toolpath[index+1] = selected
                    future_selection_index = index + 1
            else:
                # delete one toolpath from the list
                self.toolpath.remove(self.toolpath[index])
                # don't set a new index, if the list emptied
                if len(self.toolpath) > 0:
                    if index < len(self.toolpath):
                        future_selection_index = index
                    else:
                        # the last item was removed
                        future_selection_index = len(self.toolpath) - 1
                # hide the deleted toolpath immediately
                self.update_view()
        self.update_toolpath_table(new_index=future_selection_index, skip_model_update=skip_model_update)

    def update_toolpath_table(self, new_index=None, skip_model_update=False):
        # show or hide the "toolpath" tab
        toolpath_tab = self.gui.get_object("ToolPathTab")
        if not self.toolpath:
            toolpath_tab.hide()
        else:
            self.gui.get_object("ToolPathTabLabel").set_text(
                    "%s (%d)" % (self._original_toolpath_tab_label, len(self.toolpath)))
            toolpath_tab.show()
        # enable/disable the export menu item
        self.gui.get_object("ExportGCode").set_sensitive(len(self.toolpath) > 0)
        # reset the model data and the selection
        if new_index is None:
            # keep the old selection - this may return "None" if nothing is selected
            new_index = self._toolpath_table_get_active_index()
        if not skip_model_update:
            # update the TreeModel data
            model = self.toolpath_model
            model.clear()
            # columns: name, visible, drill_size, drill_id, allowance, speed, feedrate
            for index in range(len(self.toolpath)):
                tp = self.toolpath[index]
                items = (index, tp.name, tp.visible, tp.drill_size,
                        tp.drill_id, tp.material_allowance, tp.speed, tp.feedrate)
                model.append(items)
            if not new_index is None:
                self._toolpath_table_set_active_index(new_index)
        # enable/disable the modification buttons
        self.gui.get_object("toolpath_up").set_sensitive((not new_index is None) and (new_index > 0))
        self.gui.get_object("toolpath_delete").set_sensitive(not new_index is None)
        self.gui.get_object("toolpath_down").set_sensitive((not new_index is None) and (new_index + 1 < len(self.toolpath)))

    @gui_activity_guard
    def save_processing_settings_file(self, widget=None, filename=None):
        no_dialog = False
        if callable(filename):
            filename = filename()
        if isinstance(filename, basestring):
            no_dialog = True
        else:
            # we open a dialog
            filename = self.get_filename_via_dialog("Save processing settings to ...",
                    mode_load=False, type_filter=FILTER_CONFIG)
            if filename:
                self.last_config_file = filename
                self.update_save_actions()
        # no filename given -> exit
        if not filename:
            return
        if not self.processing_settings.write_to_file(filename) and not no_dialog:
            show_error_dialog(self.window, "Failed to save processing settings file")

    def toggle_progress_bar(self, status):
        if status:
            self.task_pane.set_sensitive(False)
            self.update_progress_bar("", 0)
            self.progress_widget.show()
        else:
            self.progress_widget.hide()
            self.task_pane.set_sensitive(True)

    def update_progress_bar(self, text=None, percent=None):
        if not percent is None:
            percent = min(max(percent, 0.0), 100.0)
            self.progress_bar.set_fraction(percent/100.0)
        if not text is None:
            self.progress_bar.set_text(text)

    def cancel_progress(self, widget=None):
        self._progress_cancel_requested = True

    @gui_activity_guard
    @progress_activity_guard
    def generate_toolpath(self, widget=None, data=None):
        start_time = time.time()
        self.update_progress_bar("Preparing toolpath generation")
        parent = self
        class UpdateView:
            def __init__(self, func, max_fps=1):
                self.last_update = time.time()
                self.max_fps = max_fps
                self.func = func
            def update(self, text=None, percent=None):
                parent.update_progress_bar(text, percent)
                if (time.time() - self.last_update) > 1.0/self.max_fps:
                    self.last_update = time.time()
                    if self.func:
                        self.func()
                # update the GUI
                while gtk.events_pending():
                    gtk.main_iteration()
                # break the loop if someone clicked the "cancel" button
                return parent._progress_cancel_requested
        if self.settings.get("show_drill_progress"):
            callback = self.update_view
        else:
            callback = None
        draw_callback = UpdateView(callback,
                max_fps=self.settings.get("drill_progress_max_fps")).update
        radius = self.settings.get("tool_radius")
        cuttername = self.settings.get("cutter_shape")
        pathgenerator = self.settings.get("path_generator")
        pathprocessor = self.settings.get("path_postprocessor")
        direction = self.settings.get("path_direction")
        # Due to some weirdness the height of the drill must be bigger than the object's size.
        # Otherwise some collisions are not detected.
        cutter_height = 4 * max((self.settings.get("maxz") - self.settings.get("minz")), (self.model.maxz - self.model.minz))
        if cuttername == "SphericalCutter":
            cutter = pycam.Cutters.SphericalCutter(radius, height=cutter_height)
        elif cuttername == "CylindricalCutter":
            cutter = pycam.Cutters.CylindricalCutter(radius, height=cutter_height)
        elif cuttername == "ToroidalCutter":
            toroid = self.settings.get("torus_radius")
            cutter = pycam.Cutters.ToroidalCutter(radius, toroid, height=cutter_height)

        self.update_progress_bar("Generating collision model")
        self.update_physics(cutter)
        self.cutter = cutter

        # this offset allows to cut a model with a minimal boundary box correctly
        offset = radius/2

        minx = float(self.settings.get("minx"))-offset
        maxx = float(self.settings.get("maxx"))+offset
        miny = float(self.settings.get("miny"))-offset
        maxy = float(self.settings.get("maxy"))+offset
        minz = float(self.settings.get("minz"))
        maxz = float(self.settings.get("maxz"))

        effective_toolradius = self.settings.get("tool_radius") * (1.0 - self.settings.get("overlap")/200.0)
        x_shift = effective_toolradius
        y_shift = effective_toolradius

        self.update_progress_bar("Starting the toolpath generation")

        if pathgenerator == "DropCutter":
            if pathprocessor == "ZigZagCutter":
                self.option = pycam.PathProcessors.PathAccumulator(zigzag=True)
            else:
                self.option = None
            self.pathgenerator = pycam.PathGenerators.DropCutter(cutter,
                    self.model, self.option, physics=self.physics,
                    safety_height=self.settings.get("safety_height"))
            dx = x_shift
            dy = y_shift
            if direction == "x":
                toolpath = self.pathgenerator.GenerateToolPath(minx, maxx, miny, maxy, minz, maxz, dx, dy, 0, draw_callback)
            elif direction == "y":
                toolpath = self.pathgenerator.GenerateToolPath(minx, maxx, miny, maxy, minz, maxz, dy, dx, 1, draw_callback)

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
            self.pathgenerator = pycam.PathGenerators.PushCutter(cutter,
                    self.model, self.option, physics=self.physics)
            if pathprocessor == "ContourCutter":
                dx = x_shift
            else:
                dx = utils.INFINITE
            dy = y_shift
            if self.settings.get("step_down") > 0:
                dz = self.settings.get("step_down")
            else:
                dz = utils.INFINITE
            if direction == "x":
                toolpath = self.pathgenerator.GenerateToolPath(minx, maxx, miny, maxy, minz, maxz, 0, dy, dz, draw_callback)
            elif direction == "y":
                toolpath = self.pathgenerator.GenerateToolPath(minx, maxx, miny, maxy, minz, maxz, dy, 0, dz, draw_callback)
            elif direction == "xy":
                toolpath = self.pathgenerator.GenerateToolPath(minx, maxx, miny, maxy, minz, maxz, dy, dy, dz, draw_callback)
        print "Time elapsed: %f" % (time.time() - start_time)
        # calculate the z offset for the starting position
        # TODO: fix these hard-coded offsets; maybe use the safety height instead?
        if self.settings.get("unit") == 'mm':
            start_offset = 7.0
        else:
            start_offset = 0.25
        # hide the previous toolpath if it is the only visible one (automatic mode)
        if (len([True for path in self.toolpath if path.visible]) == 1) \
                and self.toolpath[-1].visible:
            self.toolpath[-1].visible = False
        # add the new toolpath
        self.toolpath.add_toolpath(toolpath,
                self.processing_config_selection.get_active_text(),
                cutter,
                self.settings.get("speed"),
                self.settings.get("feedrate"),
                self.settings.get("material_allowance"),
                self.settings.get("safety_height"),
                self.settings.get("unit"),
                minx, miny, maxz + start_offset)
        self.update_toolpath_table()
        self.update_view()

    # for compatibility with old pycam GUI (see pycam_start.py)
    # TODO: remove it in v0.2
    generateToolpath = generate_toolpath

    def get_filename_via_dialog(self, title, mode_load=False, type_filter=None):
        # we open a dialog
        if mode_load:
            dialog = gtk.FileChooserDialog(title=title,
                    parent=self.window, action=gtk.FILE_CHOOSER_ACTION_OPEN,
                    buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                        gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        else:
            dialog = gtk.FileChooserDialog(title=title,
                    parent=self.window, action=gtk.FILE_CHOOSER_ACTION_SAVE,
                    buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                        gtk.STOCK_SAVE, gtk.RESPONSE_OK))
        # add filter for files
        if type_filter:
            filter = gtk.FileFilter()
            filter.set_name(type_filter[0])
            file_extensions = type_filter[1]
            if not isinstance(file_extensions, (list, tuple)):
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
            if response != gtk.RESPONSE_OK:
                dialog.destroy()
                return None
            if not mode_load and filename:
                # check if we want to add a default suffix
                filename = self.get_filename_with_suffix(filename, type_filter)
            if not mode_load and os.path.exists(filename):
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

    @gui_activity_guard
    def save_toolpath(self, widget=None, data=None):
        if not self.toolpath:
            return
        if callable(widget):
            widget = widget()
        if isinstance(widget, basestring):
            filename = widget
            no_dialog = True
        else:
            # we open a dialog
            filename = self.get_filename_via_dialog("Save toolpath to ...",
                    mode_load=False, type_filter=FILTER_GCODE)
            if filename:
                self.last_toolpath_file = filename
                self.update_save_actions()
            no_dialog = False
        # no filename given -> exit
        if not filename:
            return
        try:
            destination = open(filename, "w")
            index = 0
            for index in range(len(self.toolpath)):
                tp = self.toolpath[index]
                # check if this is the last loop iteration
                # only the last toolpath of the list should contain the "M2"
                # ("end program") G-code
                if index + 1 == len(self.toolpath):
                    is_last_loop = True
                else:
                    is_last_loop = False
                pycam.Exporters.SimpleGCodeExporter.ExportPathList(destination,
                        tp.toolpath, tp.unit,
                        tp.start_x, tp.start_y, tp.start_z,
                        tp.feedrate, tp.speed, tp.safety_height, tp.drill_id,
                        finish_program=is_last_loop)
            destination.close()
            if self.no_dialog:
                print "GCode file successfully written: %s" % str(filename)
        except IOError, err_msg:
            if not no_dialog:
                show_error_dialog(self.window, "Failed to save toolpath file")

    def mainloop(self):
        gtk.main()

if __name__ == "__main__":
    gui = ProjectGui()
    if len(sys.argv) > 1:
        gui.open(sys.argv[1])
    gui.mainloop()

