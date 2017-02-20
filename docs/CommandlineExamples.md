Using PyCAM via the commandline
===============================

**WARNING: this page is slightly outdated. Please refer to the output of
“pycam --help” or take a look at it as
[HTML](http://pycam.sourceforge.net/pycam.1.html).**

The following examples show some command use-cases for the
non-interactive generation of GCode with PyCAM:

-   load a specific settings file for the GUI:

<!-- -->

    pycamGUI --config SOME_CONFIG_FILE

-   open a model:

<!-- -->

    pycamGUI SOME_MODEL_FILE

-   generate a GCode file using all default tasks (taken from the
    default settings):

<!-- -->

    pycamGUI SOME_MODEL_FILE DESTINATION_GCODE_FILE

-   generate a GCode file using a custom settings file and picking just
    one specific task:

<!-- -->

    pycamGUI --config YOUR_SETTINGS_FILE --task 2 SOME_MODEL_FILE DESTINATION_GCODE_FILE
