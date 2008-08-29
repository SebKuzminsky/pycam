from pycam.Geometry import *

class MGEDExporter:

    def __init__(self, filename):
        self.file = file(filename,"w")

    def close(self):
        self.file.close()

    def AddCutter(self, cutter):
        self.file.write(cutter.to_mged())

    def AddModel(self, model):
        self.file.write(model.to_mged())

    def AddPath(self, path):
        prev = path.points[0]
        for i in range(1, len(path.points)):
            next = path.points[i]
            self.file.write(Line(prev,next).to_mged())
            prev = next

    def AddPathList(self, pathlist):
        for path in pathlist:
            self.AddPath(path)
