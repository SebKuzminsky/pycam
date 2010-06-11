# -*- coding: utf-8 -*-
"""
$Id$

Copyright 2008 Lode Leroy
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

__all__ = ["STLImporter", "DXFImporter", "TestModel"]

import DXFImporter
import STLImporter

import os
import sys

def detect_file_type(filename):
    failure = (None, None)
    if not os.path.isfile(filename):
        return failure
    else:
        # check all listed importers
        # TODO: this should be done by evaluating the header of the file
        if filename.endswith(".stl"):
            return ("stl", STLImporter.ImportModel)
        elif filename.endswith(".dxf"):
            return ("dxf", DXFImporter.import_model)
        else:
            print >>sys.stderr, "Failed to detect the model type of '%s'." \
                    % filename + " Is the file extension (.stl/.dxf) correct?"
            failure

