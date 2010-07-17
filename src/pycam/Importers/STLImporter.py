# -*- coding: utf-8 -*-
"""
$Id$

Copyright 2008-2010 Lode Leroy
Copyright 2010 Lars Kruse <devel@sumpfralle.de>

This file is part of PyCAM.

PyCAM is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

PyCAM is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with PyCAM.  If not, see <http://www.gnu.org/licenses/>.
"""

from pycam.Geometry import Point, Line, Triangle
from pycam.Geometry.PointKdtree import PointKdtree
from pycam.Geometry.TriangleKdtree import TriangleKdtree
from pycam.Geometry.Model import Model
import pycam.Utils.log

from struct import unpack 
import re
import os

log = pycam.Utils.log.get_logger()


vertices = 0
edges = 0
epsilon = 0.0001
kdtree = None

def UniqueVertex(x, y, z):
    global vertices
    if kdtree:
        last = Point.id
        p = kdtree.Point(x, y, z)
        if p.id == last:
            vertices += 1
        return p
    else:
        vertices += 1
        return Point(x, y, z)

def UniqueEdge(p1, p2):
    global edges
    if hasattr(p1, "edges"):
        for e in p1.edges:
            if e.p1 == p1 and e.p2 == p2:
                return e
            if e.p2 == p1 and e.p1 == p2:
                return e
    edges += 1
    e = Line(p1, p2)
    if not hasattr(p1, "edges"):
        p1.edges = [e]
    else:
        p1.edges.append(e)
    if not hasattr(p2, "edges"):
        p2.edges = [e]
    else:
        p2.edges.append(e)
    return e


