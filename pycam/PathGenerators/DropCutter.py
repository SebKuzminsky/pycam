from pycam.PathProcessors import *
from pycam.Geometry import *
from pycam.Geometry.utils import *

class DropCutter:

    def __init__(self, cutter, model, PathProcessor=None):
        self.cutter = cutter
        self.model = model
        self.processor = PathProcessor

    def GenerateToolPath(self, minx, maxx, miny, maxy, z0, z1, dx, dy, direction):
        if self.processor:
            pa = self.processor
        else:
            pa = PathAccumulator()

        if (direction==0):
            pa.new_direction(0)
            y = miny
            while y<=maxy:
                x = minx
                pa.new_scanline()
                t_last = None
                while x<=maxx:
                    p = Point(x,y,z1)
                    z_max = -INFINITE
                    cl_max = None
                    t_max = None
                    self.cutter.moveto(p)
                    for t in self.model.triangles():
                        if t.normal().z < 0: continue;
                        cl = self.cutter.drop(t)
                        if cl and (cl.z > z_max or cl_max is None):
                            z_max = cl.z
                            cl_max = cl
                            t_max = t
                    if not cl_max or cl_max.z<z0:
                        cl_max = Point(x,y,z0)

                    if (t_max and not t_last) or (t_last and not t_max):
                        if cl_last.z < z_max:
                            pa.append(Point(cl_last.x,cl_last.y,cl_max.z))
                        else:
                            pa.append(Point(cl_max.x,cl_max.y,cl_last.z))
                    elif (t_max and t_last and cl_last and cl_max ) and (t_max != t_last):
                        nxl = -t_last.normal().x
                        nzl = t_last.normal().z
                        nxm = -t_max.normal().x
                        nzm = t_max.normal().z
                        xl = cl_last.x
                        zl = cl_last.z
                        xm = cl_max.x
                        zm = cl_max.z
                        try:
                            X = (zl-zm+(xm*nxm/nzm+xl*nxl/nzl))/(nxm/nzm+nxl/nzl)
                            Y = cl_last.y
                            Z = zl + (X-xl)*nxl/nzm
                            if xl < X and X < xm:
                                pa.append(Point(X,Y,Z))
                        except:
                            pass
                    pa.append(cl_max)

                    cl_last = cl_max
                    t_last = t_max
                    x += dx

                pa.end_scanline()
                y += dy

            pa.end_direction()
        if direction==1:
            pa.new_direction(1)
            x = minx
            while x<=maxx:
                y = miny
                pa.new_scanline()
                t_last = None
                while y<=maxy:
                    p = Point(x,y,z1)
                    z_max = -INFINITE
                    cl_max = None
                    t_max = None
                    self.cutter.moveto(p)
                    for t in self.model.triangles():
                        if t.normal().z < 0: continue;
                        cl = self.cutter.drop(t)
                        if cl and (cl.z > z_max or cl_max is None):
                            z_max = cl.z
                            cl_max = cl
                            t_max = t
                    if not cl_max or cl_max.z<z0:
                        cl_max = Point(x,y,z0)


                    if (t_max and not t_last) or (t_last and not t_max):
                        if cl_last.z < z_max:
                            pa.append(Point(cl_last.x,cl_last.y,cl_max.z))
                        else:
                            pa.append(Point(cl_max.x,cl_max.y,cl_last.z))
                    elif (t_max and t_last and cl_last and cl_max ) and (t_max != t_last):
                        nyl = t_last.normal().y
                        nzl = t_last.normal().z
                        nym = t_max.normal().y
                        nzm = t_max.normal().z
                        yl = cl_last.y
                        zl = cl_last.z
                        ym = cl_max.y
                        zm = cl_max.z
                        try:
                            X = cl_last.x
                            Y = (zl-zm+(ym*nym/nzm+yl*nyl/nzl))/(nym/nzm+nyl/nzl)
                            Z = zl + (Y-yl)*nyl/nzm
                            if yl > Y and Y < ym:
                                pa.append(Point(X,Y,Z))
                        except:
                            pass

                    pa.append(cl_max)

                    cl_last = cl_max
                    t_last = t_max
                    y += dy

                pa.end_scanline()
                x += dx

            pa.end_direction()

        pa.finish()
        return pa.paths
