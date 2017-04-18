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

import collections
import copy
from enum import Enum
import functools
import os.path

from pycam.Cutters.CylindricalCutter import CylindricalCutter
from pycam.Cutters.SphericalCutter import SphericalCutter
from pycam.Cutters.ToroidalCutter import ToroidalCutter
from pycam.Geometry import Box3D, Point3D
import pycam.PathGenerators.DropCutter
import pycam.PathGenerators.EngraveCutter
import pycam.PathGenerators.PushCutter
from pycam.Plugins.Bounds import ToolBoundaryMode
from pycam.Toolpath.Filters import MachineSetting
import pycam.Toolpath.MotionGrid as MotionGrid
from pycam.Importers import detect_file_type
import pycam.Utils.log

_log = pycam.Utils.log.get_logger()


# dictionary of all collections by name
_data_collections = {}


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


class BoundsSpecification(Enum):
    ABSOLUTE = "absolute"
    MARGINS = "margins"


class TaskType(Enum):
    MILLING = "milling"


class SourceType(Enum):
    FILE = "file"
    URL = "url"
    COPY = "copy"
    TASK = "task"
    TOOLPATH = "toolpath"


class TargetType(Enum):
    FILE = "file"


class ExportType(Enum):
    GCODE = "gcode"


def _get_enum_value(enum_class, value):
    try:
        return enum_class(value)
    except ValueError:
        raise InvalidKeyError(value, enum_class)


def _get_enum_resolver(enum_class):
    """ return a function that would convert a raw value to an enum item of the given class """
    return functools.partial(_get_enum_value, enum_class)


def _bool_converter(value):
    if isinstance(value, int):
        if value == 1:
            return True
        elif value == 0:
            return False
        else:
            raise InvalidDataError("Invalid boolean value: {} (int)".format(value))
    elif isinstance(value, str):
        if value.lower() in ("true", "yes", "1", "on", "enabled"):
            return True
        elif value.lower() in ("false", "no", "0", "off", "disabled"):
            return False
        else:
            raise InvalidDataError("Invalid boolean value: {} (string)".format(value))
    elif isinstance(value, bool):
        return value
    else:
        raise InvalidDataError("Invalid boolean value type ({}): {}".format(type(value), value))


LimitSingle = collections.namedtuple("LimitSingle", ("value", "is_relative"))
Limit3D = collections.namedtuple("Limit3D", ("x", "y", "z"))


def _limit3d_converter(point):
    """ convert a tuple or list of three numbers or a dict with x/y/z keys into a 'Limit3D' """
    if len(point) != 3:
        raise InvalidDataError("A 3D limit needs to contain exactly three items: {}"
                               .format(point))
    result = []
    if isinstance(point, dict):
        try:
            point = (point["x"], point["y"], point["z"])
        except KeyError:
            raise InvalidDataError("All three axis are required for lower/upper limits")
    for value in point:
        is_relative = False
        if isinstance(value, str):
            try:
                if value.endswith("%"):
                    is_relative = True
                    # convert percent value to 0..1
                    value = float(value[:-1]) / 100.0
                else:
                    value = float(value)
            except ValueError:
                raise InvalidDataError("Failed to parse float from 3D limit: {}".format(value))
        elif isinstance(value, (int, float)):
            value = float(value)
        else:
            raise InvalidDataError("Non-numeric data supplied for 3D limit: {}".format(value))
        result.append(LimitSingle(value, is_relative))
    return Limit3D(*result)


