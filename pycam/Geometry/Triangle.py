from Point import *
from Plane import *
from utils import *

ORIENTATION_CCW = 2
ORIENTATION_CW  = 3

try:
    from OpenGL.GL import *
    from OpenGL.GLU import *
    from OpenGL.GLUT import *
except:
    pass

class Triangle:
    id = 0
    # points are expected to be in ClockWise order
    def __init__(self, p1=None, p2=None, p3=None):
        self.id = Triangle.id
        Triangle.id += 1
        self.p1 = p1
        self.p2 = p2
        self.p3 = p3

    def __repr__(self):
        return "Triangle<%s,%s,%s>" % (self.p1,self.p2,self.p3)

    def name(self):
        return "triangle%d" % self.id

    def to_mged(self, sphere=False):
        s = "in %s bot 3 1" % self.name()
        s += " 1 3"
        s += " %f %f %f" % (self.p1.x,self.p1.y,self.p1.z)
        s += " %f %f %f" % (self.p2.x,self.p2.y,self.p2.z)
        s += " %f %f %f" % (self.p3.x,self.p3.y,self.p3.z)
        s += " 0 1 2"
        s += "\n"
        if sphere and hasattr(self, "_center"):
            s += "in %s_sph sph " % self.name()
            s += " %f %f %f" % (self._center.x, self._center.y, self._center.z)
            s += " %f" % self._radius
            s += "\n"
        return s

    def to_OpenGL(self):
        glBegin(GL_TRIANGLES)
        glVertex3f(self.p1.x, self.p1.y, self.p1.z)
        glVertex3f(self.p2.x, self.p2.y, self.p2.z)
        glVertex3f(self.p3.x, self.p3.y, self.p3.z)
        glEnd()
        if hasattr(self, "_center"):
            glPushMatrix()
            glTranslate(self._center.x, self._center.y, self._center.z)
            if not hasattr(self,"_sphere"):
                self._sphere = gluNewQuadric()
            gluSphere(self._sphere, self._radius, 10, 10)
            glPopMatrix()

    def normal(self):
        if not hasattr(self, '_normal'):
            self._normal = self.p3.sub(self.p1).cross(self.p2.sub(self.p1))
            denom = self._normal.norm()
#            # TODO: fix kludge: make surface normal point up for now
#            if self._normal.z < 0:
#                denom = -denom
            self._normal = self._normal.div(denom)
        return self._normal

    def plane(self):
        if not hasattr(self, '_plane'):
            if hasattr(self, '_center'):
                self._plane=Plane(self._center, self.normal())
            else:
                self._plane=Plane(self.p1, self.normal())
        return self._plane

    def point_inside(self, p):
        # http://www.blackpawn.com/texts/pointinpoly/default.html

        # Compute vectors
        v0 = self.p3.sub(self.p1)
        v1 = self.p2.sub(self.p1)
        v2 = p.sub(self.p1)

        # Compute dot products
        dot00 = v0.dot(v0)
        dot01 = v0.dot(v1)
        dot02 = v0.dot(v2)
        dot11 = v1.dot(v1)
        dot12 = v1.dot(v2)

        # Compute barycentric coordinates
        invDenom = 1 / (dot00 * dot11 - dot01 * dot01)
        u = (dot11 * dot02 - dot01 * dot12) * invDenom
        v = (dot00 * dot12 - dot01 * dot02) * invDenom

        # Check if point is in triangle
        return (u > 0) and (v > 0) and (u + v < 1)

    def minx(self):
        if not hasattr(self, "_minx"):
            self._minx = min3(self.p1.x, self.p2.x, self.p3.x)
        return self._minx

    def miny(self):
        if not hasattr(self, "_miny"):
            self._miny = min3(self.p1.y, self.p2.y, self.p3.y)
        return self._miny

    def minz(self):
        if not hasattr(self, "_minz"):
            self._minz = min3(self.p1.z, self.p2.z, self.p3.z)
        return self._minz

    def maxx(self):
        if not hasattr(self, "_maxx"):
            self._maxx = max3(self.p1.x, self.p2.x, self.p3.x)
        return self._maxx

    def maxy(self):
        if not hasattr(self, "_maxy"):
            self._maxy = max3(self.p1.y, self.p2.y, self.p3.y)
        return self._maxy

    def maxz(self):
        if not hasattr(self, "_maxz"):
            self._maxz = max3(self.p1.z, self.p2.z, self.p3.z)
        return self._maxz

    def center(self):
        if not hasattr(self, "_center"):
            self.calc_circumcircle()
        return self._center

    def radius(self):
        if not hasattr(self, "_radius"):
            self.calc_circumcircle()
        return self._radius

    def radiussq(self):
        if not hasattr(self, "_radiussq"):
            self.calc_circumcircle()
        return self._radiussq

    def calc_circumcircle(self):
        normal = self.p2.sub(self.p1).cross(self.p3.sub(self.p2))
        denom = normal.norm()
        self._radius = (self.p2.sub(self.p1).norm()*self.p3.sub(self.p2).norm()*self.p3.sub(self.p1).norm())/(2*denom)
        self._radiussq = self._radius*self._radius
        denom2 = 2*denom*denom;
        alpha = self.p3.sub(self.p2).normsq()*(self.p1.sub(self.p2).dot(self.p1.sub(self.p3))) / (denom2)
        beta  = self.p1.sub(self.p3).normsq()*(self.p2.sub(self.p1).dot(self.p2.sub(self.p3))) / (denom2)
        gamma = self.p1.sub(self.p2).normsq()*(self.p3.sub(self.p1).dot(self.p3.sub(self.p2))) / (denom2)
        self._center = Point(self.p1.x*alpha+self.p2.x*beta+self.p3.x*gamma,
                             self.p1.y*alpha+self.p2.y*beta+self.p3.y*gamma,
                             self.p1.z*alpha+self.p2.z*beta+self.p3.z*gamma)

    def subdivide(self, depth):
        sub = []
        if depth == 0:
            sub.append(self)
        else:
            p4 = self.p1.add(self.p2).div(2)
            p5 = self.p2.add(self.p3).div(2)
            p6 = self.p3.add(self.p1).div(2)
            sub += Triangle(self.p1,p4,p6).subdivide(depth-1)
            sub += Triangle(p6,p5,self.p3).subdivide(depth-1)
            sub += Triangle(p6,p4,p5).subdivide(depth-1)
            sub += Triangle(p4,self.p2,p5).subdivide(depth-1)
        return sub

