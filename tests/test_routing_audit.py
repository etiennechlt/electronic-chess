"""The delivered boards hold the invariants of the routing rules that a
test can pin: orthogonal placement, fabrication gates, ground drops
within reach of every ground pad (note 21)."""

from pathlib import Path

import pytest
from routing_audit import pad_shape, read_board
from shapely.geometry import Point

from chessboard_calc.config import DEFAULT_CONFIG_PATH

BOARDS = ("hardware/quadrant-2x2/quadrant-2x2.kicad_pcb", "hardware/bench/bench.kicad_pcb")
MIN_WIDTH_MM = 0.127  # the standard capability of the fabricator
MIN_DRILL_MM = 0.2
GROUND_REACH_MM = 3.5  # the strip's pour is on the back layer, so every pad needs a via near


@pytest.fixture(scope="module", params=BOARDS)
def board(request):
    path = DEFAULT_CONFIG_PATH.parents[1] / request.param
    if not path.exists():
        pytest.skip(f"{request.param} not generated")
    return read_board(path)


def test_the_reader_finds_the_whole_board(board):
    assert board.pads and board.tracks and board.vias and board.rotations
    # every segment and via carries the name of its net, so the net table was read
    assert all(t.net for t in board.tracks)
    assert all(v.net for v in board.vias)


def test_every_footprint_is_orthogonal(board):
    off = {ref: angle for ref, angle in board.rotations.items() if abs(angle % 90.0) > 1e-6}
    assert off == {}


def test_the_fabrication_gates_hold(board):
    assert min(t.width for t in board.tracks) >= MIN_WIDTH_MM
    assert min(v.drill for v in board.vias) >= MIN_DRILL_MM
    assert min(v.pad - v.drill for v in board.vias) >= 0.2  # annular ring, both sides


def test_the_quadrant_keeps_its_ground_drops_within_reach():
    path = Path(DEFAULT_CONFIG_PATH.parents[1] / BOARDS[0])
    if not path.exists():
        pytest.skip("quadrant not generated")
    b = read_board(path)
    drops = [(v.x, v.y) for v in b.vias if v.net == "GND"]
    assert drops
    for pad in (p for p in b.pads if p.net == "GND"):
        shape = pad_shape(pad)
        near = min(shape.distance(Point(x, y)) for x, y in drops)
        assert near <= GROUND_REACH_MM, f"{pad.ref}.{pad.number} is {near:.2f} mm from a drop"
