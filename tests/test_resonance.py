"""Frequency plan pinned against the specification table and separation gates."""

import pytest

from chessboard_calc.config import BoardConfig, Color, PieceType
from chessboard_calc.resonance import check_separation, frequency_plan, ringdown_tau_us

# The brief's table (3.3), rounded to the kHz. The config only stores L
# and the capacitor values; these figures are assertions, not inputs.
BRIEF_TABLE_KHZ = {
    (PieceType.KING, Color.WHITE): 612,
    (PieceType.QUEEN, Color.WHITE): 559,
    (PieceType.ROOK, Color.WHITE): 506,
    (PieceType.BISHOP, Color.WHITE): 457,
    (PieceType.KNIGHT, Color.WHITE): 413,
    (PieceType.PAWN, Color.WHITE): 380,
    (PieceType.KING, Color.BLACK): 346,
    (PieceType.QUEEN, Color.BLACK): 317,
    (PieceType.ROOK, Color.BLACK): 288,
    (PieceType.BISHOP, Color.BLACK): 262,
    (PieceType.KNIGHT, Color.BLACK): 237,
    (PieceType.PAWN, Color.BLACK): 217,
}


def test_twelve_frequencies_match_brief_within_1khz(cfg):
    plan = frequency_plan(cfg)
    assert len(plan.lines) == 12
    for (piece, color), expected_khz in BRIEF_TABLE_KHZ.items():
        f = plan.line(piece, color).f0_hz
        assert f / 1e3 == pytest.approx(expected_khz, abs=1.0), (piece, color)


def test_plan_is_sorted_and_inside_the_analog_band(cfg):
    plan = frequency_plan(cfg)
    freqs = [line.f0_hz for line in plan.lines]
    assert freqs == sorted(freqs)
    lo, hi = cfg.measurement.band_hz
    assert lo <= freqs[0] and freqs[-1] <= hi


def test_resonance_widths_match_brief_range(cfg):
    # Brief 3.3: widths f/Q from 4.3 to 12 kHz at Q = 50.
    plan = frequency_plan(cfg)
    widths_khz = [line.width_nominal_hz / 1e3 for line in plan.lines]
    assert min(widths_khz) == pytest.approx(4.33, abs=0.1)
    assert max(widths_khz) == pytest.approx(12.25, abs=0.15)


def test_ringdown_tau_matches_brief(cfg):
    # Brief 3.4: tau = Q / (pi f) ~ 40 us at 400 kHz, Q = 50.
    assert ringdown_tau_us(400e3, cfg.resonator.q_nominal) == pytest.approx(39.8, abs=0.5)


def test_separation_at_nominal_q(cfg):
    report = check_separation(cfg, q=cfg.resonator.q_nominal)
    assert report.ok
    # True worst adjacent pair is the 3.3 / 3.9 nF E12 step (413 / 380 kHz),
    # at 4.17 widths; slightly tighter than the brief's 4.6 figure, which
    # was quoted for the bottom pair.
    assert report.min_gap_widths == pytest.approx(4.17, abs=0.1)
    worst = min(report.gaps, key=lambda g: g.gap_widths)
    assert (worst.lower.piece, worst.lower.color) == (PieceType.PAWN, Color.WHITE)
    assert (worst.upper.piece, worst.upper.color) == (PieceType.KNIGHT, Color.WHITE)


def test_separation_at_degraded_q_still_passes_gate(cfg):
    report = check_separation(cfg)  # defaults to q_min_with_magnet
    assert report.q_used == cfg.resonator.q_min_with_magnet
    assert report.min_gap_widths == pytest.approx(2.50, abs=0.06)
    assert report.min_gap_widths >= cfg.resonator.min_separation_widths
    assert report.ok


def test_worst_case_tolerance_gap(cfg):
    # +-5 % L and +-1 % C drift both neighbors by 3 % of f toward each
    # other; the bottom pair (12 / 10 nF) keeps about 7.1 kHz.
    report = check_separation(cfg)
    assert report.f_tol_pct == pytest.approx(3.0)
    assert report.min_worst_case_gap_hz == pytest.approx(7.06e3, rel=0.05)
    assert report.min_worst_case_gap_hz >= cfg.resonator.min_tolerance_gap_khz * 1e3


def test_guard_fires_when_inductance_tolerance_degrades(raw_config_dict):
    # Hand winding at +-8 % would nearly close the bottom-pair gap.
    raw_config_dict["resonator"]["L_tol_pct"] = 8.0
    mutated = BoardConfig.model_validate(raw_config_dict)
    report = check_separation(mutated)
    assert report.min_worst_case_gap_hz < mutated.resonator.min_tolerance_gap_khz * 1e3
    assert not report.ok
