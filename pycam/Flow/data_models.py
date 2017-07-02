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
from pycam.Geometry.Plane import Plane
import pycam.PathGenerators.DropCutter
import pycam.PathGenerators.EngraveCutter
import pycam.PathGenerators.PushCutter
from pycam.Plugins.Bounds import ToolBoundaryMode
from pycam.Toolpath import ToolpathPathMode
import pycam.Toolpath.Filters as tp_filters
import pycam.Toolpath.MotionGrid as MotionGrid
from pycam.Importers import detect_file_type
from pycam.Utils import get_type_name
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


class AmbiguousDataError(InvalidDataError):
    pass


class UnexpectedAttributeError(InvalidDataError):
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


class ModelTransformationAction(Enum):
    SCALE = "scale"
    SHIFT = "shift"
    ROTATE = "rotate"
    MIRROR = "mirror"
    PROJECTION = "projection"


class ToolpathTransformationAction(Enum):
    CROP = "crop"


class ModelScaleTarget(Enum):
    FACTOR = "factor"
    SIZE = "size"


class ModelShiftTarget(Enum):
    DISTANCE = "distance"
    ALIGN_MIN = "align_min"
    ALIGN_MAX = "align_max"
    CENTER = "center"


class TargetType(Enum):
    FILE = "file"


class FormatType(Enum):
    GCODE = "gcode"


class GCodeDialect(Enum):
    LINUXCNC = "linuxcnc"


class ToolpathFilter(Enum):
    SAFETY_HEIGHT = "safety_height"
    PLUNGE_FEEDRATE = "plunge_feedrate"
    STEP_WIDTH = "step_width"
    CORNER_STYLE = "corner_style"


def _get_enum_value(enum_class, value):
    try:
        return enum_class(value)
    except ValueError:
        raise InvalidKeyError(value, enum_class)


def _get_enum_resolver(enum_class):
    """ return a function that would convert a raw value to an enum item of the given class """
    return functools.partial(_get_enum_value, enum_class)


def _get_list_item_value(item_converter, values):
    return [item_converter(value) for value in values]


def _get_list_resolver(item_converter):
    return functools.partial(_get_list_item_value, item_converter)


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
        raise InvalidDataError("Invalid boolean value type ({}): {}"
                               .format(get_type_name(value), value))


LimitSingle = collections.namedtuple("LimitSingle", ("value", "is_relative"))
Limit3D = collections.namedtuple("Limit3D", ("x", "y", "z"))
AxesValues = collections.namedtuple("AxesValues", ("x", "y", "z"))


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


def _axes_values_converter(data, allow_none=False):
    result = []
    if isinstance(data, (list, dict)):
        if isinstance(data, dict):
            data = dict(data)
            for key in "xyz":
                try:
                    value = data.pop(key)
                except KeyError:
                    if allow_none:
                        value = None
                    else:
                        raise InvalidDataError("Missing mandatory axis component ({})".format(key))
                result.append(value)
            if data:
                raise InvalidDataError("Superfluous axes key(s) supplied: {} (expected: x / y / z)"
                                       .format(" / ".join(data.keys())))
        else:
            # a list
            for value in data:
                result.append(value)
            if len(result) != 3:
                raise InvalidDataError("Invalid number of axis components supplied: {:d} "
                                       "(expected: 3)".format(len(result)))
        for index, value in enumerate(result):
            if value is not None:
                try:
                    result[index] = float(value)
                except ValueError:
                    raise InvalidDataError("Axis value is not a float: {} ({})"
                                           .format(value, get_type_name(value)))
    else:
        try:
            factor = float(data)
        except ValueError:
            raise InvalidDataError("Axis value is not a float: {} ({})"
                                   .format(data, get_type_name(data)))
        result = [factor] * 3
    return AxesValues(*result)


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


