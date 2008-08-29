from pycam.Geometry import *

class PathAccumulator:
    def __init__(self, zigzag=False):
        self.paths = []
        self.curr_path = None
        self.zigzag = zigzag

    def append(self, p):
        if self.curr_path == None:
            self.curr_path = Path()
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
