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


def parse_yaml(source, reset=False):
    """ read processing data from a file-like source and fill the object collections

    @param source: a file-like object (providing "read") referring to a yaml description
    @param reset: remove all previously stored objects (tools, processes, bounds, tasks, ...)
    """
    parsed = yaml.safe_load(source)
    if parsed is None:
        try:
            fname = source.name
        except AttributeError:
            fname = str(source)
        _log.warning("Ignoring empty parsed yaml source: %s", fname)
        return
    for section, item_class in DATA_MAP:
        collection = item_class.get_collection()
        if reset:
            collection.clear()
        count_before = len(collection)
        _log.debug("Importing items into '%s'", section)
        for name, data in parsed.get(section, {}).items():
            if item_class(name, data) is None:
                _log.error("Failed to import '%s' into '%s'.", name, section)
        _log.info("Imported %d items into '%s'", len(collection) - count_before, section)


def dump_yaml(target=None, sections=None):
    """export the current data structure as a yaml representation

    @param target: if a file-like object is given, then the output is written to this object.
        Otherwise the resulting yaml string is returned.
    @param sections: if specified, this parameter is interpreted as a list of names of sections
        (e.g. "tools") that should be exported.
    """
    if sections is None:
        wanted_section_map = DATA_MAP
    else:
        wanted_section_map = [(key, value) for key, value in DATA_MAP if key in sections]
    data = {section: item_class.get_collection().get_dict(with_application_attributes=True)
            for section, item_class in wanted_section_map}
    return yaml.dump(data, stream=target)
