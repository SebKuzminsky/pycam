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
import pycam.Toolpath.MotionGrid as MotionGrid
import pycam.Utils.log

_log = pycam.Utils.log.get_logger()


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


class ProcessStrategy(Enum):
    SLICE = "slice"
    CONTOUR = "contour"
    SURFACE = "surface"
    ENGRAVE = "engrave"


class PathPattern(Enum):
    SPIRAL = "spiral"
    GRID = "grid"


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


class Process(BaseDataContainer):

    def get_path_generator(self):
        strategy = _get_enum_value(ProcessStrategy, self.get_value("strategy"))
        if strategy == ProcessStrategy.SLICE:
            return pycam.PathGenerators.PushCutter.PushCutter(waterlines=False)
        elif strategy == ProcessStrategy.CONTOUR:
            return pycam.PathGenerators.PushCutter.PushCutter(waterlines=True)
        elif strategy == ProcessStrategy.SURFACE:
            return pycam.PathGenerators.DropCutter.DropCutter()
        elif strategy == ProcessStrategy.ENGRAVE:
            return pycam.PathGenerators.EngraveCutter.EngraveCutter()
        else:
            raise InvalidKeyError(strategy, ProcessStrategy)

    def get_motion_grid(self, tool_radius, box):
        strategy = _get_enum_value(ProcessStrategy, self.get_value("strategy"))
        overlap = self.get_value("overlap", 0)
        line_distance = 2 * tool_radius * (1 - overlap)
        milling_style = _get_enum_value(MotionGrid.MillingStyle,
                                        self.get_value("milling_style"))
        if strategy == ProcessStrategy.SLICE:
            return MotionGrid.get_fixed_grid(
                box, self.get_value("step_down"), line_distance=line_distance,
                grid_direction=MotionGrid.GridDirection.X,
                milling_style=milling_style)
        elif strategy == ProcessStrategy.CONTOUR:
            # TODO: milling_style currently refers to the grid lines - not to the waterlines
            return MotionGrid.get_fixed_grid(box, self.get_value("step_down"),
                                             line_distance=line_distance,
                                             grid_direction=MotionGrid.GridDirection.X,
                                             milling_style=milling_style)
        elif strategy == ProcessStrategy.SURFACE:
            path_pattern = _get_enum_value(PathPattern, self.get_value("path_pattern"))
            if path_pattern == PathPattern.SPIRAL:
                func = MotionGrid.get_spiral
                kwarg_names = ("grid_direction", )
            elif path_pattern == PathPattern.GRID:
                func = MotionGrid.get_fixed_grid
                kwarg_names = ("spiral_direction", "rounded_corners")
            else:
                raise InvalidKeyError(path_pattern, PathPattern)
            # surfacing requires a finer grid (arbitrary factor)
            step_width = tool_radius / 4.0
            kwargs = {key: self.get_value(key) for key in kwarg_names}
            return func(box, None, step_width=step_width, line_distance=line_distance,
                        milling_style=milling_style, **kwargs)
        elif strategy == ProcessStrategy.ENGRAVE:
            models = [m.model for m in self.get_value("trace_models")]
            if not models:
                _log.error("No trace models given: you need to assign a 2D model to the engraving "
                           "process.")
                return None
            progress = self.core.get("progress")
            radius_compensation = self.get_value("radius_compensation", raise_if_missing=False)
            if radius_compensation:
                progress.update(text="Offsetting models")
                progress.set_multiple(len(models), "Model")
                for index, model in enumerate(models):
                    models[index] = model.get_offset_model(tool_radius, callback=progress.update)
                    progress.update_multiple()
                progress.finish()
            progress.update(text="Calculating moves")
            line_distance = 1.8 * tool_radius
            step_width = tool_radius / 4.0
            pocketing_type = _get_enum_value(PocketingType, self.get_value("pocketing_type"))
            motion_grid = MotionGrid.get_lines_grid(
                models, box, self.get_value("step_down"), line_distance=line_distance,
                step_width=step_width, milling_style=milling_style, pocketing_type=pocketing_type,
                skip_first_layer=True, callback=progress.update)
            progress.finish()
            return motion_grid
        else:
            raise InvalidKeyError(strategy, ProcessStrategy)


class Task(BaseDataContainer):

    def generate_toolpath(self, callback=None):
        process = self.get_value("process")
        bounds = self.get_value("bounds")
        task_type = _get_enum_value(TaskType, self.get_value("type"))
        if task_type == TaskType.MILLING:
            tool = self.get_value("tool")
            box = bounds.get_absolute_limits(tool_radius=tool.radius,
                                             models=self.get_value("collision_models"))
            path_generator = process.get_path_generator()
            motion_grid = process.get_motion_grid(tool.radius, box)
            if path_generator is None:
                # we assume that an error message was given already
                return
            models = [m.model for m in self.get_value("collision_models")]
            if not models:
                # issue a warning - and go ahead ...
                _log.warn("No collision model was selected. This can be intentional, but maybe "
                          "you simply forgot it.")
            moves = path_generator.GenerateToolPath(tool.get_tool_geometry(), models, motion_grid,
                                                    minz=box.lower.z, maxz=box.upper.z,
                                                    draw_callback=callback)
            if not moves:
                _log.info("No valid moves found")
                return None
            return pycam.Toolpath.Toolpath(toolpath_path=moves, tool=tool,
                                           toolpath_filters=tool.get_toolpath_filters())
        else:
            raise InvalidKeyError(task_type, TaskType)
