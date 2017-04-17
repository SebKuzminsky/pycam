import yaml

import pycam.Exporters.GCode.LinuxCNC
import pycam.Flow.data_models
import pycam.Importers
import pycam.Plugins
from pycam.Utils.events import EventCore
import pycam.Utils.log


_log = pycam.Utils.log.get_logger()


def parse_yaml(event_manager, source):
    parsed = yaml.safe_load(source)
    for collection, parser_func in (("tools", pycam.Flow.data_models.Tool),
                                    ("processes", pycam.Flow.data_models.Process),
                                    ("bounds", pycam.Flow.data_models.Boundary),
                                    ("tasks", pycam.Flow.data_models.Task),
                                    ("models", pycam.Flow.data_models.Model),
                                    ("toolpaths", pycam.Flow.data_models.Toolpath)):
        for name, spec in parsed.get(collection, {}).items():
            data = dict(spec)
            data["name"] = name
            obj = parser_func(data)
            if obj is None:
                _log.error("Failed to import '%s' into '%s'.", name, collection)
    for export_params in parsed.get("exports", []):
        export_toolpath(event_manager, export_params)


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
            toolpath = pycam.Flow.data_models._get_from_collection("toolpath", toolpath_name)
            if toolpath:
                toolpaths.append(toolpath.generate_toolpath())
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
