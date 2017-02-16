# -*- coding: utf-8 -*-
"""
Copyright 2013 Lars Kruse <devel@sumpfralle.de>

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


import unittest


class PycamTestCase(unittest.TestCase):

    def _compare_vectors(self, v1, v2, max_deviance=0.000001):
        # provide readable error messages
        result_difference = "%s != %s" % (v1, v2)
        result_equal = None
        if v1 == v2:
            return result_equal
        for index in range(3):
            if max_deviance < abs(v1[index] - v2[index]):
                return result_difference
        return result_equal

    def assertVectorEqual(self, v1, v2):
        self.assertIsNone(self._compare_vectors(v1, v2))

    def assertVectorNotEqual(self, v1, v2):
        self.assertIsNotNone(self._compare_vectors(v1, v2))

    def assertCollisionEqual(self, (ccp1, cp1, d1), (ccp2, cp2, d2)):
        self.assertVectorEqual(ccp1, ccp2)
        self.assertVectorEqual(cp1, cp2)
        self.assertAlmostEqual(d1, d2)


main = unittest.main

