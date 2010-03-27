""" the points of a path are only used for describing coordinates. Thus we
don't really need complete "Point" instances that consume a lot of memory.
Since python 2.6 the "namedtuple" factory is available.
This reduces the memory consumption of a toolpath down to 1/3.
"""
try:
    # this works for python 2.6 or above (saves memory)
    from collections import namedtuple
    tuple_point = collections.namedtuple("TuplePoint", "x y z")
    get_point_object = lambda point: tuple_point(point.x, point.y, point.z)
except ImportError:
    # dummy for python < v2.6 (consumes more memory)
    get_point_object = lambda point: point


class Path:
    id = 0
    def __init__(self):
        self.id = Path.id
        Path.id += 1
        self.top_join = None
        self.bot_join = None
        self.winding=0
        self.points = []

    def __repr__(self):
        s = ""
        s += "path %d: " % self.id
        first = True
        for p in self.points:
            if first:
                first = False
            else:
                s +="-"
            s += "%d(%g,%g,%g)" % (p.id, p.x, p.y, p.z)
        return s

    def append(self, p):
        self.points.append(get_point_object(p))

    def reverse(self):
        self.points.reverse()
