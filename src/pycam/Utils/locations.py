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

import os
import sys

import pycam.Utils.log


DATA_DIR_ENVIRON_KEY = "PYCAM_DATA_DIR"
FONT_DIR_ENVIRON_KEY = "PYCAM_FONT_DIR"
DATA_BASE_DIRS = [os.path.realpath(os.path.join(os.path.dirname(__file__),
            os.pardir, os.pardir, os.pardir, "share")),
        os.path.join(sys.prefix, "local", "share", "pycam"),
        os.path.join(sys.prefix, "share", "pycam")]
FONTS_SUBDIR = "fonts"
UI_SUBDIR = "ui"


# necessary for "pyinstaller"
if "_MEIPASS2" in os.environ:
    DATA_BASE_DIRS.insert(0, os.path.join(os.path.normpath(os.environ["_MEIPASS2"]), "share"))
# respect an override via an environment setting
if DATA_DIR_ENVIRON_KEY in os.environ:
    DATA_BASE_DIRS.insert(0, os.path.normpath(os.environ[DATA_DIR_ENVIRON_KEY]))
if FONT_DIR_ENVIRON_KEY in os.environ:
    FONT_DIR_OVERRIDE = os.path.normpath(os.environ[FONT_DIR_ENVIRON_KEY])
else:
    FONT_DIR_OVERRIDE = None
FONT_DIRS_FALLBACK = ["/usr/share/librecad/fonts", "/usr/share/qcad/fonts"]


log = pycam.Utils.log.get_logger()


def get_ui_file_location(filename, silent=False):
    return get_data_file_location(os.path.join(UI_SUBDIR, filename), silent=silent)

def get_data_file_location(filename, silent=False):
    for base_dir in DATA_BASE_DIRS:
        test_path = os.path.join(base_dir, filename)
        if os.path.exists(test_path):
            return test_path
    else:
        if not silent:
            lines = []
            lines.append("Failed to locate a resource file (%s) in %s!" \
                    % (filename, DATA_BASE_DIRS))
            lines.append("You can extend the search path by setting the " \
                    + "environment variable '%s'." % str(DATA_DIR_ENVIRON_KEY))
            log.error(os.linesep.join(lines))
        return None

def get_font_dir():
    if FONT_DIR_OVERRIDE:
        if os.path.isdir(FONT_DIR_OVERRIDE):
            return FONT_DIR_OVERRIDE
        else:
            log.warn(("You specified a font dir that does not exist (%s). " \
                    + "I will ignore it.") % FONT_DIR_OVERRIDE)
    font_dir = get_data_file_location(FONTS_SUBDIR, silent=True)
    if not font_dir is None:
        return font_dir
    else:
        log.warn(("Failed to locate the fonts directory '%s' below '%s'. " \
                + "Falling back to '%s'.") \
                 % (FONTS_SUBDIR, DATA_BASE_DIRS, ":".join(FONT_DIRS_FALLBACK)))
        for font_dir_fallback in FONT_DIRS_FALLBACK:
            if os.path.isdir(font_dir_fallback):
                return font_dir_fallback
        else:
            log.warn(("None of the fallback font directories (%s) exist. " + \
                    "No fonts will be available.") % \
                    ":".join(FONT_DIRS_FALLBACK))
            return None

