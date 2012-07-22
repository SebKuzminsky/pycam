# -*- coding: utf-8 -*-

import copy

import area

import pycam.Utils.log
import pycam.Geometry.Line
import pycam.Geometry.Polygon
from pycam.Geometry.PointUtils import pdist_sq

_log = pycam.Utils.log.get_logger()


def _polygon2curve(polygon):
    curve = area.Curve()
    for pt in polygon.get_points():
        curve.append(area.Vertex(area.Point(pt[0], pt[1])))
    return curve


def _polygons2area(polygons):
    result = area.Area()
    for lg in polygons:
        result.append(_polygon2curve(lg))
    return result


def _pocket_model(polygons, offset):
    """Create pocketing path."""
    # libarea.Vertex Linetypes
    LINE = 0
    ARC_CCW = 1
    ARC_CW = -1
    return _pocket_area(_polygons2area(polygons), offset)


def vertex2lines(before, vt):
    import math
    end = (vt.p.x, vt.p.y, 0.0)
    if vt.type in (-1, 1):
        center = (vt.c.x, vt.c.y, 0.0)
        direction_before = (before[0] - center[0], before[1] - center[1], 0)
        direction_end = (end[0] - center[0], end[1] - center[1], 0)
        radius_before = math.sqrt(direction_before[0]**2 + direction_before[1]**2)
        radius_end = math.sqrt(direction_end[0]**2 + direction_end[1]**2)
        #assert radius_before == radius_end
        radius = 0.5 * (radius_before + radius_end)
        angles = [180 * pycam.Geometry.get_angle_pi((1, 0, 0), (0, 0, 0),
                        direction, (0, 0, 1), pi_factor=True)
                for direction in (direction_before, direction_end)]
        if vt.type == -1:
            angles.reverse()
        points = pycam.Geometry.get_points_of_arc(center, radius, *angles)
        # the first point should be the same as "before" - skip it
        if points:
            #assert points.pop(0) == before
            points.pop(0)
        result = []
        for p in points:
            if pdist_sq(before, p) > 0.0001:
                result.append(pycam.Geometry.Line.Line(before, p))
            before = p
        return result
    else:
        return [pycam.Geometry.Line.Line(before, end)]

def _pocket_area(a, offset):
    polygons = []
    #a.m_round_corners_factor = params.m_round_corner_factor
    a.m_round_corners_factor = 1.0
    arealist = _get_inner_polygons(a, offset)
    #if params.m_from_center:
    #    arealist.reverse()
    arealist.reverse()
    
    vertex2point = lambda vt: (vt.p.x, vt.p.y, 0.0)
    # add all vertices from all areas to the polygons list
    import pycam.Geometry.Model
    model = pycam.Geometry.Model.ContourModel()
    for a in arealist:
        for c in a.getCurves():
            vertices = c.getVertices()
            if not vertices:
                continue
            p_previous = None
            for current in vertices:
                # from 2D to 3D with Z=0
                if p_previous:
                    lines = vertex2lines(p_previous, current)
                    for line in lines:
                        model.append(line)
                p_previous = vertex2point(current)
    return model.get_polygons()


def _get_area_copy(original):
    # TODO: Curve deepcopy not yet fully covered, thus Area neither as it depends on it
    #a_offset = copy.deepcopy(a1)
    result = area.Area()
    for c in original.getCurves():
        copy_curve = area.Curve()
        for vt in c.getVertices():
            copy_curve.append(copy.deepcopy(vt))
        result.append(copy_curve)
    return result


def _get_inner_polygons(a1, step_over):
    if a1.num_curves == 0:
        return []
    areas = []
    # copy Area instance
    a_offset = _get_area_copy(a1)
    a_offset.Offset(step_over)
    for curve in a_offset.getCurves():
        a2 = area.Area()
        a2.append(curve)
        areas.append(a2)
        areas.extend(_get_inner_polygons(a2, step_over))
    return areas

        
class PocketParams:
    """Settings used for pocketing toolpath generation."""
    m_from_center = True
    m_round_corner_factor = 1.0
    m_material_allowance = 0.0
    m_step_over = 1.5
    m_clearance_height = 5
    m_start_depth = 0
    m_step_down = 1
    m_final_depth = -1              # original: -3
    m_rapid_down_to_height = 2
    m_tool_diameter = 2             # original: 3
    m_format_style = 0

