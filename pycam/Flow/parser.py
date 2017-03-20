import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))

import yaml

import pycam.Exporters.GCode.LinuxCNC
import pycam.Importers
import pycam.Plugins
from pycam.Utils.events import EventCore
import pycam.Utils.log


_log = pycam.Utils.log.get_logger()


def parse_yaml(event_manager, source):
    import pycam.Toolpath.MotionGrid
    from pycam.Plugins.Bounds import BoundsEntity
    from pycam.Plugins.Processes import ProcessEntity
    from pycam.Plugins.Tasks import TaskEntity
    from pycam.Plugins.Tools import ToolEntity
    milling_style_map = {"ignore": pycam.Toolpath.MotionGrid.MillingStyle.IGNORE,
                         "conventional": pycam.Toolpath.MotionGrid.MillingStyle.CONVENTIONAL,
                         "climb": pycam.Toolpath.MotionGrid.MillingStyle.CLIMB}
    parsed = yaml.safe_load(source)
    for collection, parser_func in (("tools", ToolEntity),
                                    ("processes", ProcessEntity),
                                    ("bounds", BoundsEntity),
                                    ("tasks", TaskEntity),
                                    ("models", import_model_by_attributes),
                                    ("toolpaths", generate_toolpath_by_specification)):
        for name, spec in parsed.get(collection, {}).items():
            if collection == "bounds":
                obj = parser_func(event_manager, name, **spec)
            elif collection == "toolpaths":
                obj = parser_func(event_manager, spec)
            else:
                spec["name"] = name
                if collection == "tools":
                    spec["radius"] = spec["diameter"] / 2
                if collection == "processes":
                    spec["path_pattern"] = {"name": spec["path_pattern"]}
                    parameters = dict(spec)
                    parameters["milling_style"] = milling_style_map[parameters["milling_style"]]
                    del parameters["name"]
                    # TODO: where does this value come from?
                    del parameters["step_down"]
                    # TODO: where does this value come from?
                    del parameters["overlap"]
                    del parameters["path_pattern"]
                    del parameters["strategy"]
                    spec["path_pattern"]["parameters"] = parameters
                obj = parser_func(spec)
                if isinstance(obj, dict):
                    obj["parameters"] = spec
            if obj:
                if collection == "models":
                    event_manager.get(collection).add_model(obj, name=name)
                elif collection == "toolpaths":
                    event_manager.get(collection).add_new(obj, name=name)
                else:
                    event_manager.get(collection).append(obj)
            else:
                _log.error("Failed to import model '%s'.", name)
    for export_params in parsed.get("exports", []):
        export_toolpath(event_manager, export_params)


def import_model_by_attributes(params):
    try:
        source = params["source"]
    except KeyError:
        _log.error("Failed to load model without 'source' attribute")
        return None
    try:
        source_type = source["type"]
    except KeyError:
        _log.error("Failed to load model without 'source.type' attribute")
        return None
    if source_type == "file":
        try:
            file_path = source["location"]
        except KeyError:
            _log.error("Failed to load model from file without 'source.location' attribute")
            return None
        file_type, importer = pycam.Importers.detect_file_type(file_path)
        if file_type and callable(importer):
            return importer(file_path)
        else:
            _log.error("Failed to detect filetype: %s", file_path)
            return None
    else:
        _log.error("Unsupported model 'source' given: %s", source)
        return None


def generate_toolpath_by_specification(event_manager, params):
    def get_component(collection, name, event_manager=event_manager):
        return event_manager.get(collection).get_by_attribute("name", name)

    try:
        source = params["source"]
    except KeyError:
        _log.error("Missing 'source' attribute of toolpath")
        return None
    try:
        source_type = source["type"]
    except KeyError:
        _log.error("Missing 'type' attribute within source of toolpath")
        return None
    if source_type == "task":
        try:
            task_names = source["tasks"]
        except KeyError:
            _log.error("Missing 'tasks' attribute for task-based toolpath")
            return None
        for task_name in task_names:
            task_references = get_component("tasks", task_name)
            task = {}
            task["name"] = task_name
            task["parameters"] = {}
            task["parameters"]["bounds"] = get_component("bounds", task_references["bounds"])
            task["parameters"]["process"] = get_component("processes", task_references["process"])
            task["parameters"]["tool"] = get_component("tools", task_references["tool"])
            collision_models = []
            for model_name in task_references["collision_models"]:
                model = get_component("models", model_name)
                if model:
                    collision_models.append(model)
                else:
                    _log.error("Failed to retrieve model: %s", model_name)
            task["parameters"]["collision_models"] = collision_models
            task_resolver = event_manager.get("get_parameter_sets")(
                "task")[task_references["type"]]["func"]
            return task_resolver(task)
    else:
        _log.error("Unsupported 'source' type for toolpath: %s", source_type)
        return None


def export_toolpath(event_manager, params):
    try:
        source = params["source"]
    except KeyError:
        _log.error("Missing 'source' attribute of export")
        return None
    try:
        source_type = source["type"]
    except KeyError:
        _log.error("Missing 'type' attribute within source of export")
        return None
    try:
        target = params["target"]
    except KeyError:
        _log.error("Missing 'target' attribute of export")
        return None
    try:
        target_type = target["type"]
    except KeyError:
        _log.error("Missing 'type' attribute within target of export")
        return None
    if source_type == "toolpath":
        toolpaths = []
        try:
            toolpath_names = source["toolpaths"]
        except KeyError:
            _log.error("Missing 'toolpaths' attribute within source of export")
            return None
        for toolpath_name in toolpath_names:
            toolpath = event_manager.get("toolpaths").get_by_attribute("name", toolpath_name)
            if toolpath:
                toolpaths.append(toolpath)
            else:
                _log.error("Unknown toolpath '%s' selected for export", toolpath_name)
        if target_type == "file":
            try:
                target_location = target["location"]
            except KeyError:
                _log.error("Missing 'location' attribute within target of export")
                return None
            destination = open(target_location, "w")
            generator = pycam.Exporters.GCode.LinuxCNC.LinuxCNC(destination)
#           generator.add_filters(settings_filters)
#           generator.add_filters(common_filters)
            for toolpath in toolpaths:
                # TODO: implement toolpath.get_meta_data()
                generator.add_moves(toolpath.path, toolpath.filters)
            generator.finish()
            destination.close()
    else:
        _log.error("Unsupported 'source' type for export: %s", source_type)
        return None


def get_environment():
    event_manager = EventCore()
    plugin_manager = pycam.Plugins.PluginManager(core=event_manager)
    plugin_manager.import_plugins(ignore_names=["GtkConsole", "OpenGLWindow"])
    return event_manager


if __name__ == "__main__":
    import os
    example_filename = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir,
                                    "yaml_flow_example.yml")
    event_manager = get_environment()
    with open(example_filename, "r") as config_file:
        parse_yaml(event_manager, config_file)
