#!/usr/bin/python
import sys, time 
sys.path.insert(0,'.')


from pycam.Importers import STLImporter
from pycam.Gui.Visualization import ShowTestScene


if len(sys.argv)>1:
    filename = sys.argv[1]
else:
    filename = "Samples/STL/TestModel.stl"

start = time.clock()
model = STLImporter.ImportModel(filename)
end = time.clock()

print "time=", (end-start)

#ShowTestScene(model)

