# -*- coding: utf-8 -*-
"""
Copyright 2010 Lars Kruse <devel@sumpfralle.de>

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

import pycam.Cutters
import pycam.Toolpath
import pycam.Utils
import pycam.Utils.log

CONFIG_DIR = "pycam"

log = pycam.Utils.log.get_logger()


def get_config_dirname():
    try:
        from win32com.shell import shellcon, shell
        homedir = shell.SHGetFolderPath(0, shellcon.CSIDL_APPDATA, 0, 0)
        config_dir = os.path.join(homedir, CONFIG_DIR)
    except ImportError:
        # quick semi-nasty fallback for non-windows/win32com case
        homedir = os.path.expanduser("~")
        # hide the config directory for unixes
        config_dir = os.path.join(homedir, "." + CONFIG_DIR)
    if not os.path.isdir(config_dir):
        try:
            os.makedirs(config_dir)
        except OSError:
            config_dir = None
    return config_dir


def get_config_filename(filename=None):
    if filename is None:
        filename = "preferences.conf"
    config_dir = get_config_dirname()
    if config_dir is None:
        return None
    else:
        return os.path.join(config_dir, filename)


class Settings(dict):

    GET_INDEX = 0
    SET_INDEX = 1
    VALUE_INDEX = 2

    def __getitem_orig(self, key):
        return super(Settings, self).__getitem__(key)

    def __setitem_orig(self, key, value):
        super(Settings, self).__setitem__(key, value)

    def add_item(self, key, get_func=None, set_func=None):
        self.__setitem_orig(key, [None, None, None])
        self.define_get_func(key, get_func)
        self.define_set_func(key, set_func)
        self.__getitem_orig(key)[self.VALUE_INDEX] = None

    def set(self, key, value):
        self[key] = value

    def get(self, key, default=None):
        try:
            return self.__getitem__(key)
        except KeyError:
            return default

    def define_get_func(self, key, get_func=None):
        if key not in self:
            return
        if get_func is None:
            real_get_func = lambda: self.__getitem_orig(key)[self.VALUE_INDEX]
        else:
            real_get_func = get_func
        self.__getitem_orig(key)[self.GET_INDEX] = real_get_func

    def define_set_func(self, key, set_func=None):
        def default_set_func(value):
            self.__getitem_orig(key)[self.VALUE_INDEX] = value
        if key not in self:
            return
        if set_func is None:
            set_func = default_set_func
        self.__getitem_orig(key)[self.SET_INDEX] = set_func

    def __getitem__(self, key):
        try:
            return self.__getitem_orig(key)[self.GET_INDEX]()
        except TypeError as err_msg:
            log.info("Failed to retrieve setting '%s': %s", key, err_msg)
            return None

    def __setitem__(self, key, value):
        if key not in self:
            self.add_item(key)
        self.__getitem_orig(key)[self.SET_INDEX](value)
        self.__getitem_orig(key)[self.VALUE_INDEX] = value
