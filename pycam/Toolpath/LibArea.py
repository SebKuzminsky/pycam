# -*- coding: utf-8 -*-

import copy

import area

import pycam.Utils.log
import pycam.Geometry.Line
import pycam.Geometry.Polygon

_log = pycam.Utils.log.get_logger()


def _pocket_model(polygons):
    """Create pocketing path."""
    # libarea.Vertex Linetypes
    LINE = 0
    ARC_CCW = 1
    ARC_CW = -1
    
    # copy pycam.Model to libarea.Area
    my_area = area.Area()
    for lg in polygons:
        my_curve = area.Curve()
        """ TODO: direction is not used for now
        if lg.is_closed:
            curve_type = ARC_CW
        else:
            curve_type = LINE
        """
        for pt in lg.get_points():
            my_curve.append(area.Vertex(area.Point(pt[0], pt[1])))
        my_area.append(my_curve)
    my_pocketParams = PocketParams()
    return _pocket_area(my_area, my_pocketParams)


def _pocket_area(a, params):
    polygons = []
    my_params = params

    if (my_params.m_rapid_down_to_height > my_params.m_clearance_height):
        my_params.m_rapid_down_to_height = my_params.m_clearance_height
    
    a.m_round_corners_factor = params.m_round_corner_factor
    
    arealist = _get_inner_polygons(my_params, a)
    if params.m_from_center:
        arealist.reverse()
    
    # add all vertices from all areas to the polygons list
    vertex2point = lambda vt: (vt.p.x, vt.p.y, 0.0)
    for a in arealist:
        for c in a.getCurves():
            my_poly = pycam.Geometry.Polygon.Polygon()
            vertices = c.getVertices()
            if not vertices:
                continue
            p_previous = vertex2point(vertices.pop(0))
            for vt in vertices:
                # from 2D to 3D with Z=0
                current = vertex2point(vt)
                my_poly.append(pycam.Geometry.Line.Line(p_previous, current))
                p_previous = current
            polygons.append(my_poly)
    return polygons


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


def _get_inner_polygons(params, a1):
    if a1.num_curves == 0:
        return []
    areas = []
    # copy Area instance
    a_offset = _get_area_copy(a1)
    a_offset.Offset(params.m_step_over)
    for curve in a_offset.getCurves():
        a2 = area.Area()
        a2.append(curve)
        areas.append(a2)
        areas.extend(_get_inner_polygons(params, a2))
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

