from pycam.Geometry import *

def TestModel():
    points = []
    points.append(Point(-2,1,4))
    points.append(Point(2,1,4))
    points.append(Point(0,-2,4))

    points.append(Point(-5,2,2))
    points.append(Point(-1,3,2))
    points.append(Point(5,2,2))

    points.append(Point(4,-1,2))
    points.append(Point(2,-4,2))
    points.append(Point(-2,-4,2))
    points.append(Point(-3,-2,2))

    model = Model()
    model.append(Triangle(points[0],points[1],points[2]))
    model.append(Triangle(points[0],points[3],points[4]))
    model.append(Triangle(points[0],points[4],points[1]))
    model.append(Triangle(points[1],points[4],points[5]))
    model.append(Triangle(points[1],points[5],points[6]))
    model.append(Triangle(points[1],points[6],points[2]))
    model.append(Triangle(points[2],points[6],points[7]))
    model.append(Triangle(points[2],points[7],points[8]))
    model.append(Triangle(points[2],points[8],points[9]))
    model.append(Triangle(points[2],points[9],points[0]))
    model.append(Triangle(points[0],points[9],points[3]))
    return model

