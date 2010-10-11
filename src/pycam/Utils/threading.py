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
import random
import uuid
import time
import os

DEFAULT_PORT = 1250


log = pycam.Utils.log.get_logger()

#TODO: create one or two classes for these functions (to get rid of the globals)

# possible values:
#   None: not initialized
#   False: no threading
#   multiprocessing: the multiprocessing module is impored and enabled
__multiprocessing = None

# needs to be initialized, if multiprocessing is enabled
__num_of_processes = None

__manager = None
__closing = None
__task_source_uuid = None
__finished_jobs = []


def run_in_parallel(*args, **kwargs):
    global __manager
    if __manager is None:
        return run_in_parallel_local(*args, **kwargs)
    else:
        return run_in_parallel_remote(*args, **kwargs)

def init_threading(number_of_processes=None, enable_server=False, remote=None, run_server=False,
        server_credentials=""):
    global __multiprocessing, __num_of_processes, __manager, __closing, __task_source_uuid
    # only local -> no server settings allowed
    if (not enable_server) and (not run_server):
        remote = None
        run_server = None
        server_credentials = ""
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
            if (multiprocessing.cpu_count() > 1) or remote or run_server:
                __multiprocessing = multiprocessing
                __num_of_processes = multiprocessing.cpu_count()
            else:
                __multiprocessing = False
        elif (number_of_processes < 1) and (remote is None):
            # zero processes are allowed if we use a remote server
            __multiprocessing = False
        else:
            __multiprocessing = multiprocessing
            __num_of_processes = number_of_processes
    # initialize the manager
    if not __multiprocessing:
        __manager == None
        log.info("Disabled parallel processing")
    elif not enable_server and not run_server:
        __manager == None
        log.info("Enabled %d parallel local processes" % __num_of_processes)
    else:
        # with multiprocessing
        log.info("Enabled %d parallel local processes" % __num_of_processes)
        log.info("Allow remote processing")
        # initialize the uuid list for all workers
        worker_uuid_list = [str(uuid.uuid1()) for index in range(__num_of_processes)]
        __task_source_uuid = str(uuid.uuid1())
        if remote is None:
            address = ('', DEFAULT_PORT)
        else:
            if ":" in remote:
                host, port = remote.split(":", 1)
                try:
                    port = int(port)
                except ValueError:
                    log.warning(("Invalid port specified: '%s' - using default " \
                            + "port (%d) instead") % (port, DEFAULT_PORT))
                    port = DEFAULT_PORT
            else:
                host = remote
                port = DEFAULT_PORT
            address = (host, port)
        from multiprocessing.managers import SyncManager
        class TaskManager(SyncManager):
            @classmethod
            def _run_server(cls, *args):
                # make sure that the server ignores SIGINT (KeyboardInterrupt)
                import signal
                signal.signal(signal.SIGINT, signal.SIG_IGN)
                SyncManager._run_server(*args)
        if remote is None:
            tasks_queue = multiprocessing.Queue()
            results_queue = multiprocessing.Queue()
            statistics = ProcessStatistics()
            cache = ProcessDataCache()
            TaskManager.register("tasks", callable=lambda: tasks_queue)
            TaskManager.register("results", callable=lambda: results_queue)
            TaskManager.register("statistics", callable=lambda: statistics)
            TaskManager.register("cache", callable=lambda: cache)
        else:
            TaskManager.register("tasks")
            TaskManager.register("results")
            TaskManager.register("statistics")
            TaskManager.register("cache")
        __manager = TaskManager(address=address, authkey=server_credentials)
        # run the local server, connect to a remote one or begin serving
        if remote is None:
            __manager.start()
            log.info("Started a local server.")
        else:
            __manager.connect()
            log.info("Connected to a remote task server.")
        # create the spawning process
        __closing = __manager.Value("b", False)
        if __num_of_processes > 0:
            # only start the spawner, if we want to use local workers
            spawner = __multiprocessing.Process(name="spawn", target=_spawn_daemon,
                    args=(__manager, __num_of_processes, worker_uuid_list))
            spawner.start()
        else:
            spawner = None
        # wait forever - in case of a server
        if run_server:
            log.info("Running a local server and waiting for remote connections.")
            # the server can be stopped via CTRL-C - it is caught later
            if not spawner is None:
                spawner.join()

def cleanup():
    global __manager, __closing
    if __multiprocessing and __closing:
        __closing.set(True)

def _spawn_daemon(manager, number_of_processes, worker_uuid_list):
    """ wait for items in the 'tasks' queue to appear and then spawn workers
    """
    global __multiprocessing, __closing
    tasks = manager.tasks()
    results = manager.results()
    stats = manager.statistics()
    cache = manager.cache()
    try:
        while not __closing.get():
            if not tasks.empty():
                workers = []
                for task_id in worker_uuid_list:
                    worker = __multiprocessing.Process(
                            name="task-%s" % str(task_id), target=_handle_tasks,
                            args=(tasks, results, stats, cache))
                    worker.start()
                    workers.append(worker)
                # wait until all workers are finished
                for worker in workers:
                    worker.join()
            else:
                time.sleep(0.2)
    except KeyboardInterrupt:
        # set the "closing" flag and just exit
        __closing.set(True)

