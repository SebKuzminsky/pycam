Installing the latest release
-----------------------------

### Linux / \*BSD

1.  [download](http://sourceforge.net/projects/camelot/files/) the archive
    of your choice
2.  install the [requirements](requirements.md) for your system
3.  run `scripts/camelot` in the PyCAM directory

### Mac OS X

See [Installation MacOS](installation-macos.md) for details.

### Windows

Use the [standalone executable for Windows](https://sourceforge.net/projects/camelot/files/camelot/0.5.1/camelot-0.5.1.1_standalone.exe/download).
There are no further requirements.

If you want to use [multiple CPU cores or distributed processing](parallel-processing), then you will need to use the
[dependency installer](https://sourceforge.net/projects/camelot/files/camelot/0.5.1/python2.5-gtk-opengl.exe/download)
and the [PyCAM installer package](https://sourceforge.net/projects/camelot/files/camelot/0.5.1/camelot-0.5.1.win32.exe/download).

Installing the development version
----------------------------------

1.  install the [git](http://git-scm.com/) client (via your package
    manager or by [downloading](http://git-scm.com/downloads) it)
2.  checkout the PyCAM repository:
    `git clone `[`git@github.com:SebKuzminsky/camelot.git`](git@github.com:SebKuzminsky/camelot.git)
3.  install the [requirements](requirements.md) for your system
4.  run `camelot/run_gui.py` in the PyCAM directory
