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
import pycam.Geometry.utils as utils
import pycam.Gui.OpenGLTools as ogl_tools
import threading
import pygtk
import gtk
import os
import sys
import time

GTKBUILD_FILE = os.path.join(os.path.dirname(__file__), "gtk-interface", "pycam-project.ui")

BUTTON_ROTATE = gtk.gdk.BUTTON1_MASK
BUTTON_MOVE = gtk.gdk.BUTTON2_MASK
BUTTON_ZOOM = gtk.gdk.BUTTON3_MASK


class GLView:
    def __init__(self, gui, settings, notify_destroy=None):
        # assume, that initialization will fail
        self.enabled = False
        try:
            import gtk.gtkgl
        except ImportError:
            return
        self.initialized = False
        self.busy = False
        self.mouse = {"start_pos": None, "button": None, "timestamp": 0}
        self.enabled = True
        self.settings = settings
        self.gui = gui
        self.is_visible = False
        self.window = self.gui.get_object("view3dwindow")
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
        # OpenGL stuff
        glconfig = gtk.gdkgl.Config(mode=gtk.gdkgl.MODE_RGB|gtk.gdkgl.MODE_DEPTH|gtk.gdkgl.MODE_DOUBLE)
        self.area = gtk.gtkgl.DrawingArea(glconfig)
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
        self.camera = ogl_tools.Camera(self.settings, lambda: (self.area.allocation.width, self.area.allocation.height))
        self.container.add(self.area)
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
            prev_mode = GL.glGetIntegerv(GL.GL_MATRIX_MODE)
            GL.glMatrixMode(GL.GL_MODELVIEW)
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
        if self.initialized:
            return
        GLUT.glutInit()
        GL.glShadeModel(GL.GL_FLAT)
        GL.glClearColor(0., 0., 0., 0.)
        GL.glClearDepth(1.)
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glDepthFunc(GL.GL_LEQUAL)
        GL.glDepthMask(GL.GL_TRUE)
        GL.glHint(GL.GL_PERSPECTIVE_CORRECTION_HINT, GL.GL_NICEST)
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glMaterial(GL.GL_FRONT_AND_BACK, GL.GL_AMBIENT, (0.1, 0.1, 0.1, 1.0))
        GL.glMaterial(GL.GL_FRONT_AND_BACK, GL.GL_SPECULAR, (0.1, 0.1, 0.1, 1.0))
        GL.glMaterial(GL.GL_FRONT_AND_BACK, GL.GL_SHININESS, (0.5))
        GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_FILL)
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        GL.glViewport(0, 0, self.area.allocation.width, self.area.allocation.height)

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
        GuiCommon.draw_complete_model_view(self.settings)


