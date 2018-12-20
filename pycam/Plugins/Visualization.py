"""
Copyright 2018 Lars Kruse <devel@sumpfralle.de>

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


class Visualization(pycam.Plugins.PluginBase):

    UI_FILE = "visualization.ui"
    CATEGORIES = {"Visualization"}

    # TODO: to be implemented later
    VIEWS = {"reset": None, "top": None, "bottom": None, "left": None, "right": None,
             "front": None, "back": None}

    def setup(self):
        if self.gui:
            self._gtk_handlers = []
            self._color_settings = {}
            self.window = self.gui.get_object("VisualizationWindow")
            self.window.insert_action_group(self.core.get("gtk_action_group_prefix"),
                                            self.core.get("gtk_action_group"))
            drag_n_drop_func = self.core.get("configure-drag-drop-func")
            if drag_n_drop_func:
                drag_n_drop_func(self.window)
            self.is_visible = False
            self._position = [200, 200]
            box = self.gui.get_object("VisualizationPrefTab")
            self.core.register_ui("preferences", "Visualization", box, 40)
            # frames per second
            skip_obj = self.gui.get_object("DrillProgressFrameSkipControl")
            self.core.add_item("tool_progress_max_fps", skip_obj.get_value, skip_obj.set_value)
            # info bar above the model view
            detail_box = self.gui.get_object("InfoBox")

            def clear_window():
                for child in detail_box.get_children():
                    detail_box.remove(child)

            def add_widget_to_window(item, name):
                if len(detail_box.get_children()) > 0:
                    sep = self._gtk.HSeparator()
                    detail_box.pack_start(sep, fill=True, expand=True, padding=0)
                    sep.show()
                detail_box.pack_start(item, fill=True, expand=True, padding=0)
                item.show()

            self.core.register_ui_section("visualization_window", add_widget_to_window,
                                          clear_window)
            self.core.register_ui("visualization_window", "Views",
                                  self.gui.get_object("ViewControls"), weight=0)
            # color box
            color_frame = self.gui.get_object("ColorPrefTab")
            color_frame.unparent()
            self.core.register_ui("preferences", "Colors", color_frame, 30)
            self.core.set("register_color", self.register_color_setting)
            self.core.set("unregister_color", self.unregister_color_setting)
            for name, label, weight in (("color_background", "Background", 10),
                                        ("color_material", "Material", 80)):
                self.core.get("register_color")(name, label, weight)
            # display items
            items_frame = self.gui.get_object("DisplayItemsPrefTab")
            items_frame.unparent()
            self._display_items = {}
            self.core.register_ui("preferences", "Display Items", items_frame, 20)
            self.core.set("register_display_item", self.register_display_item)
            self.core.set("unregister_display_item", self.unregister_display_item)
            # visual and general settings
            self.core.get("register_display_item")("show_directions", "Show Directions", 80)
            # toggle window state
            toggle_3d = self.gui.get_object("ToggleVisualization")
            self._gtk_handlers.append((toggle_3d, "toggled", self.toggle_3d_view))
            self.register_gtk_accelerator("visualization", toggle_3d, "<Control><Shift>v",
                                          "ToggleVisualization")
            self.core.register_ui("view_menu", "View3D", toggle_3d, -20)
            self.mouse = {"start_pos": None, "button": None, "event_timestamp": 0,
                          "last_timestamp": 0, "pressed_pos": None, "pressed_timestamp": 0,
                          "pressed_button": None}
            self.window.connect("delete-event", self.destroy)
            self.window.set_default_size(560, 400)
            for obj_name, view in (("ResetView", "reset"),
                                   ("LeftView", "left"),
                                   ("RightView", "right"),
                                   ("FrontView", "front"),
                                   ("BackView", "back"),
                                   ("TopView", "top"),
                                   ("BottomView", "bottom")):
                self._gtk_handlers.append((self.gui.get_object(obj_name), "clicked",
                                           self.rotate_view, self.VIEWS[view]))
            self._event_handlers = (("visual-item-updated", self.update_view),
                                    ("visualization-state-changed", self._update_widgets),
                                    ("visual-item-updated", "visualization-updated"))
            # handlers
            self.register_gtk_handlers(self._gtk_handlers)
            self.register_event_handlers(self._event_handlers)
            toggle_3d.set_active(True)
            # refresh display
            self.core.emit_event("visual-item-updated")

            def get_get_set_functions(name):
                get_func = lambda: self.core.get(name)
                set_func = lambda value: self.core.set(name, value)
                return get_func, set_func

            for name in ("view_light", "view_shadow", "view_polygon", "view_perspective",
                         "tool_progress_max_fps"):
                self.register_state_item("settings/view/visualization/%s" % name,
                                         *get_get_set_functions(name))
        return True

    def teardown(self):
        if self.gui:
            toggle_3d = self.gui.get_object("ToggleVisualization")
            # hide the window
            toggle_3d.set_active(False)
            self.core.unregister_ui("view_menu", toggle_3d)
            self.unregister_gtk_accelerator("visualization", toggle_3d)
            for name in ("color_background", "color_tool", "color_material"):
                self.core.get("unregister_color")(name)
            self.core.get("unregister_display_item")("show_directions")
            self.unregister_gtk_handlers(self._gtk_handlers)
            self.unregister_event_handlers(self._event_handlers)
            self.core.unregister_ui("preferences", self.gui.get_object("DisplayItemsPrefTab"))
            self.core.unregister_ui("preferences", self.gui.get_object("VisualizationPrefTab"))
            self.core.unregister_ui("visualization_window", self.gui.get_object("ViewControls"))
            self.core.unregister_ui("preferences", self.gui.get_object("ColorPrefTab"))
            self.core.unregister_ui_section("visualization_window")
        self.clear_state_items()

    def update_view(self, widget=None, data=None):
        if self.is_visible:
            self.trigger_rendering()

    def _update_widgets(self):
        self.unregister_gtk_handlers(self._gtk_handlers)
        self.gui.get_object("ToggleVisualization").set_active(self.is_visible)
        self.register_gtk_handlers(self._gtk_handlers)

    def register_display_item(self, name, label, weight=100):
        if name in self._display_items:
            self.log.debug("Tried to register display item '%s' twice", name)
            return
        # create an action and three derived items:
        #  - a checkbox for the preferences window
        #  - a tool item for the drop-down list in the 3D window
        #  - a menu item for the context menu in the 3D window
        # the string value will be interpreted by the callback as the most recently updated widget
        action_name = ".".join((self.core.get("gtk_action_group_prefix"), name))
        action = self._gio.SimpleAction.new_stateful(name, self._glib.VariantType.new("s"),
                                                     self._glib.Variant.new_string("0"))
        widgets = []
        for index, item in enumerate((self._gtk.CheckButton(),
                                      self._gtk.ToggleToolButton(),
                                      self._gtk.CheckMenuItem())):
            item.insert_action_group(self.core.get("gtk_action_group_prefix"),
                                     self.core.get("gtk_action_group"))
            item.set_label(label)
            item.set_action_target_value(self._glib.Variant.new_string(str(index)))
            item.set_action_name(action_name)
            # The "target value" (the stringified widget index) is used by GTK for guessing the
            # sensitivity of a control.  This approach differs from ours - we ignore it.
            item.set_sensitive(True)
            widgets.append(item)
        self._display_items[name] = {"name": name, "label": label, "weight": weight,
                                     "widgets": widgets, "action": action}

        def synchronize_widgets(action, widget_index_variant, widgets=widgets, is_blocked=[],
                                name=name):
            """ copy the state of the most recently changed ("activated") control to the others

            widget_index_variant: GLib.Variant containing the stringified index of the changed
                widget (0, 1 or 2) - based on the widgets list
            widgets: the three associated widgets
            is_blocked: we need to avoid pseudo-recursive calls of this function after every
                programmatic change of a control
            """
            widget_index = int(widget_index_variant.get_string())
            if not is_blocked:
                is_blocked.append(True)
                current_widget = widgets[widget_index]
                current_value = current_widget.get_active()
                for index, widget in enumerate(widgets):
                    if widget_index != index:
                        if hasattr(widget, "set_active"):
                            widget.set_active(current_value)
                        else:
                            widget.set_state(current_value)
                    widget.set_sensitive(True)
                self.core.set(name, current_value)
                self.core.emit_event("visual-item-updated")
                is_blocked.clear()

        action.connect("activate", synchronize_widgets)
        self.core.get("gtk_action_group").add_action(action)
        self.core.add_item(name, set_func=widgets[0].set_active)
        # add this item to the state handler
        self.register_state_item("settings/view/items/%s" % name,
                                 widgets[0].get_active, widgets[0].set_active)
        # synchronize the widgets
        synchronize_widgets(None, self._glib.Variant.new_string("0"))
        self._rebuild_display_items()

    def unregister_display_item(self, name):
        if name not in self._display_items:
            self.log.info("Failed to unregister unknown display item: %s", name)
            return
        first_widget = self._display_items[name]["widgets"][0]
        self.unregister_state_item("settings/view/items/%s" % name,
                                   first_widget.get_active, first_widget.set_active)
        action_name = ".".join((self.core.get("gtk_action_group_prefix"), name))
        self.core.get("gtk_action_group").remove(action_name)
        del self._display_items[name]
        self._rebuild_display_items()

    def _rebuild_display_items(self):
        pref_box = self.gui.get_object("PreferencesVisibleItemsBox")
        toolbar = self.gui.get_object("ViewItems")
        parents = (pref_box, toolbar)
        for parent in parents:
            for child in parent.get_children():
                parent.remove(child)
        items = list(self._display_items.values())
        items.sort(key=lambda item: item["weight"])
        for item in items:
            pref_box.pack_start(item["widgets"][0], expand=True, fill=True, padding=0)
            toolbar.add(item["widgets"][1])
        for parent in parents:
            parent.show_all()
            parent.insert_action_group(self.core.get("gtk_action_group_prefix"),
                                       self.core.get("gtk_action_group"))

    def register_color_setting(self, name, label, weight=100):
        if name in self._color_settings:
            self.log.debug("Tried to register color '%s' twice", name)
            return

        def get_color_wrapper(obj):
            def gtk_color_to_dict():
                color_components = obj.get_rgba()
                return {"red": color_components.red,
                        "green": color_components.green,
                        "blue": color_components.blue,
                        "alpha": color_components.alpha}
            return gtk_color_to_dict

        def set_color_wrapper(obj):
            def set_gtk_color_by_dict(color):
                obj.set_rgba(
                    self._gdk.RGBA(color["red"], color["green"], color["blue"], color["alpha"]))
            return set_gtk_color_by_dict

        widget = self._gtk.ColorButton()
        widget.set_use_alpha(True)
        wrappers = (get_color_wrapper(widget), set_color_wrapper(widget))
        self._color_settings[name] = {"name": name, "label": label, "weight": weight,
                                      "widget": widget, "wrappers": wrappers}
        widget.connect("color-set", lambda widget: self.core.emit_event("visual-item-updated"))
        self.core.add_item(name, *wrappers)
        self.register_state_item("settings/view/colors/%s" % name, *wrappers)
        self._rebuild_color_settings()

    def unregister_color_setting(self, name):
        if name not in self._color_settings:
            self.log.debug("Failed to unregister unknown color item: %s", name)
            return
        wrappers = self._color_settings[name]["wrappers"]
        self.unregister_state_item("settings/view/colors/%s" % name, *wrappers)
        del self._color_settings[name]
        self._rebuild_color_settings()

    def _rebuild_color_settings(self):
        color_table = self.gui.get_object("ColorTable")
        for child in color_table.get_children():
            color_table.remove(child)
        items = list(self._color_settings.values())
        items.sort(key=lambda item: item["weight"])
        for index, item in enumerate(items):
            label = self._gtk.Label("%s:" % item["label"])
            label.set_alignment(0.0, 0.5)
            color_table.attach(label, 0, index, 1, 1)
            color_table.attach(item["widget"], 1, index, 1, 1)
        color_table.show_all()

    def toggle_3d_view(self, widget=None, value=None):
        current_state = self.is_visible
        if value is None:
            new_state = not current_state
        else:
            new_state = value
        if new_state == current_state:
            return
        elif new_state:
            if self.is_visible:
                self.reset_view()
            else:
                # the window is just hidden
                self.show()
        else:
            self.hide()

    def show(self):
        self.is_visible = True
        self.window.move(*self._position)
        self.window.show()

    def hide(self):
        self.is_visible = False
        self._position = self.window.get_position()
        self.window.hide()

    def destroy(self, widget=None, data=None):
        self.hide()
        self.core.emit_event("visualization-state-changed")
        # don't close the window
        return True

    def rotate_view(self, widget=None, view=None):
        if view:
            self._last_view = view.copy()
        # TODO: set view
        self.trigger_rendering()

    def reset_view(self):
        self.rotate_view(view=None)
        self.trigger_rendering()

    def _resize_window(self, widget, width, height, data=None):
        self.trigger_rendering()

    def trigger_rendering(self):
        # TODO: trigger a rendering as soon as final visualization object is selected
        pass
