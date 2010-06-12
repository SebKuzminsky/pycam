# -*- coding: utf-8 -*-
"""
$Id$

Copyright 2008 Lode Leroy

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

__all__ = ["DropCutter", "PushCutter", "EngraveCutter"]

from pycam.Geometry.utils import INFINITE, epsilon
from pycam.Geometry import Point
import math


class ProgressCounter:

    def __init__(self, max_value, update_callback):
        self.max_value = max_value
        self.current_value = 0
        self.update_callback = update_callback

    def increment(self):
        self.current_value += 1
        if self.update_callback:
            # "True" means: "quit requested via GUI"
            return self.update_callback(percent=self.get_percent())
        else:
            return False

    def get_percent(self):
        return 100.0 * self.current_value / self.max_value


class Hit:
    def __init__(self, cl, t, d, dir):
        self.cl = cl
        self.t = t
        self.d = d
        self.dir = dir
        self.z = -INFINITE

    def cmp(a,b):
        return cmp(a.d, b.d)

def get_free_paths_triangles(model, cutter, p1, p2):
    points = []
    x_dist = p2.x - p1.x
    y_dist = p2.y - p1.y
    z_dist = p2.z - p1.z
    xyz_dist = math.sqrt(x_dist * x_dist + y_dist * y_dist + z_dist * z_dist)
    x_frac = x_dist / xyz_dist
    y_frac = y_dist / xyz_dist
    z_frac = z_dist / xyz_dist
    forward = Point(x_frac, y_frac, z_frac)
    backward = Point(-x_frac, -y_frac, -z_frac)
    forward_small = Point(epsilon * x_frac, epsilon * y_frac, epsilon * z_frac)
    backward_small = Point(-epsilon * x_frac, -epsilon * y_frac, -epsilon * z_frac)

    minx = min(p1.x, p2.x)
    maxx = max(p1.x, p2.x)
    miny = min(p1.y, p2.y)
    maxy = max(p1.y, p2.y)
    minz = min(p1.z, p2.z)
    maxz = max(p1.z, p2.z)

    # find all hits along scan line
    hits = []
    hits.append(Hit(p1, None, 0, None))

    triangles = model.triangles(minx - cutter.radius, miny - cutter.radius, minz,
            maxx + cutter.radius, maxy + cutter.radius, INFINITE)

    for t in triangles:
        # normals point outward... and we want to approach the model from the outside!
        n = t.normal().dot(forward)
        cutter.moveto(p1)
        if n >= 0:
            (cl, d) = cutter.intersect(backward, t)
            if cl:
                hits.append(Hit(cl, t, -d, backward))
                hits.append(Hit(cl.sub(backward_small), t, -d + epsilon, backward))
                hits.append(Hit(cl.add(backward_small), t, -d - epsilon, backward))
        if n <= 0:
            (cl, d) = cutter.intersect(forward, t)
            if cl:
                hits.append(Hit(cl, t, d, forward))
                hits.append(Hit(cl.add(forward_small), t, d + epsilon, forward))
                hits.append(Hit(cl.sub(forward_small), t, d - epsilon, forward))

    hits.append(Hit(p2, None, xyz_dist, None))


    # sort along the scan direction
    hits.sort(Hit.cmp)

    # Remove duplicates (typically shared edges)
    # Remove hits outside the min/max area of x/y/z (especially useful for the
    # short-line cuts of the EngraveCutter
    filtered_hits = []
    previous_hit = None
    for one_hit in hits:
        if not ((minx - epsilon) < one_hit.cl.x < (maxx + epsilon)):
            continue
        elif not ((miny - epsilon) < one_hit.cl.y < (maxy + epsilon)):
            continue
        elif not ((minz - epsilon) < one_hit.cl.z < (maxz + epsilon)):
            continue
        elif previous_hit and (abs(previous_hit.d - one_hit.d) < epsilon / 2):
            continue
        else:
            previous_hit = one_hit
            filtered_hits.append(one_hit)
    hits = filtered_hits

    # determine height at each interesting point
    for h in hits:
        (zmax, tmax) = drop_cutter_test(cutter, h.cl, model)
        h.z = zmax

    # find first hit cutter location that is below z-level
    begin = hits[0].cl
    end = None
    for h in hits:
        if h.z >= minz - epsilon / 10:
            if begin and end:
                points.append(begin)
                points.append(end)
            begin = None
            end = None
        if h.z <= maxz + epsilon / 10:
            if not begin:
                begin = h.cl
            else:
                end = h.cl
        
    # add add possibly remaining couple from the previous loop
    if begin and end:
        points.append(begin)
        points.append(end)

    return points


def get_free_paths_ode(physics, p1, p2, depth=8):
    """ Recursive function for splitting a line (usually along x or y) into
    small pieces to gather connected paths for the PushCutter.
    Strategy: check if the whole line is free (without collisions). Do a
    recursive call (for the first and second half), if there was a
    collision.

    Usually either minx/maxx or miny/maxy should be equal, unless you want
    to do a diagonal cut.
    @param minx: lower limit of x
    @type minx: float
    @param maxx: upper limit of x; should equal minx for a cut along the x axis
    @type maxx: float
    @param miny: lower limit of y
    @type miny: float
    @param maxy: upper limit of y; should equal miny for a cut along the y axis
    @type maxy: float
    @param z: the fixed z level
    @type z: float
    @param depth: number of splits to be calculated via recursive calls; the
        accuracy can be calculated as (maxx-minx)/(2^depth)
    @type depth: int
    @returns: a list of points that describe the tool path of the PushCutter;
        each pair of points defines a collision-free path
    @rtype: list(pycam.Geometry.Point.Point)
    """
    points = []
    # "resize" the drill along the while x/y range and check for a collision
    physics.extend_drill(p2.x - p1.x, p2.y - p1.y, p2.z - p1.z)
    physics.set_drill_position((p1.x, p1.y, p1.z))
    if physics.check_collision():
        # collision detected
        if depth > 0:
            middle_x = (p1.x + p2.x) / 2.0
            middle_y = (p1.y + p2.y) / 2.0
            middle_z = (p1.z + p2.z) / 2.0
            p_middle = Point(middle_x, middle_y, middle_z)
            group1 = get_free_paths_ode(physics, p1, p_middle, depth - 1)
            group2 = get_free_paths_ode(physics, p_middle, p2, depth - 1)
            if group1 and group2 and (group1[-1] == group2[0]):
                # the last couple of the first group ends where the first couple of the second group starts
                # we will combine them into one couple
                points.extend(group1[:-1])
                points.extend(group2[1:])
            else:
                # the two groups are not connected - just add both
                points.extend(group1)
                points.extend(group2)
        else:
            # no points to be added
            pass
    else:
        # no collision - the line is free
        points.append(p1)
        points.append(p2)
    physics.reset_drill()
    return points

def drop_cutter_test(cutter, point, model):
    zmax = -INFINITE
    tmax = None
    cutter.moveto(point)
    for t in model.triangles():
        if t.normal().z < 0: continue
        cl = cutter.drop(t)
        if cl and cl.z > zmax and cl.z < INFINITE:
            zmax = cl.z
            tmax = t
    return (zmax, tmax)

def get_max_height_ode(physics, x, y, minz, maxz, order=None):
    low, high = minz, maxz
    trip_start = 20
    safe_z = None
    # check if the full step-down would be ok
    physics.set_drill_position((x, y, minz))
    if physics.check_collision():
        # there is an object between z1 and z0 - we need more=None loops
        trips = trip_start
    else:
        # no need for further collision detection - we can go down the whole range z1..z0
        trips = 0
        safe_z = minz
    while trips > 0:
        current_z = (low + high) / 2.0
        physics.set_drill_position((x, y, current_z))
        if physics.check_collision():
            low = current_z
        else:
            high = current_z
            safe_z = current_z
        trips -= 1
    if safe_z is None:
        # no safe position was found - let's check the upper bound
        physics.set_drill_position((x, y, maxz))
        if physics.check_collision():
            # the object fills the whole range of z0..z1 -> no safe height
            pass
        else:
            # at least the upper bound is collision free
            safe_z = maxz
    if safe_z is None:
        return []
    else:
        return [Point(x, y, safe_z)]

def get_max_height_triangles(model, cutter, x, y, minz, maxz, order=None, last_pos=None):
    # TODO: "order" should be replaced with a direction vector
    result = []
    if last_pos is None:
        last_pos = {}
    for key in ("triangle", "cut"):
        if not key in last_pos:
            last_pos[key] = None
    if order is None:
        order = ["x", "y"]
    p = Point(x, y, maxz)
    height_max = None
    cut_max = None
    triangle_max = None
    cutter.moveto(p)
    box_x_min = cutter.minx
    box_x_max = cutter.maxx
    box_y_min = cutter.miny
    box_y_max = cutter.maxy
    box_z_min = minz
    box_z_max = maxz
    triangles = model.triangles(box_x_min, box_y_min, box_z_min, box_x_max, box_y_max, box_z_max)
    for t in triangles:
        if t.normal().z < 0: continue;
        cut = cutter.drop(t)
        if cut and (cut.z > height_max or height_max is None):
            height_max = cut.z
            cut_max = cut
            triangle_max = t
    # don't do a complete boundary check for the height
    # this avoids zero-cuts for models that exceed the bounding box height
    if not cut_max or cut_max.z < minz:
        cut_max = Point(x, y, minz)
    if last_pos["cut"] and \
            ((triangle_max and not last_pos["triangle"]) \
            or (last_pos["triangle"] and not triangle_max)):
        if minz <= last_pos["cut"].z <= maxz:
            result.append(Point(last_pos["cut"].x, last_pos["cut"].y, cut_max.z))
        else:
            result.append(Point(cut_max.x, cut_max.y, last_pos["cut"].z))
    elif (triangle_max and last_pos["triangle"] and last_pos["cut"] and cut_max) and (triangle_max != last_pos["triangle"]):
        nl = range(3)
        nl[0] = -getattr(last_pos["triangle"].normal(), order[0])
        nl[2] = last_pos["triangle"].normal().z
        nm = range(3)
        nm[0] = -getattr(triangle_max.normal(), order[0])
        nm[2] = triangle_max.normal().z
        last = range(3)
        last[0] = getattr(last_pos["cut"], order[0])
        last[2] = last_pos["cut"].z
        mx = range(3)
        mx[0] = getattr(cut_max, order[0])
        mx[2] = cut_max.z
        c = range(3)
        (c[0], c[2]) = intersect_lines(last[0], last[2], nl[0], nl[2], mx[0], mx[2], nm[0], nm[2])
        if c[0] and last[0] < c[0] and c[0] < mx[0] and (c[2] > last[2] or c[2] > mx[2]):
            c[1] = getattr(last_pos["cut"], order[1])
            if c[2]<minz-10 or c[2]>maxz+10:
                print "^", "%sl=%s" % (order[0], last[0]), \
                        ", %sl=%s" % ("z", last[2]), \
                        ", n%sl=%s" % (order[0], nl[0]), \
                        ", n%sl=%s" % ("z", nl[2]), \
                        ", %s=%s" % (order[0].upper(), c[0]), \
                        ", %s=%s" % ("z".upper(), c[2]), \
                        ", %sm=%s" % (order[0], mx[0]), \
                        ", %sm=%s" % ("z", mx[2]), \
                        ", n%sm=%s" % (order[0], nm[0]), \
                        ", n%sm=%s" % ("z", nm[2])

            else:
                if order[0] == "x":
                    result.append(Point(c[0], c[1], c[2]))
                else:
                    result.append(Point(c[1], c[0], c[2]))
    result.append(cut_max)

    last_pos["cut"] = cut_max
    last_pos["triangle"] = triangle_max
    return result

