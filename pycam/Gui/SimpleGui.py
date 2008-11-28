#!/usr/bin/python
import sys
sys.path.insert(0,'.')

from ConfigParser import ConfigParser

from OpenGL.GL import *
from OpenGL.Tk import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import tkFileDialog

from pycam import *
from pycam.Cutters import *
from pycam.PathGenerators import *
from pycam.PathProcessors import *
from pycam.Geometry.utils import *
from pycam.Importers import *
from pycam.Exporters import *

class OpenglWidget(Opengl):
    def __init__(self, master=None, cnf={}, **kw):
        Opengl.__init__(self, master, kw)
        glShadeModel(GL_FLAT)
#        glShadeModel(GL_SMOOTH)

        glMatrixMode(GL_MODELVIEW)
        glMaterial(GL_FRONT_AND_BACK, GL_AMBIENT, (0.1, 0.1, 0.1, 1.0))
        glMaterial(GL_FRONT_AND_BACK, GL_SPECULAR, (0.1, 0.1, 0.1, 1.0))
        glMaterial(GL_FRONT_AND_BACK, GL_SHININESS, (0.5))

#        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

    def basic_lighting(self):
        Opengl.basic_lighting(self)
        # "Let There Be Light"
        glPushMatrix()
        glLoadIdentity()
        glLightfv(GL_LIGHT0, GL_AMBIENT, (0.5, 0.5, 0.5, 1.0))
        glLightfv(GL_LIGHT0, GL_DIFFUSE, (1.0, 1.0, 1.0, 1.0))
        glLightfv(GL_LIGHT0, GL_SPECULAR, (1.0, 1.0, 1.0, 1.0))
        glLightfv(GL_LIGHT0, GL_POSITION, (2, 2, +10, 1.0))
        glEnable(GL_LIGHT0)
        glDisable(GL_LIGHTING)
        glPopMatrix()
        self.master.resetView()

