import yaml

import pycam.Exporters.GCode.LinuxCNC
import pycam.Flow.data_models
import pycam.Importers
import pycam.Plugins
from pycam.Utils.events import EventCore
import pycam.Utils.log


_log = pycam.Utils.log.get_logger()


def parse_yaml(event_manager, source):
    import pycam.Toolpath.MotionGrid
    from pycam.Plugins.Bounds import BoundsEntity
    milling_style_map = {"ignore": pycam.Toolpath.MotionGrid.MillingStyle.IGNORE,
                         "conventional": pycam.Toolpath.MotionGrid.MillingStyle.CONVENTIONAL,
                         "climb": pycam.Toolpath.MotionGrid.MillingStyle.CLIMB}
    parsed = yaml.safe_load(source)
    for collection, parser_func in (("tools", pycam.Flow.data_models.Tool),
                                    ("processes", pycam.Flow.data_models.Process),
                                    ("bounds", BoundsEntity),
                                    ("tasks", pycam.Flow.data_models.Task),
                                    ("models", import_model_by_attributes),
                                    ("toolpaths", generate_toolpath_by_specification)):
        for name, spec in parsed.get(collection, {}).items():
            if collection in ("tools", "processes"):
                data = dict(spec)
                data["name"] = name
                obj = parser_func(data)
            elif collection == "bounds":
                obj = parser_func(event_manager, name, **spec)
                obj["parameters"]["BoundaryLowX"] = obj["lower"]["x"]
                obj["parameters"]["BoundaryLowY"] = obj["lower"]["y"]
                obj["parameters"]["BoundaryLowZ"] = obj["lower"]["z"]
                obj["parameters"]["BoundaryHighX"] = obj["upper"]["x"]
                obj["parameters"]["BoundaryHighY"] = obj["upper"]["y"]
                obj["parameters"]["BoundaryHighZ"] = obj["upper"]["z"]
                if obj["specification"] == "absolute":
                    obj["parameters"]["TypeCustom"] = True
                    obj["parameters"]["TypeRelativeMargin"] = False
                else:
                    obj["parameters"]["TypeCustom"] = False
                    obj["parameters"]["TypeRelativeMargin"] = True
            elif collection == "toolpaths":
                obj = parser_func(event_manager, spec)
            else:
                spec["name"] = name
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
                _log.error("Failed to import '%s' into '%s'.", name, collection)
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
            task = get_component("tasks", task_name)
            task.set_value("tool", get_component("tools", task.get_value("tool")))
            task.set_value("process", get_component("processes", task.get_value("process")))
            task.set_value("bounds", get_component("bounds", task.get_value("bounds")))
            collision_models = []
            bounds_models = []
            for model_source, model_destination in (
                    (task.get_value("collision_models"), collision_models),
                    (task.get_value("bounds")["models"], bounds_models)):
                for model_name in model_source:
                    model = get_component("models", model_name)
                    if model:
                        model_destination.append(model)
                    else:
                        _log.error("Failed to retrieve model: %s", model_name)
            task.set_value("collision_models", collision_models)
            # task["bounds"]["Models"] = bounds_models
            return task.generate_toolpath()
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
    import sys
    filename = sys.argv[1]
    event_manager = get_environment()
    with open(filename, "r") as config_file:
        parse_yaml(event_manager, config_file)
