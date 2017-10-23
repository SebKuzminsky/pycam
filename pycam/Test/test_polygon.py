from pycam.Geometry.Polygon import Polygon
from pycam.Geometry.Line import Line


def assert_polygons_are_identical(polygon0, polygon1):
    lines0 = polygon0.get_lines()
    lines1 = polygon1.get_lines()
    assert len(lines0) == len(lines1)
    for i in range(len(lines0)):
        line0 = lines0[i]
        line1 = lines1[i]
        (p00, p01) = line0.get_points()
        (p10, p11) = line1.get_points()
        assert p00 == p10
        assert p01 == p11


# "square_p" is a polygon consisting of a simple square,
# counter-clockwise.
lines = (Line((0, 0, 0), (10, 0, 0)),
         Line((10, 0, 0), (10, 10, 0)),
         Line((10, 10, 0), (0, 10, 0)),
         Line((0, 10, 0), (0, 0, 0)))
square_p = Polygon()
for line in lines:
    square_p.append(line)


def test_get_offset_polygons_square_outside():
    # 'expected_outside_p' is the expected offset polygon with a
    # *positive* offset, so it's outside the input polygon.
    lines = (Line((-1, -1, 0), (11, -1, 0)),
             Line((11, -1, 0), (11, 11, 0)),
             Line((11, 11, 0), (-1, 11, 0)),
             Line((-1, 11, 0), (-1, -1, 0)))
    expected_outside_p = Polygon()
    for line in lines:
        expected_outside_p.append(line)

    output_p = square_p.get_offset_polygons(1)[0]
    assert_polygons_are_identical(output_p, expected_outside_p)


def test_get_offset_polygons_square_inside():
    # 'expected_inside_p' is the expected offset polygon with a *negative*
    # offset, so it's inside the input polygon.
    lines = (Line((1, 1, 0), (9, 1, 0)),
             Line((9, 1, 0), (9, 9, 0)),
             Line((9, 9, 0), (1, 9, 0)),
             Line((1, 9, 0), (1, 1, 0)))
    expected_inside_p = Polygon()
    for line in lines:
        expected_inside_p.append(line)

    output_p = square_p.get_offset_polygons(-1)[0]
    assert_polygons_are_identical(output_p, expected_inside_p)
