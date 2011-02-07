# -*- coding: utf-8 -*-
"""
$ID$

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

from pycam.Geometry.Point import Point
from pycam.Geometry.Line import Line
import pycam.Geometry.Model
import pycam.Geometry
import pycam.Utils.log

log = pycam.Utils.log.get_logger()


class DXFParser(object):

    # see http://www.autodesk.com/techpubs/autocad/acad2000/dxf/group_code_value_types_dxf_01.htm
    MAX_CHARS_PER_LINE = 2049

    KEYS = {
        "MARKER": 0,
        "START_X": 10,
        "START_Y": 20,
        "START_Z": 30,
        "END_X": 11,
        "END_Y": 21,
        "END_Z": 31,
        "RADIUS": 40,
        "ANGLE_START": 50,
        "ANGLE_END": 51,
        "COLOR": 62,
    }

    def __init__(self, inputstream, color_as_height=False, callback=None):
        self.inputstream = inputstream
        self.line_number = 0
        self.lines = []
        self._input_stack = []
        self._color_as_height = color_as_height
        self.callback = callback
        self.parse_content()
        self.optimize_line_order()

    def get_model(self):
        return {"lines": self.lines}

    def optimize_line_order(self):
        groups = []
        current_group = []
        groups.append(current_group)
        remaining_lines = self.lines[:]
        while remaining_lines:
            if self.callback and self.callback():
                return
            if not current_group:
                current_group.append(remaining_lines.pop(0))
            else:
                first_line = current_group[0]
                last_line = current_group[-1]
                for line in remaining_lines:
                    if last_line.p2 == line.p1:
                        current_group.append(line)
                        remaining_lines.remove(line)
                        break
                    if first_line.p1 == line.p2:
                        current_group.insert(0, line)
                        remaining_lines.remove(line)
                        break
                else:
                    current_group = []
                    groups.append(current_group)
        def get_distance_between_groups(group1, group2):
            forward = group1[-1].p2.sub(group2[0].p1).norm
            backward = group2[-1].p2.sub(group1[0].p1).norm
            return min(forward, backward)
        remaining_groups = groups[:]
        ordered_groups = []
        while remaining_groups:
            if not ordered_groups:
                ordered_groups.append(remaining_groups.pop(0))
            else:
                current_group = ordered_groups[-1]
                closest_distance = None
                for cmp_group in remaining_groups:
                    cmp_distance = get_distance_between_groups(current_group,
                            cmp_group)
                    if (closest_distance is None) \
                            or (cmp_distance < closest_distance):
                        closest_distance = cmp_distance
                        closest_group = cmp_group
                ordered_groups.append(closest_group)
                remaining_groups.remove(closest_group)
        result = []
        for group in ordered_groups:
            result.extend(group)
        self.lines = result

    def _push_on_stack(self, key, value):
        self._input_stack.append((key, value))

    def _read_key_value(self):
        if self._input_stack:
            return self._input_stack.pop()
        try:
            line1 = self.inputstream.readline(self.MAX_CHARS_PER_LINE).strip()
            line2 = self.inputstream.readline(self.MAX_CHARS_PER_LINE).strip()
        except IOError:
            return None, None
        if not line1 and not line2:
            return None, None
        try:
            line1 = int(line1)
        except ValueError:
            log.warn("DXFImporter: Invalid key in line " \
                    + "%d (int expected): %s" % (self.line_number, line1))
            return None, None
        if line1 in [self.KEYS[key] for key in ("START_X", "START_Y", "START_Z",
                "END_X", "END_Y", "END_Z", "RADIUS", "ANGLE_START",
                "ANGLE_END")]:
            try:
                line2 = float(line2)
            except ValueError:
                log.warn("DXFImporter: Invalid input in line " \
                        + "%d (float expected): %s" % (self.line_number, line2))
                line1 = None
                line2 = None
        elif line1 in (self.KEYS["COLOR"],):
            try:
                line2 = int(line2)
            except ValueError:
                log.warn("DXFImporter: Invalid input in line " \
                        + "%d (int expected): %s" % (self.line_number, line2))
                line1 = None
                line2 = None
        else:
            line2 = line2.upper()
        self.line_number += 2
        return line1, line2

    def parse_content(self):
        key, value = self._read_key_value()
        while (not key is None) \
                and not ((key == self.KEYS["MARKER"]) and (value == "EOF")):
            if self.callback and self.callback():
                return
            if key == self.KEYS["MARKER"]:
                if value in ("SECTION", "TABLE", "LAYER", "ENDTAB", "ENDSEC"):
                    # we don't handle these meta-information
                    pass
                elif value == "LINE":
                    self.parse_line()
                elif value == "LWPOLYLINE":
                    self.parse_polyline()
                elif value == "ARC":
                    self.parse_arc()
                else:
                    # not supported
                    log.warn("DXFImporter: Ignored unsupported element in " \
                            + "line %d: %s" % (self.line_number, value))
            key, value = self._read_key_value()

    def parse_polyline(self):
        points = []
        def add_point(p_array):
            # fill all "None" values with zero
            for index in range(len(p_array)):
                if p_array[index] is None:
                    if (index == 0) or (index == 1):
                        log.debug("DXFImporter: weird LWPOLYLINE input " + \
                                "date in line %d: %s" % \
                                (self.line_number, p_array))
                    p_array[index] = 0
            points.append(Point(p_array[0], p_array[1], p_array[2]))
        start_line = self.line_number
        current_point = [None, None, None]
        key, value = self._read_key_value()
        while (not key is None) and (key != self.KEYS["MARKER"]):
            if key == self.KEYS["START_X"]:
                axis = 0
            elif key == self.KEYS["START_Y"]:
                axis = 1
            elif not self._color_as_height and (key == self.KEYS["START_Z"]):
                axis = 2
            elif self._color_as_height and (key == self.KEYS["COLOR"]):
                # interpret the color as the height
                axis = 2
                value = float(value) / 255
            else:
                axis = None
            if not axis is None:
                if current_point[axis] is None:
                    # The current point definition is not complete, yet.
                    current_point[axis] = value
                else:
                    # The current point seems to be complete.
                    add_point(current_point)
                    current_point = [None, None, None]
                    current_point[axis] = value
            key, value = self._read_key_value()
        end_line = self.line_number
        # The last lines were not used - they are just the marker for the next
        # item.
        if not key is None:
            self._push_on_stack(key, value)
        # check if there is a remaining item in "current_point"
        if len(current_point) != current_point.count(None):
            add_point(current_point)
        if len(points) < 2:
            # too few points for a polyline
            log.warn("DXFImporter: Empty LWPOLYLINE definition between line " \
                    + "%d and %d" % (start_line, end_line))
        else:
            for index in range(len(points) - 1):
                point = points[index]
                next_point = points[index + 1]
                if point != next_point:
                    self.lines.append(Line(point, next_point))
                else:
                    log.warn("DXFImporter: Ignoring zero-length LINE " \
                            + "(between input line %d and %d): %s" \
                            % (start_line, end_line, point))

    def parse_line(self):
        start_line = self.line_number
        # the z-level defaults to zero (for 2D models)
        p1 = [None, None, 0]
        p2 = [None, None, 0]
        color = None
        key, value = self._read_key_value()
        while (not key is None) and (key != self.KEYS["MARKER"]):
            if key == self.KEYS["START_X"]:
                p1[0] = value
            elif key == self.KEYS["START_Y"]:
                p1[1] = value
            elif key == self.KEYS["START_Z"]:
                p1[2] = value
            elif key == self.KEYS["END_X"]:
                p2[0] = value
            elif key == self.KEYS["END_Y"]:
                p2[1] = value
            elif key == self.KEYS["END_Z"]:
                p2[2] = value
            elif key == self.KEYS["COLOR"]:
                color = value
            else:
                pass
            key, value = self._read_key_value()
        end_line = self.line_number
        # The last lines were not used - they are just the marker for the next
        # item.
        if not key is None:
            self._push_on_stack(key, value)
        if (None in p1) or (None in p2):
            log.warn("DXFImporter: Incomplete LINE definition between line " \
                    + "%d and %d" % (start_line, end_line))
        else:
            if self._color_as_height and (not color is None):
                # use the color code as the z coordinate
                p1[2] = float(color) / 255
                p2[2] = float(color) / 255
            line = Line(Point(p1[0], p1[1], p1[2]), Point(p2[0], p2[1], p2[2]))
            if line.len > 0:
                self.lines.append(line)
            else:
                log.warn("DXFImporter: Ignoring zero-length LINE (between " \
                        + "input line %d and %d): %s" % (start_line, end_line,
                        line))
    def parse_arc(self):
        start_line = self.line_number
        # the z-level defaults to zero (for 2D models)
        center = [None, None, 0]
        color = None
        radius = None
        angle_start = None
        angle_end = None
        key, value = self._read_key_value()
        while (not key is None) and (key != self.KEYS["MARKER"]):
            if key == self.KEYS["START_X"]:
                center[0] = value
            elif key == self.KEYS["START_Y"]:
                center[1] = value
            elif key == self.KEYS["START_Z"]:
                center[2] = value
            elif key == self.KEYS["RADIUS"]:
                radius = value
            elif key == self.KEYS["ANGLE_START"]:
                angle_start = value
            elif key == self.KEYS["ANGLE_END"]:
                angle_end = value
            elif key == self.KEYS["COLOR"]:
                color = value
            else:
                pass
            key, value = self._read_key_value()
        end_line = self.line_number
        # The last lines were not used - they are just the marker for the next
        # item.
        if not key is None:
            self._push_on_stack(key, value)
        if (None in center) or (None in (radius, angle_start, angle_end)):
            log.warn("DXFImporter: Incomplete ARC definition between line " \
                    + "%d and %d" % (start_line, end_line))
        else:
            if self._color_as_height and (not color is None):
                # use the color code as the z coordinate
                center[2] = float(color) / 255
            center = Point(center[0], center[1], center[2])
            xy_point_coords = pycam.Geometry.get_points_of_arc(center, radius,
                    angle_start, angle_end)
            # Somehow the order of points seems to be the opposite of what is
            # expected.
            xy_point_coords.reverse()
            if len(xy_point_coords) > 1:
                for index in range(len(xy_point_coords) - 1):
                    p1 = xy_point_coords[index]
                    p1 = Point(p1[0], p1[1], center.z)
                    p2 = xy_point_coords[index + 1]
                    p2 = Point(p2[0], p2[1], center.z)
                    self.lines.append(Line(p1, p2))
            else:
                log.warn("DXFImporter: Ignoring tiny ARC (between input " + \
                        "line %d and %d): %s / %s (%s - %s)" % (start_line,
                        end_line, center, radius, angle_start, angle_end))

    def check_header(self):
        # TODO: this function is not used?
        # we expect "0" in the first line and "SECTION" in the second one
        key, value = self._read_key_value()
        if (key != self.KEYS["MARKER"]) or (value and (value != "SECTION")):
            log.error("DXFImporter: DXF file header not recognized")
            return None


def import_model(filename, program_locations=None, unit=None,
        color_as_height=False, callback=None):
    try:
        infile = open(filename,"rb")
    except IOError, err_msg:
        log.error("DXFImporter: Failed to read file (%s): %s" \
                % (filename, err_msg))
        return None

    result = DXFParser(infile, color_as_height=color_as_height,
            callback=callback)

    lines = result.get_model()["lines"]

    if callback and callback():
        log.warn("DXFImporter: load model operation was cancelled")
        return None

    if lines:
        model = pycam.Geometry.Model.ContourModel()
        for index, line in enumerate(lines):
            model.append(line)
            # keep the GUI smooth
            if callback and (index % 50 == 0):
                callback()
        # z scaling is always targeted at the 0..1 range
        if color_as_height and (model.minz != model.maxz):
            # scale z to 1
            scale_z = 1.0 / (model.maxz - model.minz)
            if callback:
                callback(text="Scaling height for multi-layered 2D model")
            log.info("DXFImporter: scaling height for multi-layered 2D model")
            model.scale(scale_x=1.0, scale_y=1.0, scale_z=scale_z,
                    callback=callback)
        # shift the model down to z=0
        if model.minz != 0:
            if callback:
                callback(text="Shifting 2D model down to to z=0")
            model.shift(0, 0, -model.minz, callback=callback)
        log.info("DXFImporter: Imported DXF model: %d lines / %d polygons" \
                % (len(lines), len(model.get_polygons())))
        return model
    else:
        link = "http://sf.net/apps/mediawiki/pycam/?title=SupportedFormats"
        log.error('DXFImporter: No supported elements found in DXF file!\n' \
                + '<a href="%s">Read PyCAM\'s modelling hints.</a>' % link)
        return None

