#!/usr/bin/python
import sys
sys.path.insert(0,'.')

import math

from pycam.Geometry import *

if __name__ == "__main__":
    p1 = Point(1,0,0)
    p2 = Point(0,1,0)
    p3 = Point(0,0,1)

    print "p1=" + str(p1);
    print "p2=" + str(p2);
    print "p3=" + str(p3);

    print "p2-p1=" + str(p2.sub(p1))
    print "p3-p2=" + str(p3.sub(p2))
    print "p1-p3=" + str(p1.sub(p3))

    print "p2.p1=" + str(p2.dot(p1))
    print "p3.p2=" + str(p3.dot(p2))
    print "p1.p3=" + str(p1.dot(p3))

    print "p1xp2=" + str(p1.cross(p2))
    print "p2xp3=" + str(p2.cross(p3))
    print "p3xp1=" + str(p3.cross(p1))

    t = Triangle(p1,p2,p3)
    print t

    t.calc_circumcircle()
    print "circ(t) = %s@%s" % (t.radius,t.center())

    f = file("triangle0.txt","w")
    f.write(t.to_mged(sphere=True))
    f.close()

