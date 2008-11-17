import sys
import os
sys.path.insert(0, os.path.join(sys.prefix, "PyOpenGL-3.0.0b5-py2.5.egg"))
sys.path.insert(0, os.path.join(sys.prefix, "setuptools-0.6c8-py2.5.egg"))

from pycam.Gui.SimpleGui import SimpleGui
from pycam.Importers.TestModel import TestModel

gui = SimpleGui()
gui.model = TestModel()
gui.mainloop()
