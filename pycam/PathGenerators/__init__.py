# -*- coding: utf-8 -*-
"""
Copyright 2010 Lars Kruse <devel@sumpfralle.de>
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

from pycam.Geometry import epsilon, INFINITE
from pycam.Geometry.PointUtils import pdist, pnorm, pnormalized, psub


class Hit(object):
    def __init__(self, cl, cp, t, d, direction):
        self.cl = cl
        self.cp = cp
        self.t = t
        self.d = d
        self.dir = direction
        self.z = -INFINITE

    def __repr__(self):
        return "%s - %s - %s - %s" % (self.d, self.cl, self.dir, self.cp)


def get_free_paths_triangles(models, cutter, p1, p2, return_triangles=False):
    if (len(models) == 0) or ((len(models) == 1) and (models[0] is None)):
        return (p1, p2)
    elif len(models) == 1:
        # only one model is left - just continue
        model = models[0]
    else:
        # multiple models were given - process them in layers
        result = get_free_paths_triangles(models[:1], cutter, p1, p2, return_triangles)
        # group the result into pairs of two points (start/end)
        point_pairs = []
        while result:
            pair1 = result.pop(0)
            pair2 = result.pop(0)
            point_pairs.append((pair1, pair2))
        all_results = []
        for pair in point_pairs:
            one_result = get_free_paths_triangles(models[1:], cutter, pair[0], pair[1],
                                                  return_triangles)
            all_results.extend(one_result)
        return all_results

    backward = pnormalized(psub(p1, p2))
    forward = pnormalized(psub(p2, p1))
    xyz_dist = pdist(p2, p1)

    minx = min(p1[0], p2[0])
    maxx = max(p1[0], p2[0])
    miny = min(p1[1], p2[1])
    maxy = max(p1[1], p2[1])
    minz = min(p1[2], p2[2])

    # find all hits along scan line
    hits = []

    triangles = model.triangles(minx - cutter.distance_radius, miny - cutter.distance_radius, minz,
                                maxx + cutter.distance_radius, maxy + cutter.distance_radius,
                                INFINITE)

    for t in triangles:
        (cl1, d1, cp1) = cutter.intersect(backward, t, start=p1)
        if cl1:
            hits.append(Hit(cl1, cp1, t, -d1, backward))
        (cl2, d2, cp2) = cutter.intersect(forward, t, start=p1)
        if cl2:
            hits.append(Hit(cl2, cp2, t, d2, forward))

    # sort along the scan direction
    hits.sort(key=lambda h: h.d)

    count = 0
    points = []
    for h in hits:
        if h.dir == forward:
            if count == 0:
                if -epsilon <= h.d <= xyz_dist + epsilon:
                    if len(points) == 0:
                        points.append((p1, None, None))
                    points.append((h.cl, h.t, h.cp))
            count += 1
        else:
            if count == 1:
                if -epsilon <= h.d <= xyz_dist + epsilon:
                    points.append((h.cl, h.t, h.cp))
            count -= 1

    if len(points) % 2 == 1:
        points.append((p2, None, None))

    if len(points) == 0:
        # check if the path is completely free or if we are inside of the model
        inside_counter = 0
        for h in hits:
            if -epsilon <= h.d:
                # we reached the outer limit of the model
                break
            if h.dir == forward:
                inside_counter += 1
            else:
                inside_counter -= 1
        if inside_counter <= 0:
            # we are not inside of the model
            points.append((p1, None, None))
            points.append((p2, None, None))

    if return_triangles:
        return points
    else:
        # return only the cutter locations (without triangles)
        return [cut_info[0] for cut_info in points]


def get_max_height_triangles(model, cutter, x, y, minz, maxz):
    if model is None:
        return (x, y, minz)
    p = (x, y, maxz)
    height_max = None
    box_x_min = cutter.get_minx(p)
    box_x_max = cutter.get_maxx(p)
    box_y_min = cutter.get_miny(p)
    box_y_max = cutter.get_maxy(p)
    box_z_min = minz
    box_z_max = maxz
    triangles = model.triangles(box_x_min, box_y_min, box_z_min, box_x_max, box_y_max, box_z_max)
    for t in triangles:
        cut = cutter.drop(t, start=p)
        if cut and ((height_max is None) or (cut[2] > height_max)):
            height_max = cut[2]
    # don't do a complete boundary check for the height
    # this avoids zero-cuts for models that exceed the bounding box height
    if (height_max is None) or (height_max < minz + epsilon):
        height_max = minz
    if height_max > maxz + epsilon:
        return None
    else:
        return (x, y, height_max)


def _check_deviance_of_adjacent_points(p1, p2, p3, min_distance):
    straight = psub(p3, p1)
    added = pdist(p2, p1) + pdist(p3, p2)
    # compare only the x/y distance of p1 and p3 with min_distance
    if straight[0] ** 2 + straight[1] ** 2 < min_distance ** 2:
        # the points are too close together
        return True
    else:
        # allow 0.1% deviance - this is an angle of around 2 degrees
        return (added / pnorm(straight)) < 1.001


def get_max_height_dynamic(model, cutter, positions, minz, maxz):
    max_depth = 8
    # the points don't need to get closer than 1/1000 of the cutter radius
    min_distance = cutter.distance_radius / 1000
    points = []
    get_max_height = lambda x, y: get_max_height_triangles(model, cutter, x, y, minz, maxz)
    # add one point between all existing points
    for index, p in enumerate(positions):
        points.append(get_max_height(p[0], p[1]))
    # Check if three consecutive points are "flat".
    # Add additional points if necessary.
    index = 0
    depth_count = 0
    while index < len(points) - 2:
        p1 = points[index]
        p2 = points[index + 1]
        p3 = points[index + 2]
        if ((None not in (p1, p2, p3))
                and not _check_deviance_of_adjacent_points(p1, p2, p3, min_distance)
                and (depth_count < max_depth)):
            # distribute the new point two before the middle and one after
            if depth_count % 3 != 2:
                # insert between the 1st and 2nd point
                middle = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
                points.insert(index + 1, get_max_height(middle[0], middle[1]))
            else:
                # insert between the 2nd and 3rd point
                middle = ((p2[0] + p3[0]) / 2, (p2[1] + p3[1]) / 2)
                points.insert(index + 2, get_max_height(middle[0], middle[1]))
            depth_count += 1
        else:
            index += 1
            depth_count = 0
    # remove all points that are in line
    index = 1
    while index + 1 < len(points):
        p1, p2, p3 = points[index - 1:index + 2]
        if _check_deviance_of_adjacent_points(p1, p2, p3, 0):
            # remove superfluous point
            points.pop(index)
        else:
            index += 1
    return points
