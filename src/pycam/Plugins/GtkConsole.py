# -*- coding: utf-8 -*-
"""
$Id$

Copyright 2012 Lars Kruse <devel@sumpfralle.de>

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
import sys
import code
# gtk is imported later
#import gtk
import StringIO

import pycam.Plugins
import pycam.Utils.log

_log = pycam.Utils.log.get_logger()


class GtkConsole(pycam.Plugins.PluginBase):

    UI_FILE = "gtk_console.ui"
    DEPENDS = ["Clipboard"]
    CATEGORIES = ["System"]

    # sys.ps1 and sys.ps2 don't seem to be available outside of the shell
    PROMPT_PS1 = ">>> "
    PROMPT_PS2 = "... "

    def setup(self):
        self._history = []
        self._history_position = None
        if self.gui:
            import gtk
            self._gtk = gtk
            self._console = code.InteractiveConsole(
                    locals=self.core.get_namespace(), filename="PyCAM")
            self._console_output = StringIO.StringIO()
            # TODO: clean up this stdin/stdout mess (maybe subclass "sys"?)
            code.sys.stdout = self._console_output
            code.sys.stdin = StringIO.StringIO()
            self._console_buffer = self.gui.get_object("ConsoleViewBuffer")
            def console_write(data):
                self._console_buffer.insert(
                        self._console_buffer.get_end_iter(), data)
                self._console_buffer.place_cursor(
                        self._console_buffer.get_end_iter())
            self._console.write  = console_write
            self._clear_console()
            console_action = self.gui.get_object("ToggleConsoleWindow")
            self.register_gtk_accelerator("console", console_action, None,
                    "ToggleConsoleWindow")
            self.core.register_ui("view_menu", "ToggleConsoleWindow",
                    console_action, 90)
            self._window = self.gui.get_object("ConsoleDialog")
            self._window_position = None
            self._gtk_handlers = []
            hide_window = lambda *args: self._toggle_window(value=False)
            for objname, signal, func in (
                    ("ConsoleExecuteButton", "clicked", self._execute_command),
                    ("CommandInput", "activate", self._execute_command),
                    ("CopyConsoleButton", "clicked", self._copy_to_clipboard),
                    ("WipeConsoleButton", "clicked", self._clear_console),
                    ("CommandInput", "key-press-event", self._scroll_history),
                    ("ToggleConsoleWindow", "toggled", self._toggle_window),
                    ("CloseConsoleButton", "clicked", hide_window),
                    ("ConsoleDialog", "delete-event", hide_window),
                    ("ConsoleDialog", "destroy", hide_window)):
                self._gtk_handlers.append((self.gui.get_object(objname),
                        signal, func))
            self.register_gtk_handlers(self._gtk_handlers)
        return True

    def teardown(self):
        if self.gui:
            self.unregister_gtk_handlers(self._gtk_handlers)

    def _hide_window(self, widget=None, event=None):
        self.gui.get_object("ConsoleDialog").hide()
        # don't close window (for "destroy" event)
        return True

    def _clear_console(self, widget=None):
        start, end = self._console_buffer.get_bounds()
        self._console_buffer.delete(start, end)
        self._console.write(self.PROMPT_PS1)

    def _execute_command(self, widget=None):
        input_control = self.gui.get_object("CommandInput")
        text = input_control.get_text()
        if not text:
            return
        input_control.set_text("")
        # add the command to the console window
        self._console.write(text + os.linesep)
        # execute command - check if it needs more input
        if not self._console.push(text):
            # append result to console view
            self._console_output.seek(0)
            for line in self._console_output.readlines():
                self._console.write(line)
            # scroll down console view to the end of the buffer
            view = self.gui.get_object("ConsoleView")
            view.scroll_mark_onscreen(self._console_buffer.get_insert())
            # clear the buffer
            self._console_output.truncate(0)
            # show the prompt again
            self._console.write(self.PROMPT_PS1)
        else:
            # show the "waiting for more" prompt
            self._console.write(self.PROMPT_PS2)
        # add to history
        if not self._history or (text != self._history[-1]):
            self._history.append(text)
        self._history_position = None

    def _copy_to_clipboard(self, widget=None):
        start, end = self._console_buffer.get_bounds()
        content = self._console_buffer.get_text(start, end)
        self.core.get("clipboard-set")(content)

    def _toggle_window(self, widget=None, value=None, action=None):
        toggle_checkbox = self.gui.get_object("ToggleConsoleWindow")
        checkbox_state = toggle_checkbox.get_active()
        if value is None:
            new_state = checkbox_state
        elif action is None:
            new_state = value
        else:
            new_state = action
        if new_state:
            if self._window_position:
                self._window.move(*self._window_position)
            self._window.show()
        else:
            self._window_position = self._window.get_position()
            self._window.hide()
        toggle_checkbox.set_active(new_state)
        return True

    def _scroll_history(self, widget=None, event=None):
        if event is None:
            return False
        try:
            keyval = getattr(event, "keyval")
            get_state = getattr(event, "get_state")
        except AttributeError:
            return False
        if get_state():
            # ignore, if any modifier is pressed
            return False
        input_control = self.gui.get_object("CommandInput")
        if (keyval == self._gtk.keysyms.Up):
            if self._history_position is None:
                # store the current (new) line for later
                self._history_lastline_backup = input_control.get_text()
                # start with the last item
                self._history_position = len(self._history) - 1
            elif self._history_position > 0:
                self._history_position -= 1
            else:
                # invalid -> no change
                return True
        elif (keyval == self._gtk.keysyms.Down):
            if self._history_position is None:
                return True
            self._history_position += 1
        else:
            # all other keys: ignore
            return False
        if self._history_position >= len(self._history):
            input_control.set_text(self._history_lastline_backup)
            # make sure that the backup can be stored again
            self._history_position = None
        else:
            input_control.set_text(self._history[self._history_position])
        # move the cursor to the end of the new text
        input_control.set_position(0)
        input_control.grab_focus()
        return True

