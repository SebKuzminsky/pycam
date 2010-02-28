import pycam.Geometry

from pycam.Geometry import *
from pycam.Geometry.utils import *
from pycam.Geometry.utils import *
from math import sqrt

class BaseCutter:
    id = 0
    vertical = Point(0,0,-1)

    def __init__(self, location, radius):
        self.location = location
        self.id = BaseCutter.id
        BaseCutter.id += 1
        self.radius = radius
        self.radiussq = radius*radius
        self.minx = location.x-radius
        self.maxx = location.x+radius
        self.miny = location.y-radius
        self.maxy = location.y+radius
        self.shape = {}

    def __repr__(self):
        return "BaseCutter"

    def __cmp__(self, other):
        """ Compare Cutters by shape and size (ignoring the location)
        This function should be overridden by subclasses, if they describe
        cutters with a shape depending on more than just the radius.
        See the ToroidalCutter for an example.
        """
        if isinstance(other, BaseCutter):
            return cmp(self.radius, other.radius)
        else:
            # just return a string comparison
            return cmp(str(self), str(other))

    def moveto(self, location):
        self.location = location
        self.minx = location.x-self.radius
        self.maxx = location.x+self.radius
        self.miny = location.y-self.radius
        self.maxy = location.y+self.radius
        for shape, set_pos_func in self.shape.values():
            set_pos_func(location.x, location.y, location.z)

    def intersect(self, direction, triangle):
        return (None, None, None, INFINITE)

    def drop(self, triangle):
        # check bounding box collision
        if self.minx > triangle.maxx():
            return None
        if self.maxx < triangle.minx():
            return None
        if self.miny > triangle.maxy():
            return None
        if self.maxy < triangle.miny():
            return None

        # check bounding circle collision
        c = triangle.center()
        if sqr(c.x-self.location.x)+sqr(c.y-self.location.y)>(self.radiussq+2*self.radius*triangle.radius()+triangle.radiussq()):
            return None

        (cl,d)= self.intersect(BaseCutter.vertical, triangle)
        return cl

    def push(self, dx, dy, triangle):
        # check bounding box collision
        if dx == 0:
            if self.miny > triangle.maxy():
                return None
            if self.maxy < triangle.miny():
                return None
        if dy == 0:
            if self.minx > triangle.maxx():
                return None
            if self.maxx < triangle.minx():
                return None
        if triangle.maxz()<self.location.z:
            return None

        # check bounding sphere collision
        c = triangle.center()
        d = (c.x-self.location.x)*dy-(c.y-self.location.y)*dx
        t = self.radius + triangle.radius()
        if d < -t or d > t:
            return None

        (cl,d)= self.intersect(Point(dx,dy,0), triangle)
        return cl

