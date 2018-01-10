# -*- coding: utf-8 -*-
"""
Copyright 2011 Lars Kruse <devel@sumpfralle.de>

This file is part of PyCAM.

PyCAM is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

PyCAM is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with PyCAM.  If not, see <http://www.gnu.org/licenses/>.
"""

import imp
import inspect
import os
import uuid

try:
    import gtk
except ImportError:
    gtk = None
try:
    import gobject
except ImportError:
    gobject = None

import pycam.Utils.log
import pycam.Utils.locations


_log = pycam.Utils.log.get_logger()


class PluginBase(object):

    UI_FILE = None
    DEPENDS = []
    CATEGORIES = []
    ICONS = {}
    ICON_SIZE = 23

    def __init__(self, core, name):
        self.enabled = True
        self.name = name
        self.core = core
        self.gui = None
        self.log = _log
        self._gtk = gtk
        self._gobject = gobject
        if self.UI_FILE and self._gtk:
            gtk_build_file = pycam.Utils.locations.get_ui_file_location(self.UI_FILE)
            if gtk_build_file:
                self.gui = self._gtk.Builder()
                try:
                    self.gui.add_from_file(gtk_build_file)
                except RuntimeError as err_msg:
                    self.log.info("Failed to import UI file (%s): %s", gtk_build_file, err_msg)
                    self.gui = None
                else:
                    # All windows should share the same accel group (for
                    # keyboard shortcuts).
                    try:
                        common_accel_group = self.core["gtk-accel-group"]
                    except KeyError:
                        self.log.info("Failed to connect to a common GTK accelerator group")
                        common_accel_group = None
                    if common_accel_group:
                        for obj in self.gui.get_objects():
                            if isinstance(obj, self._gtk.Window):
                                obj.add_accel_group(common_accel_group)

        if self._gtk:
            for key in self.ICONS:
                icon_location = pycam.Utils.locations.get_ui_file_location(self.ICONS[key])
                if icon_location:
                    try:
                        pixbuf = self._gtk.gdk.pixbuf_new_from_file_at_size(
                            icon_location, self.ICON_SIZE, self.ICON_SIZE)
                    except self._gobject.GError:
                        self.ICONS[key] = None
                    else:
                        self.ICONS[key] = pixbuf
                else:
                    self.log.debug("Failed to locate icon: %s", self.ICONS[key])
                    self.ICONS[key] = None
        self._func_cache = {}
        self._gtk_handler_id_cache = []
        self.enabled = True
        self._state_items = []

    def register_state_item(self, path, get_func, set_func=None):
        group = (path, get_func, set_func)
        if group in self._state_items:
            self.log.debug("Trying to register a state item twice: %s", path)
        else:
            self._state_items.append(group)

    def clear_state_items(self):
        self._state_items = []

    def unregister_state_item(self, path, get_func, set_func=None):
        group = (path, get_func, set_func)
        if group in self._state_items:
            self._state_items.remove(group)
        else:
            self.log.debug("Trying to unregister an unknown state item: %s", path)

    def dump_state(self, result):
        for path, get_func, set_func in self._state_items:
            if callable(get_func):
                value = get_func()
            else:
                value = get_func
            result.append((path, value))

    def __get_handler_func(self, func, params=None):
        if params is None:
            params = []
        params = tuple(params)
        try:
            key = (hash(func), repr(params))
        except TypeError:
            key = (id(func), repr(params))
        if key not in self._func_cache:
            if callable(func):
                if not params:
                    result = func
                else:
                    result = lambda *args, **kwargs: func(*(args + params), **kwargs)
            else:
                # it is the name of a signal
                result = lambda *args: self.core.emit_event(func, *params)
            self._func_cache[key] = result
        return self._func_cache[key]

    def register_event_handlers(self, event_handlers):
        for data in event_handlers:
            name, func = data[:2]
            if len(data) > 2:
                params = data[2:]
            else:
                params = []
            self.core.register_event(name, self.__get_handler_func(func, params))

    def register_gtk_handlers(self, gtk_widget_handlers):
        for data in gtk_widget_handlers:
            obj, signal, func = data[:3]
            if len(data) > 3:
                params = data[3:]
            else:
                params = []
            handler_id = obj.connect(signal, self.__get_handler_func(func, params))
            self._gtk_handler_id_cache.append((obj, handler_id))

    def unregister_event_handlers(self, event_handlers):
        for data in event_handlers:
            name, func = data[:2]
            if len(data) > 2:
                params = data[2:]
            else:
                params = []
            self.core.unregister_event(name, self.__get_handler_func(func, params))

    def unregister_gtk_handlers(self, gtk_widget_handlers):
        while self._gtk_handler_id_cache:
            obj, handler_id = self._gtk_handler_id_cache.pop()
            obj.disconnect(handler_id)

    def setup(self):
        raise NotImplementedError("Module %s (%s) does not implement 'setup'"
                                  % (self.name, __file__))

    def teardown(self):
        raise NotImplementedError("Module %s (%s) does not implement 'teardown'"
                                  % (self.name, __file__))

    def register_gtk_accelerator(self, groupname, action, accel_string, accel_name):
        # menu item and shortcut
        if not self._gtk:
            return
        actiongroup = self._gtk.ActionGroup(groupname)
        accel_path = "<pycam>/%s" % accel_name
        action.set_accel_path(accel_path)
        # it is a bit pointless, but we allow an empty accel_string anyway ...
        if accel_string:
            key, mod = self._gtk.accelerator_parse(accel_string)
            self._gtk.accel_map_change_entry(accel_path, key, mod, True)
        actiongroup.add_action(action)
        ui_manager = self.core.get("gtk-uimanager")
        # it can happen that there is no gtk ui manager available (in script mode)
        if ui_manager:
            ui_manager.insert_action_group(actiongroup, pos=-1)

    def unregister_gtk_accelerator(self, groupname, action):
        actiongroup = self._gtk.ActionGroup(groupname)
        actiongroup.remove_action(action)
        ui_manager = self.core.get("gtk-uimanager")
        if ui_manager and (len(actiongroup.list_actions()) == 0) \
                and (actiongroup in ui_manager.get_action_groups()):
            ui_manager.remove_action_group(actiongroup)


