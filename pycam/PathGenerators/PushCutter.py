from pycam.PathProcessors import *
from pycam.Geometry import *
from pycam.Geometry.utils import *

from pycam.Exporters.SVGExporter import SVGExporter

DEBUG_PUSHCUTTER = False
DEBUG_PUSHCUTTER2 = False
DEBUG_PUSHCUTTER3 = False

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
        if dx != 0:
            self.pa.dx = dx
        else:
            self.pa.dx = dy

        if dy != 0:
            self.pa.dy = dy
        else:
            self.pa.dy = dx

        if DEBUG_PUSHCUTTER2 or DEBUG_PUSHCUTTER3:
            self.svg = SVGExporter("test.svg")

        z = maxz

        paths = []

        while z >= minz:
            if dy > 0:
                self.pa.new_direction(0)
                self.GenerateToolPathSlice(minx, maxx, miny, maxy, z, 0, dy)
                self.pa.end_direction()
            if dx > 0:
                self.pa.new_direction(1)
                self.GenerateToolPathSlice(minx, maxx, miny, maxy, z, dx, 0)
                self.pa.end_direction()
            self.pa.finish()

            if self.pa.paths:
                paths += self.pa.paths
            z -= dz

        if DEBUG_PUSHCUTTER2:
            self.svg.fill('none')
            self.svg.stroke('black')
            self.svg.AddPathList(paths)
        if hasattr(self,"svg"):
            self.svg.close()

        return paths

    def DropCutterTest(self, point, model):
        zmax = -INFINITE
        tmax = None
        c = self.cutter
        c.moveto(point)
        for t in model.triangles():
            if t.normal().z < 0: continue
            cl = c.drop(t)
            if cl and cl.z > zmax and cl.z < INFINITE:
                zmax = cl.z
                tmax = t
        return (zmax, tmax)

    def GenerateToolPathSlice(self, minx, maxx, miny, maxy, z, dx, dy):
        global DEBUG_PUSHCUTTER, DEBUG_PUSHCUTTER2, DEBUG_PUSHCUTTER3
        c = self.cutter
        model = self.model

        if dx==0:
            forward = Point(1,0,0)
            backward = Point(-1,0,0)
        elif dy == 0:
            forward = Point(0,1,0)
            backward = Point(0,-1,0)

        x = minx
        y = miny
        
        line = 0
            
        while x<=maxx and y<=maxy:
            self.pa.new_scanline()
            if False:
                line += 1
                if line == 13:
                    DEBUG_PUSHCUTTER=True
                    DEBUG_PUSHCUTTER2=True
                    DEBUG_PUSHCUTTER3=True
                    p = Path()
                    self.svg.stroke('orange')
                    p.append(Point(minx,y-0.05,z))
                    p.append(Point(maxx,y-0.05,z))
                    p.append(Point(maxx,y+0.05,z))
                    p.append(Point(minx,y+0.05,z))
                    p.append(Point(minx,y-0.05,z))
                    self.svg.AddPath(p)
                else:
                    DEBUG_PUSHCUTTER=False
                    DEBUG_PUSHCUTTER2=True
                    DEBUG_PUSHCUTTER3=False


            if DEBUG_PUSHCUTTER3:
                self.svg.stroke('gray')
                self.svg.AddLine(minx, z, maxx, z)
                self.svg.fill('lightgreen')
                p = Point(minx, y, 10)
                for i in range(0,100):
                    p.x = minx + float(i)/100*float(maxx-minx)
                    (zmax, tmax) = self.DropCutterTest(p, model)
                    if DEBUG_PUSHCUTTER: print "v cl=",p,",zmax=",zmax
                    self.svg.AddDot(p.x, zmax)

                self.svg.fill('black')

            # find all hits along scan line
            hits = []
            prev = Point(x,y,z)
            c.moveto(prev)

            for t in model.triangles():
                #if t.normal().z < 0: continue;
                # normals point outward... and we want to approach the model from the outside!
                n = t.normal().dot(forward)
                if n>=0:
                    (cl,d) = c.intersect(backward, t)
                    if cl:
                        #if DEBUG_PUSHCUTTER: print "< cl=",cl,",d=",-d,",t=",t
                        hits.append(Hit(cl,t,-d,backward))
                        if DEBUG_PUSHCUTTER3: self.svg.AddDot(cl.x, cl.z)
                if n<=0:
                    (cl,d) = c.intersect(forward, t)
                    if cl:
                        #if DEBUG_PUSHCUTTER: print "> cl=",cl,",d=",d,",t=",t
                        hits.append(Hit(cl,t,d,forward))
                        if DEBUG_PUSHCUTTER3: self.svg.AddDot(cl.x, cl.z)

            # sort along the scan direction
            hits.sort(Hit.cmp)

