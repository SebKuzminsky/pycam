#!/usr/bin/python
import sys
sys.path.insert(0,'.')

from pycam.Importers import STLImporter
from pycam.Gui.Visualization import ShowTestScene

model = STLImporter.ImportModel("Samples/STL/SampleScene.stl")

ShowTestScene(model)

