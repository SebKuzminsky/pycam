# -*- coding: utf-8 -*-
"""
$Id$

Copyright 2011 Lars Kruse <devel@sumpfralle.de>

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

import os
import imp
import inspect
import gtk

import pycam.Utils.log
import pycam.Utils.locations


_log = pycam.Utils.log.get_logger()


class PluginBase(object):

    UI_FILE = None

    def __init__(self, core, name):
        self.enabled = True
        self.name = name
        self.core = core
        self.gui = None
        if self.UI_FILE:
            gtk_build_file = pycam.Utils.locations.get_ui_file_location(
                    self.UI_FILE)
            if gtk_build_file:
                self.gui = gtk.Builder()
                try:
                    self.gui.add_from_file(gtk_build_file)
                except RuntimeError:
                    self.gui = None
        if not self.setup():
            raise RuntimeError("Failed to load plugin '%s'" % str(name))

    def setup(self):
        raise NotImplementedError("Module %s (%s) does not implement " + \
                "'setup'" % (self.name, __file__))

    def teardown(self):
        raise NotImplementedError("Module %s (%s) does not implement " + \
                "'teardown'" % (self.name, __file__))


class PluginManager(object):

    def __init__(self, core):
        self.core = core
        self.modules = {}

    def import_plugins(self, directory=None):
        if directory is None:
            directory = os.path.dirname(__file__)
        try:
            files = os.listdir(directory)
        except OSError:
            return
        for filename in files:
            if filename.endswith(".py") and (filename != "__init__.py") and \
                    os.path.isfile(os.path.join(directory, filename)):
                mod_name = filename[0:-(len(".py"))]
                try:
                    mod_file, mod_filename, mod_desc = imp.find_module(
                            mod_name, [directory])
                    full_mod_name = "pycam.Plugins.%s" % mod_name
                    mod = imp.load_module(full_mod_name, mod_file,
                            mod_filename, mod_desc)
                except ImportError:
                    _log.debug("Skipping broken plugin %s" % os.path.join(
                            directory, filename))
                    continue
                for attr in dir(mod):
                    item = getattr(mod, attr)
                    if inspect.isclass(item) and hasattr(item, "setup"):
                        self._load_plugin(item, mod_filename, attr)

    def _load_plugin(self, obj, filename, local_name):
        name = "%s.%s" % (os.path.basename(filename)[0:-len(".py")], local_name)
        if name in self.modules:
            _log.debug("Cleaning up module %s" % name)
            self.modules[name].teardown()
        _log.debug("Initializing module %s (%s)" % (name, filename))
        self.modules[name] = obj(self.core, name)

