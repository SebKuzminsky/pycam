from pycam.Geometry.Point import Point
import OpenGL.GL as GL
import OpenGL.GLU as GLU
import math

# the length of the distance vector does not matter - it will be normalized and multiplied later anyway
VIEWS = {
    "reset": {"distance": (1.0, 1.0, 1.0), "center": (0.0, 0.0, 0.0), "up": (0.0, 0.0, 1.0), "znear": 0.1, "zfar": 1000.0, "fovy": 30.0},
    "top": {"distance": (0.0, 0.0, 1.0), "center": (0.0, 0.0, 0.0), "up": (1.0, 0.0, 0.0), "znear": 0.1, "zfar": 1000.0, "fovy": 30.0},
    "bottom": {"distance": (0.0, 0.0, -1.0), "center": (0.0, 0.0, 0.0), "up": (1.0, 0.0, 0.0), "znear": 0.1, "zfar": 1000.0, "fovy": 30.0},
    "left": {"distance": (-1.0, 0.0, 0.0), "center": (0.0, 0.0, 0.0), "up": (0.0, 0.0, 1.0), "znear": 0.1, "zfar": 1000.0, "fovy": 30.0},
    "right": {"distance": (1.0, 0.0, 0.0), "center": (0.0, 0.0, 0.0), "up": (0.0, 0.0, 1.0), "znear": 0.1, "zfar": 1000.0, "fovy": 30.0},
    "front": {"distance": (0.0, -1.0, 0.0), "center": (0.0, 0.0, 0.0), "up": (0.0, 0.0, 1.0), "znear": 0.1, "zfar": 1000.0, "fovy": 30.0},
    "back": {"distance": (0.0, 1.0, 0.0), "center": (0.0, 0.0, 0.0), "up": (0.0, 0.0, 1.0), "znear": 0.1, "zfar": 1000.0, "fovy": 30.0},
}

def rotate(orig, rot_axis, sin, cos):
    """ rotation of an original vector around a normalized "rot_axis" vector
    see http://mathworld.wolfram.com/RotationMatrix.html
    @type orig: tuple(float)
    @value orig: the vector to be rotated
    @type rot_axis: tuple(float)
    @value rot_axis: the vector describes the rotation axis
    @type sin: float
    @value sin: sinus of the rotation angle
    @type cos: float
    @value cos: cosinus of the rotation angle
    @rtype: tuple(float)
    """
    rot_matrix = ((cos + rot_axis[0]*rot_axis[0]*(1-cos), rot_axis[0]*rot_axis[1]*(1-cos) - rot_axis[2]*sin, rot_axis[0]*rot_axis[2]*(1-cos) + rot_axis[1]*sin),
            (rot_axis[1]*rot_axis[0]*(1-cos) + rot_axis[2]*sin, cos + rot_axis[1]*rot_axis[1]*(1-cos), rot_axis[1]*rot_axis[2]*(1-cos) - rot_axis[0]*sin),
            (rot_axis[2]*rot_axis[0]*(1-cos) - rot_axis[1]*sin, rot_axis[2]*rot_axis[1]*(1-cos) + rot_axis[0]*sin, cos + rot_axis[2]*rot_axis[2]*(1-cos)))
    return (orig[0]*rot_matrix[0][0] + orig[1]*rot_matrix[0][1] + orig[2]*rot_matrix[0][2],
            orig[0]*rot_matrix[1][0] + orig[1]*rot_matrix[1][1] + orig[2]*rot_matrix[1][2],
            orig[0]*rot_matrix[2][0] + orig[1]*rot_matrix[2][1] + orig[2]*rot_matrix[2][2])


