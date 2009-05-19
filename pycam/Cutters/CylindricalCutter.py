import pycam.Geometry

from pycam.Geometry import *
from pycam.Geometry.utils import *
from pycam.Geometry.intersection import *
from pycam.Cutters.BaseCutter import BaseCutter

from math import sqrt

try:
    from OpenGL.GL import *
    from OpenGL.GLU import *
    from OpenGL.GLUT import *
except:
    pass

class CylindricalCutter(BaseCutter):

    def __init__(self, radius, location=Point(0,0,0), height=10):
        BaseCutter.__init__(self, location, radius)
        self.height = height
        self.axis = Point(0,0,1)
        self.center = location

    def __repr__(self):
        return "CylindricalCutter<%s,%s>" % (self.location,self.radius)

    def to_OpenGL(self):
        glPushMatrix()
        glTranslate(self.center.x, self.center.y, self.center.z)
        if not hasattr(self,"_cylinder"):
            self._cylinder = gluNewQuadric()
        gluCylinder(self._cylinder, self.radius, self.radius, self.height, 10, 10)
        if not hasattr(self,"_disk"):
            self._disk = gluNewQuadric()
        gluDisk(self._disk, 0, self.radius, 10, 10)
        glPopMatrix()

    def moveto(self, location):
        BaseCutter.moveto(self, location)
        self.center = location

    def intersect_circle_plane(self, direction, triangle):
        (ccp,cp,d) = intersect_circle_plane(self.center, self.radius, direction, triangle)
        if ccp:
            cl = cp.add(self.location.sub(ccp))
            return (cl,ccp,cp,d)
        return (None, None, None, INFINITE)

    def intersect_circle_triangle(self, direction, triangle):
        (cl,ccp,cp,d) = self.intersect_circle_plane(direction, triangle)
        if cp and triangle.point_inside(cp):
            return (cl,d)
        return (None,INFINITE)

    def intersect_circle_point(self, direction, point):
        (ccp,cp,l) = intersect_circle_point(self.center, self.axis, self.radius, self.radiussq, direction, point)
        if ccp:
            cl = cp.add(self.location.sub(ccp))
            return (cl,ccp,cp,l)
        return (None,None,None,INFINITE)

    def intersect_circle_vertex(self, direction, point):
        (cl,ccp,cp,l) = self.intersect_circle_point(direction, point)
        return (cl,l)

    def intersect_circle_line(self, direction, edge):
        (ccp,cp,l) = intersect_circle_line(self.center, self.axis, self.radius, self.radiussq, direction, edge)
        if ccp:
            cl = cp.add(self.location.sub(ccp))
            return (cl,ccp,cp,l)
        return (None,None,None,INFINITE)

    def intersect_circle_edge(self, direction, edge):
        (cl,ccp,cp,l) = self.intersect_circle_line(direction, edge)
        if cp:
            # check if the contact point is between the endpoints
            m = cp.sub(edge.p1).dot(edge.dir())
            if m<0 or m>edge.len():
                return (None,INFINITE)
        return (cl,l)

    def intersect_cylinder_point(self, direction, point):
        (ccp,cp,l) = intersect_cylinder_point(self.center, self.axis, self.radius, self.radiussq, direction, point)
        # offset intersection
        if ccp:
            cl = cp.add(self.location.sub(ccp))
            return (cl,ccp,cp,l)
        return (None, None, None, INFINITE)

    def intersect_cylinder_vertex(self, direction, point):
        (cl,ccp,cp,l) = self.intersect_cylinder_point(direction, point)
        if ccp and ccp.z < self.center.z:
            return (None, INFINITE)
        return (cl, l)

    def intersect_cylinder_line(self, direction, edge):
        (ccp,cp,l) = intersect_cylinder_line(self.center, self.axis, self.radius, self.radiussq, direction, edge)
        # offset intersection
        if ccp:
            cl = cp.add(self.location.sub(ccp))
            return (cl,ccp,cp,l)
        return (None,None,None,INFINITE)

    def intersect_cylinder_edge(self, direction, edge):
        (cl,ccp,cp,l) = self.intersect_cylinder_line(direction, edge)
        if not ccp:
            return (None,INFINITE)
        m = cp.sub(edge.p1).dot(edge.dir())
        if m<0 or m>edge.len():
            return (None,INFINITE)
        if ccp.z<self.center.z:
            return (None,INFINITE)
        return (cl,l)

    def intersect(self, direction, triangle):
        (cl_t,d_t) = self.intersect_circle_triangle(direction, triangle)
        d = INFINITE
        cl = None
        if d_t < d:
            d = d_t
            cl = cl_t
        if cl:
            return (cl,d)
        (cl_e1,d_e1) = self.intersect_circle_edge(direction, triangle.e1)
        (cl_e2,d_e2) = self.intersect_circle_edge(direction, triangle.e2)
        (cl_e3,d_e3) = self.intersect_circle_edge(direction, triangle.e3)
        if d_e1 < d:
            d = d_e1
            cl = cl_e1
        if d_e2 < d:
            d = d_e2
            cl = cl_e2
        if d_e3 < d:
            d = d_e3
            cl = cl_e3
        if cl:
            return (cl,d)
        (cl_p1,d_p1) = self.intersect_circle_vertex(direction, triangle.p1)
        (cl_p2,d_p2) = self.intersect_circle_vertex(direction, triangle.p2)
        (cl_p3,d_p3) = self.intersect_circle_vertex(direction, triangle.p3)
        if d_p1 < d:
            d = d_p1
            cl = cl_p1
        if d_p2 < d:
            d = d_p2
            cl = cl_p2
        if d_p3 < d:
            d = d_p3
            cl = cl_p3
        if cl:
            return (cl,d)
        if direction.x != 0 or direction.y != 0:
            (cl_e1,d_e1) = self.intersect_cylinder_edge(direction, triangle.e1)
            (cl_e2,d_e2) = self.intersect_cylinder_edge(direction, triangle.e2)
            (cl_e3,d_e3) = self.intersect_cylinder_edge(direction, triangle.e3)
            if d_p1 < d:
                d = d_p1
                cl = cl_p1
            if d_p2 < d:
                d = d_p2
                cl = cl_p2
            if d_p3 < d:
                d = d_p3
                cl = cl_p3
            if cl:
                return (cl,d)
            (cl_p1,d_p1) = self.intersect_cylinder_vertex(direction, triangle.p1)
            (cl_p2,d_p2) = self.intersect_cylinder_vertex(direction, triangle.p2)
            (cl_p3,d_p3) = self.intersect_cylinder_vertex(direction, triangle.p3)
            if d_e1 < d:
                d = d_e1
                cl = cl_e1
            if d_e2 < d:
                d = d_e2
                cl = cl_e2
            if d_e3 < d:
                d = d_e3
                cl = cl_e3
        return (cl,d)
