import pycam.Geometry

from pycam.Geometry import *
from pycam.Geometry.utils import *
from pycam.Geometry.intersection import *
from pycam.Cutters.BaseCutter import BaseCutter

from math import sqrt

try:
    import OpenGL.GL as GL
    import OpenGL.GLU as GLU
    import OpenGL.GLUT as GLUT
    GL_enabled = True
except:
    GL_enabled = False

class ToroidalCutter(BaseCutter):

    def __init__(self, radius, minorradius, location=Point(0,0,0), height=10):
        BaseCutter.__init__(self, location, radius)
        self.majorradius = radius-minorradius
        self.minorradius = minorradius
        self.height = height
        self.axis = Point(0,0,1)
        self.center = Point(location.x, location.y, location.z+minorradius)
        self.majorradiussq = sqr(self.majorradius)
        self.minorradiussq = sqr(self.minorradius)

    def __repr__(self):
        return "ToroidalCutter<%s,%f,R=%f,r=%f>" % (self.location,self.radius,self.majorradius,self.minorradius)

    def __cmp__(self, other):
        """ Compare Cutters by shape and size (ignoring the location) """
        if isinstance(other, ToroidalCutter):
            # compare the relevant attributes
            return cmp((self.radius, self.majorradius, self.minorradius),
                    (other.radius, other.majorradius, other.minorradius))
        else:
            # just return a string comparison
            return cmp(str(self), str(other))

    def get_shape(self, format="ODE", additional_distance=0.0):
        if format == "ODE":
            import ode
            from pycam.Cutters.CylindricalCutter import CylindricalCutter
            # TODO: use an appromixated trimesh instead (ODE does not support toroidal shapes)
            # for now: use the simple cylinder shape - this should not do any harm
            self.shape[format] = CylindricalCutter(self.radius, self.location,
                    height=self.height).get_shape(format, additional_distance)
            return self.shape[format]

    def to_OpenGL(self):
        if not GL_enabled:
            return
        GL.glPushMatrix()
        GL.glTranslate(self.center.x, self.center.y, self.center.z)
        GLUT.glutSolidTorus(self.minorradius, self.majorradius, 10, 20)
        if not hasattr(self,"_cylinder"):
            self._cylinder = GLU.gluNewQuadric()
        GLU.gluCylinder(self._cylinder, self.radius, self.radius, self.height, 10, 20)
        GL.glPopMatrix()
        GL.glPushMatrix()
        GL.glTranslate(self.location.x, self.location.y, self.location.z)
        if not hasattr(self,"_disk"):
            self._disk = GLU.gluNewQuadric()
        GLU.gluDisk(self._disk, 0, self.majorradius, 20, 10)
        GL.glPopMatrix()

    def moveto(self, location):
        BaseCutter.moveto(self, location)
        self.center = Point(location.x, location.y, location.z+self.minorradius)

    def intersect_torus_plane(self, direction, triangle):
        (ccp,cp,l) = intersect_torus_plane(self.center, self.axis, self.majorradius, self.minorradius, direction, triangle)
        if cp:
            cl = cp.add(self.location.sub(ccp))
            return (cl,ccp,cp,l)
        return (None, None, None, INFINITE)

    def intersect_torus_triangle(self, direction, triangle):
        (cl,ccp,cp,d) = self.intersect_torus_plane(direction, triangle)
        if cp and triangle.point_inside(cp):
            return (cl,d)
        return (None,INFINITE)

    def intersect_torus_point(self, direction, point):
        (ccp,cp,l) = intersect_torus_point(self.center, self.axis, self.majorradius, self.minorradius, self.majorradiussq, self.minorradiussq, direction, point)
        if ccp:
            cl = point.add(self.location.sub(ccp))
            return (cl, ccp, point, l)
        return (None, None, None, INFINITE)

    def intersect_torus_vertex(self, direction, point):
        (cl,ccp,cp,l) = self.intersect_torus_point(direction, point)
        return (cl,l)

    def intersect_torus_edge(self, direction, edge):        # TODO: calculate "optimal" scale = max(dir.dot(axis)/minor,dir.dot(dir.cross(axis).normalized())/major)
        # "When in doubt, use brute force." Ken Thompson
        min_m = 0
        min_l = INFINITE
        min_cl = None
        scale = int(edge.len()/self.minorradius*2)
        if scale<3:
            scale = 3
        for i in range(0,scale+1):
            m = float(i)/(scale)
            p = edge.point(m)
            (cl,ccp,cp,l) = self.intersect_torus_point(direction, p)
            if not cl:
                continue
            if l<min_l:
                min_m = m
                min_l = l
                min_cl = cl
        if min_l == INFINITE:
            return (None, INFINITE)
        scale2 = 10
        for i in range(1,scale2+1):
            m = min_m + ((float(i)/(scale2))*2-1)/scale
            if m<0 or m>1:
                continue
            p = edge.point(m)
            (cl,ccp,cp,l) = self.intersect_torus_point(direction, p)
            if not cl:
                continue
            if l<min_l:
                min_l = l
                min_cl = cl
        return (min_cl, min_l)

    def intersect_cylinder_point(self, direction, point):
        (ccp,cp,l) = intersect_cylinder_point(self.center, self.axis, self.radius, self.radiussq, direction, point)
        # offset intersection
        if ccp:
            cl = self.location.add(direction.mul(l))
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
            cl = self.location.add(cp.sub(ccp))
            return (cl,ccp,cp,l)
        return (None, None, None, INFINITE)

    def intersect_cylinder_edge(self, direction, edge):
        (cl,ccp,cp,l) = self.intersect_cylinder_line(direction, edge)
        if ccp and ccp.z<self.center.z:
            return (None,INFINITE)
        if ccp:
            m = cp.sub(edge.p1).dot(edge.dir())
            if m<0 or m>edge.len():
                return (None,INFINITE)
        return (cl,l)

    def intersect_circle_plane(self, direction, triangle):
        (ccp,cp,l) = intersect_circle_plane(self.location, self.majorradius, direction, triangle)
        # offset intersection
        if ccp:
            cl = cp.sub(ccp.sub(self.location))
            return (cl,ccp,cp,l)
        return (None, None, None, INFINITE)

    def intersect_circle_triangle(self, direction, triangle):
        (cl,ccp,cp,d) = self.intersect_circle_plane(direction, triangle)
        if cp and triangle.point_inside(cp):
            return (cl,d)
        return (None,INFINITE)

    def intersect_circle_point(self, direction, point):
        (ccp, cp, l) = intersect_circle_point(self.location, self.axis, self.majorradius, self.majorradiussq, direction, point)
        if ccp:
            cl = cp.sub(ccp.sub(self.location))
            return (cl,ccp,point,l)
        return (None,None,None,INFINITE)

    def intersect_circle_vertex(self, direction, point):
        (cl,ccp,cp,l) = self.intersect_circle_point(direction, point)
        return (cl,l)

    def intersect_circle_line(self, direction, edge):
        (ccp,cp,l) = intersect_circle_line(self.location, self.axis, self.majorradius, self.majorradiussq, direction, edge)
        if ccp:
            cl = cp.sub(ccp.sub(self.location))
            return (cl,ccp,cp,l)
        return (None, None, None, INFINITE)

    def intersect_circle_edge(self, direction, edge):
        (cl,ccp,cp,l) = self.intersect_circle_line(direction, edge)
        if cp:
            # check if the contact point is between the endpoints
            m = cp.sub(edge.p1).dot(edge.dir())
            if m<0 or m>edge.len():
                return (None,INFINITE)
        return (cl,l)

    def intersect(self, direction, triangle):
        (cl_t,d_t) = self.intersect_torus_triangle(direction, triangle)
        d = INFINITE
        cl = None
        if d_t < d:
            d = d_t
            cl = cl_t
        (cl_e1,d_e1) = self.intersect_torus_edge(direction, triangle.e1)
        (cl_e2,d_e2) = self.intersect_torus_edge(direction, triangle.e2)
        (cl_e3,d_e3) = self.intersect_torus_edge(direction, triangle.e3)
        if d_e1 < d:
            d = d_e1
            cl = cl_e1
        if d_e2 < d:
            d = d_e2
            cl = cl_e2
        if d_e3 < d:
            d = d_e3
            cl = cl_e3
        (cl_p1,d_p1) = self.intersect_torus_vertex(direction, triangle.p1)
        (cl_p2,d_p2) = self.intersect_torus_vertex(direction, triangle.p2)
        (cl_p3,d_p3) = self.intersect_torus_vertex(direction, triangle.p3)
        if d_p1 < d:
            d = d_p1
            cl = cl_p1
        if d_p2 < d:
            d = d_p2
            cl = cl_p2
        if d_p3 < d:
            d = d_p3
            cl = cl_p3
        (cl_t,d_t) = self.intersect_circle_triangle(direction, triangle)
        if d_t < d:
            d = d_t
            cl = cl_t
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
        if direction.x != 0 or direction.y != 0:
            (cl_p1,d_p1) = self.intersect_cylinder_vertex(direction, triangle.p1)
            (cl_p2,d_p2) = self.intersect_cylinder_vertex(direction, triangle.p2)
            (cl_p3,d_p3) = self.intersect_cylinder_vertex(direction, triangle.p3)
            if d_p1 < d:
                d = d_p1
                cl = cl_p1
            if d_p2 < d:
                d = d_p2
                cl = cl_p2
            if d_p3 < d:
                d = d_p3
                cl = cl_p3
            (cl_e1,d_e1) = self.intersect_cylinder_edge(direction, triangle.e1)
            (cl_e2,d_e2) = self.intersect_cylinder_edge(direction, triangle.e2)
            (cl_e3,d_e3) = self.intersect_cylinder_edge(direction, triangle.e3)
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
