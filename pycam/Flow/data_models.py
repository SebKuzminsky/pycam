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
import time
import uuid

from pycam.Cutters.CylindricalCutter import CylindricalCutter
from pycam.Cutters.SphericalCutter import SphericalCutter
from pycam.Cutters.ToroidalCutter import ToroidalCutter
from pycam.Geometry import Box3D, Point3D
from pycam.Geometry.Plane import Plane
from pycam.PathGenerators import UpdateToolView
import pycam.PathGenerators.DropCutter
import pycam.PathGenerators.EngraveCutter
import pycam.PathGenerators.PushCutter
import pycam.Toolpath
import pycam.Toolpath.Filters as tp_filters
import pycam.Toolpath.MotionGrid as MotionGrid
from pycam.Importers import detect_file_type
from pycam.Utils import get_type_name, get_application_key
from pycam.Utils.events import get_event_handler
from pycam.Utils.progress import ProgressContext
import pycam.Utils.log

_log = pycam.Utils.log.get_logger()


# dictionary of all collections by name
_data_collections = {}
_cache = {}


APPLICATION_ATTRIBUTES_KEY = "X-Application"


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
    OBJECT = "object"


class ModelTransformationAction(Enum):
    SCALE = "scale"
    SHIFT = "shift"
    ROTATE = "rotate"
    MULTIPLY_MATRIX = "multiply_matrix"
    PROJECTION = "projection"
    TOGGLE_POLYGON_DIRECTIONS = "toggle_polygon_directions"
    REVISE_POLYGON_DIRECTIONS = "revise_polygon_directions"


class ToolpathTransformationAction(Enum):
    CROP = "crop"
    CLONE = "clone"
    SHIFT = "shift"


class ModelScaleTarget(Enum):
    FACTOR = "factor"
    SIZE = "size"


class PositionShiftTarget(Enum):
    DISTANCE = "distance"
    ALIGN_MIN = "align_min"
    ALIGN_MAX = "align_max"
    CENTER = "center"

    @classmethod
    def _get_shift_offset(cls, shift_target, shift_axes, obj):
        offset = []
        if shift_target == cls.DISTANCE:
            for value in shift_axes:
                offset.append(0.0 if value is None else value)
        elif shift_target == cls.ALIGN_MIN:
            for value, current_position in zip(shift_axes, (obj.minx, obj.miny, obj.minz)):
                offset.append(0.0 if value is None else (value - current_position))
        elif shift_target == cls.ALIGN_MAX:
            for value, current_position in zip(shift_axes, (obj.maxx, obj.maxy, obj.maxz)):
                offset.append(0.0 if value is None else (value - current_position))
        elif shift_target == cls.CENTER:
            for value, current_position in zip(shift_axes, obj.get_center()):
                offset.append(0.0 if value is None else (value - current_position))
        else:
            assert False
        return offset


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


class ToolBoundaryMode(Enum):
    INSIDE = "inside"
    ALONG = "along"
    AROUND = "around"


class ModelType(Enum):
    TRIMESH = "trimesh"
    POLYGON = "polygon"


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


class LimitSingle(collections.namedtuple("LimitSingle", ("value", "is_relative"))):

    @property
    def export(self):
        """return the storage string for later parsing"""
        if self.is_relative:
            return "{:f}%".format(self.value)
        else:
            return self.value


Limit3D = collections.namedtuple("Limit3D", ("x", "y", "z"))
AxesValues = collections.namedtuple("AxesValues", ("x", "y", "z"))
CacheItem = collections.namedtuple("CacheItem", ("timestamp", "content"))


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
        if isinstance(value, LimitSingle):
            value, is_relative = value
        elif isinstance(value, str):
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


def _get_collection_resolver(collection_name, many=False):
    return functools.partial(_get_from_collection, collection_name, many=many)


def _set_parser_context(description):
    """ store a string describing the current parser context (useful for error messages) """
    def wrap(func):
        @functools.wraps(func)
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
        @functools.wraps(func)
        def inner_function(self, *args, **kwargs):
            self.validate_allowed_attributes(attr_set)
            return func(self, *args, **kwargs)
        return inner_function
    return wrap


