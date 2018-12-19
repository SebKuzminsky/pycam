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
