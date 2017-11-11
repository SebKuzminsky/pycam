#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""

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

# for "print" to stderr
from __future__ import print_function

import logging
from optparse import OptionParser
import os
import socket
import sys
import warnings

# we need the multiprocessing exception for remote connections
try:
    import multiprocessing
    from multiprocessing import AuthenticationError
except ImportError:
    multiprocessing = None
    # use an arbitrary other Exception
    AuthenticationError = socket.error

try:
    from pycam import VERSION
except ImportError:
    # running locally (without a proper PYTHONPATH) requires manual intervention
    sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                                     os.pardir)))
    from pycam import VERSION

import pycam.Exporters.GCodeExporter
import pycam.Gui.common as GuiCommon
import pycam.Gui.Settings
import pycam.Gui.Console
import pycam.Importers.TestModel
import pycam.Importers
import pycam.Plugins
import pycam.Utils
from pycam.Utils.events import get_event_handler
import pycam.Utils.log
import pycam.Utils.threading

# register the glut32.dll manually for the pyinstaller standalone executable
if hasattr(sys, "frozen") and sys.frozen and "_MEIPASS2" in os.environ:
    from ctypes import windll
    windll[os.path.join(os.path.normpath(os.environ["_MEIPASS2"]), "glut32.dll")]

# The installer for PyODE does not add the required PATH variable.
if pycam.Utils.get_platform() == pycam.Utils.OSPlatform.WINDOWS:
    os.environ["PATH"] = os.environ.get("PATH", "") + os.path.pathsep + sys.exec_prefix
# The GtkGLExt installer does not add the required PATH variable.
if pycam.Utils.get_platform() == pycam.Utils.OSPlatform.WINDOWS:
    import _winreg
    path = None
    try:
        reg = _winreg.ConnectRegistry(None, _winreg.HKEY_LOCAL_MACHINE)
        regkey = _winreg.OpenKey(reg, r"SOFTWARE\GtkGLExt\1.0\Runtime")
    except WindowsError:
        regkey = None
    index = 0
    while regkey:
        try:
            key, value = _winreg.EnumValue(regkey, index)[:2]
        except WindowsError:
            # no more items left
            break
        if key == "Path":
            path = os.path.join(str(value), "bin")
            break
        index += 1
    if path:
        os.environ["PATH"] = os.environ.get("PATH", "") + os.path.pathsep + path

BASE_DIR = os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir))

EXAMPLE_MODEL_LOCATIONS = [
    os.path.join(BASE_DIR, "samples"),
    os.path.join(sys.prefix, "share", "pycam", "samples"),
    os.path.join(sys.prefix, "local", "share", "pycam", "samples"),
    os.path.join("usr", "share", "pycam", "samples")]

# for pyinstaller (windows distribution)
if "_MEIPASS2" in os.environ:
    EXAMPLE_MODEL_LOCATIONS.insert(0, os.path.join(os.path.normpath(os.environ["_MEIPASS2"]),
                                                   "samples"))
DEFAULT_MODEL_FILE = "pycam-textbox.stl"
# DEFAULT_MODEL_FILE = "problem_1_triangle.stl"
EXIT_CODES = {"ok": 0,
              "requirements": 1,
              "load_model_failed": 2,
              "write_output_failed": 3,
              "parsing_failed": 4,
              "server_without_password": 5,
              "connection_error": 6,
              "toolpath_error": 7}

log = pycam.Utils.log.get_logger()


def show_gui():
    deps_gtk = GuiCommon.requirements_details_gtk()
    report_gtk = GuiCommon.get_dependency_report(deps_gtk, prefix="\t")
    if GuiCommon.check_dependencies(deps_gtk):
        from pycam.Gui.Project import ProjectGui
        gui_class = ProjectGui
    else:
        full_report = []
        full_report.append("PyCAM dependency problem")
        full_report.append("Error: Failed to load the GTK interface.")
        full_report.append("Details:")
        full_report.append(report_gtk)
        full_report.append("")
        full_report.append("Detailed list of requirements: %s" % GuiCommon.REQUIREMENTS_LINK)
        log.critical(os.linesep.join(full_report))
        return EXIT_CODES["requirements"]

    event_manager = get_event_handler()
    gui = gui_class(event_manager)
    # initialize plugins
    plugin_manager = pycam.Plugins.PluginManager(core=event_manager)
    plugin_manager.import_plugins()
    # some more initialization
    gui.reset_preferences()
    # TODO: preferences are not loaded until the new format is stable
#   self.load_preferences()

    # tell the GUI to empty the "undo" queue
    gui.clear_undo_states()

    event_manager.emit_event("notify-initialization-finished")

    # open the GUI
    gui.mainloop()
    # no error -> return no error code
    return None


