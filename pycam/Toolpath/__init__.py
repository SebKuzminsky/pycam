# -*- coding: utf-8 -*-
"""
$Id$

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

__all__ = ["simplify_toolpath", "ToolpathList", "Toolpath", "Generator"]

import OpenGL.GL as GL
from OpenGL.arrays import vbo
import numpy
from numpy import array
from pycam.Geometry.PointUtils import *
from pycam.Geometry.Path import Path
from pycam.Geometry.Line import Line
from pycam.Geometry.utils import number, epsilon
import pycam.Utils.log
import random
import os

import math
from itertools import groupby


MOVE_STRAIGHT, MOVE_STRAIGHT_RAPID, MOVE_ARC, MOVE_SAFETY, TOOL_CHANGE, \
        MACHINE_SETTING = range(6)


def _check_colinearity(p1, p2, p3):
    v1 = pnormalized(psub(p2, p1))
    v2 = pnormalized(psub(p3, p2))
    # compare if the normalized distances between p1-p2 and p2-p3 are equal
    return v1 == v2


def simplify_toolpath(path):
    """ remove multiple points in a line from a toolpath

    If A, B, C and D are on a straight line, then B and C will be removed.
    This reduces memory consumption and avoids a severe slow-down of the machine
    when moving along very small steps.
    The toolpath is simplified _in_place_.
    @value path: a single separate segment of a toolpath
    @type path: pycam.Geometry.Path.Path
    """
    index = 1
    points = path.points
    while index < len(points) - 1:
        if _check_colinearity(points[index-1], points[index], points[index+1]):
            points.pop(index)
            # don't increase the counter - otherwise we skip one point
        else:
            index += 1


class Toolpath(object):

    def __init__(self, path, parameters=None):
        self.path = path
        if not parameters:
            parameters = {}
        self.parameters = parameters
        # TODO: remove this hidden import (currently necessary to avoid dependency loop)
        from pycam.Toolpath.Filters import TinySidewaysMovesFilter, MachineSetting, \
                SafetyHeightFilter
        self.filters = []
        self.filters.append(MachineSetting("metric", True))
        self.filters.append(MachineSetting("feedrate",
                parameters.get("tool_feedrate", 300)))
        self.filters.append(TinySidewaysMovesFilter(
                2 * parameters.get("tool_radius", 0)))
        self.filters.append(SafetyHeightFilter(20))
        self._feedrate = parameters.get("tool_feedrate", 300)
        self.clear_cache()
        
    def clear_cache(self):
        self.opengl_safety_height = None
        self._minx = None
        self._maxx = None
        self._miny = None
        self._maxy = None
        self._minz = None
        self._maxz = None

    def get_params(self):
        return dict(self.parameters)

    def copy(self):
        new_paths = []
        for path in self.path:
            new_path = Path()
            for point in path:
                new_path.append(point)
            new_paths.append(new_path)
        return Toolpath(new_paths, parameters=self.get_params())

    def _get_limit_generic(self, idx, func):
        values = [p[idx] for move_type, p in self.path
                  if move_type in (MOVE_STRAIGHT, MOVE_STRAIGHT_RAPID)]
        return func(values)

    @property
    def minx(self):
        if self._minx == None:
            self._minx = self._get_limit_generic(0, min)
        return self._minx

    @property
    def maxx(self):
        if self._maxx == None:
            self._maxx = self._get_limit_generic(0, max)
        return self._maxx

    @property
    def miny(self):
        if self._miny == None:
            self._miny = self._get_limit_generic(1, min)
        return self._miny

    @property
    def maxy(self):
        if self._maxy == None:
            self._maxy = self._get_limit_generic(1, max)
        return self._maxy

    @property
    def minz(self):
        if self._minz == None:
            self._minz = self._get_limit_generic(2, min)
        return self._minz

    @property
    def maxz(self):
        if self._maxz == None:
            self._maxz = self._get_limit_generic(2, max)
        return self._maxz

    def get_meta_data(self):
        meta = self.toolpath_settings.get_string()
        start_marker = self.toolpath_settings.META_MARKER_START
        end_marker = self.toolpath_settings.META_MARKER_END
        return os.linesep.join((start_marker, meta, end_marker))

    def get_moves(self, safety_height, max_movement=None):
        self._update_safety_height(safety_height)
        class MoveContainer(object):
            def __init__(self, max_movement):
                self.max_movement = max_movement
                self.moved_distance = 0
                self.moves = []
                self.last_pos = None
                if max_movement is None:
                    self.append = self.append_without_movement_limit
                else:
                    self.append = self.append_with_movement_limit
            def append_with_movement_limit(self, new_position, rapid):
                if self.last_pos is None:
                    # first move with unknown start position - ignore it
                    self.moves.append((new_position, rapid))
                    self.last_pos = new_position
                    return True
                else:
                    distance = pdist(new_position, self.last_pos)
                    if self.moved_distance + distance > self.max_movement:
                        partial = (self.max_movement - self.moved_distance) / \
                                distance
                        partial_dest = padd(self.last_pos, pmul(psub(new_position, self.last_pos), partial))
                        self.moves.append((partial_dest, rapid))
                        self.last_pos = partial_dest
                        # we are finished
                        return False
                    else:
                        self.moves.append((new_position, rapid))
                        self.moved_distance += distance
                        self.last_pos = new_position
                        return True
            def append_without_movement_limit(self, new_position, rapid):
                self.moves.append((new_position, rapid))
                return True
        p_last = None
        result = MoveContainer(max_movement)
        for path in self.path:
            if not path:
                # ignore empty paths
                continue
            p_next = path[0]
            if p_last is None:
                p_last = (p_next[0], p_next[1], safety_height)
                if not result.append(p_last, True):
                    return result.moves
            if ((abs(p_last[0] - p_next[0]) > epsilon) or (abs(p_last[1] - p_next[1]) > epsilon)):
                # Draw the connection between the last and the next path.
                # Respect the safety height.
                if (abs(p_last[2] - p_next[2]) > epsilon) or (pdist(p_last, p_next) > self._max_safe_distance + epsilon):
                    # The distance between these two points is too far.
                    # This condition helps to prevent moves up/down for
                    # adjacent lines.
                    safety_last = (p_last[0], p_last[1], safety_height)
                    safety_next = (p_next[0], p_next[1], safety_height)
                    if not result.append(safety_last, True):
                        return result.moves
                    if not result.append(safety_next, True):
                        return result.moves
            for p in path.points:
                if not result.append(p, False):
                    return result.moves
            p_last = path.points[-1]
        if not p_last is None:
            p_last_safety = (p_last[0], p_last[1], safety_height)
            result.append(p_last_safety, True)
        return result.moves
    
    def _rotate_point(self, rp, sp, v, angle):
        vx = v[0]
        vy = v[1]
        vz = v[2]
        x = (sp[0] * (vy ** 2 + vz ** 2) - vx * (sp[1] * vy + sp[2] * vz - vx * rp[0] - vy * rp[1] - vz * rp[2])) * (1 - math.cos(angle)) + rp[0] * math.cos(angle) + (-sp[2] * vy + sp[1] * vz - vz * rp[1] + vy * rp[2]) * math.sin(angle)
        y = (sp[1] * (vx ** 2 + vz ** 2) - vy * (sp[0] * vx + sp[2] * vz - vx * rp[0] - vy * rp[1] - vz * rp[2])) * (1 - math.cos(angle)) + rp[1] * math.cos(angle) + (sp[2] * vx - sp[0] * vz + vz * rp[0] - vx * rp[2]) * math.sin(angle)
        z = (sp[2] * (vx ** 2 + vy ** 2) - vz * (sp[0] * vx + sp[1] * vy - vx * rp[0] - vy * rp[1] - vz * rp[2])) * (1 - math.cos(angle)) + rp[2] * math.cos(angle) + (-sp[1] * vx + sp[0] * vy - vy * rp[0] + vx * rp[1]) * math.sin(angle)
        return (x,y,z)
    
    def draw_direction_cone_mesh(self, p1, p2, position=0.5, precision=12, size=0.1):
        distance = psub(p2, p1)
        length = pnorm(distance)
        direction = pnormalized(distance)
        if direction is None or length < 0.5:
            # zero-length line
            return []
        cone_length = length * size
        cone_radius = cone_length / 3.0
        bottom = padd(p1, pmul(psub(p2, p1), position - size/2))
        top = padd(p1, pmul(psub(p2, p1), position + size/2))
        #generate a a line perpendicular to this line, cross product is good at this
        cross = pcross(direction, (0, 0, -1))
        conepoints = []
        if pnorm(cross) != 0:
            # The line direction is not in line with the z axis.
            conep1 = padd(bottom, pmul(cross, cone_radius))
            conepoints = [ self._rotate_point(conep1, bottom, direction, x) for x in numpy.linspace(0, 2*math.pi, precision)]
        else:
            # Z axis
            # just add cone radius to the x axis and rotate the point
            conep1 = (bottom[0] + cone_radius, bottom[1], bottom[2])
            conepoints = [ self._rotate_point(conep1, p1, direction, x) for x in numpy.linspace(0, 2*math.pi, precision)]
        
        triangles = [(top, conepoints[idx], conepoints[idx + 1]) for idx in range ( len(conepoints) - 1)]
        return triangles

       
    def get_moves_for_opengl(self, safety_height):
        if self.opengl_safety_height != safety_height:
            self.make_moves_for_opengl(safety_height)
            self.make_vbo_for_moves()
        return (self.opengl_coords, self.opengl_indices)
    
    # separate vertex coordinates from line definitions and convert to indices
    def make_vbo_for_moves(self):
        index = 0
        output = []
        store_vertices = {}
        vertices = []
        for path in self.opengl_lines:
            indices = []
            triangles = []
            triangle_indices = []
            # compress the lines into a centeral array containing all the vertices
            # generate a matching index for each line
            for idx in range(len(path[0]) - 1):
                point = path[0][idx]
                if not point in store_vertices:
                    store_vertices[point] = index
                    vertices.insert(index, point)
                    index += 1
                indices.append(store_vertices[point])
                point2 = path[0][idx + 1]
                if not point2 in store_vertices:
                    store_vertices[point2] = index
                    vertices.insert(index, point2)
                    index += 1
                triangles.extend(self.draw_direction_cone_mesh(path[0][idx], path[0][idx + 1]))
                for t in triangles:
                    for p in t:
                        if not p in store_vertices:
                            store_vertices[p] = index
                            vertices.insert(index, p)
                            index += 1
                        triangle_indices.append(store_vertices[p])
            triangle_indices = array(triangle_indices, dtype=numpy.int32)
            indices.append(store_vertices[path[0][-1]])
            # this list comprehension removes consecutive duplicate points.
            indices = array([x[0] for x in groupby(indices)],dtype=numpy.int32)
            output.append((indices, triangle_indices, path[1]))
        vertices = array(vertices, dtype=numpy.float32)
        self.opengl_coords = vbo.VBO(vertices)
        self.opengl_indices = output

    
    #convert moves into lines for dispaly with opengl
    def make_moves_for_opengl(self, safety_height):
        working_path = []
        outpaths = []
        for path in self.paths:
            if not path:
                continue
            path = path.points
            
            if len(outpaths) != 0:
                lastp = outpaths[-1][0][-1]
                working_path.append((path[0][0], path[0][1], safety_height))
                if ((abs(lastp[0] - path[0][0]) > epsilon) or (abs(lastp[1] - path[0][1]) > epsilon)):
                    if (abs(lastp[2] - path[0][2]) > epsilon) or (pdist(lastp, path[0]) > self._max_safe_distance + epsilon):
                        outpaths.append((tuple([x[0] for x in groupby(working_path)]), True))
            else:
                working_path.append((0,0,0))
                working_path.append((path[0][0], path[0][1], safety_height))
                outpaths.append((working_path, True))
            
            # add this move to last move if last move was not rapid
            if outpaths[-1][1] == False:
                outpaths[-1] = (outpaths[-1][0] + tuple(path), False)
            else:
                # last move was rapid, so add last point of rapid to beginning of path
                outpaths.append((tuple([x[0] for x in groupby((outpaths[-1][0][-1],) + tuple(path))]), False))
            working_path = []
            working_path.append(path[-1])
            working_path.append((path[-1][0], path[-1][1], safety_height))
        outpaths.append((tuple([x[0] for x in groupby(working_path)]), True))
        self.opengl_safety_height = safety_height
        self.opengl_lines = outpaths
        
    def get_machine_time(self, safety_height=0.0):
        """ calculate an estimation of the time required for processing the
        toolpath with the machine

        @value safety_height: the safety height configured for this toolpath
        @type safety_height: float
        @rtype: float
        @returns: the machine time used for processing the toolpath in minutes
        """
        return self.get_machine_move_distance(safety_height) / self._feedrate

    def _update_safety_height(self, safety_height):
        # TODO: remove this ugly hack!
        from pycam.Toolpath.Filters import SafetyHeightFilter
        for index in range(len(self.filters)):
            if isinstance(self.filters[index], SafetyHeightFilter) and \
                    (self.filters[index].safety_height != safety_height):
                self.filters[index] = SafetyHeightFilter(safety_height)
                self.get_basic_moves(reset_cache=True)
                break

    def get_machine_move_distance(self, safety_height):
        result = 0
        current_position = None
        self._update_safety_height(safety_height)
        # go through all points of the path
        for move_type, args in self.get_basic_moves():
            if move_type in (MOVE_STRAIGHT, MOVE_STRAIGHT_RAPID):
                if not current_position is None:
                    result += pdist(args, current_position)
                current_position = args
        return result
    def get_basic_moves(self, reset_cache=False):
        if reset_cache or not hasattr(self, "_cache_basic_moves"):
            result = list(self.path)
            for move_filter in self.filters:
                result |= move_filter
            self._cache_basic_moves = result
        return self._cache_basic_moves

    def get_cropped_copy(self, polygons, callback=None):
        # create a deep copy of the current toolpath
        tp = self.copy()
        tp.crop(polygons, callback=callback)
        return tp

    def crop(self, polygons, callback=None):
        # collect all existing toolpath lines
        open_lines = []
        # TODO: migrate "crop" to the new toolpath structure
        for index in range(len(path) - 1):
            open_lines.append(Line(path[index], path[index + 1]))
        # go through all polygons and add "inner" lines (or parts thereof) to
        # the final list of remaining lines
        inner_lines = []
        for polygon in polygons:
            new_open_lines = []
            for line in open_lines:
                if callback and callback():
                    return
                inner, outer = polygon.split_line(line)
                inner_lines.extend(inner)
                new_open_lines.extend(outer)
            open_lines = new_open_lines
        # turn all "inner_lines" into toolpath moves
        new_paths = []
        current_path = Path()
        if inner_lines:
            line = inner_lines.pop(0)
            current_path.append(line.p1)
            current_path.append(line.p2)
        while inner_lines:
            if callback and callback():
                return
            end = current_path[-1]
            # look for the next connected point
            for line in inner_lines:
                if line.p1 == end:
                    inner_lines.remove(line)
                    current_path.append(line.p2)
                    break
            else:
                new_paths.append(current_path)
                current_path = Path()
                line = inner_lines.pop(0)
                current_path.append(line.p1)
                current_path.append(line.p2)
        if current_path:
            new_paths.append(current_path)
        self.path = new_path


class Bounds(object):

    TYPE_RELATIVE_MARGIN = 0
    TYPE_FIXED_MARGIN = 1
    TYPE_CUSTOM = 2

    def __init__(self, bounds_type=None, bounds_low=None, bounds_high=None,
            reference=None):
        """ create a new Bounds instance

        @value bounds_type: any of TYPE_RELATIVE_MARGIN | TYPE_FIXED_MARGIN |
            TYPE_CUSTOM
        @type bounds_type: int
        @value bounds_low: the lower margin of the boundary compared to the
            reference object (for TYPE_RELATIVE_MARGIN | TYPE_FIXED_MARGIN) or
            the specific boundary values (for TYPE_CUSTOM). Only the lower
            values of the three axes (x, y and z) are given.
        @type bounds_low: (tuple|list) of float
        @value bounds_high: see 'bounds_low'
        @type bounds_high: (tuple|list) of float
        @value reference: optional default reference Bounds instance
        @type reference: Bounds
        """
        self.name = "No name"
        # set type
        self.bounds_type = None
        if bounds_type is None:
            self.set_type(Bounds.TYPE_CUSTOM)
        else:
            self.set_type(bounds_type)
        # store the bounds values
        self.bounds_low = None
        self.bounds_high = None
        if bounds_low is None:
            bounds_low = [0, 0, 0]
        if bounds_high is None:
            bounds_high = [0, 0, 0]
        self.set_bounds(bounds_low, bounds_high)
        self.reference = reference

    def __repr__(self):
        bounds_type_labels = ("relative", "fixed", "custom")
        return "Bounds(%s, %s, %s)" % (bounds_type_labels[self.bounds_type],
                self.bounds_low, self.bounds_high)

    def is_valid(self):
        for index in range(3):
            if self.bounds_low[index] > self.bounds_high[index]:
                return False
        else:
            return True

    def set_reference(self, reference):
        self.reference = reference

    def set_name(self, name):
        self.name = name

    def get_name(self):
        return self.name

    def get_type(self):
        return self.bounds_type

    def set_type(self, bounds_type):
        # complain if an unknown bounds_type value was given
        if not bounds_type in (Bounds.TYPE_RELATIVE_MARGIN,
                Bounds.TYPE_FIXED_MARGIN, Bounds.TYPE_CUSTOM):
            raise ValueError, "failed to create an instance of " \
                    + "pycam.Toolpath.Bounds due to an invalid value of " \
                    + "'bounds_type': %s" % repr(bounds_type)
        else:
            self.bounds_type = bounds_type

    def get_referenced_bounds(self, reference):
        return Bounds(bounds_type=self.bounds_type, bounds_low=self.bounds_low,
                bounds_high=self.bounds_high, reference=reference)

    def get_bounds(self):
        return self.bounds_low[:], self.bounds_high[:]

    def set_bounds(self, low=None, high=None):
        if not low is None:
            if len(low) != 3:
                raise ValueError, "lower bounds should be supplied as a " \
                        + "tuple/list of 3 items - but %d were given" % len(low)
            else:
                self.bounds_low = [number(value) for value in low]
        if not high is None:
            if len(high) != 3:
                raise ValueError, "upper bounds should be supplied as a " \
                        + "tuple/list of 3 items - but %d were given" \
                        % len(high)
            else:
                self.bounds_high = [number(value) for value in high]

    def get_absolute_limits(self, reference=None):
        """ calculate the current absolute limits of the Bounds instance

        @value reference: a reference object described by a tuple (or list) of
            three item. These three values describe only the lower boundary of
            this object (for the x, y and z axes). Each item must be a float
            value. This argument is ignored for the boundary type "TYPE_CUSTOM".
        @type reference: (tuple|list) of float
        @returns: a tuple of two lists containg the low and high limits
        @rvalue: tuple(list)
        """
        # use the default reference if none was given
        if reference is None:
            reference = self.reference
        # check if a reference is given (if necessary)
        if self.bounds_type \
                in (Bounds.TYPE_RELATIVE_MARGIN, Bounds.TYPE_FIXED_MARGIN):
            if reference is None:
                raise ValueError, "any non-custom boundary definition " \
                        + "requires a reference object for caluclating " \
                        + "absolute limits"
            else:
                ref_low, ref_high = reference.get_absolute_limits()
        low = [None] * 3
        high = [None] * 3
        # calculate the absolute limits
        if self.bounds_type == Bounds.TYPE_RELATIVE_MARGIN:
            for index in range(3):
                dim_width = ref_high[index] - ref_low[index]
                low[index] = ref_low[index] \
                        - self.bounds_low[index] * dim_width
                high[index] = ref_high[index] \
                        + self.bounds_high[index] * dim_width
        elif self.bounds_type == Bounds.TYPE_FIXED_MARGIN:
            for index in range(3):
                low[index] = ref_low[index] - self.bounds_low[index]
                high[index] = ref_high[index] + self.bounds_high[index]
        elif self.bounds_type == Bounds.TYPE_CUSTOM:
            for index in range(3):
                low[index] = number(self.bounds_low[index])
                high[index] = number(self.bounds_high[index])
        else:
            # this should not happen
            raise NotImplementedError, "the function 'get_absolute_limits' is" \
                    + " currently not implemented for the bounds_type " \
                    + "'%s'" % str(self.bounds_type)
        return low, high

    def adjust_bounds_to_absolute_limits(self, limits_low, limits_high,
            reference=None):
        """ change the current bounds settings according to some absolute values

        This does not change the type of this bounds instance (e.g. relative).
        @value limits_low: a tuple describing the new lower absolute boundary
        @type limits_low: (tuple|list) of float
        @value limits_high: a tuple describing the new lower absolute boundary
        @type limits_high: (tuple|list) of float
        @value reference: a reference object described by a tuple (or list) of
            three item. These three values describe only the lower boundary of
            this object (for the x, y and z axes). Each item must be a float
            value. This argument is ignored for the boundary type "TYPE_CUSTOM".
        @type reference: (tuple|list) of float
        """
        # use the default reference if none was given
        if reference is None:
            reference = self.reference
        # check if a reference is given (if necessary)
        if self.bounds_type \
                in (Bounds.TYPE_RELATIVE_MARGIN, Bounds.TYPE_FIXED_MARGIN):
            if reference is None:
                raise ValueError, "any non-custom boundary definition " \
                        + "requires an a reference object for caluclating " \
                        + "absolute limits"
            else:
                ref_low, ref_high = reference.get_absolute_limits()
        # calculate the new settings
        if self.bounds_type == Bounds.TYPE_RELATIVE_MARGIN:
            for index in range(3):
                dim_width = ref_high[index] - ref_low[index]
                if dim_width == 0:
                    # We always loose relative margins if the specific dimension
                    # is zero. There is no way to avoid this.
                    message = "Non-zero %s boundary lost during conversion " \
                            + "to relative margins due to zero size " \
                            + "dimension '%s'." % "xyz"[index]
                    # Display warning messages, if we can't reach the requested
                    # absolute dimension.
                    if ref_low[index] != limits_low[index]:
                        log.info(message % "lower")
                    if ref_high[index] != limits_high[index]:
                        log.info(message % "upper")
                    self.bounds_low[index] = 0
                    self.bounds_high[index] = 0
                else:
                    self.bounds_low[index] = \
                            (ref_low[index] - limits_low[index]) / dim_width
                    self.bounds_high[index] = \
                            (limits_high[index] - ref_high[index]) / dim_width
        elif self.bounds_type == Bounds.TYPE_FIXED_MARGIN:
            for index in range(3):
                self.bounds_low[index] = ref_low[index] - limits_low[index]
                self.bounds_high[index] = limits_high[index] - ref_high[index]
        elif self.bounds_type == Bounds.TYPE_CUSTOM:
            for index in range(3):
                self.bounds_low[index] = limits_low[index]
                self.bounds_high[index] = limits_high[index]
        else:
            # this should not happen
            raise NotImplementedError, "the function " \
                    + "'adjust_bounds_to_absolute_limits' is currently not " \
                    + "implemented for the bounds_type '%s'" \
                    % str(self.bounds_type)

