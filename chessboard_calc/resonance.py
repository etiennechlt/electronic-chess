"""Resonant frequency plan, resonance widths and separation checks."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .config import BoardConfig, Color, PieceType


def f0_hz(L_uH: float, C_nF: float) -> float:
    return 1.0 / (2.0 * math.pi * math.sqrt(L_uH * 1e-6 * C_nF * 1e-9))


def resonance_width_hz(f_hz: float, q: float) -> float:
    return f_hz / q


def ringdown_tau_us(f_hz: float, q: float) -> float:
    """Amplitude decay time constant: A(t) = A0 * exp(-t / tau)."""
    return q / (math.pi * f_hz) * 1e6


@dataclass(frozen=True)
class ResonatorLine:
    piece: PieceType
    color: Color
    cap_nF: float
    f0_hz: float
    width_nominal_hz: float
    width_min_q_hz: float
    tau_nominal_us: float


@dataclass(frozen=True)
class FrequencyPlan:
    lines: tuple[ResonatorLine, ...]  # sorted by ascending f0

    def line(self, piece: PieceType, color: Color) -> ResonatorLine:
        for entry in self.lines:
            if entry.piece is piece and entry.color is color:
                return entry
        raise KeyError((piece, color))


def frequency_plan(cfg: BoardConfig) -> FrequencyPlan:
    lines = []
    for piece, spec in cfg.pieces.classes.items():
        for color, cap in spec.cap_nF.items():
            f = f0_hz(cfg.resonator.L_target_uH, cap)
            lines.append(
                ResonatorLine(
                    piece=piece,
                    color=color,
                    cap_nF=cap,
                    f0_hz=f,
                    width_nominal_hz=resonance_width_hz(f, cfg.resonator.q_nominal),
                    width_min_q_hz=resonance_width_hz(f, cfg.resonator.q_min_with_magnet),
                    tau_nominal_us=ringdown_tau_us(f, cfg.resonator.q_nominal),
                )
            )
    lines.sort(key=lambda entry: entry.f0_hz)
    return FrequencyPlan(lines=tuple(lines))


@dataclass(frozen=True)
class AdjacentGap:
    lower: ResonatorLine
    upper: ResonatorLine
    gap_hz: float
    gap_widths: float  # gap over the mean resonance width at the evaluated Q
    worst_case_gap_hz: float  # once both neighbors drift by full tolerance


@dataclass(frozen=True)
class SeparationReport:
    q_used: float
    f_tol_pct: float
    gaps: tuple[AdjacentGap, ...]
    min_gap_widths: float
    min_worst_case_gap_hz: float
    ok: bool


def check_separation(cfg: BoardConfig, q: float | None = None) -> SeparationReport:
    """Adjacent-class separation, in resonance widths and under tolerance.

    Two criteria, both from config:
    - nominal peaks at least min_separation_widths apart at the given Q
      (defaults to the degraded q_min_with_magnet, the conservative case);
    - once both neighbors drift toward each other by the full first-order
      frequency tolerance (L_tol + C_tol) / 2, the remaining gap stays at
      least min_tolerance_gap_khz, so per-piece nearest-neighbor
      calibration keeps classes apart at the measurement resolution.
    """
    res = cfg.resonator
    q_used = res.q_min_with_magnet if q is None else q
    f_tol_pct = (res.L_tol_pct + res.C_tol_pct) / 2.0
    plan = frequency_plan(cfg)
    gaps = []
    for lower, upper in zip(plan.lines, plan.lines[1:], strict=False):
        gap = upper.f0_hz - lower.f0_hz
        mean_width = (
            resonance_width_hz(lower.f0_hz, q_used) + resonance_width_hz(upper.f0_hz, q_used)
        ) / 2.0
        worst = gap - (lower.f0_hz + upper.f0_hz) * f_tol_pct / 100.0
        gaps.append(
            AdjacentGap(
                lower=lower,
                upper=upper,
                gap_hz=gap,
                gap_widths=gap / mean_width,
                worst_case_gap_hz=worst,
            )
        )
    min_widths = min(g.gap_widths for g in gaps)
    min_worst = min(g.worst_case_gap_hz for g in gaps)
    ok = min_widths >= res.min_separation_widths and min_worst >= res.min_tolerance_gap_khz * 1e3
    return SeparationReport(
        q_used=q_used,
        f_tol_pct=f_tol_pct,
        gaps=tuple(gaps),
        min_gap_widths=min_widths,
        min_worst_case_gap_hz=min_worst,
        ok=ok,
    )
