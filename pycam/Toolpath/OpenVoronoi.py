# -*- coding: utf-8 -*-

import math

import openvoronoi

import pycam.Utils.log
import pycam.Geometry.Line
import pycam.Geometry.Polygon
import pycam.Geometry.Model
from pycam.Geometry.PointUtils import pdist_sq
from pycam.Geometry.utils import epsilon

_log = pycam.Utils.log.get_logger()


def _polygon2diagram(polygon, dia):
    """ add a polygon to an existing voronoi diagram
    """
    points = polygon.get_points()
    _log.info("Poly2dia points: %s" % str(points))
    if not points:
        return
    # TODO: somehow this causes a hang - see below for the step-by-step loop with log output
    #vpoints = [dia.addVertexSite(openvoronoi.Point(*p[:2])) for p in points]
    vpoints = []
    for p in points:
        ovp = openvoronoi.Point(*p[:2])
        _log.info("OVP: %s" % str(ovp))
        vpoints.append(dia.addVertexSite(ovp))
        _log.info("OVP added")
    _log.info("all vertices added to openvoronoi!")
    if polygon.is_closed:
        # recycle the first voronoi vertex ID
        vpoints.append(vpoints[0])
    before = None
    for current in vpoints:
        if not before is None:
            dia.addLineSite(before, current)
        before = current
    _log.info("all lines added to openvoronoi!")

def pocket_model(polygons, offset):
    maxx = max([poly.maxx for poly in polygons])
    maxy = max([poly.maxy for poly in polygons])
    minx = min([poly.minx for poly in polygons])
    miny = min([poly.miny for poly in polygons])
    radius = math.sqrt((maxx - minx) ** 2 + (maxy - miny) ** 2) / 1.8
    _log.info("Radius: %f" % radius)
    bin_size = int(math.ceil(math.sqrt(sum([len(poly.get_points()) for poly in polygons]))))
    _log.info("bin_size: %f" % bin_size)
    dia = openvoronoi.VoronoiDiagram(radius, bin_size)
    for polygon in polygons:
        _polygon2diagram(polygon, dia)
    model = pycam.Geometry.Model.ContourModel()
    before = None
    offset_dia = openvoronoi.Offset(dia.getGraph())
    for loop in offset_dia.offset(offset):
        lines = []
        for item in loop:
            if before is None:
                before = (item[0].x, item[0].y, 0.0)
            else:
                point, radius = item[:2]
                point = (point.x, point.y, 0.0)
                if len(item) == 2:
                    if radius == -1:
                        lines.append(pycam.Geometry.Line.Line(before, point))
                    else:
                        _log.warn("Unexpected voronoi condition: too few items (%s)" % str(item))
                else:
                    center, clock_wise = item[2:]
                    center = (center.x, center.y, 0.0)
                    direction_before = (before[0] - center[0], before[1] - center[1], 0.0)
                    direction_end = (point[0] - center[0], point[1] - center[1], 0.0)
                    angles = [180.0 * pycam.Geometry.get_angle_pi((1.0, 0.0, 0.0), (0, 0.0, 0.0),
                                    direction, (0.0, 0.0, 1.0), pi_factor=True)
                            for direction in (direction_before, direction_end)]
                    if clock_wise:
                        angles.reverse()
                    points = pycam.Geometry.get_points_of_arc(center, radius, angles[0], angles[1])
                    last_p = before
                    for p in points:
                        lines.append(pycam.Geometry.Line.Line(last_p, p))
                        last_p = p
                before = point
        for line in lines:
            if line.len > epsilon:
                model.append(line)
    return model.get_polygons()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        import pycam.Importers.DXFImporter as importer
        model = importer.import_model(sys.argv[1])
    else:
        model = pycam.Geometry.Model.ContourModel()
        # convert some points to a 2D model
        points = ((0.0, 0.0, 0.0), (0.5, 0.0, 0.0), (0.5, 0.5, 0.0), (0.0, 0.0, 0.0))
        print "original points: ", points
        before = None
        for p in points:
            if before:
                model.append(pycam.Geometry.Line.Line(before, p))
            before = p
    if len(sys.argv) > 2:
        offset = float(sys.argv[2])
    else:
        offset = 0.4
    # scale model within a range of -1..1
    maxdim = max(model.maxx - model.minx, model.maxy - model.miny)
    # stay well below sqrt(2)/2 in all directions
    model.scale(1.4 / maxdim)
    shift_x = - (model.minx + (model.maxx - model.minx) / 2.0)
    shift_y = - (model.miny + (model.maxy - model.miny) / 2.0)
    model.shift(shift_x, shift_y, 0.0)
    print "Model dimensions x: %f..%f" % (model.minx, model.maxx)
    print "Model dimensions y: %f..%f" % (model.miny, model.maxy)
    print pocket_model(model.get_polygons(), offset)

