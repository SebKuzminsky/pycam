from configparser import ConfigParser
import enum
import json

import pycam.Gui.Settings
import pycam.Utils.log


class QuestionStatus(enum.Enum):
    YES = "yes"
    NO = "no"
    ASK = "ask"


PREFERENCES_DEFAULTS = {
    "unit": "mm",
    "default_task_settings_file": "",
    "save_project_settings_on_exit": QuestionStatus.ASK.value,
    "show_model": True,
    "show_support_preview": True,
    "show_axes": True,
    "show_dimensions": True,
    "show_bounding_box": True,
    "show_toolpath": True,
    "show_tool": False,
    "show_directions": False,
    "show_grid": False,
    "color_background": {"red": 0.0, "green": 0.0, "blue": 0.0, "alpha": 1.0},
    "color_model": {"red": 0.5, "green": 0.5, "blue": 1.0, "alpha": 1.0},
    "color_support_preview": {"red": 0.8, "green": 0.8, "blue": 0.3, "alpha": 1.0},
    "color_bounding_box": {"red": 0.3, "green": 0.3, "blue": 0.3, "alpha": 1.0},
    "color_tool": {"red": 1.0, "green": 0.2, "blue": 0.2, "alpha": 1.0},
    "color_toolpath_cut": {"red": 1.0, "green": 0.5, "blue": 0.5, "alpha": 1.0},
    "color_toolpath_return": {"red": 0.9, "green": 1.0, "blue": 0.1, "alpha": 0.4},
    "color_material": {"red": 1.0, "green": 0.5, "blue": 0.0, "alpha": 1.0},
    "color_grid": {"red": 0.75, "green": 1.0, "blue": 0.7, "alpha": 0.55},
    "view_light": True,
    "view_shadow": True,
    "view_polygon": True,
    "view_perspective": True,
    "tool_progress_max_fps": 30.0,
    "gcode_safety_height": 25.0,
    "gcode_plunge_feedrate": 100.0,
    "gcode_minimum_step_x": 0.0001,
    "gcode_minimum_step_y": 0.0001,
    "gcode_minimum_step_z": 0.0001,
    "gcode_path_mode": 0,
    "gcode_motion_tolerance": 0,
    "gcode_naive_tolerance": 0,
    "gcode_start_stop_spindle": True,
    "gcode_filename_extension": "",
    "gcode_spindle_delay": 3,
    "external_program_inkscape": "",
    "external_program_pstoedit": "",
    "touch_off_on_startup": False,
    "touch_off_on_tool_change": False,
    "touch_off_position_type": "absolute",
    "touch_off_position_x": 0.0,
    "touch_off_position_y": 0.0,
    "touch_off_position_z": 0.0,
    "touch_off_rapid_move": 0.0,
    "touch_off_slow_move": 1.0,
    "touch_off_slow_feedrate": 20,
    "touch_off_height": 0.0,
    "touch_off_pause_execution": False,
}
""" the listed items will be loaded/saved via the preferences file in the
user's home directory on startup/shutdown"""

DEFAULT_PROJECT_SETTINGS = """
models:
        model:
            source:
                    type: file
                    location: samples/Box0.stl
            X-Application:
                pycam-gtk:
                    name: Example 3D Model
                    color: { red: 0.1, green: 0.4, blue: 1.0, alpha: 0.8 }

tools:
        rough:
            tool_id: 1
            shape: flat_bottom
            radius: 3
            feed: 600
            spindle_speed: 1000
            X-Application: { pycam-gtk: { name: Big Tool } }
        fine:
            tool_id: 2
            shape: ball_nose
            radius: 1
            feed: 1200
            spindle_speed: 1000
            X-Application: { pycam-gtk: { name: Small Tool } }

processes:
        process_slicing:
            strategy: slice
            path_pattern: grid
            overlap: 0.10
            step_down: 3.0
            grid_direction: y
            milling_style: ignore
            X-Application: { pycam-gtk: { name: Slice (rough) } }
        process_surfacing:
            strategy: surface
            overlap: 0.80
            step_down: 1.0
            grid_direction: x
            milling_style: ignore
            X-Application: { pycam-gtk: { name: Surface (fine) } }

bounds:
        minimal:
            specification: margins
            lower: [5, 5, 0]
            upper: [5, 5, 1]
            X-Application: { pycam-gtk: { name: minimal } }

tasks:
        rough:
            type: milling
            tool: rough
            process: process_slicing
            bounds: minimal
            collision_models: [ model ]
            X-Application: { pycam-gtk: { name: Quick Removal } }
        fine:
            type: milling
            tool: fine
            process: process_surfacing
            bounds: minimal
            collision_models: [ model ]
            X-Application: { pycam-gtk: { name: Finishing } }
"""

