"""Sanity checks of the CadQuery parts (skipped when cadquery is absent,
for instance in the lightweight CI job)."""

import math
import sys
from pathlib import Path

import pytest

cq = pytest.importorskip("cadquery")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mechanical"))

from common import FIT_TIGHT, puck_dims  # noqa: E402
from parts import magnet_bracket_base, magnet_cup, test_puck, winding_jig  # noqa: E402

from chessboard_calc.config import PieceType  # noqa: E402


def test_puck_has_cavities_and_fits_the_class_diameter(cfg):
    pitch = cfg.pitch.mockup_mm
    for piece in (PieceType.PAWN, PieceType.ROOK):
        dims = puck_dims(cfg, piece, pitch)
        part = test_puck(dims)
        solid = part.val()
        full = math.pi * (dims.base_d / 2.0) ** 2 * dims.height
        assert 0.3 * full < solid.Volume() < 0.95 * full
        bb = solid.BoundingBox()
        assert bb.xlen == pytest.approx(dims.base_d, abs=0.1)
        assert dims.magnet_d + 2.0 * FIT_TIGHT < dims.coil_d


def test_jig_core_matches_coil_inner_diameter(cfg):
    pitch = cfg.pitch.mockup_mm
    dims = puck_dims(cfg, PieceType.PAWN, pitch)
    d_in = cfg.resonator.coil.inner_ratio * dims.coil_d
    part = winding_jig(dims.coil_d, d_in, dims.coil_h)
    assert part.val().Volume() > 0.0


def test_bracket_and_cup_build(cfg):
    mm = cfg.mockup.coil_board.magnet_mount
    base = magnet_bracket_base(mm.hole_spacing_mm, cfg.carriage.magnet.d_mm)
    cup = magnet_cup(cfg.carriage.magnet.d_mm, cfg.carriage.magnet.h_mm)
    assert base.val().Volume() > 0.0
    assert cup.val().Volume() > 0.0
    plate = mm.hole_spacing_mm + 12.0
    assert base.val().BoundingBox().xlen == pytest.approx(plate, abs=0.2)
