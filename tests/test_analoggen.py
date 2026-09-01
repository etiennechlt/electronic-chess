"""Analog board generators: circuit invariants, filters, SPICE, schematic.

The full PCB routing takes minutes and runs on demand (see the
analog-board README); these tests cover everything upstream of it.
"""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from analoggen.bom import bom_csv, jlc_bom_csv  # noqa: E402
from analoggen.circuit import JOINT_ORDER, build_circuit  # noqa: E402
from analoggen.filters import round_e96  # noqa: E402
from analoggen.schematic import emit_schematic  # noqa: E402
from analoggen.spice import run_chain_ac  # noqa: E402
from coilgen.board import PAD_PLAN  # noqa: E402


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
        ["kicad-cli", "sch", "export", "netlist", "--output",
         str(tmp_path / "n.net"), str(sch)],
        capture_output=True, text=True, timeout=120,
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
        tracks.append(("WALL", 0.4,
                       [(ang_x, 8.0 + 1.9 * (k // 40)),
                        (ang_x, 8.2 + 1.9 * (k // 40))], "F.Cu"))
        tracks.append(("WALL", 0.4,
                       [(ang_x, 8.0 + 1.9 * (k // 40)),
                        (ang_x, 8.2 + 1.9 * (k // 40))], "B.Cu"))
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