class SimpleGui(Frame):

    def Redraw(self, event=None):
        # default scale and orientation
        glTranslatef(0,0,-2)

        if self.Unit.get() == "mm":
            size = 100
        else:
            size = 5

        # axes
        glBegin(GL_LINES)
        glColor3f(1,0,0)
        glVertex3f(0,0,0)
        glVertex3f(size,0,0)
        glEnd()
        glBegin(GL_LINES)
        glColor3f(0,1,0)
        glVertex3f(0,0,0)
        glVertex3f(0,size,0)
        glEnd()
        glBegin(GL_LINES)
        glColor3f(0,0,1)
        glVertex3f(0,0,0)
        glVertex3f(0,0,size)
        glEnd()

        # stock model
        minx = float(self.MinX.get())
        maxx = float(self.MaxX.get())
        miny = float(self.MinY.get())
        maxy = float(self.MaxY.get())
        minz = float(self.MinZ.get())
        maxz = float(self.MaxZ.get())
        glBegin(GL_LINES)
        glColor3f(0.3,0.3,0.3)

        glVertex3f(minx,miny,minz)
        glVertex3f(maxx,miny,minz)

        glVertex3f(minx,maxy,minz)
        glVertex3f(maxx,maxy,minz)

        glVertex3f(minx,miny,maxz)
        glVertex3f(maxx,miny,maxz)

        glVertex3f(minx,maxy,maxz)
        glVertex3f(maxx,maxy,maxz)


        glVertex3f(minx,miny,minz)
        glVertex3f(minx,maxy,minz)

        glVertex3f(maxx,miny,minz)
        glVertex3f(maxx,maxy,minz)

        glVertex3f(minx,miny,maxz)
        glVertex3f(minx,maxy,maxz)

        glVertex3f(maxx,miny,maxz)
        glVertex3f(maxx,maxy,maxz)


        glVertex3f(minx,miny,minz)
        glVertex3f(minx,miny,maxz)

        glVertex3f(maxx,miny,minz)
        glVertex3f(maxx,miny,maxz)

        glVertex3f(minx,maxy,minz)
        glVertex3f(minx,maxy,maxz)

        glVertex3f(maxx,maxy,minz)
        glVertex3f(maxx,maxy,maxz)

        glEnd()

        if self.model:
            glColor3f(0.5,.5,1)
            self.model.to_OpenGL()

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

    def browseOpen(self):
        filename = tkFileDialog.Open(self, filetypes=[("STL files", ".stl")]).show()
        self.model = None
        if filename:
            self.InputFileName.set(filename)
            self.model = STLImporter.ImportModel(filename)
        self.toolpath = None
        if self.model:
            self.scale = 2.0/self.model.maxsize()
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
        minz = float(self.MinZ.get())-offset
        maxz = float(self.MaxZ.get())+offset
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
            else:
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
            else:
                self.toolpath = self.pathgenerator.GenerateToolPath(minx, maxx, miny, maxy, minz, maxz, dy, 0, dz)
        self.ogl.tkRedraw()

    def browseSaveAs(self):
        filename = tkFileDialog.SaveAs(self, filetypes=[("GCODE files", ".nc .gc")]).show()
        if filename:
            self.OutputFileName.set(filename)
            if self.toolpath:
                offset = float(self.ToolRadius.get())/2
                minx = float(self.MinX.get())-offset
                maxx = float(self.MaxX.get())+offset
                miny = float(self.MinY.get())-offset
                maxy = float(self.MaxY.get())+offset
                minz = float(self.MinZ.get())-offset
                maxz = float(self.MaxZ.get())+offset
                exporter = SimpleGCodeExporter.ExportPathList(filename, self.toolpath, self.Unit, minx, miny, maxz)

    def createWidgets(self):
        self.ogl = OpenglWidget(self, width=600, height=500)

        self.TopFrame = Frame(self).pack(side=TOP, expand=1, fill=X)

        self.InputFileFrame = Frame(self.TopFrame)
        self.InputFileFrame.pack(side=TOP, anchor=W, expand=1, fill=X)
        Label(self.InputFileFrame, width=10, text="Input File: ").pack(side=LEFT, anchor=W)
        self.InputFileName = StringVar()
        Entry(self.InputFileFrame, textvariable=self.InputFileName).pack(side=LEFT, expand=1, fill=X)
        Button(self.InputFileFrame, text="Import...",command=self.browseOpen).pack(side=RIGHT)

        self.CutterFrame = Frame(self.TopFrame)
        self.CutterFrame.pack(side=TOP, anchor=W)
        Label(self.CutterFrame, text="Tool: ").pack(side=LEFT)
        self.CutterName = StringVar()
        self.CutterName.set(Cutters.list[0])
        for cutter in Cutters.list:
            Radiobutton(self.CutterFrame, text=cutter, variable=self.CutterName, value=cutter).pack(side=LEFT)

        self.PathGeneratorFrame = Frame(self.TopFrame)
        self.PathGeneratorFrame.pack(side=TOP, anchor=W)
        Label(self.PathGeneratorFrame, text="PathGenerator: ").pack(side=LEFT)
        self.PathGeneratorName = StringVar()
        self.PathGeneratorName.set(PathGenerators.list[0])
        for PathGenerator in PathGenerators.list:
            Radiobutton(self.PathGeneratorFrame, text=PathGenerator, variable=self.PathGeneratorName, value=PathGenerator).pack(side=LEFT)

        self.PathProcessorFrame = Frame(self.TopFrame)
        self.PathProcessorFrame.pack(side=TOP, anchor=W)
        Label(self.PathProcessorFrame, text="Postprocessor: ").pack(side=LEFT)
        self.PathProcessorName = StringVar()
        self.PathProcessorName.set(PathProcessors.list[0])
        for option in PathProcessors.list:
            Radiobutton(self.PathProcessorFrame, text=option, variable=self.PathProcessorName, value=option).pack(side=LEFT)

        self.ConfigurationFrame = Frame(self.TopFrame)
        self.ConfigurationFrame.pack(side=TOP, anchor=W, expand=1, fill=X)
        Label(self.ConfigurationFrame, text="Tool Radius: ").pack(side=LEFT)
        self.ToolRadius = StringVar()
        self.ToolRadius.set("1.0")
        s = Spinbox(self.ConfigurationFrame, width=5, text='Radius', from_=0.1, to=5.0, increment=0.1, format="%2.1f")
        s.pack(side=LEFT)
        s["textvariable"] = self.ToolRadius

        Label(self.ConfigurationFrame, text="Torus Radius: ").pack(side=LEFT)
        self.TorusRadius = StringVar()
        self.TorusRadius.set("0.25")
        s = Spinbox(self.ConfigurationFrame, width=5, text='Toroid', from_=0.1, to=5.0, increment=0.1, format="%2.1f")
        s["textvariable"] = self.TorusRadius
        s.pack(side=LEFT)

        Label(self.ConfigurationFrame, text="Unit: ").pack(side=LEFT)
        self.Unit = StringVar()
        self.Unit.set("mm")
        Radiobutton(self.ConfigurationFrame, text="mm", variable=self.Unit, value="mm", command=self.ogl.tkRedraw).pack(side=LEFT)
        Radiobutton(self.ConfigurationFrame, text="in", variable=self.Unit, value="in", command=self.ogl.tkRedraw).pack(side=LEFT)

        Label(self.ConfigurationFrame, text="Dir: ").pack(side=LEFT)
        self.Direction = StringVar()
        self.Direction.set("x")
        Radiobutton(self.ConfigurationFrame, text="x", variable=self.Direction, value="x", command=self.ogl.tkRedraw).pack(side=LEFT)
        Radiobutton(self.ConfigurationFrame, text="y", variable=self.Direction, value="y", command=self.ogl.tkRedraw).pack(side=LEFT)

        self.MinX = StringVar()
        self.MinX.set("-7")
        self.MinY = StringVar()
        self.MinY.set("-7")
        self.MinZ = StringVar()
        self.MinZ.set("0")
        self.MaxX = StringVar()
        self.MaxX.set("+7")
        self.MaxY = StringVar()
        self.MaxY.set("+7")
        self.MaxZ = StringVar()
        self.MaxZ.set("+3")

        self.StockModelFrame1 = Frame(self.TopFrame)
        self.StockModelFrame1.pack(side=TOP, anchor=W, expand=1, fill=X)
        Label(self.StockModelFrame1, text="Min X").pack(side=LEFT)
        Entry(self.StockModelFrame1, textvariable=self.MinX, width=6).pack(side=LEFT)
        Label(self.StockModelFrame1, text="Min Y").pack(side=LEFT)
        Entry(self.StockModelFrame1, textvariable=self.MinY, width=6).pack(side=LEFT)
        Label(self.StockModelFrame1, text="Min Z").pack(side=LEFT)
        Entry(self.StockModelFrame1, textvariable=self.MinZ, width=6).pack(side=LEFT)

        self.StockModelFrame2 = Frame(self.TopFrame)
        self.StockModelFrame2.pack(side=TOP, anchor=W, expand=1, fill=X)
        Label(self.StockModelFrame2, text="Max X").pack(side=LEFT)
        Entry(self.StockModelFrame2, textvariable=self.MaxX, width=6).pack(side=LEFT)
        Label(self.StockModelFrame2, text="Max Y").pack(side=LEFT)
        Entry(self.StockModelFrame2, textvariable=self.MaxY, width=6).pack(side=LEFT)
        Label(self.StockModelFrame2, text="Max Z").pack(side=LEFT)
        Entry(self.StockModelFrame2, textvariable=self.MaxZ, width=6).pack(side=LEFT)

        self.ConfigFrame = Frame(self.TopFrame)
        self.ConfigFrame.pack(side=TOP, anchor=W, expand=1, fill=X)
        self.Layers = StringVar()
        self.Layers.set("1")
        Label(self.ConfigFrame, text="Layers").pack(side=LEFT)
        Entry(self.ConfigFrame, textvariable=self.Layers, width=6).pack(side=LEFT)
        self.Samples = StringVar()
        self.Samples.set("50")
        Label(self.ConfigFrame, text="Samples").pack(side=LEFT)
        Entry(self.ConfigFrame, textvariable=self.Samples, width=6).pack(side=LEFT)
        self.Lines = StringVar()
        self.Lines.set("20")
        Label(self.ConfigFrame, text="Lines").pack(side=LEFT)
        Entry(self.ConfigFrame, textvariable=self.Lines, width=6).pack(side=LEFT)
        Button(self.ConfigFrame, text="Generate Toolpath", command=self.generateToolpath).pack(side=RIGHT)

        self.OutputFileFrame = Frame(self.TopFrame)
        self.OutputFileFrame.pack(side=TOP, anchor=W, expand=1, fill=X)
        Label(self.OutputFileFrame, width=10, text= "Output File: ").pack(side=LEFT)
        self.OutputFileName = StringVar()
        self.OutputFileField = Entry(self.OutputFileFrame, textvariable=self.OutputFileName).pack(side=LEFT, expand=1, fill=X)
        self.OutputFileBrowse = Button(self.OutputFileFrame, text="Export...", command=self.browseSaveAs).pack(side=RIGHT)

        self.ViewFrame = Frame(self.TopFrame)
        self.ViewFrame.pack(side=TOP, anchor=W, expand=0)
        Label(self.ViewFrame, text="View: ").pack(side=LEFT)
        Button(self.ViewFrame, text="Reset", command=self.resetView).pack(side=LEFT)
        Button(self.ViewFrame, text="Front", command=self.frontView).pack(side=LEFT)
        Button(self.ViewFrame, text="Back", command=self.backView).pack(side=LEFT)
        Button(self.ViewFrame, text="Left", command=self.leftView).pack(side=LEFT)
        Button(self.ViewFrame, text="Right", command=self.rightView).pack(side=LEFT)
        Button(self.ViewFrame, text="Top", command=self.topView).pack(side=LEFT)

        self.ogl.pack(side='bottom', expand=1, fill=BOTH)
        self.ogl.set_background(0,0,0)
        self.ogl.bind('<Button-2>',self.ogl.tkRecordMouse)
        self.ogl.bind('<B2-Motion>', self.ogl.tkTranslate)
        self.ogl.bind('<Button-1>', self.ogl.StartRotate)
        self.ogl.bind('<B1-Motion>', self.ogl.tkRotate)
        self.ogl.bind('<Button-3>', self.ogl.tkRecordMouse)
        self.ogl.bind('<B3-Motion>', self.ogl.tkScale)

        self.ogl.redraw = self.Redraw
        self.pack(expand=1, fill=BOTH)

    def __init__(self, master=None):
        Frame.__init__(self, master)
        self.model = None
        self.toolpath = None
        self.createWidgets()
        self.scale = 0.2
        self.ogl.tkRedraw()
        self.resetView()

    def cutmodel(self, z):
        cutter = SphericalCutter(1, Point(0,0,7))
        pc = DropCutter(cutter, self.model, PathAccumulator())

        x0 = -7.0
        x1 = +7.0
        y0 = -7.0
        y1 = +7.0
        z0 = 0.0
        z1 = 4.0

        samples = 20
        lines = 20
        layers = 10

        dx = (x1-x0)/samples
        dy = (y1-y0)/lines
        dz = (z1-z0)/(layers+1)

        self.toolpath = pc.GenerateToolPath(x0,x1,y0,y1,z0,z1,dx,dy,dz)

    def resetView(self):
        glMatrixMode(GL_MODELVIEW)
	glLoadIdentity()
        glScalef(self.scale,self.scale,self.scale)
        glRotatef(110,1.0,0.0,0.0)
        glRotatef(180,0.0,1.0,0.0)
        glRotatef(160,0.0,0.0,1.0)
        self.ogl.tkRedraw()

    def frontView(self):
        glMatrixMode(GL_MODELVIEW)
	glLoadIdentity()
        glScalef(self.scale,self.scale,self.scale)
        glRotatef(-90,1.0,0,0)
        self.ogl.tkRedraw()

    def backView(self):
        glMatrixMode(GL_MODELVIEW)
	glLoadIdentity()
        glScalef(self.scale,self.scale,self.scale)
        glRotatef(-90,1.0,0,0)
        glRotatef(180,0,0,1.0)
        self.ogl.tkRedraw()

    def leftView(self):
        glMatrixMode(GL_MODELVIEW)
	glLoadIdentity()
        glScalef(self.scale,self.scale,self.scale)
        glRotatef(-90,1.0,0,0)
        glRotatef(90,0,0,1.0)
        self.ogl.tkRedraw()

    def rightView(self):
        glMatrixMode(GL_MODELVIEW)
	glLoadIdentity()
        glScalef(self.scale,self.scale,self.scale)
        glRotatef(-90,1.0,0,0)
        glRotatef(-90,0,0,1.0)
        self.ogl.tkRedraw()

    def topView(self):
        glMatrixMode(GL_MODELVIEW)
	glLoadIdentity()
        glScalef(self.scale,self.scale,self.scale)
        self.ogl.tkRedraw()



if __name__ == "__main__":
    app = SimpleGui()
    app.model = TestModel.TestModel()
    app.mainloop()
