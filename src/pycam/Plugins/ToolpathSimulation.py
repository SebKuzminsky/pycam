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

import math
import datetime
import gobject

import pycam.Plugins
# this requires ODE - we import it later, if necessary
#import pycam.Simulation.ODEBlocks


class ToolpathSimulation(pycam.Plugins.PluginBase):

    UI_FILE = "toolpath_simulation.ui"
    DEPENDS = ["Toolpaths", "OpenGLViewToolpath"]
    CATEGORIES = ["Toolpath"]

    def setup(self):
        self._running = None
        if self.gui:
            self._gtk_handlers = []
            self._frame = self.gui.get_object("SimulationBox")
            self.core.register_ui("toolpath_handling", "Simulation",
                    self._frame, 25)
            self._speed_factor_widget = self.gui.get_object(
                    "SimulationSpeedFactorValue")
            self._speed_factor_widget.set_value(1.0)
            self._progress = self.gui.get_object(
                    "SimulationProgressTimelineValue")
            self._timer_widget = self.gui.get_object(
                    "SimulationProgressTimeDisplay")
            self.core.set("show_simulation", False)
            self._toolpath_moves = None
            self._start_button = self.gui.get_object("SimulationStartButton")
            self._pause_button = self.gui.get_object("SimulationPauseButton")
            self._stop_button = self.gui.get_object("SimulationStopButton")
            for obj, handler in ((self._start_button, self._start_simulation),
                    (self._pause_button, self._pause_simulation),
                    (self._stop_button, self._stop_simulation)):
                self._gtk_handlers.append((obj, "clicked", handler))
            self._gtk_handlers.append((self._progress, "value-changed",
                    self._update_toolpath))
            self._event_handlers = (
                    ("toolpath-selection-changed", self._update_visibility), )
            self.register_event_handlers(self._event_handlers)
            self.register_gtk_handlers(self._gtk_handlers)
            self._update_visibility()
            self.core.register_event("visualize-items", self.show_simulation)
        return True

    def teardown(self):
        if self.gui:
            self.core.remove_item("show_simulation")
            self.core.unregister_ui("toolpath_handling", self._frame)
            self.core.unregister_event("visualize-items", self.show_simulation)
            self.unregister_event_handlers(self._event_handlers)
            self.unregister_gtk_handlers(self._gtk_handlers)

    def _update_visibility(self):
        toolpaths = self.core.get("toolpaths").get_selected()
        if toolpaths and (len(toolpaths) == 1):
            self._frame.show()
        else:
            self._frame.hide()

    def _start_simulation(self, widget=None):
        if self._running is None:
            # initial start of simulation (not just continuing)
            toolpaths = self.core.get("toolpaths")
            if not toolpaths:
                # this should not happen
                return
            # we use only one toolpath
            self._toolpath = toolpaths[0]
            # calculate steps
            self._safety_height = self.core.get("gcode_safety_height")
            self._progress.set_upper(self._toolpath.get_machine_time(
                    safety_height=self._safety_height))
            self._progress.set_value(0)
            self._distance = self._toolpath.get_machine_movement_distance(
                        safety_height=self._safety_height)
            self._feedrate = self._toolpath.get_params().get("tool_feedrate",
                    300)
            self._toolpath_moves = None
            self.core.set("show_simulation", True)
            self._running = True
            interval_ms = int(1000 / self.core.get("drill_progress_max_fps"))
            self._set_sensitive_others(self._frame, False)
            gobject.timeout_add(interval_ms, self._next_timestep)
        else:
            self._running = True
        self._start_button.set_sensitive(False)
        self._pause_button.set_sensitive(True)
        self._stop_button.set_sensitive(True)

    def _set_sensitive_others(self, widget, new_state):
        """ go through all widgets above the given one and change their
        "sensitivity" state. This effects everything besides the one
        given widget (and its direct line of ancestors).
        Useful for disabling the screen while an action is going on.
        """
        child = widget
        parent = widget.get_parent()
        def disable_if_different(obj, current):
            if not obj is current:
                obj.set_sensitive(new_state)
        while parent:
            # Use "forall" instead of "foreach" - this also catches all tab
            # labels.
            parent.forall(disable_if_different, child)
            child = parent
            parent = parent.get_parent()

    def _pause_simulation(self, widget=None):
        self._start_button.set_sensitive(True)
        self._pause_button.set_sensitive(False)
        self._running = False

    def _stop_simulation(self, widget=None):
        self._running = None
        self.core.set("show_simulation", False)
        self._toolpath_moves = None
        self._timer_widget.set_label("")
        self._progress.set_value(0)
        self._start_button.set_sensitive(True)
        self._pause_button.set_sensitive(False)
        self._stop_button.set_sensitive(False)
        self._set_sensitive_others(self._frame, True)
        self.core.emit_event("visual-item-updated")

    def _next_timestep(self):
        if self._running is None:
            # stop operation
            return False
        if not self._running:
            # pause -> no change
            return True
        if self._progress.get_value() < self._progress.get_upper():
            time_step = self._speed_factor_widget.get_value() / \
                    self.core.get("drill_progress_max_fps")
            new_time = self._progress.get_value() + time_step
            new_time = min(new_time, self._progress.get_upper())
            if new_time != self._progress.get_value():
                # update the visualization
                self._progress.set_value(new_time)
        return True

    def _update_toolpath(self, widget=None):
        if (not self._running is None) and (self._progress.get_upper() > 0):
            fraction = self._progress.get_value() / self._progress.get_upper()
            current = datetime.timedelta(
                    seconds=int(self._progress.get_value()))
            complete = datetime.timedelta(
                    seconds=int(self._progress.get_upper()))
            self._timer_widget.set_label("%s / %s" % (current, complete))
            self._toolpath_moves = self._toolpath.get_moves(
                    safety_height=self._safety_height,
                    max_movement=self._distance * fraction)
            self.core.emit_event("visual-item-updated")

    def show_simulation(self):
        if self._toolpath_moves and self.core.get("show_simulation"):
            self.core.get("draw_toolpath_moves_func")(self._toolpath_moves)

    def update_toolpath_simulation_ode(self, widget=None, toolpath=None):
        import pycam.Simulation.ODEBlocks as ODEBlocks
        # get the currently selected toolpath, if none is give
        if toolpath is None:
            toolpath_index = self._treeview_get_active_index(self.toolpath_table, self.toolpath)
            if toolpath_index is None:
                return
            else:
                toolpath = self.toolpath[toolpath_index]
        paths = toolpath.paths
        # set the current cutter
        self.cutter = pycam.Cutters.get_tool_from_settings(
                toolpath.get_tool_settings())
        # calculate steps
        detail_level = self.gui.get_object("SimulationDetailsValue").get_value()
        grid_size = 100 * pow(2, detail_level - 1)
        bounding_box = toolpath.get_toolpath_settings().get_bounds()
        (minx, miny, minz), (maxx, maxy, maxz) = bounding_box.get_bounds()
        # proportion = dimension_x / dimension_y
        proportion = (maxx - minx) / (maxy - miny)
        x_steps = int(sqrt(grid_size) * proportion)
        y_steps = int(sqrt(grid_size) / proportion)
        simulation_backend = ODEBlocks.ODEBlocks(toolpath.get_tool_settings(),
                toolpath.get_bounding_box(), x_steps=x_steps, y_steps=y_steps)
        self.core.set("simulation_object", simulation_backend)
        # disable the simulation widget (avoids confusion regarding "cancel")
        if not widget is None:
            self.gui.get_object("SimulationTab").set_sensitive(False)
        # update the view
        self.update_view()
        # calculate the simulation and show it simultaneously
        progress = self.core.get("progress")
        for path_index, path in enumerate(paths):
            progress_text = "Simulating path %d/%d" % (path_index, len(paths))
            progress_value_percent = 100.0 * path_index / len(paths)
            if progress.update(text=progress_text, percent=progress_value_percent):
                # break if the user pressed the "cancel" button
                break
            for index in range(len(path.points)):
                self.cutter.moveto(path.points[index])
                if index != 0:
                    start = path.points[index - 1]
                    end = path.points[index]
                    if start != end:
                        simulation_backend.process_cutter_movement(start, end)
                self.update_view()
                # break the loop if someone clicked the "cancel" button
                if progress.update():
                    break
            progress.finish()
        # enable the simulation widget again (if we were started from the GUI)
        if not widget is None:
            self.gui.get_object("SimulationTab").set_sensitive(True)

