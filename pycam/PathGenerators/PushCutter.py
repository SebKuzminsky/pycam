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
        self.z = -INFINITE

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
            forward_small = Point(epsilon,0,0)
            backward_small = Point(-epsilon,0,0)
        elif dy == 0:
            forward = Point(0,1,0)
            backward = Point(0,-1,0)
            forward_small = Point(0,epsilon,0)
            backward_small = Point(0,-epsilon,0)

        x = minx
        y = miny
        
        line = 0
            
        while x<=maxx and y<=maxy:
            self.pa.new_scanline()
            if False:
                line += 1
                if line == 10:
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
                self.svg.fill('lightgreen')
                p = Point(minx, y, 10)
                for i in range(0,100):
                    p.x = minx + float(i)/100*float(maxx-minx)
                    self.svg.AddDot(p.x, zmax)

                self.svg.fill('black')

            # find all hits along scan line
            hits = []
            prev = Point(x,y,z)
            hits.append(Hit(prev, None, 0, None))

            for t in model.triangles():
                #if t.normal().z < 0: continue;
                # normals point outward... and we want to approach the model from the outside!
                n = t.normal().dot(forward)
                c.moveto(prev)
                if n>=0:
                    (cl,d) = c.intersect(backward, t)
                    if cl:
                        if DEBUG_PUSHCUTTER: print "< cl=",cl,",d=",-d,",t=",t.id,",t.n=",t.normal(),",n=",n
                        hits.append(Hit(cl,t,-d,backward))
                        hits.append(Hit(cl.sub(backward_small),t,-d+epsilon,backward))
                        if DEBUG_PUSHCUTTER3: self.svg.AddDot(cl.x, cl.z)
                    else:
                        if DEBUG_PUSHCUTTER: print "< cl=",cl,",0",",t=",t.id
                if n<=0:
                    (cl,d) = c.intersect(forward, t)
                    if cl:
                        if DEBUG_PUSHCUTTER: print "> cl=",cl,",d=",d,",t=",t.id,",t.n=",t.normal(),",n=",n
                        hits.append(Hit(cl,t,d,forward))
                        hits.append(Hit(cl.sub(forward_small),t,d-epsilon,forward))
                        if DEBUG_PUSHCUTTER3: self.svg.AddDot(cl.x, cl.z)
                    else:
                        if DEBUG_PUSHCUTTER: print "> cl=",cl,",0",",t=",t.id

            if dx == 0:
                x = maxx
            if dy == 0:
                y = maxy

            next = Point(x, y, z)
            hits.append(Hit(next, None, maxx-minx, None))


            # sort along the scan direction
            hits.sort(Hit.cmp)

            # remove duplicates (typically shared edges)
            i = 1
            while i < len(hits):
                while i<len(hits) and abs(hits[i].d - hits[i-1].d)<epsilon/2:
                    del hits[i]
                i += 1

            # determine height at each interesting point
            for h in hits:
                (zmax, tmax) = self.DropCutterTest(h.cl, model)
                h.z = zmax
                if DEBUG_PUSHCUTTER: print "@ cl=",h.cl,",d=",h.d,",z=",h.z
                if DEBUG_PUSHCUTTER3: self.svg.fill("blue"); self.svg.AddDot(h.cl.x, h.z)


            if DEBUG_PUSHCUTTER or DEBUG_PUSHCUTTER3:
                yt = -4
                i = 0
                for h in hits:
                    if DEBUG_PUSHCUTTER3:
                        self.svg.fill('black')
                        self.svg.stroke('gray')
                        self.svg.AddLine(h.cl.x, yt, h.cl.x, h.z)
                        self.svg.AddText(h.cl.x, yt, str(h.cl.x))
                        yt -= 0.5
                    i += 1



            # find first hit cutter location that is below z-level
            begin = hits[0].cl
            end = None
            for h in hits:
                if h.z >= z - epsilon/10:
                    if begin and end:
                        if DEBUG_PUSHCUTTER: 
                            print "C ", begin, " - ", end
                        self.pa.append(begin)
                        self.pa.append(end)
                        if DEBUG_PUSHCUTTER3: 
                            self.svg.stroke("red' stroke-width='0.1")
                            self.svg.AddLine(begin.x, z-0.1, end.x, z-0.1)
                    begin = None
                    end = None
                if h.z <= z + epsilon/10:
                    if not begin:
                        begin = h.cl
                    else:
                        end = h.cl
                
            if begin and end:
                if DEBUG_PUSHCUTTER: 
                    print "C ", begin, " - ", end
                self.pa.append(begin)
                self.pa.append(end)
                if DEBUG_PUSHCUTTER3: 
                    self.svg.stroke("red' stroke-width='0.1")
                    self.svg.AddLine(begin.x, z-0.1, end.x, z-0.1)

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
