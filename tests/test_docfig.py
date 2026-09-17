"""The documentation figures build from the yaml and carry the model's numbers."""

import xml.etree.ElementTree as ET

import pytest
from docfig import FIGURES
from docfig.common import fr_num, standalone
from docfig.q import plan_rows

from chessboard_calc.config import Color, PieceType
from chessboard_calc.resonance import frequency_plan, ringdown_tau_us


@pytest.mark.parametrize("name", sorted(FIGURES))
def test_every_figure_is_well_formed_svg(cfg, name):
    svg = standalone(FIGURES[name](cfg))
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")
    assert root.get("viewBox", "").startswith("0 0 ")
    assert root.get("aria-label")
    assert chr(0x2014) not in svg and chr(0x2013) not in svg  # no dashes in the texts


def test_plan_figure_lists_the_twelve_notes(cfg):
    svg = FIGURES["q-plan.svg"](cfg)
    for line in frequency_plan(cfg).lines:
        assert f">{line.f0_hz / 1e3:.0f}<" in svg
    assert len(plan_rows(cfg)) == 12


def test_ringdown_figure_uses_the_model_tau(cfg):
    svg = FIGURES["q-ringdown.svg"](cfg)
    f0 = frequency_plan(cfg).line(PieceType.PAWN, Color.BLACK).f0_hz
    tau = ringdown_tau_us(f0, cfg.resonator.q_nominal)
    assert f"τ = {fr_num(tau, 0)} µs" in svg


def test_fr_num():
    assert fr_num(7.06) == "7,1"
    assert fr_num(50.0, 0) == "50"
    assert fr_num(2.5) == "2,5"
    assert fr_num(1234.5, 1) == "1 234,5"
