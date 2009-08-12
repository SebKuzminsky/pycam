import string
import math

from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *

from OpenGL.constant import Constant
GLUT_WHEEL_UP=Constant('GLUT_WHEEL_UP',3)
GLUT_WHEEL_DOWN=Constant('GLUT_WHEEL_DOWN',4)

from pycam.Geometry.utils import *

_DrawCurrentSceneFunc = None
_KeyHandlerFunc = None

# Some api in the chain is translating the keystrokes to this octal string
# so instead of saying: ESCAPE = 27, we use the following.
ESCAPE = '\033'

# Number of the glut window.
window = 0

# Rotations for cube.
xrot = 110
yrot = 180
zrot = 250
scale = 0.5
xdist = 0
ydist = -1.0
zdist = -8.0

texture_num = 2
object = 0
light = 1
shade_model = GL_FLAT
polygon_mode = GL_FILL
width = 320
height = 200

# A general OpenGL initialization function.  Sets all of the initial parameters.
def InitGL(Width, Height):				# We call this right after our OpenGL window is created.
    global width, height
    width = Width
    height = Height

    glClearColor(0.0, 0.0, 0.0, 0.0)	# This Will Clear The Background Color To Black
    glClearDepth(1.0)					# Enables Clearing Of The Depth Buffer
    glDepthFunc(GL_LESS)				# The Type Of Depth Test To Do
    glEnable(GL_DEPTH_TEST)				# Enables Depth Testing
#    glShadeModel(GL_SMOOTH)				# Enables Smooth Color Shading
#    glShadeModel(GL_FLAT)				# Enables Flat Color Shading
    glShadeModel(shade_model)

    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()					# Reset The Projection Matrix
										# Calculate The Aspect Ratio Of The Window
    gluPerspective(60.0, float(Width)/float(Height), 0.1, 100.0)

    glLightfv(GL_LIGHT0, GL_AMBIENT, (0.5, 0.5, 0.5, 1.0))		# Setup The Ambient Light
    glLightfv(GL_LIGHT0, GL_DIFFUSE, (1.0, 1.0, 1.0, 1.0))		# Setup The Diffuse Light
    glLightfv(GL_LIGHT0, GL_POSITION, (-10.0, 0.0, 0.0, 1.0))	# Position The Light
    glEnable(GL_LIGHT0)					# Enable Light One

    glMatrixMode(GL_MODELVIEW)
    glMaterial(GL_FRONT_AND_BACK, GL_SPECULAR, (0.1, 0.1, 0.1, 1.0))
#    glMaterial(GL_FRONT_AND_BACK, GL_SHININESS, (0.5))

    glPolygonMode(GL_FRONT_AND_BACK, polygon_mode)

def ReSizeGLScene(Width, Height):
    if Height == 0:						# Prevent A Divide By Zero If The Window Is Too Small
        Height = 1

    global width, height
    width = Width
    height = Height

    glViewport(0, 0, Width, Height)		# Reset The Current Viewport And Perspective Transformation
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(60.0, float(Width)/float(Height), 0.1, 100.0)
    glMatrixMode(GL_MODELVIEW)

# The main drawing function.
def DrawGLScene():
    global xrot, yrot, zrot, scale, xdist, ydist, zdist, light

    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)	# Clear The Screen And The Depth Buffer
    glLoadIdentity()					# Reset The View
    glTranslatef(xdist,ydist,zdist)			# Move Into The Screen

    glRotatef(xrot,1.0,0.0,0.0)			# Rotate The Cube On It's X Axis
    glRotatef(yrot,0.0,1.0,0.0)			# Rotate The Cube On It's Y Axis
    glRotatef(zrot,0.0,0.0,1.0)			# Rotate The Cube On It's Z Axis
    glScalef(scale,scale,scale)
    if light:
        glEnable(GL_LIGHTING)
    else:
        glDisable(GL_LIGHTING)

    if _DrawCurrentSceneFunc:
        _DrawCurrentSceneFunc()

    #  since this is double buffered, swap the buffers to display what just got drawn.
    glutSwapBuffers()

# The function called whenever a key is pressed
def keyPressed(key, x, y):
    global light, polygon_mode, shade_model
    global xrot, yrot, zrot
    global _KeyHandlerFunc

    key = string.upper(key)
    if key == ESCAPE or key=='Q':
        # If escape is pressed, kill everything.
        sys.exit()
    elif key == 'S':
        light = not light
    elif key == '=':
        print "rot=<%g,%g,%g>" % (xrot,yrot,zrot)
    elif key == 'I':
        xrot = 110
        yrot = 180
        zrot = 250
    elif key == 'T': # top
        xrot=0
        yrot=0
        zrot=0
    elif key == 'F': # front
        xrot=-90
        yrot=0
        zrot=0
    elif key == 'R': # right
        xrot=-90
        yrot=0
        zrot=-90
    elif key == 'L': # left
        xrot=-90
        yrot=0
        zrot=+90
    elif key == 'M':
        if shade_model == GL_SMOOTH:
            shade_model = GL_FLAT
        else:
            shade_model = GL_SMOOTH
        glShadeModel(shade_model)
    elif key == 'P':
        if polygon_mode == GL_FILL:
            polygon_mode = GL_LINE
        else:
            polygon_mode = GL_FILL
        glPolygonMode(GL_FRONT_AND_BACK, polygon_mode)
    elif _KeyHandlerFunc:
        _KeyHandlerFunc(key, x, y)

