from utils import *
from Point import *
from Line import *
from Triangle import *

try:
    from OpenGL.GL import *
    from OpenGL.GLUT import *
    from OpenGL.GLU import *
except:
    pass

class Model:
    id = 0

    def __init__(self):
        self.id = Model.id
        Model.id += 1
        self._triangles = []
        self.name = "model%d" % self.id

    def to_mged(self): # TODO: optimize to not export points multiple times
        s = "in %s bot" % self.name
        s += " %d" % (len(self._triangles)*3)
        s += " %d" % len(self._triangles)
        s += " 1 3"
        for t in self._triangles:
            s += " %g %g %g" % (t.p1.x,t.p1.y,t.p1.z)
            s += " %g %g %g" % (t.p2.x,t.p2.y,t.p2.z)
            s += " %g %g %g" % (t.p3.x,t.p3.y,t.p3.z)
        i = 0
        for t in self._triangles:
            s += " %d %d %d" % (i, i+1, i+2)
            i += 3
        s += "\n"
        return s

    def to_OpenGL(self):
        if True:
            glBegin(GL_TRIANGLES)
            for t in self._triangles:
                glVertex3f(t.p1.x, t.p1.y, t.p1.z)
                glVertex3f(t.p2.x, t.p2.y, t.p2.z)
                glVertex3f(t.p3.x, t.p3.y, t.p3.z)
            glEnd()
        else:
            for t in self._triangles:
                t.to_OpenGL()

    def append(self, t):
        self._triangles.append(t)

    def triangles(self):
        return self._triangles

    def subdivide(self, depth):
        model = Model()
        for t in self._triangles:
            for s in t.subdivide(depth):
                model.append(s)
        return model


