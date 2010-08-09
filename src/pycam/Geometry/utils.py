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

import decimal
import math

INFINITE = 10000
epsilon = 0.0001

# use the "decimal" module for fixed precision numbers (only for debugging)
_use_precision = False


def sqrt(value):
    # support precision libraries like "decimal" (built-in)
    if hasattr(value, "sqrt"):
        return value.sqrt()
    else:
        return math.sqrt(value)

def ceil(value):
    if hasattr(value, "next_minus"):
        return int((value + number(1).next_minus()) // 1)
    else:
        return int(math.ceil(value))

def number(value):
    if _use_precision:
        return decimal.Decimal(str(value))
    else:
        return float(value)

