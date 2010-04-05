from pycam.Geometry import *

def _check_colinearity(p1, p2, p3):
    v1 = p2.sub(p1)
    v2 = p3.sub(p2)
    v1.normalize()
    v2.normalize()
    # compare if the normalized distances between p1-p2 and p2-p3 are equal
    return v1 == v2

class PathAccumulator:
    def __init__(self, zigzag=False):
        self.paths = []
        self.curr_path = None
        self.zigzag = zigzag

    def append(self, p):
        if self.curr_path == None:
            self.curr_path = Path()
        if (len(self.curr_path.points) >= 2) and \
                (_check_colinearity(self.curr_path.points[-2], self.curr_path.points[-1], p)):
            # remove the previous point since it is in line with its
            # predecessor and the new point
            self.curr_path.points.pop()
        self.curr_path.append(p)

    def new_direction(self, dir):
        self.scanline = 0

    def end_direction(self):
        pass

    def new_scanline(self):
        self.scanline += 1
        if self.curr_path:
            print "ERROR: curr_path expected to be empty"
            self.curr_path = None

    def end_scanline(self):
        if self.curr_path:
            if self.zigzag and (self.scanline%2 == 0):
                self.curr_path.reverse()
            self.paths.append(self.curr_path)
            self.curr_path = None

    def finish(self):
        pass
