import ConfigParser
import StringIO
import sys
import os

CONFIG_DIR = "pycam"

def get_config_dirname():
    try:
        from win32com.shell import shellcon, shell            
        homedir = shell.SHGetFolderPath(0, shellcon.CSIDL_APPDATA, 0, 0)
        config_dir = os.path.join(homedir, CONFIG_DIR)
    except ImportError: # quick semi-nasty fallback for non-windows/win32com case
        homedir = os.path.expanduser("~")
        # hide the config directory for unixes
        config_dir = os.path.join(homedir, "." + CONFIG_DIR)
    if not os.path.isdir(config_dir):
        try:
            os.makedirs(config_dir)
        except OSError:
            config_dir = None
    return config_dir

def get_config_filename(filename=None):
    if filename is None:
        filename = "preferences.conf"
    config_dir = get_config_dirname()
    if config_dir is None:
        return None
    else:
        return os.path.join(config_dir, filename)


class Settings:

    GET_INDEX = 0
    SET_INDEX = 1
    VALUE_INDEX = 2
    
    def __init__(self):
        self.items = {}
        self.values = {}

    def add_item(self, key, get_func=None, set_func=None):
        self.items[key] = [None, None, None]
        self.define_get_func(key, get_func)
        self.define_set_func(key, set_func)
        self.items[key][self.VALUE_INDEX] = None

    def define_get_func(self, key, get_func=None):
        if not self.items.has_key(key):
            return
        if get_func is None:
            get_func = lambda: self.items[key][self.VALUE_INDEX]
        self.items[key][self.GET_INDEX] = get_func

    def define_set_func(self, key, set_func=None):
        if not self.items.has_key(key):
            return
        def default_set_func(value):
            self.items[key][self.VALUE_INDEX] = value
        if set_func is None:
            set_func = default_set_func
        self.items[key][self.SET_INDEX] = set_func

    def get(self, key, default=None):
        if self.items.has_key(key):
            return self.items[key][self.GET_INDEX]()
        else:
            return default

    def set(self, key, value):
        if not self.items.has_key(key):
            self.add_item(key)
        self.items[key][self.SET_INDEX](value)
        self.items[key][self.VALUE_INDEX] = value

    def has_key(self, key):
        """ expose the "has_key" function of the items list """
        return self.items.has_key(key)

    def __str__(self):
        result = {}
        for key in self.items.keys():
            result[key] = self.get(key)
        return str(result)


