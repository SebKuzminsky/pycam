class SVGExporter:

    def __init__(self, filename):
        self.file = file(filename,"w")
        self.file.write("""<?xml version='1.0'?>
<svg xmlns='http://www.w3.org/2000/svg' width='640' height='800'>
<g transform='translate(320,320) scale(50)' stroke-width='0.01' font-size='0.2'>
""")
        self._fill = 'none'
        self._stroke = 'black'

    def close(self):
        self.file.write("""</g>
</svg>
""")

        self.file.close()

    def stroke(self, stroke):
        self._stroke = stroke

    def fill(self, fill):
        self._fill = fill

    def AddDot(self, x, y):
        if x < -1000:
            x = -7
        if y < -1000:
            y = -7
        l = "<circle fill='" + self._fill +"'" + (" cx='%g'" % x) + (" cy='%g'" % -y) + " r='0.04'/>\n"
        self.file.write(l)

    def AddText(self, x, y, text):
        l = "<text fill='" + self._fill +"'" + (" x='%g'" % x) + (" y='%g'" % -y) + " dx='0.07'>" + text + "</text>\n"
        self.file.write(l)
        

    def AddLine(self, x1, y1, x2, y2):
        if y1 < -1000:
            y1 = -7
        if y2 < -1000:
            y2 = -7
        l = "<line fill='" + self._fill +"' stroke='" + self._stroke + "'" + (" x1='%g'" % x1) + (" y1='%g'" % -y1) + (" x2='%g'" % x2) + (" y2='%g'" % -y2) + " />\n"
        self.file.write(l)
        
    def AddPoint(self, p):
        AddDot(p.x, p.y)

    def AddPath(self, path):
        l = "<path fill='" + self._fill +"' stroke='" + self._stroke + "' d='"
        for i in range(0, len(path.points)):
            p = path.points[i]
            if i==0:
                l += "M "
            else:
                l += " L "
            l += "%g %g" % (p.x, -p.y-5)
        l += "'/>\n"
        self.file.write(l)

    def AddPathList(self, pathlist):
        for path in pathlist:
            self.AddPath(path)
