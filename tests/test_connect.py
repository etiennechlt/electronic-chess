"""The connectivity bookkeeping shared by the generators: cells inside the
real copper of a pad, the pieces of a net, the joining loop and the exact
check, on a small lattice with hand-made copper."""

from __future__ import annotations

from dataclasses import dataclass

from quadgen.connect import (
    Piece,
    close_net,
    connectivity_check,
    ground_drops,
    net_pieces,
    pad_cells,
    reached,
    stub_copper,
    track_cells,
)
from quadgen.router import MultiRouter

LAYERS = ["F.Cu", "B.Cu"]


@dataclass
class Pad:
    net: str
    layer: str
    x: float
    y: float
    w: float
    h: float
    rot: float = 0.0
    ref: str = "R1"
    number: str = "1"
    shape: str = "rect"
    rratio: float = 0.0


@dataclass
class Trk:
    net: str
    layer: str
    width: float
    pts: list


@dataclass
class Vi:
    net: str
    x: float
    y: float
    pad: float
    drill: float


def router() -> MultiRouter:
    return MultiRouter(LAYERS, 0.0, 0.0, 10.0, 10.0, 0.1, 0.15, 0.6)


def test_round_pad_cells_stay_inside_the_disc():
    mr = router()
    cells = pad_cells(mr, Pad("N", "F.Cu", 5.0, 5.0, 1.0, 1.0, shape="circle"))
    assert (50, 50) in cells and (54, 50) in cells
    assert (54, 54) not in cells  # the corner of the bounding box
    assert (54, 54) in pad_cells(mr, Pad("N", "F.Cu", 5.0, 5.0, 1.0, 1.0))


def test_track_cells_follow_the_polyline_inside_the_lattice():
    mr = router()
    cells = track_cells(mr, [(1.0, 1.0), (1.0, 2.0), (12.0, 2.0)])
    assert (10, 10) in cells and (10, 20) in cells and (100, 20) in cells
    assert max(i for i, _j in cells) == 100  # the polyline leaves the lattice at x = 10


def test_pieces_follow_the_real_contact_of_the_copper():
    mr = router()
    pads = [
        Pad("N", "F.Cu", 2.0, 2.0, 1.0, 0.6, ref="R1", number="1"),
        Pad("N", "F.Cu", 6.0, 2.0, 1.0, 0.6, ref="R1", number="2"),
        Pad("N", "F.Cu", 6.0, 6.0, 1.0, 0.6, ref="C1", number="1"),
    ]
    tracks = [
        Trk("N", "F.Cu", 0.3, [(2.0, 2.0), (4.0, 2.0)]),
        Trk("N", "F.Cu", 0.3, [(4.0, 2.0), (6.0, 2.0)]),
    ]
    pieces = net_pieces(mr, LAYERS, pads, tracks, [], first=[tracks[1]])
    assert [pc.label for pc in pieces] == ["R1.1 R1.2", "C1.1"]
    assert (40, 20) in pieces[0].cells["F.Cu"]  # the joint of the two tracks
    assert set(pieces[1].cells) == {"F.Cu"}
    # a pad off the lattice is no piece at all
    far = Pad("N", "F.Cu", 30.0, 2.0, 1.0, 0.6, ref="X1", number="1")
    assert len(net_pieces(mr, LAYERS, pads + [far], tracks, [])) == 2


def test_a_via_joins_the_layers_and_a_stub_extends_its_pad():
    mr = router()
    pads = [
        Pad("N", "F.Cu", 2.0, 2.0, 0.4, 0.4, ref="U1", number="1"),
        Pad("N", "F.Cu", 8.0, 8.0, 1.0, 1.0, ref="C1", number="1"),
    ]
    stub = ("N", [(2.0, 2.0), (2.0, 2.5)], 0.8, True)  # fanout via 0.8 mm past the stub
    tracks = [
        Trk("N", "F.Cu", 0.2, [(2.0, 2.0), (2.0, 2.5)]),
        Trk("N", "F.Cu", 0.2, [(2.0, 2.5), (2.0, 3.3)]),
    ]
    vias = [Vi("N", 2.0, 3.3, 0.45, 0.2)]
    pieces = net_pieces(mr, LAYERS, pads, tracks, vias, stubs=[stub], exit_layer="B.Cu")
    assert len(pieces) == 2 and pieces[0].label == "U1.1"
    assert (20, 25) in pieces[0].cells["F.Cu"]  # the stub
    assert (20, 33) in pieces[0].cells["B.Cu"]  # the fanout via
    assert (20, 45) in pieces[0].cells["B.Cu"]  # the exit corridor past the via


def test_close_net_needs_a_route_to_land_in_a_piece():
    mr = router()
    a = Piece({"F.Cu": [(10, 10)]}, "A")
    b = Piece({"F.Cu": [(50, 10)]}, "B")
    log = []

    def good(starts, goals):
        log.append((dict(starts), dict(goals)))
        return [("F.Cu", [(1.0, 1.0), (5.0, 1.0)])], [], mr

    open_nets: list[str] = []
    assert close_net("N", [a, b], good, open_nets) and open_nets == []
    assert log == [({"F.Cu": {(10, 10)}}, {"F.Cu": {(50, 10)}})]

    def short(starts, goals):
        return [("F.Cu", [(1.0, 1.0), (4.0, 1.0)])], [], mr

    open_nets = []
    assert not close_net("N", [a, b], short, open_nets)
    assert open_nets == ["N: route ended off every piece at (4.0, 1.0) (B)"]

    def none(starts, goals):
        return "no route"

    open_nets = []
    assert not close_net("N", [a, b], none, open_nets)
    assert open_nets == ["N: 1 piece(s) left open (B): no route"]


