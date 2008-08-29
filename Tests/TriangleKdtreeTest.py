#!/usr/bin/python
import sys
sys.path.insert(0,'.')

from pycam.Geometry.TriangleKdtree import *
from pycam.Geometry.Model import Model
from pycam.Importers.TestModel import TestModel

def comb_tomged(f, triangles, name, color):
    comb = ""
    for t in triangles:
        comb += " u triangle%d" % t.id
        if len(comb)>512:
            f.write("comb "+name+comb+"\n")
            comb = ""
    if len(comb)>0:
        f.write("comb "+name+comb+"\n")
    f.write("mater " + name + " del " + color + " 1\n")


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

print "# write mged"

f = file("test.txt","w")

f.write("in query.s arb8 %f %f %f %f %f %f %f %f %f %f %f %f %f %f %f %f %f %f %f %f %f %f %f %f\n" %
(minx, miny, 0, maxx, miny, 0, minx, maxy, 0, maxx, maxy, 0, minx, miny, 10, maxx, miny, 10, minx, maxy, 10, maxx, maxy, 10))
f.write("comb query.c u query.s\n")
f.write("mater query.c del 255 255 255 0\n")

if False:
    for t in model.triangles():
        f.write(t.to_mged())
    comb_tomged(f, model.triangles(), "model.c", "255 0 0")
else:
    for t in tests:
        f.write(t.to_mged())

comb_tomged(f, tests, "tests.c", "0 255 0")
comb_tomged(f, hits, "hits.c", "0 0 255")

#print kdtree
#f.write(kdtree.to_mged(-7,-7,7,7))
f.write(SearchKdtree2d_mged(kdtree, minx, maxx, miny, maxy,-7,-7,+7,+7))
f.close()
