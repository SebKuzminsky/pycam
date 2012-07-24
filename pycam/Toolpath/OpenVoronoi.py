# -*- coding: utf-8 -*-

import math

import openvoronoi

import pycam.Utils.log
import pycam.Geometry.Line
import pycam.Geometry.Polygon
import pycam.Geometry.Model
from pycam.Geometry.PointUtils import pdist_sq

_log = pycam.Utils.log.get_logger()


def _polygon2diagram(polygon, dia):
    """ add a polygon to an existing voronoi diagram
    """
    points = list(polygon.get_points())
    if not points:
        return
    if polygon.is_closed:
        # the last and the first point are identical for closed polygons
        points.pop(-1)
    vpoints = [dia.addVertexSite(openvoronoi.Point(*p[:2])) for p in points]
    if polygon.is_closed:
        # recycle the first voronoi vertex ID
        vpoints.append(vpoints[0])
    before = None
    for current in vpoints:
        if before:
            dia.addLineSite(before, current)
        before = current

def pocket_model(polygons, offset):
    maxx = max([poly.maxx for poly in polygons])
    maxy = max([poly.maxy for poly in polygons])
    minx = min([poly.minx for poly in polygons])
    miny = min([poly.miny for poly in polygons])
    radius = max(maxx - minx, maxy - miny) / 1.8
    bin_size = sum([len(poly.get_points()) for poly in polygons])
    dia = openvoronoi.VoronoiDiagram(radius, int(math.ceil(math.sqrt(bin_size))))
    #dia.setEdgeOffset(offset)
    for polygon in polygons:
        _polygon2diagram(polygon, dia)
    dia.check()
    offset_dia = openvoronoi.Offset(dia.getGraph())
    #polygons = []
    model = pycam.Geometry.Model.ContourModel()
    before = None
    for loop in offset_dia.offset(offset):
        #polygon = pycam.Geometry.Polygon.Polygon()
        for item in loop:
            if before is None:
                before = (item[0].x, item[0].y, 0.0)
            else:
                point, radius, center, clock_wise = item
                point = (point.x, point.y, 0.0)
                center = (center.x, center.y, 0.0)
                if radius == -1:
                    model.append(pycam.Geometry.Line.Line(before, point))
                else:
                    direction_before = (before[0] - center[0], before[1] - center[1], 0)
                    direction_end = (point[0] - center[0], point[1] - center[1], 0)
                    angles = [180 * pycam.Geometry.get_angle_pi((1, 0, 0), (0, 0, 0),
                                    direction, (0, 0, 1), pi_factor=True)
                            for direction in (direction_before, direction_end)]
                    if not clock_wise:
                        angles.reverse()
                    points = pycam.Geometry.get_points_of_arc(center, radius, angles[0], angles[1], cords=64)
                    points.pop(0)
                    last_p = None
                    for p in points:
                        if last_p:
                            model.append(pycam.Geometry.Line.Line(last_p, p))
                        last_p = p
                before = point
        #polygons.append(polygon)
    return model.get_polygons()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        import pycam.Importers.DXFImporter as importer
        model = importer.import_model(sys.argv[1])
    else:
        model = pycam.Geometry.Model.ContourModel()
        # convert some points to a 2D model
        points = ((0.0, 0.0, 0.0), (10.0, 0.0, 0.0), (10.0, 10.0, 0.0), (0.0, 0.0, 0.0))
        before = None
        for p in points:
            if before:
                model.append(pycam.Geometry.Line.Line(before, p))
            before = p
    if len(sys.argv) > 2:
        offset = float(sys.argv[2])
    else:
        offset = 1.0
    print pocket_model(model.get_polygons(), offset)

