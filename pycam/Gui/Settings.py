import ConfigParser
import StringIO
import sys
import os

GET_INDEX = 0
SET_INDEX = 1
VALUE_INDEX = 2

class Settings:
    
    def __init__(self):
        self.items = {}
        self.values = {}

    def add_item(self, key, get_func=None, set_func=None):
        self.items[key] = [None, None, None]
        self.define_get_func(key, get_func)
        self.define_set_func(key, set_func)
        self.items[key][VALUE_INDEX] = None

    def define_get_func(self, key, get_func=None):
        if not self.items.has_key(key):
            return
        if get_func is None:
            get_func = lambda: self.items[key][VALUE_INDEX]
        self.items[key][GET_INDEX] = get_func

    def define_set_func(self, key, set_func=None):
        if not self.items.has_key(key):
            return
        def default_set_func(value):
            self.items[key][VALUE_INDEX] = value
        if set_func is None:
            set_func = default_set_func
        self.items[key][SET_INDEX] = set_func

    def get(self, key, default=None):
        if self.items.has_key(key):
            return self.items[key][GET_INDEX]()
        else:
            return default

    def set(self, key, value):
        if not self.items.has_key(key):
            self.add_item(key)
        self.items[key][SET_INDEX](value)
        self.items[key][VALUE_INDEX] = value

    def __str__(self):
        result = {}
        for key in self.items.keys():
            result[key] = self.get(key)
        return str(result)


class ProcessingSettings:

    DEFAULT_CONFIG = """
[DEFAULT]
cutter_shape: SphericalCutter
path_direction: x
path_generator: DropCutter
path_postprocessor: PathAccumulator
# the dimensions of the bounding box are disabled to keep the previous values
#minx: -7
#miny: -7
#minz: 0
#maxx: 7
#maxy: 7
#maxz: 3
tool_radius: 1.0
torus_radius: 0.25

[Rough]
cutter_shape: CylindricalCutter
path_generator: PushCutter
path_postprocessor: PolygonCutter
tool_radius: 1.0


[Semi-finish]
cutter_shape: ToroidalCutter
path_generator: PushCutter
path_postprocessor: ContourCutter
tool_radius: 0.5

[Finish]
cutter_shape: SphericalCutter
path_generator: DropCutter
path_postprocessor: ZigZagCutter
tool_radius: 0.1
"""

    SETTING_TYPES = {
            "cutter_shape": str,
            "path_direction": str,
            "path_generator": str,
            "path_postprocessor": str,
            "minx": float,
            "miny": float,
            "minz": float,
            "maxx": float,
            "maxy": float,
            "maxz": float,
            "tool_radius": float,
            "torus_radius": float,
    }

    def __init__(self, settings):
        self.settings = settings
        self.config = None
        self.reset()

    def reset(self):
        self.config = ConfigParser.SafeConfigParser()
        self.config.readfp(StringIO.StringIO(self.DEFAULT_CONFIG))

    def load_file(self, filename):
        try:
            self.config.read([filename])
        except ConfigParser.ParsingError, err_msg:
            print sys.stderr, "Failed to parse config file '%s': %s" % (filename, err_msg)
            return False
        return True

    def load_from_string(self, config_text):
        input_text = StringIO.StringIO(config_text)
        try:
            self.config.readfp(input_text)
        except ConfigParser.ParsingError, err_msg:
            print sys.stderr, "Failed to parse config data: %s" % str(err_msg)
            return False
        return True

    def write_to_file(self, filename):
        try:
            fi = open(filename, "w")
            self.config.write(fi)
            fi.close()
        except IOError, err_msg:
            print sys.stderr, "Failed to write configuration to file (%s): %s" % (filename, err_msg)
            return False
        return True

    def enable_config(self, section="DEFAULT"):
        for key, value_type in self.SETTING_TYPES.items():
            try:
                value = value_type(self.config.get(section, key))
            except ConfigParser.NoOptionError:
                # we can safely ignore it and keep the original
                try:
                    value = value_type(self.config.get("DEFAULT", key))
                except ConfigParser.NoOptionError:
                    value = None
            except ValueError, err_msg:
                print sys.stderr, "Invalid config value for '%s = %s': %s" % (key, self.config.get(section, key), err_msg)
                value = None
            if not value is None:
                self.settings.set(key, value)

    def get_config_list(self):
        return self.config.sections()

    def store_config(self, section="DEFAULT"):
        if not self.config.has_section(section):
            self.config.add_section(section)
        for key, value_type in self.SETTING_TYPES.items():
            self.config.set(section, key, str(self.settings.get(key)))

    def delete_config(self, section=None):
        if self.config.has_section(section):
            self.config.remove_section(section)

