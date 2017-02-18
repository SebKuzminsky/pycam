# -*- coding: utf-8 -*-
"""

Copyright 2012 Lars Kruse <devel@sumpfralle.de>

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

import pycam.Utils.log
import pycam.Toolpath.Filters
from pycam.Toolpath import MOVE_STRAIGHT, MOVE_STRAIGHT_RAPID, MACHINE_SETTING, COMMENT

_log = pycam.Utils.log.get_logger()


class BaseGenerator(object):

    def __init__(self, destination):
        if isinstance(destination, basestring):
            # open the file
            self.destination = file(destination, "w")
            self._close_stream_on_exit = True
        else:
            # assume that "destination" is something like a StringIO instance
            # or an open file
            self.destination = destination
            # don't close the stream if we did not open it on our own
            self._close_stream_on_exit = False
        self._filters = []
        self._cache = {}
        self.add_header()

    def _get_cache(self, key, default_value):
        return self._cache.get(key, default_value)

    def add_filters(self, filters):
        self._filters.extend(filters)
        self._filters.sort()

    def add_comment(self, comment):
        raise NotImplementedError("someone forgot to implement 'add_comment'")

    def add_command(self, command, comment=None):
        raise NotImplementedError("someone forgot to implement 'add_command'")

    def add_move(self, coordinates, is_rapid=False):
        raise NotImplementedError("someone forgot to implement 'add_move'")

    def add_footer(self):
        raise NotImplementedError("someone forgot to implement 'add_footer'")

    def finish(self):
        self.add_footer()
        if self._close_stream_on_exit:
            self.destination.close()

    def add_moves(self, moves, filters=None):
        # combine both lists/tuples in a type-agnostic way
        all_filters = list(self._filters)
        if filters:
            all_filters.extend(filters)
        filtered_moves = pycam.Toolpath.Filters.get_filtered_moves(moves, all_filters)
        for move_type, args in filtered_moves:
            if move_type in (MOVE_STRAIGHT, MOVE_STRAIGHT_RAPID):
                is_rapid = move_type == MOVE_STRAIGHT_RAPID
                self.add_move(args, is_rapid)
                self._cache["position"] = args
                self._cache["rapid_move"] = is_rapid
            elif move_type == COMMENT:
                self.add_comment(args)
            elif move_type == MACHINE_SETTING:
                key, value = args
                func_name = "command_%s" % key
                if hasattr(self, func_name):
                    _log.debug("GCode: machine setting '%s': %s", key, value)
                    getattr(self, func_name)(value)
                    self._cache[key] = value
                    self._cache["rapid_move"] = None
                else:
                    _log.warn("The current GCode exporter does not support the machine setting "
                              "'%s=%s' -> ignore", key, value)
            else:
                _log.warn("A non-basic toolpath item (%d -> %s) remained in the queue -> ignore",
                          move_type, args)
