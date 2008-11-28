from pycam.Utils.iterators import *

from pycam.Geometry.utils import *
from pycam.Geometry.Path import *
from pycam.Geometry.Point import *

DEBUG_POLYGONEXTRACTOR=False

class PolygonExtractor:
    CONTOUR=1
    MONOTONE=2
    def __init__(self, policy=MONOTONE):
        self.policy = policy
        self.hor_path_list = None
        self.ver_path_list = None
        self.merge_path_list = None
        self.dx = 1
        self.dy = 1

    def append(self, p):
        if (self.current_dir==0):
            self.curr_line.append(p)
        elif self.current_dir==1:
            # store as flipped
            self.curr_line.append(Point(p.y, p.x, p.z))

    def new_direction(self, dir):
        self.current_dir = dir
        self.all_path_list = []
        self.curr_path_list = []
        self.prev_line = []
        self.curr_line = []

    def end_direction(self):
        self.new_scanline()
        self.end_scanline()

        if DEBUG_POLYGONEXTRACTOR: print "%d paths" % len(self.all_path_list)
        for path in self.all_path_list:
            if DEBUG_POLYGONEXTRACTOR: print "%d:" % path.id,
            if DEBUG_POLYGONEXTRACTOR: print "%d ->" % path.top_join.id
            for point in path.points:
                if DEBUG_POLYGONEXTRACTOR: print "(%g,%g)" % (point.x, point.y),
            if DEBUG_POLYGONEXTRACTOR: print "->%d" % path.bot_join.id

        path_list = []
        while len(self.all_path_list)>0:
            p0 = self.all_path_list[0]
            for path in self.all_path_list:
                if path.id < p0.id:
                    p0 = path

            if DEBUG_POLYGONEXTRACTOR: print "linking %d" % p0.id
            self.all_path_list.remove(p0)

            p1 = p0.bot_join
            while True:
                if DEBUG_POLYGONEXTRACTOR: print "splice %d into %d" % (p1.id, p0.id)
                self.all_path_list.remove(p1)
                p1.reverse()
                p0.points += p1.points
                if p1.top_join == p0:
                    break;

                p2 = p1.top_join
                if DEBUG_POLYGONEXTRACTOR: print "splicing %d into %d" % (p2.id, p0.id)
                self.all_path_list.remove(p2)
                p0.points += p2.points
                p1 = p2.bot_join

            path_list.append(p0)

        if DEBUG_POLYGONEXTRACTOR: print "%d paths" % len(path_list)
        for path in path_list:
            if DEBUG_POLYGONEXTRACTOR: print "path %d(w=%d): " % (path.id, path.winding),
            for point in path.points:
                if DEBUG_POLYGONEXTRACTOR: print "(%g,%g)" % (point.x, point.y),
            if DEBUG_POLYGONEXTRACTOR: print

        if self.current_dir==0:
            self.hor_path_list = path_list
        elif self.current_dir==1:
            # flip back since we stored the points flipped (see add_point)
            for path in path_list:
                path.reverse()
                for point in path.points:
                    (point.x,point.y) = (point.y,point.x)

            self.ver_path_list = path_list

    def finish(self):
        if self.policy == PolygonExtractor.CONTOUR:
            if self.hor_path_list and self.ver_path_list:
                self.merge_path_lists()

    def new_scanline(self):
        self.curr_line = []

    def end_scanline(self):
        last = 0
        inside = False
        s = ""
        for point in self.curr_line:
            next = point.x
            if inside:
                s += "*" * int(next-last)
            else:
                s += " " * int(next-last)
            last = next
            inside = not inside
        if DEBUG_POLYGONEXTRACTOR: print s

        if DEBUG_POLYGONEXTRACTOR: print "active paths: ",
        for path in self.curr_path_list:
            if DEBUG_POLYGONEXTRACTOR: print "%d(%g,%g)" % (path.id, path.points[-1].x, path.points[-1].y),
        if DEBUG_POLYGONEXTRACTOR: print

        if DEBUG_POLYGONEXTRACTOR: print "prev points: ",
        for point in self.prev_line:
            if DEBUG_POLYGONEXTRACTOR: print "(%g,%g)" % (point.x, point.y),
        if DEBUG_POLYGONEXTRACTOR: print

        if DEBUG_POLYGONEXTRACTOR: print "active points: ",
        for point in self.curr_line:
            if DEBUG_POLYGONEXTRACTOR: print "(%g,%g)" % (point.x, point.y),
        if DEBUG_POLYGONEXTRACTOR: print

        prev_point = Iterator(self.prev_line)
        curr_point = Iterator(self.curr_line)
        curr_path = Iterator(self.curr_path_list)

        winding = 0
        while prev_point.remains()>0 or curr_point.remains()>0:
            if DEBUG_POLYGONEXTRACTOR: print "num_prev=", prev_point.remains(), ", num_curr=",curr_point.remains()
            if prev_point.remains()==0 and curr_point.remains()>=2:
                c0 = curr_point.next()
                c1 = curr_point.next()
                # new path starts
                p0 = Path()
                p0.winding = winding+1
                if DEBUG_POLYGONEXTRACTOR: print "new path %d(%g,%g)" % ( p0.id, c0.x, c0.y)
                p0.append(c0)
                self.curr_path_list.append(p0)
                p1 = Path()
                p1.winding = winding
                if DEBUG_POLYGONEXTRACTOR: print "new path %d(%g,%g)" % (p1.id, c1.x, c1.y)
                p1.append(c1)
                self.curr_path_list.append(p1)
                p0.top_join = p1
                p1.top_join = p0
                continue

            if prev_point.remains()>=2 and curr_point.remains()==0:
                #old path ends
                p0 = curr_path.takeNext()
                if DEBUG_POLYGONEXTRACTOR: print "end path %d" % p0.id
                self.all_path_list.append(p0)
                prev_point.next()
                p1 = curr_path.takeNext()
                if DEBUG_POLYGONEXTRACTOR: print "end path %d" % p1.id
                self.all_path_list.append(p1)
                prev_point.next()
                p0.bot_join = p1
                p1.bot_join = p0
                continue

            if prev_point.remains()>=2 and curr_point.remains()>=2:
                p0 = prev_point.peek(0)
                p1 = prev_point.peek(1)
                c0 = curr_point.peek(0)
                c1 = curr_point.peek(1)

                if DEBUG_POLYGONEXTRACTOR: print "overlap test: p0=%g p1=%g" % (p0.x, p1.x)
                if DEBUG_POLYGONEXTRACTOR: print "overlap test: c0=%g c1=%g" % (c0.x, c1.x)

                if c1.x < p0.x:
                    # new segment is completely to the left
                    # new path starts
                    s0 = Path()
                    if DEBUG_POLYGONEXTRACTOR: print "new path %d(%g,%g) w=%d" % (s0.id, c0.x, c0.y, winding+1)
                    s0.append(c0)
                    curr_path.insert(s0)
                    s1 = Path()
                    s0.winding = winding+1
                    s1.winding = winding
                    if DEBUG_POLYGONEXTRACTOR: print "new path %d(%g,%g) w=%d" % (s1.id, c1.x, c1.y, winding)
                    s1.append(c1)
                    curr_path.insert(s1)
                    curr_point.next()
                    curr_point.next()
                    s0.top_join = s1
                    s1.top_join = s0
                elif c0.x > p1.x:
                    # new segment is completely to the right
                    # old path ends
                    s0 = curr_path.takeNext()
                    if DEBUG_POLYGONEXTRACTOR: print "end path %d" % s0.id
                    self.all_path_list.append(s0)
                    prev_point.next()
                    s1 = curr_path.takeNext()
                    if DEBUG_POLYGONEXTRACTOR: print "end path %d" % s1.id
                    self.all_path_list.append(s1)
                    prev_point.next()
                    s0.bot_join = s1;
                    s1.bot_join = s0;
                    winding = s1.winding;
                else:
                    # new segment is overlapping
                    left_path = curr_path.next()
                    right_path = curr_path.peek()
                    left_point = c0
                    right_point = c1
                    winding = left_path.winding
                    curr_point.next()
                    prev_point.next()

                    overlap_p = True
                    overlap_c = True
                    while overlap_c or overlap_p:
                        overlap_p = False
                        overlap_c = False
                        # check for path joins
                        if prev_point.remains()>=2:
                            p2 = prev_point.peek(1)
                            if DEBUG_POLYGONEXTRACTOR: print "join test: p0=%g p1=%g p2=%g" % (p0.x, p1.x, p2.x)
                            if DEBUG_POLYGONEXTRACTOR: print "join test: c0=%g c1=%g" % (c0.x, c1.x)
                            if p2.x <= c1.x:
                                overlap_p = True
                                if self.policy == PolygonExtractor.CONTOUR:
                                    s0 = curr_path.takeNext()
                                    s1 = curr_path.takeNext()
                                    if curr_path.remains()>=1:
                                        right_path = curr_path.peek()
                                    self.all_path_list.append(s0)
                                    self.all_path_list.append(s1);
                                    if DEBUG_POLYGONEXTRACTOR: print "path %d joins %d" % (s0.id, s1.id)
                                    s0.bot_join = s1;
                                    s1.bot_join = s0;
                                elif self.policy == PolygonExtractor.MONOTONE:
                                    s0 = curr_path.takeNext()
                                    left_path.bot_join = s0
                                    s0.bot_join = left_path
                                    if DEBUG_POLYGONEXTRACTOR: print "path %d joins %d" % (left_path.id, s0.id)
                                    curr_path.remove(left_path)
                                    self.all_path_list.append(left_path)
                                    self.all_path_list.append(s0)
                                    s1 = curr_path.next()
                                    left_path = s1
                                    right_path = curr_path.peek()
                                prev_point.next()
                                prev_point.next()
                                winding = s1.winding
                                p0 = p2
                                if prev_point.remains()>=1:
                                    p1 = prev_point.peek(0)
                            else:
                                overlap_p = False

                        # check for path splits
                        if curr_point.remains()>=2:
                            c2 = curr_point.peek(1)
                            if DEBUG_POLYGONEXTRACTOR: print "split test: p0=%g p1=%g" % (p0.x, p1.x)
                            if DEBUG_POLYGONEXTRACTOR: print "split test: c0=%g c1=%g c2=%g" % (c0.x, c1.x, c2.x)
                            if c2.x <= p1.x:
                                overlap_c = True
                                s0 = Path()
                                s1 = Path()
                                s0.winding=winding+1
                                s1.winding=winding
                                s0.top_join = s1
                                s1.top_join = s0
                                if DEBUG_POLYGONEXTRACTOR: print "region split into %d and %d (w=%d)" %(s0.id, s1.id, winding+1)
                                curr_point.next()
                                c0 = curr_point.next()
                                if self.policy == PolygonExtractor.CONTOUR:
                                    s0.append(c1)
                                    curr_path.insert(s0)
                                    s1.append(c2)
                                    curr_path.insert(s1)
                                elif self.policy == PolygonExtractor.MONOTONE:
                                    s0.append(left_point)
                                    s1.append(c1)
                                    curr_path.insertBefore(s0)
                                    curr_path.insertBefore(s1)
                                    left_point = c2
                                if curr_point.remains()>=1:
                                    c1 = curr_point.peek(0)
                                    right_point = c1
                            else:
                                overlap_c = False

                    if DEBUG_POLYGONEXTRACTOR: print "add to path %d(%g,%g)" % (left_path.id, left_point.x, left_point.y)
                    left_path.append(left_point)
                    right_path.append(right_point)
                    if right_path == curr_path.peek():
                        curr_path.next()
                    if DEBUG_POLYGONEXTRACTOR: print "add to path %d(%g,%g)" % (right_path.id, right_point.x, right_point.y)
                    winding = right_path.winding;
                    prev_point.next()
                    curr_point.next()

        if DEBUG_POLYGONEXTRACTOR: print "active paths: ",
        for path in self.curr_path_list:
            if DEBUG_POLYGONEXTRACTOR: print "%d(%g,%g,w=%d)" % (path.id, path.points[-1].x, path.points[-1].y, path.winding),
        if DEBUG_POLYGONEXTRACTOR: print

        self.prev_line = self.curr_line

    def merge_path_lists(self):
        if self.hor_path_list:
            self.merge_path_list = self.hor_path_list
        else:
            self.merge_path_list = self.ver_path_list
        return
        # find matching path to merge with */
        for s0 in self.hor_path_list:

            if DEBUG_POLYGONEXTRACTOR: print "merging %d" % s0.id
            if DEBUG_POLYGONEXTRACTOR: print "s0=", s0

            #TODO: store/cache topmost point inside the path

            # find top of path to merge
            point_iter = Iterator(s0.points)
            top0 = CyclicIterator(point_iter.seq, point_iter.ind)
            min_x0 = top0.peek().x
            min_y0 = top0.peek().y
            while point_iter.remains()>0:
                point = point_iter.peek()
                if point and ((point.y<min_y0) or (point.y==min_y0 and point.x>min_x0)):
                    min_y0 = point.y
                    min_x0 = point.x
                    top0 = CyclicIterator(point_iter.seq, point_iter.ind)
                point_iter.next()
            if DEBUG_POLYGONEXTRACTOR: print "top0: x=", min_x0, "y=",min_y0, "p=",top0.peek().id
            # find matching path to merge with
            path_iter = Iterator(self.ver_path_list)
            while path_iter.remains()>0:
                s1 = path_iter.next()
                if DEBUG_POLYGONEXTRACTOR: print "trying %d" % s1.id
                if DEBUG_POLYGONEXTRACTOR: print "s1=", s1

                min_d = -1
                point_iter = Iterator(s1.points)
                top1 = None
                min_x1 = 0
                min_y1 = 0
                while point_iter.remains()>0:
                    point = point_iter.peek()
                    # check points in second quadrant   # TODO: if none found: check other quadrants
                    if point.y<=min_y0 and point.x<=min_x0:
                        d = sqr(point.x-min_x0)+sqr(point.y-min_y0)
                        if (d<min_d or top1==None):
                            min_x1 = point.x
                            min_y1 = point.y
                            min_d = d
                            top1 = CyclicIterator(point_iter.seq, point_iter.ind)
                    point_iter.next()

                if DEBUG_POLYGONEXTRACTOR: print "min_y0=%g min_y1=%g (d=%g)" % (min_y0, min_y1, min_d)
                if min_d < 0:
                    continue

                if DEBUG_POLYGONEXTRACTOR: print "top1: x=", min_x1, "y=",min_y1, "p=",top1.peek().id

                if (min_y1 >= min_y0-dy) and (min_y1 <= min_y0+dy) and (min_x1 >= min_x0-dx) and (min_x1 <= min_x0+dx):
                    # we have a potential match
                    if DEBUG_POLYGONEXTRACTOR: print "matched %d" % s1.id
                    if DEBUG_POLYGONEXTRACTOR: print "i0=%d i1=%d" % (top0.peek().id, top1.peek().id)
                    if DEBUG_POLYGONEXTRACTOR: print "s1=", s1
                    total = len(s0.points) + len(s1.points)
                    p = Path()
                    p.winding = s0.winding

                    p0 = top0.next()
                    p1 = top1.next()

                    next_p0 = top0.peek()
                    next_p1 = top1.peek()

                    if p0.y == next_p0.y:
                        while (p1.y < p0.y) and (next_p1.y < p0.y) and (p0.x <= p1.x) and (p1.x <= next_p0.x):
                            p1 = top1.next()
                            next_p1 = top1.peek()

                    if DEBUG_POLYGONEXTRACTOR: print "top0=%d: (%g,%g)" % (p0.id, p0.x, p0.y)
                    if DEBUG_POLYGONEXTRACTOR: print "top1=%d: (%g,%g)" % (p1.id, p1.x, p1.y)

                    last = p0;

                    pathlen = 0
                    while pathlen < total:
                        next_p0 = top0.peek()
                        next_p1 = top1.peek()

                        pathlen = len(p.points)

                        if DEBUG_POLYGONEXTRACTOR: print "last=%d: (%g, %g)" % (last.id, last.x, last.y)
                        if DEBUG_POLYGONEXTRACTOR: print "p0: %d(%g,%g)\t" % (p0.id, p0.x, p0.y),
                        if DEBUG_POLYGONEXTRACTOR: print "next_p0: %d(%g,%g)" % (next_p0.id, next_p0.x, next_p0.y)
                        if DEBUG_POLYGONEXTRACTOR: print "p1: %d(%g,%g)\t" % (p1.id, p1.x, p1.y),
                        if DEBUG_POLYGONEXTRACTOR: print "next_p1: %d(%g,%g)" % (next_p1.id, next_p1.x, next_p1.y)
                        if DEBUG_POLYGONEXTRACTOR: print "|p1-last|=%g |p0-last|=%g" % (sqr(p1.x - last.x) + sqr(p1.y - last.y), sqr(p0.x - last.x) + sqr(p0.y - last.y))
                        if sqr(p1.x - last.x) + sqr(p1.y - last.y) < sqr(p0.x - last.x) + sqr(p0.y - last.y):
                            if DEBUG_POLYGONEXTRACTOR: print "0: p1=%d: (%g,%g)" % (p1.id, p1.x, p1.y)
                            p.append(p1)
                            last = p1
                            p1 = top1.next()
                            continue
                        else:
                            if DEBUG_POLYGONEXTRACTOR: print "1: p0=%d: (%g,%g)" % (p0.id, p0.x, p0.y)
                            p.append(p0)
                            last = p0
                            p0 = top0.next()
                            continue;

                        if pathlen == len(p):
                            if DEBUG_POLYGONEXTRACTOR: print "failed: size=%d total=%d" %(len(p), total)
                            p = None
                            break

                    if p:
                        self.merge_path_list.append(p)
                        if DEBUG_POLYGONEXTRACTOR: print "done: size=%d total=%d" % (len(p.points), total)
                        break
