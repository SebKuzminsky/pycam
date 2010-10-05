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

import pycam.Utils.log
# multiprocessing is imported later
#import multiprocessing


log = pycam.Utils.log.get_logger()


# possible values:
#   None: not initialized
#   False: no threading
#   multiprocessing: the multiprocessing module is impored and enabled
__multiprocessing = None

# needs to be initialized, if multiprocessing is enabled
__num_of_processes = None

__lock = None


def init_threading(number_of_processes=None):
    global __multiprocessing, __num_of_processes, __lock
    try:
        import multiprocessing
        mp_is_available = True
    except ImportError:
        mp_is_available = False
    if not mp_is_available:
        __multiprocessing = False
    else:
        if number_of_processes is None:
            # use defaults
            # don't enable threading for a single cpu
            if multiprocessing.cpu_count() > 1:
                __multiprocessing = multiprocessing
                __num_of_processes = multiprocessing.cpu_count()
            else:
                __multiprocessing = False
        elif number_of_processes < 1:
            __multiprocessing = False
        else:
            __multiprocessing = multiprocessing
            __num_of_processes = number_of_processes
    # send the configured state to the logger
    if __multiprocessing is False:
        log.info("Disabled multi-threading")
    else:
        __lock = multiprocessing.Lock()
        log.info("Enabled multi-threading with %d parallel processes" % __num_of_processes)


def run_in_parallel(func, args, unordered=False, disable_multiprocessing=False):
    global __multiprocessing, __num_of_processes
    if __multiprocessing is None:
        # threading was not configured before
        init_threading()
    if __multiprocessing and not disable_multiprocessing:
        # use the number of CPUs as the default number of worker threads
        pool = __multiprocessing.Pool(__num_of_processes)
        if unordered:
            imap_func = pool.imap_unordered
        else:
            imap_func = pool.imap
        # Beware: we may not return "pool.imap" or "pool.imap_unordered"
        # directly. It would somehow loose the focus and just hang infinitely.
        # Thus we wrap our own generator around it.
        for result in imap_func(func, args):
            yield result
    else:
        for arg in args:
            yield func(arg)

def acquire_lock():
    if __multiprocessing:
        __lock.acquire()

def release_lock():
    if __multiprocessing:
        __lock.release()

