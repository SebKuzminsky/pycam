from __future__ import print_function

import yaml

import pycam.Exporters.GCode.LinuxCNC
import pycam.Flow.data_models
import pycam.Importers
import pycam.Plugins
import pycam.Utils.log


_log = pycam.Utils.log.get_logger()


DATA_MAP = (("tools", pycam.Flow.data_models.Tool),
            ("processes", pycam.Flow.data_models.Process),
            ("bounds", pycam.Flow.data_models.Boundary),
            ("tasks", pycam.Flow.data_models.Task),
            ("models", pycam.Flow.data_models.Model),
            ("toolpaths", pycam.Flow.data_models.Toolpath),
            ("export_settings", pycam.Flow.data_models.ExportSettings),
            ("exports", pycam.Flow.data_models.Export))


def parse_yaml(source):
    """ read processing data from a file-like source """
    parsed = yaml.safe_load(source)
    if parsed is None:
        try:
            fname = source.name
        except AttributeError:
            fname = str(source)
        _log.warning("Ignoring empty parsed yaml source: %s", fname)
        return
    for section, item_class in DATA_MAP:
        for name, data in parsed.get(section, {}).items():
            _log.warning("Importing items into '%s'", section)
            if item_class(name, data) is None:
                _log.error("Failed to import '%s' into '%s'.", name, section)
        _log.info("Imported %d items into '%s'", len(item_class.get_collection()), section)
