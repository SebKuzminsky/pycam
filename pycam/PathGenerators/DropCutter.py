from pycam.PathProcessors import *
from pycam.Geometry import *
from pycam.Geometry.intersection import intersect_lines
from pycam.Geometry.utils import INFINITE
import math
import sys


class Dimension:
    def __init__(self, start, end):
        self.start = float(start)
        self.end = float(end)
        self.min = float(min(start, end))
        self.max = float(max(start, end))
        self.downward = start > end
        self.value = 0.0

    def check_bounds(self, value=None, tolerance=None):
        if value is None:
            value = self.value
        if tolerance is None:
            return (value >= self.min) and (value <= self.max)
        else:
            return (value > self.min - tolerance) and (value < self.max + tolerance)

    def shift(self, distance):
        if self.downward:
            self.value -= distance
        else:
            self.value += distance

    def set(self, value):
        self.value = float(value)

    def get(self):
        return self.value


class DropCutter:

    def __init__(self, cutter, model, PathProcessor=None, physics=None, safety_height=INFINITE):
        self.cutter = cutter
        self.model = model
        self.processor = PathProcessor
        self.physics = physics
        self.safety_height = safety_height
        # used for the non-ode code
        self._triangle_last = None
        self._cut_last = None
        # remember if we already reported an invalid boundary
        self._boundary_warning_already_shown = False

    def GenerateToolPath(self, minx, maxx, miny, maxy, z0, z1, d0, d1, direction, draw_callback=None):
        if self.processor:
            pa = self.processor
        else:
            pa = PathAccumulator()

        dim_x = Dimension(minx, maxx)
        dim_y = Dimension(miny, maxy)
        dim_height = Dimension(z1, z0)
        dims = [None, None, None]
        # map the scales according to the order of direction
        if direction == 0:
            x, y = 0, 1
            dim_attrs = ["x", "y"]
        else:
            y, x = 0, 1
            dim_attrs = ["y", "x"]
        # order of the "dims" array: first dimension, second dimension
        dims[x] = dim_x
        dims[y] = dim_y

        dim_height.set(dim_height.start)
        pa.new_direction(direction)
        dims[1].set(dims[1].start)

        finished_plane = False
        self._boundary_warning_already_shown = False
        last_outer_loop = False

        num_of_lines = math.ceil((dims[1].max - dims[1].min) / d1)
        current_line = 0

        while not finished_plane:
            last_inner_loop = False
            finished_line = False
            dims[0].set(dims[0].start)
            pa.new_scanline()
            self._triangle_last = None
            self._cut_last = None

            if draw_callback and draw_callback(text="DropCutter: processing line %d/%d" \
                        % (current_line, num_of_lines),
                        percent=(100.0 * current_line / num_of_lines)):
                # cancel requested
                finished_plane = True

            while not finished_line:
                if self.physics:
                    points = self.get_max_height_with_ode(dims[x], dims[y], dim_height, order=dim_attrs[:])
                else:
                    points = self.get_max_height_manually(dims[x], dims[y], dim_height, order=dim_attrs[:])

                for next_point in points:
                    pa.append(next_point)
                self.cutter.moveto(next_point)
                if draw_callback and draw_callback():
                    finished_line = True

                dims[0].shift(d0)

                # make sure, that the we also handle the outmost border of the bounding box
                if dims[0].check_bounds(tolerance=d0):
                    if not dims[0].check_bounds() and not last_inner_loop:
                        dims[0].set(dims[0].end)
                        last_inner_loop = True
                else:
                    finished_line = True

            pa.end_scanline()
            dims[1].shift(d1)

            # make sure, that the we also handle the outmost border of the bounding box
            if dims[1].check_bounds(tolerance=d1):
                if not dims[1].check_bounds() and not last_outer_loop:
                    dims[1].set(dims[1].end)
                    last_outer_loop = True
            else:
                finished_plane = True

            # update progress
            current_line += 1

        pa.end_direction()

        pa.finish()
        return pa.paths

    def get_max_height_with_ode(self, x, y, dim_height, order=None):
        low, high = dim_height.end, dim_height.start
        trip_start = 20
        safe_z = None
        # check if the full step-down would be ok
        self.physics.set_drill_position((x.get(), y.get(), dim_height.end))
        if self.physics.check_collision():
            # there is an object between z1 and z0 - we need more=None loops
            trips = trip_start
        else:
            # no need for further collision detection - we can go down the whole range z1..z0
            trips = 0
            safe_z = dim_height.end
        while trips > 0:
            current_z = (low + high)/2.0
            self.physics.set_drill_position((x.get(), y.get(), current_z))
            if self.physics.check_collision():
                low = current_z
            else:
                high = current_z
                safe_z = current_z
            trips -= 1
            #current_z -= dz
        if safe_z is None:
            # no safe position was found - let's check the upper bound
            self.physics.set_drill_position((x.get(), y.get(), dim_height.start))
            if self.physics.check_collision():
                # the object fills the whole range of z0..z1 - we should issue a warning
                next_point = Point(x.get(), y.get(), self.safety_height)
                if not self._boundary_warning_already_shown:
                    print >>sys.stderr, "WARNING: DropCutter exceed the height" \
                            + " of the boundary box: using a safe height " \
                            + "instead. This warning is reported only once."
                    self._boundary_warning_already_shown = True
            else:
                next_point = Point(x.get(), y.get(), dim_height.start)
        else:
            next_point = Point(x.get(), y.get(), safe_z)
        return [next_point]

    def get_max_height_manually(self, x, y, dim_height, order=None):
        result = []
        if order is None:
            order = ["x", "y"]
        p = Point(x.get(), y.get(), dim_height.get())
        height_max = None
        cut_max = None
        triangle_max = None
        self.cutter.moveto(p)
        box_x_min = p.x - self.cutter.radius
        box_x_max = p.x + self.cutter.radius
        box_y_min = p.y - self.cutter.radius
        box_y_max = p.y + self.cutter.radius
        box_z_min = dim_height.end
        box_z_max = self.safety_height
        triangles = self.model.triangles(box_x_min, box_y_min, box_z_min, box_x_max, box_y_max, box_z_max)
        for t in triangles:
            if t.normal().z < 0: continue;
            cut = self.cutter.drop(t)
            if cut and (cut.z > height_max or height_max is None):
                height_max = cut.z
                cut_max = cut
                triangle_max = t
        # don't do a complete boundary check for the height
        # this avoids zero-cuts for models that exceed the bounding box height
        if not cut_max or cut_max.z < dim_height.min:
            cut_max = Point(x.get(), y.get(), dim_height.end)
        if self._cut_last and ((triangle_max and not self._triangle_last) or (self._triangle_last and not triangle_max)):
            if dim_height.check_bounds(self._cut_last.z):
                result.append(Point(self._cut_last.x, self._cut_last.y, cut_max.z))
            else:
                result.append(Point(cut_max.x, cut_max.y, self._cut_last.z))
        elif (triangle_max and self._triangle_last and self._cut_last and cut_max) and (triangle_max != self._triangle_last):
            nl = range(3)
            nl[0] = -getattr(self._triangle_last.normal(), order[0])
            nl[2] = self._triangle_last.normal().z
            nm = range(3)
            nm[0] = -getattr(triangle_max.normal(), order[0])
            nm[2] = triangle_max.normal().z
            last = range(3)
            last[0] = getattr(self._cut_last, order[0])
            last[2] = self._cut_last.z
            mx = range(3)
            mx[0] = getattr(cut_max, order[0])
            mx[2] = cut_max.z
            c = range(3)
            (c[0], c[2]) = intersect_lines(last[0], last[2], nl[0], nl[2], mx[0], mx[2], nm[0], nm[2])
            if c[0] and last[0] < c[0] and c[0] < mx[0] and (c[2] > last[2] or c[2] > mx[2]):
                c[1] = getattr(self._cut_last, order[1])
                if c[2]<dim_height.end-10 or c[2]>dim_height.start+10:
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

        self._cut_last = cut_max
        self._triangle_last = triangle_max
        return result

