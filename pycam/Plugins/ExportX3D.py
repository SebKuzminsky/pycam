"""
Copyright 2018 Lars Kruse <devel@sumpfralle.de>

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

import io
import os

import pycam.Plugins


class ExportX3D(pycam.Plugins.PluginBase):

    CATEGORIES = {"Export", "Visualization"}

    def setup(self):
        self._x3d_cache = None
        self._event_handlers = [("visual-item-updated", self.invalidate_x3d_cache)]
        self.register_event_handlers(self._event_handlers)
        self.core.set("get_x3d_export", self.get_x3d_export)
        self.core.emit_event("visual-item-updated")
        return True

    def teardown(self):
        self.core.set("get_x3d_export", None)
        self.unregister_event_handlers(self._event_handlers)

    def invalidate_x3d_cache(self):
        self._x3d_cache = None

    def get_x3d_export(self):
        """ deliver a file-like bytes buffer containing the X3D data """
        if self._x3d_cache is None:
            # refresh the cache
            tree = X3DTree()
            self.core.call_chain("generate_x3d", tree)
            target = io.BytesIO()
            for line in tree.to_string():
                target.write((line + os.linesep).encode())
            self._x3d_cache = target
        # create a copy: consumers may want to override it
        self._x3d_cache.seek(0)
        result = io.BytesIO(self._x3d_cache.read())
        result.seek(0)
        return result


class X3DTree:

    def __init__(self):
        self.header = '<X3D version="3.0" profile="Immersive"><Scene>'
        self.footer = "</Scene></X3D>"
        self.sources = []

    def add_data_source(self, source):
        self.sources.append(source)

    def to_string(self):
        yield self.header
        for source in self.sources:
            for line in source:
                yield line
        yield self.footer
