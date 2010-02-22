#!/usr/bin/env python

import OpenGL.GL as GL
import OpenGL.GLUT as GLUT
import pycam.Importers.STLImporter
import pycam.Gui.Settings
import pycam.Gui.common as GuiCommon
import pygtk
import gtk
import os
import sys

GTKBUILD_FILE = os.path.join(os.path.dirname(__file__), "gtk-interface", "pycam-project.ui")


def gtkgl_functionwrapper(function):
    def decorated(self, *args, **kwords):
        gldrawable=self.area.get_gl_drawable()
        glcontext=self.area.get_gl_context()
        if not gldrawable.gl_begin(glcontext):
            return
        function(self, *args, **kwords)
        gldrawable.gl_end()
    return decorated # TODO: make this a well behaved decorator (keeping name, docstring etc)


class GLView:
    def __init__(self, gui, settings):
        # assume, that initialization will fail
        self.enabled = False
        try:
            import gtk.gtkgl
        except ImportError:
            return
        self.enabled = True
        self.settings = settings
        self.gui = gui
        self.window = self.gui.get_object("view3dwindow")
        self.window.set_size_request(400,400)
        self.window.connect("destroy", lambda widget, data=None: self.window.destroy())
        self.container = self.gui.get_object("view3dbox")
        self.gui.get_object("Reset View").connect("clicked", self.rotate_view, GuiCommon.VIEW_ROTATIONS["reset"])
        self.gui.get_object("Left View").connect("clicked", self.rotate_view, GuiCommon.VIEW_ROTATIONS["left"])
        self.gui.get_object("Right View").connect("clicked", self.rotate_view, GuiCommon.VIEW_ROTATIONS["right"])
        self.gui.get_object("Front View").connect("clicked", self.rotate_view, GuiCommon.VIEW_ROTATIONS["front"])
        self.gui.get_object("Back View").connect("clicked", self.rotate_view, GuiCommon.VIEW_ROTATIONS["back"])
        self.gui.get_object("Top View").connect("clicked", self.rotate_view, GuiCommon.VIEW_ROTATIONS["top"])
        self.gui.get_object("Bottom View").connect("clicked", self.rotate_view, GuiCommon.VIEW_ROTATIONS["bottom"])
        # OpenGL stuff
        glconfig = gtk.gdkgl.Config(mode=gtk.gdkgl.MODE_RGB|gtk.gdkgl.MODE_DEPTH|gtk.gdkgl.MODE_DOUBLE)
        self.area = gtk.gtkgl.DrawingArea(glconfig)
        self.area.set_size_request(400, 400)
        # first run; might also be important when doing other fancy gtk/gdk stuff
        self.area.connect_after('realize', self._realize)
        # called when a part of the screen is uncovered
        self.area.connect('expose_event', self._expose_event) 
        # resize window
        self.area.connect('configure_event', self._resize_window)
        self.area.show()
        self.container.add(self.area)
        self.container.show()
        self.window.show()

    def glsetup(self):
        GLUT.glutInit()
        GL.glShadeModel(GL.GL_FLAT)
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glMaterial(GL.GL_FRONT_AND_BACK, GL.GL_AMBIENT, (0.1, 0.1, 0.1, 1.0))
        GL.glMaterial(GL.GL_FRONT_AND_BACK, GL.GL_SPECULAR, (0.1, 0.1, 0.1, 1.0))
        GL.glMaterial(GL.GL_FRONT_AND_BACK, GL.GL_SHININESS, (0.5))

    def _gl_clear(self):
        GL.glClear(GL.GL_COLOR_BUFFER_BIT|GL.GL_DEPTH_BUFFER_BIT)

    def _gl_finish(self):
        self.area.get_gl_drawable().swap_buffers()

    @gtkgl_functionwrapper
    def rotate_view(self, widget, data=None):
        self._gl_clear()
        GuiCommon.rotate_view(self.settings.get("scale"), data)
        self.paint()
        self._gl_finish()

    def reset_view(self):
        self.rotate_view(self.area, GuiCommon.VIEW_ROTATIONS["reset"])

    @gtkgl_functionwrapper
    def _realize(self, widget):
        self.glsetup()

    def _expose_event(self, widget, event):
        self.paint()

    @gtkgl_functionwrapper
    def _resize_window(self, widget, data=None):
        GL.glViewport(0, 0, widget.allocation.width, widget.allocation.height)

    def paint(self):
        self._gl_clear()
        self._paint()
        self._gl_finish()

    @gtkgl_functionwrapper
    def _paint(self, widget=None):
        GuiCommon.draw_complete_model_view(self.settings)


class ProjectGui:

    def __init__(self, master=None):
        self.gui = gtk.Builder()
        self.gui.add_from_file(GTKBUILD_FILE)
        self.window = self.gui.get_object("ProjectWindow")
        # file loading
        self.file_selector = self.gui.get_object("File chooser")
        self.file_selector.connect("file-set",
                self.load_model_file, self.file_selector.get_filename)
        self.window.connect("destroy", self.destroy)
        self.window.show()
        self.model = None
        self.toolpath = None
        # add some dummies - to be implemented later ...
        self.settings = pycam.Gui.Settings.Settings()
        self.settings.add_item("model", lambda: getattr(self, "model"))
        self.settings.add_item("toolpath", lambda: getattr(self, "toolpath"))
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
        self.view3d.paint()

    def minimize_bounds(self, widget, data=None):
        # be careful: this depends on equal names of "settings" keys and "model" variables
        for limit in ["minx", "miny", "minz", "maxx", "maxy", "maxz"]:
            self.settings.set(limit, getattr(self.model, limit))

    def reset_bounds(self, widget, data=None):
        xwidth = self.model.maxx - self.model.minx
        ywidth = self.model.maxy - self.model.miny
        zwidth = self.model.maxz - self.model.minz
        self.settings.set("minx", self.model.minx - 0.1 * xwidth)
        self.settings.set("miny", self.model.miny - 0.1 * ywidth)
        self.settings.set("minz", self.model.minz - 0.1 * zwidth)
        self.settings.set("maxx", self.model.maxx + 0.1 * xwidth)
        self.settings.set("maxy", self.model.maxy + 0.1 * ywidth)
        self.settings.set("maxz", self.model.maxz + 0.1 * zwidth)

    def destroy(self, widget, data=None):
        gtk.main_quit()
        
    def open(self, filename):
        self.file_selector.set_filename(filename)
        self.load_model_file(filename=filename)
        
    def load_model_file(self, widget=None, filename=None):
        if not filename:
            return
        # evaluate "filename" after showing the dialog above - then we will get the new value
        if callable(filename):
            filename = filename()
        self.model = pycam.Importers.STLImporter.ImportModel(filename)
        # do the gl initialization
        self.view3d = GLView(self.gui, self.settings)
        if self.model and self.view3d.enabled:
            self.reset_bounds(None)
            # why "2.0"?
            self.settings.set("scale", 0.9/self.model.maxsize())
            self.view3d.reset_view()

    def mainloop(self):
        gtk.main()

if __name__ == "__main__":
    gui = ProjectGui()
    if len(sys.argv) > 1:
        gui.open(None, sys.argv[1])
    gui.mainloop()