def _require_model_type(wanted_type):
    def wrap(func):
        @functools.wraps(func)
        def inner_function(self, model, *args, **kwargs):
            if (wanted_type == ModelType.TRIMESH) and not hasattr(model, "triangles"):
                raise InvalidDataError(
                    "Expected 3D mesh model, but received '{}'".format(type(model)))
            elif (wanted_type == ModelType.POLYGON) and not hasattr(model, "get_polygons"):
                raise InvalidDataError(
                    "Expected 2D polygon model, but received '{}'".format(type(model)))
            else:
                return func(self, model, *args, **kwargs)
        return inner_function
    return wrap


class CacheStorage(object):
    """ cache result values of a method

    The method's instance object may be a BaseDataContainer (or another non-trivial object).
    Arguments for the method call are hashed.
    Multiple data keys for a BaseDataContainer may be specified - a change of their value
    invalidates cached values.
    """

    def __init__(self, relevant_dict_keys, max_cache_size=10):
        self._relevant_dict_keys = tuple(relevant_dict_keys)
        self._max_cache_size = max_cache_size

    def __call__(self, calc_function):
        def wrapped(inst, *args, **kwargs):
            return self.get_cached(inst, args, kwargs, calc_function)
        return wrapped

    @classmethod
    def _get_stable_hashs_for_value(cls, value):
        """calculate a hash value for simple values and complex objects"""
        if isinstance(value, dict):
            for key_value in sorted(value.items()):
                yield from cls._get_stable_hashs_for_value(key_value)
        elif isinstance(value, (list, tuple)):
            for item in value:
                yield from cls._get_stable_hashs_for_value(item)
        elif isinstance(value, (float, int, str)):
            yield hash(value)
        elif isinstance(value, pycam.Toolpath.Toolpath):
            yield hash(value)
        elif value is None:
            yield hash(None)
        elif isinstance(value, BaseDataContainer):
            yield from cls._get_stable_hashs_for_value(value.get_dict())
        elif isinstance(value, Enum):
            yield hash(value.value)
        else:
            assert False, ("Non-hashable type needs hash conversion for cache key: {}"
                           .format(type(value)))

    def _get_cache_key(self, inst, args, kwargs):
        hashes = []
        for key in self._relevant_dict_keys:
            value = inst.get_value(key)
            hashes.append(hash(key))
            hashes.extend(self._get_stable_hashs_for_value(value))
        return (tuple(hashes)
                + tuple(self._get_stable_hashs_for_value(args))
                + tuple(self._get_stable_hashs_for_value(kwargs)))

    def get_cached(self, inst, args, kwargs, calc_function):
        # every instance manages its own cache
        try:
            my_cache = _cache[hash(inst)]
        except KeyError:
            my_cache = {}
            _cache[hash(inst)] = my_cache
        cache_key = self._get_cache_key(inst, args, kwargs)
        try:
            return my_cache[cache_key].content
        except KeyError:
            pass
        cache_item = CacheItem(time.time(), calc_function(inst, *args, **kwargs))
        my_cache[cache_key] = cache_item
        if len(my_cache) > self._max_cache_size:
            # remove the oldest cache item
            item_list = [(key, value.timestamp) for key, value in my_cache.items()]
            item_list.sort(key=lambda item: item[1])
            my_cache.pop(item_list[0][0])
        return cache_item.content


