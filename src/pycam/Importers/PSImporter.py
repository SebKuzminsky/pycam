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

from pycam.Importers.SVGImporter import convert_eps2dxf
import pycam.Importers.DXFImporter
import tempfile
import subprocess
import os

log = pycam.Utils.log.get_logger()


def import_model(filename, program_locations=None, unit=None, callback=None):
    if not os.path.isfile(filename):
        log.error("PSImporter: file (%s) does not exist" % filename)
        return None

    if program_locations and "pstoedit" in program_locations:
        pstoedit_path = program_locations["pstoedit"]
    else:
        pstoedit_path = None

    def remove_temp_file(filename):
        if os.path.isfile(filename):
            try:
                os.remove(filename)
            except OSError, err_msg:
                log.warn("PSImporter: failed to remove temporary file " \
                        + "(%s): %s" % (filename, err_msg))

    # convert eps to dxf via pstoedit
    dxf_file_handle, dxf_file_name = tempfile.mkstemp(suffix=".dxf")
    os.close(dxf_file_handle)
    success = convert_eps2dxf(filename, dxf_file_name, location=pstoedit_path)
    if not success:
        result = None
    elif callback and callback():
        log.warn("PSImporter: load model operation cancelled")
        result = None
    else:
        log.info("Successfully converted PS file to DXF file")
        # pstoedit uses "inch" -> force a scale operation
        result = pycam.Importers.DXFImporter.import_model(dxf_file_name,
                unit=unit, callback=callback)
        if unit == "mm":
            # pstoedit uses inch internally - we need to scale
            if callback:
                callback(text="Scaling model from inch to mm")
            log.info("PSImporter: scaling model from inch to mm")
            scale_x = 25.4
            scale_y = 25.4
            result.scale(scale_x=scale_x, scale_y=scale_y, scale_z=1.0,
                    callback=callback)
    # always remove the dxf file
    remove_temp_file(dxf_file_name)
    return result

