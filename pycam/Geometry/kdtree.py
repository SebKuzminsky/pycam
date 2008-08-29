#!/usr/bin/env python

import math

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


class kd_tree:
    id = 0

    def __repr__(self):
        if self.bucket:
            return "(#%d)" % (len(self.nodes))
        else:
            return "(%f<=%s,%d:%f,%s<=%f)" % (self.minval,self.lo, self.cutdim,self.cutval,self.hi,self.maxval)

    def to_mged(self, minx, maxx, miny, maxy):
        s = ""
        if self.bucket:
            s += "in kdtree_%d arb8 " % self.id
            s += " %f %f %f " % (minx, miny, 0)
            s += " %f %f %f " % (maxx, miny, 0)
            s += " %f %f %f " % (maxx, maxy, 0)
            s += " %f %f %f " % (minx, maxy, 0)
            s += " %f %f %f " % (minx, miny, 10)
            s += " %f %f %f " % (maxx, miny, 10)
            s += " %f %f %f " % (maxx, maxy, 10)
            s += " %f %f %f" % (minx, maxy, 10)
            s += "\n"
        else:
            if True: # show bounding box
                if self.cutdim == 0 or self.cutdim == 2:
                    s += self.lo.to_mged(self.minval,self.cutval,miny,maxy)
                    s += self.hi.to_mged(self.cutval,self.maxval,miny,maxy)
                elif self.cutdim == 1 or self.cutdim == 3:
                    s += self.lo.to_mged(minx,maxx,self.minval,self.cutval)
                    s += self.hi.to_mged(minx,maxx,self.cutval,self.maxval)
            else:    # show partitions
                if self.cutdim == 0 or self.cutdim == 2:
                    s += self.lo.to_mged(minx,self.cutval,miny,maxy)
                    s += self.hi.to_mged(self.cutval,maxx,miny,maxy)
                elif self.cutdim == 1 or self.cutdim == 3:
                    s += self.lo.to_mged(minx,maxx,miny,self.cutval)
                    s += self.hi.to_mged(minx,maxx,self.cutval,maxy)
        return s

    def __init__(self, nodes, cutoff, cutoff_distance):
        self.id = kd_tree.id
        kd_tree.id += 1
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
                self.lo = kd_tree(nodes[0:median], cutoff, cutoff_distance)
                self.hi = kd_tree(nodes[median:], cutoff, cutoff_distance)




