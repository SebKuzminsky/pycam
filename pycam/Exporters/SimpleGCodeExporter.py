from gcode import gcode

# simplistic GCode exporter
# does each run, and moves the tool to the safetyheight in between

class SimpleGCodeExporter:

    def __init__(self, filename, safetyheight=7.0, homeheight=7.0):
        self.file = file(filename,"w")
        self.gcode = gcode(homeheight, safetyheight)
        gc = self.gcode
        self.file.write(gc.begin()+"\n")
        self.file.write(gc.safety()+"\n")

    def close(self):
        gc = self.gcode
        self.file.write(gc.safety()+"\n")
        self.file.write(gc.end()+"\n")
        self.file.close()

    def AddPath(self, path):
        gc = self.gcode
        point = path.points[0]
        self.file.write(gc.rapid(point.x,point.y,gc.safetyheight)+"\n")
        for point in path.points:
            self.file.write(gc.cut(point.x,point.y,point.z)+"\n")
        self.file.write(gc.rapid(point.x,point.y,gc.safetyheight)+"\n")

    def AddPathList(self, pathlist):
        for path in pathlist:
            self.AddPath(path)


def ExportPathList(filename, pathlist, unit):
    exporter = SimpleGCodeExporter(filename)
    if unit == "mm":
        exporter.file.write("G20\n")
    else:
        exporter.file.write("G21\n")
    exporter.AddPathList(pathlist)
    exporter.close()

