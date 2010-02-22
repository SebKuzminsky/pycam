#!/usr/bin/python

from optparse import OptionParser
import sys

# check if we were started as a separate program
if __name__ == "__main__":
    inputfile = None
    outputfile = None

    parser = OptionParser(usage="usage: %prog [options] [inputfile [outputfile]]")
    parser.add_option("", "--gui", dest="display",
            action="store_true", default=False,
            help="don't create the outputfile on the fly - just preset the output filename and show the GUI")
    parser.add_option("", "--gtk", dest="gtk_gui",
            action="store_true", default=False,
            help="use the new GTK interface")
    (options, args) = parser.parse_args()

    if len(args) > 0:
        inputfile = args[0]
    if len(args) > 1:
        outputfile = args[1]
    if len(args) > 2:
        parser.error("too many arguments given (%d instead of %d)" % (len(args), 2))

    if options.gtk_gui:
        try:
            from pycam.Gui.Project import ProjectGui
        except ImportError, err_msg:
            print sys.stderr, "Failed to load GTK bindings for python. Please install the package 'python-gtk2'."
            print sys.stderr, "Details: %s" % str(err_msg)
        gui = ProjectGui()
    else:
        try:
            from pycam.Gui.SimpleGui import SimpleGui
        except ImportError, err_msg:
            print sys.stderr, "Failed to load TkInter bindings for python. Please install the package 'python-tk'."
            print sys.stderr, "Details: %s" % str(err_msg)
        gui = SimpleGui()

    if not inputfile:
        from pycam.Importers.TestModel import TestModel
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

