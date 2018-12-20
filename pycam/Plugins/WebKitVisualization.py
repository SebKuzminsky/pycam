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

import os

import pycam.Plugins


class WebKitVisualization(pycam.Plugins.PluginBase):

    CATEGORIES = {"Visualization"}
    DEPENDS = {"Visualization"}

    def setup(self):
        try:
            import gi
            gi.require_version('WebKit2', '4.0')
            import gi.repository.WebKit2
            self._webkit = gi.repository.WebKit2
        except ImportError:
            self.log.warning("Failed to import WebKitGTK. You may either install it or abstain "
                             "from the embedded interactive 3D preview.")
            return False
        self.view = self._webkit.WebView()
        self.view_settings = self.view.get_settings()
        self.view_settings.set_allow_file_access_from_file_urls(True)
        self.view_settings.set_enable_write_console_messages_to_stdout(True)
        self.view_settings.set_enable_webgl(True)
        self.core.register_ui("visualization_window", "3D Preview", self.view, weight=70)
        self.view.set_size_request(400, 400)
        # TODO: deliver the data via a port or socket
        self.view.load_uri("file://{}/pycam-preview.html".format(os.getcwd()))
        self._event_handlers = [("visualization-updated", self.trigger_reload)]
        self.register_event_handlers(self._event_handlers)
        return True

    def teardown(self):
        self.unregister_event_handlers(self._event_handlers)
        self.core.unregister_ui("visualization_window", self.view)
        self.view.hide()
        self.view.try_close()
        del self.view

    def trigger_reload(self):
        self.view.get_context().clear_cache()
        self.view.reload()