class PluginManager(object):

    def __init__(self, core):
        self.core = core
        self.modules = {}
        self.core.set("plugin-manager", self)

    def import_plugins(self, directory=None, ignore_names=None):
        if ignore_names is None:
            ignore_names = []
        if directory is None:
            directory = os.path.dirname(__file__)
        try:
            files = os.listdir(directory)
        except OSError:
            return
        plugins = []
        for filename in files:
            if (filename.endswith(".py")
                    and (filename.lower() != "__init__.py")
                    and os.path.isfile(os.path.join(directory, filename))):
                mod_name = filename[0:-(len(".py"))]
                if mod_name in ignore_names:
                    _log.info("Skipping plugin %s (marked as 'ignore')", mod_name)
                    continue
                try:
                    mod_file, mod_filename, mod_desc = imp.find_module(mod_name, [directory])
                    full_mod_name = "pycam.Plugins.%s" % mod_name
                    mod = imp.load_module(full_mod_name, mod_file, mod_filename, mod_desc)
                except ImportError as exc:
                    _log.info("Skipping plugin %s: %s", os.path.join(directory, filename), exc)
                    continue
                for attr in dir(mod):
                    item = getattr(mod, attr)
                    if inspect.isclass(item) and hasattr(item, "setup"):
                        plugins.append((item, mod_filename, attr))
        try_again = True
        while try_again:
            try_again = False
            postponed_plugins = []
            for plugin, filename, name in plugins:
                for dep in plugin.DEPENDS:
                    if (dep not in self.modules) and (("%s.%s" % (dep, dep)) not in self.modules):
                        # dependency not loaded, yet
                        postponed_plugins.append((plugin, filename, name))
                        break
                else:
                    self._load_plugin(plugin, filename, name)
                    try_again = True
            plugins = postponed_plugins
        for plugin, filename, name in plugins:
            # module failed to load due to missing dependencies
            missing = []
            for depend in plugin.DEPENDS:
                try:
                    # check if this dependency is available
                    self.get_plugin(depend)
                except KeyError:
                    missing.append(depend)
            _log.info("Skipping plugin '%s' due to missing dependencies: %s",
                      name, ", ".join(missing))

    def _load_plugin(self, obj, filename, plugin_name):
        if plugin_name in self.modules:
            _log.debug("Cleaning up module %s", plugin_name)
            self.modules[plugin_name].teardown()
        _log.debug("Initializing module %s (%s)", plugin_name, filename)
        new_plugin = obj(self.core, plugin_name)
        try:
            if not new_plugin.setup():
                _log.info("Failed to setup plugin '%s'", str(plugin_name))
            else:
                self.modules[plugin_name] = new_plugin
                self.core.emit_event("plugin-list-changed")
        except NotImplementedError as err_msg:
            _log.info("Skipping incomplete plugin '%s': %s", plugin_name, err_msg)

    def get_plugin(self, name):
        long_name = "%s.%s" % (name, name)
        if name in self.modules:
            return self.modules[name]
        elif long_name in self.modules:
            return self.modules[long_name]
        else:
            raise KeyError("Plugin '%s' is not available" % name)

    def enable_plugin(self, name):
        plugin = self.get_plugin(name)
        if plugin.enabled:
            _log.debug("Refused to enable an active plugin: %s" % name)
            return
        else:
            plugin.enabled = plugin.setup()

    def disable_plugin(self, name):
        plugin = self.get_plugin(name)
        if not plugin.enabled:
            _log.debug("Refused to disable an active plugin: %s" % name)
            return
        else:
            plugin.teardown()
            plugin.enabled = False

    def get_plugin_state(self, name):
        plugin = self.get_plugin(name)
        return plugin.enabled

    def get_plugins(self):
        return list(self.modules.values())

    def get_plugin_names(self):
        names = self.modules.keys()
        names.sort()
        return names

    def is_plugin_required(self, name):
        long_name = "%s.%s." % (name, name)
        for plugin in self.modules.values():
            if not plugin.enabled:
                continue
            if (name in plugin.DEPENDS) or (long_name in plugin.DEPENDS):
                break
        else:
            return False
        return True

    def get_plugin_missing_dependencies(self, name):
        plugin = self.get_plugin(name)
        missing = []
        for depend in plugin.DEPENDS:
            long_depend = "%s.%s" % (depend, depend)
            if (depend in self.modules) and self.modules[depend].enabled:
                continue
            elif (long_depend in self.modules) and (self.modules[long_depend].enabled):
                continue
            else:
                missing.append(depend)
        return missing