class Camera:

    def __init__(self, settings, get_dim_func, view=None):
        self.view = None
        self.settings = settings
        self._get_dim_func = get_dim_func
        self.set_view(view)

    def set_view(self, view=None):
        if view is None:
            self.view = VIEWS["reset"].copy()
        else:
            self.view = view.copy()
        self.center_view()
        self.auto_adjust_distance()

    def center_view(self):
        s = self.settings
        # center the view on the object
        self.view["center"] = ((s.get("maxx") + s.get("minx"))/2, (s.get("maxy") + s.get("miny"))/2, (s.get("maxz") + s.get("minz"))/2)

    def auto_adjust_distance(self):
        s = self.settings
        v = self.view
        # adjust the distance to get a view of the whole object
        dimx = s.get("maxx") - s.get("minx")
        dimy = s.get("maxy") - s.get("miny")
        dimz = s.get("maxz") - s.get("minz")
        max_dim = max(max(dimx, dimy), dimz)
        width, height = self._get_screen_dimensions()
        win_size = min(width, height)
        distv = Point(v["distance"][0], v["distance"][1], v["distance"][2]).normalize()
        # the multiplier "2.0" is based on: sqrt(2) + margin  -- the squre root makes sure, that the the diagonal fits
        distv = distv.mul((max_dim * 2.0) / math.sin(v["fovy"]/2))
        self.view["distance"] = (distv.x, distv.y, distv.z)

    def scale_distance(self, scale):
        if scale != 0:
            dist = self.view["distance"]
            self.view["distance"] = (scale * dist[0], scale * dist[1], scale * dist[2])

    def get(self, key, default=None):
        if (not self.view is None) and self.view.has_key(key):
            return self.view[key]
        else:
            return default

    def set(self, key, value):
        self.view[key] = value

    def move_camera_by_screen(self, x_move, y_move, max_model_shift):
        """ move the camera acoording to a mouse movement
        @type x_move: int
        @value x_move: movement of the mouse along the x axis
        @type y_move: int
        @value y_move: movement of the mouse along the y axis
        @type max_model_shift: float
        @value max_model_shift: maximum shifting of the model view (e.g. for x_move == screen width)
        """
        factors_x, factors_y = self._get_axes_vectors()
        width, height = self._get_screen_dimensions()
        # relation of x/y movement to the respective screen dimension
        win_x_rel = ((-2.0 * x_move) / width) / math.sin(self.view["fovy"])
        win_y_rel = ((-2.0 * y_move) / height) / math.sin(self.view["fovy"])
        # update the model position that should be centered on the screen
        old_center = self.view["center"]
        new_center = []
        for i in range(3):
            new_center.append(old_center[i] + max_model_shift * (win_x_rel * factors_x[i] + win_y_rel * factors_y[i]))
        self.view["center"] = tuple(new_center)

    def rotate_camera_by_screen(self, start_x, start_y, end_x, end_y):
        factors_x, factors_y = self._get_axes_vectors()
        width, height = self._get_screen_dimensions()
        # calculate rotation factors - based on the distance to the center (between -1 and 1)
        rot_x_factor = (2.0 * start_x) / width - 1
        rot_y_factor = (2.0 * start_y) / height - 1
        # calculate rotation angles (between -90 and +90 degrees)
        xdiff = end_x - start_x
        ydiff = end_y - start_y
        # compensate inverse rotation left/right side (around x axis) and top/bottom (around y axis)
        if rot_x_factor < 0:
            ydiff = -ydiff
        if rot_y_factor > 0:
            xdiff = -xdiff
        rot_x_angle = rot_x_factor * math.pi * ydiff / height
        rot_y_angle = rot_y_factor * math.pi * xdiff / width
        # calculate sinus / cosinus
        rot_x_sin = math.sin(rot_x_angle)
        rot_x_cos = math.cos(rot_x_angle)
        rot_y_sin = math.sin(rot_y_angle)
        rot_y_cos = math.cos(rot_y_angle)
        # rotate around the "up" vector with the y-axis rotation
        original_distance = self.view["distance"]
        original_up = self.view["up"]
        new_distance = rotate(original_distance, factors_y, rot_y_sin, rot_y_cos)
        new_up = rotate(original_up, factors_y, rot_y_sin, rot_y_cos)
        # rotate around the cross vector with the x-axis rotation
        new_distance = rotate(new_distance, factors_x, rot_x_sin, rot_x_cos)
        new_up = rotate(new_up, factors_x, rot_x_sin, rot_x_cos)
        self.view["distance"] = new_distance
        self.view["up"] = new_up

    def position_camera(self):
        width, height = self._get_screen_dimensions()
        prev_mode = GL.glGetIntegerv(GL.GL_MATRIX_MODE)
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        v = self.view
        # position the light according to the current bounding box
        light_pos = range(3)
        light_pos[0] = 2 * self.settings.get("maxx") - self.settings.get("minx")
        light_pos[1] = 2 * self.settings.get("maxy") - self.settings.get("miny")
        light_pos[2] = 2 * self.settings.get("maxz") - self.settings.get("minz")
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_POSITION, (light_pos[0], light_pos[1], light_pos[2], 1.0))
        # position the camera
        camera_position = (v["center"][0] + v["distance"][0],
                v["center"][1] + v["distance"][1], v["center"][2] + v["distance"][2])
        GLU.gluPerspective(v["fovy"], (0.0 + width) / height, v["znear"], v["zfar"])
        GLU.gluLookAt(camera_position[0], camera_position[1], camera_position[2],
                v["center"][0], v["center"][1], v["center"][2], v["up"][0], v["up"][1], v["up"][2])
        GL.glMatrixMode(prev_mode)

    def _get_screen_dimensions(self):
        return self._get_dim_func()

    def _get_axes_vectors(self):
        """calculate the model vectors along the screen's x and y axes"""
        # the "up" vector defines, in what proportion each axis of the model is in line with the screen's y axis
        v_up = self.view["up"]
        factors_y = (v_up[0], v_up[1], v_up[2])
        # calculate the proportion of each model axis according to the x axis of the screen
        distv = self.view["distance"]
        distv = Point(distv[0], distv[1], distv[2]).normalize()
        factors_x = distv.cross(Point(v_up[0], v_up[1], v_up[2])).normalize()
        factors_x = (factors_x.x, factors_x.y, factors_x.z)
        return (factors_x, factors_y)


