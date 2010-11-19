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

from pycam.Geometry.Letters import Charset
from pycam.Geometry.Line import Line
from pycam.Geometry.Point import Point
from pycam.Geometry import get_points_of_arc
import pycam.Utils.log

log = pycam.Utils.log.get_logger()


class _CXFParseError(BaseException):
    pass


class _LineFeeder(object):

    def __init__(self, items):
        self.items = items
        self._len = len(items)
        self.index = 0

    def consume(self):
        if not self.is_empty():
            result = self.get()
            self.index += 1
        else:
            result = None
        return result

    def get(self):
        if not self.is_empty():
            return self.items[self.index].strip()
        else:
            return None

    def is_empty(self):
        return self.index >= self._len

    def get_index(self):
        return self.index + 1


class CXFParser(object):

    META_KEYWORDS = ("letterspacing", "wordspacing", "linespacingfactor",
            "encoding")
    META_KEYWORDS_MULTI = ("author", "name")


    def __init__(self, stream, callback=None):
        self.letters = {}
        self.meta = {}
        self.callback = callback
        feeder = _LineFeeder(stream.readlines())
        while not feeder.is_empty():
            line = feeder.consume()
            if not line:
                # ignore
                pass
            elif line.startswith("#"):
                # comment or meta data
                content = line[1:].split(":", 1)
                if len(content) == 2:
                    key = content[0].lower().strip()
                    value = content[1].strip()
                    if key in self.META_KEYWORDS:
                        try:
                            if key != "encoding":
                                self.meta[key] = float(value)
                            else:
                                self.meta[key] = value
                        except ValueError:
                            raise _CXFParseError("Invalid meta information " \
                                    + "in line %d" % feeder.get_index())
                    elif key in self.META_KEYWORDS_MULTI:
                        if key in self.meta:
                            self.meta[key].append(value)
                        else:
                            self.meta[key] = [value]
                    else:
                        # unknown -> ignore
                        pass
            elif line.startswith("["):
                # Update the GUI from time to time.
                # This is useful for the big unicode font.
                if self.callback and (len(self.letters) % 100 == 0):
                    self.callback.update()
                if (len(line) >= 3) and (line[2] == "]"):
                    # single character
                    character = line[1]
                elif (len(line) >= 6) and (line[5] == "]"):
                    # unicode character (e.g. "[1ae4]")
                    try:
                        character = unichr(int(line[1:5], 16))
                    except ValueError:
                        raise _CXFParseError("Failed to parse unicode " \
                                + "character at line %d" % feeder.get_index())
                elif (len(line) > 3) and (line.find("]") > 2):
                    # read UTF8 (qcad 1 compatibility)
                    end_bracket = line.find("] ")
                    text = line[1:end_bracket]
                    character = text.decode("utf-8")[0]
                else:
                    # unknown format
                    raise _CXFParseError("Failed to parse character at line " \
                            + "%d" % feeder.get_index())
                # parse the following lines up to the next empty line
                char_definition = []
                while not feeder.is_empty() and (len(feeder.get()) > 0):
                    line = feeder.consume()
                    # split the line after the first whitespace
                    type_def, coord_string = line.split(None, 1)
                    coords = [float(value) for value in coord_string.split(",")]
                    type_char = line[0].upper()
                    if (type_def == "L") and (len(coords) == 4):
                        # line
                        p1 = Point(coords[0], coords[1], 0)
                        p2 = Point(coords[2], coords[3], 0)
                        char_definition.append(Line(p1, p2))
                    elif (type_def in ("A", "AR")) and (len(coords) == 5):
                        # arc
                        previous = None
                        center = Point(coords[0], coords[1], 0)
                        radius = coords[2]
                        start_angle, end_angle = coords[3], coords[4]
                        if type_def == "AR":
                            # reverse the arc
                            start_angle, end_angle = end_angle, start_angle
                        for p in get_points_of_arc(center, radius, start_angle,
                                end_angle):
                            current = Point(p[0], p[1], 0)
                            if not previous is None:
                                char_definition.append(Line(previous, current))
                            previous = current
                    else:
                        raise _CXFParseError("Failed to read item coordinates" \
                                + " in line %d" % feeder.get_index())
                self.letters[character] = char_definition
            else:
                # unknown line format
                raise _CXFParseError("Failed to parse unknown content in " \
                        + "line %d" % feeder.get_index())


def import_font(filename, callback=None):
    try:
        infile = open(filename,"r")
    except IOError, err_msg:
        log.error("CXFImporter: Failed to read file (%s): %s" \
                % (filename, err_msg))
        return None
    try:
        parsed_font = CXFParser(infile, callback=callback)
    except _CXFParseError, err_msg:
        log.warn("CFXImporter: Skipped font defintion file '%s'. Reason: %s." \
                % (filename, err_msg))
        return None
    charset = Charset(**parsed_font.meta)
    for key, value in parsed_font.letters.iteritems():
        charset.add_character(key, value)
    log.info("CXFImporter: Imported CXF font from '%s': %d letters" \
            % (filename, len(parsed_font.letters)))
    infile.close()
    return charset