class ProcessSettings:

    DEFAULT_CONFIG = """
[ToolDefault]
torus_radius: 0.25
feedrate: 1000
speed: 200

[Tool0]
name: Cylindrical (r=3)
shape: CylindricalCutter
tool_radius: 3

[Tool1]
name: Spherical (r=0.5)
shape: SphericalCutter
tool_radius: 0.5

[Tool2]
name: Toroidal (r=2)
shape: ToroidalCutter
tool_radius: 2
torus_radius: 0.2

[ProcessDefault]
path_direction: x
safety_height: 5

[Process0]
name: Rough
path_generator: PushCutter
path_postprocessor: PolygonCutter
material_allowance: 0.5
step_down: 0.8
overlap_percent: 0

[Process1]
name: Semi-finish
path_generator: PushCutter
path_postprocessor: ContourCutter
material_allowance: 0.2
step_down: 0.5
overlap_percent: 20

[Process2]
name: Finish
path_generator: DropCutter
path_postprocessor: ZigZagCutter
material_allowance: 0.0
step_down: 1.0
overlap_percent: 60

[TaskDefault]
enabled: 1

[Task0]
tool: 0
process: 0

[Task1]
tool: 2
process: 1

[Task2]
tool: 1
process: 2
"""

    SETTING_TYPES = {
            "name": str,
            "shape": str,
            "tool_radius": float,
            "torus_radius": float,
            "speed": float,
            "feedrate": float,
            "path_direction": str,
            "path_generator": str,
            "path_postprocessor": str,
            "safety_height": float,
            "material_allowance": float,
            "overlap_percent": int,
            "step_down": float,
            "tool": object,
            "process": object,
            "enabled": bool,
            "minx": float,
            "miny": float,
            "minz": float,
            "maxx": float,
            "maxy": float,
            "maxz": float,
    }

    CATEGORY_KEYS = {
            "tool": ("name", "shape", "tool_radius", "torus_radius", "feedrate", "speed"),
            "process": ("name", "path_generator", "path_postprocessor", "path_direction",
                    "safety_height", "material_allowance", "overlap_percent", "step_down"),
            "task": ("tool", "process", "enabled"),
    }

    SECTION_PREFIXES = {
        "tool": "Tool",
        "process": "Process",
        "task": "Task",
    }

    DEFAULT_SUFFIX = "Default"

    def __init__(self):
        self.config = None
        self._cache = {}
        self.reset()

    def reset(self, config_text=None):
        self._cache = {}
        self.config = ConfigParser.SafeConfigParser()
        if config_text is None:
            config_text = StringIO.StringIO(self.DEFAULT_CONFIG)
        else:
            config_text = StringIO.StringIO(config_text)
        self.config.readfp(config_text)

    def load_file(self, filename):
        try:
            self.config.read([filename])
        except ConfigParser.ParsingError, err_msg:
            print >> sys.stderr, "Failed to parse config file '%s': %s" % (filename, err_msg)
            return False
        return True

    def load_from_string(self, config_text):
        input_text = StringIO.StringIO(config_text)
        try:
            self.reset(input_text)
        except ConfigParser.ParsingError, err_msg:
            print >> sys.stderr, "Failed to parse config data: %s" % str(err_msg)
            return False
        return True

    def write_to_file(self, filename, tools=None, processes=None, tasks=None):
        text = self.get_config_text(tools, processes, tasks)
        try:
            fi = open(filename, "w")
            fi.write(text)
            fi.close()
        except IOError, err_msg:
            print >> sys.stderr, "Failed to write configuration to file (%s): %s" % (filename, err_msg)
            return False
        return True

    def get_tools(self):
        return self._get_category_items("tool")

    def get_processes(self):
        return self._get_category_items("process")

    def get_tasks(self):
        return self._get_category_items("task")

    def _get_category_items(self, type_name):
        if not self._cache.has_key(type_name):
            item_list = []
            index = 0
            prefix = self.SECTION_PREFIXES[type_name]
            current_section_name = "%s%d" % (prefix, index)
            while current_section_name in self.config.sections():
                item = {}
                for key in self.CATEGORY_KEYS[type_name]:
                    value_type = self.SETTING_TYPES[key]
                    try:
                        value_raw = self.config.get(current_section_name, key)
                    except ConfigParser.NoOptionError:
                        try:
                            value_raw = self.config.get(prefix + self.DEFAULT_SUFFIX, key)
                        except ConfigParser.NoOptionError:
                            value_raw = None
                    if not value_raw is None:
                        try:
                            if value_type == object:
                                # try to get the referenced object
                                value = self._get_category_items(key)[int(value_raw)]
                            else:
                                # just do a simple type cast
                                value = value_type(value_raw)
                        except (ValueError, IndexError):
                            value = None
                        if not value is None:
                            item[key] = value
                item_list.append(item)
                index += 1
                current_section_name = "%s%d" % (prefix, index)
            self._cache[type_name] = item_list
        return self._cache[type_name][:]

    def _value_to_string(self, lists, key, value):
        value_type = self.SETTING_TYPES[key]
        if value_type == bool:
            if value:
                return "1"
            else:
                return "0"
        elif value_type == object:
            try:
                return lists[key].index(value)
            except IndexError:
                return None
        else:
            return str(value_type(value))

    def get_config_text(self, tools=None, processes=None, tasks=None):
        result = []
        if tools is None:
            tools = []
        if processes is None:
            processes = []
        if tasks is None:
            tasks = []
        lists = {}
        lists["tool"] = tools
        lists["process"] = processes
        lists["task"] = tasks
        for type_name in lists.keys():
            type_list = lists[type_name]
            # generate "Default" section
            common_keys = []
            for key in self.CATEGORY_KEYS[type_name]:
                try:
                    values = [item[key] for item in type_list]
                except KeyError, err_msg:
                    values = None
                # check if there are values and if they all have the same value
                if values and (values.count(values[0]) == len(values)):
                    common_keys.append(key)
            if common_keys:
                section = "[%s%s]" % (self.SECTION_PREFIXES[type_name], self.DEFAULT_SUFFIX)
                result.append(section)
                for key in common_keys:
                    value = type_list[0][key]
                    value_string = self._value_to_string(lists, key, value)
                    if not value_string is None:
                        result.append("%s: %s" % (key, value_string))
                # add an empty line to separate sections
                result.append("")
            # generate individual sections
            for index in range(len(type_list)):
                section = "[%s%d]" % (self.SECTION_PREFIXES[type_name], index)
                result.append(section)
                item = type_list[index]
                for key in self.CATEGORY_KEYS[type_name]:
                    if key in common_keys:
                        # skip keys, that are listed in the "Default" section
                        continue
                    if item.has_key(key):
                        value = item[key]
                        value_string = self._value_to_string(lists, key, value)
                        if not value_string is None:
                            result.append("%s: %s" % (key, value_string))
                # add an empty line to separate sections
                result.append("")
        return os.linesep.join(result)

