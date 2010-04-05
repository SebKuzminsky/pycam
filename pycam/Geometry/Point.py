import math

class Point:
    id=0

    def __init__(self,x,y,z):
        self.id = Point.id
        Point.id += 1
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)

    def __repr__(self):
        return "Point%d<%g,%g,%g>" % (self.id,self.x,self.y,self.z)

    def __cmp__(self, other):
        """ Two points are equal if all dimensions are identical.
        Otherwise the result is based on the individual x/y/z comparisons.
        """
        if self.__class__ == other.__class__:
            if (self.x == other.x) and (self.y == other.y) and (self.z == other.y):
                return 0
            elif self.x < other.y:
                return -1
            elif self.x > other.y:
                return 1
            elif self.y < other.y:
                return -1
            elif self.y > other.y:
                return 1
            elif self.z < other.z:
                return -1
            else:
                return 1
        else:
            return cmp(str(self), str(other))

    def mul(self, c):
        return Point(self.x*c,self.y*c,self.z*c)

    def div(self, c):
        return Point(self.x/c,self.y/c,self.z/c)

    def add(p1, p2):
        return Point(p1.x+p2.x,p1.y+p2.y,p1.z+p2.z)

    def sub(p1, p2):
        return Point(p1.x-p2.x,p1.y-p2.y,p1.z-p2.z)

    def dot(p1, p2):
        return p1.x*p2.x + p1.y*p2.y + p1.z*p2.z

    def cross(p1, p2):
        return Point(p1.y*p2.z-p2.y*p1.z, p2.x*p1.z-p1.x*p2.z, p1.x*p2.y-p2.x*p1.y)

    def normsq(self):
        if not hasattr(self, "_normsq"):
            self._normsq = self.dot(self)
        return self._normsq

    def norm(self):
        if not hasattr(self, "_norm"):
            self._norm = math.sqrt(self.normsq())
        return self._norm

    def normalize(self):
        n = self.norm()
        if n != 0:
            self.x /= n
            self.y /= n
            self.z /= n
            self._norm = 1.0
            self._normsq = 1.0
        return self

