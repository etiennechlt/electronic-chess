"""The board core's geometry helpers: the copper of a pad as KiCad draws it,
and the erosion that keeps ground drops where the pour can reach them."""

import numpy as np
from boardgen.core import PadItem, _erode, pad_copper
from shapely.geometry import Point


def _pad(shape, w, h, rratio=0.0, rot=0.0):
    return PadItem("N", "F.Cu", 10.0, 20.0, w, h, rot, "R1", "1", 0.0, shape, rratio)


def test_rect_pad_keeps_its_corners():
    g = pad_copper(_pad("rect", 1.0, 2.0))
    assert g.covers(Point(10.49, 20.99))


def test_roundrect_pad_loses_its_corners():
    g = pad_copper(_pad("roundrect", 1.0, 2.0, rratio=0.25))
    assert g.covers(Point(10.0, 20.0)) and g.covers(Point(10.49, 20.0))
    assert not g.covers(Point(10.49, 20.99))  # the corner KiCad rounds off


def test_round_pad_is_a_disc():
    g = pad_copper(_pad("circle", 1.7, 1.7))
    assert g.covers(Point(10.0, 20.84))
    assert not g.covers(Point(10.7, 20.7))  # inside the bounding box, outside the disc


def test_oval_pad_is_a_stadium_along_its_long_side():
    g = pad_copper(_pad("oval", 1.0, 2.0, rot=90.0))  # rotated: long side along x
    assert g.covers(Point(10.9, 20.0)) and not g.covers(Point(10.0, 20.9))


def test_erosion_keeps_the_cells_with_a_free_disc_around_them():
    free = np.ones((9, 9), dtype=bool)
    free[4, 4] = False
    out = _erode(free, 2)
    assert not out[4, 4] and not out[4, 6] and not out[2, 4]
    assert out[2, 2] and out[6, 2] and out[6, 6]
    assert not out[0, 0]  # the board edge counts as blocked
