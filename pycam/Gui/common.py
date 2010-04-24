# -*- coding: utf-8 -*-
"""
$Id$

Copyright 2010 Lars Kruse <devel@sumpfralle.de>

This file is part of PyCAM.

PyCAM is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

PyCAM is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with PyCAM.  If not, see <http://www.gnu.org/licenses/>.
"""

# Tkinter is used for "EmergencyDialog" below - but we will try to import it carefully
#import Tkinter
import sys
import os


DEPENDENCY_DESCRIPTION = {
    "gtk": ("Python bindings for GTK+",
        "Install the package 'python-gtk2'",
        "see http://www.bonifazi.eu/appunti/pygtk_windows_installer.exe"),
    "opengl": ("Python bindings for OpenGL",
        "Install the package 'python-opengl'",
        "see http://www.bonifazi.eu/appunti/pygtk_windows_installer.exe"),
    "gtkgl": ("GTK extension for OpenGL",
        "Install the package 'python-gtkglext1'",
        "see http://www.bonifazi.eu/appunti/pygtk_windows_installer.exe"),
    "togl": ("Tk for OpenGL",
        "see http://downloads.sourceforge.net/togl/",
        "see http://downloads.sourceforge.net/togl/"),
    "tkinter": ("Tk interface for Python",
        "Install the package 'python-tk'",
        "see http://tkinter.unpythonic.net/wiki/"),
}

REQUIREMENTS_LINK = "http://sourceforge.net/apps/mediawiki/pycam/index.php?title=Requirements"


def dependency_details_gtk():
    result = {}
    try:
        import gtk
        result["gtk"] = True
    except ImportError:
        result["gtk"] = False
    try:
        import gtk.gtkgl
        result["gtkgl"] = True
    except ImportError:
        result["gtkgl"] = False
    try:
        import OpenGL
        result["opengl"] = True
    except ImportError:
        result["opengl"] = False
    return result

def dependency_details_tk():
    result = {}
    try:
        import OpenGL
        result["opengl"] = True
    except ImportError:
        result["opengl"] = False
    try:
        import Tkinter
        result["tkinter"] = True
    except ImportError:
        result["tkinter"] = False
    # Don't try to import OpenGL.Tk if Tkinter itself is missing.
    # Otherwise the "except" statement below fails due to the unknown
    # Tkinter.TclError exception.
    if result["tkinter"]:
        try:
            import logging
            try:
                # temporarily disable debug output of the logging module
                # the error message is: No handlers could be found for logger "OpenGL.Tk"
                previous = logging.raiseExceptions
                logging.raiseExceptions = 0
            except AttributeError:
                previous = None
            import OpenGL.Tk
            if not previous is None:
                logging.raiseExceptions = previous
            result["togl"] = True
        except (ImportError, Tkinter.TclError):
            result["togl"] = False
    else:
        result["togl"] = False
    return result

def check_dependencies(details):
    """you can feed this function with the output of "dependency_details_gtk" or "..._tk".
    The result is True if all dependencies are met.
    """
    failed = [key for (key, state) in details.items() if not state]
    return len(failed) == 0

def get_dependency_report(details, prefix=""):
    result = []
    DESC_COL = 0
    if sys.platform.startswith("win"):
        ADVICE_COL = 2
    else:
        ADVICE_COL = 1
    for key, state in details.items():
        text = "%s%s: " % (prefix, DEPENDENCY_DESCRIPTION[key][DESC_COL])
        if state:
            text += "OK"
        else:
            text += "MISSING (%s)" % DEPENDENCY_DESCRIPTION[key][ADVICE_COL]
        result.append(text)
    return os.linesep.join(result)


class EmergencyDialog:
    """ This graphical message window requires no external dependencies.
    The Tk interface package is part of the main python distribution.
    Use this class for displaying dependency errors (especially on Windows).
    """

    def __init__(self, title, message):
        try:
            import Tkinter
        except ImportError:
            # tk is not installed
            print >>sys.stderr, "Warning: %s" % str(title)
            print >>sys.stderr, message
            return
        try:
            root = Tkinter.Tk()
        except Tkinter.TclError, err_msg:
            print >>sys.stderr, "Warning: Failed to create error dialog window (%s). Probably you are running PyCAM from a terminal." % str(err_msg)
            print >>sys.stderr, "%s: %s" % (title, message)
            return
        root.title(title)
        root.bind("<Return>", self.finish)
        root.bind("<Escape>", self.finish)
        root.minsize(300, 100)
        self.root = root
        frame = Tkinter.Frame(root)
        frame.pack()
        # add text output as label
        message = Tkinter.Message(root, text=message)
        # we need some space for the dependency report
        message["width"] = 800
        message.pack()
        # add the "close" button
        close = Tkinter.Button(root, text="Close")
        close["command"] = self.finish
        close.pack(side=Tkinter.BOTTOM)
        root.mainloop()

    def finish(self, *args):
        self.root.quit()

