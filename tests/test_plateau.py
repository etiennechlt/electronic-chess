"""Geometry of the 8x8 board and of the clock, pinned from the yaml (ADR 0010)."""

import pytest

from chessboard_calc.plateau import (
    check,
    geometry,
    led_points,
    quadrant_origins,
    thin_base,
)


def test_yaml_is_consistent(cfg):
    assert check(cfg) == []


def test_pitch_is_decided_and_still_a_candidate(cfg):
    assert cfg.pitch.plateau_mm == 50.0
    assert cfg.pitch.plateau_mm in cfg.pitch.candidates_mm


def test_stack_heights(cfg):
    g = geometry(cfg)
    assert g.top_module_thickness_mm == pytest.approx(6.6)
    assert g.thin.total_height_mm == pytest.approx(20.6)
    assert g.gantry.total_height_mm == pytest.approx(53.6)
    assert cfg.gap.nominal_total_mm == pytest.approx(7.1)
    assert cfg.gap.nominal_total_mm <= cfg.gap.max_total_mm


def test_footprints(cfg):
    g = geometry(cfg)
    assert g.play_mm == 400.0
    assert g.module_mm == 432.0
    assert (g.thin.width_mm, g.thin.depth_mm) == (432.0, 432.0)
    assert (g.gantry.width_mm, g.gantry.depth_mm) == (532.0, 452.0)
    assert g.capture_band_mm == 50.0


def test_quadrants_tile_the_play_area(cfg):
    g = geometry(cfg)
    origins = quadrant_origins(cfg)
    assert len(origins) == g.quadrants_per_side**2 == 4
    covered = {(x + dx, y + dy) for x, y in origins
               for dx in (0.0, g.quadrant_mm) for dy in (0.0, g.quadrant_mm)}
    assert max(x for x, _ in covered) == g.play_mm
    assert max(y for _, y in covered) == g.play_mm


def test_led_points_are_uniform_and_inside_their_square(cfg):
    pts = led_points(cfg)
    assert len(pts) == 2 * cfg.plateau.grid**2 == 128
    p = cfg.pitch.plateau_mm
    inset = cfg.mockup.coil_board.leds.corner_inset_mm
    for x, y in pts:
        # every point sits exactly `inset` from two edges of its square
        assert min(x % p, p - x % p) == pytest.approx(inset)
        assert min(y % p, p - y % p) == pytest.approx(inset)
    # the same two corners on every square: NW and SE
    first = pts[0], pts[1]
    assert first[0] == pytest.approx((inset, inset))
    assert first[1] == pytest.approx((p - inset, p - inset))


def test_thin_base_hides_no_component_under_the_quadrants(cfg):
    assert cfg.plateau.module_underside_clear
    assert thin_base(cfg).cavity_mm == cfg.plateau.base.electronics_cavity_mm


def test_guards_fire(cfg):
    from chessboard_calc.config import BoardConfig
    raw = cfg.model_dump()
    raw["gap"]["air_mm"] = 1.0                 # LEDs and front end no longer fit
    assert "front end parts taller than the air clearance" in check(BoardConfig.model_validate(raw))
    raw = cfg.model_dump()
    raw["clock"]["rocker"]["length_mm"] = 118.0
    assert "rocker recess cuts the side walls" in check(BoardConfig.model_validate(raw))
    raw = cfg.model_dump()
    raw["plateau"]["leds"]["corners"] = ["NW", "NE"]
    with pytest.raises(ValueError):
        BoardConfig.model_validate(raw)
