# -*- coding: utf-8 -*-
"""
$Id$

Copyright 2009 Lode Leroy

This file is part of PyCAM.

PyCAM is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

PyCAM is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with PyCAM.  If not, see <http://www.gnu.org/licenses/>.
"""

# Inkscape uses a fixed resolution of 90 dpi
SVG_OUTPUT_DPI = 90


class SVGExporter:

    def __init__(self, output, unit="mm"):
        if isinstance(output, basestring):
            # a filename was given
            self.output = file(filename,"w")
        else:
            # a stream was given
            self.output = output
        if unit == "mm":
            dots_per_px = SVG_OUTPUT_DPI / 25.4
        else:
            dots_per_px = SVG_OUTPUT_DPI
        self.output.write("""<?xml version='1.0'?>
<svg xmlns='http://www.w3.org/2000/svg' width='640' height='800'>
<g transform='scale(%f)' stroke-width='0.01' font-size='0.2'>
""" % dots_per_px)
        self._fill = 'none'
        self._stroke = 'black'

    def close(self, close_stream=True):
        self.output.write("""</g>
</svg>
""")
        if close_stream:
            self.output.close()

    def stroke(self, stroke):
        self._stroke = stroke

    def fill(self, fill):
        self._fill = fill

    def AddDot(self, x, y):
        if x < -1000:
            x = -7
        if y < -1000:
            y = -7
        l = "<circle fill='" + self._fill +"'" + (" cx='%g'" % x) \
                + (" cy='%g'" % -y) + " r='0.04'/>\n"
        self.output.write(l)

    def AddText(self, x, y, text):
        l = "<text fill='" + self._fill +"'" + (" x='%g'" % x) \
                + (" y='%g'" % -y) + " dx='0.07'>" + text + "</text>\n"
        self.output.write(l)
        

    def AddLine(self, x1, y1, x2, y2):
        if y1 < -1000:
            y1 = -7
        if y2 < -1000:
            y2 = -7
        l = "<line fill='" + self._fill +"' stroke='" + self._stroke + "'" \
                + (" x1='%g'" % x1) + (" y1='%g'" % -y1) + (" x2='%g'" % x2) \
                + (" y2='%g'" % -y2) + " />\n"
        self.output.write(l)
        
    def AddPoint(self, p):
        self.AddDot(p.x, p.y)

    def AddPath(self, path):
        self.AddLines(path.points)
    
    def AddLines(self, points):
        l = "<path fill='" + self._fill +"' stroke='" + self._stroke + "' d='"
        for i in range(0, len(points)):
            p = points[i]
            if i == 0:
                l += "M "
            else:
                l += " L "
            l += "%g %g" % (p.x, -p.y-5)
        l += "'/>\n"
        self.output.write(l)

    def AddPathList(self, pathlist):
        for path in pathlist:
            self.AddPath(path)


#TODO: we need to create a unified "Exporter" interface and base class
class SVGExporterContourModel(object):

    def __init__(self, model, comment=None, unit="mm"):
        self.model = model
        self.unit = unit

    def write(self, stream):
        writer = SVGExporter(stream, unit=self.unit)
        for polygon in self.model.get_polygons():
            points = polygon.get_points()
            if polygon.is_closed:
                points.append(points[0])
            writer.AddLines(points)
        writer.close(close_stream=False)

