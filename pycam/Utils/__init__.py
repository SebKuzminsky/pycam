# -*- coding: utf-8 -*-
"""
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

import os
import re
import socket
import sys
import traceback
import urllib
try:
    # Python3
    from urllib.parse import urlparse
    from urllib.request import url2pathname
except ImportError:
    # Python2
    from urlparse import urlparse
    from urllib import url2pathname
# this is imported below on demand
# import win32com
# import win32api


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


def get_case_insensitive_file_pattern(pattern):
    """ Convert something like "*.svg" into "*.[sS][vV][gG]" - as it is
        required for GTK's FileFilter.
    """
    result = []
    char_match = re.compile(r"[a-zA-Z]")
    for char in pattern:
        if char_match.match(char):
            result.append("[%s%s]" % (char.lower(), char.upper()))
        else:
            result.append(char)
    return "".join(result)


def get_non_conflicting_name(template, conflicts, start=None, get_next_func=None):
    """ Find a string containing a number that is not in conflict with any of
        the given strings. A name template (containing "%d") is required.

        You may use non-numbers (strings, floats, ...) as well. In this case
        you need to override "start" and "get_next_func".

        @value template: a string template containing "%d" (e.g. "Object %d")
        @type template: basestr
        @value conflicts: a list of strings that need may not be used
        @type conflicts: list(basestr)
        @value start: optional initial value (default: len(conflicts) + 1)
        @type start: undefined
        @value get_next_func: function used for determining the next value to
            be tested. This function defaults to "lambda value: value + 1".
        @returns: a usable name that was not found in "conflicts"
        @rtype: basestr
    """
    if start is None:
        index = len(conflicts) + 1
    else:
        index = start
    if get_next_func is None:
        get_next_func = lambda current: current + 1
    while (template % index) in conflicts:
        index = get_next_func(index)
    return template % index


class URIHandler(object):

    DEFAULT_PREFIX = "file://"

    def __init__(self, location):
        self._uri = None
        self.set_location(location)

    def __str__(self):
        if self.is_local():
            return self.get_local_path()
        else:
            return self._uri.geturl()

    def set_location(self, location):
        if isinstance(location, URIHandler):
            self._uri = location._uri
        elif not location:
            self._uri = urlparse(self.DEFAULT_PREFIX)
        elif (get_platform() == PLATFORM_WINDOWS) and (location[1:3] == ":\\"):
            self._uri = urlparse(self.DEFAULT_PREFIX + location.replace("\\", "/"))
        else:
            self._uri = urlparse(location)
            if not self._uri.scheme:
                # always fill the "scheme" field - some functions expect this
                self._uri = urlparse(self.DEFAULT_PREFIX
                                     + os.path.realpath(os.path.abspath(location)))

    def is_local(self):
        return bool(self and (not self._uri.scheme or (self._uri.scheme == "file")))

    def get_local_path(self):
        if self.is_local():
            return self.get_path()
        else:
            return None

    def get_path(self):
        encoded_path = self._uri.path
        if get_platform() == PLATFORM_WINDOWS:
            # prepend "netloc" (the drive letter - e.g. "c:")
            encoded_path = self._uri.netloc + encoded_path
        # decode all special characters like "%20" and replace "/" with "\\" (Windows)
        return url2pathname(encoded_path)

    def get_url(self):
        return self._uri.geturl()

    def open(self):
        if self.is_local():
            return open(self.get_local_path(), "rb")
        else:
            return urllib.urlopen(self._uri.geturl())

    def retrieve_remote_file(self, destination, callback=None):
        if callback:
            download_callback = lambda current_blocks, block_size, num_of_blocks: callback()
        else:
            download_callback = None
        try:
            urllib.urlretrieve(self.get_url(), destination, download_callback)
            return True
        except IOError:
            return False

    def __eq__(self, other):
        if hasattr(other, "split"):
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
            return os.path.exists(self.get_local_path())
        else:
            try:
                handle = self.open()
                handle.close()
                return True
            except IOError:
                return False

    def is_writable(self):
        return bool(self.is_local()
                    and os.path.isfile(self.get_local_path())
                    and os.access(self.get_local_path(), os.W_OK))


def get_all_ips():
    """ try to get all IPs of this machine

    The resulting list of IPs contains non-local IPs first, followed by
    local IPs (starting with "127....").
    """
    def get_ips_of_name(name):
        try:
            ips = socket.gethostbyname_ex(name)
            if len(ips) == 3:
                return ips[2]
        except socket.gaierror:
            return []
    result = []
    result.extend(get_ips_of_name(socket.gethostname()))
    result.extend(get_ips_of_name("localhost"))
    filtered_result = []
    for one_ip in result:
        if one_ip not in filtered_result:
            filtered_result.append(one_ip)
    # non-local IPs first
    filtered_result.sort(key=lambda ip: ((1 if ip.startswith("127.") else 0), ip))
    return filtered_result


def get_exception_report():
    return ("An unexpected exception occoured: please send the text below to the developers of "
            "PyCAM. Thanks a lot!" + os.linesep + traceback.format_exc())


def print_stack_trace():
    # for debug purposes
    traceback.print_stack()


class ProgressCounter(object):

    def __init__(self, max_value, update_callback):
        if max_value <= 0:
            # prevent divide-by-zero in "get_percent"
            self.max_value = 100
        else:
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
        return min(100, max(0, 100.0 * self.current_value / self.max_value))
