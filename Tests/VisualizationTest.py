#!/usr/bin/python
import sys
sys.path.insert(0,'.')

from pycam.Gui.Visualization import Visualization
from pycam.Importers.TestModel import TestModel

model = TestModel()

def DrawScene():
    model.to_OpenGL()

Visualization("VisualizationTest", DrawScene)
