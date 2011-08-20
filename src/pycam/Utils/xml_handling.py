#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$

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

import xml.etree.ElementTree as ET


def get_xml(item, name="value", ignore_self=False):
    if not ignore_self and hasattr(item, "get_xml"):
        return item.get_xml(name=name)
    elif isinstance(item, (list, tuple, set)):
        leaf = ET.Element("list", name=name)
        for single in item:
            leaf.append(get_xml(single))
        return leaf
    elif isinstance(item, dict):
        leaf = ET.Element("dict", name=name)
        for key, value in item.iteritems():
            leaf.append(get_xml(value, name=key))
        return leaf
    else:
        leaf = ET.Element(name)
        leaf.text=repr(item)
        return leaf

