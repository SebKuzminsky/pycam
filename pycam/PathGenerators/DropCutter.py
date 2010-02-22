from pycam.PathProcessors import *
from pycam.Geometry import *
from pycam.Geometry.utils import *
from pycam.Geometry.intersection import intersect_lines

class Dimension:
    def __init__(self, start, end):
        self.start = float(start)
        self.end = float(end)
        self._min = float(min(start, end))
        self._max = float(max(start, end))
        self.downward = start > end
        self.value = 0.0

    def check_bounds(self, value=None):
        if value is None:
            value = self.value
        return (value >= self._min) and (value <= self._max)

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

    def __init__(self, cutter, model, PathProcessor=None, physics=None):
        self.cutter = cutter
        self.model = model
        self.processor = PathProcessor
        self.physics = physics

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
        while dims[1].check_bounds():
            dims[0].set(dims[0].start)
            pa.new_scanline()
            t_last = None
            while dims[0].check_bounds():
                p = Point(dims[x].get(), dims[y].get(), dim_height.get())

                low, high = z0, z1
                trip_start = 20
                safe_z = None
                # check if the full step-down would be ok
                self.physics.set_drill_position((dims[x].get(), dims[y].get(), z0))
                if self.physics.check_collision():
                    # there is an object between z1 and z0 - we need more loops
                    trips = trip_start
                else:
                    # no need for further collision detection - we can go down the whole range z1..z0
                    trips = 0
                    safe_z = z0
                while trips > 0:
                    current_z = (low + high)/2.0
                    self.physics.set_drill_position((dims[x].get(), dims[y].get(), current_z))
                    if self.physics.check_collision():
                        low = current_z
                    else:
                        high = current_z
                        safe_z = current_z
                    trips -= 1
                    #current_z -= dz
                if safe_z is None:
                    # no safe position was found - let's check the upper bound
                    self.physics.set_drill_position((dims[x].get(), dims[y].get(), z1))
                    if self.physics.check_collision():
                        # the object fills the whole range of z0..z1 - we should issue a warning
                        next_point = Point(dims[x].get(), dims[y].get(), INFINITE)
                    else:
                        next_point = Point(dims[x].get(), dims[y].get(), z1)
                else:
                    next_point = Point(dims[x].get(), dims[y].get(), safe_z)

                pa.append(next_point)
                self.cutter.moveto(next_point)
                if draw_callback:
                    draw_callback()

                """
                height_max = -INFINITE
                cut_max = None
                triangle_max = None
                cut_last = None
                self.cutter.moveto(p)
                box_x_min = p.x - self.cutter.radius
                box_x_max = p.x + self.cutter.radius
                box_y_min = p.y - self.cutter.radius
                box_y_max = p.y + self.cutter.radius
                box_z_min = dim_height.end
                box_z_max = +INFINITE
                triangles = self.model.triangles(box_x_min, box_y_min, box_z_min, box_x_max, box_y_max, box_z_max)
                for t in triangles:
                    if t.normal().z < 0: continue;
                    cut = self.cutter.drop(t)
                    if cut and (cut.z > height_max or height_max is None):
                        height_max = cut.z
                        cut_max = cut
                        triangle_max = t
                if not cut_max or not dim_height.check_bounds(cut_max.z):
                    cut_max = Point(dims[x].get(), dims[y].get(), dim_height.end)
                if cut_last and ((triangle_max and not triangle_last) or (triangle_last and not triangle_max)):
                    if dim_height.check_bounds(cut_last.z):
                        pa.append(Point(cut_last.x, cut_last.y, cut_max.z))
                    else:
                        pa.append(Point(cut_max.x, cut_max.y, cut_last.z))
                elif (triangle_max and triangle_last and cut_last and cut_max) and (triangle_max != triangle_last):
                    nl = range(3)
                    nl[0] = -getattr(triangle_last.normal(), dim_attrs[0])
                    nl[2] = triangle_last.normal().z
                    nm = range(3)
                    nm[0] = -getattr(triangle_max.normal(), dim_attrs[0])
                    nm[2] = triangle_max.normal().z
                    last = range(3)
                    last[0] = getattr(cut_last, dim_attrs[0])
                    last[2] = cut_last.z
                    mx = range(3)
                    mx[0] = getattr(cut_max, dim_attrs[0])
                    mx[2] = cut_max.z
                    c = range(3)
                    (c[0], c[2]) = intersect_lines(last[0], last[2], nl[0], nl[2], mx[0], mx[2], nm[0], nm[2])
                    if c[0] and last[0] < c[0] and c[0] < mx[0] and (c[2] > last[2] or c[2] > mx[2]):
                        c[1] = getattr(cut_last, dim_attrs[1])
                        if c[2]<dims[2].min-10 or c[2]>dims[2].max+10:
                            print "^", "%sl=" % dim_attrs[0], last[0], \
                                    ", %sl=" % dim_attrs[2], last[2], \
                                    ", n%sl=" % dim_attrs[0], nl[0], \
                                    ", n%sl=" %dim_attrs[2], nl[2], \
                                    ", %s=" % dim_attrs[0].upper(), c[0], \
                                    ", %s=" % dim_attrs[2].upper(), c[2], \
                                    ", %sm=" % dim_attrs[0], mx[0], \
                                    ", %sm=" % dim_attrs[2], mx[2], \
                                    ", n%sm=" % dim_attrs[0], nm[0], \
                                    ", n%sm=" % dim_attrs[2], nm[2]

                        else:
                            pa.append(Point(c[x], c[y], c[2]))
                pa.append(cut_max)

                cut_last = cut_max
                triangle_last = triangle_max
                """

                dims[0].shift(d0)

            pa.end_scanline()
            dims[1].shift(d1)

        pa.end_direction()

        pa.finish()
        return pa.paths