def test_touching_pieces_and_vias_count_as_joined():
    mr = router()
    a = Piece({"F.Cu": [(10, 10), (11, 10)]}, "A")
    b = Piece({"F.Cu": [(11, 10)]}, "B")  # shares a cell with A: no route needed
    c = Piece({"B.Cu": [(30, 10)]}, "C")  # reached through a via
    calls = []

    def via_route(starts, goals):
        calls.append(sorted(goals))
        return [("F.Cu", [(1.1, 1.0), (3.0, 1.0)])], [(3.0, 1.0)], mr

    assert close_net("N", [a, b, c], via_route, [])
    assert calls == [["B.Cu"]]
    assert reached([c], [], [(3.0, 1.0)], mr) == {0}


def test_connectivity_check_reports_pieces_islands_and_pours():
    p1 = Pad("N", "F.Cu", 1.0, 1.0, 1.0, 1.0, ref="R1", number="1")
    p2 = Pad("N", "F.Cu", 5.0, 1.0, 1.0, 1.0, ref="R1", number="2")
    joined = [Trk("N", "F.Cu", 0.3, [(1.0, 1.0), (5.0, 1.0)])]
    assert connectivity_check(joined, [], [p1, p2], LAYERS) == []
    short = [Trk("N", "F.Cu", 0.3, [(1.0, 1.0), (4.0, 1.0)])]
    assert connectivity_check(short, [], [p1, p2], LAYERS) == ["N: 2 pieces (R1.1; R1.2)"]
    island = [Trk("N", "B.Cu", 0.3, [(7.0, 7.0), (8.0, 7.0)])]
    out = connectivity_check(joined + island, [], [p1, p2], LAYERS)
    assert out == ["N: 2 pieces (R1.1 R1.2; island on B.Cu at (7.0,7.0))"]
    # the ground pour joins whatever reaches its layer
    g1 = Pad("GND", "F.Cu", 1.0, 5.0, 1.0, 1.0, ref="C1", number="2")
    g2 = Pad("GND", "F.Cu", 5.0, 5.0, 1.0, 1.0, ref="C2", number="2")
    vias = [Vi("GND", 1.0, 5.0, 0.8, 0.4), Vi("GND", 5.0, 5.0, 0.8, 0.4)]
    assert connectivity_check([], vias, [g1, g2], LAYERS) == ["GND: 2 pieces (C1.2; C2.2)"]
    assert connectivity_check([], vias, [g1, g2], LAYERS, pours={"GND": "B.Cu"}) == []
    stranded = connectivity_check([], vias[:1], [g1, g2], LAYERS, pours={"GND": "B.Cu"})
    assert stranded == ["GND: 2 pieces (C1.2; C2.2)"]


def test_stub_copper_joins_a_route_to_the_stub_it_lands_on():
    mr = router()
    fan = [("N", [(2.0, 2.0), (2.0, 2.5)], 0.8, True)]  # via at (2, 3.3), corridor to 5.3
    route = [("B.Cu", [(2.0, 4.5), (6.0, 4.5)])]
    assert stub_copper(mr, "B.Cu", route, [], fan) == [("B.Cu", [(2.0, 3.3), (2.0, 4.5)])]
    # a via dropped into the corridor from another layer owes it the same copper
    dropped = [("F.Cu", [(6.0, 4.5), (2.0, 4.5)])]
    assert stub_copper(mr, "B.Cu", dropped, [(2.0, 4.5)], fan) == [
        ("B.Cu", [(2.0, 3.3), (2.0, 4.5)])
    ]
    beside = [("B.Cu", [(2.4, 4.5), (6.0, 4.5)])]
    assert stub_copper(mr, "B.Cu", beside, [], fan) == []
    assert stub_copper(mr, "B.Cu", dropped, [], fan) == []  # another layer, no via
    # a plain runway (no via fitted) is copper only up to the stub end
    plain = [("N", [(2.0, 2.0), (2.0, 2.5)], 0.3, False)]  # runway cells from 2.5 to 2.8
    landing = [("F.Cu", [(2.0, 2.7), (5.0, 2.7)])]
    assert stub_copper(mr, "B.Cu", landing, [], plain) == [("F.Cu", [(2.0, 2.5), (2.0, 2.7)])]


def test_ground_drops_only_for_pieces_off_the_pour_layer():
    mr = router()
    on_pour = Piece({"F.Cu": [(10, 10)], "B.Cu": [(10, 10)]}, "A")
    off = Piece({"F.Cu": [(50, 50)]}, "B")
    calls = []

    def attempt(starts, goals):
        calls.append((starts, goals))
        return [("F.Cu", [(5.0, 5.0), (5.5, 5.0)])], [(5.5, 5.0)], mr

    open_nets: list[str] = []
    ground_drops(mr, "GND", [on_pour, off], "B.Cu", 3, attempt, open_nets, (4.0, 4.0, 7.0, 7.0))
    assert open_nets == [] and len(calls) == 1
    starts, goals = calls[0]
    assert starts == {"F.Cu": {(50, 50)}}
    assert set(goals) == {"B.Cu"}
    assert (55, 50) in goals["B.Cu"] and (35, 50) not in goals["B.Cu"]

    def none(starts, goals):
        return "no route"

    ground_drops(mr, "GND", [off], "B.Cu", 3, none, open_nets)
    assert open_nets == ["GND: B has no drop to the pour: no route"]
