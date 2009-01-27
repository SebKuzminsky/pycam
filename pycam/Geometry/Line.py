import math


class Line:
    id=0
    def __init__(self,p1,p2):
        self.id = Line.id
        Line.id += 1
        self.p1 = p1
        self.p2 = p2

    def __repr__(self):
        return "Line<%g,%g,%g>-<%g,%g,%g>" % (self.p1.x,self.p1.y,self.p1.z,
                                              self.p2.x,self.p2.y,self.p2.z)

    def dir(self):
        if not hasattr(self,"_dir"):
            self._dir = self.p2.sub(self.p1)
            self._dir.normalize()
        return self._dir

    def len(self):
        if not hasattr(self,"_len"):
            self._len = self.p2.sub(self.p1).norm()
        return self._len

    def point(self, l):
        return self.p1.add(self.dir().mul(l*self.len()))

    def closest_point(self, p):
        v = self.dir()
        l = self.p1.dot(v)-p.dot(v)
        return self.p1.sub(v.mul(l))

    def dist_to_point_sq(self, p):
        return p.sub(self.closest_point(p)).normsq()

    def dist_to_point(self, p):
        return sqrt(self.dist_to_point_sq(p))
