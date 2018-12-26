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
from pycam.Utils.httpserver import get_x3d_handler, HTTPServer


class WebKitVisualization(pycam.Plugins.PluginBase):

    CATEGORIES = {"Visualization"}
    DEPENDS = {"Visualization", "ExportX3D"}

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
        self.http_server = HTTPServer.create_with_random_port(
            get_x3d_handler(self.core.get("get_x3d_export")))
        if self.http_server is None:
            return False
        self.http_server.run_threaded()
        self.view = self._webkit.WebView()
        self.view_settings = self.view.get_settings()
        self.view_settings.set_enable_write_console_messages_to_stdout(True)
        self.view_settings.set_enable_webgl(True)
        self.core.register_ui("visualization_view", "3D Preview", self.view, weight=70)
        self.view.set_size_request(400, 400)
        # TODO: deliver the data via a port or socket
        self.view.load_uri(self.http_server.get_url("/preview/x3d/scene.html"))
        self._event_handlers = [("visualization-updated", self.trigger_reload)]
        self.register_event_handlers(self._event_handlers)
        return super().setup()

    def teardown(self):
        self.unregister_event_handlers(self._event_handlers)
        self.core.unregister_ui("visualization_view", self.view)
        self.http_server.shutdown()
        self.view.hide()
        self.view.try_close()
        del self.view
        super().teardown()

    def trigger_reload(self):
        self.view.get_context().clear_cache()
        self.view.reload()
