"""Analog board generators: circuit invariants, filters, SPICE, schematic.

The full PCB routing takes minutes and runs on demand (see the
analog-board README); these tests cover everything upstream of it.
"""

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from analoggen.bom import bom_csv, jlc_bom_csv  # noqa: E402
from analoggen.circuit import JOINT_ORDER, build_circuit  # noqa: E402
from analoggen.filters import round_e96  # noqa: E402
from analoggen.schematic import emit_schematic  # noqa: E402
from analoggen.spice import run_chain_ac  # noqa: E402
from coilgen.board import PAD_PLAN  # noqa: E402

from chessboard_calc.config import load_config  # noqa: E402


@pytest.fixture(scope="module")
def circuit(cfg):
    ckt, chain = build_circuit(cfg)
    return ckt, chain


def test_circuit_size_and_no_floating_nets(circuit):
    ckt, _ = circuit
    assert len(ckt.components) == 138
    solo = [n for n, pins in ckt.nets.items() if len(pins) < 2]
    assert solo == []


def test_chain_gain_within_spec(cfg, circuit):
    _, chain = circuit
    lo, hi = cfg.measurement.preamp_gain
    assert lo <= chain.total_gain <= hi


def test_joint_order_matches_coil_board(circuit):
    special = {"GND": "GND", "LED_DIN": "LED_DIN5", "LED_5V": "5V_BUCK"}
    plan_nets = [special.get(t[0], f"C{t[0][1]}_{t[1]}") for t in PAD_PLAN]
    assert plan_nets == JOINT_ORDER


def test_e96_rounding():
    assert round_e96(795.77) == pytest.approx(787.0)
    assert round_e96(523000) == pytest.approx(523000.0)


def test_bom_exports(circuit):
    ckt, _ = circuit
    assert bom_csv(ckt).count("\n") > 20
    jlc = jlc_bom_csv(ckt)
    assert "Designator" in jlc and "DNP" not in jlc


@pytest.mark.skipif(shutil.which("ngspice") is None, reason="ngspice not installed")
def test_spice_chain_validates_the_analog_path(cfg, tmp_path):
    _, chain = build_circuit(cfg)
    rep = run_chain_ac(chain, tmp_path)
    assert rep.gain_400k == pytest.approx(200.0, rel=0.08)
    assert rep.f_low_3db_hz == pytest.approx(cfg.mockup.analog.filter.hp_hz, rel=0.15)
    assert rep.f_high_3db_hz == pytest.approx(cfg.mockup.analog.filter.lp_hz, rel=0.15)
    assert rep.att_1m5_db > 14.0
    assert rep.att_50k_db > 18.0


