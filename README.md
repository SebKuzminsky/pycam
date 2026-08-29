[![Build Status](https://travis-ci.org/SebKuzminsky/camelot.svg?branch=master)](https://travis-ci.org/SebKuzminsky/camelot)

# PyCAM: a toolpath generator

PyCAM generates toolpaths (GCode) based on 2D or 3D models for 3-axis CNC machining.


## Running

Extract the archive or clone the repository.

Graphical Interface: `camelot/run_gui.py`

Scripted Toolpath Processing: `camelot/run_cli.py FLOW_SPECIFICATION_FILE`


## Resources

See the [documentation](http://camelot.sourceforge.net/introduction/) for a short introduction.

* [Website / Documentation](http://camelot.sf.net/)
* [Getting started](http://camelot.sf.net/getting-started.md)
* [FAQ](http://camelot.sf.net/faq.md)
* [Video tutorials](http://vimeo.com/channels/camelot)
* [Screenshots](http://camelot.sourceforge.net/screenshots/)
* [Mailing lists](https://sourceforge.net/p/camelot/mailman/)


## Development

* [Code Repository](https://github.com/SebKuzminsky/camelot)
* [Issue Tracker](https://github.com/SebKuzminsky/camelot/issues)


## Contributors

* Lode Leroy: initiated the project; developed the toolpath generation,
  collision detection, geometry, Tk interface, ...
* Lars Kruse: GTK interface and many features
* Paul: GCode stepping precision
* Arthur Magill: distutils packaging
* Sebastian Kuzminsky: debian packaging
* Nicholas Humfrey: documentation, recovery of old sourceforge-wiki
* Piers Titus van der Torren: documentation
* Reuben Rissler: gtk3 migration
