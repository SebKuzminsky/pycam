System requirements for PyCAM
=============================

PyCAM currently runs on Unix/Linux.

Older releases of PyCAM were also running on Windows and MacOS ([via
MacPorts](http://sourceforge.net/projects/pycam/forums/forum/860183/topic/3800091)).

Please document your experiences here, if you successfully used PyCAM
with other operating systems.

Linux
-----

Install the following packages with your package manager (see below):

-   **python**
-   **python-gtk2**
-   **python-opengl** (at least v3.0.1)
-   **python-gtkglext1** (for OpenSuSE: *python-gtkglext*)

### Debian

Run the following command in a *root* terminal:

    apt-get install python-gtk2 python-opengl python-gtkglext1

Please note, that the outdated Debian *Lenny* contains broken *python-opengl* packages.
You need to temporarily add the *Squeeze* repository during the installation of these two packages.

### Ubuntu

Enable the *universe* repository. See detailed instructions
[here](http://help.ubuntu.com/community/Repositories/Ubuntu).

    sudo apt-get install python-gtk2 python-opengl python-gtkglext1

Please note, that Ubuntu *Jaunty* (maybe also *Dapper/Hardy/Intrepid*) contains broken
*python-opengl* packages. You need to temporarily add the *Karmic* repository during the
installation of these two packages.

### OpenSuSE

Run the following command in a *root* terminal:

    zypper install python-gtk2 python-gtkglext python-opengl

### Fedora

Run the following command in a *root* terminal:

    yum install pygtk2 pygtkglext python-opengl

Windows
-------

The latest releases do not run under Windows.

You may want to use the standalone executable of [v0.5.1 (the latest release supporting
Windows)](https://sourceforge.net/projects/pycam/files/pycam/0.5.1/). This old version is not
maintained anymore - but maybe you are lucky and it just works for you.


MacOS
-----

Please take a look at [Installation MacOS](installation-macos.md)
for the details of installing PyCAM's requirements via
[MacPorts](http://www.macports.org/).


Optional external programs
==========================

Some features of PyCAM require additional external programs.


SVG/PS/EPS import
-----------------

PyCAM supports only STL and DXF files natively. Native SVG support is available
since PyCAM v0.7. For previous versions you need to install external programs
for the conversions of other file formats.

### Debian/Ubuntu

    apt-get install inkscape pstoedit

### OpenSuSE

    zypper install inkscape pstoedit

### Fedora

    yum install inkscape pstoedit

### Windows

Download and install the following programs:

* inkscape: <http://inkscape.org>
* pstoedit: <http://www.pstoedit.net/pstoedit>
* ghostscript: <http://pages.cs.wisc.edu/~ghost/>

*Hint: there is no need to install GraphicMagick - even though pstoedit
suggests it.*