def execute(parser, opts, args, pycam):
    # try to change the process name
    pycam.Utils.setproctitle("pycam")

    if opts.trace:
        log.setLevel(logging.DEBUG / 2)
    elif opts.debug:
        log.setLevel(logging.DEBUG)
    elif opts.quiet:
        log.setLevel(logging.WARNING)
        # disable the progress bar
        opts.progress = "none"
        # silence all warnings
        warnings.filterwarnings("ignore")
    else:
        # silence gtk warnings
        try:
            import gi
            gi.require_version("Gtk", "3.0")
            # from gi.repository import Gtk as gtk
            # warnings.filterwarnings("ignore", category=gtk.Warning) FIXME
        except ImportError:
            pass

    # show version and exit
    if opts.show_version:
        if opts.quiet:
            # print only the bare version number
            print(VERSION)
        else:
            text = """PyCAM %s
Copyright (C) 2008-2010 Lode Leroy
Copyright (C) 2010-2017 Lars Kruse and many other contributors

License GPLv3+: GNU GPL version 3 or later <http://gnu.org/licenses/gpl.html>.
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.""" % VERSION
            print(text)
        return EXIT_CODES["ok"]

    # check if server-auth-key is given -> this is mandatory for server mode
    if (opts.enable_server or opts.start_server) and not opts.server_authkey:
        parser.error(
            "You need to supply a shared secret for server mode. This is supposed to prevent you "
            "from exposing your host to remote access without authentication.\nPlease add the "
            "'--server-auth-key' argument followed by a shared secret password.")
        return EXIT_CODES["server_without_password"]

    # initialize multiprocessing
    try:
        if opts.start_server:
            pycam.Utils.threading.init_threading(
                opts.parallel_processes, remote=opts.remote_server, run_server=True,
                server_credentials=opts.server_authkey)
            pycam.Utils.threading.cleanup()
            return EXIT_CODES["ok"]
        else:
            pycam.Utils.threading.init_threading(
                opts.parallel_processes, enable_server=opts.enable_server,
                remote=opts.remote_server, server_credentials=opts.server_authkey)
    except socket.error as err_msg:
        log.error("Failed to connect to remote server: %s", err_msg)
        return EXIT_CODES["connection_error"]
    except AuthenticationError as err_msg:
        log.error("The remote server rejected your authentication key: %s", err_msg)
        return EXIT_CODES["connection_error"]

    show_gui()


def main_func():
    # The PyInstaller standalone executable requires this "freeze_support" call. Otherwise we will
    # see a warning regarding an invalid argument called "--multiprocessing-fork". This problem can
    # be triggered on single-core systems with these arguments:
    #    "--enable-server --server-auth-key foo".
    if hasattr(multiprocessing, "freeze_support"):
        multiprocessing.freeze_support()
    parser = OptionParser(
        prog="PyCAM", usage=("usage: pycam [options]\n\n"
                             "Start the PyCAM toolpath generator. Supplying one of the "
                             "'--export-?' parameters will cause PyCAM to start in batch mode. "
                             "Most parameters are useful only for batch mode."),
        epilog="PyCAM website: https://github.com/SebKuzminsky/pycam")
    group_general = parser.add_option_group("General options")
    # general options
    group_general.add_option(
        "", "--unit", dest="unit_size", default="mm", action="store", type="choice",
        choices=["mm", "inch"],
        help="choose 'mm' or 'inch' for all numbers. By default 'mm' is assumed.")
    group_general.add_option(
        "", "--collision-engine", dest="collision_engine", default="triangles", action="store",
        type="choice", choices=["triangles"],
        help=("choose a specific collision detection engine. The default is 'triangles'. "
              "Use 'help' to get a list of possible engines."))
    group_general.add_option(
        "", "--number-of-processes", dest="parallel_processes", default=None, type="int",
        action="store",
        help=("override the default detection of multiple CPU cores. Parallel processing only "
              "works with Python 2.6 (or later) or with the additional 'multiprocessing' module."))
    group_general.add_option(
        "", "--enable-server", dest="enable_server", default=False, action="store_true",
        help="enable a local server and (optionally) remote worker servers.")
    group_general.add_option(
        "", "--remote-server", dest="remote_server", default=None, action="store", type="string",
        help=("Connect to a remote task server to distribute the processing load. "
              "The server is given as an IP or a hostname with an optional port (default: 1250) "
              "separated by a colon."))
    group_general.add_option(
        "", "--start-server-only", dest="start_server", default=False, action="store_true",
        help="Start only a local server for handling remote requests.")
    group_general.add_option(
        "", "--server-auth-key", dest="server_authkey", default="", action="store", type="string",
        help=("Secret used for connecting to a remote server or for granting access to remote "
              "clients."))
    group_general.add_option(
        "-q", "--quiet", dest="quiet", default=False, action="store_true",
        help="output only warnings and errors.")
    group_general.add_option(
        "-d", "--debug", dest="debug", default=False, action="store_true",
        help="enable output of debug messages.")
    group_general.add_option(
        "", "--trace", dest="trace", default=False, action="store_true",
        help="enable more verbose debug messages.")
    group_general.add_option(
        "", "--progress", dest="progress", default="text", action="store", type="choice",
        choices=["none", "text", "bar", "dot"],
        help=("specify the type of progress bar used in non-GUI mode. The following options are "
              "available: text, none, bar, dot."))
    group_general.add_option(
        "", "--profiling", dest="profile_destination", action="store", type="string",
        help="store profiling statistics in a file (only for debugging)")
    group_general.add_option(
        "-v", "--version", dest="show_version", default=False, action="store_true",
        help="output the current version of PyCAM and exit")
    (opts, args) = parser.parse_args()
    try:
        if opts.profile_destination:
            import cProfile
            exit_code = cProfile.run('execute(parser, opts, args, pycam)',
                                     opts.profile_destination)
        else:
            # We need to add the parameter "pycam" to avoid weeeeird namespace
            # issues. Any idea how to fix this?
            exit_code = execute(parser, opts, args, pycam)
    except KeyboardInterrupt:
        log.info("Quit requested")
        exit_code = None
    pycam.Utils.threading.cleanup()
    if exit_code is not None:
        sys.exit(exit_code)
    else:
        sys.exit(EXIT_CODES["ok"])


if __name__ == "__main__":
    main_func()
