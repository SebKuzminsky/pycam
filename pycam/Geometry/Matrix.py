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

"""
various matrix related functions for PyCAM
"""

from pycam.Geometry.Point import Point
import math

def get_dot_product(a, b):
    """ calculate the dot product of two 3d vectors

    @type a: tuple(float) | list(float)
    @value a: the first vector to be multiplied
    @type b: tuple(float) | list(float)
    @value b: the second vector to be multiplied
    @rtype: float
    @return: the dot product is (a0*b0 + a1*b1 + a2*b2)
    """
    return sum(map(lambda l1, l2: l1 * l2, a, b))

def get_cross_product(a, b):
    """ calculate the cross product of two 3d vectors

    @type a: tuple(float) | list(float) | pycam.Geometry.Point
    @value a: the first vector to be multiplied
    @type b: tuple(float) | list(float) | pycam.Geometry.Point
    @value b: the second vector to be multiplied
    @rtype: tuple(float)
    @return: the cross product is a 3d vector
    """
    if isinstance(a, Point):
        a = (a.x, a.y, a.z)
    if isinstance(b, Point):
        b = (b.x, b.y, b.z)
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])

def get_length(vector):
    """ calculate the lengt of a 3d vector

    @type vector: tuple(float) | list(float)
    @value vector: the given 3d vector
    @rtype: float
    @return: the length of a vector is the square root of the dot product
        of the vector with itself
    """
    return math.sqrt(get_dot_product(vector, vector))

def get_rotation_matrix_from_to(v_orig, v_dest):
    """ calculate the rotation matrix used to transform one vector into another
    
    The result is useful for modifying the rotation matrix of a 3d object.
    See the "extend_shape" code in each of the cutter classes (for ODE).
    The simplest example is the following with the original vector pointing
    along the x axis, while the destination vectors goes along the y axis:
        get_rotation_matrix((1, 0, 0), (0, 1, 0))
    Basically this describes a rotation around the z axis by 90 degrees.
    The resulting 3x3 matrix (tuple of 9 floats) can be multiplied with any
    other vector to rotate it in the same way around the z axis.
    @type v_orig: tuple(float) | list(float) | pycam.Geometry.Point
    @value v_orig: the original 3d vector
    @type v_dest: tuple(float) | list(float) | pycam.Geometry.Point
    @value v_dest: the destination 3d vector
    @rtype: tuple(float)
    @return: the tuple of 9 floats represents a 3x3 matrix, that can be
        multiplied with any vector to rotate it in the same way, as you would
        rotate v_orig to the position of v_dest
    """
    if isinstance(v_orig, Point):
        v_orig = (v_orig.x, v_orig.y, v_orig.z)
    if isinstance(v_dest, Point):
        v_dest = (v_dest.x, v_dest.y, v_dest.z)
    v_orig_length = get_length(v_orig)
    v_dest_length = get_length(v_dest)
    cross_product = get_length(get_cross_product(v_orig, v_dest))
    arcsin = cross_product / (v_orig_length * v_dest_length)
    # prevent float inaccuracies to crash the calculation (within limits)
    if arcsin > 1.0001:
        arcsin = 1.0
    elif arcsin < 1.001:
        arcsin = -1.0
    rot_angle = math.asin(arcsin)
    # calculate the rotation axis
    # the rotation axis is equal to the cross product of the original and destination vectors
    rot_axis = Point(v_orig[1] * v_dest[2] - v_orig[2] * v_dest[1],
            v_orig[2] * v_dest[0] - v_orig[0] * v_dest[2],
            v_orig[0] * v_dest[1] - v_orig[1] * v_dest[0])
    rot_axis.normalize()
    # get the rotation matrix
    # see http://www.fastgraph.com/makegames/3drotation/
    c = math.cos(rot_angle)
    s = math.sin(rot_angle)
    t = 1 - c
    return (t * rot_axis.x * rot_axis.x + c,
            t * rot_axis.x * rot_axis.y - s * rot_axis.z,
            t * rot_axis.x * rot_axis.z + s * rot_axis.y,
            t * rot_axis.x * rot_axis.y + s * rot_axis.z,
            t * rot_axis.y * rot_axis.y + c,
            t * rot_axis.y * rot_axis.z - s * rot_axis.x,
            t * rot_axis.x * rot_axis.z - s * rot_axis.y,
            t * rot_axis.y * rot_axis.z + s * rot_axis.x,
            t * rot_axis.z * rot_axis.z + c)

def get_rotation_matrix_axis_angle(rot_axis, rot_angle):
    """ calculate rotation matrix for a normalized "rot_axis" vector and an angle

    see http://mathworld.wolfram.com/RotationMatrix.html
    @type rot_axis: tuple(float)
    @value rot_axis: the vector describes the rotation axis. Its length should
        be 1.0 (normalized).
    @type rot_angle: float
    @value rot_angle: rotation angle (radiant)
    @rtype: tuple(float)
    @return: the roation
    """
    sin = math.sin(rot_angle)
    cos = math.cos(rot_angle)
    return ((cos + rot_axis[0]*rot_axis[0]*(1-cos),
            rot_axis[0]*rot_axis[1]*(1-cos) - rot_axis[2]*sin,
            rot_axis[0]*rot_axis[2]*(1-cos) + rot_axis[1]*sin),
            (rot_axis[1]*rot_axis[0]*(1-cos) + rot_axis[2]*sin,
            cos + rot_axis[1]*rot_axis[1]*(1-cos),
            rot_axis[1]*rot_axis[2]*(1-cos) - rot_axis[0]*sin),
            (rot_axis[2]*rot_axis[0]*(1-cos) - rot_axis[1]*sin,
            rot_axis[2]*rot_axis[1]*(1-cos) + rot_axis[0]*sin,
            cos + rot_axis[2]*rot_axis[2]*(1-cos)))

def multiply_vector_matrix(v, m):
    """ Multiply a 3d vector with a 3x3 matrix. The result is a 3d vector.

    @type v: tuple(float) | list(float)
    @value v: a 3d vector as tuple or list containing three floats
    @type m: tuple(tuple(float)) | list(list(float))
    @value m: a 3x3 list/tuple of floats
    @rtype: tuple(float)
    @return: a tuple of 3 floats as the matrix product
    """
    return (v[0] * m[0][0] + v[1] * m[0][1] + v[2] * m[0][2],
            v[0] * m[1][0] + v[1] * m[1][1] + v[2] * m[1][2],
            v[0] * m[2][0] + v[1] * m[2][1] + v[2] * m[2][2])

