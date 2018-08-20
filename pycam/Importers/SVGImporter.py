# -*- coding: utf-8 -*-
"""
TODO: remove this obsolete SVGImporter
see https://github.com/SebKuzminsky/pycam/issues/118

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
import subprocess
import tempfile

import pycam.Importers.DXFImporter
from pycam.Utils.locations import get_external_program_location
import pycam.Utils
log = pycam.Utils.log.get_logger()


def convert_svg2eps(svg_filename, eps_filename, location=None):
    if location is None:
        location = get_external_program_location("inkscape")
        if location is None:
            location = "inkscape"
    try:
        process = subprocess.Popen(stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   args=[location, "--export-area-page", "--export-eps",
                                         eps_filename, svg_filename])
    except OSError as err_msg:
        log.error("SVGImporter: failed to execute 'inkscape' (%s): %s%sMaybe you need to install "
                  "Inkscape (http://inkscape.org)?", location, err_msg, os.linesep)
        return False
    returncode = process.wait()
    if returncode == 0:
        return True
    else:
        log.warn("SVGImporter: failed to convert SVG file (%s) to EPS file (%s): %s",
                 svg_filename, eps_filename, process.stderr.read())
        return False


def convert_eps2dxf(eps_filename, dxf_filename, location=None, unit="mm"):
    if location is None:
        location = get_external_program_location("pstoedit")
        if location is None:
            location = "pstoedit"
    args = [location, "-dt", "-nc", "-f", "dxf:-polyaslines"]
    if unit == "mm":
        # eps uses inch by default - we need to scale
        args.extend(("-xscale", "25.4", "-yscale", "25.4"))
    args.append(eps_filename)
    args.append(dxf_filename)
    try:
        process = subprocess.Popen(stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, args=args)
    except OSError as err_msg:
        log.error("SVGImporter: failed to execute 'pstoedit' (%s): %s%sMaybe you need to install "
                  "pstoedit (http://pstoedit.net)?", location, err_msg, os.linesep)
        return False
    returncode = process.wait()
    if returncode == 0:
        try:
            # pstoedit fails with exitcode=0 if ghostscript is not installed.
            # The resulting file seems to be quite small (268 byte). But it is
            # not certain, that this filesize is fixed in case of this problem.
            if os.path.getsize(dxf_filename) < 280:
                log.warn("SVGImporter: maybe there was a problem with the conversion from EPS "
                         "(%s) to DXF.\nProbably you need to install 'ghostscript' "
                         "(http://pages.cs.wisc.edu/~ghost).", str(eps_filename))
            return True
        except OSError:
            # The dxf file was not created.
            log.warn("SVGImporter: no DXF file was created, even though no error code was "
                     "returned. This seems to be a bug of 'pstoedit'. Please send the original "
                     "model file to the PyCAM developers. Thanks!")
            return False
    elif returncode == -11:
        log.warn("SVGImporter: maybe there was a problem with the conversion from EPS (%s) to "
                 "DXF.\n Users of Ubuntu 'lucid' should install the package 'libpstoedit0c2a' "
                 "from the 'maverick' repository to avoid this warning.", str(eps_filename))
        return True
    else:
        log.warn("SVGImporter: failed to convert EPS file (%s) to DXF file (%s): %s",
                 eps_filename, dxf_filename, process.stderr.read())
        return False


def import_model(filename, program_locations=None, unit="mm", callback=None, **kwargs):
    local_file = False
    if hasattr(filename, "read"):
        infile = filename
        svg_file_handle, svg_file_name = tempfile.mkstemp(suffix=".svg")
        try:
            temp_file = os.fdopen(svg_file_handle, "w")
            temp_file.write(infile.read())
            temp_file.close()
        except IOError as err_msg:
            log.error("SVGImporter: Failed to create temporary local file (%s): %s",
                      svg_file_name, err_msg)
            return
        filename = svg_file_name
    else:
        uri = pycam.Utils.URIHandler(filename)
        if not uri.exists():
            log.error("SVGImporter: file (%s) does not exist", filename)
            return None
        if not uri.is_local():
            # non-local file - write it to a temporary file first
            svg_file_handle, svg_file_name = tempfile.mkstemp(suffix=".svg")
            os.close(svg_file_handle)
            log.debug("Retrieving SVG file for local access: %s -> %s", uri, svg_file_name)
            if not uri.retrieve_remote_file(svg_file_name, callback=callback):
                log.error("SVGImporter: Failed to retrieve the SVG model file: %s -> %s",
                          uri, svg_file_name)
            filename = svg_file_name
        else:
            filename = uri.get_local_path()
            local_file = True

    if program_locations and "inkscape" in program_locations:
        inkscape_path = program_locations["inkscape"]
    else:
        inkscape_path = None

    if program_locations and "pstoedit" in program_locations:
        pstoedit_path = program_locations["pstoedit"]
    else:
        pstoedit_path = None

    # the "right" way would be:
    # inkscape --print='| pstoedit -dt -f dxf:-polyaslines - -' input.svg
    # Sadly a bug in v0.47 breaks this:
    # https://bugs.launchpad.net/inkscape/+bug/511361

    # convert svg to eps via inkscape
    eps_file_handle, eps_file_name = tempfile.mkstemp(suffix=".eps")
    os.close(eps_file_handle)
    success = convert_svg2eps(filename, eps_file_name, location=inkscape_path)

    def remove_temp_file(filename):
        if os.path.isfile(filename):
            try:
                os.remove(filename)
            except OSError as err_msg:
                log.warn("SVGImporter: failed to remove temporary file (%s): %s",
                         filename, err_msg)

    # remove the temporary file
    if not local_file:
        remove_temp_file(svg_file_name)
    if not success:
        remove_temp_file(eps_file_name)
        return None
    if callback and callback():
        remove_temp_file(eps_file_name)
        log.warn("SVGImporter: load model operation was cancelled")
        return None
    log.info("Successfully converted SVG file to EPS file")

    # convert eps to dxf via pstoedit
    dxf_file_handle, dxf_file_name = tempfile.mkstemp(suffix=".dxf")
    os.close(dxf_file_handle)
    success = convert_eps2dxf(eps_file_name, dxf_file_name, unit=unit, location=pstoedit_path)
    # we don't need the eps file anymore
    remove_temp_file(eps_file_name)
    if not success:
        result = None
    elif callback and callback():
        log.warn("SVGImporter: load model operation was cancelled")
        result = None
    else:
        log.info("Successfully converted EPS file to DXF file")
        result = pycam.Importers.DXFImporter.import_model(dxf_file_name, unit=unit,
                                                          color_as_height=True, callback=callback)
    # always remove the dxf file
    remove_temp_file(dxf_file_name)
    return result