#            # remove duplicates (typically edges)
#            i = 1
#            while i < len(hits):
#                while i<len(hits) and abs(hits[i].d - hits[i-1].d)<epsilon:
#                    del hits[i]
#                i += 1

            if DEBUG_PUSHCUTTER or DEBUG_PUSHCUTTER3:
                for h in hits:
                    (zmax, tmax) = self.DropCutterTest(h.cl, model)
                    if DEBUG_PUSHCUTTER: print "  cl=",h.cl,",d=",h.d,",zmax=",zmax
                    if DEBUG_PUSHCUTTER3:
                        self.svg.stroke('gray')
                        self.svg.AddLine(h.cl.x, -1, h.cl.x, zmax)

            # find parts of scanline where model is below z-level
            i = 0
            while i < len(hits):

                # find next hit cutter location that is below z-level
                while i < len(hits):
                    (zmax, tmax) = self.DropCutterTest(prev, model)

                    if DEBUG_PUSHCUTTER: print "1", prev, "z=",zmax

                    if zmax <= z+epsilon:
                        break

                    if DEBUG_PUSHCUTTER3: 
                        self.svg.stroke('lightred')
                        self.svg.AddLine(prev.x, prev.z, prev.x, zmax)

                    prev = hits[i].cl
                    i += 1


                if DEBUG_PUSHCUTTER3:
                    self.svg.stroke('red')
                    self.svg.AddLine(prev.x, prev.z, prev.x, zmax)

                # find next hit cutter location that is above z-level
                while i < len(hits):
                    next = hits[i].cl
                    (zmax, tmax) = self.DropCutterTest(next, model)

                    if DEBUG_PUSHCUTTER: print "2", next, "z=",zmax

                    i += 1

                    if zmax >= z-epsilon:
                        break

                    if DEBUG_PUSHCUTTER3: 
                        self.svg.stroke('lightblue')
                        self.svg.AddLine(next.x, next.z, next.x, zmax)

                if DEBUG_PUSHCUTTER3: 
                    self.svg.stroke('blue')
                    self.svg.AddLine(next.x, next.z, next.x, zmax)

                if i < len(hits):
                    self.pa.append(prev)
                    self.pa.append(next)
                    if DEBUG_PUSHCUTTER: print "C ", prev, next, "z=",zmax
                    if DEBUG_PUSHCUTTER3: 
                        self.svg.stroke('red')
                        self.svg.AddLine(prev.x, z-0.1, next.x, z-0.1)

                    prev = hits[i].cl

            if dx == 0:
                x = maxx
            if dy == 0:
                y = maxy

            next = Point(x,y,z)
            (zmax, tmax) = self.DropCutterTest(next, model)
            if DEBUG_PUSHCUTTER: print "3 ", next, "z=",zmax

            if zmax <= z+epsilon:
                self.pa.append(prev)
                self.pa.append(next)
                if DEBUG_PUSHCUTTER: print "C ", prev, next, "z=",zmax
                if DEBUG_PUSHCUTTER3: 
                    self.svg.stroke('red')
                    self.svg.AddLine(prev.x, z-0.1, next.x, z-0.1)

            if dx != 0:
                x += dx
            else:
                x = minx
            if dy != 0:
                y += dy
            else:
                y = miny

            self.pa.end_scanline()
            if DEBUG_PUSHCUTTER: print 

        if DEBUG_PUSHCUTTER: print 
