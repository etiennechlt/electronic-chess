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
    assert len(ckt.components) == 135
    solo = [n for n, pins in ckt.nets.items() if len(pins) < 2]
    assert solo == []


def test_chain_gain_within_spec(cfg, circuit):
    _, chain = circuit
    lo, hi = cfg.measurement.preamp_gain
    assert lo <= chain.total_gain <= hi


def test_joint_order_matches_coil_board(circuit):
    plan_nets = [f"C{t[0][1]}_{t[1]}" if t[0] != "GND" else "GND" for t in PAD_PLAN]
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
