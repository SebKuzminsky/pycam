pycam : Python CAM
==================

Toolpath Generation for 3-Axis CNC machining


## RUNNING:

Extract the archive and run "python pycam"


## USAGE:

As a practical approach, you would probably: 

1) for "rough" cutting,
* use the Cylindrical cutter 
* with the PushCutter Pathgenerator 
* and the Polygon PostProcessor in "x" or "y" mode 

2) for "semifinish" cutting,
* use the Cylindrical/Toroidal cutter 
* with the PushCutter Pathgenerator 
* and the Contour PostProcessor in "xy" mode 

3) "finish" cutting
* use the Spherical cutter 
* with the DropCutter Pathgenerator 
* and the ZigZag PostProcessor in "x" or "y" mode



## BUG TRACKER:

https://github.com/SebKuzminsky/pycam/issues


## CONTRIBUTORS:

* Lode Leroy: initiated the project; developed the toolpath generation,
  collision detection, geometry, Tk interface, ...

* Lars Kruse: GTK interface and many features

* Paul: GCode stepping precision

* Arthur Magill: distutils packaging

* Sebastian Kuzminsky: debian packaging

