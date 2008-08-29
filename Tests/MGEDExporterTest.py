#!/usr/bin/python
import sys
sys.path.insert(0,'.')

from pycam.Exporters.MGEDExporter import MGEDExporter
from pycam.Importers.TestModel import TestModel

model = TestModel()
file = MGEDExporter("TestModel.txt")
file.AddModel(model)
file.close()


