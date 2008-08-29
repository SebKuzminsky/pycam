
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
        self.points.append(p)

    def reverse(self):
        self.points.reverse()
