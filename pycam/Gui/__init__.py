try:
    # Python3
    from configparser import ConfigParser
except ImportError:
    # Python2
    from ConfigParser import ConfigParser
import pickle
try:
    # Python2 (load first - due to incompatible interface)
    from StringIO import StringIO
except ImportError:
    # Python3
    from io import StringIO

import pycam.Gui.Settings
import pycam.Utils.log


PREFERENCES_DEFAULTS = {
    "unit": "mm",
    "default_task_settings_file": "",
    "show_model": True,
    "show_support_preview": True,
    "show_axes": True,
    "show_dimensions": True,
    "show_bounding_box": True,
    "show_toolpath": True,
    "show_tool": False,
    "show_directions": False,
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
    "tool_progress_max_fps": 30,
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

MAX_UNDO_STATES = 10
PICKLE_PROTOCOL = 2

log = pycam.Utils.log.get_logger()


class BaseUI(object):

    def __init__(self, event_manager):
        self.settings = event_manager
        self._undo_states = []
        self.settings.register_event("model-change-before", self.store_undo_state)

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
            value_raw = config.get("DEFAULT", item)
            value_type = type(PREFERENCES_DEFAULTS[item])
            if hasattr(value_type(), "split"):
                # keep strings as they are
                value = str(value_raw)
            else:
                # parse tuples, integers, bools, ...
                value = eval(value_raw)
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
            config.set("DEFAULT", item, self.settings.get(item))
        try:
            config_file = open(config_filename, "w")
            config.write(config_file)
            config_file.close()
        except IOError as err_msg:
            log.warn("Failed to write preferences file (%s): %s", config_filename, err_msg)

    def clear_undo_states(self):
        """ This function is called by the pycam script after everything is set up properly.  """
        # empty the "undo" states (accumulated by loading the default model)
        while self._undo_states:
            self._undo_states.pop(0)
        self.settings.emit_event("undo-states-changed")

    def store_undo_state(self):
        # for now we only store the model
        if not self.settings.get("models"):
            return
        # TODO: store all models
        self._undo_states.append(pickle.dumps(self.settings.get("models")[0].model,
                                              PICKLE_PROTOCOL))
        log.debug("Stored the current state of the model for undo")
        while len(self._undo_states) > MAX_UNDO_STATES:
            self._undo_states.pop(0)
        self.settings.emit_event("undo-states-changed")

    def restore_undo_state(self, widget=None, event=None):
        if len(self._undo_states) > 0:
            latest = StringIO(self._undo_states.pop(-1))
            model = pickle.Unpickler(latest).load()
            self.load_model(model)
            self.gui.get_object("UndoButton").set_sensitive(len(self._undo_states) > 0)
            log.info("Restored the previous state of the model")
            self.settings.emit_event("model-change-after")
        else:
            log.info("No previous undo state available - request ignored")
