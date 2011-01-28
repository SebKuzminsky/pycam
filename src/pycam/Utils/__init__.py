# -*- coding: utf-8 -*-
"""
$Id$

Copyright 2008 Lode Leroy

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

__all__ = ["iterators", "polynomials", "ProgressCounter", "threading",
        "get_platform", "get_external_program_location", "PLATFORM_WINDOWS",
        "PLATFORM_MACOS", "PLATFORM_LINUX", "PLATFORM_UNKNOWN"]

import sys
import os
# this is imported below on demand
#import win32com
#import win32api

PLATFORM_LINUX = 0
PLATFORM_WINDOWS = 1
PLATFORM_MACOS = 2
PLATFORM_UNKNOWN = 3

# setproctitle is (optionally) imported
try:
    from setproctitle import setproctitle
except ImportError:
    # silently ignore name change requests
    setproctitle = lambda name: None


def get_platform():
    if hasattr(sys, "getwindowsversion"):
        return PLATFORM_WINDOWS
    elif sys.platform == "darwin":
        return PLATFORM_MACOS
    elif sys.platform.startswith("linux"):
        return PLATFORM_LINUX
    else:
        return PLATFORM_UNKNOWN


def get_external_program_location(key):
    extensions = ["", ".exe"]
    potential_names = ["%s%s" % (key, ext) for ext in extensions]
    windows_program_directories = {'inkscape': ['Inkscape'],
            'pstoedit': ['pstoedit']}
    # check the windows path via win32api
    try:
        import win32api
        handle, location = win32api.FindExecutable(key)
        if location:
            return location
    except:
        # Wildcard exeception to match "ImportError" and "pywintypes.error"
        # (for "not found").
        pass
    # go through the PATH environment variable
    if "PATH" in os.environ:
        path_env = os.environ["PATH"]
        for one_dir in path_env.split(os.pathsep):
            for basename in potential_names:
                location = os.path.join(one_dir, basename)
                if os.path.isfile(location):
                    return location
    # do a manual scan in the programs directory (only for windows)
    try:
        from win32com.shell import shellcon, shell            
        program_dir = shell.SHGetFolderPath(0, shellcon.CSIDL_PROGRAM_FILES, 0, 0)
    except ImportError:
        # no other options for non-windows systems
        return None
    # scan the program directory
    for sub_dir in windows_program_directories[key]:
        for basename in potential_names:
            location = os.path.join(program_dir, sub_dir, basename)
            if os.path.isfile(location):
                return location
    # nothing found
    return None


class ProgressCounter:

    def __init__(self, max_value, update_callback):
        self.max_value = max_value
        self.current_value = 0
        self.update_callback = update_callback

    def increment(self, increment=1):
        self.current_value += increment
        return self.update()

    def update(self):
        if self.update_callback:
            # "True" means: "quit requested via GUI"
            return self.update_callback(percent=self.get_percent())
        else:
            return False

    def get_percent(self):
        return 100.0 * self.current_value / self.max_value

