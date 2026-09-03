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
from .project import DesignRules

COPPER_LAYERS = ["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"]

# LED subsystem vias, the only drill on the board besides the coil
# stacking vias, the joint header and the mounting holes.
LED_VIA_PAD, LED_VIA_DRILL = 0.8, 0.4

# Pad order chosen so no escape route crosses another (see routing plan
# below): S1 comes from the left, S3 and S4 climb the two center lanes,
# S2 comes from the right. Tuples are (net, terminal label).
PAD_PLAN = [
    ("GND", ""),
    ("C1", "A"),
    ("C1", "B"),
    ("C3", "A"),
    ("C3", "B"),
    ("C4", "A"),
    ("C4", "B"),
    ("C2", "A"),
    ("C2", "B"),
    ("GND", ""),
    ("LED_DIN", ""),
    ("LED_5V", ""),
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
    leds: list[tuple[str, tuple[float, float]]] = field(default_factory=list)
    led_tracks: list = field(default_factory=list)  # (net, layer, width, pts)
    led_vias: list = field(default_factory=list)  # (x, y)


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
        board=board,
        track_width_mm=width,
        turns_per_layer=turns,
        outline_mm=(w_mm, h_mm),
    )

    gnd = board.net("GND")
    pad_row_y = 2.5
    row_north = 4.0  # escape row for S1 and S2 (both layers)
    row_lane_a, row_lane_b = 4.4, 4.8  # escape rows for the lane coils
    lane = {"S3": 46.5, "S4": 52.6}  # 53.5 would graze the shifted C2A escape
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
        (net, term): px for px, (net, term) in zip(pad_xs, PAD_PLAN, strict=True) if net != "GND"
    }

    for name, center in centers.items():
        net_name = f"C{name[1]}"
        net = board.net(net_name)
        paths = spiral_stack(center, COPPER_LAYERS, r_in, r_out, turns)
        dbg = CoilDebug(
            name=name,
            center=center,
            paths=paths,
            vias=[],
            terminal=(center[0], center[1] - r_out),
            routes=[],
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
                dbg,
                term,
                layer,
                [
                    (tx, ty),
                    (tx, gutter_y),
                    (lane[name], gutter_y),
                    (lane[name], row),
                    (px, row),
                    (px, pad_row_y),
                ],
            )

    # GND strip linking the two shield pins above the pad row.
    gnd_pad_xs = [px for px, (n, _t) in zip(pad_xs, PAD_PLAN, strict=True) if n == "GND"]
    board.polyline(
        [
            (gnd_pad_xs[0], pad_row_y),
            (gnd_pad_xs[0], 1.2),
            (gnd_pad_xs[-1], 1.2),
            (gnd_pad_xs[-1], pad_row_y),
        ],
        1.0,
        "F.Cu",
        gnd,
    )

    # Joint connector footprint.
    joint = mock.joint
    pads = []
    for i, (px, (net_name, _term)) in enumerate(zip(pad_xs, PAD_PLAN, strict=True), start=1):
        pads.append(
            (
                str(i),
                px - w_mm / 2.0,
                0.0,
                joint.pad_d_mm,
                joint.drill_mm,
                board.net(net_name),
                net_name,
            )
        )
    board.tht_pad_footprint("J1", f"COIL_JOINT_1x{joint.pins}", w_mm / 2.0, pad_row_y, pads)

    _place_leds(cfg, board, result, centers, pad_xs, r_out)

    # Mounting holes.
    inset = mock.mounting_hole_inset_mm
    corners = [
        (inset, inset),
        (w_mm - inset, inset),
        (inset, h_mm - inset),
        (w_mm - inset, h_mm - inset),
    ]
    for i, (hx, hy) in enumerate(corners, start=1):
        board.npth_hole(hx, hy, mock.mounting_hole_d_mm, ref=f"H{i}")
        result.holes.append((hx, hy, mock.mounting_hole_d_mm))

    # Magnet bracket holes under the configured square (row 0 = south).
    col, row = mock.magnet_mount.square
    mcx = pitch / 2.0 + col * pitch
    mcy = h_mm - (pitch / 2.0 + row * pitch)
    half = mock.magnet_mount.hole_spacing_mm / 2.0
    for i, (hx, hy) in enumerate(
        [
            (mcx - half, mcy - half),
            (mcx + half, mcy - half),
            (mcx - half, mcy + half),
            (mcx + half, mcy + half),
        ],
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


def _place_leds(
    cfg: BoardConfig,
    board: Board,
    result: BuildResult,
    centers: dict[str, tuple[float, float]],
    pad_xs: list[float],
    r_out: float,
) -> None:
    """Camp indicator LEDs: two WS2812B per square at opposite corners.

    Data is chained on In1.Cu, 5V and GND run as nested loops plus a
    center cross on In2.Cu (both inner layers are virgin outside the
    spirals; the coil escapes only use F.Cu and B.Cu). Every LED pad
    reaches its layer through a via with a short vertical F.Cu stub,
    vertical so the stubs never cross the center escape lanes. All
    geometry is validated against the spiral circles at build time.
    """
    from analoggen.fplib import load_footprint, pad_abs_pos, place_footprint

    leds = cfg.mockup.coil_board.leds
    pitch = cfg.pitch.mockup_mm
    clr = cfg.mockup.coil_board.track_clearance_mm
    o = leds.corner_inset_mm
    w_chain = leds.chain_track_mm
    w_ring = leds.ring_track_mm
    via_pad, via_drill = LED_VIA_PAD, LED_VIA_DRILL
    w_mm, h_mm = cfg.mockup.coil_board.size_mm

    fp = load_footprint("LED_SMD:LED_WS2812B_PLCC4_5.0x5.0mm_P3.2mm")
    fp_c = load_footprint("Capacitor_SMD:C_0603_1608Metric")
    # Verified against the official WS2812B symbol: 1 VDD, 2 DOUT,
    # 3 VSS, 4 DIN.
    pad_roles = {"1": "VDD", "2": "DOUT", "3": "VSS", "4": "DIN"}

    def corner(sq: str, which: str) -> tuple[float, float]:
        cx, cy = centers[sq]
        d = pitch / 2.0 - o
        return {
            "NW": (cx - d, cy - d),
            "SE": (cx + d, cy + d),
            "NE": (cx + d, cy - d),
            "SW": (cx - d, cy + d),
        }[which]

    # Square sequence comes from the yaml (shared with the firmware);
    # the corner pattern is layout knowledge: S2 uses the NE-SW
    # diagonal (its NW corner sits under the joint pad row), and each
    # square's first-visited corner keeps the chain hops short. Both
    # diagonals satisfy "two opposite corners".
    first_corner = {"S1": "SE", "S2": "NE", "S3": "SE", "S4": "NW"}
    other = {"NE": "SW", "SW": "NE", "NW": "SE", "SE": "NW"}
    seen: dict[str, int] = {}
    chain = []
    for k in leds.chain_squares:
        sq = f"S{k}"
        which = first_corner[sq] if sq not in seen else other[first_corner[sq]]
        seen[sq] = seen.get(sq, 0) + 1
        chain.append((sq, which))
    if [c[0] for c in chain] != ["S2", "S2", "S4", "S4", "S3", "S3", "S1", "S1"]:
        raise ValueError("led chain routing is tuned for the S2 S4 S3 S1 order")

    net_5v = "LED_5V"
    net_gnd = "GND"
    seg_log: list[tuple[str, float, list[tuple[float, float]]]] = []
    joint = cfg.mockup.coil_board.joint
    joint_pads = [
        (n, px, 2.5, joint.pad_d_mm / 2.0) for px, (n, _t) in zip(pad_xs, PAD_PLAN, strict=True)
    ]
    # The stacked coil terminals poke out of the r_out envelope at the
    # top of each spiral: keep the LED copper away from them too.
    joint_pads += [(f"C{c.name[1]}", c.terminal[0], c.terminal[1], 1.3) for c in result.coils]

    def track(net: str, pts, width, layer):
        board.polyline(pts, width, layer, board.net(net))
        seg_log.append((net, width, [tuple(p) for p in pts]))
        result.led_tracks.append((net, layer, width, [tuple(p) for p in pts]))

    def via(net: str, x, y):
        board.via(x, y, via_pad, via_drill, board.net(net))
        seg_log.append((net, via_pad, [(x, y)]))
        result.led_vias.append((x, y))

    # LED footprints, decoupling, and per-pad vias with vertical stubs.
    lref = 0
    pad_via: dict[tuple[int, str], tuple[float, float]] = {}
    link_nets = ["LED_DIN"] + [f"LED_L{i}" for i in range(1, len(chain))]
    for idx, (sq, which) in enumerate(chain):
        lref += 1
        x, y = corner(sq, which)
        nets = {
            "VDD": net_5v,
            "VSS": net_gnd,
            "DIN": link_nets[idx],
            "DOUT": link_nets[idx + 1] if idx + 1 < len(chain) else "LED_END",
        }
        pad_nets = {num: (board.net(nets[role]), "") for num, role in pad_roles.items()}
        board.body.append(place_footprint(fp, f"LD{lref}", leds.part, x, y, 0.0, pad_nets))
        for pad in fp.pads:
            px, py = pad_abs_pos(x, y, 0.0, pad)
            role = pad_roles[pad.number]
            vy = py + (1.2 if py > y else -1.2)
            track(nets[role], [(px, py), (px, vy)], 0.3, "F.Cu")
            via(nets[role], px, vy)
            pad_via[(lref, role)] = (px, vy)
        # 100 nF with its own pair of vias (x +/- 1.9). Vertically it
        # sits toward the square center (outward falls off the board on
        # edge corners, onto escape fences on central ones); the ground
        # via takes whichever side clears the coil escape routes best,
        # and the cap is rotated so its pads match the via sides.
        y_cap = y + (4.4 if which in ("NW", "NE") else -4.4)

        def _route_clear(px_, py_):
            worst = 1e9
            for coil in result.coils:
                for _lbl, _r_layer, rpts in coil.routes:
                    for q0, q1 in zip(rpts, rpts[1:], strict=False):
                        worst = min(worst, _seg_point_dist(q0[0], q0[1], q1[0], q1[1], px_, py_))
            return worst

        placed = False
        for dx_cap in (0.0, -2.5, 2.5, -4.0, 4.0):
            x_cap = x + dx_cap
            west, east = (x_cap - 1.9, y_cap), (x_cap + 1.9, y_cap)
            span = [(x_cap - 2.0, y_cap), (x_cap + 2.0, y_cap)]
            ok = min(_route_clear(*west), _route_clear(*east)) >= (0.4 + 0.5 / 2 + clr)
            # the stub sweep itself must clear the F.Cu escapes
            for coil2 in result.coils:
                for _lbl2, rl2, rpts2 in coil2.routes:
                    if rl2 != "F.Cu":
                        continue
                    for q0, q1 in zip(rpts2, rpts2[1:], strict=False):
                        if _seg_seg_dist(span[0], span[1], tuple(q0), tuple(q1)) < 0.55:
                            ok = False
            ok = ok and all(
                _seg_point_dist(span[0][0], span[0][1], span[1][0], span[1][1], cx_, cy_)
                > r_out + 1.0
                for cx_, cy_ in centers.values()
            )
            if not ok:
                continue
            for gnd_side, v5_side in ((west, east), (east, west)):
                rot_cap = 0.0 if v5_side is west else 180.0
                board.body.append(
                    place_footprint(
                        fp_c,
                        f"CL{lref}",
                        f"{leds.decoupling_nf:.0f}n",
                        x_cap,
                        y_cap,
                        rot_cap,
                        {"1": (board.net(net_5v), ""), "2": (board.net(net_gnd), "")},
                    )
                )
                for pad in fp_c.pads:
                    sx, sy = pad_abs_pos(x_cap, y_cap, rot_cap, pad)
                    if pad.number == "1":
                        track(net_5v, [(sx, sy), v5_side], 0.3, "F.Cu")
                    else:
                        track(net_gnd, [(sx, sy), gnd_side], 0.3, "F.Cu")
                via(net_5v, *v5_side)
                via(net_gnd, *gnd_side)
                pad_via[(lref, "VDDC")] = v5_side
                pad_via[(lref, "VSSC")] = gnd_side
                placed = True
                break
            if placed:
                break
        if not placed:
            raise ValueError(f"no clear decoupling spot for LD{lref}")

    # 5V owns In2 entirely: a loop with a dip under the joint pad row
    # plus a full center cross (same-net crossings are free). GND for
    # the LEDs lives on B.Cu: a loop, a spine through the free slot
    # between the escape lanes, and straight spurs picked by a guard.
    e5, eg = 3.3, 2.0
    dip_x0, dip_x1 = pad_xs[0] - 2.4, pad_xs[-1] + 2.4
    # Top run: local rises past the terminal stacks (x = 25 and 75,
    # they pierce every layer) and a dip under the joint pad row.
    ring5 = [
        (e5, 3.3),
        (22.5, 3.3),
        (22.5, 1.9),
        (27.5, 1.9),
        (27.5, 3.3),
        (dip_x0, 3.3),
        (dip_x0, 4.3),
        (dip_x1, 4.3),
        (dip_x1, 3.3),
        (72.5, 3.3),
        (72.5, 1.9),
        (77.5, 1.9),
        (77.5, 3.3),
        (w_mm - e5, 3.3),
        (w_mm - e5, h_mm - e5),
        (e5, h_mm - e5),
        (e5, 3.3),
    ]
    track(net_5v, ring5, w_ring, "In2.Cu")
    track(net_5v, [(pitch, e5), (pitch, h_mm - e5)], w_ring, "In2.Cu")
    track(net_5v, [(e5, pitch), (w_mm - e5, pitch)], w_ring, "In2.Cu")

    ringg = [
        (eg, 2.0),
        (dip_x0 - 0.9, 2.0),
        (dip_x0 - 0.9, 1.0),
        (dip_x1 + 0.9, 1.0),
        (dip_x1 + 0.9, 2.0),
        (w_mm - eg, 2.0),
        (w_mm - eg, h_mm - eg),
        (eg, h_mm - eg),
        (eg, 2.0),
    ]
    track(net_gnd, ringg, w_ring, "B.Cu")
    track(net_gnd, [(pitch - 1.4, pitch - 10.0), (pitch - 1.4, h_mm - eg)], w_ring, "B.Cu")

    # Joint pins to the loops (THT pads reach every layer).
    x_din, x_5v = pad_xs[-2], pad_xs[-1]
    pad_row_y = 2.5
    track(net_5v, [(x_5v, pad_row_y), (x_5v, 4.3)], w_ring, "In2.Cu")

    # Obstacles for spur legality: coil escape routes, per layer.
    coil_routes = [(r_layer, pts) for coil in result.coils for _lbl, r_layer, pts in coil.routes]

    def spur_clear(a, b, width, layer, net) -> bool:
        for cx, cy in centers.values():
            if _seg_point_dist(*a, *b, cx, cy) < r_out + width / 2 + clr:
                return False
        for _n, jx, jy, jr in joint_pads:
            if _seg_point_dist(*a, *b, jx, jy) < jr + width / 2 + clr:
                return False
        for r_layer, pts in coil_routes:
            if r_layer != layer:
                continue
            for q0, q1 in zip(pts, pts[1:], strict=False):
                if _seg_seg_dist(a, b, tuple(q0), tuple(q1)) < (width + route_w_of(cfg)) / 2 + clr:
                    return False
        for onet, olayer, ow, opts in result.led_tracks:
            if onet == net or olayer != layer:
                continue
            for q0, q1 in zip(opts, opts[1:], strict=False):
                if _seg_seg_dist(a, b, tuple(q0), tuple(q1)) < (width + ow) / 2 + clr:
                    return False
        return True

    def via_clear(x, y, net) -> bool:
        for cx, cy in centers.values():
            if ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 < r_out + via_pad / 2 + clr:
                return False
        for jn, jx, jy, jr in joint_pads:
            if jn != net and ((x - jx) ** 2 + (y - jy) ** 2) ** 0.5 < jr + via_pad / 2 + clr:
                return False
        for _rl, rpts in coil_routes:
            for q0, q1 in zip(rpts, rpts[1:], strict=False):
                if (
                    _seg_point_dist(q0[0], q0[1], q1[0], q1[1], x, y)
                    < (via_pad + route_w_of(cfg)) / 2 + clr
                ):
                    return False
        for onet, _ol, ow, opts in result.led_tracks:
            if onet == net:
                continue
            for q0, q1 in zip(opts, opts[1:], strict=False):
                if _seg_point_dist(q0[0], q0[1], q1[0], q1[1], x, y) < (via_pad + ow) / 2 + clr:
                    return False
        return True

    def path_clear(pts, width, layer, net) -> bool:
        return all(spur_clear(a, b, width, layer, net) for a, b in zip(pts, pts[1:], strict=False))

    spine_x = pitch - 1.4
    lines_5v = {"x": [e5, pitch, w_mm - e5], "y": [3.3, pitch, h_mm - e5]}
    lines_gnd = {"x": [eg, spine_x, w_mm - eg], "y": [2.0, h_mm - eg]}
    for (_ref, role), (vx, vy) in sorted(pad_via.items()):
        if role in ("VDD", "VDDC"):
            nn, layer, lines = net_5v, "In2.Cu", lines_5v
        elif role in ("VSS", "VSSC"):
            nn, layer, lines = net_gnd, "B.Cu", lines_gnd
        else:
            continue
        cands: list[list[tuple[float, float]]] = []
        for t in lines["x"]:
            cands.append([(vx, vy), (t, vy)])
        for t in lines["y"]:
            cands.append([(vx, vy), (vx, t)])
        for m in (2.0, -2.0, 3.5, -3.5, 5.0, -5.0, 7.0, -7.0):
            for t in lines["x"]:
                cands.append([(vx, vy), (vx, vy + m), (t, vy + m)])
            for t in lines["y"]:
                cands.append([(vx, vy), (vx + m, vy), (vx + m, t)])
        cands.sort(
            key=lambda pth: sum(
                abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(pth, pth[1:], strict=False)
            )
        )
        done = False
        for pth in cands:
            if _in_led_board(pth, w_mm, h_mm) and path_clear(pth, w_ring, layer, nn):
                track(nn, pth, w_ring, layer)
                done = True
                break
        if not done and nn == net_gnd:
            # Rescue on In1 toward the ground spine, with its own via.
            for m in (0.0, -1.5, 1.5, -3.0, 3.0, -4.5, 4.5, -6.0, 6.0):
                pth = (
                    [(vx, vy), (vx, vy + m), (spine_x, vy + m)]
                    if abs(m) > 1e-9
                    else [(vx, vy), (spine_x, vy)]
                )
                end = pth[-1]
                if (
                    _in_led_board(pth, w_mm, h_mm)
                    and path_clear(pth, w_chain, "In1.Cu", nn)
                    and via_clear(*end, nn)
                    and pitch - 10.0 <= end[1] <= h_mm - eg
                ):
                    track(nn, pth, w_chain, "In1.Cu")
                    via(nn, *end)
                    done = True
                    break
        if not done:
            raise ValueError(f"no clear spur for {role} via at ({vx},{vy})")

    # In1 data chain lanes. The spiral In1 copper peaks at r_out (the
    # inter-layer link arcs), so every lane keeps its centerline at
    # least r_out + 1.1 from each spiral center, and clear of the
    # terminal stacks; the smart bend plus the guard enforce it.
    e_lane = w_mm - 3.7  # east corridor
    s_lane = h_mm - 3.6  # south corridor
    lanes = {
        "entry": [(x_din, pad_row_y), (x_din, 4.6), (66.0, 4.6), (66.0, 3.3)],
        0: [(e_lane, 3.3)],
        1: [(e_lane, 46.2), (pitch + o + 2.45, 46.2)],
        2: [(pitch + o - 2.45, pitch + 0.6)],
        3: [(pitch + o - 2.45, s_lane), (e_lane, s_lane)],
        4: [(pitch - o + 2.45, h_mm - 1.6)],
        5: [(2.75, h_mm - 1.6), (2.75, pitch + 1.7)],
        6: [(0.9, h_mm - pitch + o + 2.85), (0.9, 47.1), (pitch - o + 2.45, 47.1)],
        # S1SE to S1NW climbs the center column between two joint pad
        # barrels, then runs above the pad row at y = 1.2.
        7: [(49.9, 48.35), (49.9, 1.2), (6.95, 1.2)],
    }
    din_of = {i: pad_via[(i + 1, "DIN")] for i in range(len(chain))}
    dout_of = {i: pad_via[(i + 1, "DOUT")] for i in range(len(chain))}

    def bend(cur, nxt):
        # Of the two possible right-angle corners, keep the one whose
        # two segments stay farthest from every spiral and pad barrel.
        cands = [(nxt[0], cur[1]), (cur[0], nxt[1])]

        def score(c):
            worst = 1e9
            for a, b in ((cur, c), (c, nxt)):
                for cc in centers.values():
                    worst = min(worst, _seg_point_dist(*a, *b, *cc) - r_out)
                for _n, jx, jy, jr in joint_pads:
                    worst = min(worst, _seg_point_dist(*a, *b, jx, jy) - jr)
            return worst

        return max(cands, key=score)

    def hop(net: int, start: tuple[float, float], mids, end: tuple[float, float]):
        pts = [start]
        cur = start
        for m in list(mids) + [end]:
            if abs(m[0] - cur[0]) > 1e-9 and abs(m[1] - cur[1]) > 1e-9:
                pts.append(bend(cur, m))
            pts.append(m)
            cur = m
        track(net, pts, w_chain, "In1.Cu")

    hop(link_nets[0], lanes["entry"][0], lanes["entry"][1:] + lanes[0], din_of[0])
    for i in range(1, len(chain)):
        hop(link_nets[i], dout_of[i - 1], lanes[i], din_of[i])

    # Geometric guard: every LED-subsystem copper stays clear of every
    # spiral circle and of every foreign joint pad barrel, whatever
    # the pitch.
    for net, width, pts in seg_log:
        segs = list(zip(pts, pts[1:] or pts, strict=False)) or [(pts[0], pts[0])]
        for (ax, ay), (bx, by) in segs:
            for qx, qy in ((ax, ay), (bx, by)):
                if not (0.5 <= qx <= w_mm - 0.5 and 0.5 <= qy <= h_mm - 0.5):
                    raise ValueError(f"LED copper outside the board at ({qx:.1f},{qy:.1f})")
            for cx, cy in centers.values():
                d = _seg_point_dist(ax, ay, bx, by, cx, cy)
                need = r_out + width / 2.0 + clr
                if d < need:
                    raise ValueError(
                        f"LED copper too close to spiral at ({cx},{cy}): "
                        f"{d:.2f} < {need:.2f} near ({ax:.1f},{ay:.1f})"
                    )
            for jnet, jx, jy, jr in joint_pads:
                if jnet == net:
                    continue
                d = _seg_point_dist(ax, ay, bx, by, jx, jy)
                need = jr + width / 2.0 + clr
                if d < need:
                    raise ValueError(
                        f"LED copper too close to joint pad ({jx:.1f},{jy}): "
                        f"{d:.2f} < {need:.2f} near ({ax:.1f},{ay:.1f})"
                    )
    result.leds = [(f"LD{i + 1}", corner(sq, which)) for i, (sq, which) in enumerate(chain)]


def _in_led_board(pts, w_mm, h_mm) -> bool:
    return all(0.5 <= x <= w_mm - 0.5 and 0.5 <= y <= h_mm - 0.5 for x, y in pts)


def design_rules(cfg: BoardConfig, result: BuildResult) -> DesignRules:
    """KiCad design rules describing the copper this build emitted.

    Widths and drills are read back from the build, so the project file
    can never drift from the board next to it.
    """
    mock = cfg.mockup.coil_board
    coil_via_pad = 2.0 * cfg.sense_coil.via_drill_mm
    widths = sorted(
        {
            result.track_width_mm,
            mock.route_track_mm,
            *(w for _net, _layer, w, _pts in result.led_tracks),
        }
    )
    return DesignRules(
        clearance_mm=mock.track_clearance_mm,
        track_width_mm=mock.route_track_mm,
        via_diameter_mm=coil_via_pad,
        via_drill_mm=cfg.sense_coil.via_drill_mm,
        min_track_width_mm=min(widths),
        min_via_diameter_mm=min(coil_via_pad, LED_VIA_PAD),
        min_hole_mm=min(cfg.sense_coil.via_drill_mm, LED_VIA_DRILL),
        edge_clearance_mm=mock.edge_clearance_mm,
        track_widths_mm=tuple(widths),
        via_sizes_mm=((LED_VIA_PAD, LED_VIA_DRILL),),
    )


def route_w_of(cfg: BoardConfig) -> float:
    return cfg.mockup.coil_board.route_track_mm


def _seg_seg_dist(a, b, c, d) -> float:
    def _d(p, q, r):
        return _seg_point_dist(p[0], p[1], q[0], q[1], r[0], r[1])

    # segments intersect -> zero
    def ccw(p, q, r):
        return (r[1] - p[1]) * (q[0] - p[0]) - (q[1] - p[1]) * (r[0] - p[0])

    if (ccw(a, b, c) * ccw(a, b, d) < 0) and (ccw(c, d, a) * ccw(c, d, b) < 0):
        return 0.0
    return min(_d(a, b, c), _d(a, b, d), _d(c, d, a), _d(c, d, b))


def _seg_point_dist(ax, ay, bx, by, px, py) -> float:
    vx, vy = bx - ax, by - ay
    ll = vx * vx + vy * vy
    if ll < 1e-12:
        return ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
    t = max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / ll))
    qx, qy = ax + t * vx, ay + t * vy
    return ((px - qx) ** 2 + (py - qy) ** 2) ** 0.5
