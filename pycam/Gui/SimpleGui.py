#!/usr/bin/python
import sys
sys.path.insert(0,'.')

from ConfigParser import ConfigParser

import OpenGL.GL as GL
import OpenGL.Tk as Tk
import OpenGL.GLUT as GLUT
import tkFileDialog

from pycam import *
from pycam.Cutters import *
from pycam.PathGenerators import *
from pycam.PathProcessors import *
from pycam.Geometry.utils import *
from pycam.Importers import *
from pycam.Exporters import *

# leave 10% margin around the model
DEFAULT_MARGIN = 0.1

class OpenglWidget(Tk.Opengl):
    def __init__(self, master=None, cnf={}, **kw):
        Tk.Opengl.__init__(self, master, kw)
        GLUT.glutInit()
        GL.glShadeModel(GL.GL_FLAT)
#        GL.glShadeModel(GL.GL_SMOOTH)

        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glMaterial(GL.GL_FRONT_AND_BACK, GL.GL_AMBIENT, (0.1, 0.1, 0.1, 1.0))
        GL.glMaterial(GL.GL_FRONT_AND_BACK, GL.GL_SPECULAR, (0.1, 0.1, 0.1, 1.0))
        GL.glMaterial(GL.GL_FRONT_AND_BACK, GL.GL_SHININESS, (0.5))

#        GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL_LINE)
        GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_FILL)

    def basic_lighting(self):
        Tk.Opengl.basic_lighting(self)
        # "Let There Be Light"
        GL.glPushMatrix()
        GL.glLoadIdentity()
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_AMBIENT, (0.5, 0.5, 0.5, 1.0))
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_DIFFUSE, (1.0, 1.0, 1.0, 1.0))
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_SPECULAR, (1.0, 1.0, 1.0, 1.0))
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_POSITION, (2, 2, +10, 1.0))
        GL.glEnable(GL.GL_LIGHT0)
        GL.glDisable(GL.GL_LIGHTING)
        GL.glPopMatrix()
        self.master.resetView()