class mouseState:
    button = None
    state = None
    x=0
    y=0

def mousePressed(button, state, x, y):
    global xrot, yrot, zrot, xdist, ydist, zdist, scale
    if button==GLUT_WHEEL_DOWN:
        scale *= 1.1
    elif button==GLUT_WHEEL_UP:
        scale /= 1.1

    mouseState.button = button
    mouseState.state = state
    mouseState.x=float(x)
    mouseState.y=float(y)

def mouseMoved(x, y):
    global xrot, yrot, zrot, xdist, ydist, zdist, scale
    global width, height
    x = float(x)
    y = float(y)
    a1 = math.atan2(mouseState.y-height/2.0, mouseState.x-width/2.0)
    r1 = math.sqrt(sqr(mouseState.y-height/2.0)+sqr(mouseState.x-width/2.0))
    a2 = math.atan2(y-height/2.0, x-width/2.0)
    r2 = math.sqrt(sqr(y-height/2.0)+sqr(x-width/2.0))
    da = abs(a2-a1)
    dr = 0
    if r2>r1:
        dr = r1/r2
    else:
        dr = r2/r1
    if mouseState.button == GLUT_LEFT_BUTTON or mouseState.button == GLUT_RIGHT_BUTTON:
        a3 = math.acos(mouseState.x/width-0.5)
        a4 = math.acos(x/width-0.5)
        zrot = zrot - (a4-a3)*180/math.pi*2
    if mouseState.button == GLUT_RIGHT_BUTTON:
        a3 = math.acos(mouseState.y/height-0.5)
        a4 = math.acos(y/height-0.5)
        if x>width/2.0:
            yrot = yrot + (a4-a3)*180/math.pi*2
        else:
            yrot = yrot - (a4-a3)*180/math.pi*2
    if mouseState.button == GLUT_LEFT_BUTTON:
        a3 = math.acos(mouseState.y/width-0.5)
        a4 = math.acos(y/width-0.5)
        xrot = xrot - (a4-a3)*180/math.pi*2
    mouseState.x=x
    mouseState.y=y

def Visualization(title, drawScene=DrawGLScene, width=320, height=200, handleKey=None):
    global window, _DrawCurrentSceneFunc, _KeyHandlerFunc
    glutInit(sys.argv)

    _DrawCurrentSceneFunc = drawScene

    if handleKey:
        _KeyHandlerFunc = handleKey

    # Select type of Display mode:
    #  Double buffer
    #  RGBA color
    # Alpha components supported
    # Depth buffer
    glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE | GLUT_DEPTH)

    # get a 640 x 480 window
    glutInitWindowSize(640, 480)

    # the window starts at the upper left corner of the screen
    glutInitWindowPosition(0, 0)

    # Okay, like the C version we retain the window id to use when closing, but for those of you new
    # to Python (like myself), remember this assignment would make the variable local and not global
    # if it weren't for the global declaration at the start of main.
    window = glutCreateWindow(title)

    # Register the drawing function with glut, BUT in Python land, at least using PyOpenGL, we need to
    # set the function pointer and invoke a function to actually register the callback, otherwise it
    # would be very much like the C version of the code.
    glutDisplayFunc(DrawGLScene)

    # Uncomment this line to get full screen.
    # glutFullScreen()

    # When we are doing nothing, redraw the scene.
    glutIdleFunc(DrawGLScene)

    # Register the function called when our window is resized.
    glutReshapeFunc(ReSizeGLScene)

    # Register the function called when the keyboard is pressed.
    glutKeyboardFunc(keyPressed)

    # Register the function called when the mouse is pressed.
    glutMouseFunc(mousePressed)

    # Register the function called when the mouse is pressed.
    glutMotionFunc(mouseMoved)

    # Initialize our window.
    InitGL(640, 480)

    # Start Event Processing Engine
    glutMainLoop()


test_model = None
test_cutter = None
test_pathlist = None

def DrawTestScene():
    global test_model, test_cutter, test_pathlist
    if test_model:
        glColor4f(1,0.5,0.5,0.1)
        test_model.to_OpenGL()
    if test_cutter:
        glColor3f(0.5,0.5,0.5)
        test_cutter.to_OpenGL()
    if test_pathlist:
        for path in test_pathlist:
            glColor3f(0.5,0.5,1)
            glBegin(GL_LINE_STRIP)
            for point in path.points:
                glVertex3f(point.x, point.y, point.z)
#                glVertex3f(point.x, point.y, point.z+1)
            glEnd()

def ShowTestScene(model=None, cutter=None, pathlist=None):
    global test_model, test_cutter, test_pathlist
    test_model = model
    test_cutter = cutter
    test_pathlist = pathlist
    Visualization("TestScene", DrawTestScene)
