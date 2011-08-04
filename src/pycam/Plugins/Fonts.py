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

import os
import StringIO
# imported later (on demand)
#import gtk

import pycam.Plugins
import pycam.Utils.FontCache
from pycam.Utils.locations import get_font_dir
from pycam.Geometry.Letters import TEXT_ALIGN_LEFT, TEXT_ALIGN_CENTER, \
        TEXT_ALIGN_RIGHT


class Fonts(pycam.Plugins.PluginBase):

    UI_FILE = "fonts.ui"
    DEPENDS = ["Clipboard"]
    CATEGORIES = ["Fonts"]

    def setup(self):
        self._fonts_cache = pycam.Utils.FontCache.FontCache(get_font_dir(),
                core=self.core)
        self.core.add_item("fonts", lambda: self._fonts_cache)
        # "font dialog" window
        if self.gui:
            import gtk
            self._gtk = gtk
            self.font_dialog_window = self.gui.get_object("FontDialog")
            self.font_dialog_window.connect("delete-event",
                    self.toggle_font_dialog_window, False)
            self.font_dialog_window.connect("destroy",
                    self.toggle_font_dialog_window, False)
            self.gui.get_object("FontDialogCancel").connect("clicked",
                    self.toggle_font_dialog_window, False)
            self.gui.get_object("FontDialogApply").connect("clicked",
                    self.import_from_font_dialog)
            self.gui.get_object("FontDialogSave").connect("clicked",
                    self.export_from_font_dialog)
            self.gui.get_object("FontDialogCopy").connect("clicked",
                    self.copy_font_dialog_to_clipboard)
            self.gui.get_object("FontDialogInputBuffer").connect("changed",
                    self.update_font_dialog_preview)
            self.gui.get_object("FontDialogPreview").connect("configure_event",
                    self.update_font_dialog_preview)
            self.gui.get_object("FontDialogPreview").connect("expose_event",
                    self.update_font_dialog_preview)
            for objname in ("FontSideSkewValue", "FontCharacterSpacingValue",
                    "FontLineSpacingValue"):
                obj = self.gui.get_object(objname)
                # set default value before connecting the change-handler
                if objname != "FontSideSkewValue":
                    obj.set_value(1.0)
                obj.connect("value-changed",
                        self.update_font_dialog_preview)
            for objname in ("FontTextAlignLeft", "FontTextAlignCenter",
                    "FontTextAlignRight"):
                self.gui.get_object(objname).connect("toggled",
                        self.update_font_dialog_preview)
            # use global key accel map
            self.font_dialog_window.add_accel_group(self.core.get("gtk-accel-group"))
            font_action = self.gui.get_object("ShowFontDialog")
            self.register_gtk_accelerator("fonts", font_action,
                    "<Control><Shift>t", "ShowFontDialog")
            font_action.connect("activate", self.toggle_font_dialog_window)
            self.core.register_ui("edit_menu", "ShowFontDialogSeparator",
                    None, 55)
            self.core.register_ui("edit_menu", "ShowFontDialog", font_action,
                    60)
            # store window position
            self._font_dialog_window_visible = False
            self._font_dialog_window_position = None
            self.font_selector = None
        return True

    def teardown(self):
        self.core.add_item("fonts", None)
        if self.gui:
            font_toggle = self.gui.get_object("ShowFontDialog")
            self.core.unregister_ui("edit_menu", font_toggle)
            self.unregister_gtk_accelerator("fonts", font_toggle)

    def toggle_font_dialog_window(self, widget=None, event=None, state=None):
        # only "delete-event" uses four arguments
        # TODO: unify all these "toggle" functions for different windows into one single function (including storing the position)
        if state is None:
            state = event
        if state is None:
            state = not self._font_dialog_window_visible
        if state:
            if self.font_selector is None:
                # create it manually to ease access
                font_selector = self._gtk.combo_box_new_text()
                self.gui.get_object("FontSelectionBox").pack_start(
                        font_selector, expand=False, fill=False)
                sorted_keys = list(self._fonts_cache.get_font_names())
                sorted_keys.sort(key=lambda x: x.upper())
                for name in sorted_keys:
                    font_selector.append_text(name)
                if sorted_keys:
                    font_selector.set_active(0)
                else:
                    self.log.warn("No single-line fonts found!")
                font_selector.connect("changed",
                        self.update_font_dialog_preview)
                font_selector.show()
                self.font_selector = font_selector
            if len(self._fonts_cache) > 0:
                # show the dialog only if fonts are available
                if self._font_dialog_window_position:
                    self.font_dialog_window.move(
                            *self._font_dialog_window_position)
                self.font_dialog_window.show()
                self._font_dialog_window_visible = True
            else:
                self.log.error("No fonts were found on your system. " \
                        + "Please check the Log Window for details.")
        else:
            self._font_dialog_window_position = \
                    self.font_dialog_window.get_position()
            self.font_dialog_window.hide()
            self._font_dialog_window_visible = False
        # don't close the window - just hide it (for "delete-event")
        return True

    def get_font_dialog_text_rendered(self):
        input_field = self.gui.get_object("FontDialogInput")
        text_buffer = input_field.get_buffer()
        text = text_buffer.get_text(text_buffer.get_start_iter(),
                text_buffer.get_end_iter())
        text = unicode(text)
        if text:
            skew = self.gui.get_object("FontSideSkewValue").get_value()
            line_space = self.gui.get_object("FontLineSpacingValue").get_value()
            pitch = self.gui.get_object("FontCharacterSpacingValue").get_value()
            # get the active align setting
            for objname, value, justification in (
                    ("FontTextAlignLeft", TEXT_ALIGN_LEFT, self._gtk.JUSTIFY_LEFT),
                    ("FontTextAlignCenter", TEXT_ALIGN_CENTER, self._gtk.JUSTIFY_CENTER),
                    ("FontTextAlignRight", TEXT_ALIGN_RIGHT, self._gtk.JUSTIFY_RIGHT)):
                obj = self.gui.get_object(objname)
                if obj.get_active():
                    align = value
                    input_field.set_justification(justification)
            font_name = self.font_selector.get_active_text()
            charset = self._fonts_cache.get_font(font_name)
            return charset.render(text, skew=skew, line_spacing=line_space,
                    pitch=pitch, align=align)
        else:
            # empty text
            return None

    def import_from_font_dialog(self, widget=None):
        self.core.get("load_model")(self.get_font_dialog_text_rendered())
        self.toggle_font_dialog_window()

    def export_from_font_dialog(self, widget=None):
        text_model = self.get_font_dialog_text_rendered()
        if text_model and (not text_model.maxx is None):
            self.save_model(model=text_model, store_filename=False)

    def copy_font_dialog_to_clipboard(self, widget=None):
        text_model = self.get_font_dialog_text_rendered()
        if text_model and (not text_model.maxx is None):
            text_buffer = StringIO.StringIO()
            # TODO: add "comment=get_meta_data()"
            text_model.export(unit=self.core.get("unit")).write(text_buffer)
            text_buffer.seek(0)
            text = text_buffer.read()
            self.core.get("clipboard-set")(text,
                    targets="svg")

    def update_font_dialog_preview(self, widget=None, event=None):
        if not self.font_selector:
            # not initialized
            return
        if len(self._fonts_cache) == 0:
            # empty
            return
        font_name = self.font_selector.get_active_text()
        font = self._fonts_cache.get_font(font_name)
        self.gui.get_object("FontAuthorText").set_label(
                os.linesep.join(font.get_authors()))
        preview_widget = self.gui.get_object("FontDialogPreview")
        final_drawing_area = preview_widget.window
        text_model = self.get_font_dialog_text_rendered()
        # always clean the background
        x, y, width, height = preview_widget.get_allocation()
        drawing_area = self._gtk.gdk.Pixmap(final_drawing_area, width, height)
        drawing_area.draw_rectangle(preview_widget.get_style().white_gc, True,
                0, 0, width, height)
        # carefully check if there are lines in the rendered text
        if text_model and (not text_model.maxx is None) and \
                (text_model.maxx > text_model.minx):
            # leave a small border around the preview
            border = 3
            x_fac = (width - 1 - 2 * border) / \
                    (text_model.maxx - text_model.minx)
            y_fac = (height - 1 - 2 * border) / \
                    (text_model.maxy - text_model.miny)
            factor = min(x_fac, y_fac)
            # vertically centered preview
            y_offset = int((height - 2 * border - \
                    factor * (text_model.maxy - text_model.miny)) // 2)
            gc = drawing_area.new_gc()
            if text_model.minx == 0:
                # left align
                get_virtual_x = lambda x: int(x * factor) + border
            elif text_model.maxx == 0:
                # right align
                get_virtual_x = lambda x: width + int(x * factor) - 1 - border
            else:
                # center align
                get_virtual_x = lambda x: \
                        int(width / 2.0 + x * factor) - 1 - border
            get_virtual_y = lambda y: -y_offset + \
                    height - int((y - text_model.miny) * factor) - 1 - border
            for polygon in text_model.get_polygons():
                draw_points = []
                points = polygon.get_points()
                if polygon.is_closed:
                    # add the first point again to close the polygon
                    points.append(points[0])
                for point in points:
                    x = get_virtual_x(point.x)
                    y = get_virtual_y(point.y)
                    draw_points.append((x, y))
                drawing_area.draw_lines(gc, draw_points)
        final_gc = final_drawing_area.new_gc()
        final_drawing_area.draw_drawable(final_gc, drawing_area, 0, 0, 0, 0,
                -1, -1)

