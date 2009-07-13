import re
from struct import unpack 

from pycam.Geometry import *
from pycam.Geometry.PointKdtree import PointKdtree
from pycam.Geometry.TriangleKdtree import TriangleKdtree

vertices = 0
edges = 0
epsilon = 0.0001
kdtree = None

def UniqueVertex(x,y,z):
    global vertices
    if kdtree:
        last = Point.id
        p = kdtree.Point(x,y,z)
        if p.id == last:
#            print p
            vertices += 1
        return p
    else:
        vertices += 1
        return Point(x,y,z)

def UniqueEdge(p1, p2):
    global edges
    if hasattr(p1,"edges"):
        for e in p1.edges:
            if e.p1 == p1 and e.p2 == p2:
                return e
            if e.p2 == p1 and e.p1 == p2:
                return e
    edges += 1
    e = Line(p1,p2)
    if not hasattr(p1,"edges"):
        p1.edges = [e]
    else:
        p1.edges.append(e)
    if not hasattr(p2,"edges"):
        p2.edges = [e]
    else:
        p2.edges.append(e)
    return e


def ImportModel(filename, use_kdtree=True):
    global vertices, edges, kdtree
    vertices = 0
    edges = 0
    kdtree = None

    f = open(filename,"rb")
    header = f.read(80)
    binary = False
    if header[0:5] == "solid":
        binary = False
        f.seek(0)
    else:
        binary = True

    if use_kdtree:
        kdtree = PointKdtree([],3,1,epsilon)
    model = Model()

    t = None
    p1 = None
    p2 = None
    p3 = None

    if binary:
        numfacets = unpack("<I",f.read(4))[0]

        for i in range(1,numfacets): 
            a1 = unpack("<f",f.read(4))[0] 
            a2 = unpack("<f",f.read(4))[0] 
            a3 = unpack("<f",f.read(4))[0] 

            n = Point(float(a1),float(a2),float(a3))
            
            v11 = unpack("<f",f.read(4))[0] 
            v12 = unpack("<f",f.read(4))[0] 
            v13 = unpack("<f",f.read(4))[0] 

            p1 = UniqueVertex(float(v11),float(v12),float(v13))
            
            v21 = unpack("<f",f.read(4))[0] 
            v22 = unpack("<f",f.read(4))[0] 
            v23 = unpack("<f",f.read(4))[0] 

            p2 = UniqueVertex(float(v21),float(v22),float(v23))
            
            v31 = unpack("<f",f.read(4))[0] 
            v32 = unpack("<f",f.read(4))[0] 
            v33 = unpack("<f",f.read(4))[0] 
            
            p3 = UniqueVertex(float(v31),float(v32),float(v33))

            attribs = unpack("<H",f.read(2)) 
            
            if n.dot(p3.sub(p1).cross(p2.sub(p1)))>0:
                t = Triangle(p1, p2, p3, UniqueEdge(p1,p2), UniqueEdge(p2,p3), UniqueEdge(p3,p1))
            else:
                t = Triangle(p1, p3, p2, UniqueEdge(p1,p3), UniqueEdge(p3,p2), UniqueEdge(p2,p1))
            t._normal = n
            if t.normal().z < 0:
                continue
            model.append(t)
    else:
        AOI = False

        solid = re.compile("\s*solid\s+(\w+)\s+.*")
        solid_AOI = re.compile("\s*solid\s+\"([\w\-]+)\"; Produced by Art of Illusion.*")
        endsolid = re.compile("\s*endsolid\s+")
        facet = re.compile("\s*facet\s+")
        normal = re.compile("\s*facet\s+normal\s+(?P<x>[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?)\s+(?P<y>[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?)\s+(?P<z>[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?)\s+")
        endfacet = re.compile("\s*endfacet\s+")
        loop = re.compile("\s*outer\s+loop\s+")
        endloop = re.compile("\s*endloop\s+")
        vertex = re.compile("\s*vertex\s+(?P<x>[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?)\s+(?P<y>[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?)\s+(?P<z>[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?)\s+")

        for line in f:
            m = solid_AOI.match(line)
            if m:
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
                        n = Point(float(m.group('x')),float(m.group('z')),float(m.group('y')))
                    else:
                        n = Point(float(m.group('x')),float(m.group('y')),float(m.group('z')))
                continue
            m = loop.match(line)
            if m:
                continue
            m = vertex.match(line)
            if m:
                if AOI:
                    p = UniqueVertex(float(m.group('x')),float(m.group('z')),float(m.group('y')))
                else:
                    p = UniqueVertex(float(m.group('x')),float(m.group('y')),float(m.group('z')))
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
                    t = Triangle(p1, p2, p3, UniqueEdge(p1,p2), UniqueEdge(p2,p3), UniqueEdge(p3,p1))
                else:
                    t = Triangle(p1, p3, p2, UniqueEdge(p1,p3), UniqueEdge(p3,p2), UniqueEdge(p2,p1))
                t._normal = n
                n=p1=p2=p3=None
                if t.normal().z < 0:
                    continue
                model.append(t)
                continue
            m = endsolid.match(line)
            if m:
                continue

    if use_kdtree:
        model.p_kdtree = kdtree
        model.t_kdtree = TriangleKdtree(model.triangles())

    print "Imported STL model: ", vertices, "vertices,", edges, "edges,", len(model.triangles()),"triangles"
    vertices = 0
    edges = 0
    kdtree = None

    return model
    
