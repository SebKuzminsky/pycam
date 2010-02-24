from pycam.PathProcessors import *
from pycam.Geometry import *
from pycam.Geometry.utils import *
import pycam.PathGenerators
from pycam.Exporters.SVGExporter import SVGExporter
import math

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

    def __init__(self, cutter, model, pathextractor=None, physics=None):
        self.cutter = cutter
        self.model = model
        self.pa = pathextractor
        self.physics = physics

    def GenerateToolPath(self, minx, maxx, miny, maxy, minz, maxz, dx, dy, dz, draw_callback=None):
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

        current_layer = 0
        num_of_layers = math.ceil((maxz - minz) / dz)

        if self.physics is None:
            GenerateToolPathSlice = self.GenerateToolPathSlice_triangles
        else:
            GenerateToolPathSlice = self.GenerateToolPathSlice_ode

        while z >= minz:
            # update the progress bar and check, if we should cancel the process
            if draw_callback and draw_callback(text="PushCutter: processing layer %d/%d" \
                        % (current_layer, num_of_layers),
                        percent=(100.0 * current_layer / num_of_layers)):
                # cancel immediately
                z = minz - 1

            if dy > 0:
                self.pa.new_direction(0)
                GenerateToolPathSlice(minx, maxx, miny, maxy, z, 0, dy, draw_callback)
                self.pa.end_direction()
            if dx > 0:
                self.pa.new_direction(1)
                GenerateToolPathSlice(minx, maxx, miny, maxy, z, dx, 0, draw_callback)
                self.pa.end_direction()
            self.pa.finish()

            if self.pa.paths:
                paths += self.pa.paths
            z -= dz

            if (z < minz) and (z + dz > minz):
                # never skip the outermost bounding limit - reduce the step size if required
                z = minz

            current_layer += 1

        if DEBUG_PUSHCUTTER2:
            self.svg.fill('none')
            self.svg.stroke('black')
            self.svg.AddPathList(paths)
        if hasattr(self,"svg"):
            self.svg.close()

        return paths

    def get_free_paths_ode(self, minx, maxx, miny, maxy, z, depth=8):
        """ Recursive function for splitting a line (usually along x or y) into
        small pieces to gather connected paths for the PushCutter.
        Strategy: check if the whole line is free (without collisions). Do a
        recursive call (for the first and second half), if there was a
        collision.

        Usually either minx/maxx or miny/maxy should be equal, unless you want
        to do a diagonal cut.
        @param minx: lower limit of x
        @type minx: float
        @param maxx: upper limit of x; should equal minx for a cut along the x axis
        @type maxx: float
        @param miny: lower limit of y
        @type miny: float
        @param maxy: upper limit of y; should equal miny for a cut along the y axis
        @type maxy: float
        @param z: the fixed z level
        @type z: float
        @param depth: number of splits to be calculated via recursive calls; the
            accuracy can be calculated as (maxx-minx)/(2^depth)
        @type depth: int
        @returns: a list of points that describe the tool path of the PushCutter;
            each pair of points defines a collision-free path
        @rtype: list(pycam.Geometry.Point.Point)
        """
        points = []
        # "resize" the drill along the while x/y range and check for a collision
        self.physics.extend_drill(maxx-minx, maxy-miny, 0.0)
        self.physics.set_drill_position((minx, miny, z))
        if self.physics.check_collision():
            # collision detected
            if depth > 0:
                middle_x = (minx + maxx)/2.0
                middle_y = (miny + maxy)/2.0
                group1 = self.get_free_paths_ode(minx, middle_x, miny, middle_y, z, depth-1)
                group2 = self.get_free_paths_ode(middle_x, maxx, middle_y, maxy, z, depth-1)
                if group1 and group2 and (group1[-1].x == group2[0].x) and (group1[-1].y == group2[0].y):
                    # the last couple of the first group ends where the first couple of the second group starts
                    # we will combine them into one couple
                    last = group1[-2]
                    first = group2[1]
                    combined = [last, first]
                    points.extend(group1[:-2])
                    points.extend(combined)
                    points.extend(group2[2:])
                else:
                    # the two groups are not connected - just add both
                    points.extend(group1)
                    points.extend(group2)
            else:
                # no points to be added
                pass
        else:
            # no collision - the line is free
            points.append(Point(minx, miny, z))
            points.append(Point(maxx, maxy, z))
        self.physics.reset_drill()
        return points

    def GenerateToolPathSlice_ode(self, minx, maxx, miny, maxy, z, dx, dy, draw_callback=None):
        """ only dx or (exclusive!) dy may be bigger than zero
        """
        # max_deviation_x = dx/accuracy
        accuracy = 20
        max_depth = 20
        x = minx
        y = miny

        # calculate the required number of steps in each direction
        if dx > 0:
            depth_x = math.log(accuracy * (maxx-minx) / dx) / math.log(2)
            depth_x = max(math.ceil(int(depth_x)), 4)
            depth_x = min(depth_x, max_depth)
        else:
            depth_y = math.log(accuracy * (maxy-miny) / dy) / math.log(2)
            depth_y = max(math.ceil(int(depth_y)), 4)
            depth_y = min(depth_y, max_depth)

        last_loop = False
        while (x <= maxx) and (y <= maxy):
            points = []
            self.pa.new_scanline()

            if dx > 0:
                points = self.get_free_paths_ode(x, x, miny, maxy, z, depth=depth_x)
            else:
                points = self.get_free_paths_ode(minx, maxx, y, y, z, depth=depth_y)

            for p in points:
                self.pa.append(p)
            if points:
                self.cutter.moveto(points[-1])
            if draw_callback:
                draw_callback()
            self.pa.end_scanline()

            if dx > 0:
                x += dx
                if (x > maxx) and not last_loop:
                    last_loop = True
                    x = maxx
            else:
                y += dy
                if (y > maxy) and not last_loop:
                    last_loop = True
                    y = maxy

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

    def GenerateToolPathSlice_triangles(self, minx, maxx, miny, maxy, z, dx, dy, draw_callback=None):
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

        last_loop = False
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
                    self.svg.AddDot(p.x, z)

                self.svg.fill('black')

            # find all hits along scan line
            hits = []
            prev = Point(x,y,z)
            hits.append(Hit(prev, None, 0, None))

            triangles = None
            if dx==0:
                triangles = model.triangles(minx-self.cutter.radius,y-self.cutter.radius,z,maxx+self.cutter.radius,y+self.cutter.radius,INFINITE)
            else:
                triangles = model.triangles(x-self.cutter.radius,miny-self.cutter.radius,z,x+self.cutter.radius,maxy+self.cutter.radius,INFINITE)

            for t in triangles:
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
                        hits.append(Hit(cl.add(backward_small),t,-d-epsilon,backward))
                        if DEBUG_PUSHCUTTER3: self.svg.AddDot(cl.x, cl.z)
                    else:
                        if DEBUG_PUSHCUTTER: print "< cl=",cl,",0",",t=",t.id
                if n<=0:
                    (cl,d) = c.intersect(forward, t)
                    if cl:
                        if DEBUG_PUSHCUTTER: print "> cl=",cl,",d=",d,",t=",t.id,",t.n=",t.normal(),",n=",n
                        hits.append(Hit(cl,t,d,forward))
                        hits.append(Hit(cl.add(forward_small),t,d+epsilon,forward))
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
                self.cutter.moveto(begin)
                self.cutter.moveto(end)
                if draw_callback:
                    draw_callback()
                if DEBUG_PUSHCUTTER3: 
                    self.svg.stroke("red' stroke-width='0.1")
                    self.svg.AddLine(begin.x, z-0.1, end.x, z-0.1)

            if dx != 0:
                x += dx
                # never skip the outermost bounding limit - reduce the step size if required
                if (x > maxx) and not last_loop:
                    x = maxx
                    last_loop = True
            else:
                x = minx
            if dy != 0:
                y += dy
                # never skip the outermost bounding limit - reduce the step size if required
                if (y > maxy) and not last_loop:
                    y = maxy
                    last_loop = True
            else:
                y = miny

            self.pa.end_scanline()
            if DEBUG_PUSHCUTTER: print 

        if DEBUG_PUSHCUTTER: print 
