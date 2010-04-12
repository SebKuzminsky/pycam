"""
various matrix related functions for PyCAM
"""

from pycam.Geometry.Point import Point
import math

def get_dot_product(a, b):
    return sum(map(lambda l1, l2: l1 * l2, a, b))

def get_cross_product(a, b):
    if isinstance(a, Point):
        a = (a.x, a.y, a.z)
    if isinstance(b, Point):
        b = (b.x, b.y, b.z)
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])

def get_length(vector):
    return math.sqrt(get_dot_product(vector, vector))

def get_rotation_matrix(v_orig, v_dest):
    if isinstance(v_orig, Point):
        v_orig = (v_orig.x, v_orig.y, v_orig.z)
    if isinstance(v_dest, Point):
        v_dest = (v_dest.x, v_dest.y, v_dest.z)
    v_orig_length = get_length(v_orig)
    v_dest_length = get_length(v_dest)
    cross_product = get_length(get_cross_product(v_orig, v_dest))
    rot_angle = math.asin(cross_product / (v_orig_length * v_dest_length))
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