def _get_source(collection_name, source_params):
    try:
        source_type_name = source_params["type"]
    except KeyError:
        raise MissingAttributeError("Source for '{}' requires a 'type' attribute: {}"
                                    .format(collection_name, source_params))
    source_type = _get_enum_value(SourceType, source_type_name)
    if source_type == SourceType.COPY:
        try:
            source_name = source_params["original"]
        except KeyError:
            raise MissingAttributeError("Source for '{}' copy requires an 'original' attribute: {}"
                                        .format(collection_name, source_params))
        return _get_from_collection(collection_name, source_name)
    elif source_type in (SourceType.FILE, SourceType.URL):
        try:
            location = source_params["location"]
        except KeyError:
            raise MissingAttributeError("Source for '{}' requires a 'location' attribute: {}"
                                        .format(collection_name, source_params))
        if source_type == SourceType.FILE:
            location = "file://" + os.path.abspath(location)
        detected_filetype = detect_file_type(location)
        if detected_filetype:
            return detected_filetype.importer(detected_filetype.uri)
        else:
            raise InvalidDataError("Failed to load model from '{}'".format(location))
    elif source_type == SourceType.TASK:
        try:
            task_name = source_params["task"]
        except KeyError:
            raise MissingAttributeError("Sourcing a task for '{}' requires a 'task' attribute: {}"
                                        .format(collection_name, source_params))
        return _get_from_collection("task", task_name)
    elif source_type == SourceType.TOOLPATH:
        try:
            toolpath_names = source_params["toolpaths"]
        except KeyError:
            raise MissingAttributeError("Sourcing a toolpath for '{}' requires a 'toolpaths' "
                                        "attribute: {}".format(collection_name, source_params))
        return _get_from_collection("toolpath", toolpath_names, many=True)
    else:
        raise InvalidKeyError(source_type, SourceType)


def _get_source_loader(collection_name):
    return functools.partial(_get_source, collection_name)


def _get_target(collection_name, target_params):
    try:
        target_type_name = target_params["type"]
    except KeyError:
        raise MissingAttributeError("Target for '{}' requires a 'type' attribute: {}"
                                    .format(collection_name, target_params))
    target_type = _get_enum_value(TargetType, target_type_name)
    if target_type == TargetType.FILE:
        try:
            location = target_params["location"]
        except KeyError:
            raise MissingAttributeError("Target for '{}' requires a 'location' attribute: {}"
                                        .format(collection_name, target_params))
        return open(location, "w")
    else:
        raise InvalidKeyError(target_type, TargetType)


def _get_target_loader(collection_name):
    return functools.partial(_get_target, collection_name)


def _get_from_collection(collection_name, wanted, many=False):
    default_result = [] if many else None
    try:
        collection = _data_collections[collection_name]
    except KeyError:
        return default_result
    try:
        if many:
            return tuple([collection[item_id] for item_id in wanted])
        else:
            return collection[wanted]
    except KeyError:
        return default_result


def _get_full_collection(collection_name):
    try:
        return _data_collections[collection_name].values()
    except KeyError:
        return None


def _get_collection_resolver(collection_name, many=False):
    return functools.partial(_get_from_collection, collection_name, many=many)


class BaseDataContainer(object):

    attribute_converters = {}
    attribute_defaults = {}

    def __init__(self, data):
        self._data = copy.deepcopy(data)

    @classmethod
    def parse_from_dict(cls, data):
        return cls(data)

    def get_value(self, key, default=None):
        try:
            raw = self._data[key]
        except KeyError:
            if default is not None:
                raw = default
            elif key in self.attribute_defaults:
                raw = self.attribute_defaults[key]
            else:
                raise MissingAttributeError("The attribute '{}' is missing in '{}'"
                                            .format(key, type(self)))
        if key in self.attribute_converters:
            return self.attribute_converters[key](raw)
        else:
            return raw

    def set_value(self, key, value):
        self._data[key] = value

    def get_dict(self):
        return copy.deepcopy(self._data)


class BaseCollectionItemDataContainer(BaseDataContainer):

    # the name of the collection should be overwritten in every subclass
    collection_name = None
    unique_attribute = "name"

    def __init__(self, data):
        super(BaseCollectionItemDataContainer, self).__init__(data)
        assert self.collection_name is not None
        item_id = data[self.unique_attribute]
        self.__get_collection()[item_id] = self

    def __get_collection(self):
        try:
            return _data_collections[self.collection_name]
        except KeyError:
            collection = {}
            _data_collections[self.collection_name] = collection
            return collection

    def __del__(self):
        item_id = self._data[self.unique_attribute]
        # maybe the dict of collections is already gone (during shutdown)
        if _data_collections:
            collection = self.__get_collection()
            try:
                del collection[item_id]
            except KeyError:
                pass


class Model(BaseCollectionItemDataContainer):

    collection_name = "model"
    attribute_converters = {"source": _get_source_loader("model")}

    def get_model(self):
        return self.get_value("source")


