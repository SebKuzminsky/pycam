from gcode import gcode

# simplistic GCode exporter
# does each run, and moves the tool to the safetyheight in between

class SimpleGCodeExporter:

    def __init__(self, filename, unit, startx, starty, startz, feedrate, speed, safety_height=None, tool_id=1):
        self.file = file(filename,"w")
        if unit == "mm":
            self.file.write("G21\n")
        else:
            self.file.write("G20\n")
        self.gcode = gcode(startx, starty, startz, safetyheight=safety_height, tool_id=tool_id)
        gc = self.gcode
        self.file.write(gc.begin() + "\n")
        self.file.write("F" + str(feedrate) + "\n")
        self.file.write("S" + str(speed) + "\n")
        self.file.write(gc.safety() + "\n")

    def close(self):
        gc = self.gcode
        self.file.write(gc.safety() + "\n")
        self.file.write(gc.end() + "\n")
        self.file.close()

    def AddPath(self, path):
        gc = self.gcode
        point = path.points[0]
        self.file.write(gc.rapid(point.x, point.y, gc.safetyheight) + "\n")
        for point in path.points:
            self.file.write(gc.cut(point.x, point.y, point.z) + "\n")
        self.file.write(gc.rapid(point.x, point.y, gc.safetyheight) + "\n")

    def AddPathList(self, pathlist):
        for path in pathlist:
            self.AddPath(path)


def ExportPathList(filename, pathlist, unit, startx, starty, startz, feedrate, speed, safety_height=None):
    exporter = SimpleGCodeExporter(filename, unit, startx, starty, startz, feedrate, speed, safety_height)
    exporter.AddPathList(pathlist)
    exporter.close()

