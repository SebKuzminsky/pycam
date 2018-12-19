import math

from pycam.Geometry.PointUtils import padd, pcross, pmul, pnormalized, pnormsq, psub


def get_x3d_line(points, color, thickness: int = None):
    yield "<Shape>"
    yield "<Appearance>"
    yield ('<Material emissiveColor="{:f} {:f} {:f}" transparency="{:f}" />'
           .format(color["red"], color["green"], color["blue"], 1 - color["alpha"]))
    if thickness is not None:
        yield '<LineProperties linewidthScaleFactor="{:d}" />'.format(int(thickness))
    yield "</Appearance>"
    yield '<LineSet vertexCount="{:d}">'.format(len(points))
    yield '<Coordinate point="{}" />'.format(" ".join("{:f} {:f} {:f}".format(*point)
                                                      for point in points))
    yield "</LineSet>"
    yield "</Shape>"


def get_x3d_cone(start: tuple, end: tuple, position: float, length: float, radius: float,
                 color: tuple):
    # by default the X3D cone points along the y axis
    original_vector = (0, 1, 0)
    line_vector = psub(end, start)
    line_normalized = pnormalized(line_vector)
    # the cone position is at its bottom
    bottom_position = padd(start, pmul(line_vector, position))
    # handling of corner cases
    if pnormsq(pcross(original_vector, line_normalized)) == 0:
        # Both vectors are aligned - but maybe point into different directions.
        rotation_axis = (1, 0, 0)
        rotation_angle = math.pi if original_vector != line_normalized else 0
    else:
        # Both vectors are not aligned.  Use a normal rotation.
        # Rotate around the vector in the vector in the middle by 180 degrees.
        rotation_axis = padd(original_vector, line_normalized)
        rotation_angle = math.pi
    yield ('<Transform translation="{:f} {:f} {:f}" rotation="{:f} {:f} {:f} {:f}">'
           .format(*bottom_position, *rotation_axis, rotation_angle))
    yield "<Shape>"
    yield "<Appearance>"
    yield ('<Material diffuseColor="{:f} {:f} {:f}" transparency="{:f}" />'
           .format(color["red"], color["green"], color["blue"], 1 - color["alpha"]))
    yield "</Appearance>"
    yield '<Cone bottomRadius="{:f}" topRadius="0" height="{:f}" />'.format(radius, length)
    yield "</Shape>"
    yield "</Transform>"
