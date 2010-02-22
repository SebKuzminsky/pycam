import OpenGL.GL as GL
import OpenGL.GLUT as GLUT


VIEW_ROTATIONS = {
    "reset":    [(110, 1.0, 0.0, 0.0), (180, 0.0, 1.0, 0.0), (160, 0.0, 0.0, 1.0)],
    "front":    [(-90, 1.0, 0, 0)],
    "back":     [(-90, 1.0, 0, 0), (180, 0, 0, 1.0)],
    "left":     [(-90, 1.0, 0, 0), (90, 0, 0, 1.0)],
    "right":    [(-90, 1.0, 0, 0), (-90, 0, 0, 1.0)],
    "top":      [],
    "bottom":    [(180, 1.0, 0, 0)],
}

MODEL_TRANSFORMATIONS = {
    "normal": ((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0)),
    "x": ((1, 0, 0, 0), (0, 0, 1, 0), (0, -1, 0, 0)),
    "y": ((0, 0, -1, 0), (0, 1, 0, 0), (1, 0, 0, 0)),
    "z": ((0, 1, 0, 0), (-1, 0, 0, 0), (0, 0, 1, 0)),
    "xy": ((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, -1, 0)),
    "xz": ((1, 0, 0, 0), (0, -1, 0, 0), (0, 0, 1, 0)),
    "yz": ((-1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0)),
    "x_swap_y": ((0, 1, 0, 0), (1, 0, 0, 0), (0, 0, 1, 0)),
    "x_swap_z": ((0, 0, 1, 0), (0, 1, 0, 0), (1, 0, 0, 0)),
    "y_swap_z": ((1, 0, 0, 0), (0, 0, 1, 0), (0, 1, 0, 0)),
}

def draw_string(x, y, z, p, s, scale=.01):
    GL.glPushMatrix()
    GL.glTranslatef(x, y, z)
    if p == 'xy':
        pass
    elif p == 'yz':
        GL.glRotatef(90, 0, 1, 0)
        GL.glRotatef(90, 0, 0, 1)
    elif p == 'xz':
        GL.glRotatef(90, 0, 1, 0)
        GL.glRotatef(90, 0, 0, 1)
        GL.glRotatef(-90, 0, 1, 0)
    GL.glScalef(scale, scale, scale)
    for c in str(s):
        GLUT.glutStrokeCharacter(GLUT.GLUT_STROKE_ROMAN, ord(c))
    GL.glPopMatrix()

def draw_axes(size):
    GL.glBegin(GL.GL_LINES)
    GL.glColor3f(1, 0, 0)
    GL.glVertex3f(0, 0, 0)
    GL.glVertex3f(size, 0, 0)
    GL.glEnd()
    draw_string(size, 0, 0, 'xy', "X")
    GL.glBegin(GL.GL_LINES)
    GL.glColor3f(0, 1, 0)
    GL.glVertex3f(0, 0, 0)
    GL.glVertex3f(0, size, 0)
    GL.glEnd()
    draw_string(0, size, 0, 'yz', "Y")
    GL.glBegin(GL.GL_LINES)
    GL.glColor3f(0, 0, 1)
    GL.glVertex3f(0, 0, 0)
    GL.glVertex3f(0, 0, size)
    GL.glEnd()
    draw_string(0, 0, size, 'xz', "Z")

def draw_bounding_box(minx, miny, minz, maxx, maxy, maxz):
    color = [0.3, 0.3, 0.3]
    p1 = [minx, miny, minz]
    p2 = [minx, maxy, minz]
    p3 = [maxx, maxy, minz]
    p4 = [maxx, miny, minz]
    p5 = [minx, miny, maxz]
    p6 = [minx, maxy, maxz]
    p7 = [maxx, maxy, maxz]
    p8 = [maxx, miny, maxz]
    # lower rectangle
    GL.glBegin(GL.GL_LINES)
    GL.glColor3f(*color)
    # all combinations of neighbouring corners
    for corner_pair in [(p1, p2), (p1, p5), (p1, p4), (p2, p3),
                (p2, p6), (p3, p4), (p3, p7), (p4, p8), (p5, p6),
                (p6, p7), (p7, p8), (p8, p5)]:
        GL.glVertex3f(*(corner_pair[0]))
        GL.glVertex3f(*(corner_pair[1]))
    GL.glEnd()

def draw_complete_model_view(settings):
    GL.glTranslatef(0, 0, -2)
    if settings.get("unit") == "mm":
        size = 100
    else:
        size = 5
    # axes
    draw_axes(size)
    # stock model
    draw_bounding_box(float(settings.get("minx")), float(settings.get("miny")),
            float(settings.get("minz")), float(settings.get("maxx")),
            float(settings.get("maxy")), float(settings.get("maxz")))
    # draw the model
    GL.glColor3f(0.5, 0.5, 1)
    settings.get("model").to_OpenGL()
    # draw the toolpath
    draw_toolpath(settings.get("toolpath"))

def draw_toolpath(toolpath):
    if toolpath:
        last = None
        for path in toolpath:
            if last:
                GL.glColor3f(0.5, 1, 0.5)
                GL.glBegin(GL.GL_LINES)
                GL.glVertex3f(last.x, last.y, last.z)
                last = path.points[0]
                GL.glVertex3f(last.x, last.y, last.z)
                GL.glEnd()
            GL.glColor3f(1, 0.5, 0.5)
            GL.glBegin(GL.GL_LINE_STRIP)
            for point in path.points:
                GL.glVertex3f(point.x, point.y, point.z)
            GL.glEnd()
            last = path.points[-1]

def rotate_view(scale, rotation=None):
    GL.glMatrixMode(GL.GL_MODELVIEW)
    GL.glLoadIdentity()
    GL.glScalef(scale, scale, scale)
    if rotation:
        for one_rot in rotation:
            GL.glRotatef(*one_rot)

def reset_view(scale):
    rotate_view(scale, rotation=VIEW_ROTATIONS["reset"])

def front_view(scale):
    rotate_view(scale, rotation=VIEW_ROTATIONS["front"])

def back_view(scale):
    rotate_view(scale, rotation=VIEW_ROTATIONS["back"])

def top_view(scale):
    rotate_view(scale, rotation=VIEW_ROTATIONS["top"])

def bottom_view(scale):
    rotate_view(scale, rotation=VIEW_ROTATIONS["bottom"])

def left_view(scale):
    rotate_view(scale, rotation=VIEW_ROTATIONS["left"])

def right_view(scale):
    rotate_view(scale, rotation=VIEW_ROTATIONS["right"])

def transform_model(model, direction="normal"):
    model.transform(MODEL_TRANSFORMATIONS[direction])
    
