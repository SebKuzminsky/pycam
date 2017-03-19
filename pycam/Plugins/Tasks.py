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

import time

from pycam import GenericError
import pycam.Plugins
import pycam.Utils
from pycam.Utils import get_non_conflicting_name


class Tasks(pycam.Plugins.ListPluginBase):

    UI_FILE = "tasks.ui"
    CATEGORIES = ["Task"]
    DEPENDS = ["Models", "Tools", "Processes", "Bounds", "Toolpaths"]

    def setup(self):
        if self.gui and self._gtk:
            self._gtk_handlers = []
            task_frame = self.gui.get_object("TaskBox")
            task_frame.unparent()
            self.core.register_ui("main", "Tasks", task_frame, weight=40)
            self._taskview = self.gui.get_object("TaskView")
            self.set_gtk_modelview(self._taskview)
            self.register_model_update(lambda: self.core.emit_event("task-list-changed"))
            for action, obj_name in ((self.ACTION_UP, "TaskMoveUp"),
                                     (self.ACTION_DOWN, "TaskMoveDown"),
                                     (self.ACTION_DELETE, "TaskDelete")):
                self.register_list_action_button(action, self.gui.get_object(obj_name))
            self._gtk_handlers.append((self.gui.get_object("TaskNew"), "clicked", self._task_new))
            # parameters
            parameters_box = self.gui.get_object("TaskParameterBox")

            def clear_parameter_widgets():
                parameters_box.foreach(parameters_box.remove)

            def add_parameter_widget(item, name):
                # create a frame within an alignment and the item inside
                if item.get_parent():
                    item.unparent()
                frame_label = self._gtk.Label()
                frame_label.set_markup("<b>%s</b>" % name)
                frame = self._gtk.Frame()
                frame.set_label_widget(frame_label)
                align = self._gtk.Alignment()
                frame.add(align)
                align.set_padding(0, 3, 12, 3)
                align.add(item)
                frame.show_all()
                parameters_box.pack_start(frame, expand=False)

            self.core.register_ui_section("task_parameters", add_parameter_widget,
                                          clear_parameter_widgets)
            self.core.get("register_parameter_group")(
                "task", changed_set_event="task-type-changed",
                changed_set_list_event="task-type-list-changed",
                get_current_set_func=self._get_type)
            self.models_widget = pycam.Gui.ControlsGTK.ParameterSection()
            self.core.register_ui_section("task_models", self.models_widget.add_widget,
                                          self.models_widget.clear_widgets)
            self.core.register_ui("task_parameters", "Collision models",
                                  self.models_widget.get_widget(), weight=20)
            self.components_widget = pycam.Gui.ControlsGTK.ParameterSection()
            self.core.register_ui_section("task_components", self.components_widget.add_widget,
                                          self.components_widget.clear_widgets)
            self.core.register_ui("task_parameters", "Components",
                                  self.components_widget.get_widget(), weight=10)
            # table
            self._gtk_handlers.append((self.gui.get_object("NameCell"), "edited",
                                       self._edit_task_name))
            selection = self._taskview.get_selection()
            self._gtk_handlers.append((selection, "changed", "task-selection-changed"))
            selection.set_mode(self._gtk.SELECTION_MULTIPLE)
            self._treemodel = self.gui.get_object("TaskList")
            self._treemodel.clear()
            # generate toolpaths
            self._gtk_handlers.extend((
                (self.gui.get_object("GenerateToolPathButton"), "clicked",
                 self._generate_selected_toolpaths),
                (self.gui.get_object("GenerateAllToolPathsButton"), "clicked",
                 self._generate_all_toolpaths)))
            # shape selector
            self._gtk_handlers.append((self.gui.get_object("TaskTypeSelector"), "changed",
                                       "task-type-changed"))
            self._event_handlers = (
                ("task-type-list-changed", self._update_table),
                ("task-selection-changed", self._task_switch),
                ("task-changed", self._store_task),
                ("task-changed", self._trigger_table_update),
                ("task-type-changed", self._store_task),
                ("task-selection-changed", self._update_widgets),
                ("task-list-changed", self._update_widgets))
            self.register_gtk_handlers(self._gtk_handlers)
            self.register_event_handlers(self._event_handlers)
            self._update_widgets()
            self._update_table()
            self._task_switch()
            self._trigger_table_update()
        self.register_state_item("tasks", self)
        self.core.set("tasks", self)
        return True

    def teardown(self):
        self.clear_state_items()
        if self.gui and self._gtk:
            self.core.unregister_ui("main", self.gui.get_object("TaskBox"))
            self.core.unregister_ui("task_parameters", self.models_widget)
            self.core.unregister_ui("task_parameters", self.components_widget)
            self.core.unregister_ui_section("task_models")
            self.core.unregister_ui_section("task_components")
            self.core.unregister_ui_section("task_parameters")
            self.unregister_gtk_handlers(self._gtk_handlers)
            self.unregister_event_handlers(self._event_handlers)
        while len(self) > 0:
            self.pop()

    def _edit_task_name(self, cell, path, new_text):
        task = self.get_by_path(path)
        if task and (new_text != task["name"]) and new_text:
            task["name"] = new_text

    def _trigger_table_update(self):
        self.gui.get_object("NameColumn").set_cell_data_func(self.gui.get_object("NameCell"),
                                                             self._render_task_name)

    def _render_task_name(self, column, cell, model, m_iter):
        task = self.get_by_path(model.get_path(m_iter))
        cell.set_property("text", task["name"])

    def _get_type(self, name=None):
        types = self.core.get("get_parameter_sets")("task")
        if name is None:
            # find the currently selected one
            selector = self.gui.get_object("TaskTypeSelector")
            model = selector.get_model()
            index = selector.get_active()
            if index < 0:
                return None
            type_name = model[index][1]
        else:
            type_name = name
        if type_name in types:
            return types[type_name]
        else:
            return None

    def select_type(self, name):
        selector = self.gui.get_object("TaskTypeSelector")
        for index, row in enumerate(selector.get_model()):
            if row[1] == name:
                selector.set_active(index)
                break
        else:
            selector.set_active(-1)

    def _update_table(self):
        selected = self._get_type()
        model = self.gui.get_object("TaskTypeList")
        model.clear()
        types = self.core.get("get_parameter_sets")("task").values()
        types.sort(key=lambda item: item["weight"])
        for one_type in types:
            model.append((one_type["label"], one_type["name"]))
        # check if any on the processes became obsolete due to a missing plugin
        removal = []
        type_names = [one_type["name"] for one_type in types]
        for index, task in enumerate(self):
            if task["type"] not in type_names:
                removal.append(index)
        removal.reverse()
        for index in removal:
            self.pop(index)
        # show "new" only if a strategy is available
        self.gui.get_object("TaskNew").set_sensitive(len(model) > 0)
        selector_box = self.gui.get_object("TaskChooserBox")
        if len(model) < 2:
            selector_box.hide()
        else:
            selector_box.show()
        if selected:
            self.select_type(selected["name"])

    def _update_widgets(self):
        self.gui.get_object("GenerateToolPathButton").set_sensitive(len(self.get_selected()) > 0)
        self.gui.get_object("GenerateAllToolPathsButton").set_sensitive(len(self) > 0)

    def _task_switch(self):
        tasks = self.get_selected()
        control_box = self.gui.get_object("TaskDetails")
        if len(tasks) != 1:
            control_box.hide()
        else:
            task = tasks[0]
            self.core.block_event("task-changed")
            self.core.block_event("task-type-changed")
            type_name = task["type"]
            self.select_type(type_name)
            self.core.get("set_parameter_values")("task", task["parameters"])
            control_box.show()
            self.core.unblock_event("task-type-changed")
            self.core.unblock_event("task-changed")
            # trigger a widget update
            self.core.emit_event("task-type-changed")

    def _store_task(self, widget=None):
        tasks = self.get_selected()
        details_box = self.gui.get_object("TaskDetails")
        task_type = self._get_type()
        if (len(tasks) != 1) or not task_type:
            details_box.hide()
        else:
            task = tasks[0]
            task["type"] = task_type["name"]
            parameters = task["parameters"]
            parameters.update(self.core.get("get_parameter_values")("task"))
            details_box.show()

    def _task_new(self, *args):
        types = self.core.get("get_parameter_sets")("task").values()
        types.sort(key=lambda item: item["weight"])
        one_type = types[0]
        name = get_non_conflicting_name("Task #%d", [task["name"] for task in self])
        new_task = TaskEntity({"type": one_type["name"],
                               "parameters": one_type["parameters"].copy(),
                               "name": name})
        self.append(new_task)
        self.select(new_task)

    def generate_toolpaths(self, tasks):
        progress = self.core.get("progress")
        progress.set_multiple(len(tasks), "Toolpath")
        for task in tasks:
            if not self.generate_toolpath(task, progress=progress):
                # break out of the loop, if cancel was requested
                break
            progress.update_multiple()
        progress.finish()

    def _generate_selected_toolpaths(self, widget=None):
        tasks = self.get_selected()
        self.generate_toolpaths(tasks)

    def _generate_all_toolpaths(self, widget=None):
        self.generate_toolpaths(self)

    def generate_toolpath(self, task, progress=None):
        start_time = time.time()
        if progress:
            use_multi_progress = True
        else:
            use_multi_progress = False
            progress = self.core.get("progress")
        progress.update(text="Preparing toolpath generation")

        class UpdateView(object):
            def __init__(self, task_plugin, request_redraw_function, max_fps=1):
                self.task_plugin = task_plugin
                self.last_update_time = time.time()
                self.max_fps = max_fps
                self.request_redraw_function = request_redraw_function
                self.last_tool_position = None
                self.current_tool_position = None

            def update(self, text=None, percent=None, tool_position=None, toolpath=None):
                if toolpath is not None:
                    self.task_plugin.core.set("toolpath_in_progress", toolpath)
                # always store the most recently reported tool_position for the next visualization
                if tool_position is not None:
                    self.current_tool_position = tool_position
                redraw_wanted = False
                current_time = time.time()
                if (current_time - self.last_update_time) > 1.0 / self.max_fps:
                    if self.current_tool_position != self.last_tool_position:
                        tool = self.task_plugin.core.get("current_tool")
                        if tool:
                            tool.moveto(self.current_tool_position)
                        self.last_tool_position = self.current_tool_position
                        redraw_wanted = True
                    if self.task_plugin.core.get("show_toolpath_progress"):
                        redraw_wanted = True
                    self.last_update_time = current_time
                    if redraw_wanted and self.request_redraw_function:
                        self.request_redraw_function()
                # break the loop if someone clicked the "cancel" button
                return progress.update(text=text, percent=percent)

        tool_shape = task["parameters"]["tool"]["shape"]
        tool_parameters = task["parameters"]["tool"]["parameters"]
        tool = self.core.get("get_parameter_sets")("tool")[tool_shape]["func"](tool_parameters)[0]
        self.core.set("current_tool", tool)
        draw_callback = UpdateView(self, lambda: self.core.emit_event("visual-item-updated"),
                                   max_fps=self.core.get("tool_progress_max_fps")).update
        progress.update(text="Generating collision model")
        # run the toolpath generation
        progress.update(text="Starting the toolpath generation")
        try:
            task_resolver = self.core.get("get_parameter_sets")("task")[task["type"]]["func"]
            toolpath = task_resolver(task, callback=draw_callback)
        except GenericError as exc:
            # an error occoured - "toolpath" contains the error message
            self.log.error("Failed to generate toolpath: %s", exc)
            # we were not successful (similar to a "cancel" request)
            return False
        except Exception:
            # catch all non-system-exiting exceptions
            self.log.error(pycam.Utils.get_exception_report())
            return False
        finally:
            self.core.set("current_tool", None)
            self.core.set("toolpath_in_progress", None)
            if not use_multi_progress:
                progress.finish()

        self.log.info("Toolpath generation time: %f", time.time() - start_time)

        if toolpath is None:
            # user interruption
            # return "False" if the action was cancelled
            result = not progress.update()
        else:
            self.core.get("toolpaths").add_new(toolpath)
            # return "False" if the action was cancelled
            result = not progress.update()
        return result


class TaskEntity(pycam.Plugins.ObjectWithAttributes):

    def __init__(self, parameters):
        super(TaskEntity, self).__init__("task", parameters)
