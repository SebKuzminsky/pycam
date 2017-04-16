# -*- coding: utf-8 -*-
"""
Copyright 2017 Lars Kruse <devel@sumpfralle.de>

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

import copy
from enum import Enum

from pycam.Cutters.CylindricalCutter import CylindricalCutter
from pycam.Cutters.SphericalCutter import SphericalCutter
from pycam.Cutters.ToroidalCutter import ToroidalCutter
import pycam.PathGenerators.DropCutter
import pycam.PathGenerators.EngraveCutter
import pycam.PathGenerators.PushCutter
from pycam.Toolpath.Filters import MachineSetting



class FlowDescriptionBaseException(Exception):
    pass


class MissingAttributeError(FlowDescriptionBaseException):
    pass


class InvalidDataError(FlowDescriptionBaseException):
    pass


class InvalidKeyError(InvalidDataError):

    def __init__(self, invalid_key, choice_enum):
        # retrieve the pretty name of the enum
        enum_name = str(choice_enum).split("'")[1]
        super(InvalidKeyError, self).__init__("Unknown {}: {} (should be one of: {})".format(
            enum_name, invalid_key, ", ".join([item.value for item in choice_enum])))


class ToolShape(Enum):
    FLAT_BOTTOM = "flat_bottom"
    BALL_NOSE = "ball_nose"
    TORUS = "torus"


class TaskType(Enum):
    MILLING = "milling"


def _get_enum_value(enum_class, value):
    try:
        return enum_class(value)
    except ValueError:
        raise InvalidKeyError(value, enum_class)


class BaseDataContainer(object):

    def __init__(self, data):
        self._data = copy.deepcopy(data)

    @classmethod
    def parse_from_dict(cls, data):
        return cls(data)

    def get_value(self, key, default=None, raise_if_missing=True):
        try:
            return self._data[key]
        except KeyError:
            if (default is None) and raise_if_missing:
                raise MissingAttributeError("The attribute '{}' is missing in '{}'"
                                            .format(key, type(self)))
            else:
                return default

    def set_value(self, key, value):
        self._data[key] = value

    def get_dict(self):
        return copy.deepcopy(self._data)


class Tool(BaseDataContainer):

    def get_tool_geometry(self):
        height = self.get_value("height", default=10, raise_if_missing=False)
        shape = _get_enum_value(ToolShape, self.get_value("shape"))
        if shape == ToolShape.FLAT_BOTTOM:
            return CylindricalCutter(self.radius, height=height)
        elif shape == ToolShape.BALL_NOSE:
            return SphericalCutter(self.radius, height=height)
        elif shape == ToolShape.TORUS:
            toroid_radius = self.get_value("toroid_radius")
            return ToroidalCutter(self.radius, toroid_radius, height=height)
        else:
            raise InvalidKeyError(shape, ToolShape)

    @property
    def radius(self):
        """ offer a uniform interface for retrieving the radius value from "radius" or "diameter"

        May raise MissingAttributeError if valid input sources are missing.
        """
        radius = self.get_value("radius", raise_if_missing=False)
        if radius is None:
            radius = self.get_value("diameter") / 2
        return radius

    @property
    def diameter(self):
        return 2 * self.radius

    def get_toolpath_filters(self):
        feed = self.get_value("feed")
        speed = self.get_value("speed", default=1000, raise_if_missing=False)
        return [MachineSetting("feedrate", feed), MachineSetting("spindle_speed", speed)]
