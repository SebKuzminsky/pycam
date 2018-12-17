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

import os

import pycam.Plugins


class ExportX3D(pycam.Plugins.PluginBase):

    CATEGORIES = {"Export", "Visualization"}

    def setup(self):
        self._event_handlers = [("visual-item-updated", self.export_x3d)]
        self.register_event_handlers(self._event_handlers)
        self.core.emit_event("visual-item-updated")
        return True

    def teardown(self):
        self.unregister_event_handlers(self._event_handlers)

    def export_x3d(self):
        tree = X3DTree()
        self.core.call_chain("generate_x3d", tree)
        # TODO: send the output to a better consumer
        with open("pycam-preview.x3d", "w") as out_file:
            for line in tree.to_string():
                out_file.write(line)
                out_file.write(os.linesep)


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