class BaseDataContainer(object):

    attribute_converters = {}
    attribute_defaults = {}
    changed_event = None

    def __init__(self, data):
        data = copy.deepcopy(data)
        # split the application-specific data (e.g. colors or visibility flags) from the model data
        self._application_attributes = data.pop(APPLICATION_ATTRIBUTES_KEY, {})
        self._data = data

    @classmethod
    def parse_from_dict(cls, data):
        return cls(data)

    def get_value(self, key, default=None, raw=False):
        try:
            raw_value = self._data[key]
        except KeyError:
            if default is not None:
                raw_value = default
            elif key in self.attribute_defaults:
                raw_value = copy.deepcopy(self.attribute_defaults[key])
            else:
                if hasattr(self, "_current_parser_context"):
                    # the context will be added automatically
                    raise MissingAttributeError("missing attribute '{}'".format(key))
                else:
                    # generate a suitable context based on the object itself
                    raise MissingAttributeError("{} -> missing attribute '{}'"
                                                .format(get_type_name(self), key))
        if raw:
            return raw_value
        elif key in self.attribute_converters:
            value = self.attribute_converters[key](raw_value)
            if hasattr(value, "set_related_collection"):
                # special case for Source: we need the original collection for "copy"
                value.set_related_collection(self.collection_name)
            return value
        else:
            return raw_value

    def set_value(self, key, value):
        new_value = copy.deepcopy(value)
        if self._data.get(key) != new_value:
            self._data[key] = new_value
            self.notify_changed()

    def extend_value(self, key, values):
        """extend a value (which must be a list) with additional values

        This is just a convenience wrapper for the combination of "get_value", "get_dict",
        "extend" and "set_value".
        """
        if values:
            try:
                current_list = self._data[key]
            except KeyError:
                current_list = []
                self._data[key] = current_list
            current_list.extend(values)
            self.notify_changed()

    def get_dict(self, with_application_attributes=False):
        result = copy.deepcopy(self._data)
        if with_application_attributes:
            minimized_data = {key: value
                              for key, value in copy.deepcopy(self._application_attributes).items()
                              if value}
            if minimized_data:
                result[APPLICATION_ATTRIBUTES_KEY] = minimized_data
        return result

    def _get_current_application_dict(self):
        try:
            return self._application_attributes[get_application_key()]
        except KeyError:
            self._application_attributes[get_application_key()] = {}
        return self._application_attributes[get_application_key()]

    def set_application_value(self, key, value):
        new_value = copy.deepcopy(value)
        value_dict = self._get_current_application_dict()
        if value_dict.get(key) != new_value:
            value_dict[key] = new_value
            self.notify_changed()

    def get_application_value(self, key, default=None):
        return self._get_current_application_dict().get(key, default)

    def validate_allowed_attributes(self, allowed_attributes):
        unexpected_attributes = set(self._data.keys()) - allowed_attributes
        if unexpected_attributes:
            unexpected_attributes_string = " / ".join(unexpected_attributes)
            raise UnexpectedAttributeError("unexpected attributes were given: {}"
                                           .format(unexpected_attributes_string))

    def notify_changed(self):
        if self.changed_event:
            get_event_handler().emit_event(self.changed_event)

    def __str__(self):
        attr_dict_string = ", ".join("{}={}".format(key, value)
                                     for key, value in self.get_dict().items())
        return "{}({})".format(get_type_name(self), attr_dict_string)


class BaseCollection(object):

    def __init__(self, name, list_changed_event=None):
        self._name = name
        self._list_changed_event = list_changed_event
        self._data = []

    @property
    def list_changed_event(self):
        return self._list_changed_event

    def clear(self):
        if self._data:
            while self._data:
                self._data.pop()
            self.notify_list_changed()

    def __setitem__(self, index, value):
        if self._data[index] != value:
            self._data[index] = value
            self.notify_list_changed()

    def append(self, value):
        self._data.append(value)
        self.notify_list_changed()

    def __getitem__(self, index_or_key):
        for item in self._data:
            if index_or_key == item.get_id():
                return item
        else:
            # Not found by ID? Interprete the value as an index.
            if isinstance(index_or_key, int):
                return self._data[index_or_key]
            else:
                _log.warning("Failed to find item in collection (%s): %s (expected: %s)",
                             self._name, index_or_key, [item.get_id() for item in self._data])
                return None

    def __delitem__(self, index):
        item = self[index]
        if item is not None:
            try:
                self.remove(item)
            except ValueError:
                pass

    def remove(self, item):
        _log.info("Removing '{}' from collection '{}'".format(item.get_id(), self._name))
        try:
            self._data.remove(item)
        except ValueError:
            raise KeyError("Failed to remove '{}' from collection '{}'"
                           .format(item.get_id(), self._name))
        self.notify_list_changed()

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __contains__(self, key):
        return (key in self._data) or (key in [item.get_id() for item in self._data])

    def __bool__(self):
        return len(self._data) > 0

    def swap_by_index(self, index1, index2):
        assert index1 != index2
        smaller, bigger = min(index1, index2), max(index1, index2)
        item1 = self._data.pop(bigger)
        item2 = self._data.pop(smaller)
        self._data.insert(smaller, item1)
        self._data.insert(bigger, item2)
        self.notify_list_changed()

    def get_dict(self, with_application_attributes=False):
        result = {}
        for item in self._data:
            result[item.get_id()] = item.get_dict(
                with_application_attributes=with_application_attributes)
        return result

    def notify_list_changed(self):
        if self._list_changed_event:
            get_event_handler().emit_event(self._list_changed_event)


