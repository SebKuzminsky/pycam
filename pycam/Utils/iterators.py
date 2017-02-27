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


class Iterator(object):
    def __init__(self, seq, start=0):
        self.seq = seq
        self.ind = start

    def next(self):
        if self.ind >= len(self.seq):
            return None
        else:
            item = self.seq[self.ind]
            self.ind += 1
            return item

    def insertBefore(self, item):
        self.seq.insert(self.ind - 1, item)
        self.ind += 1

    def insert(self, item):
        self.seq.insert(self.ind, item)
        self.ind += 1

    def replace(self, item_old, item_new):
        for i in range(len(self.seq)):
            if self.seq[i] == item_old:
                self.seq[i] = item_new

    def remove(self, item):
        for i in range(len(self.seq)):
            if self.seq[i] == item:
                del self.seq[i]
                if i < self.ind:
                    self.ind -= 1
                return

    def takeNext(self):
        if self.ind >= len(self.seq):
            return None
        else:
            return self.seq.pop(self.ind)

    def copy(self):
        return Iterator(self.seq, self.ind)

    def peek(self, i=0):
        if self.ind + i >= len(self.seq):
            return None
        else:
            return self.seq[self.ind + i]

    def remains(self):
        return len(self.seq) - self.ind


class CyclicIterator(object):
    def __init__(self, seq, start=0):
        self.seq = seq
        self.ind = start
        self.count = len(seq)

    def next(self):
        item = self.seq[self.ind]
        self.ind += 1
        if self.ind == len(self.seq):
            self.ind = 0
        return item

    def copy(self):
        return CyclicIterator(self.seq, self.ind)

    def peek(self, i=0):
        idx = self.ind + i
        while idx >= len(self.seq):
            idx -= len(self.seq)
        return self.seq[idx]


if __name__ == "__main__":
    l = [1, 2, 4, 6]
    print("l=", l)
    i = Iterator(l)
    print(i.peek())
    while True:
        val = next(i)
        if val is None:
            break
        if val == 4:
            i.insertBefore(3)
            i.insert(5)

    print("l=", l)
    i = Iterator(l)
    print("peek(0)=", i.peek(0))
    print("peek(1)=", i.peek(1))
    print("i.next()=", next(i))
    print("peek(0)=", i.peek(0))
    print("peek(1)=", i.peek(1))

    print("remains=", i.remains())

    print("l=", l)
    sum_value = 0
    i = CyclicIterator(l)
    print("cycle :"),
    while sum_value < 30:
        val = next(i)
        print(val),
        sum_value += val
    print("=", sum_value)

    i = Iterator(l)
    print("l=", l)
    next(i)
    next(i)
    print("next,next : ", i.peek())
    i.remove(2)
    print("remove(2) : ", i.peek())
    i.remove(4)
    print("remove(4) : ", i.peek())
    print("l=", l)
