#!/usr/bin/env python

from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import pycam.Importers.STLImporter
import pygtk
import gtk
import os
import sys

GTKBUILD_FILE = os.path.join(os.path.dirname(__file__), "gtk-interface", "pycam-project.ui")

#class OpenglWidget(Opengl):
#    def __init__(self, master=None, cnf={}, **kw):
#        Opengl.__init__(self, master, kw)
#        glutInit()
#        glShadeModel(GL_FLAT)
#        glMatrixMode(GL_MODELVIEW)
#        glMaterial(GL_FRONT_AND_BACK, GL_AMBIENT, (0.1, 0.1, 0.1, 1.0))
#        glMaterial(GL_FRONT_AND_BACK, GL_SPECULAR, (0.1, 0.1, 0.1, 1.0))
#        glMaterial(GL_FRONT_AND_BACK, GL_SHININESS, (0.5))
#        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

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
        glutInit()
        glShadeModel(GL_FLAT)
        glMatrixMode(GL_MODELVIEW)
        glMaterial(GL_FRONT_AND_BACK, GL_AMBIENT, (0.1, 0.1, 0.1, 1.0))
        glMaterial(GL_FRONT_AND_BACK, GL_SPECULAR, (0.1, 0.1, 0.1, 1.0))
        glMaterial(GL_FRONT_AND_BACK, GL_SHININESS, (0.5))

    def draw_string(self, x, y, z, p, s, scale=.01):
        glPushMatrix()
        glTranslatef(x,y,z)
        if p == 'xy':
            pass
        elif p == 'yz':
            glRotatef(90, 0, 1, 0)
            glRotatef(90, 0, 0, 1)
        elif p == 'xz':
            glRotatef(90, 0, 1, 0)
            glRotatef(90, 0, 0, 1)
            glRotatef(-90, 0, 1, 0)
        glScalef(scale,scale,scale)
        for c in str(s):
            glutStrokeCharacter(GLUT_STROKE_ROMAN, ord(c))
        glPopMatrix()

    def paint(self):
        glTranslatef(0,0,-2)
        if self.settings["Unit"]() == "mm":
            size = 100
        else:
            size = 5
        bounds = self.settings["bounds"]
        # axes
        glBegin(GL_LINES)
        glColor3f(1,0,0)
        glVertex3f(0,0,0)
        glVertex3f(size,0,0)
        glEnd()
        self.draw_string(size,0,0,'xy',"X")
        glBegin(GL_LINES)
        glColor3f(0,1,0)
        glVertex3f(0,0,0)
        glVertex3f(0,size,0)
        glEnd()
        self.draw_string(0,size,0,'yz',"Y")
        glBegin(GL_LINES)
        glColor3f(0,0,1)
        glVertex3f(0,0,0)
        glVertex3f(0,0,size)
        glEnd()
        self.draw_string(0,0,size,'xz',"Z")
        # stock model
        minx = float(bounds["minx"])
        maxx = float(bounds["maxx"])
        miny = float(bounds["miny"])
        maxy = float(bounds["maxy"])
        minz = float(bounds["minz"])
        maxz = float(bounds["maxz"])
        glBegin(GL_LINES)
        glColor3f(0.3,0.3,0.3)
        glVertex3f(minx, miny, minz)
        glVertex3f(maxx, miny, minz)
        glVertex3f(minx, maxy, minz)
        glVertex3f(maxx, maxy, minz)
        glVertex3f(minx, miny, maxz)
        glVertex3f(maxx, miny, maxz)
        glVertex3f(minx, maxy, maxz)
        glVertex3f(maxx, maxy, maxz)
        glVertex3f(minx, miny, minz)
        glVertex3f(minx, maxy, minz)
        glVertex3f(maxx, miny, minz)
        glVertex3f(maxx, maxy, minz)
        glVertex3f(minx, miny, maxz)
        glVertex3f(minx, maxy, maxz)
        glVertex3f(maxx, miny, maxz)
        glVertex3f(maxx, maxy, maxz)
        glVertex3f(minx, miny, minz)
        glVertex3f(minx, miny, maxz)
        glVertex3f(maxx, miny, minz)
        glVertex3f(maxx, miny, maxz)
        glVertex3f(minx, maxy, minz)
        glVertex3f(minx, maxy, maxz)
        glVertex3f(maxx, maxy, minz)
        glVertex3f(maxx, maxy, maxz)
        glEnd()
        # draw the model
        glColor3f(0.5,.5,1)
        self.model_paint_func()
        # draw the toolpath
        self.settings["toolpath_repaint_func"]()

    def _gl_clear(self):
        glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)

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
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glScalef(self.scale,self.scale,self.scale)
        if rotation:
            for one_rot in rotation:
                glRotatef(*one_rot)
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
        glViewport(0, 0, widget.allocation.width, widget.allocation.height)


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
        self.settings = {
            "bounds": {
                "minx": 0,
                "miny": 0,
                "minz": 0,
                "maxx": 7,
                "maxy": 7,
                "maxz": 2,
            },
            "Unit": lambda: "mm",
            "toolpath_repaint_func": self.draw_toolpath,
        }

    def draw_toolpath(self):
        if self.toolpath:
            last = None
            for path in self.toolpath:
                if last:
                    glColor3f(.5,1,.5)
                    glBegin(GL_LINES)
                    glVertex3f(last.x,last.y,last.z)
                    last = path.points[0]
                    glVertex3f(last.x,last.y,last.z)
                    glEnd()
                glColor3f(1,.5,.5)
                glBegin(GL_LINE_STRIP)
                for point in path.points:
                    glVertex3f(point.x,point.y,point.z)
                glEnd()
                last = path.points[-1]

    def destroy(self, widget, data=None):
        gtk.main_quit()
        
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
            # why "2.0"?
            self.view3d.set_scale(2.0/self.model.maxsize())
            self.view3d.set_model_paint_func(self.model.to_OpenGL)
            self.view3d.reset_view()

    def main(self):
        gtk.main()

if __name__ == "__main__":
    gui = ProjectGui()
    if len(sys.argv) > 1:
        gui.load_model_file(None, sys.argv[1])
    gui.main()

