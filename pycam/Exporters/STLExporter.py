#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright:    2010 by Lars Kruse <devel@sumpfralle.de>
# License:      GNU GPL v3 or higher (http://www.gnu.org/licenses/gpl-3.0.txt)
#

import datetime
import os

class STLExporter:

    def __init__(self, model, name="model", created_by="pycam", linesep=None):
        self.model = model
        self.name = name
        self.created_by = created_by
        if linesep is None:
            self.linesep = os.linesep
        else:
            self.linesep = linesep

    def __str__(self):
        return self.linesep.join(self.get_output_lines)

    def write(self, stream):
        for line in self.get_output_lines():
            stream.write(line)
            stream.write(self.linesep)

    def get_output_lines(self):
        date = datetime.date.today().isoformat()
        yield """solid "%s"; Produced by %s, %s""" % (self.name, self.created_by, date)
        for tr in self.model.triangles():
            norm = tr.normal().normalize()
            yield "facet normal %f %f %f" % (norm.x, norm.y, norm.z)
            yield "  outer loop"
            for p in (tr.p1, tr.p2, tr.p3):
                yield "    vertex %f %f %f" % (p.x, p.y, p.z)
            yield "  endloop"
            yield "endfacet"
        yield "endsolid"

