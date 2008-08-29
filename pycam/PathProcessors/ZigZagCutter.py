from pycam.Geometry import *

class ZigZagCutter:
    def __init__(self):
        self.paths = []
        self.curr_path = None
        self.scanline = None

    def append(self, p):
        curr_path = None
        if self.curr_path == None:
            curr_path = Path()
            self.curr_path = curr_path
        else:
            curr_path = self.curr_path
            self.curr_path = None

        curr_path.append(p)

        if self.curr_path == None:
            if (self.scanline % 2) == 0:
                self.curr_scanline.append(curr_path)
            else:
                curr_path.reverse()
                self.curr_scanline.insert(0, curr_path)

    def new_direction(self, dir):
        self.scanline = 0

    def end_direction(self):
        pass

    def new_scanline(self):
        self.scanline += 1
        self.curr_scanline = []

    def end_scanline(self):
        self.paths += self.curr_scanline
        self.curr_scanline = None

    def finish(self):
        pass
