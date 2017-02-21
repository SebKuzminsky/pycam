System requirements for PyCAM
=============================

PyCAM currently runs on Windows, Unix/Linux and MacOS ([via
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
-   **python-rsvg**
-   **python-guppy** (optional; required by the *Memory Analyzer*
    plugin - only useful for development)
-   **python-pyode** (optional; use at least v1.2.0-4; probably you do
    not need it)
-   **python-psyco** - this optional dependency is not available in
    recent distributions - just ignore it (*PyCAM* until v0.5.1 issues a
    negligible warning)

### Debian

Run the following command in a *root* terminal:

`apt-get install python-gtk2 python-opengl python-gtkglext1 python-rsvg python-pyode python-guppy`

Please note, that the outdated Debian *Lenny* contains broken
*python-opengl* and *python-pyode* packages. You need to temporarily add
the *Squeeze* repository during the installation of these two packages.

### Ubuntu

Enable the *universe* repository. See detailed instructions
[here](http://help.ubuntu.com/community/Repositories/Ubuntu).

`sudo apt-get install python-gtk2 python-opengl python-gtkglext1 python-rsvg python-pyode python-guppy`

Please note, that Ubuntu *Jaunty* (maybe also *Dapper/Hardy/Intrepid*)
contains broken *python-opengl* and *python-pyode* packages. You need to
temporarily add the *Karmic* repository during the installation of these
two packages.

### OpenSuSE

Run the following command in a *root* terminal:

`zypper install python-gtk2 python-gtkglext python-opengl python-rsvg python-guppy`

### Fedora

Run the following command in a *root* terminal:

`yum install pygtk2 pygtkglext python-opengl gnome-python2-rsvg python-guppy`

Windows
-------

Alternatives:

-   Use the [standalone executable for
    Windows](http://pycam.sf.net/downloads.html). It does not require
    any additional software.
-   Use the package installer, but make sure that you installed the
    dependency installer before. Both are available for
    [download](http://pycam.sf.net/downloads.html).

MacOS
-----

Please take a look at [Installation MacOS](Installation_MacOS)
for the details of installing PyCAM's requirements via
[MacPorts](http://www.macports.org/).


Optional external programs
==========================

Some features of PyCAM require additional external programs.

SVG/PS/EPS import
-----------------

PyCAM supports only STL and DXF files natively. Thus you need to install
external programs for conversions of other file formats.

### Debian/Ubuntu

    apt-get install inkscape pstoedit

### OpenSuSE

    zypper install inkscape pstoedit

### Fedora

    yum install inkscape pstoedit

### Windows

Download and install the following programs:

inkscape: <http://inkscape.org>\
pstoedit: <http://www.pstoedit.net/pstoedit>\
ghostscript: <http://pages.cs.wisc.edu/~ghost/>

*Hint: there is no need to install GraphicMagick - even though pstoedit
suggests it.*
