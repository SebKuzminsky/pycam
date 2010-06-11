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

from pycam.Geometry import Point, Line, Triangle, Model


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
    triangles.extend(get_triangles_for_face((points[0], points[1], points[2], points[3])))
    # upper face
    triangles.extend(get_triangles_for_face((points[4], points[5], points[6], points[7])))
    # front face
    triangles.extend(get_triangles_for_face((points[0], points[1], points[5], points[4])))
    # back face
    triangles.extend(get_triangles_for_face((points[2], points[3], points[7], points[6])))
    # right face
    triangles.extend(get_triangles_for_face((points[1], points[2], points[6], points[5])))
    # left face
    triangles.extend(get_triangles_for_face((points[3], points[0], points[4], points[7])))
    # add all triangles to the model
    model = Model.Model()
    for t in triangles:
        model.append(t)
    return model

def get_support_grid(minx, maxx, miny, maxy, z_plane, dist_x, dist_y, thickness):
    lines_x = 1 + int((maxx - minx) / dist_x)
    lines_y = 1 + int((maxy - miny) / dist_y)
    # we center the grid
    start_x = ((maxx - minx) - (lines_x - 1) * dist_x) / 2.0 + minx
    start_y = ((maxy - miny) - (lines_y - 1) * dist_y) / 2.0 + miny
    # create all x grid lines
    grid_model = Model.Model()
    radius = thickness / 2.0
    for i in range(lines_x):
        x = start_x + i * dist_x
        # we make the grid slightly longer (by thickness) than necessary
        grid_model += _add_cuboid_to_model(x - radius, x + radius,
                miny - thickness, maxy + thickness, z_plane, z_plane + thickness)
    for i in range(lines_y):
        y = start_y + i * dist_y
        # we make the grid slightly longer (by thickness) than necessary
        grid_model += _add_cuboid_to_model(minx - thickness, maxx + thickness,
                y - radius, y + radius, z_plane, z_plane + thickness)
    return grid_model

