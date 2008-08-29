from Point import *

class Plane:
    id = 0
    def __init__(self, p, n):
        self.id = Plane.id
        Plane.id += 1
        self.p = p
        self.n = n

    def __repr__(self):
        return "Plane<%s,%s>" % (self.p,self.n)

    def to_mged(self):
        s = ""
        s += "in plane%d half"%(self.id)
        s += " %f %f %f"% (self.n.x, self.n.y, self.n.z)
        s += " %f "% (self.p.dot(self.n))
        s += "\n"
        return s

