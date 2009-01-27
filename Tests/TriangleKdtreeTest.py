#!/usr/bin/python
import sys
sys.path.insert(0,'.')

from pycam.Geometry.TriangleKdtree import *
from pycam.Geometry.Model import Model
from pycam.Importers.TestModel import TestModel

print "# get model"
testmodel = TestModel()
print "# subdivide"
model = testmodel.subdivide(5)
print "# build kdtree"
kdtree = BuildKdtree2d(model.triangles(), 2, 0.1)
#print "#kdtree=",kdtree

x = 2
y = 2
r = 0.1

minx = x-r
miny = y-r
maxx = x+r
maxy = y+r


print "# query kdtree"
ResetKdtree2dStats(False)
tests = SearchKdtree2d(kdtree, minx, maxx, miny, maxy)
print "# query kdtree"
ResetKdtree2dStats(True)
hits = SearchKdtree2d(kdtree, minx, maxx, miny, maxy)
#print "# hits=%d / tests=%d" % GetKdtree2dStats(), "/ triangles=%d" % len(model.triangles())
print "# hits=%d " % len(hits), "/ tests=%d" % len(tests), "/ triangles=%d" % len(model.triangles())