class ProjectGui:

    def __init__(self, master=None):
        self.settings = pycam.Gui.Settings.Settings()
        self.gui_is_active = False
        self.view3d = None
        self._batch_queue = []
        self.gui = gtk.Builder()
        self.gui.add_from_file(GTKBUILD_FILE)
        self.window = self.gui.get_object("ProjectWindow")
        # file loading
        self.model_file_selector = self.gui.get_object("ModelFileChooser")
        self.model_file_selector.connect("file-set",
                self.load_model_file, self.model_file_selector.get_filename)
        self.processing_file_selector = self.gui.get_object("ProcessingSettingsLoad")
        self.processing_file_selector.connect("file-set",
                self.load_processing_file, self.processing_file_selector.get_filename)
        self.window.connect("destroy", self.destroy)
        self.gui.get_object("SaveModel").connect("clicked", self.save_model)
        model_file_chooser = self.gui.get_object("ModelFileChooser")
        filter = gtk.FileFilter()
        filter.set_name("All files")
        filter.add_pattern("*")
        model_file_chooser.add_filter(filter)
        filter = gtk.FileFilter()
        filter.set_name("STL files")
        filter.add_pattern("*.stl")
        model_file_chooser.add_filter(filter)
        model_file_chooser.set_filter(filter)
        self.window.show()
        self.model = None
        self.toolpath = None
        self.physics = None
        self.cutter = None
        # add some dummies - to be implemented later ...
        self.settings.add_item("model", lambda: getattr(self, "model"))
        self.settings.add_item("toolpath", lambda: getattr(self, "toolpath"))
        self.settings.add_item("cutter", lambda: getattr(self, "cutter"))
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
                ("SpeedControl", "speed")):
            obj = self.gui.get_object(objname)
            self.settings.add_item(key, obj.get_value, obj.set_value)
        # connect buttons with activities
        self.gui.get_object("GenerateToolPathButton").connect("clicked", self.generate_toolpath)
        self.gui.get_object("SaveToolPathButton").connect("clicked", self.save_toolpath)
        # visual and general settings
        self.gui.get_object("Toggle3dView").connect("toggled", self.toggle_3d_view)
        for name, objname in (("show_model", "ShowModelCheckBox"),
                ("show_axes", "ShowAxesCheckBox"),
                ("show_bounding_box", "ShowBoundingCheckBox"),
                ("show_toolpath", "ShowToolPathCheckBox"),
                ("show_drill_progress", "ShowDrillProgressCheckBox"),
                ("enable_ode", "SettingEnableODE")):
            obj = self.gui.get_object(objname)
            self.settings.add_item(name, obj.get_active, obj.set_active)
            # all of the objects above should trigger redraw
            if name != "enable_ode":
                obj.connect("toggled", self.update_view)
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
                self.switch_processing_config, self.processing_config_selection.get_active_text)
        self.gui.get_object("ProcessingTemplateDelete").connect("clicked",
                self.delete_processing_config, self.processing_config_selection.get_active_text)
        self.gui.get_object("ProcessingTemplateSave").connect("clicked",
                self.save_processing_config, self.processing_config_selection.get_active_text)
        self.load_processing_settings()
        self.gui.get_object("ProcessingSettingsSaveToFile").connect("clicked", self.save_processing_settings_file)
        load_processing_settings_file_control = self.gui.get_object("ProcessingSettingsLoad")
        filter = gtk.FileFilter()
        filter.set_name("All files")
        filter.add_pattern("*")
        load_processing_settings_file_control.add_filter(filter)
        filter = gtk.FileFilter()
        filter.set_name("Config files")
        filter.add_pattern("*.conf")
        load_processing_settings_file_control.add_filter(filter)
        load_processing_settings_file_control.set_filter(filter)
        # make sure that the toolpath settings are consistent
        self.disable_invalid_toolpath_settings()

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
        
    def update_view(self, widget=None, data=None):
        if self.view3d:
            self.view3d.paint()

    def update_physics(self):
        if self.settings.get("enable_ode"):
            self.physics = GuiCommon.generate_physics(self.settings, self.cutter, self.physics)
        else:
            self.physics = None

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
    def toggle_3d_view(self, widget=None, value=None):
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
                self.view3d = GLView(self.gui, self.settings, notify_destroy=self.toggle_3d_view)
                if self.model and self.view3d.enabled:
                    self.reset_bounds()
                    self.view3d.reset_view()
            else:
                # the window is just hidden
                self.view3d.show()
            self.update_view()
        else:
            self.view3d.hide()
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
            print >> sys.stderr, "Unknown button action: %s" % str(widget.get_name())
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
        gtk.main_quit()
        
    def open(self, filename):
        self.model_file_selector.set_filename(filename)
        self.load_model_file(filename=filename)
        
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
        if not filename:
            return
        if callable(filename):
            filename = filename()
        self.load_model(pycam.Importers.STLImporter.ImportModel(filename))

    @gui_activity_guard
    def load_processing_file(self, widget=None, filename=None):
        if not filename:
            return
        if callable(filename):
            filename = filename()
        self.load_processing_settings(filename)

    def load_model(self, model):
        self.model = model
        # do some initialization
        self.append_to_queue(self.reset_bounds)
        self.append_to_queue(self.toggle_3d_view, True)
        self.append_to_queue(self.update_view)

    def load_processing_settings(self, filename=None):
        if not filename is None:
            self.processing_settings.load_file(filename)
        # load the default config
        self.processing_settings.enable_config()
        # reset the combobox
        self.processing_config_selection.set_active(0)
        while self.processing_config_selection.get_active() >= 0:
            self.processing_config_selection.remove_text(0)
            self.processing_config_selection.set_active(0)
        for config_name in self.processing_settings.get_config_list():
            self.processing_config_selection.append_text(config_name)

    def switch_processing_config(self, widget=None, section=None):
        if callable(section):
            section = section()
        if not section:
            return
        if section in self.processing_settings.get_config_list():
            self.processing_settings.enable_config(section)

    def delete_processing_config(self, widget=None, section=None):
        if callable(section):
            section = section()
        if not section:
            return
        if section in self.processing_settings.get_config_list():
            self.processing_settings.delete_config(section)
            self.load_processing_settings()

    def save_processing_config(self, widget=None, section=None):
        if callable(section):
            section = section()
        if not section:
            return
        self.processing_settings.store_config(section)
        self.load_processing_settings()
        # try to select the previously stored entry
        index = 0
        self.processing_config_selection.set_active(0)
        while self.processing_config_selection.get_active() >= 0:
            if self.processing_config_selection.get_active_text() == section:
                # we found the right entry
                break
            index += 1
            self.processing_config_selection.set_active(index)

    @gui_activity_guard
    def save_processing_settings_file(self, widget=None, section=None):
        no_dialog = False
        if isinstance(widget, basestring):
            filename = widget
            no_dialog = True
        else:
            # we open a dialog
            filename = self.get_save_filename("Save processing settings to ...", ("Config files", "*.conf"))
        # no filename given -> exit
        if not filename:
            return
        if not self.processing_settings.write_to_file(filename) and not no_dialog:
            self.show_error_dialog("Failed to save processing settings file")


    @gui_activity_guard
    def generate_toolpath(self, widget, data=None):
        start_time = time.time()
        class UpdateView:
            def __init__(self, func, max_fps=1):
                self.last_update = time.time()
                self.max_fps = max_fps
                self.func = func
            def update(self):
                if (time.time() - self.last_update) > 1.0/self.max_fps:
                    self.last_update = time.time()
                    self.func()
        if self.settings.get("show_drill_progress"):
            draw_callback = UpdateView(self.update_view, self.settings.get("drill_progress_max_fps")).update
        else:
            draw_callback = None
        radius = self.settings.get("tool_radius")
        cuttername = self.settings.get("cutter_shape")
        pathgenerator = self.settings.get("path_generator")
        pathprocessor = self.settings.get("path_postprocessor")
        direction = self.settings.get("path_direction")
        # Due to some weirdness the height of the drill must be bigger than the object's size.
        # Otherwise some collisions are not detected.
        cutter_height = 4 * max((self.settings.get("maxz") - self.settings.get("minz")), (self.model.maxz - self.model.minz))
        if cuttername == "SphericalCutter":
            self.cutter = pycam.Cutters.SphericalCutter(radius, height=cutter_height)
        elif cuttername == "CylindricalCutter":
            self.cutter = pycam.Cutters.CylindricalCutter(radius, height=cutter_height)
        elif cuttername == "ToroidalCutter":
            toroid = self.settings.get("torus_radius")
            self.cutter = pycam.Cutters.ToroidalCutter(radius, toroid, height=cutter_height)

        self.update_physics()

        # TODO: check, why this offset is used
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

        if pathgenerator == "DropCutter":
            if pathprocessor == "ZigZagCutter":
                self.option = pycam.PathProcessors.PathAccumulator(zigzag=True)
            else:
                self.option = None
            self.pathgenerator = pycam.PathGenerators.DropCutter(self.cutter, self.model, self.option, physics=self.physics);
            dx = x_shift
            dy = y_shift
            if direction == "x":
                self.toolpath = self.pathgenerator.GenerateToolPath(minx, maxx, miny, maxy, minz, maxz, dx, dy, 0, draw_callback)
            elif direction == "y":
                self.toolpath = self.pathgenerator.GenerateToolPath(minx, maxx, miny, maxy, minz, maxz, dy, dx, 1, draw_callback)

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
            self.pathgenerator = pycam.PathGenerators.PushCutter(self.cutter, self.model, self.option, physics=self.physics);
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
                self.toolpath = self.pathgenerator.GenerateToolPath(minx, maxx, miny, maxy, minz, maxz, 0, dy, dz, draw_callback)
            elif direction == "y":
                self.toolpath = self.pathgenerator.GenerateToolPath(minx, maxx, miny, maxy, minz, maxz, dy, 0, dz, draw_callback)
            elif direction == "xy":
                self.toolpath = self.pathgenerator.GenerateToolPath(minx, maxx, miny, maxy, minz, maxz, dy, dy, dz, draw_callback)
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
            if response != gtk.RESPONSE_OK:
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

