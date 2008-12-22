from gcode import gcode

# simplistic GCode exporter
# does each run, and moves the tool to the safetyheight in between

class SimpleGCodeExporter:

    def __init__(self, filename, unit, x, y, z, feedrate, speed):
        self.file = file(filename,"w")
        if unit == "mm":
            self.file.write("G21\n")
            z += 7.0
        else:
            self.file.write("G20\n")
            z += 0.25
        self.gcode = gcode(x,y,z)
        gc = self.gcode
        self.file.write(gc.begin()+"\n")
        self.file.write("F"+feedrate+"\n")
        self.file.write("S"+speed+"\n")
        self.file.write(gc.safety()+"\n")

    def close(self):
        gc = self.gcode
        self.file.write(gc.safety()+"\n")
        self.file.write(gc.end()+"\n")
        self.file.close()

    def AddPath(self, path):
        gc = self.gcode
        point = path.points[0]
#        self.file.write(gc.rapid(point.x,point.y,gc.safetyheight)+"\n")
        for point in path.points:
            self.file.write(gc.cut(point.x,point.y,point.z)+"\n")
#        self.file.write(gc.rapid(point.x,point.y,gc.safetyheight)+"\n")

    def AddPathList(self, pathlist):
        for path in pathlist:
            self.AddPath(path)


def ExportPathList(filename, pathlist, unit, x, y, z, feedrate, speed):
    exporter = SimpleGCodeExporter(filename, unit, x, y, z, feedrate, speed)
    exporter.AddPathList(pathlist)
    exporter.close()

