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

