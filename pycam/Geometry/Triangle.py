from Point import *
from Plane import *
from utils import *
from Line import *

try:
    import OpenGL.GL as GL
    import OpenGL.GLU as GLU
    import OpenGL.GLUT as GLUT
    GL_enabled = True
except:
    GL_enabled = False

class Triangle:
    id = 0
    # points are expected to be in ClockWise order
    def __init__(self, p1=None, p2=None, p3=None, e1=None, e2=None, e3=None, n=None):
        self.id = Triangle.id
        Triangle.id += 1
        self.p1 = p1
        self.p2 = p2
        self.p3 = p3
        if (not e1) and p1 and p2:
            self.e1 = Line(p1,p2)
        else:
            self.e1 = e1
        if (not e2) and p2 and p3:
            self.e2 = Line(p2,p3)
        else:
            self.e2 = e2
        if (not e3) and p3 and p1:
            self.e3 = Line(p3,p1)
        else:
            self.e3 = e3
        self._normal = n
        self._minx = None
        self._miny = None
        self._minz = None
        self._maxx = None
        self._maxy = None
        self._maxz = None
        self._center = None
        self._middle = None
        self._radius = None
        self._radiussq = None
        self._plane = None

    def __repr__(self):
        return "Triangle%d<%s,%s,%s>" % (self.id,self.p1,self.p2,self.p3)

    def name(self):
        return "triangle%d" % self.id

    def to_OpenGL(self):
        if not GL_enabled:
            return
        GL.glBegin(GL.GL_TRIANGLES)
        GL.glVertex3f(self.p1.x, self.p1.y, self.p1.z)
        GL.glVertex3f(self.p2.x, self.p2.y, self.p2.z)
        GL.glVertex3f(self.p3.x, self.p3.y, self.p3.z)
        GL.glEnd()
        if False: # display surface normals
            n = self.normal()
            c = self.center()
            d = 0.5
            GL.glBegin(GL.GL_LINES)
            GL.glVertex3f(c.x, c.y, c.z)
            GL.glVertex3f(c.x+n.x*d, c.y+n.y*d, c.z+n.z*d)
            GL.glEnd()
        if False and hasattr(self, "_middle"): # display bounding sphere
            GL.glPushMatrix()
            GL.glTranslate(self._middle.x, self._middle.y, self._middle.z)
            if not hasattr(self,"_sphere"):
                self._sphere = GLU.gluNewQuadric()
            GLU.gluSphere(self._sphere, self._radius, 10, 10)
            GL.glPopMatrix()
        if True: # draw triangle id on triangle face
            GL.glPushMatrix()
            cc = GL.glGetFloatv(GL.GL_CURRENT_COLOR)
            c = self.center()
            GL.glTranslate(c.x,c.y,c.z)
            p12=self.p1.add(self.p2).mul(0.5)
            p3_12=self.p3.sub(p12).normalize()
            p2_1=self.p1.sub(self.p2).normalize()
            pn=p2_1.cross(p3_12)
            GL.glMultMatrixf((p2_1.x, p2_1.y, p2_1.z, 0, p3_12.x, p3_12.y, p3_12.z, 0, pn.x, pn.y, pn.z, 0, 0,0,0,1))
            n = self.normal().mul(0.01)
            GL.glTranslatef(n.x,n.y,n.z)
            GL.glScalef(0.003,0.003,0.003)
            w = 0
            for ch in str(self.id):
                w += GLUT.glutStrokeWidth(GLUT.GLUT_STROKE_ROMAN, ord(ch))
            GL.glTranslate(-w/2,0,0)
            GL.glColor4f(1,1,1,0)
            for ch in str(self.id):
                GLUT.glutStrokeCharacter(GLUT.GLUT_STROKE_ROMAN, ord(ch))
            GL.glPopMatrix()
            GL.glColor4f(cc[0],cc[1],cc[2],cc[3])

        if False: # draw point id on triangle face
            cc = GL.glGetFloatv(GL.GL_CURRENT_COLOR)
            c = self.center()
            p12=self.p1.add(self.p2).mul(0.5)
            p3_12=self.p3.sub(p12).normalize()
            p2_1=self.p1.sub(self.p2).normalize()
            pn=p2_1.cross(p3_12)
            n = self.normal().mul(0.01)
            for p in (self.p1,self.p2,self.p3):
                GL.glPushMatrix()
                pp = p.sub(p.sub(c).mul(0.3))
                GL.glTranslate(pp.x,pp.y,pp.z)
                GL.glMultMatrixf((p2_1.x, p2_1.y, p2_1.z, 0, p3_12.x, p3_12.y, p3_12.z, 0, pn.x, pn.y, pn.z, 0, 0,0,0,1))
                GL.glTranslatef(n.x,n.y,n.z)
                GL.glScalef(0.001,0.001,0.001)
                w = 0
                for ch in str(p.id):
                    w += GLUT.glutStrokeWidth(GLUT.GLUT_STROKE_ROMAN, ord(ch))
                    GL.glTranslate(-w/2,0,0)
                GL.glColor4f(0.5,1,0.5,0)
                for ch in str(p.id):
                    GLUT.glutStrokeCharacter(GLUT.GLUT_STROKE_ROMAN, ord(ch))
                GL.glPopMatrix()
            GL.glColor4f(cc[0],cc[1],cc[2],cc[3])

    def normal(self):
        if self._normal is None:
            # calculate normal, if p1-p2-pe are in clockwise order
            vector = self.p3.sub(self.p1).cross(self.p2.sub(self.p1))
            denom = vector.norm()
            self._normal = vector.div(denom)
        return self._normal

    def plane(self):
        if self._plane is None:
            self._plane=Plane(self.center(), self.normal())
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
        denom = dot00 * dot11 - dot01 * dot01
        # originally, "u" and "v" are multiplied with "1/denom"
        # we don't do this, to avoid division by zero (for triangles that are "almost" invalid)
        u = dot11 * dot02 - dot01 * dot12
        v = dot00 * dot12 - dot01 * dot02

        # Check if point is in triangle
        return ((u * denom) >= 0) and ((v * denom) >= 0) and (u + v <= denom)

    def minx(self):
        if self._minx is None:
            self._minx = min3(self.p1.x, self.p2.x, self.p3.x)
        return self._minx

    def miny(self):
        if self._miny is None:
            self._miny = min3(self.p1.y, self.p2.y, self.p3.y)
        return self._miny

    def minz(self):
        if self._minz is None:
            self._minz = min3(self.p1.z, self.p2.z, self.p3.z)
        return self._minz

    def maxx(self):
        if self._maxx is None:
            self._maxx = max3(self.p1.x, self.p2.x, self.p3.x)
        return self._maxx

    def maxy(self):
        if self._maxy is None:
            self._maxy = max3(self.p1.y, self.p2.y, self.p3.y)
        return self._maxy

    def maxz(self):
        if self._maxz is None:
            self._maxz = max3(self.p1.z, self.p2.z, self.p3.z)
        return self._maxz

    def center(self):
        if self._center is None:
            self._center = self.p1.add(self.p2).add(self.p3).mul(1.0/3)
        return self._center

    def middle(self):
        if self._middle is None:
            self.calc_circumcircle()
        return self._middle

    def radius(self):
        if self._radius is None:
            self.calc_circumcircle()
        return self._radius

    def radiussq(self):
        if self._radiussq is None:
            self.calc_circumcircle()
        return self._radiussq

    def calc_circumcircle(self):
        # we can't use the cached value of "normal", since we don't want the normalized value
        normal = self.p2.sub(self.p1).cross(self.p3.sub(self.p2))
        denom = normal.norm()
        self._radius = (self.p2.sub(self.p1).norm()*self.p3.sub(self.p2).norm()*self.p3.sub(self.p1).norm())/(2*denom)
        self._radiussq = self._radius*self._radius
        denom2 = 2*denom*denom
        alpha = self.p3.sub(self.p2).normsq()*(self.p1.sub(self.p2).dot(self.p1.sub(self.p3))) / (denom2)
        beta  = self.p1.sub(self.p3).normsq()*(self.p2.sub(self.p1).dot(self.p2.sub(self.p3))) / (denom2)
        gamma = self.p1.sub(self.p2).normsq()*(self.p3.sub(self.p1).dot(self.p3.sub(self.p2))) / (denom2)
        self._middle = Point(self.p1.x*alpha+self.p2.x*beta+self.p3.x*gamma,
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

    def reset_cache(self):
        self._minx = None
        self._miny = None
        self._minz = None
        self._maxx = None
        self._maxy = None
        self._maxz = None
        self._center = None
        self._middle = None
        self._radius = None
        self._radiussq = None
        self._normal = None
        self._plane = None

