#!/usr/bin/python

from optparse import OptionParser

from pycam.Gui.SimpleGui import SimpleGui
from pycam.Importers.TestModel import TestModel

# check if we were started as a separate program
if __name__ == "__main__":
    inputfile = None
    outputfile = None

    parser = OptionParser(usage="usage: %prog [--gui] [inputfile [outputfile]]")
    parser.add_option("", "--gui", dest="display",
            action="store_true", default=False,
            help="don't create the outputfile on the fly - just preset the output filename and show the GUI")
    (options, args) = parser.parse_args()

    if len(args) > 0:
        inputfile = args[0]
    if len(args) > 1:
        outputfile = args[1]
    if len(args) > 2:
        parser.error("too many arguments given (%d instead of %d)" % (len(args), 2))

    gui = SimpleGui()

    if not inputfile:
        gui.model = TestModel()
    else:
        gui.open(inputfile)
    if outputfile and not options.display:
        # an output filename is given and no gui is explicitly requested
        gui.generateToolpath()
        if outputfile:
            gui.save(outputfile)
    else:
        # the gui should be shown
        if outputfile:
            gui.setOutputFilename(outputfile)
        gui.mainloop()

