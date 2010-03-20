#!/usr/bin/python

from pycam.Gui.common import override_ode_availability
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
            action="store_true", default=True,
            help="use the new GTK interface (default)")
    parser.add_option("", "--tk", dest="gtk_gui",
            action="store_false",
            help="use the (old) Tk interface")
    parser.add_option("-c", "--config", dest="config_file",
            default=None, action="store", type="string",
            help="load a file with processing settings (requires the GTK interface)")
    parser.add_option("", "--template", dest="config_template",
            default=None, action="store", type="string",
            help="enable a specific processing settings template - e.g. 'Rough', 'Semi-finish' or 'Finish' (requires the GTK interface)")
    parser.add_option("", "--disable-ode", dest="ode_disabled",
            default=False, action="store_true", help="disable experimental ODE collision detection")
    (options, args) = parser.parse_args()

    if len(args) > 0:
        inputfile = args[0]
    if len(args) > 1:
        outputfile = args[1]
    if len(args) > 2:
        parser.error("too many arguments given (%d instead of %d)" % (len(args), 2))

    # try the configured interface first and then try to fall back to the alternative, if necessary
    if options.gtk_gui:
        try:
            from pycam.Gui.Project import ProjectGui
            gui_class = ProjectGui
        except ImportError, err_msg:
            print >> sys.stderr, "Failed to load GTK bindings for python. Please install the package 'python-gtk2'."
            print >> sys.stderr, "Details: %s" % str(err_msg)
            print >> sys.stderr, "I will try to use the alternative Tk interface now ..."
            try:
                from pycam.Gui.SimpleGui import SimpleGui
                gui_class = SimpleGui()
            except ImportError:
                gui_class = None
    else:
        try:
            from pycam.Gui.SimpleGui import SimpleGui
            gui_class = SimpleGui
        except ImportError, err_msg:
            print >> sys.stderr, "Failed to load TkInter bindings for python. Please install the package 'python-tk'."
            print >> sys.stderr, "Details: %s" % str(err_msg)
            print >> sys.stderr, "I will try to use the alternative GTK interface now ..."
            try:
                from pycam.Gui.Project import ProjectGui
                gui_class = ProjectGui
            except ImportError:
                gui_class = None
    # exit if no interface is found
    if gui_class is None:
        print >> sys.stderr, "Neither the GTK nor the Tk interface is available. Please install the corresponding packages!"
        sys.exit(1)

    if options.ode_disabled:
        override_ode_availability(False)

    if outputfile:
        gui = gui_class(no_dialog=True)
    else:
        gui = gui_class()

    if not inputfile:
        from pycam.Importers.TestModel import TestModel
        gui.load_model(TestModel())
    else:
        gui.open(inputfile)
    # load processing config file
    # only available for the GTK interface
    if options.gtk_gui:
        if options.config_file:
            gui.open_processing_settings_file(options.config_file)
        if options.config_template:
            gui.switch_processing_config(section=options.config_template)
    if outputfile and not options.display:
        # an output filename is given and no gui is explicitly requested
        gui.generateToolpath()
        if outputfile:
            gui.save_toolpath(outputfile)
    else:
        # the gui should be shown
        if outputfile:
            gui.setOutputFilename(outputfile)
        gui.mainloop()

