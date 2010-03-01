from gcode import gcode

# simplistic GCode exporter
# does each run, and moves the tool to the safetyheight in between

class SimpleGCodeExporter:

    def __init__(self, destination, unit, startx, starty, startz, feedrate,
            speed, safety_height=None, tool_id=1, finish_program=False):
        if isinstance(destination, basestring):
            # open the file
            self.destination = file(destination,"w")
            self._close_stream_on_exit = True
        else:
            # assume that "destination" is something like a StringIO instance
            # or an open file
            self.destination = destination
            # don't close the stream if we did not open it on our own
            self._close_stream_on_exit = False
        if unit == "mm":
            self.destination.write("G21\n")
        else:
            self.destination.write("G20\n")
        self.gcode = gcode(startx, starty, startz, safetyheight=safety_height, tool_id=tool_id)
        gc = self.gcode
        self._finish_program_on_exit = finish_program
        self.destination.write(gc.begin() + "\n")
        self.destination.write("F" + str(feedrate) + "\n")
        self.destination.write("S" + str(speed) + "\n")
        self.destination.write(gc.safety() + "\n")

    def close(self):
        gc = self.gcode
        self.destination.write(gc.safety() + "\n")
        if self._finish_program_on_exit:
            self.destination.write(gc.end() + "\n")
        if self._close_stream_on_exit:
            self.destination.close()

    def AddPath(self, path):
        gc = self.gcode
        point = path.points[0]
        self.destination.write(gc.rapid(point.x, point.y, gc.safetyheight) + "\n")
        for point in path.points:
            self.destination.write(gc.cut(point.x, point.y, point.z) + "\n")
        self.destination.write(gc.rapid(point.x, point.y, gc.safetyheight) + "\n")

    def AddPathList(self, pathlist):
        for path in pathlist:
            self.AddPath(path)


def ExportPathList(destination, pathlist, unit, startx, starty, startz,
        feedrate, speed, safety_height=None, tool_id=1, finish_program=False):
    exporter = SimpleGCodeExporter(destination, unit, startx, starty, startz,
            feedrate, speed, safety_height=safety_height, tool_id=tool_id,
            finish_program=finish_program)
    exporter.AddPathList(pathlist)
    exporter.close()

