"""The shared finishing pass closes the gaps the lattice router leaves,
on the exact geometry, for any copper stack."""

from dataclasses import dataclass

import pytest
from quadgen.finish import Rules, finish_pass, net_pieces
from shapely.geometry import LineString, Point, box


@dataclass
class Pad:
    net: str
    layer: str
    x: float
    y: float
    w: float
    h: float
    rot: float = 0.0
    ref: str = "R"
    number: str = "1"
    drill: float = 0.0
    shape: str = "rect"
    rratio: float = 0.0


RULES4 = Rules(
    layers=("F.Cu", "In1.Cu", "In2.Cu", "B.Cu"),
    board=(20.0, 20.0),
    edge=0.5,
    clearance=0.15,
    width=0.3,
    via=(0.45, 0.2),
    plane="In1.Cu",
    thin=0.2,
)
RULES2 = Rules(
    layers=("F.Cu", "B.Cu"), board=(20.0, 20.0), edge=0.5, clearance=0.15, width=0.3, via=(0.8, 0.4)
)


def _pieces(rules, pads, tracks, vias, pour=None):
    return net_pieces("A", rules, pads, tracks, vias, pour)


def test_a_straight_gap_on_one_layer_is_joined():
    pads = [Pad("A", "F.Cu", 5.0, 10.0, 1.0, 1.0), Pad("A", "F.Cu", 8.0, 10.0, 1.0, 1.0)]
    tracks = [("A", "F.Cu", 0.3, [(5.0, 10.0), (6.0, 10.0)])]
    assert len(_pieces(RULES4, pads, tracks, [])) == 2
    new_tracks, new_vias, log = finish_pass(RULES4, pads, tracks, [])
    assert len(log) == 1 and new_vias == []
    assert len(_pieces(RULES4, pads, tracks + new_tracks, new_vias)) == 1
    # the joint stays on the top layer, between the two pads
    assert new_tracks[0][1] == "F.Cu"
    assert LineString(new_tracks[0][3]).bounds[0] >= 5.0


def test_a_wall_in_front_of_the_pad_is_crossed_through_vias():
    pads = [Pad("A", "F.Cu", 5.0, 10.0, 1.0, 1.0), Pad("A", "F.Cu", 10.0, 10.0, 1.0, 1.0)]
    # a foreign track walls the top layer between the two, edge to edge
    tracks = [("B", "F.Cu", 0.3, [(7.5, 0.6), (7.5, 19.4)])]
    new_tracks, new_vias, log = finish_pass(RULES4, pads, tracks, [])
    assert len(log) == 1
    assert len(new_vias) == 2, new_vias
    layers = {t[1] for t in new_tracks}
    assert "In1.Cu" not in layers, "no joint runs on the plane"
    assert len(_pieces(RULES4, pads, tracks + new_tracks, new_vias)) == 1
    # every via keeps the clearance to the wall
    wall = LineString(tracks[0][3]).buffer(0.15)
    assert all(Point(v[1], v[2]).buffer(v[3] / 2.0).distance(wall) >= 0.15 - 1e-6 for v in new_vias)


def test_the_plane_net_gets_a_drop_where_it_has_no_plane_copper():
    pads = [
        Pad("GND", "F.Cu", 5.0, 10.0, 1.0, 1.0),
        Pad("GND", "*.Cu", 15.0, 10.0, 1.6, 1.6, drill=0.8),
    ]
    pour = ("In1.Cu", None)
    stranded = [pc for pc in net_pieces("GND", RULES4, pads, [], [], pour) if "In1.Cu" not in pc]
    assert len(stranded) == 1
    new_tracks, new_vias, log = finish_pass(RULES4, pads, [], [], nets=["GND"], pour=pour)
    assert len(new_vias) == 1 and log
    assert not [
        pc
        for pc in net_pieces("GND", RULES4, pads, new_tracks, new_vias, pour)
        if "In1.Cu" not in pc
    ]


def test_a_two_layer_board_joins_through_the_back():
    pads = [Pad("A", "F.Cu", 5.0, 10.0, 1.0, 1.0), Pad("A", "F.Cu", 10.0, 10.0, 1.0, 1.0)]
    tracks = [("B", "F.Cu", 0.3, [(7.5, 0.6), (7.5, 19.4)])]
    new_tracks, new_vias, log = finish_pass(RULES2, pads, tracks, [])
    assert log and len(new_vias) == 2
    assert {t[1] for t in new_tracks} == {"F.Cu", "B.Cu"}
    assert len(_pieces(RULES2, pads, tracks + new_tracks, new_vias)) == 1


def test_a_keepout_is_never_entered():
    pads = [Pad("A", "F.Cu", 3.0, 10.0, 1.0, 1.0), Pad("A", "F.Cu", 17.0, 10.0, 1.0, 1.0)]
    keep = Point(10.0, 10.0).buffer(4.0)
    new_tracks, new_vias, log = finish_pass(RULES4, pads, [], [], keepouts=[keep])
    assert log, "the pass walks around the keepout"
    for _net, _layer, width, pts in new_tracks:
        assert LineString(pts).buffer(width / 2.0).distance(keep) >= 0.15 - 1e-6
    for _net, x, y, pad, _drill in new_vias:
        assert Point(x, y).buffer(pad / 2.0).distance(keep) >= 0.15 - 1e-6


def test_the_maze_finds_a_detour_no_simple_joint_can():
    # a U-shaped wall around one pad on the top layer and the back layer
    # both, leaving a single opening two turns away
    pads = [Pad("A", "F.Cu", 6.0, 10.0, 0.8, 0.8), Pad("A", "F.Cu", 14.0, 10.0, 0.8, 0.8)]
    wall = []
    for layer in ("F.Cu", "In2.Cu", "B.Cu"):
        wall.append(("B", layer, 0.3, [(8.0, 6.0), (8.0, 14.0)]))
        wall.append(("B", layer, 0.3, [(4.0, 6.0), (8.0, 6.0)]))
        wall.append(("B", layer, 0.3, [(4.0, 14.0), (8.0, 14.0)]))
    new_tracks, new_vias, log = finish_pass(RULES4, pads, wall, [])
    assert log, "no joint found"
    assert len(_pieces(RULES4, pads, wall + new_tracks, new_vias)) == 1
    walls = [LineString(t[3]).buffer(0.15) for t in wall]
    for _net, layer, width, pts in new_tracks:
        g = LineString(pts).buffer(width / 2.0)
        for w, t in zip(walls, wall, strict=True):
            if t[1] == layer:
                assert g.distance(w) >= 0.15 - 1e-6


@pytest.mark.parametrize("rules", [RULES2, RULES4])
def test_nothing_is_drawn_when_nothing_is_open(rules):
    pads = [Pad("A", "F.Cu", 5.0, 10.0, 1.0, 1.0), Pad("A", "F.Cu", 8.0, 10.0, 1.0, 1.0)]
    tracks = [("A", "F.Cu", 0.3, [(5.0, 10.0), (8.0, 10.0)])]
    assert finish_pass(rules, pads, tracks, []) == ([], [], [])
    assert box(0, 0, 1, 1).area == 1.0
