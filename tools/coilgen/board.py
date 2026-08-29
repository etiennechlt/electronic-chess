"""Builder of the complete 2 x 2 mockup coil board.

Everything is computed from config/board.yaml: coil envelope and turn
count come from chessboard_calc.pcb_sense_coil, board outline, joint
connector, mounting and magnet-bracket holes from the mockup section.

Coordinates are KiCad style (y down). Squares, viewed like a small
chessboard with the joint connector at the top (north) edge:
S1 top-left, S2 top-right, S3 bottom-left, S4 bottom-right.
The magnet bracket sits under mockup.coil_board.magnet_mount.square,
[0, 0] meaning the bottom-left square (S3).

Net semantics: each coil is one series element, so its spiral, its
stacking vias and both of its connector pads share one net (C1..C4).
The analog board defines its own A/B nets; across the physical joint
only pad positions matter.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from chessboard_calc.config import BoardConfig, resolve_geometry
from chessboard_calc.inductance import pcb_sense_coil

from .geometry import LayerPath, spiral_stack
from .kicad import Board

COPPER_LAYERS = ["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"]

# Pad order chosen so no escape route crosses another (see routing plan
# below): S1 comes from the left, S3 and S4 climb the two center lanes,
# S2 comes from the right. Tuples are (net, terminal label).
PAD_PLAN = [
    ("GND", ""), ("C1", "A"), ("C1", "B"), ("C3", "A"), ("C3", "B"),
    ("C4", "A"), ("C4", "B"), ("C2", "A"), ("C2", "B"), ("GND", ""),
]


@dataclass
class CoilDebug:
    name: str
    center: tuple[float, float]
    paths: list[LayerPath]
    vias: list[tuple[float, float]]
    terminal: tuple[float, float]  # shared xy of the stacked A/B terminals
    routes: list[tuple[str, str, list[tuple[float, float]]]]  # (label, layer, pts)


@dataclass
class BuildResult:
    board: Board
    coils: list[CoilDebug] = field(default_factory=list)
    track_width_mm: float = 0.0
    turns_per_layer: int = 0
    pad_xs: list[float] = field(default_factory=list)
    holes: list[tuple[float, float, float]] = field(default_factory=list)
    outline_mm: tuple[float, float] = (0.0, 0.0)


def _pad_positions(cfg: BoardConfig, width_mm: float) -> list[float]:
    joint = cfg.mockup.coil_board.joint
    span = (joint.pins - 1) * joint.pitch_mm
    x0 = width_mm / 2.0 - span / 2.0
    return [x0 + i * joint.pitch_mm for i in range(joint.pins)]


def build_coil_board(cfg: BoardConfig) -> BuildResult:
    pitch = cfg.pitch.mockup_mm
    mock = cfg.mockup.coil_board
    geo = resolve_geometry(cfg, pitch)
    sense = pcb_sense_coil(cfg, pitch)

    w_mm, h_mm = mock.size_mm
    r_out = geo.sense_d_out_mm / 2.0
    r_in = geo.sense_d_in_mm / 2.0
    width = sense.track_width_mm
    turns = sense.turns_per_layer
    route_w = mock.route_track_mm
    via_drill = cfg.sense_coil.via_drill_mm
    via_pad = 2.0 * via_drill

    board = Board(thickness_mm=cfg.gap.pcb_mm, title="Damier LC, maquette 2x2, carte bobines")
    result = BuildResult(
        board=board, track_width_mm=width, turns_per_layer=turns,
        outline_mm=(w_mm, h_mm),
    )

    gnd = board.net("GND")
    pad_row_y = 2.5
    row_north = 4.0            # escape row for S1 and S2 (both layers)
    row_lane_a, row_lane_b = 4.4, 4.8  # escape rows for the lane coils
    lane = {"S3": 46.5, "S4": 53.5}
    gutter_y = 50.0

    centers = {
        "S1": (pitch / 2.0, pitch / 2.0),
        "S2": (3.0 * pitch / 2.0, pitch / 2.0),
        "S3": (pitch / 2.0, 3.0 * pitch / 2.0),
        "S4": (3.0 * pitch / 2.0, 3.0 * pitch / 2.0),
    }

    pad_xs = _pad_positions(cfg, w_mm)
    result.pad_xs = pad_xs
    pad_x = {
        (net, term): px
        for px, (net, term) in zip(pad_xs, PAD_PLAN, strict=True)
        if net != "GND"
    }

    for name, center in centers.items():
        net_name = f"C{name[1]}"
        net = board.net(net_name)
        paths = spiral_stack(center, COPPER_LAYERS, r_in, r_out, turns)
        dbg = CoilDebug(
            name=name, center=center, paths=paths, vias=[],
            terminal=(center[0], center[1] - r_out), routes=[],
        )
        for path in paths:
            board.polyline(path.points, width, path.layer, net)
        for i in range(len(paths) - 1):
            jx, jy = paths[i].points[-1]
            board.via(float(jx), float(jy), via_pad, via_drill, net)
            dbg.vias.append((float(jx), float(jy)))
        result.coils.append(dbg)

    def route(dbg: CoilDebug, term: str, layer: str, pts: list[tuple[float, float]]) -> None:
        net_name = f"C{dbg.name[1]}"
        board.polyline(pts, route_w, layer, board.net(net_name))
        dbg.routes.append((f"{net_name}_{term}", layer, pts))

    by_name = {c.name: c for c in result.coils}
    for name in ("S1", "S2"):
        dbg = by_name[name]
        tx, ty = dbg.terminal
        for term, layer in (("A", "F.Cu"), ("B", "B.Cu")):
            px = pad_x[(f"C{name[1]}", term)]
            route(dbg, term, layer, [(tx, ty), (tx, row_north), (px, row_north), (px, pad_row_y)])
    for name in ("S3", "S4"):
        dbg = by_name[name]
        tx, ty = dbg.terminal
        for term, layer, row in (("A", "F.Cu", row_lane_a), ("B", "B.Cu", row_lane_b)):
            px = pad_x[(f"C{name[1]}", term)]
            route(
                dbg, term, layer,
                [(tx, ty), (tx, gutter_y), (lane[name], gutter_y),
                 (lane[name], row), (px, row), (px, pad_row_y)],
            )

    # GND strip linking the two shield pins above the pad row.
    board.polyline(
        [(pad_xs[0], pad_row_y), (pad_xs[0], 1.2), (pad_xs[-1], 1.2), (pad_xs[-1], pad_row_y)],
        1.0, "F.Cu", gnd,
    )

    # Joint connector footprint.
    joint = mock.joint
    pads = []
    for i, (px, (net_name, _term)) in enumerate(zip(pad_xs, PAD_PLAN, strict=True), start=1):
        pads.append(
            (str(i), px - w_mm / 2.0, 0.0, joint.pad_d_mm, joint.drill_mm,
             board.net(net_name), net_name)
        )
    board.tht_pad_footprint("J1", "COIL_JOINT_1x10", w_mm / 2.0, pad_row_y, pads)

    # Mounting holes.
    inset = mock.mounting_hole_inset_mm
    corners = [(inset, inset), (w_mm - inset, inset),
               (inset, h_mm - inset), (w_mm - inset, h_mm - inset)]
    for i, (hx, hy) in enumerate(corners, start=1):
        board.npth_hole(hx, hy, mock.mounting_hole_d_mm, ref=f"H{i}")
        result.holes.append((hx, hy, mock.mounting_hole_d_mm))

    # Magnet bracket holes under the configured square (row 0 = south).
    col, row = mock.magnet_mount.square
    mcx = pitch / 2.0 + col * pitch
    mcy = h_mm - (pitch / 2.0 + row * pitch)
    half = mock.magnet_mount.hole_spacing_mm / 2.0
    for i, (hx, hy) in enumerate(
        [(mcx - half, mcy - half), (mcx + half, mcy - half),
         (mcx - half, mcy + half), (mcx + half, mcy + half)],
        start=1,
    ):
        board.npth_hole(hx, hy, mock.magnet_mount.hole_d_mm, ref=f"M{i}")
        result.holes.append((hx, hy, mock.magnet_mount.hole_d_mm))

    # Board outline and silkscreen.
    board.gr_rect(0.0, 0.0, w_mm, h_mm, "Edge.Cuts")
    board.gr_line(0.0, h_mm / 2.0, w_mm, h_mm / 2.0, "F.SilkS", 0.15)
    board.gr_line(w_mm / 2.0, 8.0, w_mm / 2.0, h_mm, "F.SilkS", 0.15)
    for name, (cx, cy) in centers.items():
        board.gr_text(name, cx, cy - 3.0, "F.SilkS", 2.0)
        board.gr_circle(cx, cy, 1.0, "F.SilkS", 0.15)
    board.gr_text("DAMIER LC / MAQUETTE 2x2 / BOBINES p50", w_mm / 2.0, h_mm - 3.0, "F.SilkS", 1.5)
    board.gr_text("AIMANT", mcx, mcy + 4.0, "F.SilkS", 1.5)
    board.gr_text("coilgen rev A", w_mm / 2.0, h_mm - 6.5, "B.SilkS", 1.2, mirror=True)
    return result
