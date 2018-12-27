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

from http import HTTPStatus
import http.server
import io
import os
import random
import threading

from pycam.Utils.locations import retrieve_cached_download
import pycam.Utils.log


_log = pycam.Utils.log.get_logger()

X3DOM_JS_URL = "http://x3dom.org/release/x3dom.js"
HTML_DOCUMENTS = {
    "x3d_scene": b"""
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
    <head>
        <meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
        <script type="text/javascript" src="x3dom.js"></script>
    </head>
<body>
<x3d width='100%' height='100%'><scene><inline url="scene.x3d" /></scene></x3d>
</body></html>""",
    "x_ite": b"""
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
    <head>
        <meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
        <link rel="stylesheet" href="http://code.create3000.de/x_ite/latest/dist/x_ite.css" type="text/css" media="all"/>
        <script type="text/javascript" src="http://code.create3000.de/x_ite/latest/dist/x_ite.min.js"></script>
        <script type="text/javascript" src="https://cdn.rawgit.com/andreasplesch/x_ite_dom/v1.0/src/x_ite_dom.js"></script>
        <style>
            X3DCanvas {
                width: 550px;
                height: 350px;
            }
        </style>
    </head>
<body>
<script>
    setTimeout(function() { document.getElementById('view_center').setAttribute('set_bind','true'); }, 4000);
</script>
<X3DCanvas><x3d><scene><inline url='"/preview/x3d/scene.x3d"' /></scene></x3d></X3DCanvas>
</body></html>""",
}


class BasePycamHandler(http.server.SimpleHTTPRequestHandler):

    def send_head(self):
        """ prepare responses for path-based requests

        Every child implementing a handler should overwrite this method, handle its own paths
        and (in case of no match) call its parent's method.
        """
        self.send_response(HTTPStatus.NOT_FOUND)
        self.end_headers()
        return io.BytesIO()

    def _send_content_data(self, data, content_type="text/html", encoding="utf8"):
        """ deliver bytes in response to a request """
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-type", "{}; charset={}".format(content_type, encoding))
        if hasattr(data, "read"):
            # handle file-like objects
            self.send_header("Content-Length", str(data.seek(0, 2)))
            out_file = data
        else:
            # handle plain bytes
            self.send_header("Content-Length", str(len(data)))
            out_file = io.BytesIO()
            out_file.write(data)
        self.end_headers()
        out_file.seek(0)
        return out_file

    def _send_content_file(self, filename, content_type="text/html", encoding="utf8"):
        """ deliver the content of a file in response to a request """
        size = os.path.getsize(filename)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-type", "{}; charset={}".format(content_type, encoding))
        self.send_header("Content-Length", str(size))
        self.end_headers()
        return open(filename, "rb")

    def copyfile(self, source, outputfile):
        """ hide ConnectionResetError from the log output """
        try:
            return super().copyfile(source, outputfile)
        except (ConnectionResetError, BrokenPipeError):
            return None

    def log_message(self, message, *args):
        # out parent's implementation sends all messages to stderr - we redirect it
        _log.debug("Internal HTTP server: {}".format(message), *args)


def get_x3d_handler(get_scene_bytes):

    class X3DHandler(BasePycamHandler):

        DOWNLOAD_MAP = {
            "/preview/x3d/x3dom.js": X3DOM_JS_URL,
            "/preview/x3d/x_ite.css": "http://code.create3000.de/x_ite/latest/dist/x_ite.css",
            "/preview/x3d/x_ite.min.js": "http://code.create3000.de/x_ite/latest/dist/x_ite.min.js",
            "/preview/x3d/x_ite_dom.js": "https://cdn.rawgit.com/andreasplesch/x_ite_dom/v1.0/src/x_ite_dom.js",
        }

        # class variable for tracking warning messages
        emitted_download_warning = False

        def send_head(self):
            try:
                if self.path == "/preview/x3d/scene.html":
                    return self._send_content_data(HTML_DOCUMENTS["x_ite"].strip())
                elif self.path in self.DOWNLOAD_MAP:
                    download_url = self.DOWNLOAD_MAP[self.path]
                    base_filename = os.path.basename(self.path)
                    try:
                        filename = retrieve_cached_download(base_filename, download_url)
                    except OSError as exc:
                        message = ("Failed to download or store external library (%s) for 3D "
                                   "visualization: %s".format(download_url, exc))
                        if not self.emitted_download_warning:
                            # emit this warning only once
                            self.emitted_download_warning = True
                            _log.warning(message)
                        self.send_error(HTTPStatus.BAD_GATEWAY, message=message)
                        return
                    else:
                        return self._send_content_file(filename)
                elif self.path == "/preview/x3d/scene.x3d":
                    return self._send_content_data(get_scene_bytes(), content_type="model/x3d+xml")
                else:
                    return super().send_head()
            except (ConnectionResetError, BrokenPipeError):
                # the client disconnected before everything was transmitted
                pass

    return X3DHandler


class HTTPServer:

    def __init__(self, address, handler):
        self.address = address
        self.handler = handler
        # bind immediately - otherwise we do not receive errors
        self.httpd = http.server.ThreadingHTTPServer(address, handler)
        _log.info("Bound local http server to %s:%d",
                  "[{}]".format(address[0]) if ":" in address[0] else address[0], address[1])

    def run_threaded(self):
        self.thread = threading.Thread(target=self.httpd.serve_forever, name="pycam-httpd")
        self.thread.start()

    def shutdown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.httpd = None
        self.thread.join()
        self.thread = None

    def get_url(self, path="/"):
        return "http://{}:{}/{}".format(self.address[0], self.address[1], path.lstrip("/"))

    @classmethod
    def create_with_random_port(cls, handler, host="localhost", min_port=10000, max_port=16383,
                                max_attempts=10):
        for attempt in range(max_attempts):
            port = random.randint(min_port, max_port)
            try:
                return cls((host, port), handler)
            except (PermissionError, OSError) as exc:
                _log.warning("Failed to bind local HTTP server to port %d: %s", port, exc)
        else:
            _log.error("Finally failed to bind local HTTP server to random port")
            return None

    def __str__(self):
        return "HTTPServer(address={}, handler={})".format(self.address, self.handler)


if __name__ == "__main__":
    import time

    class TestHandler(BasePycamHandler):
        def send_head(self):
            if self.path == "/":
                return self._send_content_data(b"foo")
            else:
                return super().send_head()

    threaded = HTTPServer.create_with_random_port(TestHandler)
    print("Running server:", threaded)
    threaded.run_threaded()
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        threaded.shutdown()
