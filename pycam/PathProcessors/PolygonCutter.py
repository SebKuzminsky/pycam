from pycam.Geometry import *
from pycam.Geometry.PolygonExtractor import *

class PolygonCutter:
    def __init__(self):
        self.paths = []
        self.curr_path = None
        self.scanline = None
        self.pe = PolygonExtractor(PolygonExtractor.MONOTONE)

    def append(self, p):
        self.pe.append(p)

    def new_direction(self, dir):
        self.pe.new_direction(dir)

    def end_direction(self):
        self.pe.end_direction()

    def new_scanline(self):
        self.pe.new_scanline()

    def end_scanline(self):
        self.pe.end_scanline()

    def finish(self):
        self.pe.finish()
        paths = []
        for path in self.pe.hor_path_list:
            points = path.points
            for i in range(0, (len(points)+1)/2):
                p = Path()
                if i % 2 == 0:
                    p.append(points[i])
                    p.append(points[-i-1])
                else:
                    p.append(points[-i-1])
                    p.append(points[i])
                paths.append(p)
        self.paths = paths