class BaseCollectionItemDataContainer(BaseDataContainer):

    # the name of the collection should be overwritten in every subclass
    collection_name = None
    list_changed_event = None
    unique_attribute = "uuid"

    def __init__(self, item_id, data):
        super(BaseCollectionItemDataContainer, self).__init__(data)
        assert self.collection_name is not None, (
            "Missing unique attribute ({}) of '{}' class"
            .format(self.unique_attribute, get_type_name(self)))
        if item_id is None:
            item_id = uuid.uuid4().hex
        try:
            hash(item_id)
        except TypeError:
            raise InvalidDataError("Invalid item ID ({}): not hashable".format(item_id))
        self._data[self.unique_attribute] = item_id
        self.get_collection().append(self)

    def get_id(self):
        return self.get_dict()[self.unique_attribute]

    @classmethod
    def get_collection(cls):
        try:
            return _data_collections[cls.collection_name]
        except KeyError:
            collection = BaseCollection(cls.collection_name,
                                        list_changed_event=cls.list_changed_event)
            _data_collections[cls.collection_name] = collection
            return collection

    def __del__(self):
        # maybe the dict of collections is already gone (during shutdown)
        if _data_collections:
            collection = self.get_collection()
            try:
                del collection[self.get_id()]
            except KeyError:
                pass


class Source(BaseDataContainer):

    attribute_converters = {"type": _get_enum_resolver(SourceType)}

    def __hash__(self):
        source_type = self.get_value("type")
        if source_type == SourceType.COPY:
            return hash(self._get_source_copy())
        elif source_type in (SourceType.FILE, SourceType.URL):
            return hash(self.get_value("location"))
        elif source_type == SourceType.TASK:
            return hash(self._get_source_task())
        elif source_type == SourceType.TOOLPATH:
            return hash(self._get_source_toolpath())
        elif source_type == SourceType.OBJECT:
            return hash(self._get_source_object())
        else:
            raise InvalidKeyError(source_type, SourceType)

    @CacheStorage({"type"})
    @_set_parser_context("Source")
    def get(self, related_collection_name):
        source_type = self.get_value("type")
        if source_type == SourceType.COPY:
            return self._get_source_copy(related_collection_name)
        elif source_type in (SourceType.FILE, SourceType.URL):
            return self._get_source_location(source_type)
        elif source_type == SourceType.TASK:
            return self._get_source_task()
        elif source_type == SourceType.TOOLPATH:
            return self._get_source_toolpath()
        elif source_type == SourceType.OBJECT:
            return self._get_source_object()
        else:
            raise InvalidKeyError(source_type, SourceType)

    @_set_parser_context("Source 'copy'")
    @_set_allowed_attributes({"type", "original"})
    def _get_source_copy(self, related_collection_name):
        source_name = self.get_value("original")
        return _get_from_collection(related_collection_name, source_name).get_model()

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

    @_set_parser_context("Source 'object'")
    @_set_allowed_attributes({"type", "data"})
    def _get_source_object(self):
        """ transfer method for intra-process transfer """
        return self.get_value("data")


