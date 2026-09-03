"""Geometry and file-level checks of the generated quadrant board (ADR 0010).

Skipped without the official KiCad libraries (the LED and connector
footprints are placed from them)."""

import math
import os
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest
from analoggen.fplib import FOOTPRINT_DIR
from coilgen.project import project_json
from quadgen.board import build_quadrant, design_rules
from quadgen.layout import make_layout

from chessboard_calc.plateau import led_points

pytestmark = pytest.mark.skipif(not FOOTPRINT_DIR.exists(), reason="KiCad libraries not installed")


@pytest.fixture(scope="module")
def build(cfg):
    # front end placed but not routed: the strip routing takes minutes and
    # is exercised by the runbook build, see test_strip_routing_is_clean
    return build_quadrant(cfg, strip=False)


def test_layout_is_consistent(cfg):
    lay = make_layout(cfg)
    q = cfg.plateau.quadrant
    assert lay.n == q.squares and len(lay.coils) == 16 and len(lay.leds) == 32
    assert (lay.board_w, lay.board_h) == (
        q.front_end_strip_mm + 4 * cfg.pitch.plateau_mm,
        4 * cfg.pitch.plateau_mm,
    )
    # every coil has its own cell and its own escape lane in its band
    assert sorted(c.cell for c in lay.coils) == list(range(16))
    for band in range(2):
        lanes = [c.lane_y for c in lay.coils if c.band == band]
        assert len(set(lanes)) == 8
    # terminals alternate north and south by row so each pair of rows shares a band
    for c in lay.coils:
        assert (c.terminal[1] < c.center[1]) == (c.row % 2 == 1)


def test_led_positions_come_from_the_single_source(cfg):
    lay = make_layout(cfg)
    strip = cfg.plateau.quadrant.front_end_strip_mm
    play = cfg.plateau.quadrant.squares * cfg.pitch.plateau_mm
    expected = {
        (round(x + strip, 3), round(y, 3)) for x, y in led_points(cfg) if x < play and y < play
    }
    got = {(round(led.x, 3), round(led.y, 3)) for led in lay.leds}
    assert got == expected
    assert {led.corner for led in lay.leds} == set(cfg.plateau.leds.corners)


def test_build_is_clean(build):
    assert build.open_routes == []
    assert build.clearance_errors == []
    assert len(build.coils) == 16 and len(build.leds) == 32


def test_spirals_are_series_stacks(build):
    for coil in build.coils:
        sweeps = [p.total_turning_deg(coil.center) for p in coil.paths]
        assert all(s > 0 for s in sweeps), coil.name
        for a, b in zip(coil.paths, coil.paths[1:], strict=False):
            assert np.linalg.norm(a.points[-1] - b.points[0]) < 1e-6
        entry, exit_ = coil.paths[0].points[0], coil.paths[-1].points[-1]
        assert np.linalg.norm(entry - exit_) < 1e-6
        assert np.allclose(entry, coil.terminal, atol=1e-6)


def test_escapes_reach_their_cell(build, cfg):
    x_in = cfg.plateau.quadrant.strip.cell_entry_x_mm
    for coil, dbg in zip(build.layout.coils, build.coils, strict=True):
        layers = {layer for _l, layer, _p in dbg.routes}
        assert layers == {"F.Cu", "B.Cu"}
        for label, _layer, pts in dbg.routes:
            assert pts[0] == coil.terminal
            dy = -0.6 if label.endswith("_A") else 0.6  # A above, B below the cell center
            assert pts[-1] == (x_in, coil.cell_y + dy)


def test_led_chain_is_continuous(build):
    """Each LED's DOUT net is the next LED's DIN net, from the FPC pin to
    the FPC pin: 33 link nets for 32 LEDs."""
    nets = build.board.nets
    links = [n for n in nets if n.startswith("LED_L")]
    assert len(links) == 31
    assert "LED_DIN" in nets and "LED_DOUT" in nets


def test_project_file_carries_the_build_rules(build, cfg):
    import json

    rules = design_rules(cfg, build)
    pro = json.loads(project_json("quadrant", rules))
    assert pro["board"]["design_settings"]["rules"]["min_clearance"] == pytest.approx(
        cfg.plateau.quadrant.routing.track_clearance_mm
    )
    assert rules.min_track_width_mm <= cfg.plateau.quadrant.routing.route_track_mm


@pytest.mark.skipif(shutil.which("kicad-cli") is None, reason="kicad-cli not installed")
def test_kicad_parses_the_board(build, tmp_path: Path):
    pcb = tmp_path / "quadrant.kicad_pcb"
    pcb.write_text(build.board.serialize(), encoding="utf-8")
    out = tmp_path / "q.svg"
    subprocess.run(
        [
            "kicad-cli",
            "pcb",
            "export",
            "svg",
            "--output",
            str(out),
            "--layers",
            "F.Cu,In1.Cu,In2.Cu,B.Cu",
            str(pcb),
        ],
        check=True,
        capture_output=True,
    )
    assert out.stat().st_size > 10_000


