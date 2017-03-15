# -*- coding: utf-8 -*-
"""
Copyright 2009-2010 Lode Leroy

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

import ctypes

try:
    import OpenGL.GL as GL
    from OpenGL.GL.pointers import glIndexPointers, glNormalPointerf, glVertexPointerf
    GL_enabled = True
except ImportError:
    GL_enabled = False


EPSILON = 1e-8

NUM_PER_CELL_X = 10
NUM_PER_CELL_Y = 10
NUM_CELL_X = 0
NUM_CELL_Y = 0


class ZBufferItem(object):
    def __init__(self, z=0.0):
        self.z = float(z)
        self.changed = True
        self.list = -1


class ZCellItem(object):
    def __init__(self):
        self.list = -1
        self.array = None


class ZBuffer(object):
    def __init__(self, minx, maxx, xres, miny, maxy, yres, minz, maxz):
        global NUM_CELL_X, NUM_CELL_Y
        self.minx = float(minx)
        self.maxx = float(maxx)
        self.miny = float(miny)
        self.maxy = float(maxy)
        self.minz = float(minz)
        self.maxz = float(maxz)
        self.xres = int(xres)
        self.yres = int(yres)
        self.changed = True

        NUM_CELL_X = self.xres / NUM_PER_CELL_X
        NUM_CELL_Y = self.yres / NUM_PER_CELL_Y

        self.x = [0.0] * self.xres
        for i in range(0, self.xres):
            self.x[i] = self.minx+(i * (self.maxx-self.minx)/self.xres)
        self.y = [0.0] * self.yres
        for i in range(0, self.yres):
            self.y[i] = self.miny+(i * (self.maxy-self.miny)/self.yres)
        self.buf = [[]] * self.yres
        for y in range(0, self.yres):
            self.buf[y] = [None] * self.xres
            for x in range(0, self.xres):
                self.buf[y][x] = ZBufferItem(self.minz)

        self.list = [[]] * self.yres
        for y in range(0, self.yres):
            self.list[y] = [None] * self.xres
            for x in range(0, self.xres):
                self.list[y][x] = -1

        self.cell = [None] * NUM_CELL_Y
        for y in range(0, NUM_CELL_Y):
            self.cell[y] = [None] * NUM_CELL_X
            for x in range(0, NUM_CELL_X):
                self.cell[y][x] = ZCellItem()

    def add_triangles(self, triangles):
        for t in triangles:
            self.add_triangle(t)

    def add_triangle(self, t):
        minx = int((t.minx - self.minx) / (self.maxx - self.minx) * self.xres) - 1
        maxx = int((t.maxx - self.minx) / (self.maxx - self.minx) * self.xres) + 1
        miny = int((t.miny - self.miny) / (self.maxy - self.miny) * self.yres) - 1
        maxy = int((t.maxy - self.miny) / (self.maxy - self.miny) * self.yres) + 2
        if minx < 0:
            minx = 0
        if maxx > self.xres - 1:
            maxx = self.xres - 1
        if miny < 0:
            miny = 0
        if maxy > self.yres - 1:
            maxy = self.yres - 1

        for y in range(miny, maxy):
            py = self.y[y]
            for x in range(minx, maxx):
                px = self.x[x]
                v0x = t.p3[0] - t.p1[0]
                v0y = t.p3[1] - t.p1[1]
                v1x = t.p2[0] - t.p1[0]
                v1y = t.p2[1] - t.p1[1]
                v2x = px - t.p1[0]
                v2y = py - t.p1[1]
                dot00 = v0x*v0x + v0y*v0y
                dot01 = v0x*v1x + v0y*v1y
                dot02 = v0x*v2x + v0y*v2y
                dot11 = v1x*v1x + v1y*v1y
                dot12 = v1x*v2x + v1y*v2y
                invDenom = 1 / (dot00 * dot11 - dot01 * dot01)
                u = (dot11 * dot02 - dot01 * dot12) * invDenom
                v = (dot00 * dot12 - dot01 * dot02) * invDenom
                if (u >= -EPSILON) and (v >= -EPSILON) and (u + v <= 1-EPSILON):
                    v0z = t.p3[2] - t.p1[2]
                    v1z = t.p2[2] - t.p1[2]
                    pz = t.p1[2] + v0z * u + v1z * v
                    if pz > self.buf[y][x].z:
                        self.buf[y][x].z = pz
                        self.buf[y+0][x+0].changed = True
                        self.buf[y+0][x+1].changed = True
                        self.buf[y+1][x+0].changed = True
                        self.buf[y+1][x+1].changed = True
                        self.changed = True

    def add_cutter(self, c):
        cx = c.location[0]
        cy = c.location[1]
        rsq = c.radiussq
        minx = int((c.minx - self.minx) / (self.maxx - self.minx) * self.xres) - 1
        maxx = int((c.maxx - self.minx) / (self.maxx - self.minx) * self.xres) + 1
        miny = int((c.miny - self.miny) / (self.maxy - self.miny) * self.yres) - 1
        maxy = int((c.maxy - self.miny) / (self.maxy - self.miny) * self.yres) + 1
        if minx < 0:
            minx = 0
        if maxx < 0:
            maxx = 0
        if minx > self.xres - 1:
            minx = self.xres - 1
        if maxx > self.xres - 1:
            maxx = self.xres - 1
        if miny < 0:
            miny = 0
        if maxy < 0:
            maxy = 0
        if maxy > self.yres - 1:
            maxy = self.yres - 1
        if miny > self.yres - 1:
            miny = self.yres - 1
        p = (0, 0, 0)
        zaxis = (0, 0, -1)

        for y in range(miny, maxy):
            py = self.y[y]
            p = (p[0], py, p[2])
            for x in range(minx, maxx):
                px = self.x[x]
                p = (px, p[1], p[2])
                if (px - cx) * (px - cx) + (py - cy) * (py - cy) <= rsq + EPSILON:
                    (cl, ccp, cp, l) = c.intersect_point(zaxis, p)
                    if ccp:
                        pz = l
                        if pz < self.buf[y][x].z:
                            self.buf[y][x].z = pz
                            self.buf[y+0][x+0].changed = True
                            self.buf[y+0][x+1].changed = True
                            self.buf[y+1][x+0].changed = True
                            self.buf[y+1][x+1].changed = True
                            self.changed = True

    def to_OpenGL(self):
        if GL_enabled:
            self.to_OpenGL_6()
        self.changed = False

    def normal(self, z0, z1, z2):
        nx = 1.0 / self.xres
        ny = 1.0 / self.yres
        nz = 1.0 / (self.maxz - self.minz)
        return (-ny * (z1 - z0) * nz / nx, -nx * (z2 - z1) * nz / ny, nx * ny / nz * 100)

    # use display list with vertex and normal and index buffers per cell
    # (cell = group of quads)
    def to_OpenGL_6(self):
        num_cell_x = NUM_CELL_X
        num_cell_y = NUM_CELL_Y

        dy = self.yres/num_cell_y
        if dy < 2:
            num_cell_y = 1
            dy = self.yres
        dx = self.xres/num_cell_x
        if dx < 2:
            num_cell_x = 1
            dx = self.xres

        GL.glEnableClientState(GL.GL_INDEX_ARRAY)
        GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
        GL.glEnableClientState(GL.GL_NORMAL_ARRAY)

        for y in range(num_cell_y):
            y0 = y * dy
            y1 = y0 + dy + 1
            if y1 > self.yres:
                y1 = self.yres
            for x in range(num_cell_x):
                x0 = x * dx
                x1 = x0 + dx + 1
                if x1 > self.xres:
                    x1 = self.xres

                changed = False

                if self.changed:
                    for yi in range(y0, y1 - 1):
                        for xi in range(x0, x1 - 1):
                            if self.buf[yi][xi].changed:
                                changed = True
                                break

                if changed:
                    if self.cell[y][x].list == -1:
                        self.cell[y][x].list = GL.glGenLists(1)
                        self.cell[y][x].vertex = (ctypes.c_float * 3 * ((y1-y0) * (x1 - x0)))()
                        self.cell[y][x].normal = (ctypes.c_float * 3 * ((y1-y0) * (x1 - x0)))()
                        self.cell[y][x].index = (ctypes.c_ushort
                                                 * (4 * (y1 - y0 - 1) * (x1 - x0 - 1)))()
                    glIndexPointers(self.cell[y][x].index)
                    glVertexPointerf(self.cell[y][x].vertex)
                    glNormalPointerf(self.cell[y][x].normal)

                    GL.glNewList(self.cell[y][x].list, GL.GL_COMPILE)
                    idx = 0
                    for yi in range(y0, y1):
                        for xi in range(x0, x1):
                            self.buf[yi][xi].changed = False
                            self.cell[y][x].vertex[idx][0] = self.x[xi]
                            self.cell[y][x].vertex[idx][1] = self.y[yi]
                            self.cell[y][x].vertex[idx][2] = self.buf[yi][xi].z

                            if (xi == self.xres - 1) or (yi == self.yres - 1):
                                n = self.normal(self.buf[yi-1][xi-1].z, self.buf[yi-1][xi].z,
                                                self.buf[yi][xi-1].z)
                            else:
                                n = self.normal(self.buf[yi][xi].z, self.buf[yi][xi+1].z,
                                                self.buf[yi+1][xi].z)
                            self.cell[y][x].normal[idx][0] = n[0]
                            self.cell[y][x].normal[idx][1] = n[1]
                            self.cell[y][x].normal[idx][2] = n[2]

                            idx += 1

                    idx = 0
                    for yi in range(y0, y1 - 1):
                        for xi in range(x0, x1 - 1):
                            self.cell[y][x].index[idx + 0] = ((yi - y0 + 0)
                                                              * (x1 - x0) + (xi - x0 + 0))
                            self.cell[y][x].index[idx + 1] = ((yi - y0 + 1)
                                                              * (x1 - x0) + (xi - x0 + 0))
                            self.cell[y][x].index[idx + 2] = ((yi - y0 + 1)
                                                              * (x1 - x0) + (xi - x0 + 1))
                            self.cell[y][x].index[idx + 3] = ((yi - y0 + 0)
                                                              * (x1 - x0) + (xi - x0 + 1))
                            idx += 4

                    GL.glDrawElements(GL.GL_QUADS, idx, GL.GL_UNSIGNED_SHORT,
                                      self.cell[y][x].index)
                    GL.glEndList()
                GL.glCallList(self.cell[y][x].list)

        GL.glDisableClientState(GL.GL_VERTEX_ARRAY)
        GL.glDisableClientState(GL.GL_NORMAL_ARRAY)
        GL.glDisableClientState(GL.GL_INDEX_ARRAY)