class Tool(BaseCollectionItemDataContainer):

    collection_name = "tool"
    attribute_converters = {"shape": _get_enum_resolver(ToolShape)}
    attribute_defaults = {"height": 10,
                          "feed": 300,
                          "speed": 1000}

    def get_tool_geometry(self):
        height = self.get_value("height")
        shape = self.get_value("shape")
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
        try:
            return self.get_value("radius")
        except MissingAttributeError:
            pass
        return self.get_value("diameter") / 2

    @property
    def diameter(self):
        return 2 * self.radius

    def get_toolpath_filters(self):
        feed = self.get_value("feed")
        speed = self.get_value("speed")
        return [MachineSetting("feedrate", feed), MachineSetting("spindle_speed", speed)]


class Process(BaseCollectionItemDataContainer):

    collection_name = "process"
    attribute_converters = {"strategy": _get_enum_resolver(ProcessStrategy),
                            "milling_style": _get_enum_resolver(MotionGrid.MillingStyle),
                            "path_pattern": _get_enum_resolver(PathPattern),
                            "grid_direction": _get_enum_resolver(MotionGrid.GridDirection),
                            "spiral_direction": _get_enum_resolver(MotionGrid.SpiralDirection),
                            "pocketing_type": _get_enum_resolver(MotionGrid.PocketingType),
                            "trace_models": _get_collection_resolver("model", many=True),
                            "rounded_corners": _bool_converter,
                            "radius_compensation": _bool_converter,
                            "step_down": float}
    attribute_defaults = {"overlap": 0,
                          "path_pattern": PathPattern.GRID,
                          "grid_direction": MotionGrid.GridDirection.X,
                          "spiral_direction": MotionGrid.SpiralDirection.OUT,
                          "rounded_corners": True,
                          "radius_compensation": False}

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
        strategy = self.get_value("strategy")
        overlap = self.get_value("overlap")
        line_distance = 2 * tool_radius * (1 - overlap)
        milling_style = self.get_value("milling_style")
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
            if path_pattern == PathPattern.SPIRAL:
                func = MotionGrid.get_spiral
                kwarg_names = ("path_pattern", "grid_direction")
            elif path_pattern == PathPattern.GRID:
                func = MotionGrid.get_fixed_grid
                kwarg_names = ("path_pattern", "spiral_direction", "rounded_corners")
            else:
                raise InvalidKeyError(path_pattern, PathPattern)
            # surfacing requires a finer grid (arbitrary factor)
            step_width = tool_radius / 4.0
            kwargs = {key: self.get_value(key) for key in kwarg_names}
            return func(box, None, step_width=step_width, line_distance=line_distance,
                        milling_style=milling_style, **kwargs)
        elif strategy == ProcessStrategy.ENGRAVE:
            models = [m.get_model() for m in self.get_value("trace_models")]
            if not models:
                _log.error("No trace models given: you need to assign a 2D model to the engraving "
                           "process.")
                return None
            progress = self.core.get("progress")
            radius_compensation = self.get_value("radius_compensation")
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
            pocketing_type = self.get_value("pocketing_type")
            motion_grid = MotionGrid.get_lines_grid(
                models, box, self.get_value("step_down"), line_distance=line_distance,
                step_width=step_width, milling_style=milling_style, pocketing_type=pocketing_type,
                skip_first_layer=True, callback=progress.update)
            progress.finish()
            return motion_grid
        else:
            raise InvalidKeyError(strategy, ProcessStrategy)


