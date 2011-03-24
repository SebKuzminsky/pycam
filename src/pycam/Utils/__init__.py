# -*- coding: utf-8 -*-
"""
$Id$

Copyright 2008 Lode Leroy

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

__all__ = ["iterators", "polynomials", "ProgressCounter", "threading",
        "get_platform", "get_external_program_location", "URIHandler",
        "PLATFORM_WINDOWS", "PLATFORM_MACOS", "PLATFORM_LINUX",
        "PLATFORM_UNKNOWN"]

import sys
import os
import socket
import urllib
import urlparse
# this is imported below on demand
#import win32com
#import win32api

PLATFORM_LINUX = 0
PLATFORM_WINDOWS = 1
PLATFORM_MACOS = 2
PLATFORM_UNKNOWN = 3

# setproctitle is (optionally) imported
try:
    from setproctitle import setproctitle
except ImportError:
    # silently ignore name change requests
    setproctitle = lambda name: None


def get_platform():
    if hasattr(sys, "getwindowsversion"):
        return PLATFORM_WINDOWS
    elif sys.platform == "darwin":
        return PLATFORM_MACOS
    elif sys.platform.startswith("linux"):
        return PLATFORM_LINUX
    else:
        return PLATFORM_UNKNOWN


class URIHandler(object):

    DEFAULT_PREFIX = "file://"

    def __init__(self, location):
        self._uri = None
        self.set_location(location)

    def __str__(self):
        url = self._uri.geturl()
        if url.startswith(self.DEFAULT_PREFIX):
            return url[len(self.DEFAULT_PREFIX):]
        else:
            return url

    def set_location(self, location):
        if isinstance(location, URIHandler):
            self._uri = location._uri
        elif (get_platform() == PLATFORM_WINDOWS) and (location[1:3] == ":\\"):
            self._uri = urlparse.urlparse(self.DEFAULT_PREFIX + location)
        else:
            self._uri = urlparse.urlparse(location)
            if not self._uri.scheme:
                # always fill the "scheme" field - some functions expect this
                self._uri = urlparse.urlparse(self.DEFAULT_PREFIX + \
                        os.path.realpath(os.path.abspath(location)))

    def is_local(self):
        return bool(self and not self._uri.scheme or \
                (self._uri.scheme == "file"))

    def get_local_path(self):
        if self.is_local():
            print "LOCAL:", self._uri.path
            return self._uri.path
        else:
            return None

    def get_path(self):
        return self._uri.path

    def get_url(self):
        return self._uri.geturl()

    def open(self):
        if self.is_local():
            return open(self.get_local_path())
        else:
            return urllib.urlopen(self._uri.geturl())

    def retrieve_remote_file(uri, destination, callback=None):
        if callback:
            download_callback = lambda current_blocks, block_size, \
                num_of_blocks: callback()
        else:
            download_callback = None
        try:
            urllib.urlretrieve(uri, destination, download_callback)
            return True
        except IOError:
            return False

    def __eq__(self, other):
        if isinstance(other, basestring):
            return self == URIHandler(other)
        elif self.__class__ == other.__class__:
            if self.is_local() and other.is_local():
                return self._uri.path == other._uri.path
            else:
                return tuple(self) == tuple(other)
        else:
            return hash(self) == hash(other)

    def __ne__(self, other):
        return not self == other

    def __nonzero__(self):
        return self.get_url() != self.DEFAULT_PREFIX

    def exists(self):
        if not self:
            return False
        elif self.is_local():
            return os.path.exists(self._uri.path)
        else:
            try:
                handle = self.open()
                handle.close()
                return True
            except IOError:
                return False

    def is_writable(self):
        return bool(self.is_local() and os.path.isfile(self._uri.path) and \
                os.access(self._uri.path, os.W_OK))


def get_all_ips():
    """ try to get all IPs of this machine

    The resulting list of IPs contains non-local IPs first, followed by
    local IPs (starting with "127....").
    """
    result = []
    def get_ips_of_name(name):
        try:
            ips = socket.gethostbyname_ex(name)
            if len(ips) == 3:
                return ips[2]
        except socket.gaierror:
            return []
    result.extend(get_ips_of_name(socket.gethostname()))
    result.extend(get_ips_of_name("localhost"))
    filtered_result = []
    for one_ip in result:
        if not one_ip in filtered_result:
            filtered_result.append(one_ip)
    def sort_ip_by_relevance(ip1, ip2):
        if ip1.startswith("127."):
            return 1
        if ip2.startswith("127."):
            return -1
        else:
            return cmp(ip1, ip2)
    # non-local IPs first
    filtered_result.sort(cmp=sort_ip_by_relevance)
    print filtered_result
    return filtered_result


def get_external_program_location(key):
    extensions = ["", ".exe"]
    potential_names = ["%s%s" % (key, ext) for ext in extensions]
    windows_program_directories = {'inkscape': ['Inkscape'],
            'pstoedit': ['pstoedit']}
    # check the windows path via win32api
    try:
        import win32api
        location = win32api.FindExecutable(key)[1]
        if location:
            return location
    except Exception:
        # Wildcard (non-system exiting) exeception to match "ImportError" and
        # "pywintypes.error" (for "not found").
        pass
    # go through the PATH environment variable
    if "PATH" in os.environ:
        path_env = os.environ["PATH"]
        for one_dir in path_env.split(os.pathsep):
            for basename in potential_names:
                location = os.path.join(one_dir, basename)
                if check_uri_exists(location):
                    return location
    # do a manual scan in the programs directory (only for windows)
    try:
        from win32com.shell import shellcon, shell            
        program_dir = shell.SHGetFolderPath(0, shellcon.CSIDL_PROGRAM_FILES,
                0, 0)
    except ImportError:
        # no other options for non-windows systems
        return None
    # scan the program directory
    for sub_dir in windows_program_directories[key]:
        for basename in potential_names:
            location = os.path.join(program_dir, sub_dir, basename)
            if check_uri_exists(location):
                return location
    # nothing found
    return None


class ProgressCounter:

    def __init__(self, max_value, update_callback):
        self.max_value = max_value
        self.current_value = 0
        self.update_callback = update_callback

    def increment(self, increment=1):
        self.current_value += increment
        return self.update()

    def update(self):
        if self.update_callback:
            # "True" means: "quit requested via GUI"
            return self.update_callback(percent=self.get_percent())
        else:
            return False

    def get_percent(self):
        return 100.0 * self.current_value / self.max_value