def ImportModel(filename, use_kdtree=True):
    global vertices, edges, kdtree
    vertices = 0
    edges = 0
    kdtree = None

    try:
        f = open(filename, "rb")
    except IOError, err_msg:
        log.error("STLImporter: Failed to read file (%s): %s" \
                % (filename, err_msg))
        return None
    # Read the first two lines of (potentially non-binary) input - they should
    # contain "solid" and "facet".
    header_lines = []
    while len(header_lines) < 2:
        current_line = f.readline(200)
        if len(current_line) == 0:
            # empty line (not even a line-feed) -> EOF
            log.error("STLImporter: No valid lines found in '%s'" % filename)
            return None
        # ignore comment lines
        # note: partial comments (starting within a line) are not handled
        if not current_line.startswith(";"):
            header_lines.append(current_line)
    header = "".join(header_lines)
    # read byte 80 to 83 - they contain the "numfacets" value in binary format
    f.seek(80)
    numfacets = unpack("<I", f.read(4))[0]
    binary = False

    if os.path.getsize(filename) == (84 + 50*numfacets):
        binary = True
    elif header.find("solid")>=0 and header.find("facet")>=0:
        binary = False
        f.seek(0)
    else:
        log.error("STLImporter: STL binary/ascii detection failed")
        return None

    if use_kdtree:
        kdtree = PointKdtree([], 3, 1, epsilon)
    model = Model(use_kdtree)

    t = None
    p1 = None
    p2 = None
    p3 = None

    if binary:
        for i in range(1, numfacets + 1): 
            a1 = unpack("<f", f.read(4))[0] 
            a2 = unpack("<f", f.read(4))[0] 
            a3 = unpack("<f", f.read(4))[0] 

            n = Point(float(a1), float(a2), float(a3))
            
            v11 = unpack("<f", f.read(4))[0] 
            v12 = unpack("<f", f.read(4))[0] 
            v13 = unpack("<f", f.read(4))[0] 

            p1 = UniqueVertex(float(v11), float(v12), float(v13))
            
            v21 = unpack("<f", f.read(4))[0] 
            v22 = unpack("<f", f.read(4))[0] 
            v23 = unpack("<f", f.read(4))[0] 

            p2 = UniqueVertex(float(v21), float(v22), float(v23))
            
            v31 = unpack("<f", f.read(4))[0] 
            v32 = unpack("<f", f.read(4))[0] 
            v33 = unpack("<f", f.read(4))[0] 
            
            p3 = UniqueVertex(float(v31), float(v32), float(v33))

            # not used
            attribs = unpack("<H", f.read(2)) 
            
            dotcross = n.dot(p3.sub(p1).cross(p2.sub(p1)))
            if a1 == a2 == a3 == 0:
                dotcross = p3.sub(p1).cross(p2.sub(p1)).z
                n = None

            if dotcross > 0:
                t = Triangle(p1, p2, p3, UniqueEdge(p1, p2), UniqueEdge(p2, p3),
                        UniqueEdge(p3, p1))
            elif dotcross < 0:
                t = Triangle(p1, p3, p2, UniqueEdge(p1, p3), UniqueEdge(p3, p2),
                        UniqueEdge(p2, p1))
            else:
                # the three points are in a line - or two points are identical
                # usually this is caused by points, that are too close together
                # check the tolerance value in pycam/Geometry/PointKdtree.py
                log.warn("Skipping invalid triangle: %s / %s / %s" \
                        % (p1, p2, p3) + " (maybe the resolution of the model" \
                        + " is too high?)")
                continue
            if n:
                t._normal = n

            model.append(t)
    else:
        solid = re.compile(r"\s*solid\s+(\w+)\s+.*")
        endsolid = re.compile(r"\s*endsolid\s*")
        facet = re.compile(r"\s*facet\s*")
        normal = re.compile(r"\s*facet\s+normal" \
                + r"\s+(?P<x>[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?)" \
                + r"\s+(?P<y>[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?)" \
                + r"\s+(?P<z>[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?)\s+")
        endfacet = re.compile(r"\s*endfacet\s+")
        loop = re.compile(r"\s*outer\s+loop\s+")
        endloop = re.compile(r"\s*endloop\s+")
        vertex = re.compile(r"\s*vertex" \
                + r"\s+(?P<x>[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?)" \
                + r"\s+(?P<y>[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?)" \
                + r"\s+(?P<z>[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?)\s+")

        current_line = 0

        for line in f:
            current_line += 1
            m = solid.match(line)
            if m:
                model.name = m.group(1)
                continue

            m = facet.match(line)
            if m:
                m = normal.match(line)
                if m:
                    n = Point(float(m.group('x')), float(m.group('y')),
                            float(m.group('z')))
                else:
                    n = None
                continue
            m = loop.match(line)
            if m:
                continue
            m = vertex.match(line)
            if m:
                p = UniqueVertex(float(m.group('x')), float(m.group('y')),
                        float(m.group('z')))
                if p1 is None:
                    p1 = p
                elif p2 is None:
                    p2 = p
                elif p3 is None:
                    p3 = p
                else:
                    log.error("STLImporter: ERROR: more then 3 points in " \
                            + "facet (line %d)" % current_line)
                continue
            m = endloop.match(line)
            if m:
                continue
            m = endfacet.match(line)
            if m:
                if not n:
                    n = p3.sub(p1).cross(p2.sub(p1))
                    n.normalize()

                # make sure the points are in ClockWise order
                dotcross = n.dot(p3.sub(p1).cross(p2.sub(p1)))
                if dotcross > 0:
                    t = Triangle(p1, p2, p3, UniqueEdge(p1, p2),
                            UniqueEdge(p2, p3), UniqueEdge(p3, p1), n)
                elif dotcross < 0:
                    t = Triangle(p1, p3, p2, UniqueEdge(p1, p3),
                            UniqueEdge(p3, p2), UniqueEdge(p2, p1), n)
                else:
                    # The three points are in a line - or two points are
                    # identical. Usually this is caused by points, that are too
                    # close together. Check the tolerance value in
                    # pycam/Geometry/PointKdtree.py.
                    print "ERROR: skipping invalid triangle: %s / %s / %s" \
                            % (p1, p2, p3)
                    n, p1, p2, p3 = (None, None, None, None)
                    continue
                n, p1, p2, p3 = (None, None, None, None)
                model.append(t)
                continue
            m = endsolid.match(line)
            if m:
                continue

    log.info("Imported STL model: %d vertices, %d edges, %d triangles" \
            % (vertices, edges, len(model.triangles())))
    vertices = 0
    edges = 0
    kdtree = None

    return model
    
