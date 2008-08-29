
import math

from Point import *
from Line import *
from Triangle import *
from kdtree import *

def BuildKdtree2d(triangles, cutoff=3, cutoff_distance=1.0):
    nodes = []
    for t in triangles:
        n = Node();
        n.triangle = t
        n.bound = []
        n.bound.append(min(min(t.p1.x,t.p2.x),t.p3.x))
        n.bound.append(min(min(t.p1.y,t.p2.y),t.p3.y))
        n.bound.append(max(max(t.p1.x,t.p2.x),t.p3.x))
        n.bound.append(max(max(t.p1.y,t.p2.y),t.p3.y))
        nodes.append(n)
    return kd_tree(nodes, cutoff, cutoff_distance)

tests = 0
hits = 0
overlaptest=True
mged = ""

def ResetKdtree2dStats(overlap=True):
    global tests, hits, overlaptest
    hits = 0
    tests = 0
    overlaptest = overlap
    mged = ""

def GetKdtree2dStats():
    global tests, hits
    return (hits, tests)


def SearchKdtree2d(kdtree, minx, maxx, miny, maxy):
    if kdtree.bucket:
        triangles = []
        for n in kdtree.nodes:
            global tests, hits, overlaptest
            tests += 1
            if not overlaptest:
#                print "not testing overlap"
                triangles.append(n.triangle)
                hits += 1
            else:
                if not (n.bound[0]>maxx
                        or n.bound[1]>maxy
                        or n.bound[2]<minx
                        or n.bound[3]<miny):
                    triangles.append(n.triangle)
                    hits += 1
        return triangles
    else:
#        return SearchKdtree2d(kdtree.lo, minx, maxx, miny, maxy)+SearchKdtree2d(kdtree.hi, minx, maxx, miny, maxy)

        if kdtree.cutdim==0:
            if maxx<kdtree.minval:
                return []
            elif maxx<=kdtree.cutval:
                return SearchKdtree2d(kdtree.lo, minx, maxx, miny, maxy)
            else:
                return SearchKdtree2d(kdtree.lo, minx, maxx, miny, maxy)+SearchKdtree2d(kdtree.hi, minx, maxx, miny, maxy)
        elif kdtree.cutdim==1:
            if maxy<kdtree.minval:
                return []
            elif maxy<=kdtree.cutval:
                return SearchKdtree2d(kdtree.lo, minx, maxx, miny, maxy)
            else:
                return SearchKdtree2d(kdtree.lo, minx, maxx, miny, maxy)+SearchKdtree2d(kdtree.hi, minx, maxx, miny, maxy)
        elif kdtree.cutdim==2:
            if minx>kdtree.maxval:
                return []
            elif minx>kdtree.cutval:
                return SearchKdtree2d(kdtree.hi, minx, maxx, miny, maxy)
            else:
                return SearchKdtree2d(kdtree.lo, minx, maxx, miny, maxy)+SearchKdtree2d(kdtree.hi, minx, maxx, miny, maxy)
        elif kdtree.cutdim==3:
            if miny>kdtree.maxval:
                return []
            elif miny>kdtree.cutval:
                return SearchKdtree2d(kdtree.hi, minx, maxx, miny, maxy)
            else:
                return SearchKdtree2d(kdtree.lo, minx, maxx, miny, maxy)+SearchKdtree2d(kdtree.hi, minx, maxx, miny, maxy)


def SearchKdtree2d_mged(kdtree, minx, maxx, miny, maxy, _minx, _maxx, _miny, _maxy):
    if kdtree.bucket:
        s = ""
        s += "in kdtree_%d arb8 " % kdtree.id
        s += " %f %f %f " % (_minx, _miny, 0)
        s += " %f %f %f " % (_maxx, _miny, 0)
        s += " %f %f %f " % (_maxx, _maxy, 0)
        s += " %f %f %f " % (_minx, _maxy, 0)
        s += " %f %f %f " % (_minx, _miny, 10)
        s += " %f %f %f " % (_maxx, _miny, 10)
        s += " %f %f %f " % (_maxx, _maxy, 10)
        s += " %f %f %f" % (_minx, _maxy, 10)
        s += "\n"
        return s
    else:
        if kdtree.cutdim==0:
            if maxx<kdtree.minval:
                return ""
            elif maxx<=kdtree.cutval:
                return SearchKdtree2d_mged(kdtree.lo, minx, maxx, miny, maxy, kdtree.minval, kdtree.cutval, _miny, _maxy)
            else:
                return SearchKdtree2d_mged(kdtree.lo, minx, maxx, miny, maxy, kdtree.minval, kdtree.cutval, _miny, _maxy)+SearchKdtree2d_mged(kdtree.hi, minx, maxx, miny, maxy, kdtree.cutval, kdtree.maxval, _miny, _maxy)
        elif kdtree.cutdim==1:
            if maxy<kdtree.minval:
                return ""
            elif maxy<=kdtree.cutval:
                return SearchKdtree2d_mged(kdtree.lo, minx, maxx, miny, maxy, _minx, _maxx, kdtree.minval, kdtree.cutval)
            else:
                return SearchKdtree2d_mged(kdtree.lo, minx, maxx, miny, maxy, _minx, _maxx, kdtree.minval, kdtree.cutval)+SearchKdtree2d_mged(kdtree.hi, minx, maxx, miny, maxy, _minx, _maxx, kdtree.cutval, kdtree.maxval)
        elif kdtree.cutdim==2:
            if minx>kdtree.maxval:
                return ""
            elif minx>kdtree.cutval:
                return SearchKdtree2d_mged(kdtree.hi, minx, maxx, miny, maxy, kdtree.minval, kdtree.cutval, _miny, _maxy)
            else:
                return SearchKdtree2d_mged(kdtree.lo, minx, maxx, miny, maxy, kdtree.minval, kdtree.cutval, _miny, _maxy)+SearchKdtree2d_mged(kdtree.hi, minx, maxx, miny, maxy, kdtree.cutval, kdtree.maxval, _miny, _maxy)
        elif kdtree.cutdim==3:
            if miny>kdtree.maxval:
                return ""
            elif miny>kdtree.cutval:
                return SearchKdtree2d_mged(kdtree.hi, minx, maxx, miny, maxy, _minx, _maxx, kdtree.minval, kdtree.cutval)
            else:
                return SearchKdtree2d_mged(kdtree.lo, minx, maxx, miny, maxy, _minx, _maxx, kdtree.minval, kdtree.cutval)+SearchKdtree2d_mged(kdtree.hi, minx, maxx, miny, maxy, _minx, _maxx, kdtree.cutval, kdtree.maxval)
