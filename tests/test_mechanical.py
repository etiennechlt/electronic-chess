"""Sanity checks of the CadQuery parts (skipped when cadquery is absent,
for instance in the lightweight CI job)."""

import math
import sys
from pathlib import Path

import pytest

cq = pytest.importorskip("cadquery")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mechanical"))

from common import FIT_TIGHT, puck_dims  # noqa: E402
from parts import magnet_bracket_base, magnet_cup, piece_puck, winding_jig  # noqa: E402

from chessboard_calc.config import PieceType  # noqa: E402


def test_puck_has_cavities_and_fits_the_class_diameter(cfg):
    pitch = cfg.pitch.mockup_mm
    for piece in (PieceType.PAWN, PieceType.ROOK):
        dims = puck_dims(cfg, piece, pitch)
        part = piece_puck(dims)
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


def test_clock_shell_has_its_cutouts(cfg):
    import clock

    closed = clock.body(cfg).faces("<Z").shell(-cfg.clock.wall_mm).val()
    cut = clock.shell(cfg).val()
    win_w, win_h = cfg.clock.display.window_mm
    removed = closed.Volume() - cut.Volume()
    # at least the display window through the wall plus the rocker recess
    assert removed > win_w * win_h * cfg.clock.wall_mm
    bb = cut.BoundingBox()
    assert bb.xlen == pytest.approx(cfg.clock.body_mm[0], abs=0.2)
    assert bb.zlen == pytest.approx(cfg.clock.height_rear_mm, abs=0.2)


def test_rocker_bar_tilts_within_the_recess(cfg):
    import clock

    bar = clock.rocker_bar(cfg).val().BoundingBox()
    rk = cfg.clock.rocker
    assert bar.zmin >= cfg.clock.height_rear_mm - rk.recess_mm - 0.5
    assert bar.xlen == pytest.approx(rk.length_mm, abs=1.5)


def test_plateau_assemblies_build(cfg):
    import plateau

    from chessboard_calc.plateau import led_points

    thin = plateau.assembly(cfg, gantry=False, with_pieces=False)
    gantry = plateau.assembly(cfg, gantry=True, with_pieces=False)
    groups_thin = {p.group for p in thin}
    assert groups_thin == {"base", "elec", "quad", "bois"}
    assert {p.group for p in gantry} == groups_thin | {"chariot", "ailes"}
    assert sum(1 for p in thin if p.name == "WS2812B") == len(led_points(cfg))
    wood = next(p for p in thin if p.group == "bois" and p.name.startswith("contreplaque"))
    bb = wood.shape.BoundingBox()
    from chessboard_calc.plateau import geometry

    assert bb.xlen == pytest.approx(geometry(cfg).module_mm, abs=0.2)
    # the wood sits exactly one air gap above the quadrant PCBs
    pcb = next(p for p in thin if p.name.startswith("quadrant Q1"))
    assert bb.zmin - pcb.shape.BoundingBox().zmax == pytest.approx(cfg.gap.air_mm)
