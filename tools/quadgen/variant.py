"""Build variants of the quadrant: the full 4 x 4 board of the plateau, or
the reduced development quadrant (plateau.quadrant.reduced) that keeps
the circuit, the bus and the firmware and shrinks the coil grid."""

from __future__ import annotations

from chessboard_calc.config import BoardConfig


def reduced_config(cfg: BoardConfig) -> BoardConfig:
    """The config with the reduced quadrant's grid and strip overhang."""
    raw = cfg.model_dump()
    quad = raw["plateau"]["quadrant"]
    quad["squares"] = quad["reduced"]["squares"]
    quad["strip_overhang_mm"] = quad["reduced"]["strip_overhang_mm"]
    return BoardConfig.model_validate(raw)


def project_name(cfg: BoardConfig, reduced: bool) -> str:
    s = cfg.plateau.quadrant.squares
    return f"quadrant-{s}x{s}" if reduced else "quadrant"
