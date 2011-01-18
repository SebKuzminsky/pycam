# -*- coding: utf-8 -*-
"""
$Id$

Copyright 2010 Lars Kruse <devel@sumpfralle.de>
Copyright 2008-2009 Lode Leroy

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

from pycam.Exporters.gcode import gcode
import os


DEFAULT_HEADER = ("G40 (disable tool radius compensation)",
                "G49 (disable_tool_length_compensation)",
                "G80 (cancel_modal_motion)",
                "G54 (select_coordinate_system_1)",
                "G90 (use_absolute_coordinates)")

PATH_MODES = {"exact_path": 0, "exact_stop": 1, "continuous": 2}


class GCodeGenerator:

    def __init__(self, destination, metric_units=True, safety_height=0.0,
            toggle_spindle_status=False, header=None, comment=None):
        if isinstance(destination, basestring):
            # open the file
            self.destination = file(destination,"w")
            self._close_stream_on_exit = True
        else:
            # assume that "destination" is something like a StringIO instance
            # or an open file
            self.destination = destination
            # don't close the stream if we did not open it on our own
            self._close_stream_on_exit = False
        self.safety_height = safety_height
        self.gcode = gcode(safetyheight=self.safety_height)
        self.toggle_spindle_status = toggle_spindle_status
        self.comment = comment
        self._finished = False
        if comment:
            self.add_comment(comment)
        if header is None:
            self.append(DEFAULT_HEADER)
        else:
            self.append(header)
        if metric_units:
            self.append("G21 (metric)")
        else:
            self.append("G20 (imperial)")

    def set_speed(self, feedrate=None, spindle_speed=None):
        if not feedrate is None:
            self.append("F%.4f" % feedrate)
        if not spindle_speed is None:
            self.append("S%.4f" % spindle_speed)

    def set_path_mode(self, mode, motion_tolerance=None,
            naive_cam_tolerance=None):
        result = ""
        if mode == PATH_MODES["exact_path"]:
            result = "G61 (exact path mode)"
        elif mode == PATH_MODES["exact_stop"]:
            result = "G61.1 (exact stop mode)"
        elif mode == PATH_MODES["continuous"]:
            if motion_tolerance is None:
                result = "G64 (continuous mode with maximum speed)"
            elif naive_cam_tolerance is None:
                result = "G64 P%f (continuous mode with tolerance)" \
                        % motion_tolerance
            else:
                result = ("G64 P%f Q%f (continuous mode with tolerance and " \
                        + "cleanup") % (motion_tolerance, naive_cam_tolerance)
        else:
            raise ValueError("GCodeGenerator: invalid path mode (%s)" \
                    % str(mode))
        self.append(result)

    def add_moves(self, moves, tool_id=None, comment=None):
        if not comment is None:
            self.add_comment(comment)
        # move straight up to safety height
        self.append(self.gcode.safety())
        if not tool_id is None:
            self.append("T%d M6" % tool_id)
        if self.toggle_spindle_status:
            self.append("M3 (start spindle)")
            self.append(self.gcode.delay(2))
        # At minimum this will stop the duplicate gcode
        # And this is a place holder for when the GUI is linked
        ResLimitX = 0.0001
        ResLimitY = 0.0001
        ResLimitZ = 0.0001
        OldPosition = None
        for pos, rapid in moves:
            if OldPosition == None:
                OldPosition = pos
            NewPosition = pos
            if rapid:
                self.append(self.gcode.rapid(pos.x, pos.y, pos.z))
            else:
                # make sure we arent putting out values with no motion
                if NewPosition.x - OldPosition.x >= ResLimitX \
                or NewPosition.x - OldPosition.x <= -ResLimitX \
                or NewPosition.y - OldPosition.y >= ResLimitY \
                or NewPosition.y - OldPosition.y <= -ResLimitY \
                or NewPosition.z - OldPosition.z >= ResLimitZ \
                or NewPosition.z - OldPosition.z <= -ResLimitZ:
                    self.append(self.gcode.cut(pos.x, pos.y, pos.z))
                    OldPosition = pos
        # go back to safety height
        self.append(self.gcode.safety())
        if self.toggle_spindle_status:
            self.append("M5 (stop spindle)")

    def finish(self):
        self.append(self.gcode.safety())
        self.append("M2 (end program)")
        self._finished = True

    def add_comment(self, comment):
        if isinstance(comment, basestring):
            lines = comment.split(os.linesep)
        else:
            lines = comment
        for line in lines:
            self.append(";%s" % line)

    def append(self, command):
        if self._finished:
            raise TypeError("GCodeGenerator: can't add further commands to a " \
                    + "finished GCodeGenerator instance: %s" % str(command))
        if isinstance(command, basestring):
            command = [command]
        for line in command:
            self.destination.write(line + os.linesep)

