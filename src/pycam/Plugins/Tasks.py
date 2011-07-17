# -*- coding: utf-8 -*-
"""
$Id$

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


import pycam.Plugins


class Tasks(pycam.Plugins.ListPluginBase):

    UI_FILE = "tasks.ui"
    COLUMN_REF, COLUMN_NAME = range(2)
    LIST_ATTRIBUTE_MAP = {"id": COLUMN_REF, "name": COLUMN_NAME}
    DEPENDS = ["Models", "Tools", "Processes", "Bounds"]

    def setup(self):
        if self.gui:
            import gtk
            self._gtk = gtk
            task_frame = self.gui.get_object("TaskBox")
            task_frame.unparent()
            self.core.register_ui("main", "Tasks", task_frame, weight=40)
            self._taskview = self.gui.get_object("TaskView")
            for action, obj_name in ((self.ACTION_UP, "TaskMoveUp"),
                    (self.ACTION_DOWN, "TaskMoveDown"),
                    (self.ACTION_DELETE, "TaskDelete")):
                self.register_list_action_button(action, self._taskview,
                        self.gui.get_object(obj_name))
            self.gui.get_object("TaskNew").connect("clicked",
                    self._task_new)
            self.core.register_event("task-selection-changed",
                    self._switch_task)
            self.gui.get_object("TaskNameCell").connect("edited",
                    self._edit_task_name)
            selection = self._taskview.get_selection()
            selection.connect("changed",
                    lambda widget, event: self.core.emit_event(event), 
                    "task-selection-changed")
            selection.set_mode(self._gtk.SELECTION_MULTIPLE)
            self._treemodel = self.gui.get_object("TaskList")
            self._treemodel.clear()
            def update_model():
                if not hasattr(self, "_model_cache"):
                    self._model_cache = {}
                cache = self._model_cache
                for row in self._treemodel:
                    cache[row[self.COLUMN_REF]] = list(row)
                self._treemodel.clear()
                for index, item in enumerate(self):
                    if id(item) in cache:
                        self._treemodel.append(cache[id(item)])
                    else:
                        self._treemodel.append((id(item), "Task #%d" % index))
                self.core.emit_event("task-list-changed")
            self._detail_handlers = []
            for obj_name in ("FeedrateControl", "SpindleSpeedControl"):
                obj = self.gui.get_object(obj_name)
                handler = obj.connect("value-changed",
                        lambda widget: self.core.emit_event("task-changed"))
                self._detail_handlers.append((obj, handler))
            for obj_name in ("Models", "ToolSelector", "ProcessSelector", "BoundsSelector"):
                obj = self.gui.get_object(obj_name)
                obj.get_model().clear()
                if hasattr(obj, "get_selection"):
                    obj = obj.get_selection()
                handler = obj.connect("changed",
                        lambda widget: self.core.emit_event("task-changed"))
                self._detail_handlers.append((obj, handler))
            for category, event in (("models", "model-list-changed"),
                    ("tool", "tool-list-changed"),
                    ("process", "process-list-changed"),
                    ("bounds", "bounds-list-changed")):
                self.core.register_event(event, self._update_external_model,
                        category)
                self._update_external_model(category)
            self.core.register_event("task-changed", self._store_task)
            self.register_model_update(update_model)
            self._switch_task()
        self.core.set("tasks", self)
        return True

    def _get_modelview_and_content(self, category):
        model = {None: self._taskview,
                "tool": self.gui.get_object("ToolSelector"),
                "process": self.gui.get_object("ProcessSelector"),
                "bounds": self.gui.get_object("BoundsSelector"),
                "models": self.gui.get_object("Models")}[category]
        content = {None: self,
                "tool": self.core.get("tools"),
                "process": self.core.get("processes"),
                "bounds": self.core.get("bounds"),
                "models": self.core.get("models")}[category]
        return model, content

    def get_selected(self, category=None, index=False):
        modelview, content = self._get_modelview_and_content(category)
        return self._get_selected(modelview, index=index, content=content)

    def select(self, item, category=None, keep=False):
        if isinstance(item, list):
            keep = False
            if not item:
                self.select(None, category=category)
            else:
                for one in item:
                    self.select(one, category=category, keep=keep)
                    keep = True
        else:
            modelview, content = self._get_modelview_and_content(category)
            if (item is None) or (item in content):
                if not item is None:
                    index = [id(entry) for entry in content].index(id(item))
                if hasattr(modelview, "get_selection"):
                    selection = modelview.get_selection()
                    if not keep:
                        selection.unselect_all()
                    if not item is None:
                        selection.select_path((index,))
                else:
                    if item is None:
                        modelview.set_active(-1)
                    else:
                        modelview.set_active(index)

    def _edit_task_name(self, cell, path, new_text):
        path = int(path)
        if (new_text != self._treemodel[path][self.COLUMN_NAME]) and \
                new_text:
            self._treemodel[path][self.COLUMN_NAME] = new_text

    def _switch_task(self):
        tasks = self.get_selected()
        if tasks:
            task = tasks[0]
        else:
            task = None
        details_box = self.gui.get_object("TaskDetails")
        if task:
            # block all "change" signals for the task controls
            for obj, signal_handler in self._detail_handlers:
                obj.handler_block(signal_handler)
            for key in ("tool", "process", "bounds", "models"):
                self.select(task[key], category=key)
            self.gui.get_object("FeedrateControl").set_value(task["feedrate"])
            self.gui.get_object("SpindleSpeedControl").set_value(task["spindlespeed"])
            # unblock the signals again
            for obj, signal_handler in self._detail_handlers:
                obj.handler_unblock(signal_handler)
            details_box.show()
        else:
            details_box.hide()

    def _store_task(self, widget=None):
        tasks = self.get_selected()
        if tasks:
            task = tasks[0]
        else:
            task = None
        details_box = self.gui.get_object("TaskDetails")
        if task is None:
            details_box.hide()
            return
        else:
            task["feedrate"] = self.gui.get_object("FeedrateControl").get_value()
            task["spindlespeed"] = self.gui.get_object("SpindleSpeedControl").get_value()
            for key in ("tool", "process", "bounds", "models"):
                task[key] = self.get_selected(category=key)
            details_box.show()

    def _update_external_model(self, category):
        modelview, content = self._get_modelview_and_content(category)
        ids = [id(item) for item in content]
        model = modelview.get_model()
        for index, one_id in enumerate(ids):
            while (len(model) > index) and \
                    (model[index][self.COLUMN_REF] != one_id):
                index_iter = model.get_iter((index, ))
                if model[index][self.COLUMN_REF] in ids:
                    # move it to the end of the list
                    model.move_before(index_iter, None)
                else:
                    model.remove(index_iter)
            if len(model) <= index:
                name = content.get_attr(content[index], "name", id_col=self.COLUMN_REF)
                model.append((one_id, name))

    def _task_new(self, *args):
        new_task = {
                "models": [],
                "tool": [],
                "process": [],
                "bounds": [],
                "feedrate": 300,
                "spindlespeed": 1000,
        }
        self.append(new_task)
        self.select(new_task)

    def process_one_task(self, task_index):
        try:
            task = self.task_list[task_index]
        except IndexError:
            # this should only happen, if we were called in batch mode (command line)
            log.warn("The given task ID (%d) does not exist. Valid values are: %s." % (task_index, range(len(self.task_list))))
            return
        self.generate_toolpath(task["tool"], task["process"], task["bounds"])

    def process_multiple_tasks(self, task_list=None):
        if task_list is None:
            task_list = self.task_list[:]
        enabled_tasks = []
        for index in range(len(task_list)):
            task = task_list[index]
            if task["enabled"]:
                enabled_tasks.append(task)
        progress = self.core.get("progress")
        progress.set_multiple(len(enabled_tasks), "Toolpath")
        for task in enabled_tasks:
            if not self.generate_toolpath(task["tool"], task["process"],
                    task["bounds"], progress=progress):
                # break out of the loop, if cancel was requested
                break
            progress.update_multiple()
        progress.finish()

