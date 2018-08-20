# -*- coding: utf-8 -*-
"""
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

import collections

import pycam.Utils
import pycam.Utils.log


_log = pycam.Utils.log.get_logger()


DetectedFileType = collections.namedtuple("DetectedFileType", ("extension", "importer", "uri"))


def detect_file_type(filename, quiet=False):
    import pycam.Importers.DXFImporter
    import pycam.Importers.PSImporter
    import pycam.Importers.STLImporter
    from pycam.Importers.SVGDirectImporter import import_model as import_model_from_svg
    # also accept URI input
    uri = pycam.Utils.URIHandler(filename)
    filename = uri.get_path()
    # check all listed importers
    # TODO: this should be done by evaluating the header of the file
    if filename.lower().endswith(".stl"):
        return DetectedFileType("stl", pycam.Importers.STLImporter.ImportModel, uri)
    elif filename.lower().endswith(".dxf"):
        return DetectedFileType("dxf", pycam.Importers.DXFImporter.import_model, uri)
    elif filename.lower().endswith(".svg"):
        return DetectedFileType("svg", import_model_from_svg, uri)
    elif filename.lower().endswith(".eps") \
            or filename.lower().endswith(".ps"):
        return DetectedFileType("ps", pycam.Importers.PSImporter.import_model, uri)
    else:
        if not quiet:
            _log.error("Importers: Failed to detect the model type of '%s'. Is the file extension "
                       "(stl/dxf/svg/eps/ps) correct?", filename)
        return None
