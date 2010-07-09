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

import logging

def get_logger(suffix=None):
    name = "PyCAM"
    if suffix:
        name += ".%s" % str(suffix)
    logger = logging.getLogger(name)
    if len(logger.handlers) == 0:
        init_logger(logger)
    return logger

def init_logger(log, logfilename=None):
    if logfilename:
        datetime_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        logfile_hander = logging.FileHandler(logfilename)
        logfile_handler.setFormatter(datetime_format)
        log.addHandler(logfile_handler)
    console_output = logging.StreamHandler()
    log.addHandler(console_output)
    log.setLevel(logging.INFO)

def add_stream(stream):
    log = get_logger()
    logstream = logging.StreamHandler(stream)
    log.addHandler(logstream)