class Boundary(BaseCollectionItemDataContainer):

    collection_name = "bounds"
    attribute_converters = {"specification": _get_enum_resolver(BoundsSpecification),
                            "reference_models": _get_collection_resolver("model", many=True),
                            "lower": _limit3d_converter,
                            "upper": _limit3d_converter,
                            "tool_boundary": _get_enum_resolver(ToolBoundaryMode)}
    attribute_defaults = {"tool_boundary": ToolBoundaryMode.ALONG}

    def get_absolute_limits(self, tool_radius=None, models=None):
        lower = self.get_value("lower")
        upper = self.get_value("upper")
        if self.get_value("specification") == BoundsSpecification.MARGINS:
            # choose the appropriate set of models
            reference_models = self.get_value("reference_models")
            if reference_models:
                # configured models always take precedence
                models = reference_models
            elif models:
                # use the supplied models (e.g. for toolpath calculation)
                pass
            else:
                # use all visible models -> for live visualization
                # TODO: filter for visible models
                models = self._get_full_collection("model")
            model_box = pycam.Geometry.Model.get_combined_bounds([model.model for model in models])
            if model_box is None:
                # zero-sized models -> no action
                return None
            is_percent = _RELATIVE_UNIT[self["parameters"]["RelativeUnit"]] == "%"
            low, high = [], []
            for model_lower, model_upper, margin_lower, margin_upper in zip(
                    model_box.lower, model_box.upper, lower, upper):
                dim = model_upper - model_lower
                if margin_lower.is_relative:
                    low.append(model_lower - margin_lower.value * dim)
                else:
                    low.append(model_lower - margin_lower.value)
                if margin_upper.is_relative:
                    low.append(model_upper - margin_upper.value * dim)
                else:
                    low.append(model_upper - margin_upper.value)
        else:
            low, high = [], []
            for abs_lower, abs_upper in zip(lower, upper):
                if abs_lower.is_relative:
                    raise InvalidDataError("Relative (%) values not allowed for absolute boundary")
                low.append(abs_lower.value)
                if abs_upper.is_relative:
                    raise InvalidDataError("Relative (%) values not allowed for absolute boundary")
                high.append(abs_upper.value)
        tool_limit = self.get_value("tool_boundary")
        # apply inside/along/outside if a tool is given
        if tool_radius and (tool_limit != ToolBoundaryMode.ALONG):
            if tool_limit == ToolBoundaryMode.INSIDE:
                offset = -tool_radius
            else:
                offset = tool_radius
            # apply offset only for x and y
            for index in range(2):
                low[index] -= offset
                high[index] += offset
        return Box3D(Point3D(*low), Point3D(*high))


class Task(BaseCollectionItemDataContainer):

    collection_name = "task"
    attribute_converters = {"process": _get_collection_resolver("process"),
                            "bounds": _get_collection_resolver("bounds"),
                            "tool": _get_collection_resolver("tool"),
                            "type": _get_enum_resolver(TaskType),
                            "collision_models": _get_collection_resolver("model", many=True)}


    def generate_toolpath(self, callback=None):
        process = self.get_value("process")
        bounds = self.get_value("bounds")
        task_type = self.get_value("type")
        if task_type == TaskType.MILLING:
            tool = self.get_value("tool")
            box = bounds.get_absolute_limits(tool_radius=tool.radius,
                                             models=self.get_value("collision_models"))
            path_generator = process.get_path_generator()
            motion_grid = process.get_motion_grid(tool.radius, box)
            if path_generator is None:
                # we assume that an error message was given already
                return
            models = [m.get_model() for m in self.get_value("collision_models")]
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


class Toolpath(BaseCollectionItemDataContainer):

    collection_name = "toolpath"
    attribute_converters = {"source": _get_source_loader("toolpath")}

    def generate_toolpath(self):
        task = self.get_value("source")
        return task.generate_toolpath()


class Export(BaseCollectionItemDataContainer):

    collection_name = "export"
    attribute_converters = {"export_type": _get_enum_resolver(ExportType),
                            "source": _get_source_loader("export"),
                            "target": _get_target_loader("export")}

    def run_export(self):
        export_type = self.get_value("export_type")
        source = self.get_value("source")
        target = self.get_value("target")
        if export_type == ExportType.GCODE:
            # we expect a tuple of toolpaths as input
            if not isinstance(source, tuple):
                raise InvalidDataError("Invalid source data type for export type '{}': {} "
                                       "(expected: list of toolpaths)"
                                       .format(export_type, type(source)))
            if not all([isinstance(item, Toolpath) for item in source]):
                raise InvalidDataError("Invalid source data type for export type '{}': {} "
                                       "(expected: list of toolpaths)"
                                       .format(export_type, [type(item) for item in source]))
            generator = pycam.Exporters.GCode.LinuxCNC.LinuxCNC(target)
            # TODO: retrieve the filters from settings
#           generator.add_filters(settings_filters)
#           generator.add_filters(common_filters)
            for toolpath in source:
                calculated = toolpath.generate_toolpath()
                # TODO: implement toolpath.get_meta_data()
                generator.add_moves(calculated.path, calculated.filters)
            generator.finish()
            target.close()
        else:
            raise InvalidKeyError(export_type, ExportType)
