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
        self.minx = None
        self.miny = None
        self.minz = None
        self.maxx = None
        self.maxy = None
        self.maxz = None
        self._maxsize = None

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

    def _update_limits(self, t):
        if self.minx is None:
            self.minx = t.minx()
            self.miny = t.miny()
            self.minz = t.minz()
            self.maxx = t.maxx()
            self.maxy = t.maxy()
            self.maxz = t.maxz()
        else:
            self.minx = min(self.minx, t.minx())
            self.miny = min(self.miny, t.miny())
            self.minz = min(self.minz, t.minz())
            self.maxx = max(self.maxx, t.maxx())
            self.maxy = max(self.maxy, t.maxy())
            self.maxz = max(self.maxz, t.maxz())

    def append(self, t):
        self._update_limits(t)
        self._triangles.append(t)

    def maxsize(self):
        if self._maxsize is None:
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

    def reset_cache(self):
        self.minx = None
        self.miny = None
        self.minz = None
        self.maxx = None
        self.maxy = None
        self.maxz = None
        for t in self._triangles:
            self._update_limits(t)
        self._maxsize = None

    def transform(self, matrix):
        processed = []
        for tr in self._triangles:
            for point in (tr.p1, tr.p2, tr.p3):
                if not point.id in processed:
                    processed.append(point.id)
                    x = point.x * matrix[0][0] + point.y * matrix[0][1] + point.z * matrix[0][2] + matrix[0][3]
                    y = point.x * matrix[1][0] + point.y * matrix[1][1] + point.z * matrix[1][2] + matrix[1][3]
                    z = point.x * matrix[2][0] + point.y * matrix[2][1] + point.z * matrix[2][2] + matrix[2][3]
                    point.x = x
                    point.y = y
                    point.z = z
            tr.reset_cache()
        self.reset_cache()

