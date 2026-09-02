"""Geometry of the 8x8 board (ADR 0010): top module, the two bases, the
clock. Pure arithmetic on the config, no CAD: the CadQuery models in
mechanical/ and the viewer consume these numbers, the tests pin them.

Frame: x to the right, y away from the player, z up. The play area
occupies [0, play] x [0, play]; the wood border and the bases extend
around it. The top module (plywood plus the four quadrants) is the
invariant; a base is either the thin one or the gantry one.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .config import BoardConfig

CORNER_SIGN = {"NW": (-1, -1), "SE": (1, 1), "NE": (1, -1), "SW": (-1, 1)}


@dataclass(frozen=True)
class Layer:
    name: str
    thickness_mm: float


@dataclass(frozen=True)
class BaseGeometry:
    name: str
    x0_mm: float
    y0_mm: float
    width_mm: float
    depth_mm: float
    height_mm: float            # base alone, without the top module
    cavity_mm: float            # free height above the electronics layer
    top_z_mm: float             # where the top module sits
    layers: tuple[Layer, ...]   # full stack, base plus top module

    @property
    def total_height_mm(self) -> float:
        return sum(layer.thickness_mm for layer in self.layers)


@dataclass(frozen=True)
class PlateauGeometry:
    pitch_mm: float
    grid: int
    play_mm: float
    module_mm: float            # top module side, wood border included
    quadrant_mm: float
    quadrants_per_side: int
    top_module_thickness_mm: float
    capture_band_mm: float
    y_margin_mm: float
    thin: BaseGeometry
    gantry: BaseGeometry


def pitch_mm(cfg: BoardConfig) -> float:
    return cfg.pitch.plateau_mm


def play_mm(cfg: BoardConfig) -> float:
    return cfg.plateau.grid * pitch_mm(cfg)


def top_module_thickness_mm(cfg: BoardConfig) -> float:
    """Quadrant PCB, air clearance for the LEDs and the front end, plywood."""
    return cfg.gap.pcb_mm + cfg.gap.air_mm + cfg.gap.surface_mm


def _top_layers(cfg: BoardConfig) -> tuple[Layer, ...]:
    return (
        Layer("PCB quadrant", cfg.gap.pcb_mm),
        Layer("entrefer d'air (LED, frontal)", cfg.gap.air_mm),
        Layer("contreplaque", cfg.gap.surface_mm),
    )


def quadrant_origins(cfg: BoardConfig) -> tuple[tuple[float, float], ...]:
    """Lower-left corner of every quadrant, row-major from the player."""
    q = cfg.plateau.quadrant.squares
    side = q * pitch_mm(cfg)
    n = cfg.plateau.grid // q
    return tuple((i * side, j * side) for j in range(n) for i in range(n))


def square_center(cfg: BoardConfig, file_idx: int, rank_idx: int) -> tuple[float, float]:
    p = pitch_mm(cfg)
    return (file_idx + 0.5) * p, (rank_idx + 0.5) * p


def led_points(cfg: BoardConfig) -> tuple[tuple[float, float], ...]:
    """Centers of the camp LEDs and of the light holes drilled in the
    plywood: the same corners on every square, in yaml order, square by
    square (file then rank). Single source for the quadrant generator, the
    wood template and the 3D models."""
    p = pitch_mm(cfg)
    d = p / 2.0 - cfg.mockup.coil_board.leds.corner_inset_mm
    pts = []
    for rank in range(cfg.plateau.grid):
        for file_idx in range(cfg.plateau.grid):
            cx, cy = square_center(cfg, file_idx, rank)
            for corner in cfg.plateau.leds.corners:
                sx, sy = CORNER_SIGN[corner]
                pts.append((cx + sx * d, cy + sy * d))
    return tuple(pts)


def led_clears_spiral(cfg: BoardConfig) -> bool:
    """The LED body (5 x 5 mm) must stay outside the sense spiral circle."""
    p = pitch_mm(cfg)
    d = p / 2.0 - cfg.mockup.coil_board.leds.corner_inset_mm
    led_half_diag = 2.5 * math.sqrt(2.0)
    return d * math.sqrt(2.0) - led_half_diag > cfg.sense_coil.outer_ratio * p / 2.0


def front_end_strip_fits(cfg: BoardConfig) -> bool:
    return cfg.plateau.quadrant.front_end_max_height_mm < cfg.gap.air_mm


def thin_base(cfg: BoardConfig) -> BaseGeometry:
    b = cfg.plateau.base
    border = cfg.plateau.wood.border_mm
    side = play_mm(cfg) + 2.0 * border
    height = b.shell_mm + b.electronics_cavity_mm
    layers = (Layer("coque", b.shell_mm),
              Layer("cavite electronique", b.electronics_cavity_mm)) + _top_layers(cfg)
    return BaseGeometry("fine", -border, -border, side, side, height,
                        b.electronics_cavity_mm, height, layers)


def gantry_base(cfg: BoardConfig) -> BaseGeometry:
    b = cfg.plateau.base
    border = cfg.plateau.wood.border_mm
    band = cfg.gantry.capture_band_ratio * pitch_mm(cfg)
    play = play_mm(cfg)
    width = play + 2.0 * band + 2.0 * border
    depth = play + cfg.gantry.y_margin_mm + 2.0 * border
    height = b.shell_mm + b.electronics_cavity_mm + b.gantry_cavity_mm
    layers = (Layer("coque", b.shell_mm),
              Layer("cavite electronique", b.electronics_cavity_mm),
              Layer("CoreXY", b.gantry_cavity_mm)) + _top_layers(cfg)
    return BaseGeometry("chariot", -band - border, -border, width, depth, height,
                        b.gantry_cavity_mm, height, layers)


def geometry(cfg: BoardConfig) -> PlateauGeometry:
    p = pitch_mm(cfg)
    q = cfg.plateau.quadrant.squares
    return PlateauGeometry(
        pitch_mm=p,
        grid=cfg.plateau.grid,
        play_mm=play_mm(cfg),
        module_mm=play_mm(cfg) + 2.0 * cfg.plateau.wood.border_mm,
        quadrant_mm=q * p,
        quadrants_per_side=cfg.plateau.grid // q,
        top_module_thickness_mm=top_module_thickness_mm(cfg),
        capture_band_mm=cfg.gantry.capture_band_ratio * p,
        y_margin_mm=cfg.gantry.y_margin_mm,
        thin=thin_base(cfg),
        gantry=gantry_base(cfg),
    )


def check(cfg: BoardConfig) -> list[str]:
    """Design guards; an empty list means the yaml is consistent."""
    problems = []
    if cfg.gap.nominal_total_mm > cfg.gap.max_total_mm:
        problems.append("stack exceeds the maximum gap")
    if not front_end_strip_fits(cfg):
        problems.append("front end parts taller than the air clearance")
    if not led_clears_spiral(cfg):
        problems.append("LED body overlaps the sense spiral")
    if cfg.plateau.quadrant.front_end_strip_mm > cfg.plateau.wood.border_mm + 5.0:
        problems.append("front end strip sticks out far beyond the wood border")
    ck = cfg.clock
    slope_len = math.hypot(ck.slope_end_mm, ck.height_rear_mm - ck.height_front_mm)
    win_w, win_h = ck.display.window_mm
    if ck.display.up_slope_mm - win_h / 2.0 < ck.wall_mm + 1.0:
        problems.append("display window cuts the front wall")
    if ck.display.up_slope_mm + win_h / 2.0 > slope_len - 1.0:
        problems.append("display window runs past the slope")
    if ck.rocker.length_mm + 4.0 > ck.body_mm[0] - 2.0 * ck.wall_mm - 2.0:
        problems.append("rocker recess cuts the side walls")
    if ck.rocker.width_mm + 4.0 > ck.body_mm[1] - ck.slope_end_mm - ck.wall_mm - 2.0:
        problems.append("rocker recess does not fit the flat rear top")
    tilt_drop = ck.rocker.length_mm / 2.0 * math.sin(math.radians(ck.rocker.tilt_deg))
    if tilt_drop > ck.rocker.recess_mm:
        problems.append("rocker end travels deeper than the recess")
    return problems
