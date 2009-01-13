import sys
import os

from pycam.Gui.SimpleGui import SimpleGui
from pycam.Importers.TestModel import TestModel

gui = SimpleGui()
gui.model = TestModel()
gui.mainloop()
