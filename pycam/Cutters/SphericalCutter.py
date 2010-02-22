import pycam.Geometry

from pycam.Geometry import *
from pycam.Geometry.utils import *
from pycam.Geometry.intersection import *
from pycam.Cutters.BaseCutter import BaseCutter

from math import sqrt

try:
    import OpenGL.GL as GL
    import OpenGL.GLU as GLU
    GL_enabled = True
except:
    GL_enabled = False

class SphericalCutter(BaseCutter):

    def __init__(self, radius, location=Point(0,0,0), height=10):
        BaseCutter.__init__(self, location, radius)
        self.height = height
        self.axis = Point(0,0,1)
        self.center = Point(location.x, location.y, location.z+radius)

    def __repr__(self):
        return "SphericalCutter<%s,%s>" % (self.location,self.radius)

    def get_shape(self, format="ODE", additional_distance=0.0):
        if format == "ODE":
            import ode
            radius = self.radius + additional_distance
            center_height = 0.5 * self.height + radius - additional_distance
            geom = ode.GeomTransform(None)
            geom_drill = ode.GeomCapsule(None, radius, self.height)
            geom_drill.setPosition((0, 0, center_height))
            geom.setGeom(geom_drill)
            geom.children = []
            def reset_shape():
                geom.children = []
            def set_position(x, y, z):
                geom.setPosition((x, y, z))
            def extend_shape(diff_x, diff_y, diff_z):
                # diff_z is assumed to be zero
                reset_shape()
                geom_end_transform = ode.GeomTransform(geom.space)
                geom_end_transform.setBody(geom.getBody())
                geom_end = ode.GeomCapsule(None, radius, self.height)
                geom_end.setPosition((diff_x, diff_y, center_height))
                geom_end_transform.setGeom(geom_end)
                # create the block that connects the two cylinders at the end
                geom_connect_transform = ode.GeomTransform(geom.space)
                geom_connect_transform.setBody(geom.getBody())
                hypotenuse = sqrt(diff_x * diff_x + diff_y * diff_y)
                cosinus = diff_x/hypotenuse
                sinus = diff_y/hypotenuse
                geom_connect = ode.GeomBox(None, (2.0 * radius, hypotenuse, self.height))
                # see http://mathworld.wolfram.com/RotationMatrix.html
                rot_matrix_box = (cosinus, sinus, 0.0, -sinus, cosinus, 0.0, 0.0, 0.0, 1.0)
                geom_connect.setRotation(rot_matrix_box)
                geom_connect.setPosition((diff_x/2.0, diff_y/2.0, center_height))
                geom_connect_transform.setGeom(geom_connect)
                # create a cylinder, that connects the two half spheres at the lower end of both drills
                geom_cyl_transform = ode.GeomTransform(geom.space)
                geom_cyl_transform.setBody(geom.getBody())
                geom_cyl = ode.GeomCylinder(None, radius, hypotenuse)
                # switch x and z axis of the cylinder and then rotate it according to diff_x/diff_y
                rot_matrix_cyl = (rot_matrix_box[2], rot_matrix_box[1], rot_matrix_box[0],
                        rot_matrix_box[5], rot_matrix_box[4], rot_matrix_box[3],
                        rot_matrix_box[8], rot_matrix_box[7], rot_matrix_box[6])
                geom_cyl.setRotation(rot_matrix_cyl)
                geom_cyl.setPosition((diff_x/2.0, diff_y/2.0, radius - additional_distance))
                geom_cyl_transform.setGeom(geom_cyl)
                # sort the geoms in order or collision probability
                geom.children = [geom_connect_transform, geom_cyl_transform, geom_end_transform]
            geom.extend_shape = extend_shape
            geom.reset_shape = reset_shape
            self.shape[format] = (geom, set_position)
            return self.shape[format]


    def to_OpenGL(self):
        if not GL_enabled:
            return
        GL.glPushMatrix()
        GL.glTranslate(self.center.x, self.center.y, self.center.z)
        if not hasattr(self,"_sphere"):
            self._sphere = GLU.gluNewQuadric()
        GLU.gluSphere(self._sphere, self.radius, 10, 10)
        if not hasattr(self,"_cylinder"):
            self._cylinder = GLU.gluNewQuadric()
        GLU.gluCylinder(self._cylinder, self.radius, self.radius, self.height, 10, 10)
        GL.glPopMatrix()

    def moveto(self, location):
        BaseCutter.moveto(self, location)
        self.center = Point(location.x, location.y, location.z+self.radius)

    def intersect_sphere_plane(self, direction, triangle):
        (ccp,cp,d) = intersect_sphere_plane(self.center, self.radius, direction, triangle)
        # offset intersection
        if ccp:
            cl = cp.add(self.location.sub(ccp))
            return (cl,ccp,cp,d)
        return (None, None, None, INFINITE)

    def intersect_sphere_triangle(self, direction, triangle):
        (cl,ccp,cp,d) = self.intersect_sphere_plane(direction, triangle)
        if cp and triangle.point_inside(cp):
            return (cl,d)
        return (None,INFINITE)

    def intersect_sphere_point(self, direction, point):
        (ccp,cp,l) = intersect_sphere_point(self.center, self.radius, self.radiussq, direction, point)
        # offset intersection
        cl = None
        if cp:
            cl = self.location.add(direction.mul(l))
        return (cl,ccp,cp,l)

    def intersect_sphere_vertex(self, direction, point):
        (cl,ccp,cp,l) = self.intersect_sphere_point(direction, point)
        return (cl,l)

    def intersect_sphere_line(self, direction, edge):
        (ccp,cp,l) = intersect_sphere_line(self.center, self.radius, self.radiussq, direction, edge)
        # offset intersection
        if ccp:
            cl = cp.sub(ccp.sub(self.location))
            return (cl,ccp,cp,l)
        return (None, None, None, INFINITE)

    def intersect_sphere_edge(self, direction, edge):
        (cl,ccp,cp,l) = self.intersect_sphere_line(direction, edge)
        if cp:
            # check if the contact point is between the endpoints
            d = edge.p2.sub(edge.p1)
            m = cp.sub(edge.p1).dot(d)
            if m<0 or m>d.normsq():
                return (None,INFINITE)
        return (cl,l)

    def intersect_cylinder_point(self, direction, point):
        (ccp,cp,l)=intersect_cylinder_point(self.center, self.axis, self.radius, self.radiussq, direction, point)
        # offset intersection
        if ccp:
            cl = cp.add(self.location.sub(ccp))
            return (cl,ccp,cp,l)
        return (None,None,None,INFINITE)

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

    def intersect_point(self, direction, point):
        return self.intersect_sphere_point(direction, point)

    def intersect(self, direction, triangle):
        (cl_t,d_t) = self.intersect_sphere_triangle(direction, triangle)
        d = INFINITE
        cl = None
        if d_t < d:
            d = d_t
            cl = cl_t
        if cl and direction.x==0 and direction.y==0:
            return (cl,d)
        (cl_e1,d_e1) = self.intersect_sphere_edge(direction, triangle.e1)
        (cl_e2,d_e2) = self.intersect_sphere_edge(direction, triangle.e2)
        (cl_e3,d_e3) = self.intersect_sphere_edge(direction, triangle.e3)
        if d_e1 < d:
            d = d_e1
            cl = cl_e1
        if d_e2 < d:
            d = d_e2
            cl = cl_e2
        if d_e3 < d:
            d = d_e3
            cl = cl_e3
        if cl and direction.x==0 and direction.y==0:
            return (cl,d)
        (cl_p1,d_p1) = self.intersect_sphere_vertex(direction, triangle.p1)
        (cl_p2,d_p2) = self.intersect_sphere_vertex(direction, triangle.p2)
        (cl_p3,d_p3) = self.intersect_sphere_vertex(direction, triangle.p3)
        if d_p1 < d:
            d = d_p1
            cl = cl_p1
        if d_p2 < d:
            d = d_p2
            cl = cl_p2
        if d_p3 < d:
            d = d_p3
            cl = cl_p3
        if cl and direction.x==0 and direction.y==0:
            return (cl,d)
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

    def drop_bis(self, triangle):
        n = triangle.normal()
        if abs(n.dot(self.axis))<epsilon:
            d = triangle.p1.sub(self.center).dot(n)
            if abs(d)>= self.radius-epsilon:
                return None
        (cl,d)= self.intersect(Point(0,0,-1), triangle)
        return cl
