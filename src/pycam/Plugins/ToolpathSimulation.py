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
# this requires ODE - we import it later, if necessary
#import pycam.Simulation.ODEBlocks


class ToolpathSimulation(pycam.Plugins.PluginBase):

    UI_FILE = "toolpath_simulation.ui"

    def setup(self):
        if self.gui:
            speed_factor_widget = self.gui.get_object("SimulationSpeedFactor")
            self.core.add_item("simulation_speed_factor",
                    lambda: pow(10, speed_factor_widget.get_value()),
                    lambda value: speed_factor_widget.set_value(math.log10(
                            max(0.001, value))))
            simulation_progress = self.gui.get_object(
                    "SimulationProgressTimelineValue")
            def update_simulation_progress(widget):
                if widget.get_value() == 100:
                    # a negative value indicates, that the simulation is finished
                    self.core.set("simulation_current_distance", -1)
                else:
                    complete = self.core.get("simulation_complete_distance")
                    partial = widget.get_value() / 100.0 * complete
                    self.core.set("simulation_current_distance", partial)
            simulation_progress.connect("value-changed", update_simulation_progress)
            # update the speed factor label
            speed_factor_widget.connect("value-changed", lambda widget: \
                    self.gui.get_object("SimulationSpeedFactorValueLabel").\
                    set_label("%.2f" % self.core.get("simulation_speed_factor")))
            self.simulation_window = self.gui.get_object("SimulationDialog")
            self.simulation_window.connect("delete-event",
                    self.finish_toolpath_simulation)
            sim_detail_obj = self.gui.get_object("SimulationDetailsValue")
            self.core.add_item("simulation_details_level",
                    sim_detail_obj.get_value, sim_detail_obj.set_value)
        return True

    def finish_toolpath_simulation(self, widget=None, data=None):
        # hide the simulation tab
        self.simulation_window.hide()
        # enable all other tabs again
        self.toggle_tabs_for_simulation(True)
        self.core.set("simulation_object", None)
        self.core.set("simulation_toolpath_moves", None)
        self.core.set("show_simulation", False)
        self.core.set("simulation_toolpath", None)
        self.update_view()
        # don't destroy the simulation window (for "destroy" event)
        return True

    def update_toolpath_simulation(self, widget=None, toolpath=None):
        s = self.core
        # update the GUI
        while gtk.events_pending():
            gtk.main_iteration()
        if not s.get("show_simulation"):
            # cancel
            return False
        safety_height = s.get("gcode_safety_height")
        if not s.get("simulation_toolpath"):
            # get the currently selected toolpath, if none is give
            if toolpath is None:
                toolpath_index = self._treeview_get_active_index(self.toolpath_table, self.toolpath)
                if toolpath_index is None:
                    return
                else:
                    toolpath = self.toolpath[toolpath_index]
            s.set("simulation_toolpath", toolpath)
            # set the current cutter
            self.cutter = toolpath.toolpath_settings.get_tool()
            # calculate steps
            s.set("simulation_machine_time",
                    toolpath.get_machine_time(safety_height=safety_height))
            s.set("simulation_complete_distance",
                    toolpath.get_machine_movement_distance(
                        safety_height=safety_height))
            s.set("simulation_current_distance", 0)
        else:
            toolpath = s.get("simulation_toolpath")
        if (s.get("simulation_current_distance") \
                < s.get("simulation_complete_distance")):
            if s.get("simulation_current_distance") < 0:
                # "-1" -> simulation is finished
                updated_distance = s.get("simulation_complete_distance")
            else:
                time_step = 1.0 / s.get("drill_progress_max_fps")
                feedrate = toolpath.toolpath_settings.get_tool_settings(
                        )["feedrate"]
                distance_step = s.get("simulation_speed_factor") * \
                        time_step * feedrate / 60
                updated_distance = min(distance_step + \
                        s.get("simulation_current_distance"),
                        s.get("simulation_complete_distance"))
            if updated_distance != s.get("simulation_current_distance"):
                s.set("simulation_current_distance", updated_distance)
                moves = toolpath.get_moves(safety_height=safety_height,
                        max_movement=updated_distance)
                s.set("simulation_toolpath_moves", moves)
                if moves:
                    self.cutter.moveto(moves[-1][0])
                self.update_view()
        progress_value_percent = 100.0 * s.get("simulation_current_distance") \
                / s.get("simulation_complete_distance")
        self.gui.get_object("SimulationProgressTimelineValue").set_value(
                progress_value_percent)
        return True

    def show_toolpath_simulation(self, toolpath=None):
        # disable the main controls
        self.toggle_tabs_for_simulation(False)
        # show the simulation controls
        self.simulation_window.show()
        # start the simulation
        self.core.set("show_simulation", True)
        time_step = int(1000 / self.core.get("drill_progress_max_fps"))
        # update the toolpath simulation repeatedly
        gobject.timeout_add(time_step, self.update_toolpath_simulation)

    def update_toolpath_simulation_ode(self, widget=None, toolpath=None):
        import pycam.Simulation.ODEBlocks as ODEBlocks
        # get the currently selected toolpath, if none is give
        if toolpath is None:
            toolpath_index = self._treeview_get_active_index(self.toolpath_table, self.toolpath)
            if toolpath_index is None:
                return
            else:
                toolpath = self.toolpath[toolpath_index]
        paths = toolpath.get_paths()
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