def _handle_tasks(tasks, results, stats, cache):
    global __multiprocessing
    name = __multiprocessing.current_process().name
    local_cache = {}
    try:
        while not tasks.empty():
            try:
                start_time = time.time()
                job_id, func, args, cache_id = tasks.get(timeout=1.0)
                if not cache_id in local_cache.keys():
                    local_cache[cache_id] = cache.get(cache_id)
                stats.add_transfer_time(name, time.time() - start_time)
                start_time = time.time()
                results.put((job_id, func((args, local_cache[cache_id]))))
                stats.add_process_time(name, time.time() - start_time)
            except Queue.Empty:
                break
    except KeyboardInterrupt:
        pass

def run_in_parallel_remote(func, args_list, unordered=False,
        disable_multiprocessing=False, host=None):
    global __multiprocessing, __num_of_processes, __manager, __task_source_uuid, __finished_jobs
    if __multiprocessing is None:
        # threading was not configured before
        init_threading()
    if __multiprocessing and not disable_multiprocessing:
        tasks_queue = __manager.tasks()
        results_queue = __manager.results()
        cache = __manager.cache()
        stats = __manager.statistics()
        previous_cache_values = {}
        job_id = str(uuid.uuid1())
        for args in args_list:
            normal_args, cache_args = args
            start_time = time.time()
            for key, value in previous_cache_values.iteritems():
                if cache_args == value:
                    cache_id = key
                    break
            else:
                cache_id = str(uuid.uuid4())
                previous_cache_values[cache_id] = cache_args
                cache.add(cache_id, cache_args)
            tasks_queue.put((job_id, func, normal_args, cache_id))
            stats.add_queueing_time(__task_source_uuid, time.time() - start_time)
        def job_cleanup():
            # remove the previously added cached items
            for key in previous_cache_values.keys():
                cache.remove(key)
            print stats.get_stats()
        for index in range(len(args_list)):
            try:
                result_job_id = None
                while result_job_id != job_id:
                    result_job_id, result = results_queue.get()
                    if result_job_id == job_id:
                        yield result
                    elif result_job_id in __finished_jobs:
                        # throw this result of an job away
                        pass
                    else:
                        # put the result back to the queue for the next manager
                        results_queue.put((result_job_id, result))
                        # wait for 0.5 up to 1.5 seconds before trying again
                        time.sleep(0.5 + random.random())
            except GeneratorExit:
                # catch this specific (silent) exception and flush the task queue
                queue_len = tasks.qsize()
                # remove all remaining tasks with the current job id
                for index in queue_len:
                    this_job_id, func, normal_args, cache_id = tasks_queue.get(timeout=0.1)
                    if job_id != this_job_id:
                        tasks.put((this_job_id, func, normal_args, cache_id))
                __finished_jobs.append(job_id)
                while len(__finished_jobs) > 10:
                    __finished_jobs.pop(0)
                job_cleanup()
                # re-raise the GeneratorExit exception to finish destruction
                raise
        job_cleanup()
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


class OneProcess(object):
    def __init__(self, name, is_queue=False):
        self.is_queue = is_queue
        self.name = name
        self.transfer_time = 0
        self.transfer_count = 0
        self.process_time = 0
        self.process_count = 0

    def __str__(self):
        try:
            if self.is_queue:
                return "Queue %s: %s (%s/%s)" \
                    % (self.name, self.transfer_time/self.transfer_count,
                            self.transfer_time, self.transfer_count)
            else:
                return "Process %s: %s (%s/%s) - %s (%s/%s)" \
                        % (self.name, self.transfer_time/self.transfer_count,
                                self.transfer_time, self.transfer_count,
                                self.process_time/self.process_count,
                                self.process_time, self.process_count)
        except ZeroDivisionError:
            # race condition between adding new objects and output
            if self.is_queue:
                return "Queue %s: not ready" % str(self.name)
            else:
                return "Process %s: not ready" % str(self.name)


class ProcessStatistics(object):

    def __init__(self):
        self.processes = {}
        self.queues = {}

    def __str__(self):
        return os.linesep.join([str(item)
                for item in self.processes.values() + self.queues.values()])

    def get_stats(self):
        return str(self)

    def add_transfer_time(self, name, amount):
        if not name in self.processes:
            self.processes[name] = OneProcess(name)
        self.processes[name].transfer_count += 1
        self.processes[name].transfer_time += amount

    def add_process_time(self, name, amount):
        if not name in self.processes:
            self.processes[name] = OneProcess(name)
        self.processes[name].process_count += 1
        self.processes[name].process_time += amount

    def add_queueing_time(self, name, amount):
        if not name in self.queues:
            self.queues[name] = OneProcess(name, is_queue=True)
        self.queues[name].transfer_count += 1
        self.queues[name].transfer_time += amount


class ProcessDataCache(object):

    def __init__(self):
        self.cache = {}

    def add(self, name, value):
        self.cache[name] = value

    def get(self, name):
        return self.cache[name]

    def remove(self, name):
        if name in self.cache:
            del self.cache[name]

