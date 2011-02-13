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

import decimal
import os


DEFAULT_HEADER = ("G40 (disable tool radius compensation)",
                "G49 (disable_tool_length_compensation)",
                "G80 (cancel_modal_motion)",
                "G54 (select_coordinate_system_1)",
                "G90 (use_absolute_coordinates)")

PATH_MODES = {"exact_path": 0, "exact_stop": 1, "continuous": 2}
MAX_DIGITS = 12


def _get_num_of_significant_digits(number):
    # use only positive numbers
    number = abs(number)
    max_diff = 0.1 ** MAX_DIGITS
    if number <= max_diff:
        # input value is smaller than the smallest usable number
        return MAX_DIGITS
    elif number >= 1:
        # no negative number of significant digits
        return 0
    else:
        for digit in range(1, MAX_DIGITS):
            shifted = number * (10 ** digit)
            if shifted - int(shifted) < max_diff:
                return digit
        else:
            return MAX_DIGITS


def _get_num_converter(step_width):
    digits=_get_num_of_significant_digits(step_width)
    format_string = "%%.%df" % digits
    return lambda number: decimal.Decimal(format_string % number)
    

class GCodeGenerator:

    NUM_OF_AXES = 3

    def __init__(self, destination, metric_units=True, safety_height=0.0,
            toggle_spindle_status=False, header=None, comment=None,
            minimum_steps=None):
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
        self.toggle_spindle_status = toggle_spindle_status
        self.comment = comment
        # define all axes steps and the corresponding formatters
        self._axes_formatter = []
        if not minimum_steps:
            # default: minimum steps for all axes = 0.0001
            minimum_steps = [0.0001]
        for i in range(self.NUM_OF_AXES):
            if i < len(minimum_steps):
                step_width = minimum_steps[i]
            else:
                step_width = minimum_steps[-1]
            conv = _get_num_converter(step_width)
            self._axes_formatter.append((conv(step_width), conv))
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
        self.last_position = [None, None, None]
        self.last_rapid = None

    def set_speed(self, feedrate=None, spindle_speed=None):
        if not feedrate is None:
            self.append("F%.5f" % feedrate)
        if not spindle_speed is None:
            self.append("S%.5f" % spindle_speed)

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
                        + "cleanup)") % (motion_tolerance, naive_cam_tolerance)
        else:
            raise ValueError("GCodeGenerator: invalid path mode (%s)" \
                    % str(mode))
        self.append(result)

    def add_moves(self, moves, tool_id=None, comment=None):
        if not comment is None:
            self.add_comment(comment)
        # move straight up to safety height
        self.add_move_to_safety()
        if not tool_id is None:
            self.append("T%d M6" % tool_id)
        if self.toggle_spindle_status:
            self.append("M3 (start spindle)")
            self.append("G04 P%d (wait for %d seconds)" % (2, 2))
        for pos, rapid in moves:
            self.add_move(pos, rapid=rapid)
        # go back to safety height
        self.add_move_to_safety()
        if self.toggle_spindle_status:
            self.append("M5 (stop spindle)")
        # make sure that all sections are independent of each other
        self.last_position = [None, None, None]
        self.last_rapid = None

    def add_move_to_safety(self):
        new_pos = [None, None, self.safety_height]
        self.add_move(new_pos, rapid=True)

    def add_move(self, position, rapid=False):
        """ add the GCode for a machine move to 'position'. Use rapid (G00) or
        normal (G01) speed.

        @value position: the new position
        @type position: Point or list(float)
        @value rapid: is this a rapid move?
        @type rapid: bool
        """
        new_pos = []
        for index, attr in enumerate("xyz"):
            conv = self._axes_formatter[index][1]
            if hasattr(position, attr):
                value = getattr(position, attr)
            else:
                value = position[index]
            if value is None:
                new_pos.append(None)
            else:
                new_pos.append(conv(value))
        # check if there was a significant move
        no_diff = True
        for index in range(len(new_pos)):
            if new_pos[index] is None:
                continue
            if self.last_position[index] is None:
                no_diff = False
                break
            diff = new_pos[index] - self.last_position[index]
            if diff > self._axes_formatter[index][0]:
                no_diff = False
                break
        if no_diff:
            # we can safely skip this move
            return
        # compose the position string
        pos_string = []
        for index, axis_spec in enumerate("XYZ"):
            if new_pos[index] is None:
                continue
            if not self.last_position or \
                    (new_pos[index] != self.last_position[index]):
                pos_string.append("%s%s" % (axis_spec, new_pos[index]))
                self.last_position[index] = new_pos[index]
        if rapid == self.last_rapid:
            prefix = "   "
        elif rapid:
            prefix = "G00"
        else:
            prefix = "G01"
        self.append(prefix + " ".join(pos_string))

    def finish(self):
        self.add_move_to_safety()
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

