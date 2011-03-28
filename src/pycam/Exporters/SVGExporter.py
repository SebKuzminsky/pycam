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

    def __init__(self, output, unit="mm", maxx=None, maxy=None):
        if isinstance(output, basestring):
            # a filename was given
            self.output = file(output,"w")
        else:
            # a stream was given
            self.output = output
        if unit == "mm":
            dots_per_px = SVG_OUTPUT_DPI / 25.4
        else:
            dots_per_px = SVG_OUTPUT_DPI
        if maxx is None:
            width = 640
        else:
            width = dots_per_px * maxx
            if width <= 0:
                width = 640
        if maxy is None:
            height = 800
        else:
            height = dots_per_px * maxy
            if height <= 0:
                height = 800
        self.output.write("""<?xml version='1.0'?>
<svg xmlns='http://www.w3.org/2000/svg' width='%f' height='%f'>
<g transform='translate(0,%f) scale(%.10f)' stroke-width='0.05' font-size='0.2'>
""" % (width, height, height, dots_per_px))
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
        l = "<circle fill='" + self._fill +"'" + (" cx='%g'" % x) \
                + (" cy='%g'" % -y) + " r='0.04'/>\n"
        self.output.write(l)

    def AddText(self, x, y, text):
        l = "<text fill='" + self._fill +"'" + (" x='%g'" % x) \
                + (" y='%g'" % -y) + " dx='0.07'>" + text + "</text>\n"
        self.output.write(l)
        

    def AddLine(self, x1, y1, x2, y2):
        l = "<line fill='" + self._fill +"' stroke='" + self._stroke + "'" \
                + (" x1='%.8f'" % x1) + (" y1='%.8f'" % -y1) + (" x2='%.8f'" % x2) \
                + (" y2='%.8f'" % -y2) + " />\n"
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
            l += "%.8f %.8f" % (p.x, -p.y)
        l += "'/>\n"
        self.output.write(l)

    def AddPathList(self, pathlist):
        for path in pathlist:
            self.AddPath(path)


#TODO: we need to create a unified "Exporter" interface and base class
class SVGExporterContourModel(object):

    def __init__(self, model, unit="mm", **kwargs):
        self.model = model
        self.unit = unit

    def write(self, stream):
        writer = SVGExporter(stream, unit=self.unit, maxx=self.model.maxx,
                maxy=self.model.maxy)
        for polygon in self.model.get_polygons():
            points = polygon.get_points()
            if polygon.is_closed:
                points.append(points[0])
            writer.AddLines(points)
        writer.close(close_stream=False)

