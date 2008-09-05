import re

from pycam.Geometry import *

def ImportModel(filename):
    model = Model()
    f = file(filename,"r")
    solid = re.compile("\s*solid\s+(\w+)\s+.*")
    solid_AOI = re.compile("\s*solid\s+\"(\w+)\"; Produced by Art of Illusion.*")
    endsolid = re.compile("\s*endsolid\s+")
    facet = re.compile("\s*facet\s+")
    normal = re.compile("\s*facet\s+normal\s+(?P<x>[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?)\s+(?P<y>[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?)\s+(?P<z>[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?)\s+")
    endfacet = re.compile("\s*endfacet\s+")
    loop = re.compile("\s*outer\s+loop\s+")
    endloop = re.compile("\s*endloop\s+")
    vertex = re.compile("\s*vertex\s+(?P<x>[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?)\s+(?P<y>[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?)\s+(?P<z>[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?)\s+")

    model = Model()
    t = None
    p1 = None
    p2 = None
    p3 = None
    AOI = False
    for line in f:
        m = solid_AOI.match(line)
        if m:
            print "AOI"
            model.name = m.group(1)
            AOI = True
            continue
        m = solid.match(line)
        if m:
            model.name = m.group(1)
            continue
        m = facet.match(line)
        if m:
            m = normal.match(line)
            if m:
                if AOI:
                    n = Point(float(m.group('x')),-float(m.group('z')),float(m.group('y')))
                else:
                    n = Point(float(m.group('x')),float(m.group('y')),float(m.group('z')))
            continue
        m = loop.match(line)
        if m:
            continue
        m = vertex.match(line)
        if m:
            if AOI:
                p = Point(float(m.group('x')),-float(m.group('z')),float(m.group('y')))
            else:
                p = Point(float(m.group('x')),float(m.group('y')),float(m.group('z')))
            # TODO: check for duplicate points (using kdtree?)
            if p1 == None:
                p1 = p
            elif p2 == None:
                p2 = p
            elif p3 == None:
                p3 = p
            else:
                print "ERROR: more then 3 points in facet"
            continue
        m = endloop.match(line)
        if m:
            continue
        m = endfacet.match(line)
        if m:
            # make sure the points are in ClockWise order
            if n.dot(p3.sub(p1).cross(p2.sub(p1)))>0:
                t = Triangle(p1, p2, p3)
            else:
                t = Triangle(p1, p3, p2)
            t._normal = n
            n=p1=p2=p3=None
#            if t.normal().z < 0:
#                continue
            model.append(t)
            continue
        m = endsolid.match(line)
        if m:
            continue
    return model
    
