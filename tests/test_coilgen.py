"""Geometry and file-level checks of the generated mockup coil board."""

import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest
from coilgen.board import build_coil_board, design_rules
from coilgen.geometry import min_adjacent_turn_gap_mm
from coilgen.project import project_json
from scipy.spatial import cKDTree


@pytest.fixture(scope="module")
def build(cfg):
    return build_coil_board(cfg)


def _sample_segments(polyline_sets, step_mm=0.25):
    """Sample points along polylines: [(net, layer, (N,2) array), ...]."""
    out = []
    for net, layer, pts in polyline_sets:
        pts = np.asarray(pts, dtype=float)
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]
            n = max(2, int(np.linalg.norm(b - a) / step_mm) + 1)
            t = np.linspace(0.0, 1.0, n)[:, None]
            out.append((net, layer, a[None, :] * (1 - t) + b[None, :] * t))
    return out


def _copper_items(build):
    items = []
    for coil in build.coils:
        net = f"C{coil.name[1]}"
        for path in coil.paths:
            items.append((net, path.layer, path.points, build.track_width_mm))
        for _label, layer, pts in coil.routes:
            items.append((net, layer, np.asarray(pts), 0.5))
    for net, layer, width, pts in build.led_tracks:
        if len(pts) >= 2:
            items.append((net, layer, np.asarray(pts), width))
    return items


def test_layers_share_the_same_circulation_direction(build):
    for coil in build.coils:
        sweeps = [p.total_turning_deg(coil.center) for p in coil.paths]
        assert all(s > 0 for s in sweeps), coil.name
        # 5 turns per layer plus the 90 degree link arcs.
        assert sweeps[0] == pytest.approx(1800.0, abs=5.0)
        assert sweeps[1] == pytest.approx(1890.0, abs=5.0)
        assert sweeps[3] == pytest.approx(1980.0, abs=5.0)


def test_series_path_is_continuous_and_terminals_stack(build):
    for coil in build.coils:
        for a, b in zip(coil.paths, coil.paths[1:], strict=False):
            assert np.linalg.norm(a.points[-1] - b.points[0]) < 1e-6, coil.name
        entry = coil.paths[0].points[0]
        exit_ = coil.paths[-1].points[-1]
        assert np.linalg.norm(entry - exit_) < 1e-6, coil.name
        assert np.allclose(entry, coil.terminal, atol=1e-6)


def test_adjacent_turn_gap_clears_the_design_rule(cfg, build):
    geo_gap = min_adjacent_turn_gap_mm(
        r_in_mm=0.45 * cfg.pitch.mockup_mm / 2.0,
        r_out_mm=0.80 * cfg.pitch.mockup_mm / 2.0,
        turns=build.turns_per_layer,
        width_mm=build.track_width_mm,
    )
    assert geo_gap >= cfg.mockup.coil_board.track_clearance_mm
    assert geo_gap == pytest.approx(cfg.sense_coil.track_gap_mm, abs=1e-6)


def test_junction_vias_are_distinct_and_apart(build):
    for coil in build.coils:
        vias = np.asarray(coil.vias)
        assert len(vias) == 3
        d = np.linalg.norm(vias[:, None, :] - vias[None, :, :], axis=-1)
        d[np.diag_indices(3)] = np.inf
        assert d.min() > 2.0


def test_everything_stays_inside_the_board(cfg, build):
    w, h = build.outline_mm
    margin = cfg.mockup.coil_board.edge_clearance_mm
    for net, _layer, pts in (
        (c[0], c[1], c[2]) for c in ((f"C{co.name[1]}", p.layer, p.points)
                                     for co in build.coils for p in co.paths)
    ):
        assert pts[:, 0].min() >= margin and pts[:, 0].max() <= w - margin, net
        assert pts[:, 1].min() >= margin and pts[:, 1].max() <= h - margin, net


def test_cross_net_copper_clearance(cfg, build):
    """Sampled min distance between copper of different nets, per layer."""
    items = _copper_items(build)
    clearance = cfg.mockup.coil_board.track_clearance_mm
    layers = {layer for _n, layer, _p, _w in items}
    for layer in layers:
        layer_items = [(n, la, p, w) for n, la, p, w in items if la == layer]
        for i, (net_a, _l, pts_a, w_a) in enumerate(layer_items):
            samples_a = np.vstack([s for _n, _la, s in _sample_segments([(net_a, layer, pts_a)])])
            tree = cKDTree(samples_a)
            for net_b, _lb, pts_b, w_b in layer_items[i + 1:]:
                if net_b == net_a:
                    continue
                samples_b = np.vstack(
                    [s for _n, _la, s in _sample_segments([(net_b, layer, pts_b)])]
                )
                dmin = tree.query(samples_b)[0].min()
                need = (w_a + w_b) / 2.0 + clearance
                assert dmin >= need, (layer, net_a, net_b, dmin, need)


def test_serialized_board_is_balanced_and_complete(build):
    text = build.board.serialize()
    assert text.count("(") == text.count(")")
    assert text.count("(via ") == 12 + len(build.led_vias)
    # joint + 4 mount + 4 magnet + 8 LED + 8 decoupling
    assert text.count("(footprint ") == 1 + 4 + 4 + 16
    assert "Edge.Cuts" in text and "F.SilkS" in text
    seg_count = text.count("(segment ")
    assert seg_count > 5000  # four coils, four layers of sampled spirals


def test_led_subsystem(cfg, build):
    """Eight chained LEDs at opposite corners, clear of the spirals."""
    leds = cfg.mockup.coil_board.leds
    assert len(build.leds) == 4 * leds.per_square
    p = cfg.pitch.mockup_mm
    per_square: dict[str, list] = {}
    for _ref, (x, y) in build.leds:
        sq = (int(x // p), int(y // p))
        per_square.setdefault(sq, []).append((x, y))
    for _sq, pts in per_square.items():
        assert len(pts) == leds.per_square
        (x1, y1), (x2, y2) = pts
        # opposite corners: both offsets flip sign
        assert abs((x1 + x2) / 2.0 % p - p / 2.0) < 1e-6
        assert abs((y1 + y2) / 2.0 % p - p / 2.0) < 1e-6
    nets = {n for n, _l, _w, _p in build.led_tracks}
    assert "LED_DIN" in nets and "LED_5V" in nets and "GND" in nets
    assert sum(1 for n in nets if n.startswith("LED_L")) == 7


@pytest.mark.skipif(shutil.which("kicad-cli") is None, reason="kicad-cli not installed")
def test_kicad_cli_parses_the_board(build, tmp_path):
    pcb = tmp_path / "coil-board.kicad_pcb"
    pcb.write_text(build.board.serialize(), encoding="utf-8")
    out_svg = tmp_path / "out.svg"
    proc = subprocess.run(
        ["kicad-cli", "pcb", "export", "svg", "--output", str(out_svg),
         "--layers", "F.Cu,B.Cu,Edge.Cuts", str(pcb)],
        capture_output=True, text=True, timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    assert out_svg.exists() and out_svg.stat().st_size > 10_000


def test_committed_project_matches_this_build(cfg, build):
    """The .kicad_pro in the repo is what this build emits, rule for rule."""
    path = (Path(__file__).resolve().parents[1] / "hardware" / "mockup-2x2"
            / "coil-board" / "coil-board.kicad_pro")
    emitted = json.loads(project_json("coil-board", design_rules(cfg, build)))
    assert json.loads(path.read_text(encoding="utf-8")) == emitted
