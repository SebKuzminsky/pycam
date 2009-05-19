
import math

from Point import *
from Line import *
from Triangle import *
from kdtree import *


class PointKdtree(kdtree):
    def __init__(self, points=[],cutoff=5, cutoff_distance=0.5, tolerance=0.001):
        self._n = None
        self.tolerance=tolerance
        nodes = []
        for p in points:
            n = Node();
            n.point = p
            n.bound = []
            n.bound.append(p.x)
            n.bound.append(p.y)
            n.bound.append(p.z)
            nodes.append(n)
        kdtree.__init__(self, nodes, cutoff, cutoff_distance)

    def dist(self, n1, n2):
        dx = n1.bound[0]-n2.bound[0]
        dy = n1.bound[1]-n2.bound[1]
        dz = n1.bound[2]-n2.bound[2]
        return dx*dx+dy*dy+dz*dz

    def Point(self, x, y, z):
        #return Point(x,y,z)
        if self._n:
            n = self._n
        else:
            n = Node();
        n.bound = []
        n.bound.append(x)
        n.bound.append(y)
        n.bound.append(z)
        (nn,dist) = self.nearest_neighbor(n, self.dist)
        if nn and dist<self.tolerance:
            self._n = n
            return nn.p
        else:
            n.p = Point(x,y,z)
            self._n = None
            self.insert(n)
            return n.p


