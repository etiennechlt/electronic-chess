"""Corridor constraint: pieces travel along board lines between squares.

For a moving piece to pass between two adjacent occupied squares the
brief requires r_mobile + r_static <= p / 2 with margin above the
mechanical tolerance budget. Violating it deadlocks the game as early
as e2-e4 (corridor between d2 and f2), so this module backs the CI
gate in tests/test_corridor.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations_with_replacement

from .config import BoardConfig, PieceType, base_diameter_mm


def corridor_margin_mm(
    cfg: BoardConfig, a: PieceType, b: PieceType, pitch_mm: float
) -> float:
    """p/2 minus the sum of the two base radii; must exceed the budget."""
    r_a = base_diameter_mm(cfg, a, pitch_mm) / 2.0
    r_b = base_diameter_mm(cfg, b, pitch_mm) / 2.0
    return pitch_mm / 2.0 - (r_a + r_b)


@dataclass(frozen=True)
class PairMargin:
    a: PieceType
    b: PieceType
    margin_mm: float
    ok: bool


@dataclass(frozen=True)
class CorridorReport:
    pitch_mm: float
    budget_mm: float
    pairs: tuple[PairMargin, ...]
    worst: PairMargin
    ok: bool

    def violations(self) -> tuple[PairMargin, ...]:
        return tuple(p for p in self.pairs if not p.ok)


def check_corridor(cfg: BoardConfig, pitch_mm: float) -> CorridorReport:
    budget = cfg.corridor.tolerance_budget_mm
    pairs = []
    for a, b in combinations_with_replacement(PieceType, 2):
        margin = corridor_margin_mm(cfg, a, b, pitch_mm)
        pairs.append(PairMargin(a=a, b=b, margin_mm=margin, ok=margin >= budget))
    worst = min(pairs, key=lambda p: p.margin_mm)
    return CorridorReport(
        pitch_mm=pitch_mm,
        budget_mm=budget,
        pairs=tuple(pairs),
        worst=worst,
        ok=all(p.ok for p in pairs),
    )