@pytest.mark.skipif(shutil.which("kicad-cli") is None, reason="kicad-cli not installed")
def test_schematic_is_parsed_by_kicad(circuit, tmp_path):
    ckt, _ = circuit
    sch = tmp_path / "analog.kicad_sch"
    sch.write_text(emit_schematic(ckt, "test"), encoding="utf-8")
    proc = subprocess.run(
        ["kicad-cli", "sch", "export", "netlist", "--output", str(tmp_path / "n.net"), str(sch)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    netlist = (tmp_path / "n.net").read_text()
    for net in ("VREF", "AMP_OUT", "DRIVE_BUS", "C1_A", "5VA"):
        assert net in netlist


def test_finish_pass_joins_and_respects_clearance():
    from dataclasses import dataclass

    from analoggen.finish import CLEAR, finish_pass

    @dataclass(frozen=True)
    class FakePad:
        ref: str
        number: str
        net: str | None
        x: float
        y: float
        w: float
        h: float
        tht: bool

    pads = [
        FakePad("R1", "1", "A", 10.0, 10.0, 1.0, 0.6, False),
        FakePad("R2", "1", "A", 13.0, 10.0, 1.0, 0.6, False),
        # foreign obstacle right on the straight line between the pieces
        FakePad("R3", "1", "B", 11.5, 10.0, 0.6, 0.6, False),
        # a pair that nothing can join: walled in by foreign copper
        FakePad("R4", "1", "C", 40.0, 10.0, 0.5, 0.5, False),
        FakePad("R5", "1", "C", 44.0, 10.0, 0.5, 0.5, False),
    ]
    tracks: list = []
    vias: list = []
    for k in range(160):
        ang_x = 42.0 + 3.4 * ((k % 40) - 20) / 20.0
        tracks.append(
            ("WALL", 0.4, [(ang_x, 8.0 + 1.9 * (k // 40)), (ang_x, 8.2 + 1.9 * (k // 40))], "F.Cu")
        )
        tracks.append(
            ("WALL", 0.4, [(ang_x, 8.0 + 1.9 * (k // 40)), (ang_x, 8.2 + 1.9 * (k // 40))], "B.Cu")
        )
    log = finish_pass(pads, tracks, vias)
    joined = [line for line in log if line.startswith("A:")]
    assert joined, "net A should be joined around the obstacle"
    new_a = [t for t in tracks if t[0] == "A"]
    assert new_a
    from shapely.geometry import LineString
    from shapely.geometry import box as _box

    obstacle = _box(11.2, 9.7, 11.8, 10.3)
    for _net, w, pts, _layer in new_a:
        assert LineString(pts).buffer(w / 2.0).distance(obstacle) >= CLEAR - 1e-9
    assert not [line for line in log if line.startswith("C:")]


@dataclass(frozen=True)
class Pad:
    """The pad fields the routing bookkeeping reads."""

    ref: str
    number: str
    net: str | None
    x: float
    y: float
    w: float
    h: float
    tht: bool = False


def test_the_exact_check_counts_the_pieces_kicad_would():
    from analoggen import connect
    from shapely.geometry import box as _box

    pads = [
        Pad("R1", "1", "A", 10.0, 10.0, 1.0, 0.6),
        Pad("R2", "1", "A", 13.0, 10.0, 1.0, 0.6),
        Pad("R3", "1", "B", 20.0, 10.0, 1.0, 0.6),
        Pad("R4", "1", "B", 23.0, 10.0, 1.0, 0.6),
    ]
    # a track that stops short of the second pad leaves the net open
    short = ("A", 0.25, [(10.5, 10.0), (12.0, 10.0)], "F.Cu")
    assert connect.errors(pads, [short], [], 0.6) == [
        "A: 2 pieces (R1.1; R2.1)",
        "B: 2 pieces (R3.1; R4.1)",
    ]
    full = ("A", 0.25, [(10.5, 10.0), (12.5, 10.0)], "F.Cu")
    # the two halves of B change layer without a via: two pieces still
    two_layers = [
        full,
        ("B", 0.25, [(20.5, 10.0), (21.5, 10.0)], "F.Cu"),
        ("B", 0.25, [(21.5, 10.0), (22.2, 10.0)], "B.Cu"),
    ]
    assert [e.split(":")[0] for e in connect.errors(pads, two_layers, [], 0.6)] == ["B"]
    # one via down, one via back up under the second pad, and B is whole
    vias = [("B", 21.5, 10.0), ("B", 22.2, 10.0)]
    assert connect.errors(pads, two_layers, vias, 0.6) == []

    # a pour joins what its own island covers, and only that
    ground = [
        Pad("J1", "1", "GND", 30.0, 10.0, 1.6, 1.6, True),
        Pad("J1", "2", "GND", 40.0, 10.0, 1.6, 1.6, True),
    ]
    one = [_box(28.0, 8.0, 42.0, 12.0)]
    assert connect.errors(ground, [], [], 0.6, islands=one) == []
    cut = [_box(28.0, 8.0, 34.0, 12.0), _box(36.0, 8.0, 42.0, 12.0)]
    assert [e.split(":")[0] for e in connect.errors(ground, [], [], 0.6, islands=cut)] == ["GND"]


def test_the_maze_goes_around_a_wall_the_joints_cannot():
    from analoggen import maze
    from analoggen.finish import CLEAR, THERMAL_PAD_MM, VIA_R, W_JOIN
    from shapely.geometry import LineString

    pads = [Pad("R1", "1", "A", 10.0, 10.0, 1.0, 0.6), Pad("R2", "1", "A", 16.0, 10.0, 1.0, 0.6)]
    # a wall between them, with one gap 2 mm north of the straight line
    wall = [
        ("W", 0.4, [(13.0, 4.0), (13.0, 8.2)], "F.Cu"),
        ("W", 0.4, [(13.0, 9.8), (13.0, 20.0)], "F.Cu"),
    ]
    piece_a = (LineString([(10.0, 10.0), (10.0, 10.0)]).buffer(0.3), None)
    piece_b = (LineString([(16.0, 10.0), (16.0, 10.0)]).buffer(0.3), None)
    plan = maze.maze_join(
        "A", piece_a, piece_b, pads, wall, [], W_JOIN, CLEAR, VIA_R, THERMAL_PAD_MM
    )
    assert plan, "the maze should thread the gap in the wall"
    drawn = maze.plan_geometry(plan, W_JOIN, VIA_R)
    obstacles = [LineString(pts).buffer(w / 2.0) for _n, w, pts, _la in wall]
    for layer, geoms in drawn.items():
        for g in geoms:
            for o in obstacles:
                assert g.distance(o) >= CLEAR - 1e-9, layer


def test_the_hand_seeds_of_the_analog_board_stay_legal():
    """Every seeded route is re-checked against the real pad geometry."""
    from analoggen.pcb import Router, _hand_seeds, _pad_instances, full_placements

    cfg = load_config()
    ckt, _chain = build_circuit(cfg)
    pads = _pad_instances(ckt, full_placements(cfg))
    router = Router(pads)
    _hand_seeds(router, pads)
    seeded = {net for net, _w, _pts, _layer in router.tracks}
    for net in ("BUCK_FB", "C2_A", "C3_B", "M1_A", "M2_A", "VREF", "GND"):
        assert net in seeded, net


def test_no_two_courtyards_of_the_analog_board_overlap():
    """What the KiCad DRC calls a courtyard overlap, checked at build time.

    Not a short circuit and no copper rule says a word about it, but two
    parts that claim the same room are a rework at assembly.
    """
    from analoggen.pcb import full_placements
    from analoggen.yards import courtyard_errors, footprint_courtyard

    cfg = load_config()
    ckt, _chain = build_circuit(cfg)
    assert footprint_courtyard("Resistor_SMD:R_0603_1608Metric").bounds == (
        -1.48,
        -0.73,
        1.48,
        0.73,
    )
    assert courtyard_errors(ckt, full_placements(cfg)) == []


def test_the_maze_coarsens_its_raster_for_a_haul_across_the_board():
    """A 50 mm link would rasterize to millions of cells at 0.05 mm.

    The window is coarsened until it fits the ceiling, and the plan is
    still checked in exact geometry: coarse costs detail, not legality.
    """
    from analoggen import maze
    from analoggen.finish import CLEAR, THERMAL_PAD_MM, VIA_R, W_JOIN
    from shapely.geometry import LineString

    pads = [Pad("R1", "1", "A", 6.0, 30.0, 1.0, 0.6), Pad("R2", "1", "A", 56.0, 30.0, 1.0, 0.6)]
    # a wall on both layers, its only gap 8 mm north of the straight line
    wall = [
        (net, 0.4, [(31.0, y0), (31.0, y1)], layer)
        for layer in ("F.Cu", "B.Cu")
        for net, y0, y1 in (("W", 8.0, 21.0), ("W", 23.0, 52.0))
    ]
    piece_a = (LineString([(6.0, 30.0), (6.0, 30.0)]).buffer(0.3), None)
    piece_b = (LineString([(56.0, 30.0), (56.0, 30.0)]).buffer(0.3), None)
    plan = maze.maze_join(
        "A", piece_a, piece_b, pads, wall, [], W_JOIN, CLEAR, VIA_R, THERMAL_PAD_MM
    )
    assert plan, "the maze should haul across the board through the gap"
    drawn = maze.plan_geometry(plan, W_JOIN, VIA_R)
    for layer, geoms in drawn.items():
        obstacles = [LineString(p).buffer(w / 2.0) for _n, w, p, la in wall if la == layer]
        for g in geoms:
            for o in obstacles:
                assert g.distance(o) >= CLEAR - 1e-9, layer
