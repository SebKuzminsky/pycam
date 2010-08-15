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

__all__ = ["ConsoleProgressBar"]

import os

class ConsoleProgressBar(object):

    def __init__(self, output):
        self.output = output
        self.last_length = 0
        self.text = ""
        self.percent = 0
        
    def update(self, text=None, percent=None, **kwargs):
        if not text is None:
            self.text = text
        if not percent is None:
            self.percent = int(percent)
        if self.last_length > 0:
            # delete the previous line
            self.output.write("\x08" * self.last_length)
        result = "%d%% %s" % (self.percent, self.text)
        self.last_length = len(result)
        self.output.write(result)
        self.output.flush()

    def finish(self):
        self.output.write(os.linesep)

