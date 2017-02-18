#!/usr/bin/env python
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

import xml.etree.ElementTree as ET


def get_xml(item, name=None):
    if name is None:
        if hasattr(item, "node_key"):
            name = item.node_key
        else:
            name = "value"
    if isinstance(item, (list, tuple, set)):
        leaf = ET.Element(name)
        for single in item:
            leaf.append(get_xml(single))
        return leaf
    elif isinstance(item, dict):
        leaf = ET.Element(name)
        for key, value in item.iteritems():
            leaf.append(get_xml(value, name=key))
        return leaf
    else:
        leaf = ET.Element(name)
        leaf.text = str(item)
        return leaf


def parse_xml_dict(item):
    pass


def get_xml_lines(item):
    lines = []
    content = ET.tostring(item)
    content = content.replace("><", ">\n<")
    indent = 0
    for line in content.split("\n"):
        indented = False
        if line.startswith("</"):
            indent -= 2
            indented = True
        lines.append(" " * indent + line)
        if indented:
            pass
        elif line.endswith("/>"):
            pass
        elif line.startswith("</"):
            indent -= 2
        elif "</" in line:
            pass
        else:
            indent += 2
    return lines
