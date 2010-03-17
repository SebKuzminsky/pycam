#!/usr/bin/env python

from distutils.core import setup
import distutils.sysconfig
import glob
import os.path

setup(
    name="pycam",
    version="0.2.2",
    license="GPL v3",
    description="Open Source CAM - Toolpath Generation for 3-Axis CNC machining",
    author="Lode Leroy",
    #author_email="",
    provides=["pycam"],
    requires=["ode", "gtk", "gtk.gtkgl", "OpenGL"],
    url="http://sourceforge.net/projects/pycam",
    download_url="http://sourceforge.net/projects/pycam/files/pycam/0.2.2/pycam-0.2.2.tgz/download",
    keywords=["3-axis", "cnc", "cam", "toolpath", "machining", "g-code"],
    # full list of classifiers at:
    #   http://pypi.python.org/pypi?:action=list_classifiers
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "Topic :: Scientific/Engineering",
        "Environment :: Win32 (MS Windows)",
        "Environment :: X11 Applications",
        "Intended Audience :: Manufacturing",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX",
    ],
    packages=[
        "pycam",
        "pycam.Cutters", 
        "pycam.Geometry", 
        "pycam.Importers",
        "pycam.PathProcessors", 
        "pycam.Utils", 
        "pycam.Exporters",
        "pycam.Gui", 
        "pycam.PathGenerators", 
        "pycam.Simulation"
    ],
    scripts = ['pycam_start.py', 'pycam_win32_postinstall.py'],
    data_files=[("share/python-pycam",[
            "COPYING.TXT",
            "HOWTO.TXT",
            "INSTALL.TXT",
            "LICENSE.TXT",
            "README.TXT",
            "Changelog",
            "release_info.txt"]),
        ("share/python-pycam/ui", [
            os.path.join("pycam", "Gui", "gtk-interface", "pycam-project.ui"),
            os.path.join("pycam", "Gui", "gtk-interface", "menubar.xml"),
            ]),
        ("share/python-pycam/samples", 
            glob.glob(os.path.join("Samples","STL","*.stl"))),
    ],
)

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