def _set_parser_context(description):
    """ store a string describing the current parser context (useful for error messages) """
    def wrap(func):
        def inner_function(self, *args, **kwargs):
            original_description = getattr(self, "_current_parser_context", None)
            self._current_parser_context = description
            try:
                result = func(self, *args, **kwargs)
            except FlowDescriptionBaseException as exc:
                # add a prefix to exceptions
                exc.message = "{} -> {}".format(self._current_parser_context, exc)
                raise exc
            if original_description is None:
                delattr(self, "_current_parser_context")
            else:
                self._current_parser_context = original_description
            return result
        return inner_function
    return wrap


def _set_allowed_attributes(attr_set):
    def wrap(func):
        def inner_function(self, *args, **kwargs):
            self.validate_allowed_attributes(attr_set)
            return func(self, *args, **kwargs)
        return inner_function
    return wrap


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
                if hasattr(self, "_current_parser_context"):
                    # the context will be added automatically
                    raise MissingAttributeError("missing attribute '{}'".format(key))
                else:
                    # generate a suitable context based on the object itself
                    raise MissingAttributeError("{} -> missing attribute '{}'"
                                                .format(get_type_name(self), key))
        if key in self.attribute_converters:
            return self.attribute_converters[key](raw)
        else:
            return raw

    def set_value(self, key, value):
        self._data[key] = value

    def get_dict(self):
        return copy.deepcopy(self._data)

    def validate_allowed_attributes(self, allowed_attributes):
        unexpected_attributes = set(self._data.keys()) - allowed_attributes
        if unexpected_attributes:
            unexpected_attributes_string = " / ".join(unexpected_attributes)
            raise UnexpectedAttributeError("unexpected attributes were given: {}"
                                           .format(unexpected_attributes_string))


class BaseCollectionItemDataContainer(BaseDataContainer):

    # the name of the collection should be overwritten in every subclass
    collection_name = None
    unique_attribute = "name"

    def __init__(self, data):
        super(BaseCollectionItemDataContainer, self).__init__(data)
        assert self.collection_name is not None, (
            "Missing unique attribute ({}) of '{}' class"
            .format(self.unique_attribute, get_type_name(self)))
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


class Source(BaseDataContainer):

    attribute_converters = {"type": _get_enum_resolver(SourceType)}

    def get(self, target_collection):
        source_type = self.get_value("type")
        if source_type == SourceType.COPY:
            return self._get_source_copy()
        elif source_type in (SourceType.FILE, SourceType.URL):
            return self._get_source_location(source_type)
        elif source_type == SourceType.TASK:
            return self._get_source_task()
        elif source_type == SourceType.TOOLPATH:
            return self._get_source_toolpath()
        else:
            raise InvalidKeyError(source_type, SourceType)

    @_set_parser_context("Source 'copy'")
    @_set_allowed_attributes({"type", "original"})
    def _get_source_copy(self):
        source_name = self.get_value("original")
        return _get_from_collection(target_collection, source_name).get_model()

    @_set_parser_context("Source 'file/url'")
    @_set_allowed_attributes({"type", "location"})
    def _get_source_location(self, source_type):
        location = self.get_value("location")
        if source_type == SourceType.FILE:
            location = "file://" + os.path.abspath(location)
        detected_filetype = detect_file_type(location)
        if detected_filetype:
            return detected_filetype.importer(detected_filetype.uri)
        else:
            raise InvalidDataError("Failed to load model from '{}'".format(location))

    @_set_parser_context("Source 'task'")
    @_set_allowed_attributes({"type", "task"})
    def _get_source_task(self):
        task_name = self.get_value("task")
        return _get_from_collection("task", task_name)

    @_set_parser_context("Source 'toolpath'")
    @_set_allowed_attributes({"type", "toolpaths"})
    def _get_source_toolpath(self):
        toolpath_names = self.get_value("toolpaths")
        return _get_from_collection("toolpath", toolpath_names, many=True)


