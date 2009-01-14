#!/usr/bin/python
import sys
import os

from pycam.Gui.SimpleGui import SimpleGui
from pycam.Importers.TestModel import TestModel

gui = SimpleGui()

inputfile = None
outputfile = None
display = False

for arg in sys.argv[1:]:
    if arg == "-gui":
        display = True
    elif arg[0] != '-':
        if not inputfile:
            inputfile = arg
        elif not outputfile:
            outputfile = arg

if not inputfile:
    gui.model = TestModel()
    gui.mainloop()
else:
    gui.open(inputfile)
    if display:
        gui.mainloop()
    else:
        gui.generateToolpath()
        if outputfile:
            gui.save(outputfile)