class ModelTransformation(BaseDataContainer):

    attribute_converters = {"action": _get_enum_resolver(ModelTransformationAction),
                            "scale_target": _get_enum_resolver(ModelScaleTarget),
                            "shift_target": _get_enum_resolver(PositionShiftTarget),
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
        elif action == ModelTransformationAction.MULTIPLY_MATRIX:
            return self._get_matrix_multiplied_model(model)
        elif action == ModelTransformationAction.PROJECTION:
            return self._get_projected_model(model)
        elif action in (ModelTransformationAction.TOGGLE_POLYGON_DIRECTIONS,
                        ModelTransformationAction.REVISE_POLYGON_DIRECTIONS):
            return self._get_polygon_transformed(model)
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
        with ProgressContext("Scaling model") as progress:
            new_model.scale(callback=progress.update, **kwargs)
        return new_model

    @_set_parser_context("Model transformation 'shift'")
    @_set_allowed_attributes({"action", "shift_target", "axes"})
    def _get_shifted_model(self, model):
        target = self.get_value("shift_target")
        axes = self.get_value("axes")
        offset = target._get_shift_offset(target, axes, model)
        new_model = model.copy()
        with ProgressContext("Shifting Model") as progress:
            new_model.shift(*offset, callback=progress.update)
        return new_model

    @_set_parser_context("Model transformation 'rotate'")
    @_set_allowed_attributes({"action", "center", "vector", "angle"})
    def _get_rotated_model(self, model):
        center = self.get_value("center")
        vector = self.get_value("vector")
        angle = self.get_value("angle")
        new_model = model.copy()
        with ProgressContext("Rotating Model") as progress:
            new_model.rotate(center, vector, angle, callback=progress.update)
        return new_model

    @_set_parser_context("Model transformation 'matrix multiplication'")
    @_set_allowed_attributes({"action", "matrix"})
    def _get_matrix_multiplied_model(self, model):
        matrix = self.get_value("matrix")
        lengths = [len(row) for row in matrix]
        if not lengths == [3, 3, 3]:
            raise InvalidDataError("Invalid Matrix row lengths ({}) - expected [3, 3, 3] instead."
                                   .format(lengths))
        # add zero shift offsets (the fourth column)
        for row in matrix:
            row.append(0)
        new_model = model.copy()
        with ProgressContext("Transform Model") as progress:
            new_model.transform_by_matrix(matrix, callback=progress.update)
        return new_model

    @_set_parser_context("Model transformation 'projection'")
    @_set_allowed_attributes({"action", "center", "vector"})
    @_require_model_type(ModelType.TRIMESH)
    def _get_projected_model(self, model):
        center = self.get_value("center")
        vector = self.get_value("vector")
        plane = Plane(center, vector)
        with ProgressContext("Calculate waterline of model") as progress:
            return model.get_waterline_contour(plane, callback=progress.update)

    @_set_parser_context("Model transformation 'polygon directions'")
    @_set_allowed_attributes({"action"})
    @_require_model_type(ModelType.POLYGON)
    def _get_polygon_transformed(self, model):
        action = self.get_value("action")
        new_model = model.copy()
        if action == ModelTransformationAction.REVISE_POLYGON_DIRECTIONS:
            with ProgressContext("Revise polygon directions") as progress:
                new_model.revise_directions(callback=progress.update)
        elif action == ModelTransformationAction.TOGGLE_POLYGON_DIRECTIONS:
            with ProgressContext("Reverse polygon directions") as progress:
                new_model.reverse_directions(callback=progress.update)
        else:
            assert False
        return new_model


class Model(BaseCollectionItemDataContainer):

    collection_name = "model"
    changed_event = "model-changed"
    list_changed_event = "model-list-changed"
    attribute_converters = {"source": Source,
                            "transformations": _get_list_resolver(ModelTransformation)}
    attribute_defaults = {"transformations": []}

    @CacheStorage({"source", "transformations"})
    @_set_parser_context("Model")
    def get_model(self):
        model = self.get_value("source").get("model")
        for transformation in self.get_value("transformations"):
            model = transformation.get_transformed_model(model)
        return model


class Tool(BaseCollectionItemDataContainer):

    collection_name = "tool"
    changed_event = "tool-changed"
    list_changed_event = "tool-list-changed"
    attribute_converters = {"shape": _get_enum_resolver(ToolShape),
                            "tool_id": int,
                            "radius": float,
                            "diameter": float,
                            "toroid_radius": float,
                            "height": float,
                            "feed": float,
                            "spindle_enabled": _bool_converter,
                            "spindle_speed": float,
                            "spindle_delay": float}
    attribute_defaults = {"tool_id": 1,
                          "height": 10,
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
        return self.get_value("diameter") / 2.0

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
    changed_event = "process-changed"
    list_changed_event = "process-list-changed"
    attribute_converters = {"strategy": _get_enum_resolver(ProcessStrategy),
                            "milling_style": _get_enum_resolver(MotionGrid.MillingStyle),
                            "path_pattern": _get_enum_resolver(PathPattern),
                            "grid_direction": _get_enum_resolver(MotionGrid.GridDirection),
                            "spiral_direction": _get_enum_resolver(MotionGrid.SpiralDirection),
                            "pocketing_type": _get_enum_resolver(MotionGrid.PocketingType),
                            "trace_models": _get_collection_resolver("model", many=True),
                            "rounded_corners": _bool_converter,
                            "radius_compensation": _bool_converter,
                            "overlap": float,
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
                func = functools.partial(MotionGrid.get_spiral,
                                         spiral_direction=self.get_value("spiral_direction"),
                                         rounded_corners=self.get_value("rounded_corners"))
            elif path_pattern == PathPattern.GRID:
                func = functools.partial(MotionGrid.get_fixed_grid,
                                         grid_direction=self.get_value("grid_direction"))
            else:
                raise InvalidKeyError(path_pattern, PathPattern)
            # surfacing requires a finer grid (arbitrary factor)
            step_width = tool_radius / 4.0
            return func(box, None, step_width=step_width, line_distance=line_distance,
                        milling_style=milling_style)
        elif strategy == ProcessStrategy.ENGRAVE:
            models = [m.get_model() for m in self.get_value("trace_models")]
            if not models:
                _log.error("No trace models given: you need to assign a 2D model to the engraving "
                           "process.")
                return None
            progress = get_event_handler().get("progress")
            radius_compensation = self.get_value("radius_compensation")
            if radius_compensation:
                with ProgressContext("Offsetting models") as progress:
                    progress.set_multiple(len(models), "Model")
                    for index, model in enumerate(models):
                        models[index] = model.get_offset_model(tool_radius,
                                                               callback=progress.update)
                        progress.update_multiple()
            with ProgressContext("Calculating moves") as progress:
                line_distance = 1.8 * tool_radius
                step_width = tool_radius / 4.0
                pocketing_type = self.get_value("pocketing_type")
                motion_grid = MotionGrid.get_lines_grid(
                    models, box, self.get_value("step_down"), line_distance=line_distance,
                    step_width=step_width, milling_style=milling_style,
                    pocketing_type=pocketing_type, skip_first_layer=True, callback=progress.update)
            return motion_grid
        else:
            raise InvalidKeyError(strategy, ProcessStrategy)


class Boundary(BaseCollectionItemDataContainer):

    collection_name = "bounds"
    changed_event = "bounds-changed"
    list_changed_event = "bounds-list-changed"
    attribute_converters = {"specification": _get_enum_resolver(BoundsSpecification),
                            "reference_models": _get_collection_resolver("model", many=True),
                            "lower": _limit3d_converter,
                            "upper": _limit3d_converter,
                            "tool_boundary": _get_enum_resolver(ToolBoundaryMode)}
    attribute_defaults = {"tool_boundary": ToolBoundaryMode.ALONG,
                          "reference_models": []}

    @_set_parser_context("Boundary")
    def coerce_limits(self, models=None):
        abs_boundary = self.get_absolute_limits(models=models)
        if abs_boundary is None:
            # nothing to be changed
            return
        for axis_name, lower, upper in (("X", abs_boundary.minx, abs_boundary.maxx),
                                        ("Y", abs_boundary.miny, abs_boundary.maxy),
                                        ("Z", abs_boundary.minz, abs_boundary.maxz)):
            if upper < lower:
                # TODO: implement boundary adjustment in case of conflicts
                _log.warning("Negative Boundary encounterd for %s: %g < %g. "
                             "Coercing is not implemented, yet.", axis_name, lower, upper)

    @CacheStorage({"specification", "reference_models", "lower", "upper", "tool_boundary"})
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
                models = Model.get_collection()
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
                    high.append(model_upper + margin_upper.value * dim)
                else:
                    high.append(model_upper + margin_upper.value)
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
    changed_event = "task-changed"
    list_changed_event = "task-list-changed"
    attribute_converters = {"process": _get_collection_resolver("process"),
                            "bounds": _get_collection_resolver("bounds"),
                            "tool": _get_collection_resolver("tool"),
                            "type": _get_enum_resolver(TaskType),
                            "collision_models": _get_collection_resolver("model", many=True)}

    @CacheStorage({"process", "bounds", "tool", "type", "collision_models"})
    @_set_parser_context("Task")
    def generate_toolpath(self):
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
            with ProgressContext("Calculating toolpath") as progress:
                draw_callback = UpdateToolView(
                    progress.update,
                    max_fps=get_event_handler().get("tool_progress_max_fps", 1)).update
                moves = path_generator.GenerateToolPath(
                    tool.get_tool_geometry(), models, motion_grid, minz=box.lower.z,
                    maxz=box.upper.z, draw_callback=draw_callback)
            if not moves:
                _log.info("No valid moves found")
                return None
            return pycam.Toolpath.Toolpath(toolpath_path=moves, tool=tool,
                                           toolpath_filters=tool.get_toolpath_filters())
        else:
            raise InvalidKeyError(task_type, TaskType)


class ToolpathTransformation(BaseDataContainer):

    attribute_converters = {"action": _get_enum_resolver(ToolpathTransformationAction),
                            # TODO: we should add and implement 'allow_percent=True' here
                            "offset": _axes_values_converter,
                            "clone_count": int,
                            "lower": functools.partial(_axes_values_converter, allow_none=True),
                            "upper": functools.partial(_axes_values_converter, allow_none=True),
                            "shift_target": _get_enum_resolver(PositionShiftTarget),
                            "axes": functools.partial(_axes_values_converter, allow_none=True),
                            "models": _get_collection_resolver("model", many=True)}

    def get_transformed_toolpath(self, toolpath):
        action = self.get_value("action")
        if action == ToolpathTransformationAction.CROP:
            return self._get_cropped_toolpath(toolpath)
        elif action == ToolpathTransformationAction.CLONE:
            return self._get_cloned_toolpath(toolpath)
        elif action == ToolpathTransformationAction.SHIFT:
            return self._get_shifted_toolpath(toolpath)
        else:
            raise InvalidKeyError(action, ToolpathTransformationAction)

    @CacheStorage({"action", "offset", "clone_count"})
    @_set_parser_context("Toolpath transformation 'clone'")
    @_set_allowed_attributes({"action", "offset", "clone_count"})
    def _get_cloned_toolpath(self, toolpath):
        offset = self.get_value("offset")
        clone_count = self.get_value("clone_count")
        new_moves = list(toolpath.path)
        for index in range(1, (clone_count + 1)):
            shift_matrix = ((1, 0, 0, index * offset[0]),
                            (0, 1, 0, index * offset[1]),
                            (0, 0, 1, index * offset[2]))
            shifted = toolpath | tp_filters.TransformPosition(shift_matrix)
            new_moves.extend(shifted)
        new_toolpath = toolpath.copy()
        new_toolpath.path = new_moves
        return new_toolpath

    @CacheStorage({"action", "shift_target", "axes"})
    @_set_parser_context("Model transformation 'shift'")
    @_set_allowed_attributes({"action", "shift_target", "axes"})
    def _get_shifted_toolpath(self, toolpath):
        target = self.get_value("shift_target")
        axes = self.get_value("axes")
        offset = target._get_shift_offset(target, axes, toolpath)
        shift_matrix = ((1, 0, 0, offset[0]),
                        (0, 1, 0, offset[1]),
                        (0, 0, 1, offset[2]))
        new_toolpath = toolpath.copy()
        new_toolpath.path = toolpath | tp_filters.TransformPosition(shift_matrix)
        return new_toolpath

    @CacheStorage({"action", "models"})
    @_set_parser_context("Model transformation 'crop'")
    @_set_allowed_attributes({"action", "models"})
    def _get_cropped_toolpath(self, toolpath):
        polygons = []
        for model in [m.get_model() for m in self.get_value("models")]:
            if hasattr(model, "get_polygons"):
                polygons.extend(model.get_polygons())
            else:
                raise InvalidDataError("Toolpath Crop: 'models' may only contain 2D models")
        # Store the new toolpath first separately - otherwise we can't
        # revert the changes in case of an empty result.
        new_moves = toolpath | tp_filters.Crop(polygons)
        if new_moves | tp_filters.MovesOnly():
            new_toolpath = toolpath.copy()
            new_toolpath.path = new_moves
            return new_toolpath
        else:
            _log.info("Toolpath cropping: the result is empty")
            return None


class Toolpath(BaseCollectionItemDataContainer):

    collection_name = "toolpath"
    changed_event = "toolpath-changed"
    list_changed_event = "toolpath-list-changed"
    attribute_converters = {"source": Source,
                            "transformations": _get_list_resolver(ToolpathTransformation)}
    attribute_defaults = {"transformations": []}

    @CacheStorage({"source", "transformations"})
    @_set_parser_context("Toolpath")
    def get_toolpath(self):
        task = self.get_value("source").get("toolpath")
        toolpath = task.generate_toolpath()
        for transformation in self.get_value("transformations"):
            toolpath = transformation.get_transformed_toolpath(toolpath)
        return toolpath

    def append_transformation(self, transform_dict):
        current_transformations = self.get_value("transformations", raw=True)
        current_transformations.append(copy.deepcopy(transform_dict))
        # verify the result (bail out on error)
        self.attribute_converters["transformations"](current_transformations)
        # there was no problem - overwrite the previous transformations
        self.set_value("transformations", current_transformations)


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
                mode = _get_enum_value(pycam.Toolpath.ToolpathPathMode, parameters["mode"])
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
                          "export_settings": None,
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
        if export_settings:
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
