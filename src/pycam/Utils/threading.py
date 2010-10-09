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
#from multiprocessing.managers import SyncManager
import Queue
import time

DEFAULT_PORT = 1250


log = pycam.Utils.log.get_logger()


# possible values:
#   None: not initialized
#   False: no threading
#   multiprocessing: the multiprocessing module is impored and enabled
__multiprocessing = None

# needs to be initialized, if multiprocessing is enabled
__num_of_processes = None

__manager = None
__workers = None


def init_threading(number_of_processes=None, host=None):
    global __multiprocessing, __num_of_processes, __manager, __workers
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
        log.info("Enabled multi-threading with %d parallel processes" % __num_of_processes)
    # initialize the manager
    if __multiprocessing:
        if host is None:
            address = ('', DEFAULT_PORT)
        else:
            if ":" in host:
                host, port = host.split(":", 1)
                try:
                    port = int(port)
                except ValueError:
                    log.warning(("Invalid port specified: '%s' - using default " \
                            + "port (%d) instead") % (port, DEFAULT_PORT))
                    port = DEFAULT_PORT
            else:
                port = DEFAULT_PORT
            address = (host, port)
        tasks_queue = multiprocessing.Queue()
        results_queue = multiprocessing.Queue()
        from multiprocessing.managers import BaseManager
        class TaskManager(BaseManager):
            pass
        TaskManager.register("tasks", callable=lambda: tasks_queue)
        TaskManager.register("results", callable=lambda: results_queue)
        __manager = TaskManager(address=address)
        if not host is None:
            __manager.connect()
        else:
            __manager.start()

def _handle_tasks(tasks, results):
    while not tasks.empty():
        try:
            func, args = tasks.get(timeout=1.0)
            results.put(func(args))
        except Queue.Empty:
            break

def run_in_parallel_remote(func, args_list, unordered=False,
        disable_multiprocessing=False, host=None):
    global __multiprocessing, __num_of_processes, __manager
    if __multiprocessing is None:
        # threading was not configured before
        init_threading()
    if __multiprocessing and not disable_multiprocessing:
        tasks_queue = __manager.tasks()
        results_queue = __manager.results()
        for args in args_list:
            tasks_queue.put((func, args))
        workers = []
        for index in range(__num_of_processes):
            worker = __multiprocessing.Process(name="task-%d" % index,
                    target=_handle_tasks, args=(tasks_queue, results_queue))
            worker.start()
            workers.append(worker)
        for index in range(len(args_list)):
            try:
                yield results_queue.get()
            except GeneratorExit:
                # catch this specific (silent) exception and kill all workers
                for w in workers:
                    w.terminate()
                # re-raise the GeneratorExit exception to finish destruction
                raise
    else:
        for args in args_list:
            yield func(args)

def run_in_parallel_local(func, args, unordered=False, disable_multiprocessing=False):
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

#run_in_parallel = run_in_parallel_local
run_in_parallel = run_in_parallel_remote

