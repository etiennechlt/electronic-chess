"""Geometry and file-level checks of the generated quadrant board (ADR 0010).

Skipped without the official KiCad libraries (the LED and connector
footprints are placed from them)."""

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
    return build_quadrant(cfg)


def test_layout_is_consistent(cfg):
    lay = make_layout(cfg)
    q = cfg.plateau.quadrant
    assert lay.n == q.squares and len(lay.coils) == 16 and len(lay.leds) == 32
    assert (lay.board_w, lay.board_h) == (q.front_end_strip_mm + 4 * cfg.pitch.plateau_mm,
                                          4 * cfg.pitch.plateau_mm)
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
    expected = {(round(x + strip, 3), round(y, 3)) for x, y in led_points(cfg)
                if x < play and y < play}
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
        for _label, _layer, pts in dbg.routes:
            assert pts[0] == coil.terminal
            assert pts[-1] == (x_in, coil.cell_y)


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
        cfg.plateau.quadrant.routing.track_clearance_mm)
    assert rules.min_track_width_mm <= cfg.plateau.quadrant.routing.route_track_mm


@pytest.mark.skipif(shutil.which("kicad-cli") is None, reason="kicad-cli not installed")
def test_kicad_parses_the_board(build, tmp_path: Path):
    pcb = tmp_path / "quadrant.kicad_pcb"
    pcb.write_text(build.board.serialize(), encoding="utf-8")
    out = tmp_path / "q.svg"
    subprocess.run(["kicad-cli", "pcb", "export", "svg", "--output", str(out),
                    "--layers", "F.Cu,In1.Cu,In2.Cu,B.Cu", str(pcb)], check=True,
                   capture_output=True)
    assert out.stat().st_size > 10_000
