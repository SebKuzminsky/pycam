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

from pycam.Geometry.Point import Point
from pycam.Geometry.Line import Line
from pycam.Geometry.Triangle import Triangle
from pycam.Geometry.Model import Model


def _add_cuboid_to_model(minx, maxx, miny, maxy, minz, maxz):
    def get_triangles_for_face(pts):
        t1 = Triangle(pts[0], pts[1], pts[2], Line(pts[0], pts[1]),
                Line(pts[1], pts[2]), Line(pts[2], pts[0]))
        t2 = Triangle(pts[2], pts[3], pts[0], Line(pts[2], pts[3]),
                Line(pts[3], pts[0]), Line(pts[0], pts[2]))
        return (t1, t2)
    points = (
            Point(minx, miny, minz),
            Point(maxx, miny, minz),
            Point(maxx, maxy, minz),
            Point(minx, maxy, minz),
            Point(minx, miny, maxz),
            Point(maxx, miny, maxz),
            Point(maxx, maxy, maxz),
            Point(minx, maxy, maxz))
    triangles = []
    # lower face
    triangles.extend(get_triangles_for_face(
            (points[0], points[1], points[2], points[3])))
    # upper face
    triangles.extend(get_triangles_for_face(
            (points[4], points[5], points[6], points[7])))
    # front face
    triangles.extend(get_triangles_for_face(
            (points[0], points[1], points[5], points[4])))
    # back face
    triangles.extend(get_triangles_for_face(
            (points[2], points[3], points[7], points[6])))
    # right face
    triangles.extend(get_triangles_for_face(
            (points[1], points[2], points[6], points[5])))
    # left face
    triangles.extend(get_triangles_for_face(
            (points[3], points[0], points[4], points[7])))
    # add all triangles to the model
    model = Model()
    for t in triangles:
        model.append(t)
    return model

def get_support_grid_locations(minx, maxx, miny, maxy, dist_x, dist_y,
        offset_x=0.0, offset_y=0.0, adjustments_x=None, adjustments_y=None):
    def get_lines(center, dist, min_value, max_value):
        """ generate a list of positions starting from the middle going up and
        and down
        """
        if dist > 0:
            lines = [center]
            current = center
            while current - dist > min_value:
                current -= dist
                lines.insert(0, current)
            current = center
            while current + dist < max_value:
                current += dist
                lines.append(current)
        else:
            lines = []
        # remove lines that are out of range (e.g. due to a huge offset)
        lines = [line for line in lines if min_value < line < max_value]
        return lines
    center_x = (maxx + minx) / 2.0 + offset_x
    center_y = (maxy + miny) / 2.0 + offset_y
    lines_x = get_lines(center_x, dist_x, minx, maxx)
    lines_y = get_lines(center_y, dist_y, miny, maxy)
    if adjustments_x:
        for index in range(min(len(lines_x), len(adjustments_x))):
            lines_x[index] += adjustments_x[index]
    if adjustments_y:
        for index in range(min(len(lines_y), len(adjustments_y))):
            lines_y[index] += adjustments_y[index]
    return lines_x, lines_y

def get_support_grid(minx, maxx, miny, maxy, z_plane, dist_x, dist_y, thickness,
        height, offset_x=0.0, offset_y=0.0, adjustments_x=None,
        adjustments_y=None):
    lines_x, lines_y = get_support_grid_locations(minx, maxx, miny, maxy, dist_x,
            dist_y, offset_x, offset_y, adjustments_x, adjustments_y)
    # create all x grid lines
    grid_model = Model()
    # helper variables
    thick_half = thickness / 2.0
    length_extension = max(thickness, height)
    for line_x in lines_x:
        # we make the grid slightly longer (by thickness) than necessary
        grid_model += _add_cuboid_to_model(line_x - thick_half,
                line_x + thick_half, miny - length_extension,
                maxy + length_extension, z_plane, z_plane + height)
    for line_y in lines_y:
        # we make the grid slightly longer (by thickness) than necessary
        grid_model += _add_cuboid_to_model(minx - length_extension,
                maxx + length_extension, line_y - thick_half,
                line_y + thick_half, z_plane, z_plane + height)
    return grid_model

