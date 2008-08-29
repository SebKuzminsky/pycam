from pycam.Geometry import *

class SimpleCutter:
    def __init__(self):
        self.paths = []
        self.curr_path = None

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
            self.paths.append(curr_path)

    def new_direction(self, dir):
        pass

    def end_direction(self):
        pass

    def new_scanline(self):
        if self.curr_path:
            print "ERROR: curr_path expected to be empty"
            self.curr_path = None

    def end_scanline(self):
        if self.curr_path:
            print "ERROR: curr_path expected to be empty"
            self.curr_path = None

    def finish(self):
        pass
