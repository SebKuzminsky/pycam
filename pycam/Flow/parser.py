import yaml

import pycam.Exporters.GCode.LinuxCNC
import pycam.Flow.data_models
import pycam.Importers
import pycam.Plugins
from pycam.Utils.events import EventCore
import pycam.Utils.log


_log = pycam.Utils.log.get_logger()


def parse_yaml(source):
    parsed = yaml.safe_load(source)
    exports = []
    for collection, parser_func in (("tools", pycam.Flow.data_models.Tool),
                                    ("processes", pycam.Flow.data_models.Process),
                                    ("bounds", pycam.Flow.data_models.Boundary),
                                    ("tasks", pycam.Flow.data_models.Task),
                                    ("models", pycam.Flow.data_models.Model),
                                    ("toolpaths", pycam.Flow.data_models.Toolpath),
                                    ("exports", pycam.Flow.data_models.Export)):
        for name, spec in parsed.get(collection, {}).items():
            data = dict(spec)
            data["name"] = name
            obj = parser_func(data)
            if obj is None:
                _log.error("Failed to import '%s' into '%s'.", name, collection)
            elif collection == "exports":
                exports.append(obj)
    for export in exports:
        export.run_export()


if __name__ == "__main__":
    import sys
    filename = sys.argv[1]
    with open(filename, "r") as config_file:
        parse_yaml(config_file)
