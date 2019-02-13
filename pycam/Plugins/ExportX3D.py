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

import collections
import io
import math
import os

import pycam.Plugins


class ExportX3D(pycam.Plugins.PluginBase):

    CATEGORIES = {"Export", "Visualization"}

    def setup(self):
        self._x3d_cache = None
        self._event_handlers = [("visual-item-updated", self.invalidate_x3d_cache)]
        self.core.set("get_x3d_export", self.get_x3d_export)
        self.register_event_handlers(self._event_handlers)
        self.core.emit_event("visual-item-updated")
        return super().setup()

    def teardown(self):
        self.unregister_event_handlers(self._event_handlers)
        self.core.set("get_x3d_export", None)
        super().teardown()

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


SceneView = collections.namedtuple("SceneView", ("orientation", "angle", "direction"))


class X3DTree:

    VIEWS = {
        "center": SceneView((-1, 1, 1), -math.pi / 2, (-1.0, -0.2, 0.4)),
        "top": SceneView((0, 0, 1), 0, (0, 0, 1)),
        "bottom": SceneView((0, 1, 0), math.pi, (0, 0, -1)),
        "left": SceneView((1, -1, -1), math.pi * 2 / 3, (-1, 0, 0)),
        "right": SceneView((1, 1, 1), math.pi * 2 / 3, (1, 0, 0)),
        "front": SceneView((1, 0, 0), math.pi / 2, (0, -1, 0)),
        "back": SceneView((0, 1, 1), math.pi, (0, 1, 0)),
    }

    def __init__(self, use_orthogonal=True):
        self.header = '<X3D version="3.0" profile="Immersive"><Scene>'
        self.header += """<NavigationInfo isActive="true" type='"EXAMINE" "ANY"' />"""
        if use_orthogonal:
            view_type = "OrthoViewpoint"
        else:
            view_type = "Viewpoint"
        dim_low = (0, 0, -10)
        dim_high = (130, 50, 0)
        dims = tuple(u - l for l, u in zip(dim_low, dim_high))
        max_dims = max(dims)
        center = tuple((l + u) / 2 for l, u in zip(dim_low, dim_high))
        if use_orthogonal:
            field_radius = max_dims * 0.3
            extra_attributes = 'fieldOfView="{:f} {:f} {:f} {:f}"'.format(
                -field_radius, -field_radius, field_radius, field_radius)
            # the distance of the position is not used for orthogonal views (only the fieldOfView)
            distance_factor = 1.0
        else:
            extra_attributes = 'zNear="{:f}"'.format(max_dims)
            distance_factor = 1.1
        for name, view in self.VIEWS.items():
            position = tuple(c + distance_factor * o * max_dims
                             for c, o in zip(center, view.direction))
            self.header += (
                '<{} DEF="{}" id="view_{}" isActive="true" description="{}" '
                'centerOfRotation="{:f} {:f} {:f}" position="{:f} {:f} {:f}" '
                'orientation="{:f} {:f} {:f} {:f}" {} />'
                .format(view_type, name, name, name, *center, *position, *view.orientation,
                        view.angle, extra_attributes))
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
