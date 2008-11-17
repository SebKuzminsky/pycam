from pycam.PathProcessors import *
from pycam.Geometry import *
from pycam.Geometry.utils import *

class Hit:
    def __init__(self, cl, t, d, dir):
        self.cl = cl
        self.t = t
        self.d = d
        self.dir = dir
    def cmp(a,b):
        return cmp(a.d, b.d)

class PushCutter:

    def __init__(self, cutter, model, pathextractor=None):
        self.cutter = cutter
        self.model = model
        self.pa = pathextractor

    def GenerateToolPath(self, minx, maxx, miny, maxy, minz, maxz, dx, dy, dz):
        if dx==0:
            forward = Point(1,0,0)
            backward = Point(-1,0,0)
        elif dy == 0:
            forward = Point(0,1,0)
            backward = Point(0,-1,0)

        z = maxz

        c = self.cutter
        model = self.model
        paths = []

        while z >= minz:
            self.pa.new_direction(0)
            x = minx
            y = miny
            while x<=maxx and y<=maxy:
                self.pa.new_scanline()

                # find all hits along scan line
                hits = []
                prev = Point(x,y,z)
                c.moveto(prev)

                for t in model.triangles():
                    if t.normal().z < 0: continue;
                    # normals point outward... and we want to approach the model from the outside!
                    n = t.normal().dot(forward)
                    if n>=0:
                        (cl,d) = c.intersect(backward, t)
                        if cl:
#                            print "< cl=",cl,",d=",-d,",t=",t
                            hits.append(Hit(cl,t,-d,backward))
                    if n<=0:
                        (cl,d) = c.intersect(forward, t)
                        if cl:
#                            print "> cl=",cl,",d=",d,",t=",t
                            hits.append(Hit(cl,t,d,forward))

                # sort along the scan direction
                hits.sort(Hit.cmp)

                # remove duplicates (typically edges)
                i = 1
                while i < len(hits):
                    while i<len(hits) and abs(hits[i].d - hits[i-1].d)<epsilon:
                        del hits[i]
                    i += 1

                # find parts of scanline where model is below z-level
                i = 0
                while i < len(hits):
                    next = hits[i].cl

                    self.pa.append(prev)
                    self.pa.append(next)
                    i += 1

                    # find next hit cutter location that is below z-level
                    while i < len(hits):
                        prev = hits[i].cl
                        c.moveto(prev)
                        c.moveto(prev.sub(hits[i].dir.mul(epsilon)))
                        zmax = -INFINITE
                        for t in model.triangles():
                            if t.normal().z < 0: continue;
                            cl = c.drop(t)
                            if cl and cl.z > zmax and cl.z < INFINITE:
                                zmax = cl.z

                        i += 1

                        if zmax <= z+epsilon:
                            break

                if dx == 0:
                    x = maxx
                if dy == 0:
                    y = maxy

                next = Point(x,y,z)

                self.pa.append(prev)
                self.pa.append(next)

                if dx != 0:
                    x += dx
                else:
                    x = minx
                if dy != 0:
                    y += dy
                else:
                    y = miny

                self.pa.end_scanline()

            self.pa.end_direction()
            self.pa.finish()

            paths += self.pa.paths
            z -= dz

        return paths
