# -*- coding: utf-8 -*-
"""
$Id$

Copyright 2010 Lars Kruse <devel@sumpfralle.de>
Copyright 2008-2009 Lode Leroy

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

__all__ = ["utils", "Line", "Model", "Path", "Plane", "Triangle",
           "PolygonExtractor", "TriangleKdtree", "intersection", "kdtree",
           "Matrix", "Polygon", "Letters", "PointUtils"]

from pycam.Geometry.PointUtils import *
from pycam.Geometry.utils import epsilon, ceil
from pycam.Utils import log
import types
log = log.get_logger()
import math


def get_bisector(p1, p2, p3, up_vector):
    """ Calculate the bisector between p1, p2 and p3, whereas p2 is the origin
    of the angle.
    """
    d1 = pnormalized(psub(p2, p1))
    #d1 = p2.sub(p1).normalized()
    d2 = pnormalized(psub(p2, p3))
    #d2 = p2.sub(p3).normalized()
    bisector_dir = pnormalized(padd(d1, d2))
    #bisector_dir = d1.add(d2).normalized()
    if bisector_dir is None:
        # the two vectors pointed to opposite directions
        bisector_dir = pnormalized(pcross(d1, up_vector))
        #bisector_dir = d1.cross(up_vector).normalized()
    else:
        skel_up_vector = pcross(bisector_dir, psub(p2, p1))
        #skel_up_vector = bisector_dir.cross(p2.sub(p1))
        #if up_vector.dot(skel_up_vector) < 0:
        if pdot(up_vector, skel_up_vector) < 0:
            # reverse the skeleton vector to point outwards
            bisector_dir = pmul(bisector_dir, -1)
            #bisector_dir = bisector_dir.mul(-1)
    return bisector_dir

def get_angle_pi(p1, p2, p3, up_vector, pi_factor=False):
    """ calculate the angle between three points
    Visualization:
            p3
           /
          /
         /\
        /  \
      p2--------p1
    The result is in a range between 0 and 2*PI.
    """
    d1 = pnormalized(psub(p2, p1))
    #d1 = p2.sub(p1).normalized()
    d2 = pnormalized(psub(p2, p3))
    #d2 = p2.sub(p3).normalized()
    if (d1 is None) or (d2 is None):
        return 2 * math.pi
    angle = math.acos(pdot(d1, d2))
    #angle = math.acos(d1.dot(d2))
    # check the direction of the points (clockwise/anti)
    # The code is taken from Polygon.get_area
    value = [0, 0, 0]
    for (pa, pb) in ((p1, p2), (p2, p3), (p3, p1)):
        value[0] += pa[1] * pb[2] - pa[2] * pb[1]
        value[1] += pa[2] * pb[0] - pa[0] * pb[2]
        value[2] += pa[0] * pb[1] - pa[1] * pb[0]
    area = up_vector[0] * value[0] + up_vector[1] * value[1] + up_vector[2] * value[2]
    if area > 0:
        # The points are in anti-clockwise order. Thus the angle is greater
        # than 180 degree.
        angle = 2 * math.pi - angle
    if pi_factor:
        # the result is in the range of 0..2
        return angle / math.pi
    else:
        return angle

def get_points_of_arc(center, radius, a1, a2, plane=None, cords=32):
    """ return the points for an approximated arc

    @param center: center of the circle
    @type center: pycam.Geometry.Point.Point
    @param radius: radius of the arc
    @type radius: float
    @param a1: angle of the start (in degree)
    @type a1: float
    @param a2: angle of the end (in degree)
    @type a2: float
    @param plane: the plane of the circle (default: xy-plane)
    @type plane: pycam.Geometry.Plane.Plane
    @param cords: number of lines for a full circle
    @type cords: int
    @return: a list of points approximating the arc
    @rtype: list(pycam.Geometry.Point.Point)
    """
    # TODO: implement 3D arc and respect "plane"
    a1 = math.pi * a1 / 180
    a2 = math.pi * a2 / 180
    angle_diff = a2 - a1
    if angle_diff < 0:
        angle_diff += 2 * math.pi
    if angle_diff >= 2 * math.pi:
        angle_diff -= 2 * math.pi
    if angle_diff == 0:
        return []
    num_of_segments = ceil(angle_diff / (2 * math.pi) * cords)
    angle_segment = angle_diff / num_of_segments
    points = []
    get_angle_point = lambda angle: (
            center[0] + radius * math.cos(angle),
            center[1] + radius * math.sin(angle))
    points.append(get_angle_point(a1))
    for index in range(num_of_segments):
        points.append(get_angle_point(a1 + angle_segment * (index + 1)))
    return points

def get_bezier_lines(points_with_bulge, segments=32):
    # TODO: add a recursive algorithm for more than two points
    if len(points_with_bulge) != 2:
        return []
    else:
        result_points = []
        p1, bulge1 = points_with_bulge[0]
        p2, bulge2 = points_with_bulge[1]
        if not bulge1 and not bulge2:
            # straight line
            return [Line.Line(p1, p2)]
        straight_dir = pnormalized(psub(p2, p1))
        #straight_dir = p2.sub(p1).normalized()
        #bulge1 = max(-1.0, min(1.0, bulge1))
        bulge1 = math.atan(bulge1)
        rot_matrix = Matrix.get_rotation_matrix_axis_angle((0, 0, 1),
                -2 * bulge1, use_radians=True)
        dir1_mat = Matrix.multiply_vector_matrix((straight_dir[0],
                straight_dir[1], straight_dir[2]), rot_matrix)
        dir1 = (dir1_mat[0], dir1_mat[1], dir1_mat[2], 'v')
        if bulge2 is None:
            bulge2 = bulge1
        else:
            bulge2 = math.atan(bulge2)
        rot_matrix = Matrix.get_rotation_matrix_axis_angle((0, 0, 1),
                2 * bulge2, use_radians=True)
        dir2_mat = Matrix.multiply_vector_matrix((straight_dir[0],
                straight_dir[1], straight_dir[2]), rot_matrix)
        dir2 = (dir2_mat[0], dir2_mat[1], dir2_mat[2], 'v')
        # interpretation of bulge1 and bulge2:
        # /// taken from http://paulbourke.net/dataformats/dxf/dxf10.html ///
        # The bulge is the tangent of 1/4 the included angle for an arc
        # segment, made negative if the arc goes clockwise from the start
        # point to the end point; a bulge of 0 indicates a straight segment,
        # and a bulge of 1 is a semicircle.
        alpha = 2 * (abs(bulge1) + abs(bulge2))
        dist = pnorm(psub(p2, p1))
        #dist = p2.sub(p1).norm
        # calculate the radius of the circumcircle - avoiding divide-by-zero
        if (abs(alpha) < epsilon) or (abs(math.pi - alpha) < epsilon):
            radius = dist / 2.0
        else:
            # see http://en.wikipedia.org/wiki/Law_of_sines
            radius = abs(dist / math.sin(alpha / 2.0)) / 2.0
        # The calculation of "factor" is based on random guessing - but it
        # seems to work well.
        factor = 4 * radius * math.tan(alpha / 4.0)
        dir1 = pmul(dir1, factor)
        #dir1 = dir1.mul(factor)
        dir2 = pmul(dir2, factor)
        #dir2 = dir2.mul(factor)
        for index in range(segments + 1):
            # t: 0..1
            t = float(index) / segments
            # see: http://en.wikipedia.org/wiki/Cubic_Hermite_spline
            #p = p1.mul(2 * t ** 3 - 3 * t ** 2 + 1).add(
            #    dir1.mul(t ** 3 - 2 * t ** 2 + t).add(
            #        p2.mul(-2 * t ** 3 + 3 * t ** 2).add(
            #            dir2.mul(t ** 3 - t ** 2)
            #        )
            #    )
            #)
            p = padd( pmul(p1, 2 * t ** 3 - 3 * t ** 2 + 1) ,padd( pmul(dir1, t ** 3 - 2 * t ** 2 + t), padd(pmul(p2, -2 * t ** 3 + 3 * t ** 2) ,pmul(dir2, t ** 3 - t ** 2))))
            result_points.append(p)
        # create lines
        result = []
        for index in range(len(result_points) - 1):
            result.append(Line.Line(result_points[index],
                    result_points[index + 1]))
        return result


def _id_generator():
    current_id = 0
    while True:
        yield current_id
        current_id += 1


class IDGenerator(object):

    __id_gen_func = _id_generator()

    def __init__(self):
        self.id = self.__id_gen_func.next()


class TransformableContainer(object):
    """ a base class for geometrical objects containing other elements

    This class is mainly used for simplifying model transformations in a
    consistent way.

    Every subclass _must_ implement a 'next' generator returning (via yield)
    its children.
    Additionally a method 'reset_cache' for any custom re-initialization must
    be provided. This method is called when all children of the object were
    successfully transformed.

    A method 'get_children_count' for calculating the number of children
    (recursively) is necessary for the "callback" parameter of
    "transform_by_matrix".

    Optionally the method 'transform_by_matrix' may be used to perform
    object-specific calculations (e.g. retaining the 'normal' vector of a
    triangle).

    The basic primitives that are part of TransformableContainer _must_
    implement the above 'transform_by_matrix' method. These primitives are
    not required to be a subclass of TransformableContainer.
    """

    def transform_by_matrix(self, matrix, transformed_list=None, callback=None):
        if transformed_list is None:
            transformed_list = []
        # Prevent any kind of loops or double transformations (e.g. Points in
        # multiple containers (Line, Triangle, ...).
        # Use the 'id' builtin to prevent expensive object comparions.
        for item in self.next():
            if isinstance(item, TransformableContainer):
                item.transform_by_matrix(matrix, transformed_list,callback=callback)
            elif not id(item) in transformed_list:
                # non-TransformableContainer do not care to update the
                # 'transformed_list'. Thus we need to do it.
                #transformed_list.append(id(item))
                # Don't transmit the 'transformed_list' if the object is
                # not a TransformableContainer. It is not necessary and it
                # is hard to understand on the lowest level (e.g. Point).
                if isinstance(item, str):
                    theval = getattr(self, item)
                    if isinstance(theval, tuple):
                        setattr(self, item, ptransform_by_matrix(theval, matrix))
                    elif isinstance(theval, list):
                        setattr(self, item, [ptransform_by_matrix(x, matrix) for x in theval])
                elif isinstance(item, tuple):
                    log.error("ERROR!! A tuple (Point, Vector) made it into base transform_by_matrix without a back reference. Point/Vector remains unchanged.")
                else:
                    item.transform_by_matrix(matrix, callback=callback)
            # run the callback - e.g. for a progress counter
            if callback and callback():
                # user requesteded abort
                break
        self.reset_cache()

    def __iter__(self):
        return self

    def next(self):
        raise NotImplementedError(("'%s' is a subclass of " \
                + "'TransformableContainer' but it fails to implement the " \
                + "'next' generator") % str(type(self)))

    def get_children_count(self):
        raise NotImplementedError(("'%s' is a subclass of " \
                + "'TransformableContainer' but it fails to implement the " \
                + "'get_children_count' method") % str(type(self)))

    def reset_cache(self):
        raise NotImplementedError(("'%s' is a subclass of " \
                + "'TransformableContainer' but it fails to implement the " \
                + "'reset_cache' method") % str(type(self)))

    def is_completely_inside(self, minx=None, maxx=None, miny=None, maxy=None,
            minz=None, maxz=None):
        return ((minx is None) or (minx - epsilon <= self.minx)) \
                and ((maxx is None) or (self.maxx <= maxx + epsilon)) \
                and ((miny is None) or (miny - epsilon <= self.miny)) \
                and ((maxy is None) or (self.maxy <= maxy + epsilon)) \
                and ((minz is None) or (minz - epsilon <= self.minz)) \
                and ((maxz is None) or (self.maxz <= maxz + epsilon))

    def is_completely_outside(self, minx=None, maxx=None, miny=None, maxy=None,
            minz=None, maxz=None):
        return ((maxx is None) or (maxx + epsilon < self.minx)) \
                or ((minx is None) or (self.maxx < minx - epsilon)) \
                or ((maxy is None) or (maxy + epsilon < self.miny)) \
                or ((miny is None) or (self.maxy < miny - epsilon)) \
                or ((maxz is None) or (maxz + epsilon < self.minz)) \
                or ((minz is None) or (self.maxz < minz - epsilon))

