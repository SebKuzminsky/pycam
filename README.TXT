pycam : Python CAM
------------------

Toolpath Generation for 3-Axis CNC machining

Read the wiki for details:
    http://sourceforge.net/apps/mediawiki/pycam/index.php?title=User_Manual


RUNNING:

   extract the archive and run "python pycam"



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




KNOWN BUGS:

    http://sourceforge.net/tracker/?group_id=237831&atid=1104176


CONTRIBUTORS:

    * Lode Leroy: initiated the project; developed the toolpath generation,
      collision detection, geometry, Tk interface, ...

    * Lars Kruse: GTK interface and many features

    * Paul: GCode stepping precision

    * Arthur Magill: distutils packaging

    * Sebastian Kuzminsky: debian packaging

