pycam : Python CAM
------------------

Toolpath Generation for 3-Axis CNC machining


Features:

    * Cutters:
      ** Spherical Cutter
      ** Cylindrical Cutter
      ** Toroidal Cutter

    * Path Generators:
      ** DropCutter
      ** PushCutter

    * Path Processors:
      ** Linear
      ** ZigZag
      ** Polygon

    * Importers:
      ** STL

    * Exporters:
      ** GCODE

    * Visualization:
      ** OpenGL


INSTALL: 

    PyOpenGL :  http://pyopengl.sourceforge.net/
                        http://downloads.sourceforge.net/pyopengl/PyOpenGL-3.0.0b5.tar.gz

	(requires TOGL)
    TOGL: http://downloads.sourceforge.net/togl/Togl2.0-8.4-Windows.zip
          (just copy Togl2.0 into Python25/tcl)
                        http://downloads.sourceforge.net/togl/Togl2.0-src.tar.gz

	(on windows, this also requires GLUT)
    GLUT :      http://www.cip.physik.uni-muenchen.de/~georg.hennig/downloads/glut-3.7.6-wheel_mingw.zip



RUNNING:

   extract the archive and run "python pycam.py"



USAGE:

   as a practical approach, you would probably: 
 
   1) use the Cylindrical cutter with the PushCutter Pathgenerator and the Polygon PostProcessor to do the "rough" cutting 
 
   2) use the Toroidal cutter with the ContourCutter Pathgenerator to do the "semifinish" cutting.
      (it's not yet implemented, so you can skip this one for now :-)

   3) use the Spherical cutter with the DropCutter Pathgenerator and the ZigZag PostProcessor to do the "finish" cutting. 


TODO:

    * Python code
    ** clean up module/package use, being all "import" statements

    * Geometry
    ** intersect_torus_line
        -> try to find a better implementation
    ** intersect_cone_*

    * Cutters
    ** FiletCutter

    * PathGenerators
    ** ContourCutter
       -> waterlevel tracer

    * PathProcessors
    ** Traveling Salesman

    * Gui
    ** create something better than "SimpleGui"
    ** move calculactions in separate thread
    ** incremental visualization
    ** add progress bar

BUGS:
    * The combination of PushCutter with PolygonCutter sometimes cuts accross
      the model in between lines
    * The combination of PushCutter with ContourCutter sometimes cuts accross
      the model in between lines in "x" or "y" mode
    * The combination of PushCutter with ContourCutter sometimes gives erratic
      toolpaths in "xy" mode


OPTIMIZATION:

    * short-circuit the plane/triangle/line/edge/point/vertex tests,
      so that when the result is known, no further intersections are calculated

    * use kdtree

    * make Model have unique points

    * make Model have unique edges

    * make Cutters have a "color" so that for each x in plane/triangle/line/edge/point/vertex
      the result of an intersection (cutter,x,color) is cachable
      (i.e. each Cutter.moveto should change the color, just increasing an "int color" should be ok)

