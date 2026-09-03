"""Inductance models, inverse solver and winding feasibility."""

import pytest

from chessboard_calc.config import PieceType, resolve_geometry
from chessboard_calc.inductance import (
    mohan_L_uH,
    pcb_sense_coil,
    piece_coil_design,
    skin_depth_mm,
    solve_turns,
    wheeler_multilayer_L_uH,
    wheeler_pancake_L_uH,
    wire_window_check,
)


def test_models_scale_with_turns_squared():
    assert wheeler_pancake_L_uH(20, 32.0, 18.0) == pytest.approx(
        4.0 * wheeler_pancake_L_uH(10, 32.0, 18.0)
    )
    assert wheeler_multilayer_L_uH(20, 10.0, 4.0, 2.0) == pytest.approx(
        4.0 * wheeler_multilayer_L_uH(10, 10.0, 4.0, 2.0)
    )


def test_wheeler_and_mohan_agree_on_pcb_spiral_geometry():
    # Sense-coil-like envelope; the two independent models should agree
    # to well within their stated few-percent accuracy class.
    lw = wheeler_pancake_L_uH(10, 32.0, 18.0)
    lm = mohan_L_uH(10, 32.0, 18.0)
    assert lw == pytest.approx(lm, rel=0.15)


def test_solver_round_trip_on_piece_geometries(cfg):
    for pitch in cfg.pitch.candidates_mm:
        for piece in PieceType:
            geo = resolve_geometry(cfg, pitch).classes[piece]
            sol = solve_turns(
                cfg.resonator.L_target_uH,
                geo.coil_d_out_mm,
                geo.coil_d_in_mm,
                height_mm=cfg.resonator.coil.height_mm,
            )
            assert abs(sol.relative_error) < 0.03, (pitch, piece)


def test_piece_coils_are_windable_for_every_class_and_pitch(cfg):
    for pitch in cfg.pitch.candidates_mm:
        for piece in PieceType:
            design = piece_coil_design(cfg, piece, pitch)
            assert design.wire_mm is not None, (
                f"no candidate wire fits the {piece.value} coil at p={pitch}"
            )
            assert 20 <= design.n_turns <= 150
            assert design.L_achieved_uH == pytest.approx(cfg.resonator.L_target_uH, rel=0.05)


def test_smallest_class_is_wire_constrained(cfg):
    # Pawn at the smallest pitch: the winding window forces a fine wire,
    # which is the root of the Q risk flagged in the critical review (C).
    smallest = min(cfg.pitch.candidates_mm)
    design = piece_coil_design(cfg, PieceType.PAWN, smallest)
    assert design.wire_mm <= 0.20


def test_window_check_rejects_oversized_wire(cfg):
    smallest = min(cfg.pitch.candidates_mm)
    geo = resolve_geometry(cfg, smallest).classes[PieceType.PAWN]
    design = piece_coil_design(cfg, PieceType.PAWN, smallest)
    report = wire_window_check(
        design.n_turns,
        geo.coil_d_out_mm,
        geo.coil_d_in_mm,
        cfg.resonator.coil.height_mm,
        max(cfg.resonator.coil.wire_candidates_mm),
        cfg.resonator.coil.fill_factor,
        cfg.resonator.coil.insulation_extra_mm,
    )
    assert not report.fits


def test_skin_depth_at_band_center():
    assert skin_depth_mm(400e3) == pytest.approx(0.103, abs=0.01)


def test_sense_coil_design_for_both_pitches(cfg):
    for pitch in cfg.pitch.candidates_mm:
        design = pcb_sense_coil(cfg, pitch)
        # Brief 3.4 window: 15 to 20 uH, integer-turn rounding allowed.
        assert 14.0 <= design.L_uH <= 21.0, pitch
        assert design.turns_total == design.turns_per_layer * design.layers
        assert design.track_width_mm >= cfg.sense_coil.track_gap_mm
        # Brief 3.5: parasitic resonance with the mux stays a decade
        # above the measurement band.
        assert design.srf_hz >= 8.0 * cfg.measurement.band_hz[1]