def test_circuit_is_complete_and_unique(cfg):
    from quadgen.circuit import build_quadrant_circuit, cell_refs

    ckt, chain = build_quadrant_circuit(cfg)
    refs = [c.ref for c in ckt.components]
    assert len(refs) == len(set(refs))
    # 16 cells, each with its 13 parts and its net tie
    for k in range(1, 17):
        for ref in cell_refs(k).values():
            assert ref in refs, ref
    assert {"U1", "U2", "U3", "U4", "U5", "U6", "U7", "U8", "J1"} <= set(refs)
    # every FPC pin carries the yaml net, and the two mux enables exist
    j1 = next(c for c in ckt.components if c.ref == "J1")
    assert [j1.pins[str(i + 1)] for i in range(16)] == list(cfg.plateau.quadrant.link.pinout)
    assert "MUX_EN_L" in ckt.nets and "MUX_EN_H" in ckt.nets
    assert 200.0 <= chain.total_gain <= 260.0


def test_strip_placements_do_not_overlap(cfg):
    from quadgen.circuit import build_quadrant_circuit
    from quadgen.strip import strip_placements

    lay = make_layout(cfg)
    ckt, _chain = build_quadrant_circuit(cfg)
    placements = strip_placements(cfg, lay, ckt)  # raises on any courtyard overlap
    strip_w = cfg.plateau.quadrant.front_end_strip_mm
    for ref, (x, y, _rot) in placements.items():
        assert 0.0 < x < strip_w, ref
        assert 0.0 < y < lay.board_h, ref


@pytest.mark.skipif(shutil.which("kicad-cli") is None, reason="kicad-cli not installed")
def test_schematic_exports_a_netlist(cfg, tmp_path: Path):
    from analoggen.schematic import emit_schematic
    from quadgen.circuit import build_quadrant_circuit, schematic_groups

    ckt, _chain = build_quadrant_circuit(cfg)
    sch = tmp_path / "quadrant.kicad_sch"
    sch.write_text(
        emit_schematic(
            ckt, "quadrant", groups=schematic_groups(cfg), project="quadrant", paper="A0"
        ),
        encoding="utf-8",
    )
    out = tmp_path / "q.net"
    subprocess.run(
        ["kicad-cli", "sch", "export", "netlist", "--output", str(out), str(sch)],
        check=True,
        capture_output=True,
    )
    text = out.read_text(encoding="utf-8")
    assert '(net (code "' in text and "MUX_EN_L" in text and "C16_B" in text


@pytest.mark.skipif(not os.environ.get("SLOW"), reason="set SLOW=1 for the full build")
def test_strip_routing_is_clean(cfg):
    res = build_quadrant(cfg, strip=True)
    assert res.clearance_errors == []
    assert res.open_routes == []
    assert len(res.open_nets) <= 3, res.open_nets


def test_escape_stubs_only_on_fine_pitch():
    from analoggen.fplib import load_footprint
    from quadgen.escape import FINE_PITCH_MM, STUB_BEYOND_MM, escape_stubs, pad_pitch

    qfn = load_footprint("Package_DFN_QFN:QFN-24-1EP_4x4mm_P0.5mm_EP2.7x2.7mm")
    assert pad_pitch(qfn) < FINE_PITCH_MM
    nets = {str(i): f"N{i}" for i in range(1, 26)}
    stubs = escape_stubs(qfn, 10.0, 10.0, 0.0, nets)
    assert len(stubs) == 24  # every perimeter pad, not the exposed pad
    for _net, _num, (a, b), _runway, _via in stubs:
        # radial: the free end is farther from the center than the pad
        assert math.hypot(b[0] - 10.0, b[1] - 10.0) > math.hypot(a[0] - 10.0, a[1] - 10.0)
        assert math.hypot(b[0] - a[0], b[1] - a[1]) > STUB_BEYOND_MM
    # fanout vias alternate between two rows along each side
    from quadgen.escape import FANOUT_ROWS_MM

    west = sorted(
        (s for s in stubs if s[2][1][0] < 10.0 and abs(s[2][1][0] - s[2][0][0]) > 0.5),
        key=lambda s: s[2][0][1],
    )
    rows = [s[3] for s in west]
    assert set(rows) == set(FANOUT_ROWS_MM)
    assert all(a != b for a, b in zip(rows, rows[1:], strict=False))
    assert all(s[4] for s in stubs)
    sot = load_footprint("Package_TO_SOT_SMD:SOT-23")
    assert escape_stubs(sot, 0.0, 0.0, 0.0, {"1": "A", "2": "B", "3": "C"}) == []