class SimpleGui(Tk.Frame):
    def draw_string(self, x, y, z, p, s, scale=.01):
        GL.glPushMatrix()
        GL.glTranslatef(x,y,z)
        if p == 'xy':
            pass
        elif p == 'yz':
            GL.glRotatef(90, 0, 1, 0)
            GL.glRotatef(90, 0, 0, 1)
        elif p == 'xz':
            GL.glRotatef(90, 0, 1, 0)
            GL.glRotatef(90, 0, 0, 1)
            GL.glRotatef(-90, 0, 1, 0)
        GL.glScalef(scale,scale,scale)
        for c in str(s):
            GLUT.glutStrokeCharacter(GLUT.GLUT_STROKE_ROMAN, ord(c))
        GL.glPopMatrix()

    def Redraw(self, event=None):
        # default scale and orientation
        GL.glTranslatef(0,0,-2)

        if self.Unit.get() == "mm":
            size = 100
        else:
            size = 5

        # axes
        GL.glBegin(GL.GL_LINES)
        GL.glColor3f(1,0,0)
        GL.glVertex3f(0,0,0)
        GL.glVertex3f(size,0,0)
        GL.glEnd()
        self.draw_string(size,0,0,'xy',"X")
        GL.glBegin(GL.GL_LINES)
        GL.glColor3f(0,1,0)
        GL.glVertex3f(0,0,0)
        GL.glVertex3f(0,size,0)
        GL.glEnd()
        self.draw_string(0,size,0,'yz',"Y")
        GL.glBegin(GL.GL_LINES)
        GL.glColor3f(0,0,1)
        GL.glVertex3f(0,0,0)
        GL.glVertex3f(0,0,size)
        GL.glEnd()
        self.draw_string(0,0,size,'xz',"Z")

        if True:
            # stock model
            minx = float(self.MinX.get())
            maxx = float(self.MaxX.get())
            miny = float(self.MinY.get())
            maxy = float(self.MaxY.get())
            minz = float(self.MinZ.get())
            maxz = float(self.MaxZ.get())
            GL.glBegin(GL.GL_LINES)
            GL.glColor3f(0.3,0.3,0.3)

            GL.glVertex3f(minx,miny,minz)
            GL.glVertex3f(maxx,miny,minz)

            GL.glVertex3f(minx,maxy,minz)
            GL.glVertex3f(maxx,maxy,minz)

            GL.glVertex3f(minx,miny,maxz)
            GL.glVertex3f(maxx,miny,maxz)

            GL.glVertex3f(minx,maxy,maxz)
            GL.glVertex3f(maxx,maxy,maxz)


            GL.glVertex3f(minx,miny,minz)
            GL.glVertex3f(minx,maxy,minz)

            GL.glVertex3f(maxx,miny,minz)
            GL.glVertex3f(maxx,maxy,minz)

            GL.glVertex3f(minx,miny,maxz)
            GL.glVertex3f(minx,maxy,maxz)

            GL.glVertex3f(maxx,miny,maxz)
            GL.glVertex3f(maxx,maxy,maxz)


            GL.glVertex3f(minx,miny,minz)
            GL.glVertex3f(minx,miny,maxz)

            GL.glVertex3f(maxx,miny,minz)
            GL.glVertex3f(maxx,miny,maxz)

            GL.glVertex3f(minx,maxy,minz)
            GL.glVertex3f(minx,maxy,maxz)

            GL.glVertex3f(maxx,maxy,minz)
            GL.glVertex3f(maxx,maxy,maxz)

            GL.glEnd()

        if self.model:
            GL.glColor3f(0.5,.5,1)
            self.model.to_OpenGL()

        if self.toolpath:
            last = None
            for path in self.toolpath:
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

    def browseOpen(self):
        filename = tkFileDialog.Open(self, filetypes=[("STL files", ".stl"),("CFG files", ".cfg")]).show()
        if filename:
            self.open(filename)

    def open(self, filename):
        # read the model data
        self.model = None
        if filename:
            self.InputFileName.set(filename)
            try:
                self.model = STLImporter.ImportModel(filename)
            except:
                self.model = None
        # guess suitable default dimensions
        if self.model:
            self.MinX.set(str(self.model.minx - (self.model.maxx - self.model.minx)*DEFAULT_MARGIN))
            self.MaxX.set(str(self.model.maxx + (self.model.maxx - self.model.minx)*DEFAULT_MARGIN))
            self.MinY.set(str(self.model.miny - (self.model.maxy - self.model.miny)*DEFAULT_MARGIN))
            self.MaxY.set(str(self.model.maxy + (self.model.maxy - self.model.miny)*DEFAULT_MARGIN))
            minz = self.model.minz - (self.model.maxz - self.model.minz)*DEFAULT_MARGIN
            if self.model.minz > 0 and minz < 0:
                # don't go below zero, if it is not necessary
                self.MinZ.set("0")
            else:
                self.MinZ.set(str(minz))
            self.MaxZ.set(str(self.model.maxz + (self.model.maxz - self.model.minz)*DEFAULT_MARGIN))
        self.toolpath = None
        # read a config file, if it exists
        config = ConfigParser();
        if config.read(filename.replace(".stl",".cfg")):
            if config.has_option("stock","Unit"):
                self.Unit.set(config.get("stock","Unit"))
            if config.has_option("stock","MinX"):
                self.MinX.set(config.get("stock","MinX"))
            if config.has_option("stock","MaxX"):
                self.MaxX.set(config.get("stock","MaxX"))
            if config.has_option("stock","MinY"):
                self.MinY.set(config.get("stock","MinY"))
            if config.has_option("stock","MaxY"):
                self.MaxY.set(config.get("stock","MaxY"))
            if config.has_option("stock","MinZ"):
                self.MinZ.set(config.get("stock","MinZ"))
            if config.has_option("stock","MaxZ"):
                self.MaxZ.set(config.get("stock","MaxZ"))
            if config.has_option("stock","Model"):
                if not os.path.isabs(config.get("stock","Model")):
                    (path,ext) = os.path.split(filename)
                    filename = path + '/' + config.get("stock","Model")
            if config.has_option("config","ToolRadius"):
                self.ToolRadius.set(config.get("config","ToolRadius"))
            if config.has_option("config","TorusRadius"):
                self.TorusRadius.set(config.get("config","TorusRadius"))
            if config.has_option("config","Samples"):
                self.Samples.set(config.get("config","Samples"))
            if config.has_option("config","Lines"):
                self.Lines.set(config.get("config","Lines"))
            if config.has_option("config","Layers"):
                self.Layers.set(config.get("config","Layers"))
            if config.has_option("config","Cutter"):
                self.CutterName.set(config.get("config","Cutter"))
            if config.has_option("config","PathGenerator"):
                self.PathGeneratorName.set(config.get("config","PathGenerator"))
            if config.has_option("config","PathProcessor"):
                self.PathProcessorName.set(config.get("config","PathProcessor"))
            if config.has_option("config","Direction"):
                self.Direction.set(config.get("config","Direction"))
        if self.model:
            self.scale = 2.0/self.model.maxsize()
        self.resetView()

    def generateToolpath(self):
        radius = float(self.ToolRadius.get())
        if self.CutterName.get() == "SphericalCutter":
            self.cutter = SphericalCutter(radius)
        elif self.CutterName.get() == "CylindricalCutter":
            self.cutter = CylindricalCutter(radius)
        elif self.CutterName.get() == "ToroidalCutter":
            toroid = float(self.TorusRadius.get())
            self.cutter = ToroidalCutter(radius, toroid)

        offset = radius/2

        minx = float(self.MinX.get())-offset
        maxx = float(self.MaxX.get())+offset
        miny = float(self.MinY.get())-offset
        maxy = float(self.MaxY.get())+offset
        minz = float(self.MinZ.get())
        maxz = float(self.MaxZ.get())
        samples = float(self.Samples.get())
        lines = float(self.Lines.get())
        layers = float(self.Layers.get())
        if self.PathGeneratorName.get() == "DropCutter":
            if self.PathProcessorName.get() == "ZigZagCutter":
                self.option = PathAccumulator(zigzag=True)
            else:
                self.option = None
            self.pathgenerator = DropCutter(self.cutter, self.model, self.option);
            if samples>1:
                dx = (maxx-minx)/(samples-1)
            else:
                dx = INFINITE
            if lines>1:
                dy = (maxy-miny)/(lines-1)
            else:
                dy = INFINITE
            if self.Direction.get() == "x":
                self.toolpath = self.pathgenerator.GenerateToolPath(minx, maxx, miny, maxy, minz, maxz, dx, dy, 0)
            elif self.Direction.get() == "y":
                self.toolpath = self.pathgenerator.GenerateToolPath(minx, maxx, miny, maxy, minz, maxz, dy, dx, 1)

        elif self.PathGeneratorName.get() == "PushCutter":
            if self.PathProcessorName.get() == "PathAccumulator":
                self.option = PathAccumulator()
            elif self.PathProcessorName.get() == "SimpleCutter":
                self.option = SimpleCutter()
            elif self.PathProcessorName.get() == "ZigZagCutter":
                self.option = ZigZagCutter()
            elif self.PathProcessorName.get() == "PolygonCutter":
                self.option = PolygonCutter()
            elif self.PathProcessorName.get() == "ContourCutter":
                self.option = ContourCutter()
            else:
                self.option = None
            self.pathgenerator = PushCutter(self.cutter, self.model, self.option);
            if self.PathProcessorName.get() == "ContourCutter" and samples>1:
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
            if self.Direction.get() == "x":
                self.toolpath = self.pathgenerator.GenerateToolPath(minx, maxx, miny, maxy, minz, maxz, 0, dy, dz)
            elif self.Direction.get() == "y":
                self.toolpath = self.pathgenerator.GenerateToolPath(minx, maxx, miny, maxy, minz, maxz, dy, 0, dz)
            elif self.Direction.get() == "xy":
                self.toolpath = self.pathgenerator.GenerateToolPath(minx, maxx, miny, maxy, minz, maxz, dy, dy, dz)
        self.ogl.tkRedraw()

    def browseSaveAs(self):
        filename = tkFileDialog.SaveAs(self, filetypes=[("GCODE files", ".nc .gc .ngc")]).show()
        if filename:
            self.save(filename)

    def setOutputFilename(self, filename):
        if filename:
            self.OutputFileName.set(filename)

    def save(self, filename):
        self.OutputFileName.set(filename)
        if self.toolpath:
            offset = float(self.ToolRadius.get())/2
            minx = float(self.MinX.get())-offset
            maxx = float(self.MaxX.get())+offset
            miny = float(self.MinY.get())-offset
            maxy = float(self.MaxY.get())+offset
            minz = float(self.MinZ.get())-offset
            maxz = float(self.MaxZ.get())+offset
            exporter = SimpleGCodeExporter.ExportPathList(filename, self.toolpath, self.Unit.get(), minx, miny, maxz, self.FeedRate.get(), self.Speed.get())

    def createWidgets(self):
        self.ogl = OpenglWidget(self, width=600, height=500, double=1)

        self.TopFrame = Tk.Frame(self).pack(side=Tk.TOP, expand=0, fill=Tk.X)

        self.InputFileFrame = Tk.Frame(self.TopFrame)
        self.InputFileFrame.pack(side=Tk.TOP, anchor=Tk.W, expand=0, fill=Tk.X)
        Tk.Label(self.InputFileFrame, text="Input File: ").pack(side=Tk.LEFT, anchor=Tk.W)
        self.InputFileName = Tk.StringVar()
        Tk.Entry(self.InputFileFrame, textvariable=self.InputFileName).pack(side=Tk.LEFT, expand=1, fill=Tk.X)
        Tk.Button(self.InputFileFrame, text="Import...",command=self.browseOpen).pack(side=Tk.RIGHT)

        self.CutterFrame = Tk.Frame(self.TopFrame)
        self.CutterFrame.pack(side=Tk.TOP, anchor=Tk.W)
        Tk.Label(self.CutterFrame, text="Tool: ").pack(side=Tk.LEFT)
        self.CutterName = Tk.StringVar()
        self.CutterName.set(Cutters.list[0])
        for cutter in Cutters.list:
            Tk.Radiobutton(self.CutterFrame, text=cutter, variable=self.CutterName, value=cutter).pack(side=Tk.LEFT)

        self.PathGeneratorFrame = Tk.Frame(self.TopFrame)
        self.PathGeneratorFrame.pack(side=Tk.TOP, expand=0, anchor=Tk.W)
        Tk.Label(self.PathGeneratorFrame, text="PathGenerator: ").pack(side=Tk.LEFT)
        self.PathGeneratorName = Tk.StringVar()
        self.PathGeneratorName.set(PathGenerators.list[0])
        for PathGenerator in PathGenerators.list:
            Tk.Radiobutton(self.PathGeneratorFrame, text=PathGenerator, variable=self.PathGeneratorName, value=PathGenerator).pack(side=Tk.LEFT)

        self.PathProcessorFrame = Tk.Frame(self.TopFrame)
        self.PathProcessorFrame.pack(side=Tk.TOP, expand=0, anchor=Tk.W)
        Tk.Label(self.PathProcessorFrame, text="Postprocessor: ").pack(side=Tk.LEFT)
        self.PathProcessorName = Tk.StringVar()
        self.PathProcessorName.set(PathProcessors.list[0])
        for option in PathProcessors.list:
            Tk.Radiobutton(self.PathProcessorFrame, text=option, variable=self.PathProcessorName, value=option).pack(side=Tk.LEFT)

        self.ConfigurationFrame = Tk.Frame(self.TopFrame)
        self.ConfigurationFrame.pack(side=Tk.TOP, anchor=Tk.W, expand=0, fill=Tk.X)
        Tk.Label(self.ConfigurationFrame, text="Tool Radius: ").pack(side=Tk.LEFT)
        self.ToolRadius = Tk.StringVar()
        self.ToolRadius.set("1.0")
        s = Tk.Spinbox(self.ConfigurationFrame, width=5, text='Radius', from_=0.1, to=5.0, increment=0.1, format="%2.1f")
        s.pack(side=Tk.LEFT)
        s["textvariable"] = self.ToolRadius

        Tk.Label(self.ConfigurationFrame, text="Torus Radius: ").pack(side=Tk.LEFT)
        self.TorusRadius = Tk.StringVar()
        self.TorusRadius.set("0.25")
        s = Tk.Spinbox(self.ConfigurationFrame, width=5, text='Toroid', from_=0.1, to=5.0, increment=0.1, format="%2.1f")
        s["textvariable"] = self.TorusRadius
        s.pack(side=Tk.LEFT)

        Tk.Label(self.ConfigurationFrame, text="Unit: ").pack(side=Tk.LEFT)
        self.Unit = Tk.StringVar()
        self.Unit.set("mm")
        Tk.Radiobutton(self.ConfigurationFrame, text="mm", variable=self.Unit, value="mm", command=self.ogl.tkRedraw).pack(side=Tk.LEFT)
        Tk.Radiobutton(self.ConfigurationFrame, text="in", variable=self.Unit, value="in", command=self.ogl.tkRedraw).pack(side=Tk.LEFT)

        Tk.Label(self.ConfigurationFrame, text="Dir: ").pack(side=Tk.LEFT)
        self.Direction = Tk.StringVar()
        self.Direction.set("x")
        Tk.Radiobutton(self.ConfigurationFrame, text="x", variable=self.Direction, value="x", command=self.ogl.tkRedraw).pack(side=Tk.LEFT)
        Tk.Radiobutton(self.ConfigurationFrame, text="y", variable=self.Direction, value="y", command=self.ogl.tkRedraw).pack(side=Tk.LEFT)
        Tk.Radiobutton(self.ConfigurationFrame, text="xy", variable=self.Direction, value="xy", command=self.ogl.tkRedraw).pack(side=Tk.LEFT)

        self.MinX = Tk.StringVar()
        self.MinX.set("-7")
        self.MinY = Tk.StringVar()
        self.MinY.set("-7")
        self.MinZ = Tk.StringVar()
        self.MinZ.set("0")
        self.MaxX = Tk.StringVar()
        self.MaxX.set("+7")
        self.MaxY = Tk.StringVar()
        self.MaxY.set("+7")
        self.MaxZ = Tk.StringVar()
        self.MaxZ.set("+3")

        self.StockModelFrame = Tk.Frame(self.TopFrame)
        self.StockModelFrame.pack(side=Tk.TOP, anchor=Tk.W, expand=0, fill=Tk.X)
        Tk.Label(self.StockModelFrame, text="Min X").pack(side=Tk.LEFT)
        Tk.Entry(self.StockModelFrame, textvariable=self.MinX, width=6).pack(side=Tk.LEFT)
        Tk.Label(self.StockModelFrame, text="Min Y").pack(side=Tk.LEFT)
        Tk.Entry(self.StockModelFrame, textvariable=self.MinY, width=6).pack(side=Tk.LEFT)
        Tk.Label(self.StockModelFrame, text="Min Z").pack(side=Tk.LEFT)
        Tk.Entry(self.StockModelFrame, textvariable=self.MinZ, width=6).pack(side=Tk.LEFT)

        Tk.Label(self.StockModelFrame, text="Max X").pack(side=Tk.LEFT)
        Tk.Entry(self.StockModelFrame, textvariable=self.MaxX, width=6).pack(side=Tk.LEFT)
        Tk.Label(self.StockModelFrame, text="Max Y").pack(side=Tk.LEFT)
        Tk.Entry(self.StockModelFrame, textvariable=self.MaxY, width=6).pack(side=Tk.LEFT)
        Tk.Label(self.StockModelFrame, text="Max Z").pack(side=Tk.LEFT)
        Tk.Entry(self.StockModelFrame, textvariable=self.MaxZ, width=6).pack(side=Tk.LEFT)

        self.ConfigFrame = Tk.Frame(self.TopFrame)
        self.ConfigFrame.pack(side=Tk.TOP, anchor=Tk.W, expand=0, fill=Tk.X)
        self.Layers = Tk.StringVar()
        self.Layers.set("1")
        Tk.Label(self.ConfigFrame, text="Layers").pack(side=Tk.LEFT)
        Tk.Entry(self.ConfigFrame, textvariable=self.Layers, width=6).pack(side=Tk.LEFT)
        self.Samples = Tk.StringVar()
        self.Samples.set("50")
        Tk.Label(self.ConfigFrame, text="Samples").pack(side=Tk.LEFT)
        Tk.Entry(self.ConfigFrame, textvariable=self.Samples, width=6).pack(side=Tk.LEFT)
        self.Lines = Tk.StringVar()
        self.Lines.set("20")
        Tk.Label(self.ConfigFrame, text="Lines").pack(side=Tk.LEFT)
        Tk.Entry(self.ConfigFrame, textvariable=self.Lines, width=6).pack(side=Tk.LEFT)
        Tk.Button(self.ConfigFrame, text="Generate Toolpath", command=self.generateToolpath).pack(side=Tk.RIGHT)

        self.OutputFileFrame = Tk.Frame(self.TopFrame)
        self.OutputFileFrame.pack(side=Tk.TOP, anchor=Tk.W, expand=0, fill=Tk.X)
        Tk.Label(self.OutputFileFrame, text= "Output File: ").pack(side=Tk.LEFT)
        self.OutputFileName = Tk.StringVar()
        self.OutputFileField = Tk.Entry(self.OutputFileFrame, textvariable=self.OutputFileName).pack(side=Tk.LEFT, expand=1, fill=Tk.X)

        self.FeedRate = Tk.StringVar()
        self.FeedRate.set("200")
        Tk.Label(self.OutputFileFrame, text="FeedRate").pack(side=Tk.LEFT)
        Tk.Entry(self.OutputFileFrame, textvariable=self.FeedRate, width=6).pack(side=Tk.LEFT)
        self.Speed = Tk.StringVar()
        self.Speed.set("1000")
        Tk.Label(self.OutputFileFrame, text="Speed").pack(side=Tk.LEFT)
        Tk.Entry(self.OutputFileFrame, textvariable=self.Speed, width=6).pack(side=Tk.LEFT)


        self.OutputFileBrowse = Tk.Button(self.OutputFileFrame, text="Export...", command=self.browseSaveAs).pack(side=Tk.RIGHT)

        self.ViewFrame = Tk.Frame(self.TopFrame)
        self.ViewFrame.pack(side=Tk.TOP, anchor=Tk.W, expand=0)
        Tk.Label(self.ViewFrame, text="View: ").pack(side=Tk.LEFT)
        Tk.Button(self.ViewFrame, text="Reset", command=self.resetView).pack(side=Tk.LEFT)
        Tk.Button(self.ViewFrame, text="Front", command=self.frontView).pack(side=Tk.LEFT)
        Tk.Button(self.ViewFrame, text="Back", command=self.backView).pack(side=Tk.LEFT)
        Tk.Button(self.ViewFrame, text="Left", command=self.leftView).pack(side=Tk.LEFT)
        Tk.Button(self.ViewFrame, text="Right", command=self.rightView).pack(side=Tk.LEFT)
        Tk.Button(self.ViewFrame, text="Top", command=self.topView).pack(side=Tk.LEFT)

        self.ogl.pack(side='bottom', expand=1, fill=Tk.BOTH)
        self.ogl.set_background(0,0,0)
        self.ogl.bind('<Button-2>',self.ogl.tkRecordMouse)
        self.ogl.bind('<B2-Motion>', self.ogl.tkTranslate)
        self.ogl.bind('<Button-1>', self.ogl.StartRotate)
        self.ogl.bind('<B1-Motion>', self.ogl.tkRotate)
        self.ogl.bind('<Button-3>', self.ogl.tkRecordMouse)
        self.ogl.bind('<B3-Motion>', self.ogl.tkScale)

        self.ogl.redraw = self.Redraw
        self.pack(expand=1, fill=Tk.BOTH)

    def __init__(self, master=None):
        Tk.Frame.__init__(self, master)
        self.model = None
        self.toolpath = None
        self.createWidgets()
        self.scale = 0.2
        self.ogl.tkRedraw()
        self.resetView()

    def resetView(self):
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()
        GL.glScalef(self.scale,self.scale,self.scale)
        GL.glRotatef(110,1.0,0.0,0.0)
        GL.glRotatef(180,0.0,1.0,0.0)
        GL.glRotatef(160,0.0,0.0,1.0)
        self.ogl.tkRedraw()

    def frontView(self):
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()
        GL.glScalef(self.scale,self.scale,self.scale)
        GL.glRotatef(-90,1.0,0,0)
        self.ogl.tkRedraw()

    def backView(self):
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()
        GL.glScalef(self.scale,self.scale,self.scale)
        GL.glRotatef(-90,1.0,0,0)
        GL.glRotatef(180,0,0,1.0)
        self.ogl.tkRedraw()

    def leftView(self):
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()
        GL.glScalef(self.scale,self.scale,self.scale)
        GL.glRotatef(-90,1.0,0,0)
        GL.glRotatef(90,0,0,1.0)
        self.ogl.tkRedraw()

    def rightView(self):
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()
        GL.glScalef(self.scale,self.scale,self.scale)
        GL.glRotatef(-90,1.0,0,0)
        GL.glRotatef(-90,0,0,1.0)
        self.ogl.tkRedraw()

    def topView(self):
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()
        GL.glScalef(self.scale,self.scale,self.scale)
        self.ogl.tkRedraw()



if __name__ == "__main__":
    app = SimpleGui()
    app.model = TestModel.TestModel()
    app.mainloop()
