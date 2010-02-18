from pycam.Geometry import *
from pycam.Geometry.PolygonExtractor import *

class ContourCutter:
    def __init__(self):
        self.paths = []
        self.curr_path = None
        self.scanline = None
        self.pe = None
        self.points = []

    def append(self, p):
        self.points.append(p)

    def new_direction(self, dir):
        if self.pe == None:
            self.pe = PolygonExtractor(PolygonExtractor.CONTOUR)

        self.pe.new_direction(dir)

    def end_direction(self):
        self.pe.end_direction()

    def new_scanline(self):
        self.pe.new_scanline()
        self.points = []

    def end_scanline(self):
        for i in range(1, len(self.points)-1):
            self.pe.append(self.points[i])
        self.pe.end_scanline()

    def finish(self):
        self.pe.finish()
        if self.pe.merge_path_list:
            self.paths = self.pe.merge_path_list
            for p in self.paths:
                p.append(p.points[0])
        else:
            if self.pe.hor_path_list:
                self.paths = self.pe.hor_path_list
            else:
                self.paths = self.pe.ver_path_list
            if self.paths:
                for p in self.paths:
                    p.append(p.points[0])
        self.pe = None

