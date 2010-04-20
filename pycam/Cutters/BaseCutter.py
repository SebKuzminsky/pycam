import pycam.Geometry

from pycam.Geometry import *
from pycam.Geometry.utils import *
from pycam.Geometry.utils import *
from math import sqrt

class BaseCutter:
    id = 0
    vertical = Point(0,0,-1)

    def __init__(self, radius, location=None, height=10):
        if location is None:
            location = Point(0, 0, 0)
        self.location = location
        self.id = BaseCutter.id
        BaseCutter.id += 1
        self.radius = radius
        self.radiussq = radius*radius
        self.height = height
        self.required_distance = 0
        self.distance_radius = self.radius
        self.distance_radiussq = self.distance_radius * self.distance_radius
        # self.minx, self.maxx, self.miny and self.maxy are defined as properties below
        self.shape = {}

    def _get_minx(self):
        return self.location.x - self.distance_radius
    minx = property(_get_minx)

    def _get_maxx(self):
        return self.location.x + self.distance_radius
    maxx = property(_get_maxx)

    def _get_miny(self):
        return self.location.y - self.distance_radius
    miny = property(_get_miny)

    def _get_maxy(self):
        return self.location.y + self.distance_radius
    maxy = property(_get_maxy)

    def __repr__(self):
        return "BaseCutter"

    def __cmp__(self, other):
        """ Compare Cutters by shape and size (ignoring the location)
        This function should be overridden by subclasses, if they describe
        cutters with a shape depending on more than just the radius.
        See the ToroidalCutter for an example.
        """
        if self.__class__ == other.__class__:
            return cmp(self.radius, other.radius)
        else:
            # just return a string comparison
            return cmp(str(self), str(other))

    def set_required_distance(self, value):
        if value >= 0:
            self.required_distance = value
            self.distance_radius = self.radius + self.get_required_distance()
            self.distance_radiussq = self.distance_radius * self.distance_radius

    def get_required_distance(self):
        return self.required_distance

    def moveto(self, location):
        self.location = location
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
        if sqr(c.x-self.location.x)+sqr(c.y-self.location.y)>(self.distance_radiussq+2*self.distance_radius*triangle.radius()+triangle.radiussq()):
            return None

        (cl,d)= self.intersect(BaseCutter.vertical, triangle)
        return cl

    def push(self, dx, dy, triangle):
        """ TODO: this function is never used - remove it? """
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

