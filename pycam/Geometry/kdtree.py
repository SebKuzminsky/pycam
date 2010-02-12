#!/usr/bin/env python

import math
import pycam

try:
    import OpenGL.GL as GL
    GL_enabled = True
except:
    GL_enabled = False

class Node:
    def __repr__(self):
        s = "";
        for i in range(0,len(self.bound)):
            s += "%g : " % (self.bound[i])
        return s

def find_max_spread(nodes):
    minval = []
    maxval = []
    n = nodes[0]
    numdim = len(n.bound)
    for b in n.bound:
        minval.append(b)
        maxval.append(b)
    for n in nodes:
        for j in range(0, numdim):
            minval[j] = min(minval[j], n.bound[j])
            maxval[j] = max(maxval[j], n.bound[j])
    maxspreaddim = 0
    maxspread = maxval[0]-minval[0]
    for i in range(1,numdim):
        spread = maxval[i]-minval[i]
        if spread > maxspread:
            maxspread = spread
            maxspreaddim = i
    return (maxspreaddim, maxspread)


class kdtree:
    id = 0

    def __repr__(self):
        if self.bucket:
            if True:
                return "(#%d)" % (len(self.nodes))
            else:
                s = "("
                for n in self.nodes:
                    if (len(s))>1:
                        s += ","
                        s += str(n.p.id)
                        s += ")"
                return s
        else:
            return "(%s,%d:%g,%s)" % (self.lo,self.cutdim,self.cutval,self.hi)

    def to_OpenGL(self,minx,maxx,miny,maxy,minz,maxz):
        if not GL_enabled:
            return
        if self.bucket:
            GL.glBegin(GL.GL_LINES)
            GL.glVertex3d(minx,miny,minz)
            GL.glVertex3d(minx,miny,maxz)
            GL.glVertex3d(minx,maxy,minz)
            GL.glVertex3d(minx,maxy,maxz)
            GL.glVertex3d(maxx,miny,minz)
            GL.glVertex3d(maxx,miny,maxz)
            GL.glVertex3d(maxx,maxy,minz)
            GL.glVertex3d(maxx,maxy,maxz)

            GL.glVertex3d(minx,miny,minz)
            GL.glVertex3d(maxx,miny,minz)
            GL.glVertex3d(minx,maxy,minz)
            GL.glVertex3d(maxx,maxy,minz)
            GL.glVertex3d(minx,miny,maxz)
            GL.glVertex3d(maxx,miny,maxz)
            GL.glVertex3d(minx,maxy,maxz)
            GL.glVertex3d(maxx,maxy,maxz)

            GL.glVertex3d(minx,miny,minz)
            GL.glVertex3d(minx,maxy,minz)
            GL.glVertex3d(maxx,miny,minz)
            GL.glVertex3d(maxx,maxy,minz)
            GL.glVertex3d(minx,miny,maxz)
            GL.glVertex3d(minx,maxy,maxz)
            GL.glVertex3d(maxx,miny,maxz)
            GL.glVertex3d(maxx,maxy,maxz)
            GL.glEnd()
        elif self.dim==6:
            if self.cutdim == 0 or self.cutdim == 2:
                self.lo.to_OpenGL(minx,self.cutval,miny,maxy,minz,maxz)
                self.hi.to_OpenGL(self.cutval,maxx,miny,maxy,minz,maxz)
            elif self.cutdim == 1 or self.cutdim == 3:
                self.lo.to_OpenGL(minx,maxx,miny,self.cutval,minz,maxz)
                self.hi.to_OpenGL(minx,maxx,self.cutval,maxy,minz,maxz)
            elif self.cutdim == 4 or self.cutdim == 5:
                self.lo.to_OpenGL(minx,maxx,miny,maxx,minz,self.cutval)
                self.hi.to_OpenGL(minx,maxx,miny,maxy,self.cutval,maxz)
        elif self.dim==4:
            if self.cutdim == 0 or self.cutdim == 2:
                self.lo.to_OpenGL(minx,self.cutval,miny,maxy,minz,maxz)
                self.hi.to_OpenGL(self.cutval,maxx,miny,maxy,minz,maxz)
            elif self.cutdim == 1 or self.cutdim == 3:
                self.lo.to_OpenGL(minx,maxx,miny,self.cutval,minz,maxz)
                self.hi.to_OpenGL(minx,maxx,self.cutval,maxy,minz,maxz)
        elif self.dim==3:
            if self.cutdim == 0:
                self.lo.to_OpenGL(minx,self.cutval,miny,maxy,minz,maxz)
                self.hi.to_OpenGL(self.cutval,maxx,miny,maxy,minz,maxz)
            elif self.cutdim == 1:
                self.lo.to_OpenGL(minx,maxx,miny,self.cutval,minz,maxz)
                self.hi.to_OpenGL(minx,maxx,self.cutval,maxy,minz,maxz)
            elif self.cutdim == 2:
                self.lo.to_OpenGL(minx,maxx,miny,maxy,minz,self.cutval)
                self.hi.to_OpenGL(minx,maxx,miny,maxy,self.cutval,maxz)

    def __init__(self, nodes, cutoff, cutoff_distance):
        self.id = kdtree.id
        self.bucket = False
        if nodes and len(nodes)>0:
            self.dim = len(nodes[0].bound)
        else:
            self.dim = 0
        kdtree.id += 1
        self.cutoff = cutoff
        self.cutoff_distance = cutoff_distance

        if (len(nodes)<=self.cutoff):
            self.bucket = True
            self.nodes = nodes
        else:
            (cutdim,spread) = find_max_spread(nodes)
            if spread <= self.cutoff_distance:
                self.bucket = True
                self.nodes = nodes
            else:
                self.bucket = False
                self.cutdim = cutdim
                nodes.sort(cmp=lambda x,y:cmp(x.bound[cutdim],y.bound[cutdim]))
                median = len(nodes)/2
                self.minval = nodes[0].bound[cutdim]
                self.maxval = nodes[-1].bound[cutdim]
                self.cutval = nodes[median].bound[cutdim]
                self.lo = kdtree(nodes[0:median], cutoff, cutoff_distance)
                self.hi = kdtree(nodes[median:], cutoff, cutoff_distance)

    def dist(self, n1, n2):
        dist = 0
        for i in range(0,len(n1.bound)):
            d = n1.bound[i]-n2.bound[i]
            dist += d*d
        return dist

    def nearest_neighbor(self, node, dist=dist):
        if self.bucket:
            if len(self.nodes)==0:
                return (None, 0)
            best = self.nodes[0]
            bestdist = self.dist(node, best)
            for n in self.nodes:
                d = self.dist(n,node)
                if d<bestdist:
                    best = n
                    bestdist = d
            return (best,bestdist)
        else:
            if node.bound[self.cutdim] <= self.cutval:
                (best,bestdist) = self.lo.nearest_neighbor(node, dist)
                if bestdist > self.cutval - best.bound[self.cutdim]:
                    (best2,bestdist2) = self.hi.nearest_neighbor(node, dist)
                    if bestdist2<bestdist:
                        return (best2,bestdist2)
                return (best,bestdist)
            else:
                (best,bestdist) = self.hi.nearest_neighbor(node, dist)
                if bestdist > best.bound[self.cutdim] - self.cutval:
                    (best2,bestdist2) = self.lo.nearest_neighbor(node, dist)
                    if bestdist2<bestdist:
                        return (best2,bestdist2)
                return (best,bestdist)
    
    def insert(self, node):
        if self.dim==0:
            self.dim = len(node.bound)

        if self.bucket:
            self.nodes.append(node)
            if (len(self.nodes)>self.cutoff):
                self.bucket = False
                (cutdim,spread) = find_max_spread(self.nodes)
                self.cutdim = cutdim
                self.nodes.sort(cmp=lambda x,y:cmp(x.bound[cutdim],y.bound[cutdim]))
                median = len(self.nodes)/2
                self.minval = self.nodes[0].bound[cutdim]
                self.maxval = self.nodes[-1].bound[cutdim]
                self.cutval = self.nodes[median].bound[cutdim]
                self.lo = kdtree(self.nodes[0:median], self.cutoff, self.cutoff_distance)
                self.hi = kdtree(self.nodes[median:], self.cutoff, self.cutoff_distance)
        else:
            if node.bound[self.cutdim] <= self.cutval:
                self.lo.insert(node)
            else:
                self.hi.insert(node)
        

