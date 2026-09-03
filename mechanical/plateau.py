"""The 8x8 board (ADR 0010): top module, thin base, gantry base, clock
beside it. Every dimension comes from config/board.yaml through
chessboard_calc.plateau; this module only turns numbers into solids.

Frame: x to the right, y away from the player, z up, z = 0 under the
base. The play area is [0, play] x [0, play]. Electronics are placed on
the same footprint in both bases, so swapping bases moves the boards,
not the design.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import cadquery as cq
from common import Part, puck_dims
from parts import piece_puck

from chessboard_calc.config import BoardConfig, PieceType
from chessboard_calc.plateau import (
    BaseGeometry,
    gantry_base,
    geometry,
    led_points,
    quadrant_origins,
    thin_base,
)

WALL = 3.0
POST = 8.0
PIN_H = 4.0
LED_BODY = 5.0
LED_H = 1.6
SPIRAL_COPPER = 0.2
STRIP_CHIP_PITCH = 30.0

COL = dict(
    shell="#3b414a",
    wing="#4b535d",
    pcb="#1d6b3c",
    strip="#2f3b2a",
    cu="#d38a3c",
    led="#f0c95a",
    chip="#22262b",
    esp="#8aa1b5",
    conn="#e6e1d6",
    cell="#7c8994",
    light="#d9c19a",
    dark="#7a4b28",
    piece="#6f9cc4",
    alu="#9da5ad",
    rail="#c3c9cf",
    motor="#2a2d31",
    magnet="#b9c1c9",
)

EXPLODE = dict(base=0.0, elec=1.0, chariot=2.0, ailes=3.0, quad=3.4, bois=4.4, pieces=5.4)


def _box(w: float, d: float, h: float, x: float, y: float, z: float):
    return (
        cq.Workplane("XY").box(w, d, h, centered=(False, False, False)).val().translate((x, y, z))
    )


def tray(base: BaseGeometry, cfg: BoardConfig) -> list[Part]:
    """Bottom plate and four walls in one solid, plus the four locating
    posts the top module drops onto."""
    shell_mm = cfg.plateau.base.shell_mm
    outer = cq.Workplane("XY").box(
        base.width_mm, base.depth_mm, base.height_mm, centered=(False, False, False)
    )
    inner = (
        cq.Workplane("XY")
        .box(
            base.width_mm - 2 * WALL,
            base.depth_mm - 2 * WALL,
            base.height_mm,
            centered=(False, False, False),
        )
        .translate((WALL, WALL, shell_mm))
    )
    body = outer.cut(inner).edges("|Z").fillet(6.0).val().translate((base.x0_mm, base.y0_mm, 0))
    parts = [
        Part(
            f"base {base.name} : coque {shell_mm:g} mm, parois {WALL:g} mm",
            body,
            COL["shell"],
            "base",
        )
    ]
    pins = cfg.plateau.base.locating_pins
    g = geometry(cfg)
    inset = cfg.plateau.wood.border_mm + POST / 2.0
    for x, y in [
        (-inset + POST / 2.0, -inset + POST / 2.0),
        (g.play_mm + inset - POST / 2.0, -inset + POST / 2.0),
        (-inset + POST / 2.0, g.play_mm + inset - POST / 2.0),
        (g.play_mm + inset - POST / 2.0, g.play_mm + inset - POST / 2.0),
    ]:
        post = _box(POST, POST, base.height_mm - shell_mm, x - POST / 2.0, y - POST / 2.0, shell_mm)
        pin = (
            cq.Workplane("XY")
            .circle(pins.d_mm / 2.0)
            .extrude(PIN_H)
            .val()
            .translate((x, y, base.height_mm))
        )
        parts.append(Part("poteau et pion de centrage", post.fuse(pin), COL["shell"], "base"))
    return parts


def electronics(cfg: BoardConfig, z: float) -> list[Part]:
    """Brain board, power board and the flat cells, placeholders sized from
    the yaml, on the footprint shared by both bases (rear-left for the
    boards, right for the cells)."""
    g = geometry(cfg)
    brain = cfg.plateau.brain
    parts = [
        Part(
            f"cerveau : {brain.mcu_board}",
            _box(120, 80, cfg.gap.pcb_mm, 20, g.play_mm - 100, z),
            COL["strip"],
            "elec",
        )
    ]
    zc = z + cfg.gap.pcb_mm
    parts.append(
        Part("STM32G474 LQFP64", _box(10, 10, 1.2, 60, g.play_mm - 65, zc), COL["chip"], "elec")
    )
    parts.append(
        Part(
            f"module {brain.comms.module}",
            _box(18, 25, 3.0, 28, g.play_mm - 95, zc),
            COL["esp"],
            "elec",
        )
    )
    parts.append(
        Part(
            "embase Pi Zero 2 W (option)",
            _box(65, 30, 1.6, 70, g.play_mm - 98, zc + 6),
            COL["strip"],
            "elec",
        )
    )
    for k in range(g.quadrants_per_side**2):
        parts.append(
            Part(
                f"nappe {cfg.plateau.quadrant.link.connector} quadrant {k + 1}",
                _box(22, 9, 8.0, 25 + k * 28, g.play_mm - 34, zc),
                COL["conn"],
                "elec",
            )
        )
    parts.append(
        Part(
            f"carte puissance : {brain.power_board}",
            _box(100, 60, cfg.gap.pcb_mm, 160, g.play_mm - 90, z),
            COL["strip"],
            "elec",
        )
    )
    parts.append(
        Part("self du buck 5 V", _box(12, 12, 6.0, 175, g.play_mm - 70, zc), COL["chip"], "elec")
    )
    parts.append(
        Part(
            f"USB-C : charge, {brain.peripheral_port}",
            _box(9, 9, 3.2, 240, g.play_mm - 60, zc),
            COL["conn"],
            "elec",
        )
    )
    cw, cd, ch = cfg.plateau.base.cell_mm
    for k in range(3):
        parts.append(
            Part(
                f"cellule plate 1S ({k + 1}/3), {cfg.power.battery.cell}",
                _box(cw, cd, ch, g.play_mm - cw - 15, 20 + k * (cd + 55), z),
                COL["cell"],
                "elec",
            )
        )
    return parts


def quadrants(cfg: BoardConfig, z: float) -> list[Part]:
    g = geometry(cfg)
    q = cfg.plateau.quadrant
    pcb = cfg.gap.pcb_mm
    r_out = cfg.sense_coil.outer_ratio * g.pitch_mm / 2.0
    r_in = cfg.sense_coil.inner_ratio * g.pitch_mm / 2.0
    parts = []
    for k, (ox, oy) in enumerate(quadrant_origins(cfg)):
        parts.append(
            Part(
                f"quadrant Q{k + 1} : {g.quadrant_mm:g} x {g.quadrant_mm:g}, "
                f"{q.layers} couches, {q.mux}",
                _box(g.quadrant_mm, g.quadrant_mm, pcb, ox, oy, z),
                COL["pcb"],
                "quad",
            )
        )
        for i in range(q.squares):
            for j in range(q.squares):
                cx, cy = ox + (i + 0.5) * g.pitch_mm, oy + (j + 0.5) * g.pitch_mm
                ring = (
                    cq.Workplane("XY")
                    .circle(r_out)
                    .circle(r_in)
                    .extrude(SPIRAL_COPPER)
                    .val()
                    .translate((cx, cy, z + pcb))
                )
                parts.append(
                    Part("spirale de detection, 4 couches en serie", ring, COL["cu"], "quad")
                )
        outer_left = ox == 0.0
        sx = ox - q.front_end_strip_mm if outer_left else ox + g.quadrant_mm
        parts.append(
            Part(
                f"bande frontal : {q.mux}, AD8421, filtres, decodeur, FET",
                _box(q.front_end_strip_mm, g.quadrant_mm, pcb, sx, oy, z),
                COL["strip"],
                "quad",
            )
        )
        n_chips = int(g.quadrant_mm // STRIP_CHIP_PITCH)
        for c in range(n_chips):
            parts.append(
                Part(
                    "",
                    _box(
                        5,
                        6,
                        q.front_end_max_height_mm - 0.3,
                        sx + 4.5,
                        oy + 15 + c * STRIP_CHIP_PITCH,
                        z + pcb,
                    ),
                    COL["chip"],
                    "quad",
                )
            )
        parts.append(
            Part(
                f"{q.link.connector} vers le cerveau",
                _box(9, 22, 5.0, sx + 2.5, oy + g.quadrant_mm - 30, z - 5.0),
                COL["conn"],
                "quad",
            )
        )
    for x, y in led_points(cfg):
        parts.append(
            Part(
                "WS2812B",
                _box(LED_BODY, LED_BODY, LED_H, x - LED_BODY / 2.0, y - LED_BODY / 2.0, z + pcb),
                COL["led"],
                "quad",
            )
        )
    return parts


def wood(cfg: BoardConfig, z: float) -> list[Part]:
    """Plywood plate with the light holes, dark squares as a thin veneer on
    top so the checkerboard reads in renders."""
    g = geometry(cfg)
    border = cfg.plateau.wood.border_mm
    t = cfg.gap.surface_mm
    plate = (
        cq.Workplane("XY")
        .box(g.module_mm, g.module_mm, t, centered=(False, False, False))
        .edges("|Z")
        .fillet(8.0)
        .faces(">Z")
        .workplane(origin=(0, 0, 0))
        .pushPoints([(x + border, y + border) for x, y in led_points(cfg)])
        .hole(cfg.mockup.coil_board.leds.light_hole_d_mm)
    )
    parts = [
        Part(
            f"contreplaque {t:g} mm, {len(led_points(cfg))} points lumineux",
            plate.val().translate((-border, -border, z)),
            COL["light"],
            "bois",
        )
    ]
    for i in range(g.grid):
        for j in range(g.grid):
            if (i + j) % 2 == 0:
                parts.append(
                    Part(
                        f"case {'abcdefgh'[i]}{j + 1}",
                        _box(g.pitch_mm, g.pitch_mm, 0.3, i * g.pitch_mm, j * g.pitch_mm, z + t),
                        COL["dark"],
                        "bois",
                    )
                )
    return parts


def wings(cfg: BoardConfig, base: BaseGeometry, z: float) -> list[Part]:
    """Gantry base only: capture wings flush with the wood on both sides,
    and the rear strip over the y margin."""
    g = geometry(cfg)
    border = cfg.plateau.wood.border_mm
    t = g.top_module_thickness_mm
    w = g.capture_band_mm + border
    return [
        Part(
            "aile de capture gauche",
            _box(w, base.depth_mm, t, base.x0_mm, base.y0_mm, z),
            COL["wing"],
            "ailes",
        ),
        Part(
            "aile de capture droite",
            _box(w, base.depth_mm, t, g.play_mm + border, base.y0_mm, z),
            COL["wing"],
            "ailes",
        ),
        Part(
            "lisiere arriere (marge y du chariot)",
            _box(g.module_mm, g.y_margin_mm, t, -border, g.play_mm + border, z),
            COL["wing"],
            "ailes",
        ),
    ]


def gantry_frame(cfg: BoardConfig, z: float) -> list[Part]:
    """CoreXY placeholders: two Y rails on 2020 profiles, the X beam with
    the carriage and its N42, two NEMA17 at the rear, the motion board."""
    g = geometry(cfg)
    band = g.capture_band_mm
    travel_y = g.play_mm + g.y_margin_mm
    parts = []
    for x in (-band - 2.0, g.play_mm + band - 18.0):
        parts.append(Part("profile 2020", _box(20, travel_y, 20, x, 0, z), COL["alu"], "chariot"))
        parts.append(
            Part(
                "rail MGN9 axe Y", _box(9, travel_y, 6, x + 5.5, 0, z + 20), COL["rail"], "chariot"
            )
        )
    by = 3.0 * g.pitch_mm
    parts.append(
        Part(
            "poutre X", _box(g.play_mm + 2 * band, 20, 8, -band, by, z + 24), COL["rail"], "chariot"
        )
    )
    parts.append(
        Part(
            "chariot", _box(30, 30, 6, 3 * g.pitch_mm + 10, by - 5, z + 24), COL["motor"], "chariot"
        )
    )
    m = cfg.carriage.magnet
    magnet = (
        cq.Workplane("XY")
        .circle(m.d_mm / 2.0)
        .extrude(m.h_mm)
        .val()
        .translate((3.5 * g.pitch_mm, by + 10, z + 27))
    )
    parts.append(
        Part(f"aimant {m.material} {m.d_mm:g} x {m.h_mm:g}", magnet, COL["magnet"], "chariot")
    )
    motor = cfg.gantry.per_pitch[int(g.pitch_mm)].motor
    for x in (-band, g.play_mm + band - 42.0):
        parts.append(Part(motor, _box(42, 42, 30, x, travel_y - 44, z), COL["motor"], "chariot"))
    parts.append(
        Part(
            f"carte moteurs : {cfg.plateau.brain.motion_board}",
            _box(90, 60, cfg.gap.pcb_mm, g.play_mm / 2.0 - 45, travel_y - 64, z),
            COL["strip"],
            "chariot",
        )
    )
    return parts


def pieces(cfg: BoardConfig, z: float, on_wing: bool = False) -> list[Part]:
    g = geometry(cfg)
    layout = [
        ((0, 0), PieceType.ROOK),
        ((1, 0), PieceType.KNIGHT),
        ((4, 0), PieceType.KING),
        ((3, 1), PieceType.PAWN),
        ((4, 7), PieceType.KING),
        ((3, 6), PieceType.PAWN),
        ((7, 7), PieceType.ROOK),
        ((2, 7), PieceType.BISHOP),
    ]
    parts = []
    for (i, j), piece in layout:
        dims = puck_dims(cfg, piece, g.pitch_mm)
        puck = piece_puck(dims).val().translate(((i + 0.5) * g.pitch_mm, (j + 0.5) * g.pitch_mm, z))
        parts.append(Part(f"{piece.value} : base {dims.base_d:g} mm", puck, COL["piece"], "pieces"))
    if on_wing:
        for k, piece in enumerate((PieceType.PAWN, PieceType.PAWN, PieceType.BISHOP)):
            dims = puck_dims(cfg, piece, g.pitch_mm)
            puck = (
                piece_puck(dims)
                .val()
                .translate((-g.capture_band_mm / 2.0, (k + 0.5) * g.pitch_mm, z))
            )
            parts.append(Part(f"{piece.value} capture", puck, COL["piece"], "pieces"))
    return parts


def assembly(cfg: BoardConfig, gantry: bool = False, with_pieces: bool = True) -> list[Part]:
    base = gantry_base(cfg) if gantry else thin_base(cfg)
    zt = base.top_z_mm
    parts = tray(base, cfg)
    parts += electronics(cfg, cfg.plateau.base.shell_mm)
    if gantry:
        parts += gantry_frame(
            cfg, cfg.plateau.base.shell_mm + cfg.plateau.base.electronics_cavity_mm
        )
        parts += wings(cfg, base, zt)
    parts += quadrants(cfg, zt)
    parts += wood(cfg, zt + cfg.gap.pcb_mm + cfg.gap.air_mm)
    if with_pieces:
        parts += pieces(cfg, zt + geometry(cfg).top_module_thickness_mm, on_wing=gantry)
    return parts


def exploded(parts: list[Part], amount_mm: float) -> list[Part]:
    """Lift every part by its group's explode order (or its own factor)."""
    out = []
    for p in parts:
        factor = p.explode if p.explode else EXPLODE.get(p.group, 0.0)
        out.append(
            Part(p.name, p.shape.translate((0, 0, factor * amount_mm)), p.color, p.group, p.explode)
        )
    return out
