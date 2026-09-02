"""Builder of one quadrant board: spirals, escapes, camp LEDs and their
distribution, the front-end strip skeleton (FPC link, buses), holes and
outline. Everything derives from config/board.yaml through layout.py.

Copper plan, per layer:
- F.Cu: spiral layer 1, coil A escapes, LED pads and via stubs, FPC pads;
- In1.Cu: spiral layer 2, LED data chain, GND bus inside the strip;
- In2.Cu: spiral layer 3, 5 V grid for the LEDs (corridor lines, ring);
- B.Cu: spiral layer 4, coil B escapes, GND lines (edges, mid corridor)
  and the LED ground spurs.

Escapes are deterministic lanes (layout.py); the LED chain and the
supply spurs are found by the grid router against everything already
placed, then a global clearance check validates the whole board.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from analoggen.fplib import Footprint, load_footprint, pad_abs_pos, place_footprint
from coilgen.geometry import LayerPath, spiral_stack
from coilgen.kicad import Board
from coilgen.project import DesignRules
from shapely.geometry import LineString, Point
from shapely.strtree import STRtree

from chessboard_calc.config import BoardConfig

from .layout import LED_ROLES, Layout, Led, make_layout
from .router import Raster

COPPER_LAYERS = ["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"]
NET_5V, NET_GND = "5V_LED", "GND"
CAP_OFFSET = (4.5, 4.0)  # decoupling cap from its LED, toward the square center
CAP_VIA_DY = 1.5  # cap vias, toward the square center
PIN_VIA_STEP = 1.2  # staggered vias behind the FPC pads
FP_LED = "LED_SMD:LED_WS2812B_PLCC4_5.0x5.0mm_P3.2mm"
FP_CAP = "Capacitor_SMD:C_0603_1608Metric"


@dataclass
class Track:
    net: str
    layer: str
    width: float
    pts: list[tuple[float, float]]


@dataclass
class Via:
    net: str
    x: float
    y: float
    pad: float
    drill: float


@dataclass
class PadItem:
    net: str
    layer: str
    x: float
    y: float
    w: float
    h: float


@dataclass
class CoilDebug:
    name: str
    center: tuple[float, float]
    paths: list[LayerPath]
    vias: list[tuple[float, float]]
    terminal: tuple[float, float]
    routes: list[tuple[str, str, list[tuple[float, float]]]]


@dataclass
class BuildResult:
    board: Board
    layout: Layout
    coils: list[CoilDebug] = field(default_factory=list)
    track_width_mm: float = 0.0
    turns_per_layer: int = 0
    pad_xs: list[float] = field(default_factory=list)
    holes: list[tuple[float, float, float]] = field(default_factory=list)
    outline_mm: tuple[float, float] = (0.0, 0.0)
    leds: list[tuple[str, tuple[float, float]]] = field(default_factory=list)
    led_tracks: list = field(default_factory=list)  # (net, layer, width, pts)
    led_vias: list = field(default_factory=list)  # (x, y)
    tracks: list[Track] = field(default_factory=list)
    vias: list[Via] = field(default_factory=list)
    pads: list[PadItem] = field(default_factory=list)
    clearance_errors: list[str] = field(default_factory=list)
    open_routes: list[str] = field(default_factory=list)


class Builder:
    def __init__(self, cfg: BoardConfig) -> None:
        self.cfg = cfg
        self.q = cfg.plateau.quadrant
        self.rt = self.q.routing
        self.lay = make_layout(cfg)
        self.board = Board(
            thickness_mm=cfg.gap.pcb_mm, title="Damier LC, quadrant 4x4, bobines et frontal"
        )
        self.res = BuildResult(
            board=self.board,
            layout=self.lay,
            track_width_mm=self.lay.spiral_track,
            turns_per_layer=self.lay.turns_per_layer,
            outline_mm=(self.lay.board_w, self.lay.board_h),
        )
        self.w = self.rt.route_track_mm
        self.clr = self.rt.track_clearance_mm
        self.gnd_lines: list[list[tuple[float, float]]] = []
        self.v5_lines: list[list[tuple[float, float]]] = []
        # obstacle rasters keyed by (layer, excluded net), painted incrementally
        self.base: dict[tuple[str, str], Raster] = {}

    # ------------------------------------------------------------ emitters
    def track(self, net: str, layer: str, pts, width: float | None = None) -> None:
        width = self.w if width is None else width
        pts = [(float(x), float(y)) for x, y in pts]
        self.board.polyline(pts, width, layer, self.board.net(net))
        self.res.tracks.append(Track(net, layer, width, pts))
        self.res.led_tracks.append((net, layer, width, pts))
        r = width / 2.0 + self.inflate
        for (rl, excl), ras in self.base.items():
            if rl == layer and excl != net:
                for a, b in zip(pts, pts[1:], strict=False):
                    ras.segment(a[0], a[1], b[0], b[1], r)

    def via(
        self, net: str, x: float, y: float, pad: float | None = None, drill: float | None = None
    ) -> None:
        pad = self.rt.led_via.pad_mm if pad is None else pad
        drill = self.rt.led_via.drill_mm if drill is None else drill
        self.board.via(x, y, pad, drill, self.board.net(net))
        self.res.vias.append(Via(net, float(x), float(y), pad, drill))
        self.res.led_vias.append((float(x), float(y)))
        for (_rl, excl), ras in self.base.items():
            if excl != net:
                ras.disc(x, y, pad / 2.0 + self.inflate)

    def footprint(
        self,
        fp: Footprint,
        ref: str,
        value: str,
        x: float,
        y: float,
        rot: float,
        pad_nets: dict[str, str],
    ) -> None:
        nets = {num: (self.board.net(n), n) for num, n in pad_nets.items()}
        self.board.body.append(place_footprint(fp, ref, value, x, y, rot, nets))
        for pad in fp.pads:
            if pad.number not in pad_nets:
                continue
            px, py = pad_abs_pos(x, y, rot, pad)
            sw, sh = pad.size
            if abs((rot + pad.rot) % 180.0 - 90.0) < 1e-6:
                sw, sh = sh, sw
            for layer in pad.layers:
                if layer in COPPER_LAYERS or layer == "*.Cu":
                    self.res.pads.append(PadItem(pad_nets[pad.number], layer, px, py, sw, sh))

    # ------------------------------------------------------------ pieces
    def spirals(self) -> None:
        lay, cfg = self.lay, self.cfg
        via_drill = cfg.sense_coil.via_drill_mm
        via_pad = 2.0 * via_drill
        for coil in lay.coils:
            net = coil.net
            paths = spiral_stack(
                coil.center,
                COPPER_LAYERS,
                lay.r_in,
                lay.r_out,
                lay.turns_per_layer,
                start_angle_deg=coil.start_angle_deg,
            )
            dbg = CoilDebug(net, coil.center, paths, [], coil.terminal, [])
            for path in paths:
                self.board.polyline(path.points, lay.spiral_track, path.layer, self.board.net(net))
                self.res.tracks.append(
                    Track(
                        net,
                        path.layer,
                        lay.spiral_track,
                        [tuple(map(float, p)) for p in path.points],
                    )
                )
            for a, _b in zip(paths, paths[1:], strict=False):
                jx, jy = map(float, a.points[-1])
                self.board.via(jx, jy, via_pad, via_drill, self.board.net(net))
                self.res.vias.append(Via(net, jx, jy, via_pad, via_drill))
                dbg.vias.append((jx, jy))
            self.res.coils.append(dbg)

    def escapes(self) -> None:
        lay = self.lay
        x_in = self.q.strip.cell_entry_x_mm
        for coil, dbg in zip(lay.coils, self.res.coils, strict=True):
            tx, ty = coil.terminal
            pts = [
                (tx, ty),
                (tx, coil.lane_y),
                (coil.lane_x, coil.lane_y),
                (coil.lane_x, coil.cell_y),
                (x_in, coil.cell_y),
            ]
            for term, layer in (("A", "F.Cu"), ("B", "B.Cu")):
                self.board.polyline(pts, self.w, layer, self.board.net(coil.net))
                self.res.tracks.append(Track(coil.net, layer, self.w, list(pts)))
                dbg.routes.append((f"{coil.net}_{term}", layer, list(pts)))

    def supply_lines(self) -> None:
        """5 V grid on In2 and GND lines on B.Cu, both joined to strip buses
        on the inner layers (the escapes cross the strip boundary on F.Cu
        and B.Cu, so a vertical bus there must be In1 or In2). No east
        edge line: the east column LED vias sit 0.65 mm from the edge."""
        lay = self.lay
        w = self.rt.ring_track_mm
        e5, eg = 1.6, 1.0
        W, H = lay.board_w, lay.board_h
        xs = lay.strip_w - 1.0
        self.bus_gnd_x, self.bus_5v_x = lay.strip_w - 0.8, lay.strip_w - 2.4

        for y in (e5, H - e5):
            line = [(self.bus_5v_x, y), (W - e5, y)]
            self.track(NET_5V, "In2.Cu", line, w)
            self.v5_lines.append(line)
        for x in lay.corridor_xs:
            line = [(x, e5), (x, H - e5)]
            self.track(NET_5V, "In2.Cu", line, w)
            self.v5_lines.append(line)
        for y in lay.corridor_ys:
            line = [(xs, y), (W - e5, y)]
            self.track(NET_5V, "In2.Cu", line, w)
            self.v5_lines.append(line)
        self.track(NET_5V, "In2.Cu", [(self.bus_5v_x, e5), (self.bus_5v_x, H - e5)], w)

        mid = lay.corridor_ys[len(lay.corridor_ys) // 2]
        for y in (eg, mid, H - eg):
            line = [(xs, y), (W - eg, y)]
            self.track(NET_GND, "B.Cu", line, w)
            self.gnd_lines.append(line)
        # In1 bus down the strip, tied to the B.Cu lines by vias at three points
        y_top, y_bot = 6.0, H - 6.0
        self.track(NET_GND, "In1.Cu", [(self.bus_gnd_x, y_top), (self.bus_gnd_x, y_bot)], w)
        for y, ly in ((y_top, eg), (mid + 1.5, mid), (y_bot, H - eg)):
            self.via(NET_GND, self.bus_gnd_x, y, 0.8, 0.4)
            pts = (
                [(self.bus_gnd_x, y), (self.bus_gnd_x, ly), (xs, ly)]
                if abs(y - ly) > 1e-9
                else [(self.bus_gnd_x, y), (xs, ly)]
            )
            self.track(NET_GND, "B.Cu", pts, w)

    def connector(self) -> None:
        lay, link = self.lay, self.q.link
        fp = load_footprint(link.footprint)
        cx, cy = lay.connector_xy
        rot = 270.0
        nets = {str(i + 1): net for i, net in enumerate(link.pinout)}
        nets["MP"] = NET_GND
        self.footprint(fp, "J1", "FPC 16", cx, cy, rot, nets)
        self.pin_vias: dict[str, tuple[float, float]] = {}
        # adjacent used pins fan out north, straight and south of their row
        # before their vias, so vias never sit next to a neighbor's stub
        bends = {NET_GND: 0.0, NET_5V: -1.35, "LED_DIN": 0.0, "LED_DOUT": 1.35}
        for i, net in enumerate(link.pinout):
            if net not in bends:
                continue
            pad = fp.pad(str(i + 1))
            px, py = pad_abs_pos(cx, cy, rot, pad)
            x_bend, vy = px + 1.15, py + bends[net]
            vx = x_bend + (1.6 if bends[net] == 0.0 else 0.5)
            pts = [(px, py), (x_bend, py)] + ([(x_bend, vy)] if bends[net] else []) + [(vx, vy)]
            self.track(net, "F.Cu", pts, 0.25)
            self.via(net, vx, vy)
            self.pin_vias[net] = (vx, vy)
        # GND and 5 V pins onto their strip buses
        gx, gy = self.pin_vias[NET_GND]
        self.track(NET_GND, "In1.Cu", [(gx, gy), (self.bus_gnd_x, gy)], self.rt.ring_track_mm)
        vx, vy = self.pin_vias[NET_5V]
        self.track(NET_5V, "In2.Cu", [(vx, vy), (self.bus_5v_x, vy)], self.rt.ring_track_mm)

    def leds(self) -> None:
        lay = self.lay
        fp, fp_c = load_footprint(FP_LED), load_footprint(FP_CAP)
        stub = self.rt.led_via.stub_mm
        chain = list(lay.leds)
        link_nets = ["LED_DIN"] + [f"LED_L{i}" for i in range(1, len(chain))] + ["LED_DOUT"]
        self.led_vias: dict[tuple[str, str], tuple[float, float]] = {}
        self.cap_vias: dict[tuple[str, str], tuple[float, float]] = {}
        for i, led in enumerate(chain):
            nets = {"VDD": NET_5V, "VSS": NET_GND, "DIN": link_nets[i], "DOUT": link_nets[i + 1]}
            pad_nets = {num: nets[role] for num, role in LED_ROLES.items()}
            self.footprint(fp, led.ref, "WS2812B", led.x, led.y, led.rot, pad_nets)
            for num, role in LED_ROLES.items():
                px, py = led.pad(num)
                vx, vy = led.via(num, stub)
                self.track(nets[role], "F.Cu", [(px, py), (vx, vy)])
                self.via(nets[role], vx, vy)
                self.led_vias[(led.ref, role)] = (vx, vy)
            self._decoupling(led, fp_c)
            self.res.leds.append((led.ref, (led.x, led.y)))

    def _decoupling(self, led: Led, fp_c: Footprint) -> None:
        coil = self.lay.coils[led.coil]
        cx, cy = coil.center
        sx = 1.0 if led.x < cx else -1.0
        sy = 1.0 if led.y < cy else -1.0
        x, y = led.x + sx * CAP_OFFSET[0], led.y + sy * CAP_OFFSET[1]
        self.footprint(fp_c, "CL" + led.ref[2:], "100n", x, y, 0.0, {"1": NET_5V, "2": NET_GND})
        for num, net in (("1", NET_5V), ("2", NET_GND)):
            pad = fp_c.pad(num)
            px, py = pad_abs_pos(x, y, 0.0, pad)
            vy = py + sy * CAP_VIA_DY
            self.track(net, "F.Cu", [(px, py), (px, vy)])
            self.via(net, px, vy)
            self.cap_vias[(led.ref, net)] = (px, vy)
            if (vy - cy) ** 2 + (px - cx) ** 2 < (self.lay.r_out + 1.2) ** 2:
                raise ValueError(f"{led.ref}: decoupling via inside the spiral margin")

    def holes(self) -> None:
        lay = self.lay
        d = self.q.mounting_hole_d_mm
        for i, (hx, hy) in enumerate(lay.mounting_holes, start=1):
            self.board.npth_hole(hx, hy, d, ref=f"H{i}")
            self.res.holes.append((hx, hy, d))
        px, py = lay.pin_hole_xy
        pin_d = self.cfg.plateau.base.locating_pins.d_mm + 0.2
        self.board.npth_hole(px, py, pin_d, ref="P1")
        self.res.holes.append((px, py, pin_d))

    # ------------------------------------------------------------ routing
    @property
    def inflate(self) -> float:
        """Obstacle inflation: clearance, half track, raster slop."""
        return self.clr + self.w / 2.0 + 0.75 * self.rt.grid_mm

    RASTERS = (("In1.Cu", ""), ("B.Cu", NET_GND), ("In2.Cu", NET_5V))

    def build_rasters(self) -> None:
        """Copper so far per (layer, excluded net); later tracks and vias
        are painted as they are emitted. The chain hops route against
        everything (each link is its own net, only its two ends are
        freed); the supply spurs see their own net as free space."""
        lay = self.lay
        g = self.rt.grid_mm
        margin = self.rt.edge_clearance_mm + self.w / 2.0
        for layer, excl in self.RASTERS:
            ras = Raster(lay.board_w, lay.board_h, g)
            ras.block_outside(margin, lay.board_w, lay.board_h)
            for t in self.res.tracks:
                if t.layer == layer and t.net != excl:
                    for a, b in zip(t.pts, t.pts[1:], strict=False):
                        ras.segment(a[0], a[1], b[0], b[1], t.width / 2.0 + self.inflate)
            for v in self.res.vias:
                if v.net != excl:
                    ras.disc(v.x, v.y, v.pad / 2.0 + self.inflate)
            for p in self.res.pads:
                if p.net != excl and (p.layer == layer or p.layer == "*.Cu"):
                    ras.rect(p.x, p.y, p.w, p.h, self.inflate)
            for hx, hy, hd in self.res.holes:
                ras.disc(hx, hy, hd / 2.0 + 0.5 + self.w / 2.0)
            self.base[(layer, excl)] = ras

    def route(self, net: str, layer: str, start, goal, label: str) -> bool:
        base = self.base.get((layer, net)) or self.base[(layer, "")]
        ras = Raster.__new__(Raster)
        ras.__dict__.update(base.__dict__)
        ras.blocked = base.blocked.copy()
        free_r = self.rt.led_via.pad_mm / 2.0 + self.inflate + 0.05
        for x, y in (start, goal):
            i0, i1, j0, j1 = ras._window(x, y, x, y, free_r)
            xs, ys = ras._xs[j0:j1, i0:i1], ras._ys[j0:j1, i0:i1]
            ras.blocked[j0:j1, i0:i1] &= ~((xs - x) ** 2 + (ys - y) ** 2 <= free_r * free_r)
        path = ras.route(start, goal)
        if path is None:
            self.res.open_routes.append(f"{label} ({net} on {layer})")
            return False
        self.track(net, layer, path)
        return True

    def chain(self) -> None:
        leds = self.lay.leds
        prev = self.pin_vias["LED_DIN"]
        prev_net = "LED_DIN"
        for i, led in enumerate(leds):
            self.route(
                prev_net, "In1.Cu", prev, self.led_vias[(led.ref, "DIN")], f"chain into {led.ref}"
            )
            prev = self.led_vias[(led.ref, "DOUT")]
            prev_net = f"LED_L{i + 1}" if i + 1 < len(leds) else "LED_DOUT"
        self.route("LED_DOUT", "In1.Cu", prev, self.pin_vias["LED_DOUT"], "chain return")

    def spurs(self) -> None:
        for led in self.lay.leds:
            for role, net, layer, lines in (
                ("VSS", NET_GND, "B.Cu", self.gnd_lines),
                ("VDD", NET_5V, "In2.Cu", self.v5_lines),
            ):
                cap = self.cap_vias[(led.ref, net)]
                self.route(
                    net,
                    layer,
                    self.led_vias[(led.ref, role)],
                    cap,
                    f"{led.ref} {role} to its capacitor",
                )
                goal = _nearest_on_lines(cap, lines)
                self.route(net, layer, cap, goal, f"{led.ref} {role} to the {net} line")

    # ------------------------------------------------------------ drawing
    def outline(self) -> None:
        lay, b = self.lay, self.board
        b.gr_rect(0.0, 0.0, lay.board_w, lay.board_h, "Edge.Cuts")
        b.gr_line(lay.strip_w, 0.0, lay.strip_w, lay.board_h, "F.SilkS", 0.15)
        for coil in lay.coils:
            cx, cy = coil.center
            b.gr_text(coil.net, cx, cy - 3.0, "F.SilkS", 2.0)
            b.gr_circle(cx, cy, 1.0, "F.SilkS", 0.15)
        b.gr_text(
            "DAMIER LC / QUADRANT 4x4 / p50",
            lay.strip_w + 2.0 * lay.pitch,
            lay.board_h - 3.0,
            "F.SilkS",
            1.5,
        )
        b.gr_text(
            "quadgen rev A",
            lay.strip_w + 2.0 * lay.pitch,
            lay.board_h - 6.5,
            "B.SilkS",
            1.2,
            mirror=True,
        )
        b.gr_text("J1 FPC", 5.5, 3.0, "F.SilkS", 1.0)

    # ------------------------------------------------------------ checks
    def clearance_check(self) -> list[str]:
        """Exact same-layer clearance between items of different nets, vias
        and holes against everything; a copper item off the board."""
        lay = self.lay
        items = []  # (net, layer, geometry)
        for t in self.res.tracks:
            items.append((t.net, t.layer, LineString(t.pts).buffer(t.width / 2.0)))
        for v in self.res.vias:
            for layer in COPPER_LAYERS:
                items.append((v.net, layer, Point(v.x, v.y).buffer(v.pad / 2.0)))
        for p in self.res.pads:
            layers = COPPER_LAYERS if p.layer == "*.Cu" else [p.layer]
            from shapely.geometry import box

            for layer in layers:
                items.append(
                    (p.net, layer, box(p.x - p.w / 2, p.y - p.h / 2, p.x + p.w / 2, p.y + p.h / 2))
                )
        for hx, hy, hd in self.res.holes:
            for layer in COPPER_LAYERS:
                items.append(("__hole__", layer, Point(hx, hy).buffer(hd / 2.0 + 0.35)))
        errors = []
        by_layer: dict[str, list] = {}
        for it in items:
            by_layer.setdefault(it[1], []).append(it)
        clr = self.clr - 0.02  # tolerance on the raster path rounding
        for layer, its in by_layer.items():
            geoms = [g for _n, _l, g in its]
            tree = STRtree(geoms)
            for i, (net, _l, g) in enumerate(its):
                for j in tree.query(g.buffer(clr)):
                    j = int(j)
                    if j <= i or its[j][0] == net:
                        continue
                    d = g.distance(geoms[j])
                    if d < clr:
                        from shapely.ops import nearest_points

                        c = nearest_points(g, geoms[j])[0]
                        errors.append(
                            f"{layer}: {net} vs {its[j][0]} at ({c.x:.1f},{c.y:.1f}) gap {d:.3f}"
                        )
        edge = self.rt.edge_clearance_mm - 0.02
        for net, _layer, g in items:
            if net == "__hole__":
                continue
            minx, miny, maxx, maxy = g.bounds
            if minx < edge or miny < edge or maxx > lay.board_w - edge or maxy > lay.board_h - edge:
                errors.append(f"{net} too close to the board edge at ({minx:.1f},{miny:.1f})")
        return sorted(set(errors))

    # ------------------------------------------------------------ build
    def build(self) -> BuildResult:
        self.spirals()
        self.escapes()
        self.holes()
        self.supply_lines()
        self.connector()
        self.leds()
        self.build_rasters()
        self.chain()
        self.spurs()
        self.outline()
        self.res.clearance_errors = self.clearance_check()
        return self.res


def _nearest_on_lines(p: tuple[float, float], lines) -> tuple[float, float]:
    best, best_d = None, float("inf")
    px, py = p
    for line in lines:
        for (ax, ay), (bx, by) in zip(line, line[1:], strict=False):
            vx, vy = bx - ax, by - ay
            ll = vx * vx + vy * vy
            t = 0.0 if ll < 1e-12 else max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / ll))
            qx, qy = ax + t * vx, ay + t * vy
            d = (px - qx) ** 2 + (py - qy) ** 2
            if d < best_d:
                best, best_d = (qx, qy), d
    return best


def build_quadrant(cfg: BoardConfig) -> BuildResult:
    return Builder(cfg).build()


def design_rules(cfg: BoardConfig, result: BuildResult) -> DesignRules:
    rt = cfg.plateau.quadrant.routing
    coil_via_pad = 2.0 * cfg.sense_coil.via_drill_mm
    widths = sorted({round(t.width, 3) for t in result.tracks})
    return DesignRules(
        clearance_mm=rt.track_clearance_mm,
        track_width_mm=rt.route_track_mm,
        via_diameter_mm=rt.led_via.pad_mm,
        via_drill_mm=rt.led_via.drill_mm,
        min_track_width_mm=min(widths),
        min_via_diameter_mm=min(coil_via_pad, rt.led_via.pad_mm),
        min_hole_mm=min(cfg.sense_coil.via_drill_mm, rt.led_via.drill_mm),
        edge_clearance_mm=rt.edge_clearance_mm,
        track_widths_mm=tuple(widths),
        via_sizes_mm=((coil_via_pad, cfg.sense_coil.via_drill_mm), (0.8, 0.4)),
    )


def summary(result: BuildResult) -> str:
    n_tracks = sum(len(t.pts) - 1 for t in result.tracks)
    return (
        f"{len(result.coils)} coils, {len(result.leds)} LEDs, {n_tracks} segments, "
        f"{len(result.vias)} vias, open routes {len(result.open_routes)}, "
        f"clearance errors {len(result.clearance_errors)}"
    )


_ = np  # numpy is used by the router; keep the import explicit for type hints
