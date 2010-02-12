from utils import *
from Point import *
from Line import *
from Triangle import *

try:
    import OpenGL.GL as GL
    GL_enabled = True
except:
    GL_enabled = False

class Model:
    id = 0

    def __init__(self):
        self.id = Model.id
        Model.id += 1
        self._triangles = []
        self.name = "model%d" % self.id

    def to_OpenGL(self):
        if not GL_enabled:
            return
        if True:
            GL.glBegin(GL.GL_TRIANGLES)
            for t in self._triangles:
                GL.glVertex3f(t.p1.x, t.p1.y, t.p1.z)
                GL.glVertex3f(t.p2.x, t.p2.y, t.p2.z)
                GL.glVertex3f(t.p3.x, t.p3.y, t.p3.z)
            GL.glEnd()
        else:
            for t in self._triangles:
                t.to_OpenGL()

    def append(self, t):
        if not hasattr(self,"minx"):
            self.minx = t.minx()
        else:
            self.minx = min(self.minx, t.minx())

        if not hasattr(self,"miny"):
            self.miny = t.miny()
        else:
            self.miny = min(self.miny, t.miny())

        if not hasattr(self,"minz"):
            self.minz = t.minz()
        else:
            self.minz = min(self.minz, t.minz())

        if not hasattr(self,"maxx"):
            self.maxx = t.maxx()
        else:
            self.maxx = max(self.maxx, t.maxx())

        if not hasattr(self,"maxy"):
            self.maxy = t.maxy()
        else:
            self.maxy = max(self.maxy, t.maxy())

        if not hasattr(self,"maxz"):
            self.maxz = t.maxz()
        else:
            self.maxz = max(self.maxz, t.maxz())

        self._triangles.append(t)

    def maxsize(self):
        if not hasattr(self,"_maxsize"):
            self._maxsize = max3(max(abs(self.maxx),abs(self.minx)),max(abs(self.maxy),abs(self.miny)),max(abs(self.maxz),abs(self.minz)))
        return self._maxsize

    def triangles(self, minx=-INFINITE,miny=-INFINITE,minz=-INFINITE,maxx=+INFINITE,maxy=+INFINITE,maxz=+INFINITE):
        if minx==-INFINITE and miny==-INFINITE and minz==-INFINITE and maxx==+INFINITE and maxy==+INFINITE and maxz==+INFINITE:
            return self._triangles
        if hasattr(self, "t_kdtree"):
            return self.t_kdtree.Search(minx,maxx,miny,maxy)
        return self._triangles

    def subdivide(self, depth):
        model = Model()
        for t in self._triangles:
            for s in t.subdivide(depth):
                model.append(s)
        return model


