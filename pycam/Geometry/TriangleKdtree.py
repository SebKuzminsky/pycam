
import math

from Point import *
from Line import *
from Triangle import *
from kdtree import *

overlaptest=True

def SearchKdtree2d(kdtree, minx, maxx, miny, maxy):
    if kdtree.bucket:
        triangles = []
        for n in kdtree.nodes:
            global tests, hits, overlaptest
            if not overlaptest:
                triangles.append(n.triangle)
            else:
                if not (n.bound[0]>maxx
                        or n.bound[1]<minx
                        or n.bound[2]>maxy
                        or n.bound[3]<miny):
                    triangles.append(n.triangle)
        return triangles
    else:
        if kdtree.cutdim==0:
            if maxx<kdtree.minval:
                return []
            elif maxx<kdtree.cutval:
                return SearchKdtree2d(kdtree.lo, minx, maxx, miny, maxy)
            else:
                return SearchKdtree2d(kdtree.lo, minx, maxx, miny, maxy)+SearchKdtree2d(kdtree.hi, minx, maxx, miny, maxy)
        elif kdtree.cutdim==1:
            if minx>kdtree.maxval:
                return []
            elif minx>kdtree.cutval:
                return SearchKdtree2d(kdtree.hi, minx, maxx, miny, maxy)
            else:
                return SearchKdtree2d(kdtree.lo, minx, maxx, miny, maxy)+SearchKdtree2d(kdtree.hi, minx, maxx, miny, maxy)
        elif kdtree.cutdim==2:
            if maxy<kdtree.minval:
                return []
            elif maxy<kdtree.cutval:
                return SearchKdtree2d(kdtree.lo, minx, maxx, miny, maxy)
            else:
                return SearchKdtree2d(kdtree.lo, minx, maxx, miny, maxy)+SearchKdtree2d(kdtree.hi, minx, maxx, miny, maxy)
        elif kdtree.cutdim==3:
            if miny>kdtree.maxval:
                return []
            elif miny>kdtree.cutval:
                return SearchKdtree2d(kdtree.hi, minx, maxx, miny, maxy)
            else:
                return SearchKdtree2d(kdtree.lo, minx, maxx, miny, maxy)+SearchKdtree2d(kdtree.hi, minx, maxx, miny, maxy)


class TriangleKdtree(kdtree):
    def __init__(self, triangles, cutoff=3, cutoff_distance=1.0):
        nodes = []
        for t in triangles:
            n = Node();
            n.triangle = t
            n.bound = []
            n.bound.append(min(min(t.p1.x,t.p2.x),t.p3.x))
            n.bound.append(max(max(t.p1.x,t.p2.x),t.p3.x))
            n.bound.append(min(min(t.p1.y,t.p2.y),t.p3.y))
            n.bound.append(max(max(t.p1.y,t.p2.y),t.p3.y))
            nodes.append(n)
        kdtree.__init__(self, nodes, cutoff, cutoff_distance)

    def Search(self, minx, maxx, miny, maxy):
        return SearchKdtree2d(self, minx, maxx, miny, maxy)