class ListPluginBase(PluginBase, list):

    ACTION_UP, ACTION_DOWN, ACTION_DELETE, ACTION_CLEAR = range(4)

    def __init__(self, *args, **kwargs):
        super(ListPluginBase, self).__init__(*args, **kwargs)
        self._update_model_funcs = []
        self._gtk_modelview = None

        def get_function(func_name):
            return lambda *args, **kwargs: self._change_wrapper(func_name, *args, **kwargs)

        for name in ("append", "extend", "insert", "pop", "reverse", "remove", "sort"):
            setattr(self, name, get_function(name))

    def _change_wrapper(self, func_name, *args, **kwargs):
        value = getattr(super(ListPluginBase, self), func_name)(*args, **kwargs)
        self._update_model()
        return value

    def get_selected(self, **kwargs):
        if self._gtk_modelview:
            return self._get_gtk_selected(**kwargs)
        else:
            return None

    def _get_gtk_selected(self, index=False, force_list=False):
        modelview = self._gtk_modelview
        if hasattr(modelview, "get_selection"):
            # a treeview selection
            selection = modelview.get_selection()
            selection_mode = selection.get_mode()
            paths = selection.get_selected_rows()[1]
        elif hasattr(modelview, "get_active"):
            # combobox
            selection_mode = self._gtk.SELECTION_SINGLE
            active = modelview.get_active()
            if active < 0:
                paths = []
            else:
                paths = [[active]]
        else:
            # an iconview
            selection_mode = modelview.get_selection_mode()
            paths = modelview.get_selected_items()
        if index:
            get_result = lambda path: path[0]
        else:
            get_result = self.get_by_path
        if (selection_mode == self._gtk.SELECTION_MULTIPLE) or force_list:
            result = []
            for path in paths:
                result.append(get_result(path))
        else:
            if not paths:
                return None
            else:
                result = get_result(paths[0])
        return result

    def select(self, selected):
        if not isinstance(selected, (list, tuple)):
            selected = [selected]
        if self._gtk_modelview:
            self._select_gtk(selected)

    def _select_gtk(self, selected_objs):
        selection = self._gtk_modelview.get_selection()
        selected_uuids = [item["uuid"] for item in selected_objs]
        for index, item in enumerate(self):
            if item["uuid"] in selected_uuids:
                selection.select_path((index, ))
            else:
                selection.unselect_path((index, ))

    def set_gtk_modelview(self, modelview):
        self._gtk_modelview = modelview

    def _update_gtk_treemodel(self):
        if not self._gtk_modelview:
            return
        treemodel = self._gtk_modelview.get_model()
        current_uuids = [item["uuid"] for item in self]
        # remove all superfluous rows from "treemodel"
        removal_indices = [index for index, item in enumerate(treemodel)
                           if item[0] not in current_uuids]
        removal_indices.reverse()
        for index in removal_indices:
            treemodel.remove(treemodel.get_iter((index, )))
        # add all missing items to "treemodel"
        model_uuids = [row[0] for row in treemodel]
        for this_uuid in current_uuids:
            if this_uuid not in model_uuids:
                treemodel.append((this_uuid, ))
        # reorder the treemodel according to the current list
        sorted_indices = [current_uuids.index(row[0]) for row in treemodel]
        if sorted_indices:
            treemodel.reorder(sorted_indices)
        self.core.emit_event("tool-list-changed")

    def get_by_path(self, path):
        if not self._gtk_modelview:
            return None
        this_uuid = self._gtk_modelview.get_model()[int(path[0])][0]
        objs = [t for t in self if this_uuid == t["uuid"]]
        if objs:
            return objs[0]
        else:
            return None

    def get_by_attribute(self, key, value):
        for item in self:
            if item.get(key, None) == value:
                return item
        return None

    def _update_model(self):
        self._update_gtk_treemodel()
        for update_func in self._update_model_funcs:
            update_func()

    def register_model_update(self, func):
        self._update_model_funcs.append(func)

    def unregister_model_update(self, func):
        if func in self._update_model_funcs:
            self._update_model_funcs.remove(func)

    def _list_action(self, *args):
        # the second-to-last paramater should be the model view
        modelview = args[-2]
        # the last parameter should be the action (ACTION_UP|DOWN|DELETE|CLEAR)
        action = args[-1]
        if action not in (self.ACTION_UP, self.ACTION_DOWN, self.ACTION_DELETE, self.ACTION_CLEAR):
            self.log.info("Invalid action for ListPluginBase.list_action: %s", str(action))
            return
        selected_items = self.get_selected(index=True, force_list=True)
        selected_items.sort()
        if action in (self.ACTION_DOWN, self.ACTION_DELETE):
            selected_items.sort(reverse=True)
        new_selection = []
        if action == self.ACTION_CLEAR:
            while len(self) > 0:
                self.pop(0)
        else:
            for index in selected_items:
                if action == self.ACTION_UP:
                    if index > 0:
                        item = self.pop(index)
                        self.insert(index - 1, item)
                        new_selection.append(index - 1)
                elif action == self.ACTION_DOWN:
                    if index < len(self) - 1:
                        item = self.pop(index)
                        self.insert(index + 1, item)
                        new_selection.append(index + 1)
                elif action == self.ACTION_DELETE:
                    self.pop(index)
                    if len(self) > 0:
                        new_selection.append(min(index, len(self) - 1))
                else:
                    pass
        self._update_model()
        if hasattr(modelview, "get_selection"):
            selection = modelview.get_selection()
        else:
            selection = modelview
        selection.unselect_all()
        for index in new_selection:
            selection.select_path((index,))

    def _update_list_action_button_state(self, *args):
        modelview = args[-3]  # noqa F841 - maybe we need it later
        action = args[-2]
        button = args[-1]
        paths = self.get_selected(index=True, force_list=True)
        if action == self.ACTION_CLEAR:
            button.set_sensitive(len(self) > 0)
        elif not paths:
            button.set_sensitive(False)
        else:
            if action == self.ACTION_UP:
                button.set_sensitive(0 not in paths)
            elif action == self.ACTION_DOWN:
                button.set_sensitive((len(self) - 1) not in paths)
            else:
                button.set_sensitive(True)

    def register_list_action_button(self, action, button):
        modelview = self._gtk_modelview
        if hasattr(modelview, "get_selection"):
            # a treeview
            selection = modelview.get_selection()
            selection.connect("changed", self._update_list_action_button_state, modelview, action,
                              button)
        else:
            modelview.connect("selection-changed", self._update_list_action_button_state,
                              modelview, action, button)
        model = modelview.get_model()
        for signal in ("row-changed", "row-deleted", "row-has-child-toggled", "row-inserted",
                       "rows-reordered"):
            model.connect(signal, self._update_list_action_button_state, modelview, action, button)
        button.connect("clicked", self._list_action, modelview, action)
        # initialize the state of the button
        self._update_list_action_button_state(modelview, action, button)


class ObjectWithAttributes(dict):

    def __init__(self, node_key=None, attributes=None, **kwargs):
        super(ObjectWithAttributes, self).__init__(**kwargs)
        if attributes is not None:
            self.update(attributes)
        self["uuid"] = str(uuid.uuid4())
        self.node_key = node_key


def filter_list(items, *args, **kwargs):
    if len(args) > 1:
        _log.info("This filter accepts only a single unnamed parameter: index(es), but %d "
                  "parameters were given", len(args))
        return []
    elif len(args) == 1:
        try:
            items = [items[index] for index in args[0]]
        except TypeError:
            # not iterable
            try:
                items = [items[args[0]]]
            except (IndexError, TypeError):
                _log.info("Invalid index requested in filter: %s", str(args[0]))
                return []
    else:
        pass
    result = []
    for item in items:
        for filter_key in kwargs:
            try:
                if not item[filter_key] == kwargs[filter_key]:
                    break
            except KeyError:
                _log.info("Tried to filter an unknown attribute: %s", str(filter_key))
                break
        else:
            # all keys are matching
            result.append(item)
    return result


def get_filter(items):
    return lambda *args, **kwargs: filter_list(items, *args, **kwargs)
