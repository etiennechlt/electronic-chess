"""Shared parameters for the CadQuery models, all from config/board.yaml."""

from __future__ import annotations

from dataclasses import dataclass

from chessboard_calc.config import BoardConfig, PieceType, load_config, resolve_geometry
from chessboard_calc.inductance import piece_coil_design

# Printing allowances.
FIT_TIGHT = 0.15   # press fit (magnet, coil former)
FIT_LOOSE = 0.30   # sliding fit
WALL_MIN = 1.2
M3_CLEAR = 3.4
M3_NUT_FLAT = 5.6  # across flats, plus fit
M3_NUT_H = 2.6


@dataclass(frozen=True)
class PuckDims:
    piece: PieceType
    base_d: float
    height: float
    coil_d: float
    coil_h: float
    magnet_d: float
    magnet_h: float


def puck_dims(cfg: BoardConfig, piece: PieceType, pitch_mm: float) -> PuckDims:
    geo = resolve_geometry(cfg, pitch_mm).classes[piece]
    return PuckDims(
        piece=piece,
        base_d=geo.base_mm,
        height=14.0,
        coil_d=geo.coil_d_out_mm,
        coil_h=cfg.resonator.coil.height_mm,
        magnet_d=geo.magnet_d_mm,
        magnet_h=cfg.piece_magnet.thickness_mm,
    )


def load() -> tuple[BoardConfig, float]:
    cfg = load_config()
    return cfg, cfg.pitch.mockup_mm


def coil_former_dims(cfg: BoardConfig, piece: PieceType, pitch_mm: float):
    design = piece_coil_design(cfg, piece, pitch_mm)
    return design


@dataclass(frozen=True)
class Part:
    """One solid of an assembly, for the scene renders and the 3D viewer.

    `group` is the layer a viewer can hide as a whole; `explode` is the
    lift factor along z in an exploded view (0 stays put).
    """
    name: str
    shape: object          # cadquery Shape (a Solid or Compound)
    color: str             # hex, the same for the PNG scenes and the viewer
    group: str
    explode: float = 0.0
