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


class Processes(pycam.Plugins.ListPluginBase):

    UI_FILE = "processes.ui"
    COLUMN_REF, COLUMN_NAME = range(2)
    LIST_ATTRIBUTE_MAP = {"ref": COLUMN_REF, "name": COLUMN_NAME}
    CONTROL_BUTTONS = ("PushRemoveStrategy", "ContourPolygonStrategy",
            "ContourFollowStrategy", "SurfaceStrategy", "EngraveStrategy",
            "OverlapPercentControl", "MaterialAllowanceControl",
            "MaxStepDownControl", "EngraveOffsetControl",
            "PocketingControl", "GridDirectionX", "GridDirectionY",
            "GridDirectionXY", "MillingStyleConventional", "MillingStyleClimb",
            "MillingStyleIgnore")
    POCKETING_TYPES = ["none", "holes", "enclosed"]
    CONTROL_SIGNALS = ("toggled", "value-changed", "changed")
    CONTROL_GET = ("get_active", "get_value")
    CONTROL_SET = ("set_active", "set_value")

    def setup(self):
        if self.gui:
            import gtk
            self._gtk = gtk
            process_frame = self.gui.get_object("ProcessBox")
            process_frame.unparent()
            self.core.register_ui("main", "Processs", process_frame, weight=20)
            self._modelview = self.gui.get_object("ProcessEditorTable")
            for action, obj_name in ((self.ACTION_UP, "ProcessMoveUp"),
                    (self.ACTION_DOWN, "ProcessMoveDown"),
                    (self.ACTION_DELETE, "ProcessDelete")):
                self.register_list_action_button(action, self._modelview,
                        self.gui.get_object(obj_name))
            self.gui.get_object("ProcessNew").connect("clicked",
                    self._process_new)
            selection = self._modelview.get_selection()
            selection.connect("changed", 
                    lambda widget, event: self.core.emit_event(event),
                    "process-selection-changed")
            self.gui.get_object("NameCell").connect("edited",
                    self._edit_process_name)
            cell = self.gui.get_object("DescriptionCell")
            self.gui.get_object("DescriptionColumn").set_cell_data_func(
                    cell, self._render_process_description)
            self._treemodel = self.gui.get_object("ProcessList")
            self._treemodel.clear()
            def update_model():
                if not hasattr(self, "_model_cache"):
                    self._model_cache = {}
                cache = self._model_cache
                for row in self._treemodel:
                    cache[row[self.COLUMN_REF]] = list(row)
                self._treemodel.clear()
                for index, item in enumerate(self):
                    if not id(item) in cache:
                        cache[id(item)] = [id(item), "Process #%d" % index]
                    self._treemodel.append(cache[id(item)])
                self.core.emit_event("process-list-changed")
            self.register_model_update(update_model)
            # process settings
            self._detail_handlers = []
            for obj_name in self.CONTROL_BUTTONS:
                obj = self.gui.get_object(obj_name)
                for signal in self.CONTROL_SIGNALS:
                    try:
                        handler = obj.connect(signal,
                                lambda *args: self.core.emit_event(args[-1]),
                                "process-changed")
                        self._detail_handlers.append((obj, handler))
                        break
                    except TypeError:
                        continue
                else:
                    self.log.info("Failed to connect to widget '%s'" % str(obj_name))
            self.core.register_event("process-selection-changed",
                    self._process_switch)
            self.core.register_event("process-changed",
                    self._store_process_settings)
            self._store_process_settings()
        self.core.set("processes", self)
        return True

    def teardown(self):
        if self.gui:
            self.core.unregister_ui("main", self.gui.get_object("ProcessBox"))
        self.core.set("processes", None)
        return True

    def get_selected(self, index=False):
        return self._get_selected(self._modelview, index=index)

    def select(self, process):
        if process in self:
            selection = self._modelview.get_selection()
            index = [id(p) for p in self].index(id(p))
            selection.unselect_all()
            selection.select_path((index,))

    def _render_process_description(self, column, cell, model, m_iter):
        path = model.get_path(m_iter)
        data = self[path[0]]
        # find the current strategy
        for key in ("PushRemoveStrategy", "ContourPolygonStrategy",
                "ContourFollowStrategy", "SurfaceStrategy", "EngraveStrategy"):
            if data[key]:
                strategy = key
                break
        if strategy == "PushRemoveStrategy":
            text = "Slice %g%s %d%%" % (data["MaxStepDownControl"],
                    self.core.get("unit"), data["OverlapPercentControl"])
        elif strategy == "ContourPolygonStrategy":
            text = "Contour (polygon) %g%s" % (data["MaxStepDownControl"],
                    self.core.get("unit"))
        elif strategy == "ContourFollowStrategy":
            text = "Contour (follow) %g%s" % (data["MaxStepDownControl"],
                    self.core.get("unit"))
        elif strategy == "SurfaceStrategy":
            text = "Surface %d%%" % data["OverlapPercentControl"]
        else:
            # EngraveStrategy
            text = "Engrave %g%s" % (data["EngraveOffsetControl"],
                    self.core.get("unit"))
        cell.set_property("text", text)

    def _edit_process_name(self, cell, path, new_text):
        path = int(path)
        if (new_text != self._treemodel[path][self.COLUMN_NAME]) and \
                new_text:
            self._treemodel[path][self.COLUMN_NAME] = new_text

    def _store_process_settings(self):
        data = self.get_selected()
        if data is None:
            self.gui.get_object("ProcessSettingsControlsBox").hide()
            return
        else:
            for obj_name in self.CONTROL_BUTTONS:
                obj = self.gui.get_object(obj_name)
                for get_func in self.CONTROL_GET:
                    if hasattr(obj, get_func):
                        value = getattr(obj, get_func)()
                        data[obj_name] = value
                        break
                else:
                    self.log.info("Failed to update value of control %s" % obj_name)
            self.gui.get_object("ProcessSettingsControlsBox").show()
            while not self._validate_process_consistency():
                pass
            # trigger a table update - this is clumsy!
            cell = self.gui.get_object("DescriptionColumn")
            renderer = self.gui.get_object("DescriptionCell")
            cell.set_cell_data_func(renderer, self._render_process_description)

    def _process_switch(self, widget=None, data=None):
        process = self.get_selected()
        control_box = self.gui.get_object("ProcessSettingsControlsBox")
        if not process:
            control_box.hide()
        else:
            for obj, handler in self._detail_handlers:
                obj.handler_block(handler)
            for obj_name, value in process.iteritems():
                obj = self.gui.get_object(obj_name)
                for set_func in self.CONTROL_SET:
                    if hasattr(obj, set_func):
                        if (value is False) and hasattr(obj, "get_group"):
                            # no "False" for radio buttons
                            pass
                        else:
                            getattr(obj, set_func)(value)
                        break
                else:
                    self.log.info("Failed to set value of control %s" % obj_name)
            for obj, handler in self._detail_handlers:
                obj.handler_unblock(handler)
            control_box.show()
        
    def _process_new(self, *args):
        current_process_index = self.get_selected(index=True)
        if current_process_index is None:
            current_process_index = 0
        new_process = {"PushRemoveStrategy": True,
                "ContourPolygonStrategy": False,
                "ContourFollowStrategy": False,
                "SurfaceStrategy": False,
                "EngraveStrategy": False,
                "OverlapPercentControl": 10,
                "MaterialAllowanceControl": 0,
                "MaxStepDownControl": 1,
                "EngraveOffsetControl": 0,
                "PocketingControl": self.POCKETING_TYPES.index("none"),
                "GridDirectionX": True,
                "GridDirectionY": False,
                "GridDirectionXY": False,
                "MillingStyleConventional": False,
                "MillingStyleClimb": False,
                "MillingStyleIgnore": True,
        }
        self.append(new_process)
        self.select(new_process)
        # loop until the process is valid
        while not self._validate_process_consistency():
            pass

    def _validate_process_consistency(self):
        data = self.get_selected()
        if not data:
            return True
        if data["ContourPolygonStrategy"] and not data["MillingStyleIgnore"]:
            data["MillingStyleConventional"] = False
            data["MillingStyleIgnore"] = True
            data["MillingStyleClimb"] = False
            self.gui.get_object("MillingStyleIgnore").set_active(True)
            return False
        if data["ContourPolygonStrategy"] and not data["GridDirectionX"]:
            # only "x" direction for ContourPolygon
            data["GridDirectionX"] = True
            data["GridDirectionY"] = False
            data["GridDirectionXY"] = False
            self.gui.get_object("GridDirectionX").set_active(True)
            return False
        if (data["ContourFollowStrategy"] or data["EngraveStrategy"]) \
                and data["MillingStyleIgnore"]:
            data["MillingStyleConventional"] = True
            data["MillingStyleIgnore"] = False
            data["MillingStyleClimb"] = False
            self.gui.get_object("MillingStyleConventional").set_active(True)
            return False
        all_controls = ("GridDirectionX", "GridDirectionY", "GridDirectionXY",
                "MillingStyleConventional", "MillingStyleClimb",
                "MillingStyleIgnore", "MaxStepDownControl",
                "MaterialAllowanceControl", "OverlapPercentControl",
                "EngraveOffsetControl", "PocketingControl")
        active_controls = {
            "PushRemoveStrategy": ("GridDirectionX", "GridDirectionY",
                    "GridDirectionXY", "MillingStyleConventional",
                    "MillingStyleClimb", "MillingStyleIgnore",
                    "MaxStepDownControl", "MaterialAllowanceControl",
                    "OverlapPercentControl"),
            # TODO: direction y and xy currently don't work for ContourPolygonStrategy
            "ContourPolygonStrategy": ("GridDirectionX",
                    "MillingStyleIgnore", "MaxStepDownControl",
                    "MaterialAllowanceControl", "OverlapPercentControl"),
            "ContourFollowStrategy": ("MillingStyleConventional",
                    "MillingStyleClimb", "MaxStepDownControl"),
            "SurfaceStrategy": ("GridDirectionX", "GridDirectionY",
                    "GridDirectionXY", "MillingStyleConventional",
                    "MillingStyleClimb", "MillingStyleIgnore",
                    "MaterialAllowanceControl", "OverlapPercentControl"),
            "EngraveStrategy": ("MaxStepDownControl", "EngraveOffsetControl",
                    "MillingStyleConventional", "MillingStyleClimb",
                    "PocketingControl"),
        }
        # find the current strategy
        for key in active_controls:
            if data[key]:
                strategy = key
                break
        # disable all invalid controls
        for one_control in all_controls:
            self.gui.get_object(one_control).set_sensitive(one_control in active_controls[strategy])
        return True

