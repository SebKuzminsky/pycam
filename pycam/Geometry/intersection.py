# -*- coding: utf-8 -*-
"""
$Id$

Copyright 2008-2010 Lode Leroy

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


#import pycam.Geometry
from pycam.Utils.polynomials import poly4_roots
from pycam.Geometry.utils import INFINITE, sqrt, epsilon
from pycam.Geometry.Plane import Plane
from pycam.Geometry.Line import Line
from pycam.Geometry.PointUtils import *

def isNear(a, b):
    return abs(a - b) < epsilon

def isZero(a):
    return isNear(a, 0)

def intersect_lines(xl, zl, nxl, nzl, xm, zm, nxm, nzm):
    X = None
    Z = None
    try:
        if isZero(nzl) and isZero(nzm):
            pass
        elif isZero(nzl) or isZero(nxl):
            X = xl
            Z = zm + (xm - xl) * nxm / nzm
            return (X, Z)
        elif isZero(nzm) or isZero(nxm):
            X = xm
            Z = zl - (xm - xl) * nxl / nzl
            return (X, Z)
        else:
            X = (zl - zm +(xm * nxm / nzm - xl * nxl / nzl)) \
                    / (nxm / nzm - nxl / nzl)
            if X and xl < X and X < xm:
                Z = zl + (X -xl) * nxl / nzl
                return (X, Z)
    except ZeroDivisionError:
        pass
    return (None, None)

def intersect_cylinder_point(center, axis, radius, radiussq, direction, point):
    # take a plane along direction and axis
    n = pnormalized(pcross(direction, axis))
    #n = direction.cross(axis).normalized()
    # distance of the point to this plane
    d = pdot(n, point) - pdot(n, center)
    #d = n.dot(point) - n.dot(center)
    if abs(d) > radius - epsilon:
        return (None, None, INFINITE)
    # ccl is on cylinder
    d2 = sqrt(radiussq-d*d)
    ccl = padd( padd(center, pmul(n, d)), pmul(direction, d2))
    #ccl = center.add(n.mul(d)).add(direction.mul(d2))
    # take plane through ccl and axis
    plane = Plane(ccl, direction)
    # intersect point with plane
    (ccp, l) = plane.intersect_point(direction, point)
    return (ccp, point, -l)

def intersect_cylinder_line(center, axis, radius, radiussq, direction, edge):
    d = edge.dir
    # take a plane throught the line and along the cylinder axis (1)
    n = pcross(d, axis)
    #n = d.cross(axis)
    if pnorm(n) == 0:
        # no contact point, but should check here if cylinder *always*
        # intersects line...
        return (None, None, INFINITE)
    n = pnormalized(n)
    # the contact line between the cylinder and this plane (1)
    # is where the surface normal is perpendicular to the plane
    # so line := ccl + \lambda * axis
    #if n.dot(direction) < 0:
    if pdot(n, direction) < 0:
        ccl = psub(center, pmul(n, radius))
        #ccl = center.sub(n.mul(radius))
    else:
        ccl = padd(center, pmul(n, radius))
        #ccl = center.add(n.mul(radius))
    # now extrude the contact line along the direction, this is a plane (2)
    n2 = pcross(direction, axis)
    #n2 = direction.cross(axis)
    if pnorm(n2) == 0:
        # no contact point, but should check here if cylinder *always*
        # intersects line...
        return (None, None, INFINITE)
    n2 = pnormalized(n2)
    #n2 = n2.normalized()
    plane1 = Plane(ccl, n2)
    # intersect this plane with the line, this gives us the contact point
    (cp, l) = plane1.intersect_point(d, edge.p1)
    if not cp:
        return (None, None, INFINITE)
    # now take a plane through the contact line and perpendicular to the
    # direction (3)
    plane2 = Plane(ccl, direction)
    # the intersection of this plane (3) with the line through the contact point
    # gives us the cutter contact point
    (ccp, l) = plane2.intersect_point(direction, cp)
    cp = padd(ccp, pmul(direction, -l))
    #cp = ccp.add(direction.mul(-l))
    return (ccp, cp, -l)

def intersect_circle_plane(center, radius, direction, triangle):
    # let n be the normal to the plane
    n = triangle.normal
    if pdot(n,direction) == 0:
        return (None, None, INFINITE)
    # project onto z=0
    n2 = (n[0], n[1], 0)
    if pnorm(n2) == 0:
        (cp, d) = triangle.plane.intersect_point(direction, center)
        ccp = psub(cp, pmul(direction, d))
        #ccp = cp.sub(direction.mul(d))
        return (ccp, cp, d)
    n2 = pnormalized(n2)
    #n2 = n2.normalized()
    # the cutter contact point is on the circle, where the surface normal is n
    ccp = padd(center, pmul(n2, -radius))
    #ccp = center.add(n2.mul(-radius))
    # intersect the plane with a line through the contact point
    (cp, d) = triangle.plane.intersect_point(direction, ccp)
    return (ccp, cp, d)

def intersect_circle_point(center, axis, radius, radiussq, direction, point):
    # take a plane through the base
    plane = Plane(center, axis)
    # intersect with line gives ccp
    (ccp, l) = plane.intersect_point(direction, point)
    # check if inside circle
    #if ccp and (center.sub(ccp).normsq < radiussq - epsilon):
    if ccp and (pnormsq(psub(center, ccp)) < radiussq - epsilon):
        return (ccp, point, -l)
    return (None, None, INFINITE)

def intersect_circle_line(center, axis, radius, radiussq, direction, edge):
    # make a plane by sliding the line along the direction (1)
    d = edge.dir
    if pdot(d, axis) == 0:
        if pdot(direction, axis) == 0:
            return (None, None, INFINITE)
        plane = Plane(center, axis)
        (p1, l) = plane.intersect_point(direction, edge.p1)
        (p2, l) = plane.intersect_point(direction, edge.p2)
        pc = Line(p1, p2).closest_point(center)
        d_sq = pnormsq(psub(pc, center))
        #d_sq = pc.sub(center).normsq
        if d_sq >= radiussq:
            return (None, None, INFINITE)
        a = sqrt(radiussq - d_sq)
        d1 = pdot(psub(p1, pc), d)
        #d1 = p1.sub(pc).dot(d)
        d2 = pdot(psub(p2, pc), d)
        #d2 = p2.sub(pc).dot(d)
        ccp = None
        cp = None
        if abs(d1) < a - epsilon:
            ccp = p1
            cp = psub(p1, pmul(direction, l))
            #cp = p1.sub(direction.mul(l))
        elif abs(d2) < a - epsilon:
            ccp = p2
            cp = psub(p2, pmul(direction, l))
            #cp = p2.sub(direction.mul(l))
        elif ((d1 < -a + epsilon) and (d2 > a - epsilon)) \
                or ((d2 < -a + epsilon) and (d1 > a - epsilon)):
            ccp = pc
            cp = psub(pc, pmul(direction, l))
            #cp = pc.sub(direction.mul(l))
        return (ccp, cp, -l)
    n = pcross(d, direction)
    #n = d.cross(direction)
    if pnorm(n)== 0:
        # no contact point, but should check here if circle *always* intersects
        # line...
        return (None, None, INFINITE)
    n = pnormalized(n)
    #n = n.normalized()
    # take a plane through the base
    plane = Plane(center, axis)
    # intersect base with line
    (lp, l) = plane.intersect_point(d, edge.p1)
    if not lp:
        return (None, None, INFINITE)
    # intersection of 2 planes: lp + \lambda v
    v = pcross(axis, n)
    #v = axis.cross(n)
    if pnorm(v) == 0:
        return (None, None, INFINITE)
    v = pnormalized(v)
    #v = v.normalized()
    # take plane through intersection line and parallel to axis
    n2 = pcross(v, axis)
    #n2 = v.cross(axis)
    if pnorm(n2) == 0:
        return (None, None, INFINITE)
    n2 = pnormalized(n2)
    #n2 = n2.normalized()
    # distance from center to this plane
    dist = pdot(n2, center) - pdot(n2, lp)
    #dist = n2.dot(center) - n2.dot(lp)
    distsq = dist * dist
    if distsq > radiussq - epsilon:
        return (None, None, INFINITE)
    # must be on circle
    dist2 = sqrt(radiussq - distsq)
    if pdot(d, axis) < 0:
        dist2 = -dist2
    ccp = psub(center, psub(pmul(n2, dist), pmul(v, dist2)))
    #ccp = center.sub(n2.mul(dist)).sub(v.mul(dist2))
    plane = Plane(edge.p1, pcross(pcross(d, direction), d))
    #plane = Plane(edge.p1, d.cross(direction).cross(d))
    (cp, l) = plane.intersect_point(direction, ccp)
    return (ccp, cp, l)

def intersect_sphere_plane(center, radius, direction, triangle):
    # let n be the normal to the plane
    n = triangle.normal
    if pdot(n, direction) == 0:
        return (None, None, INFINITE)
    # the cutter contact point is on the sphere, where the surface normal is n
    if pdot(n, direction) < 0:
        ccp = psub(center, pmul(n, radius))
        #ccp = center.sub(n.mul(radius))
    else:
        ccp = padd(center, pmul(n, radius))
        #ccp = center.add(n.mul(radius))
    # intersect the plane with a line through the contact point
    (cp, d) = triangle.plane.intersect_point(direction, ccp)
    return (ccp, cp, d)

def intersect_sphere_point(center, radius, radiussq, direction, point):
    # line equation
    # (1) x = p_0 + \lambda * d
    # sphere equation
    # (2) (x-x_0)^2 = R^2
    # (1) in (2) gives a quadratic in \lambda
    p0_x0 = psub(center, point)
    #p0_x0 = center.sub(point)
    a = pnormsq(direction)
    #a = direction.normsq
    b = 2 * pdot(p0_x0, direction)
    c = pnormsq(p0_x0) - radiussq
    d = b * b - 4 * a * c
    if d < 0:
        return (None, None, INFINITE)
    if a < 0:
        l = (-b + sqrt(d)) / (2 * a)
    else:
        l = (-b - sqrt(d)) / (2 * a)
    # cutter contact point
    ccp = padd(point, pmul(direction, -l))
    #ccp = point.add(direction.mul(-l))
    return (ccp, point, l)

def intersect_sphere_line(center, radius, radiussq, direction, edge):
    # make a plane by sliding the line along the direction (1)
    d = edge.dir
    n = pcross(n, direction)
    #n = d.cross(direction)
    if pnorm(n) == 0:
        # no contact point, but should check here if sphere *always* intersects
        # line...
        return (None, None, INFINITE)
    n = pnormalized(n)
    #n = n.normalized()

    # calculate the distance from the sphere center to the plane
    dist = - pdot(center, n) + pdot(edge.p1, n)
    #dist = - center.dot(n) + edge.p1.dot(n)
    if abs(dist) > radius - epsilon:
        return (None, None, INFINITE)
    # this gives us the intersection circle on the sphere

    # now take a plane through the edge and perpendicular to the direction (2)
    # find the center on the circle closest to this plane

    # which means the other component is perpendicular to this plane (2)
    n2 = pnormalized(pcross(n, d))
    #n2 = n.cross(d).normalized()

    # the contact point is on a big circle through the sphere...
    dist2 = sqrt(radiussq - dist * dist)

    # ... and it's on the plane (1)
    ccp = padd(center, padd(pmul(n, dist), pmul(n2, dist2)))
    #ccp = center.add(n.mul(dist)).add(n2.mul(dist2))

    # now intersect a line through this point with the plane (2)
    plane = Plane(edge.p1, n2)
    (cp, l) = plane.intersect_point(direction, ccp)
    return (ccp, cp, l)

def intersect_torus_plane(center, axis, majorradius, minorradius, direction,
        triangle):
    # take normal to the plane
    n = triangle.normal
    if pdot(n, direction) == 0:
        return (None, None, INFINITE)
    if pdot(n, axis) == 1:
        return (None, None, INFINITE)
    # find place on torus where surface normal is n
    b = pmul(n, -1)
    #b = n.mul(-1)
    z = axis
    a = psub(b, pmul(z,pdot(z, b)))
    #a = b.sub(z.mul(z.dot(b)))
    a_sq = pnormsq(a)
    if a_sq <= 0:
        return (None, None, INFINITE)
    a = pdiv(a, sqrt(a_sq))
    #a = a.div(sqrt(a_sq))
    ccp = padd(padd(center, pmul(a, majorradius)), pmul(b, minorradius))
    #ccp = center.add(a.mul(majorradius)).add(b.mul(minorradius))
    # find intersection with plane
    (cp, l) = triangle.plane.intersect_point(direction, ccp)
    return (ccp, cp, l)

def intersect_torus_point(center, axis, majorradius, minorradius, majorradiussq,
        minorradiussq, direction, point):
    dist = 0
    if (direction[0] == 0) and (direction[1] == 0):
        # drop
        minlsq = (majorradius - minorradius) ** 2
        maxlsq = (majorradius + minorradius) ** 2
        l_sq = (point[0]-center[0]) ** 2 + (point[1] - center[1]) ** 2
        if (l_sq < minlsq + epsilon) or (l_sq > maxlsq - epsilon):
            return (None, None, INFINITE)
        l = sqrt(l_sq)
        z_sq = minorradiussq - (majorradius - l) ** 2
        if z_sq < 0:
            return (None, None, INFINITE)
        z = sqrt(z_sq)
        ccp = (point[0], point[1], center[2] - z)
        dist = ccp[2] - point[2]
    elif direction[2] == 0:
        # push
        z = point[2] - center[2]
        if abs(z) > minorradius - epsilon:
            return (None, None, INFINITE)
        l = majorradius + sqrt(minorradiussq - z * z)
        n = pcross(axis, direction)
        #n = axis.cross(direction)
        d = pdot(n, point) - pdot(n, center)
        #d = n.dot(point) - n.dot(center)
        if abs(d) > l - epsilon:
            return (None, None, INFINITE)
        a = sqrt(l * l - d * d)
        ccp = padd(padd(center, pmul(n, d)), pmul(direction, a))
        #ccp = center.add(n.mul(d).add(direction.mul(a)))
        ccp = (ccp[0], ccp[1], point[2])
        #ccp.z = point.z
        dist = pdot(psub(point, ccp), direction)
        #dist = point.sub(ccp).dot(direction)
    else:
        # general case
        x = psub(point, center)
        #x = point.sub(center)
        v = pmul(direction, -1)
        #v = direction.mul(-1)
        x_x = pdot(x, x)
        #x_x = x.dot(x)
        x_v = pdot(x, v)
        #x_v = x.dot(v)
        x1 = (x[0], x[1], 0)
        #x1 = Point(x.x, x.y, 0)
        v1 = (v[0], v[1], 0)
        #v1 = Point(v.x, v.y, 0)
        x1_x1 = pdot(x1, x1)
        #x1_x1 = x1.dot(x1)
        x1_v1 = pdot(x1, v1)
        #x1_v1 = x1.dot(v1)
        v1_v1 = pdot(v1, v1)
        #v1_v1 = v1.dot(v1)
        R2 = majorradiussq
        r2 = minorradiussq
        a = 1.0
        b = 4 * x_v
        c = 2 * (x_x + 2 * x_v ** 2 + (R2 - r2) - 2 * R2 * v1_v1)
        d = 4 * (x_x * x_v + x_v * (R2 - r2) - 2 * R2 * x1_v1)
        e = (x_x) ** 2 + 2 * x_x * (R2 - r2) + (R2 - r2) ** 2 - 4 * R2 * x1_x1
        r = poly4_roots(a, b, c, d, e)
        if not r:
            return (None, None, INFINITE)
        else:
            l = min(r)
        ccp = padd(point, pmul(direction, -l))
        #ccp = point.add(direction.mul(-l))
        dist = l
    return (ccp, point, dist)