class ModelTransformation(BaseDataContainer):

    attribute_converters = {"action": _get_enum_resolver(ModelTransformationAction),
                            "scale_target": _get_enum_resolver(ModelScaleTarget),
                            "shift_target": _get_enum_resolver(ModelShiftTarget),
                            "center": _axes_values_converter,
                            "vector": _axes_values_converter,
                            "angle": float,
                            "axes": functools.partial(_axes_values_converter, allow_none=True)}

    def get_transformed_model(self, model):
        action = self.get_value("action")
        if action == ModelTransformationAction.SCALE:
            return self._get_scaled_model(model)
        elif action == ModelTransformationAction.SHIFT:
            return self._get_shifted_model(model)
        elif action == ModelTransformationAction.ROTATE:
            return self._get_rotated_model(model)
        elif action == ModelTransformationAction.MIRROR:
            # Sadly mirroring against an arbitrary plane (instead of simple XY, XZ or YZ planes) is
            # rather complicated.
            raise NotImplemented("The 'mirror' transformation is not implemented, yet.")
        elif action == ModelTransformationAction.PROJECTION:
            return self._get_projected_model(model)
        else:
            raise InvalidKeyError(action, ModelTransformationAction)

    @_set_parser_context("Model transformation 'scale'")
    @_set_allowed_attributes({"action", "scale_target", "axes"})
    def _get_scaled_model(self, model):
        target = self.get_value("scale_target")
        axes = self.get_value("axes")
        kwargs = {}
        if target == ModelScaleTarget.FACTOR:
            for key, value in zip(("scale_x", "scale_y", "scale_z"), axes):
                kwargs[key] = 1.0 if value is None else value
        elif target == ModelScaleTarget.SIZE:
            for key, current_size, target_size in zip(
                    ("scale_x", "scale_y", "scale_z"), model.get_dimensions(), axes):
                if current_size == 0:
                    raise InvalidDataError("Model transformation 'scale' does not accept "
                                           "zero as a target size ({}).".format(key))
                elif target_size is None:
                    kwargs[key] = 1.0
                else:
                    kwargs[key] = target_size / current_size
        else:
            assert False
        new_model = model.copy()
        new_model.scale(**kwargs)
        return new_model

    @_set_parser_context("Model transformation 'shift'")
    @_set_allowed_attributes({"action", "shift_target", "axes"})
    def _get_shifted_model(self, model):
        target = self.get_value("shift_target")
        axes = self.get_value("axes")
        args = []
        if target == ModelShiftTarget.DISTANCE:
            for value in axes:
                args.append(0.0 if value is None else value)
        elif target == ModelShiftTarget.ALIGN_MIN:
            for value, current_position in zip(axes, (model.minx, model.miny, model.minz)):
                args.append(0.0 if value is None else (value - current_position))
        elif target == ModelShiftTarget.ALIGN_MAX:
            for value, current_position in zip(axes, (model.maxx, model.maxy, model.maxz)):
                args.append(0.0 if value is None else (value - current_position))
        elif target == ModelShiftTarget.CENTER:
            for value, current_position in zip(axes, model.get_center()):
                args.append(0.0 if value is None else (value - current_position))
        else:
            assert False
        new_model = model.copy()
        new_model.shift(*args)
        return new_model

    @_set_parser_context("Model transformation 'rotate'")
    @_set_allowed_attributes({"action", "center", "vector", "angle"})
    def _get_rotated_model(self, model):
        self.validate_allowed_attributes({"action", "center", "vector", "angle"})
        center = self.get_value("center")
        vector = self.get_value("vector")
        angle = self.get_value("angle")
        new_model = model.copy()
        new_model.rotate(center, vector, angle)
        return new_model

    @_set_parser_context("Model transformation 'projection'")
    @_set_allowed_attributes({"action", "center", "vector"})
    def _get_projected_model(self, model):
        self.validate_allowed_attributes({"action", "center", "vector"})
        center = self.get_value("center")
        vector = self.get_value("vector")
        plane = Plane(center, vector)
        # TODO: this is not an in-place operation (since the model type changes)
        return model.get_waterline_contour(plane)


