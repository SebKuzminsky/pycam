from distutils.core import setup
import py2exe

import distutils.sysconfig

import glob

setup(
    name="pycam",
    description="Python CAM",
    version="0.1",
    windows=[
        {
            'script' : 'pycam.py',
            }
        ],
    options = {
        'py2exe': {
            "packages": 'ctypes, logging, weakref, pycam',
            "includes": 'distutils.util',
            "excludes": 'OpenGL',
            }
        },
    data_files= [
        'README.TXT',
        distutils.sysconfig.get_python_lib()+"/PyOpenGL-3.0.0b5-py2.5.egg",
        distutils.sysconfig.get_python_lib()+"/setuptools-0.6c8-py2.5.egg",
        ('Samples', glob.glob('Samples/stl/*.stl')),
        ],
    )


