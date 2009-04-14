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
      ** Contour        (aka. waterline)

    * Importers:
      ** STL

    * Exporters:
      ** GCODE

    * Visualization:
      ** OpenGL


RUNNING:

   extract the archive and run "python pycam.py"



USAGE:

   as a practical approach, you would probably: 
 
   1) for "rough" cutting,
      use the Cylindrical cutter 
      with the PushCutter Pathgenerator 
      and the Polygon PostProcessor in "x" or "y" mode 
      
 
   2) for "semifinish" cutting,
      use the Cylindrical/Toroidal cutter 
      with the PushCutter Pathgenerator 
      and the Contour PostProcessor in "xy" mode 

   3) "finish" cutting
      use the Spherical cutter 
      with the DropCutter Pathgenerator 
      and the ZigZag PostProcessor in "x" or "y" mode


TODO:

    * Python code
    ** clean up module/package use, being all "import" statements

    * Geometry
    ** intersect_torus_line
        -> try to find a better implementation
    ** intersect_cone_*

    * Cutters
    ** FiletCutter

    * PathProcessors
    ** Traveling Salesman for Polygon PostProcessor

    * Gui
    ** create something better than "SimpleGui"
    ** move calculactions in separate thread
    ** incremental visualization
    ** add progress bar


FEATURE REQUESTS:

    * climbing / conventional cutting paths

    * diagonal paths

    * start at arbitrary corner


KNOWN BUGS:

    * The combination of PushCutter with PolygonCutter and ContourCutter 
      sometimes make tiny cuts accross the model in between lines


OPTIMIZATION:

    * short-circuit the plane/triangle/line/edge/point/vertex tests,
      so that when the result is known, no further intersections are calculated

    * use kdtree to speed up collision detection

    * make Model have unique points

    * make Model have unique edges

    * make Cutters have a "color" so that for each x in plane/triangle/line/edge/point/vertex
      the result of an intersection (cutter,x,color) is cachable
      (i.e. each Cutter.moveto should change the color, just increasing an "int color" should be ok)

    * align z-levels with horizontal triangles when possible

    * align x/y paths with vertical triangles when possible