class Model(BaseCollectionItemDataContainer):

    collection_name = "model"
    attribute_converters = {"source": Source,
                            "transformations": _get_list_resolver(ModelTransformation)}
    attribute_defaults = {"transformations": []}

    def get_model(self):
        model = self.get_value("source").get("model")
        for transformation in self.get_value("transformations"):
            model = transformation.get_transformed_model(model)
        return model


class Tool(BaseCollectionItemDataContainer):

    collection_name = "tool"
    attribute_converters = {"shape": _get_enum_resolver(ToolShape)}
    attribute_defaults = {"height": 10,
                          "feed": 300,
                          "spindle_enabled": True,
                          "spindle_speed": 1000,
                          "spindle_delay": 0}

    @_set_parser_context("Tool")
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
    @_set_parser_context("Tool radius")
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
        result = []
        result.append(tp_filters.MachineSetting("feedrate", self.get_value("feed")))
        if self.get_value("spindle_enabled"):
            result.append(tp_filters.MachineSetting("spindle_speed",
                                                    self.get_value("spindle_speed")))
            result.append(tp_filters.TriggerSpindle(delay=self.get_value("spindle_delay")))
        return result


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

    @_set_parser_context("Process")
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

    @_set_parser_context("Process")
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
            path_pattern = self.get_value("path_pattern")
            if path_pattern == PathPattern.SPIRAL:
                func = MotionGrid.get_spiral
                kwarg_names = ("grid_direction")
            elif path_pattern == PathPattern.GRID:
                func = MotionGrid.get_fixed_grid
                kwarg_names = ("spiral_direction", "rounded_corners")
            else:
                raise InvalidKeyError(path_pattern, PathPattern)
            # surfacing requires a finer grid (arbitrary factor)
            step_width = tool_radius / 4.0
            kwargs = {key: self.get_value(key) for key in kwarg_names}
            return func(box, None, step_width=step_width, line_distance=line_distance,
                        milling_style=milling_style, path_pattern=path_pattern, **kwargs)
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

    @_set_parser_context("Boundary")
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
            model_box = pycam.Geometry.Model.get_combined_bounds([model.get_model()
                                                                  for model in models])
            if model_box is None:
                # zero-sized models -> no action
                return None
            low, high = [], []
            for model_lower, model_upper, margin_lower, margin_upper in zip(
                    model_box.lower, model_box.upper, lower, upper):
                dim = model_upper - model_lower
                if margin_lower.is_relative:
                    low.append(model_lower - margin_lower.value * dim)
                else:
                    low.append(model_lower - margin_lower.value)
                if margin_upper.is_relative:
                    high.append(model_upper - margin_upper.value * dim)
                else:
                    high.append(model_upper - margin_upper.value)
        else:
            # absolute boundary
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

    @_set_parser_context("Task")
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


class ToolpathTransformation(BaseDataContainer):

    attribute_converters = {"action": _get_enum_resolver(ToolpathTransformationAction),
                            "lower": functools.partial(_axes_values_converter, allow_none=True),
                            "upper": functools.partial(_axes_values_converter, allow_none=True)}

    def get_transformed_toolpath(self, toolpath):
        action = self.get_value("action")
        if action == ToolpathTransformationAction.CROP:
            return self._get_cropped_toolpath(toolpath)
        else:
            raise InvalidKeyError(action, ToolpathTransformationAction)

    @_set_parser_context("Toolpath transformation 'crop'")
    @_set_allowed_attributes({"action", "lower", "upper"})
    def _get_cropped_toolpath(self, toolpath):
        raise NotImplemented("Toolpath cropping is not implemented, yet.")


class Toolpath(BaseCollectionItemDataContainer):

    collection_name = "toolpath"
    attribute_converters = {"source": Source,
                            "transformations": _get_list_resolver(ToolpathTransformation)}
    attribute_defaults = {"transformations": []}

    @_set_parser_context("Toolpath")
    def get_toolpath(self):
        task = self.get_value("source").get("toolpath")
        toolpath = task.generate_toolpath()
        for transformation in self.get_value("transformations"):
            toolpath = transformation.get_transformed_toolpath(toolpath)
        return toolpath


