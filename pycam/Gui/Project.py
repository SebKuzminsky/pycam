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

VIEW_ROTATIONS = {
    "reset":    [(110, 1.0, 0.0, 0.0), (180, 0.0, 1.0, 0.0), (160, 0.0, 0.0, 1.0)],
    "front":    [(-90, 1.0, 0, 0)],
    "back":     [(-90, 1.0, 0, 0), (180, 0, 0, 1.0)],
    "left":     [(-90, 1.0, 0, 0), (90, 0, 0, 1.0)],
    "right":    [(-90, 1.0, 0, 0), (-90, 0, 0, 1.0)],
    "top":      [],
    "bottom":    [(180, 1.0, 0, 0)],
}


def gtkgl_functionwrapper(function):
    def decorated(self, widget, *args, **kwords):
        gldrawable=widget.get_gl_drawable()
        glcontext=widget.get_gl_context()
        if not gldrawable.gl_begin(glcontext):
            return
        function(self, widget, *args, **kwords)
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
        self.scale = 1
        self.model_paint_func = None
        self.gui = gui
        self.window = self.gui.get_object("view3dwindow")
        self.window.set_size_request(400,400)
        self.window.connect("destroy", lambda widget, data=None: self.window.destroy())
        self.container = self.gui.get_object("view3dbox")
        self.gui.get_object("Reset View").connect("clicked", self.rotate_view, VIEW_ROTATIONS["reset"])
        self.gui.get_object("Left View").connect("clicked", self.rotate_view, VIEW_ROTATIONS["left"])
        self.gui.get_object("Right View").connect("clicked", self.rotate_view, VIEW_ROTATIONS["right"])
        self.gui.get_object("Front View").connect("clicked", self.rotate_view, VIEW_ROTATIONS["front"])
        self.gui.get_object("Back View").connect("clicked", self.rotate_view, VIEW_ROTATIONS["back"])
        self.gui.get_object("Top View").connect("clicked", self.rotate_view, VIEW_ROTATIONS["top"])
        self.gui.get_object("Bottom View").connect("clicked", self.rotate_view, VIEW_ROTATIONS["bottom"])
        # OpenGL stuff
        glconfig = gtk.gdkgl.Config(mode=gtk.gdkgl.MODE_RGB|gtk.gdkgl.MODE_DEPTH|gtk.gdkgl.MODE_DOUBLE)
        self.area = gtk.gtkgl.DrawingArea(glconfig)
        self.area.set_size_request(400,400)
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
        #glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
        #glEnable(GL_TEXTURE_2D)
        #glEnable(GL_BLEND)
        #glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        GLUT.glutInit()
        GL.glShadeModel(GL.GL_FLAT)
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glMaterial(GL.GL_FRONT_AND_BACK, GL.GL_AMBIENT, (0.1, 0.1, 0.1, 1.0))
        GL.glMaterial(GL.GL_FRONT_AND_BACK, GL.GL_SPECULAR, (0.1, 0.1, 0.1, 1.0))
        GL.glMaterial(GL.GL_FRONT_AND_BACK, GL.GL_SHININESS, (0.5))

    def paint(self):
        GL.glTranslatef(0,0,-2)
        if self.settings.get("unit") == "mm":
            size = 100
        else:
            size = 5
        # axes
        GL.glBegin(GL.GL_LINES)
        GL.glColor3f(1,0,0)
        GL.glVertex3f(0,0,0)
        GL.glVertex3f(size,0,0)
        GL.glEnd()
        GuiCommon.draw_string(size,0,0,'xy',"X")
        GL.glBegin(GL.GL_LINES)
        GL.glColor3f(0,1,0)
        GL.glVertex3f(0,0,0)
        GL.glVertex3f(0,size,0)
        GL.glEnd()
        GuiCommon.draw_string(0,size,0,'yz',"Y")
        GL.glBegin(GL.GL_LINES)
        GL.glColor3f(0,0,1)
        GL.glVertex3f(0,0,0)
        GL.glVertex3f(0,0,size)
        GL.glEnd()
        GuiCommon.draw_string(0,0,size,'xz',"Z")
        # stock model
        minx = float(self.settings.get("minx"))
        miny = float(self.settings.get("miny"))
        minz = float(self.settings.get("minz"))
        maxx = float(self.settings.get("maxx"))
        maxy = float(self.settings.get("maxy"))
        maxz = float(self.settings.get("maxz"))
        GL.glBegin(GL.GL_LINES)
        GL.glColor3f(0.3,0.3,0.3)
        GL.glVertex3f(minx, miny, minz)
        GL.glVertex3f(maxx, miny, minz)
        GL.glVertex3f(minx, maxy, minz)
        GL.glVertex3f(maxx, maxy, minz)
        GL.glVertex3f(minx, miny, maxz)
        GL.glVertex3f(maxx, miny, maxz)
        GL.glVertex3f(minx, maxy, maxz)
        GL.glVertex3f(maxx, maxy, maxz)
        GL.glVertex3f(minx, miny, minz)
        GL.glVertex3f(minx, maxy, minz)
        GL.glVertex3f(maxx, miny, minz)
        GL.glVertex3f(maxx, maxy, minz)
        GL.glVertex3f(minx, miny, maxz)
        GL.glVertex3f(minx, maxy, maxz)
        GL.glVertex3f(maxx, miny, maxz)
        GL.glVertex3f(maxx, maxy, maxz)
        GL.glVertex3f(minx, miny, minz)
        GL.glVertex3f(minx, miny, maxz)
        GL.glVertex3f(maxx, miny, minz)
        GL.glVertex3f(maxx, miny, maxz)
        GL.glVertex3f(minx, maxy, minz)
        GL.glVertex3f(minx, maxy, maxz)
        GL.glVertex3f(maxx, maxy, minz)
        GL.glVertex3f(maxx, maxy, maxz)
        GL.glEnd()
        # draw the model
        GL.glColor3f(0.5,.5,1)
        self.model_paint_func()
        # draw the toolpath
        self.draw_toolpath(self.settings.get("toolpath"))

    def _gl_clear(self):
        GL.glClear(GL.GL_COLOR_BUFFER_BIT|GL.GL_DEPTH_BUFFER_BIT)

    def _gl_finish(self):
        self.area.get_gl_drawable().swap_buffers()
        
    @gtkgl_functionwrapper
    def _realize(self, widget):
        self.glsetup()

    @gtkgl_functionwrapper
    def _expose_event(self, widget, event):
        self._gl_clear()
        self.paint()
        self._gl_finish()

    def rotate_view(self, widget=None, rotation=None):
        self._gl_clear()
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()
        GL.glScalef(self.scale,self.scale,self.scale)
        if rotation:
            for one_rot in rotation:
                GL.glRotatef(*one_rot)
        self.paint()
        self._gl_finish()

    def reset_view(self):
        self.rotate_view(rotation=VIEW_ROTATIONS["reset"])

    def set_scale(self, value):
        self.scale = value

    def set_model_paint_func(self, func):
        self.model_paint_func = func

    @gtkgl_functionwrapper
    def _resize_window(self, widget, data=None):
        GL.glViewport(0, 0, widget.allocation.width, widget.allocation.height)

    def draw_toolpath(self, toolpath):
        if toolpath:
            last = None
            for path in toolpath:
                if last:
                    GL.glColor3f(.5,1,.5)
                    GL.glBegin(GL.GL_LINES)
                    GL.glVertex3f(last.x,last.y,last.z)
                    last = path.points[0]
                    GL.glVertex3f(last.x,last.y,last.z)
                    GL.glEnd()
                GL.glColor3f(1,.5,.5)
                GL.glBegin(GL.GL_LINE_STRIP)
                for point in path.points:
                    GL.glVertex3f(point.x,point.y,point.z)
                GL.glEnd()
                last = path.points[-1]


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
        # create the unit field (can't be defined via glade)
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

    def minimize_bounds(self, widget, data=None):
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
            self.view3d.set_scale(2.0/self.model.maxsize())
            self.view3d.set_model_paint_func(self.model.to_OpenGL)
            self.view3d.reset_view()

    def mainloop(self):
        gtk.main()

if __name__ == "__main__":
    gui = ProjectGui()
    if len(sys.argv) > 1:
        gui.open(None, sys.argv[1])
    gui.mainloop()

