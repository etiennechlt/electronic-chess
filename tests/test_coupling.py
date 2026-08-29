"""Mutual inductance sanity, coupling behavior and signal estimates."""

import math

import pytest

from chessboard_calc.config import Color, PieceType
from chessboard_calc.coupling import (
    coupling_k,
    mutual_coaxial_loops_nH,
    ringdown_signal,
    signal_vs_pitch,
)
from chessboard_calc.physics import MU0_H_PER_M


def test_mutual_is_symmetric():
    assert mutual_coaxial_loops_nH(5.0, 12.0, 4.0) == pytest.approx(
        mutual_coaxial_loops_nH(12.0, 5.0, 4.0)
    )


def test_mutual_decreases_with_axial_gap():
    gaps = [2.0, 4.0, 8.0, 16.0]
    values = [mutual_coaxial_loops_nH(8.0, 16.0, g) for g in gaps]
    assert values == sorted(values, reverse=True)
    assert all(v > 0.0 for v in values)


def test_mutual_matches_dipole_asymptote_at_large_distance():
    r1_mm, r2_mm, d_mm = 2.0, 3.0, 60.0
    exact_nh = mutual_coaxial_loops_nH(r1_mm, r2_mm, d_mm)
    r1, r2, d = r1_mm * 1e-3, r2_mm * 1e-3, d_mm * 1e-3
    dipole_nh = MU0_H_PER_M * math.pi * r1**2 * r2**2 / (2.0 * d**3) * 1e9
    assert exact_nh == pytest.approx(dipole_nh, rel=0.1)


def test_coupling_factor_is_physical_for_every_class(cfg):
    for pitch in cfg.pitch.candidates_mm:
        for piece in PieceType:
            k = coupling_k(cfg, piece, pitch)
            assert 0.0 < k < 0.5, (pitch, piece)


def test_coupling_decreases_with_gap(cfg):
    pitch = cfg.pitch.mockup_mm
    near = coupling_k(cfg, PieceType.PAWN, pitch, air_gap_mm=cfg.gap.air_gap_mm)
    far_gap = cfg.gap.max_total_mm - cfg.gap.pcb_mm
    far = coupling_k(cfg, PieceType.PAWN, pitch, air_gap_mm=far_gap)
    assert far < near


def test_worst_case_snr_clears_the_brief_criterion(cfg):
    # Measurement 4 criterion: SNR >= 20 dB on the peak at nominal gap.
    # The model should clear it with a wide margin for the black pawn,
    # the lowest frequency and the smallest coil.
    for pitch in cfg.pitch.candidates_mm:
        est = ringdown_signal(cfg, PieceType.PAWN, Color.BLACK, pitch)
        assert est.snr_db >= cfg.measurement.snr_min_db, pitch
        assert est.snr_avg_db > est.snr_db


def test_signal_drops_with_gap(cfg):
    pitch = cfg.pitch.mockup_mm
    near = ringdown_signal(cfg, PieceType.PAWN, Color.BLACK, pitch)
    far_gap = cfg.gap.max_total_mm - cfg.gap.pcb_mm
    far = ringdown_signal(cfg, PieceType.PAWN, Color.BLACK, pitch, air_gap_mm=far_gap)
    assert far.emf_after_blanking_v < near.emf_after_blanking_v


def test_pitch_comparison_stays_in_the_same_ballpark(cfg):
    # Brief 5.1 claims only ~5 % of signal loss from p=50 to p=40. The
    # first-order model is not trusted to that precision; the gate only
    # asserts the two pitches stay within the same ballpark, and the
    # report prints the actual ratio for the mockup to verify.
    estimates = {e.pitch_mm: e for e in signal_vs_pitch(cfg)}
    lo, hi = min(estimates), max(estimates)
    ratio = estimates[lo].emf_after_blanking_v / estimates[hi].emf_after_blanking_v
    assert 0.5 <= ratio <= 1.3
