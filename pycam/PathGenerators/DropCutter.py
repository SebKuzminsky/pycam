from pycam.PathProcessors import *
from pycam.Geometry import *
from pycam.Geometry.utils import *

class DropCutter:
    
    def __init__(self, cutter, model, PathProcessor=None):
        self.cutter = cutter
        self.model = model
        self.processor = PathProcessor

    def GenerateToolPath(self, minx, maxx, miny, maxy, z0, z1, dx, dy, dz=0):
        if self.processor:
            pa = self.processor
        else:
            pa = PathAccumulator()

        pa.new_direction(0)
        y = miny
        while y<=maxy:
            x = minx
            pa.new_scanline()
            while x<=maxx:
                p = Point(x,y,z1)
                z_max = -INFINITE
                cl_max = None
                self.cutter.moveto(p)
                for t in self.model.triangles():
                    if t.normal().z < 0: continue;
                    cl = self.cutter.drop(t)
                    if cl and (cl.z > z_max or cl_max is None):
                        z_max = cl.z
                        cl_max = cl
                if not cl_max or cl_max.z<z0:
                    cl_max = Point(x,y,z0)
                pa.append(cl_max)

                x += dx

            pa.end_scanline()
            y += dy

        pa.end_direction()
        pa.finish()
        return pa.paths