PICKLE_PROTOCOL = 2

log = pycam.Utils.log.get_logger()


class BaseUI(object):

    def __init__(self, event_manager):
        self.settings = event_manager

    def reset_preferences(self, widget=None):
        """ reset all preferences to their default values """
        for key, value in PREFERENCES_DEFAULTS.items():
            self.settings.set(key, value)
        # redraw the model due to changed colors, display items ...
        self.settings.emit_event("model-change-after")

    def load_preferences(self):
        """ load all settings that are available in the Preferences window from
        a file in the user's home directory """
        config_filename = pycam.Gui.Settings.get_config_filename()
        if config_filename is None:
            # failed to create the personal preferences directory
            return
        config = ConfigParser()
        if not config.read(config_filename):
            # no config file was read
            return
        # report any ignored (obsolete) preference keys present in the file
        for item, value in config.items("DEFAULT"):
            if item not in PREFERENCES_DEFAULTS.keys():
                log.warn("Skipping obsolete preference item: %s", str(item))
        for item in PREFERENCES_DEFAULTS:
            if not config.has_option("DEFAULT", item):
                # a new preference setting is missing in the (old) file
                continue
            value_json = config.get("DEFAULT", item)
            try:
                value = json.loads(value_json)
            except ValueError as exc:
                log.warning("Failed to parse configuration setting '%s': %s", item, exc)
                value = PREFERENCES_DEFAULTS[item]
            wanted_type = type(PREFERENCES_DEFAULTS[item])
            if wanted_type is float:
                # int is accepted for floats, too
                wanted_type = (float, int)
            if not isinstance(value, wanted_type):
                log.warning("Falling back to default configuration setting for '%s' due to "
                            "an invalid value type being parsed: %s != %s",
                            item, type(value), wanted_type)
                value = PREFERENCES_DEFAULTS[item]
            self.settings.set(item, value)

    def save_preferences(self):
        """ save all settings that are available in the Preferences window to
        a file in the user's home directory """
        config_filename = pycam.Gui.Settings.get_config_filename()
        if config_filename is None:
            # failed to create the personal preferences directory
            log.warn("Failed to create a preferences directory in your user's home directory.")
            return
        config = ConfigParser()
        for item in PREFERENCES_DEFAULTS:
            config.set("DEFAULT", item, json.dumps(self.settings.get(item)))
        try:
            config_file = open(config_filename, "w")
            config.write(config_file)
            config_file.close()
        except IOError as err_msg:
            log.warn("Failed to write preferences file (%s): %s", config_filename, err_msg)

    def restore_undo_state(self, widget=None, event=None):
        history = self.settings.get("history")
        if history and history.get_undo_steps_count() > 0:
            history.restore_previous_state()
        else:
            log.info("No previous undo state available - request ignored")

    def load_project_settings(self):
        from pycam.Flow.parser import parse_yaml
        try:
            with pycam.Gui.Settings.open_project_settings() as in_file:
                content = in_file.read()
        except FileNotFoundError:
            content = DEFAULT_PROJECT_SETTINGS
        except OSError as exc:
            log.error("Failed to read project settings: %s", exc)
            return
        parse_yaml(content, reset=True)

    def save_project_settings(self):
        from pycam.Flow.parser import dump_yaml
        try:
            with pycam.Gui.Settings.open_project_settings(mode="w") as out_file:
                dump_yaml(target=out_file,
                          sections={"models", "tools", "processes", "bounds", "tasks"})
        except OSError as exc:
            log.error("Failed to store project settings: %s", exc)
