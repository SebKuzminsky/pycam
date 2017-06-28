# -*- coding: utf-8 -*-
"""
Copyright 2010 Lars Kruse <devel@sumpfralle.de>

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

import math
import enum

from pycam.Geometry import epsilon, Point3D, Box3D
from pycam.Geometry.Line import Line
from pycam.Geometry.Plane import Plane
from pycam.Geometry.PointUtils import padd, pcross, pmul, pnormalized, psub
from pycam.Geometry.Polygon import PolygonSorter
from pycam.Geometry.utils import get_angle_pi, get_points_of_arc
import pycam.Utils.log


_log = pycam.Utils.log.get_logger()


if not hasattr(enum, "IntEnum"):
    # The following is only relevant for Python2 (Python3 includes a core library named 'enum').
    # The pypi package 'enum' is not suitable since it lacks 'IntEnum' (as of v0.4.6).
    # The pypi package 'enum34' is suitable.
    _log.error("The installed 'enum' package lacks 'IntEnum'. Maybe you should install 'enum34' "
               "instead?")


class GridDirection(enum.Enum):
    X = "x"
    Y = "y"
    XY = "xy"


class MillingStyle(enum.Enum):
    IGNORE = "ignore"
    CONVENTIONAL = "conventional"
    CLIMB = "climb"


class StartPosition(enum.IntEnum):
    NONE = 0x0
    X = 0x1
    Y = 0x2
    Z = 0x4


class SpiralDirection(enum.Enum):
    IN = "in"
    OUT = "out"


class PocketingType(enum.Enum):
    NONE = "none"
    HOLES = "holes"
    MATERIAL = "material"


def isiterable(obj):
    try:
        iter(obj)
        return True
    except TypeError:
        return False


def floatrange(start, end, inc=None, steps=None, reverse=False):
    if reverse:
        start, end = end, start
        # 'inc' will be adjusted below anyway
    if abs(start - end) < epsilon:
        yield start
    elif inc is None and steps is None:
        raise ValueError("floatrange: either 'inc' or 'steps' must be provided")
    elif (steps is not None) and (steps < 2):
        raise ValueError("floatrange: 'steps' must be greater than 1")
    else:
        # the input is fine
        # reverse increment, if it does not suit start/end
        if steps is None:
            if ((end - start) > 0) != (inc > 0):
                inc = -inc
            steps = int(math.ceil(float(end - start) / inc) + 1)
        inc = float(end - start) / (steps - 1)
        for index in range(steps):
            yield start + inc * index


def get_fixed_grid_line(start, end, line_pos, z, step_width=None, grid_direction=GridDirection.X):
    if step_width is None:
        # useful for PushCutter operations
        steps = (start, end)
    elif isiterable(step_width):
        steps = step_width
    else:
        steps = floatrange(start, end, inc=step_width)
    if grid_direction == GridDirection.X:
        get_point = lambda pos: (pos, line_pos, z)
    else:
        get_point = lambda pos: (line_pos, pos, z)
    for pos in steps:
        yield get_point(pos)


def get_fixed_grid_layer(minx, maxx, miny, maxy, z, line_distance, step_width=None,
                         grid_direction=GridDirection.X, milling_style=MillingStyle.IGNORE,
                         start_position=StartPosition.NONE):
    if grid_direction == GridDirection.XY:
        raise ValueError("'get_one_layer_fixed_grid' does not accept XY direction")
    # zigzag is only available if the milling
    zigzag = (milling_style == MillingStyle.IGNORE)

    # If we happen to start at a position that collides with the milling style,
    # then we need to move to the closest other corner. Here we decide, which
    # would be the best alternative.
    def get_alternative_start_position(start):
        if (maxx - minx) <= (maxy - miny):
            # toggle the X position bit
            return start ^ StartPosition.X
        else:
            # toggle the Y position bit
            return start ^ StartPosition.Y

    if grid_direction == GridDirection.X:
        primary_dir = StartPosition.X
        secondary_dir = StartPosition.Y
    else:
        primary_dir = StartPosition.Y
        secondary_dir = StartPosition.X
    # Determine the starting direction (assuming we begin at the lower x/y
    # coordinates.
    if milling_style == MillingStyle.IGNORE:
        # just move forward - milling style is not important
        pass
    elif (milling_style == MillingStyle.CLIMB) == (grid_direction == GridDirection.X):
        if bool(start_position & StartPosition.X) == bool(start_position & StartPosition.Y):
            # we can't start from here - choose an alternative
            start_position = get_alternative_start_position(start_position)
    elif (milling_style == MillingStyle.CONVENTIONAL) == (grid_direction == GridDirection.X):
        if bool(start_position & StartPosition.X) != bool(start_position & StartPosition.Y):
            # we can't start from here - choose an alternative
            start_position = get_alternative_start_position(start_position)
    else:
        raise ValueError("Invalid milling style given: %s" % str(milling_style))
    # sort out the coordinates (primary/secondary)
    if grid_direction == GridDirection.X:
        start, end = minx, maxx
        line_start, line_end = miny, maxy
    else:
        start, end = miny, maxy
        line_start, line_end = minx, maxx
    # switch start/end if we move from high to low
    if start_position & primary_dir:
        start, end = end, start
    if start_position & secondary_dir:
        line_start, line_end = line_end, line_start
    # calculate the line positions
    if isiterable(line_distance):
        lines = line_distance
    else:
        lines = floatrange(line_start, line_end, inc=line_distance)
    # at the end of the layer we will be on the other side of the 2nd direction
    end_position = start_position ^ secondary_dir
    # the final position will probably be on the other side (primary)
    if not zigzag:
        end_position ^= primary_dir

    # calculate each line
    def get_lines(start, end, end_position):
        result = []
        for line_pos in lines:
            result.append(get_fixed_grid_line(start, end, line_pos, z, step_width=step_width,
                                              grid_direction=grid_direction))
            if zigzag:
                start, end = end, start
                end_position ^= primary_dir
        if zigzag and step_width:
            # Connect endpoints of zigzag lines (prevent unnecessary safety moves).
            # (DropCutter)
            zigzag_result = []
            for line in result:
                zigzag_result.extend(line)
            # return a list containing a single chain of lines
            result = [zigzag_result]
        elif zigzag and step_width is None:
            # Add a pair of end_before/start_next points between two lines.
            # (PushCutter)
            zigzag_result = []
            last = None
            for (p1, p2) in result:
                if last:
                    zigzag_result.append((last, p1))
                zigzag_result.append((p1, p2))
                last = p2
            result = zigzag_result
        return result, end_position

    return get_lines(start, end, end_position)


def get_fixed_grid(box, layer_distance, line_distance=None, step_width=None,
                   grid_direction=GridDirection.X, milling_style=MillingStyle.IGNORE,
                   start_position=StartPosition.Z):
    """ Calculate the grid positions for toolpath moves
    """
    assert isinstance(milling_style, MillingStyle)
    assert isinstance(grid_direction, GridDirection)
    assert isinstance(start_position, StartPosition)
    if isiterable(layer_distance):
        layers = layer_distance
    elif layer_distance is None:
        # useful for DropCutter
        layers = [box.lower.z]
    else:
        layers = floatrange(box.lower.z, box.upper.z, inc=layer_distance,
                            reverse=bool(start_position & StartPosition.Z))

    def get_layers_with_direction(layers):
        for layer in layers:
            # this will produce a nice xy-grid, as well as simple x and y grids
            if grid_direction != GridDirection.Y:
                yield (layer, GridDirection.X)
            if grid_direction != GridDirection.X:
                yield (layer, GridDirection.Y)

    for z, direction in get_layers_with_direction(layers):
        result, start_position = get_fixed_grid_layer(
            box.lower.x, box.upper.x, box.lower.y, box.upper.y, z, line_distance,
            step_width=step_width, grid_direction=direction, milling_style=milling_style,
            start_position=start_position)
        yield result


def _get_position(minx, maxx, miny, maxy, z, position):
    if position & StartPosition.X > 0:
        x = minx
    else:
        x = maxx
    if position & StartPosition.Y > 0:
        y = miny
    else:
        y = maxy
    return (x, y, z)


def get_spiral_layer_lines(minx, maxx, miny, maxy, z, line_distance_x, line_distance_y,
                           grid_direction, start_position, current_location):
    xor_map = {GridDirection.X: StartPosition.X, GridDirection.Y: StartPosition.Y}
    end_position = start_position ^ xor_map[grid_direction]
    end_location = _get_position(minx, maxx, miny, maxy, z, end_position)
    lines = [(current_location, end_location)]
    if grid_direction == GridDirection.X:
        next_grid_direction = GridDirection.Y
        if start_position & StartPosition.Y > 0:
            miny += line_distance_y
        else:
            maxy -= line_distance_y
    else:
        next_grid_direction = GridDirection.X
        if start_position & StartPosition.X > 0:
            minx += line_distance_x
        else:
            maxx -= line_distance_x
    if (minx - epsilon <= maxx) and (miny - epsilon <= maxy):
        # recursively compute the next lines
        lines.extend(get_spiral_layer_lines(minx, maxx, miny, maxy, z, line_distance_x,
                                            line_distance_y, next_grid_direction, end_position,
                                            end_location))
    return lines


def get_spiral_layer(minx, maxx, miny, maxy, z, line_distance, step_width, grid_direction,
                     start_position, rounded_corners, reverse):
    current_location = _get_position(minx, maxx, miny, maxy, z, start_position)
    if line_distance > 0:
        line_steps_x = math.ceil((float(maxx - minx) / line_distance))
        line_steps_y = math.ceil((float(maxy - miny) / line_distance))
        line_distance_x = (maxx - minx) / line_steps_x
        line_distance_y = (maxy - miny) / line_steps_y
        lines = get_spiral_layer_lines(minx, maxx, miny, maxy, z, line_distance_x, line_distance_y,
                                       grid_direction, start_position, current_location)
        if reverse:
            lines.reverse()
        # turn the lines into steps
        if rounded_corners:
            rounded_lines = []
            previous = None
            for index, (start, end) in enumerate(lines):
                radius = 0.5 * min(line_distance_x, line_distance_y)
                edge_vector = psub(end, start)
                # TODO: ellipse would be better than arc
                offset = pmul(pnormalized(edge_vector), radius)
                if previous:
                    start = padd(start, offset)
                    center = padd(previous, offset)
                    up_vector = pnormalized(pcross(psub(previous, center), psub(start, center)))
                    north = padd(center, (1.0, 0.0, 0.0, 'v'))
                    angle_start = get_angle_pi(north, center, previous, up_vector,
                                               pi_factor=True) * 180.0
                    angle_end = get_angle_pi(north, center, start, up_vector,
                                             pi_factor=True) * 180.0
                    # TODO: remove these exceptions based on up_vector.z (get_points_of_arc does
                    #       not respect the plane, yet)
                    if up_vector[2] < 0:
                        angle_start, angle_end = -angle_end, -angle_start
                    arc_points = get_points_of_arc(center, radius, angle_start, angle_end)
                    if up_vector[2] < 0:
                        arc_points.reverse()
                    for arc_index in range(len(arc_points) - 1):
                        p1_coord = arc_points[arc_index]
                        p2_coord = arc_points[arc_index + 1]
                        p1 = (p1_coord[0], p1_coord[1], z)
                        p2 = (p2_coord[0], p2_coord[1], z)
                        rounded_lines.append((p1, p2))
                if index != len(lines) - 1:
                    end = psub(end, offset)
                previous = end
                rounded_lines.append((start, end))
            lines = rounded_lines
        for start, end in lines:
            points = []
            if step_width is None:
                points.append(start)
                points.append(end)
            else:
                line = Line(start, end)
                if isiterable(step_width):
                    steps = step_width
                else:
                    steps = floatrange(0.0, line.len, inc=step_width)
                for step in steps:
                    next_point = padd(line.p1, pmul(line.dir, step))
                    points.append(next_point)
            if reverse:
                points.reverse()
            yield points


def get_spiral(box, layer_distance, line_distance=None, step_width=None,
               milling_style=MillingStyle.IGNORE, spiral_direction=SpiralDirection.IN,
               rounded_corners=False,
               start_position=(StartPosition.X | StartPosition.Y | StartPosition.Z)):
    """ Calculate the grid positions for toolpath moves
    """
    if isiterable(layer_distance):
        layers = layer_distance
    elif layer_distance is None:
        # useful for DropCutter
        layers = [box.lower.z]
    else:
        layers = floatrange(box.lower.z, box.upper.z, inc=layer_distance,
                            reverse=bool(start_position & StartPosition.Z))
    if (milling_style == MillingStyle.CLIMB) == (start_position & StartPosition.X > 0):
        start_direction = GridDirection.X
    else:
        start_direction = GridDirection.Y
    reverse = (spiral_direction == SpiralDirection.OUT)
    for z in layers:
        yield get_spiral_layer(box.lower.x, box.upper.x, box.lower.y, box.upper.y, z,
                               line_distance, step_width=step_width,
                               grid_direction=start_direction, start_position=start_position,
                               rounded_corners=rounded_corners, reverse=reverse)


def get_lines_layer(lines, z, last_z=None, step_width=None,
                    milling_style=MillingStyle.CONVENTIONAL):
    get_proj_point = lambda proj_point: (proj_point[0], proj_point[1], z)
    projected_lines = []
    for line in lines:
        if (last_z is not None) and (last_z < line.minz):
            # the line was processed before
            continue
        elif line.minz < z < line.maxz:
            # Split the line at the point at z level and do the calculation
            # for both point pairs.
            factor = (z - line.p1[2]) / (line.p2[2] - line.p1[2])
            plane_point = padd(line.p1, pmul(line.vector, factor))
            if line.p1[2] < z:
                p1 = get_proj_point(line.p1)
                p2 = line.p2
            else:
                p1 = line.p1
                p2 = get_proj_point(line.p2)
            projected_lines.append(Line(p1, plane_point))
            yield Line(plane_point, p2)
        elif line.minz < last_z < line.maxz:
            plane = Plane((0, 0, last_z), (0, 0, 1, 'v'))
            cp = plane.intersect_point(line.dir, line.p1)[0]
            # we can be sure that there is an intersection
            if line.p1[2] > last_z:
                p1, p2 = cp, line.p2
            else:
                p1, p2 = line.p1, cp
            projected_lines.append(Line(p1, p2))
        else:
            if line.maxz <= z:
                # the line is completely below z
                projected_lines.append(Line(get_proj_point(line.p1), get_proj_point(line.p2)))
            elif line.minz >= z:
                projected_lines.append(line)
            else:
                _log.warn("Unexpected condition 'get_lines_layer': %s / %s / %s / %s",
                          line.p1, line.p2, z, last_z)
    # process all projected lines
    for line in projected_lines:
        points = []
        if step_width is None:
            points.append(line.p1)
            points.append(line.p2)
        else:
            if isiterable(step_width):
                steps = step_width
            else:
                steps = floatrange(0.0, line.len, inc=step_width)
            for step in steps:
                next_point = padd(line.p1, pmul(line.dir, step))
                points.append(next_point)
        yield points


def _get_sorted_polygons(models, callback=None):
    # Sort the polygons according to their directions (first inside, then
    # outside. This reduces the problem of break-away pieces.
    inner_polys = []
    outer_polys = []
    for model in models:
        for poly in model.get_polygons():
            if poly.get_area() <= 0:
                inner_polys.append(poly)
            else:
                outer_polys.append(poly)
    inner_sorter = PolygonSorter(inner_polys, callback=callback)
    outer_sorter = PolygonSorter(outer_polys, callback=callback)
    return inner_sorter.get_polygons() + outer_sorter.get_polygons()


def get_lines_grid(models, box, layer_distance, line_distance=None, step_width=None,
                   milling_style=MillingStyle.CONVENTIONAL, start_position=StartPosition.Z,
                   pocketing_type=PocketingType.NONE, skip_first_layer=False, callback=None):
    _log.debug("Calculating lines grid: {} model(s), z={}..{} ({}), line_distance={}, "
               "step_width={}".format(len(models), box.lower, box.upper, layer_distance,
                                      line_distance, step_width))
    # the lower limit is never below the model
    polygons = _get_sorted_polygons(models, callback=callback)
    if polygons:
        low_limit_lines = min([polygon.minz for polygon in polygons])
        new_lower = Point3D(box.lower.x, box.lower.y, max(box.lower.z, low_limit_lines))
        box = Box3D(new_lower, box.upper)
    # calculate pockets
    if pocketing_type != PocketingType.NONE:
        if callback is not None:
            callback(text="Generating pocketing polygons ...")
        polygons = get_pocketing_polygons(polygons, line_distance, pocketing_type,
                                          callback=callback)
    # extract lines in correct order from all polygons
    lines = []
    for polygon in polygons:
        if callback:
            callback()
        if polygon.is_closed and (milling_style == MillingStyle.CONVENTIONAL):
            polygon = polygon.copy()
            polygon.reverse_direction()
        for line in polygon.get_lines():
            lines.append(line)
    if isiterable(layer_distance):
        layers = layer_distance
    elif layer_distance is None:
        # only one layer
        layers = [box.lower.z]
    else:
        layers = floatrange(box.lower.z, box.upper.z, inc=layer_distance,
                            reverse=bool(start_position & StartPosition.Z))
    # turn the generator into a list - otherwise the slicing fails
    layers = list(layers)
    # engrave ignores the top layer
    if skip_first_layer and (len(layers) > 1):
        layers = layers[1:]
    last_z = None
    if layers:
        # the upper layers are used for PushCutter operations
        for z in layers[:-1]:
            if callback:
                callback()
            yield get_lines_layer(lines, z, last_z=last_z, step_width=None,
                                  milling_style=milling_style)
            last_z = z
        # the last layer is used for a DropCutter operation
        if callback:
            callback()
        yield get_lines_layer(lines, layers[-1], last_z=last_z, step_width=step_width,
                              milling_style=milling_style)


def get_pocketing_polygons(polygons, offset, pocketing_type, callback=None):
    """ calculate the pocketing polygons for a given set of polygons

    This function checks if the (not yet fully integrated) openvoronoi library
    is found (see pycam.Toolpath.OpenVoronoi for details). If this fails it
    uses the better-tested (but known to be unstable) simple pocketing
    algorithm.
    """
    try:
        import pycam.Toolpath.OpenVoronoi
        use_voronoi = True
    except ImportError:
        use_voronoi = False
    if use_voronoi:
        _log.debug("Using openvoronoi pocketing algorithm")
        poly = pycam.Toolpath.OpenVoronoi.pocket_model(polygons, offset)
    else:
        _log.info("Failed to load openvoronoi library.")
        poly = get_pocketing_polygons_simple(polygons, offset, pocketing_type, callback)
    return poly


def get_pocketing_polygons_simple(polygons, offset, pocketing_type, callback=None):
    pocketing_limit = 1000
    base_polygons = []
    other_polygons = []
    if pocketing_type == PocketingType.HOLES:
        # go inwards
        offset *= -1
        for poly in polygons:
            if poly.is_closed and poly.is_outer():
                base_polygons.append(poly)
            else:
                other_polygons.append(poly)
    elif pocketing_type == PocketingType.MATERIAL:
        for poly in polygons:
            if poly.is_closed and not poly.is_outer():
                base_polygons.append(poly)
            else:
                other_polygons.append(poly)
    else:
        _log.warning("Invalid pocketing type given: %d", str(pocketing_type))
        return polygons
    # For now we use only the polygons that do not surround any other
    # polygons. Sorry - the pocketing is currently very simple ...
    base_filtered_polygons = []
    for candidate in base_polygons:
        if callback and callback():
            # we were interrupted
            return polygons
        for other in other_polygons:
            if candidate.is_polygon_inside(other):
                break
        else:
            base_filtered_polygons.append(candidate)
    # start the pocketing for all remaining polygons
    pocket_polygons = []
    for base_polygon in base_filtered_polygons:
        pocket_polygons.append(base_polygon)
        current_queue = [base_polygon]
        next_queue = []
        pocket_depth = 0
        while current_queue and (pocket_depth < pocketing_limit):
            if callback and callback():
                return polygons
            for poly in current_queue:
                result = poly.get_offset_polygons(offset)
                pocket_polygons.extend(result)
                next_queue.extend(result)
                pocket_depth += 1
            current_queue = next_queue
            next_queue = []
    return pocket_polygons