class ExportSettings(BaseCollectionItemDataContainer):

    collection_name = "export_settings"

    def get_settings_by_type(self, export_type):
        return self.get_value(export_type, {})

    @_set_parser_context("Export settings")
    def get_toolpath_filters(self):
        result = []
        for text_name, parameters in self.get_settings_by_type("gcode").items():
            filter_name = _get_enum_value(ToolpathFilter, text_name)
            if filter_name == ToolpathFilter.SAFETY_HEIGHT:
                result.append(tp_filters.SafetyHeight(float(parameters)))
            elif filter_name == ToolpathFilter.PLUNGE_FEEDRATE:
                result.append(tp_filters.PlungeFeedrate(float(parameters)))
            elif filter_name == ToolpathFilter.STEP_WIDTH:
                result.append(tp_filters.StepWidth(float(parameters["x"]),
                                                   float(parameters["y"]),
                                                   float(parameters["z"])))
            elif filter_name == ToolpathFilter.CORNER_STYLE:
                mode = _get_enum_value(ToolpathPathMode, parameters["mode"])
                motion_tolerance = parameters.get("motion_tolerance", 0)
                naive_tolerance = parameters.get("naive_tolerance", 0)
                result.append(tp_filters.CornerStyle(mode, motion_tolerance, naive_tolerance))
            else:
                raise InvalidKeyError(filter_name, ToolpathFilter)
        return result


class Target(BaseDataContainer):

    attribute_converters = {"type": _get_enum_resolver(TargetType)}

    @_set_parser_context("Export target")
    def open(self):
        target_type = self.get_value("type")
        if target_type == TargetType.FILE:
            location = self.get_value("location")
            return open(location, "w")
        else:
            raise InvalidKeyError(target_type, TargetType)


class Formatter(BaseDataContainer):

    attribute_converters = {"type": _get_enum_resolver(FormatType),
                            "dialect": _get_enum_resolver(GCodeDialect),
                            "export_settings": _get_collection_resolver("export_settings")}
    attribute_defaults = {"dialect": GCodeDialect.LINUXCNC,
                          "comment": ""}

    def write_data(self, source, target):
        format_type = self.get_value("type")
        if format_type == FormatType.GCODE:
            return self._write_gcode(source, target)
        else:
            raise InvalidKeyError(format_type, FormatType)

    @_set_parser_context("Export formatter 'GCode'")
    def _write_gcode(self, source, target):
        comment = self.get_value("comment")
        dialect = self.get_value("dialect")
        # we expect a tuple of toolpaths as input
        if not isinstance(source, (list, tuple)):
            raise InvalidDataError("Invalid source data type: {} (expected: list of toolpaths)"
                                   .format(get_type_name(source)))
        if not all([isinstance(item, Toolpath) for item in source]):
            raise InvalidDataError("Invalid source data type: {} (expected: list of toolpaths)"
                                   .format(" / ".join([get_type_name(item) for item in source])))
        if dialect == GCodeDialect.LINUXCNC:
            generator = pycam.Exporters.GCode.LinuxCNC.LinuxCNC(target, comment=comment)
        else:
            raise InvalidKeyError(dialect, GCodeDialect)
        export_settings = self.get_value("export_settings")
        generator.add_filters(export_settings.get_toolpath_filters())
        for toolpath in source:
            calculated = toolpath.get_toolpath()
            # TODO: implement toolpath.get_meta_data()
            generator.add_moves(calculated.path, calculated.filters)
        generator.finish()
        target.close()
        return True


class Export(BaseCollectionItemDataContainer):

    collection_name = "export"
    attribute_converters = {"format": Formatter,
                            "source": Source,
                            "target": Target}

    def run_export(self):
        formatter = self.get_value("format")
        source = self.get_value("source").get("export")
        target = self.get_value("target")
        formatter.write_data(source, target.open())
