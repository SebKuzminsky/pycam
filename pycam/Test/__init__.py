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
        for index in range(3):
            if max_deviance < abs(v1[index] - v2[index]):
                return False
        return True

    def assertVectorEqual(self, v1, v2):
        self.assertTrue(self._compare_vectors(v1, v2))

    def assertVectorNotEqual(self, v1, v2):
        self.assertFalse(self._compare_vectors(v1, v2))


main = unittest.main

