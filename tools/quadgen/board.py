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

import dataclasses
import math
import sys
from dataclasses import dataclass, field

import numpy as np
from analoggen.circuit import Circuit
from analoggen.fplib import Footprint, load_footprint, pad_abs_pos, place_footprint
from coilgen.geometry import LayerPath, spiral_stack
from coilgen.kicad import Board
from coilgen.project import DesignRules
from shapely.geometry import LineString, Point
from shapely.strtree import STRtree

from chessboard_calc.config import BoardConfig

from .circuit import build_quadrant_circuit
from .escape import (
    FANOUT_VIA_DRILL_MM,
    FANOUT_VIA_PAD_MM,
    STUB_WIDTH_MM,
    claim_stubs,
    escape_stubs,
    exit_cells,
    free_stubs,
    reclaim_stubs,
    runway_end,
    stub_cells,
)
from .layout import LED_ROLES, Layout, Led, make_layout
from .router import MultiRouter, Raster
from .strip import BUS_3V3_IN2, BUSES_IN1, strip_placements

COPPER_LAYERS = ["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"]
NET_5V, NET_GND = "5V_LED", "GND"
CAP_OFFSET = (4.5, 4.0)  # decoupling cap from its LED, toward the square center
CAP_VIA_DY = 1.5  # cap vias, toward the square center
PIN_VIA_STEP = 1.2  # staggered vias behind the FPC pads
FP_LED = "LED_SMD:LED_WS2812B_PLCC4_5.0x5.0mm_P3.2mm"
FP_CAP = "Capacitor_SMD:C_0603_1608Metric"
CHECK_SLOP_MM = 0.001  # numerical slop of the exact clearance checks
# Stacking vias sit radially off the turn bands: a via at the inner or
# outer radius lands in the turns of the two other layers (the next turn
# is a quarter turn away, 0.4 mm further out) and shorts the coil. Each
# junction is joined to its two spirals by a radial run of the same
# track. Half track 0.8, via pad 0.3, clearance 0.15, margin 0.05.
VIA_OFFSET_MM = 1.3
# The last junction (In2 to B.Cu) goes deeper into the hollow: its radial
# run on B.Cu carries the coil net tie, distances along the run from the
# via: the wide track of net A (round end), pad A, pad B touching it, the
# wide track of net B resuming past pad B, then the lead-in arc.
TIE_VIA_OFFSET_MM = 3.5
TIE_PAD_MM = 0.6
TIE_STEP_MM = 0.58
TIE_ALONG_MM = 2.33  # pad B center
TIE_WIDE_END_MM = 1.43  # net A track ends this far before pad B (cap 0.33 from pad B)
TIE_WIDE_RESUME_MM = 0.9  # net B track resumes this far past pad B (cap 0.38 from pad A)


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
    rot: float = 0.0  # degrees, KiCad sense (counterclockwise on screen)

    def geometry(self):
        """Exact outline as a shapely polygon."""
        from shapely import affinity
        from shapely.geometry import box

        g = box(-self.w / 2, -self.h / 2, self.w / 2, self.h / 2)
        if self.rot:
            g = affinity.rotate(g, -self.rot, origin=(0, 0))
        return affinity.translate(g, self.x, self.y)


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
    placements: dict = field(default_factory=dict)
    circuit: Circuit | None = None
    open_nets: list[str] = field(default_factory=list)
    routed_nets: int = 0
    chain: object = None


class Builder:
    def __init__(self, cfg: BoardConfig, strip: bool = True) -> None:
        self.cfg = cfg
        self.with_strip = strip
        self.q = cfg.plateau.quadrant
        self.rt = self.q.routing
        self.lay = make_layout(cfg)
        self.circuit, self.chain_design = build_quadrant_circuit(cfg)
        self.board = Board(
            thickness_mm=cfg.gap.pcb_mm, title="Damier LC, quadrant 4x4, bobines et frontal"
        )
        self.res = BuildResult(
            board=self.board,
            layout=self.lay,
            track_width_mm=self.lay.spiral_track,
            turns_per_layer=self.lay.turns_per_layer,
            outline_mm=(self.lay.board_w, self.lay.board_h),
            circuit=self.circuit,
            chain=self.chain_design,
        )
        self.w = self.rt.route_track_mm
        self.clr = self.rt.track_clearance_mm
        self.gnd_lines: list[list[tuple[float, float]]] = []
        self.v5_lines: list[list[tuple[float, float]]] = []
        # obstacle rasters keyed by (layer, excluded net), painted incrementally
        self.base: dict[tuple[str, str], Raster] = {}
        self.by_ref = {c.ref: c for c in self.circuit.components}

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
        """A via, unless one of the same net already covers this point (the
        strip router restarts from the escape via of a cell entry and may
        put its own a lattice cell away: two drills that close are a
        fabrication error, and the existing pad already joins the track)."""
        pad = self.rt.led_via.pad_mm if pad is None else pad
        drill = self.rt.led_via.drill_mm if drill is None else drill
        for v in self.res.vias:
            reach = min(v.pad, pad) / 2.0 - 0.02
            if v.net == net and (v.x - x) ** 2 + (v.y - y) ** 2 <= reach * reach:
                return
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
            # an unconnected pad is copper too: an obstacle for every net
            net = pad_nets.get(pad.number, f"__nc_{ref}_{pad.number}")
            px, py = pad_abs_pos(x, y, rot, pad)
            sw, sh = pad.size
            if abs((rot + pad.rot) % 180.0 - 90.0) < 1e-6:
                sw, sh = sh, sw
            for layer in pad.layers:
                if layer in COPPER_LAYERS or layer == "*.Cu":
                    self.res.pads.append(PadItem(net, layer, px, py, sw, sh))

    # ------------------------------------------------------------ pieces
    def spirals(self) -> None:
        """The four layers, the three stacking vias and the first
        millimeters of the B.Cu lead-in arc carry C{k}_A; a net tie of two
        touching B.Cu pads on that arc starts C{k}_B, which runs to the
        terminal as a thin track. The spiral is an inductor between two
        nets on the board exactly as in the schematic (NT{k}), and no
        copper of one net ever covers a hole of the other."""
        lay, cfg = self.lay, self.cfg
        via_drill = cfg.sense_coil.via_drill_mm
        via_pad = 2.0 * via_drill
        for coil in lay.coils:
            net_a, net_b = f"{coil.net}_A", f"{coil.net}_B"
            paths = spiral_stack(
                coil.center,
                COPPER_LAYERS,
                lay.r_in,
                lay.r_out,
                lay.turns_per_layer,
                start_angle_deg=coil.start_angle_deg,
            )
            paths, junctions = _offset_junctions(paths, coil.center, lay.r_in, lay.r_out)
            dbg = CoilDebug(coil.net, coil.center, paths, [], coil.terminal, [])
            for i, path in enumerate(paths):
                if i == len(paths) - 1:
                    self._tied_last_layer(coil, path, net_a, net_b)
                    continue
                self.board.polyline(
                    path.points, lay.spiral_track, path.layer, self.board.net(net_a)
                )
                self.res.tracks.append(
                    Track(
                        net_a,
                        path.layer,
                        lay.spiral_track,
                        [tuple(map(float, p)) for p in path.points],
                    )
                )
            for jx, jy in junctions:
                dbg.vias.append((jx, jy))
                self.board.via(jx, jy, via_pad, via_drill, self.board.net(net_a))
                self.res.vias.append(Via(net_a, jx, jy, via_pad, via_drill))
            self.res.coils.append(dbg)

    def _tied_last_layer(self, coil, path: LayerPath, net_a: str, net_b: str) -> None:
        """B.Cu layer of a coil: the radial run from the junction via as net
        A up to the tie, the tie, then net B along the rest of the run, the
        lead-in arc and the spiral, all at the spiral track width."""
        pts = np.asarray(path.points, dtype=float)
        seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
        s = np.concatenate([[0.0], np.cumsum(seg)])

        def at(d: float) -> tuple[float, float]:
            x = float(np.interp(d, s, pts[:, 0]))
            y = float(np.interp(d, s, pts[:, 1]))
            return round(x, 4), round(y, 4)

        s_tie = TIE_ALONG_MM
        width = self.lay.spiral_track
        wide_a = [tuple(map(float, p)) for p in pts[s < s_tie - TIE_WIDE_END_MM]]
        wide_a.append(at(s_tie - TIE_WIDE_END_MM))
        self.board.polyline(wide_a, width, path.layer, self.board.net(net_a))
        self.res.tracks.append(Track(net_a, path.layer, width, wide_a))
        s_b = s_tie + TIE_WIDE_RESUME_MM
        wide_b = [at(s_b)] + [tuple(map(float, p)) for p in pts[s > s_b]]
        self.board.polyline(wide_b, width, path.layer, self.board.net(net_b))
        self.res.tracks.append(Track(net_b, path.layer, width, wide_b))
        bx, by = at(s_tie)
        px, py = at(s_tie + 0.05)
        qx, qy = at(s_tie - 0.05)
        ux, uy = px - qx, py - qy
        norm = (ux * ux + uy * uy) ** 0.5
        ux, uy = ux / norm, uy / norm
        # footprint rotation putting pad A (local +x) behind pad B along the arc
        rot = np.degrees(np.arctan2(uy, -ux))
        self.net_tie(f"NT{coil.idx + 1}", bx, by, rot, net_a, net_b)

    def net_tie(self, ref: str, x: float, y: float, rot: float, net_a: str, net_b: str) -> None:
        """quadgen:COIL_TIE: two touching B.Cu pads, pad 2 (net B) at the
        origin and pad 1 (net A) one step along local +x, both inside the
        hollow of the coil on the radial run of the last junction. KiCad's
        net_tie_pad_groups makes their contact legal, the two nets stay
        distinct for the router and the checks (_tie_pair)."""
        ia, ib = self.board.net(net_a), self.board.net(net_b)
        pad = TIE_PAD_MM
        self.board.body.append(
            "\n".join(
                [
                    f'  (footprint "quadgen:COIL_TIE" (layer "F.Cu") (at {x:g} {y:g} {rot:.3f})',
                    "    (attr smd exclude_from_pos_files exclude_from_bom)",
                    '    (net_tie_pad_groups "1,2")',
                    f'    (fp_text reference "{ref}" (at 0 -1.5) (layer "F.Fab")',
                    "      (effects (font (size 0.8 0.8) (thickness 0.12)))",
                    "    )",
                    '    (fp_text value "spirale" (at 0 1.5) (layer "F.Fab")',
                    "      (effects (font (size 0.8 0.8) (thickness 0.12)))",
                    "    )",
                    f'    (pad "1" smd rect (at {TIE_STEP_MM:g} 0 {rot:.3f}) '
                    f'(size {pad:g} {pad:g}) (layers "B.Cu") (net {ia} "{net_a}"))',
                    f'    (pad "2" smd rect (at 0 0 {rot:.3f}) (size {pad:g} {pad:g}) '
                    f'(layers "B.Cu") (net {ib} "{net_b}"))',
                    "  )",
                ]
            )
        )
        th = np.radians(rot)
        ax = x + TIE_STEP_MM * float(np.cos(th))
        ay = y - TIE_STEP_MM * float(np.sin(th))
        self.res.pads.append(PadItem(net_a, "B.Cu", round(ax, 4), round(ay, 4), pad, pad, rot))
        self.res.pads.append(PadItem(net_b, "B.Cu", x, y, pad, pad, rot))

    def escapes(self) -> None:
        """Both terminals follow the same lane; A (F.Cu) enters its cell at
        y - 0.6 and B (B.Cu) at y + 0.6, where a via brings B to the top."""
        lay = self.lay
        x_in = self.q.strip.cell_entry_x_mm
        for coil, dbg in zip(lay.coils, self.res.coils, strict=True):
            tx, ty = coil.terminal
            for term, layer, dy in (("A", "F.Cu", -0.6), ("B", "B.Cu", 0.6)):
                net = f"{coil.net}_{term}"
                pts = [
                    (tx, ty),
                    (tx, coil.lane_y),
                    (coil.lane_x, coil.lane_y),
                    (coil.lane_x, coil.cell_y + dy),
                    (x_in, coil.cell_y + dy),
                ]
                self.board.polyline(pts, self.w, layer, self.board.net(net))
                self.res.tracks.append(Track(net, layer, self.w, list(pts)))
                dbg.routes.append((net, layer, list(pts)))
            self.via(f"{coil.net}_B", x_in, coil.cell_y + 0.6)

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
        y_top = 6.0
        # between the last cell and the 5 V line
        y_bot = self.lay.cell_ys[-1] + self.q.strip.cell_pitch_mm / 2.0 + 0.7
        self.track(NET_GND, "In1.Cu", [(self.bus_gnd_x, y_top), (self.bus_gnd_x, y_bot)], w)
        for y, ly in ((y_top, eg), (mid + 1.5, mid), (y_bot, H - eg)):
            self.via(NET_GND, self.bus_gnd_x, y, 0.8, 0.4)
            pts = (
                [(self.bus_gnd_x, y), (self.bus_gnd_x, ly), (xs, ly)]
                if abs(y - ly) > 1e-9
                else [(self.bus_gnd_x, y), (xs, ly)]
            )
            self.track(NET_GND, "B.Cu", pts, w)

    EXPLICIT_PINS = (NET_GND, NET_5V, "LED_DIN", "LED_DOUT")
    EXPLICIT_REACH = 3.2  # past both escape via rows of the neighbouring pins

    def connector(self) -> None:
        lay, link = self.lay, self.q.link
        fp = load_footprint(link.footprint)
        cx, cy = lay.connector_xy
        rot = 270.0
        nets = dict(self.by_ref["J1"].pins)
        nets["MP"] = NET_GND
        self.footprint(fp, "J1", "FPC 16", cx, cy, rot, nets)
        self.res.placements["J1"] = (cx, cy, rot)
        self.pin_vias: dict[str, tuple[float, float]] = {}
        # the pins with a dedicated destination (ground bus, 5 V bus, LED
        # chain) run straight past the escape via rows of their neighbours
        # before their own standard via; every other pin gets a fanout
        # escape like any fine-pitch package (strip_parts)
        for i, net in enumerate(link.pinout):
            if net not in self.EXPLICIT_PINS:
                continue
            pad = fp.pad(str(i + 1))
            px, py = pad_abs_pos(cx, cy, rot, pad)
            vx, vy = px + self.EXPLICIT_REACH, py
            self.track(net, "F.Cu", [(px, py), (vx, vy)], 0.2)
            self.via(net, vx, vy)
            self.pin_vias.setdefault(net, (vx, vy))
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
            self.res.placements[led.ref] = (led.x, led.y, led.rot)
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

    # ------------------------------------------------------------ strip
    def strip_parts(self) -> None:
        lay = self.lay
        placements = strip_placements(self.cfg, lay, self.circuit)
        self.stubs: list[tuple[str, list, float, bool]] = []
        pending: list = []
        for ref, (x, y, rot) in placements.items():
            comp = self.by_ref[ref]
            fp = load_footprint(comp.part.footprint)
            self.footprint(fp, ref, comp.value, x, y, rot, dict(comp.pins))
            self.res.placements[ref] = (x, y, rot)
            pending.extend(escape_stubs(fp, x, y, rot, dict(comp.pins)))
        # the FPC pins without a dedicated fan-out escape like any package
        jx, jy, jrot = self.res.placements["J1"]
        j_nets = {
            n: net for n, net in self.by_ref["J1"].pins.items() if net not in self.EXPLICIT_PINS
        }
        pending.extend(escape_stubs(load_footprint(self.q.link.footprint), jx, jy, jrot, j_nets))
        kept = free_stubs(pending, self.res, self.clr)
        if len(kept) != len(pending):
            print(f"escape stubs: {len(kept)} of {len(pending)} drawn", file=sys.stderr)
        for net, _num, pts, runway, via in kept:
            self.track(net, "F.Cu", pts, STUB_WIDTH_MM)
            if via:
                end = runway_end(pts, runway)
                self.track(net, "F.Cu", [pts[1], end], STUB_WIDTH_MM)
                self.via(net, end[0], end[1], FANOUT_VIA_PAD_MM, FANOUT_VIA_DRILL_MM)
            self.stubs.append((net, pts, runway, via))

    def strip_buses(self) -> None:
        """Supply and logic buses on the inner layers, from the first cell
        to the last; the router ties them to the FPC pins and to the parts."""
        q = self.q.strip
        y0 = self.lay.cell_ys[0] - q.cell_pitch_mm / 2.0
        y1 = self.lay.cell_ys[-1] + q.cell_pitch_mm / 2.0
        for net, x, w in BUSES_IN1:
            self.track(net, "In1.Cu", [(x, y0), (x, y1)], w)
        net, x, w = BUS_3V3_IN2
        self.track(net, "In2.Cu", [(x, y0), (x, y1)], w)

    def strip_routing(self) -> None:
        """Every net with a pad in the strip, shortest span first, on all
        four layers; what the router cannot close is listed for pcbnew."""
        lay, rt = self.lay, self.rt
        W, H = lay.strip_w, lay.board_h
        mr = MultiRouter(
            COPPER_LAYERS, 0.0, 0.0, W, H, 0.1, self.clr, rt.led_via.pad_mm, h_weight=1.3
        )
        edge = rt.edge_clearance_mm
        for la in COPPER_LAYERS:
            mr.own[la][:, : int(edge / 0.1) + 3] = MultiRouter.MULTI
            mr.own[la][: int(edge / 0.1) + 3, :] = MultiRouter.MULTI
            mr.own[la][-(int(edge / 0.1) + 3) :, :] = MultiRouter.MULTI
            mr.own_via[la][:, : int(edge / 0.1) + 5] = MultiRouter.MULTI
        for t in self.res.tracks:
            for a, b in zip(t.pts, t.pts[1:], strict=False):
                if min(a[0], b[0]) < W + 1.0:
                    mr.segment(t.net, t.layer, a[0], a[1], b[0], b[1], t.width)
        for v in self.res.vias:
            if v.x < W + 1.0:
                mr.disc(v.net, COPPER_LAYERS, v.x, v.y, v.pad / 2.0)
        pad_cells: dict[str, list[tuple[str, list]]] = {}
        for p in self.res.pads:
            if p.x >= W + 1.0:
                continue
            layers = COPPER_LAYERS if p.layer == "*.Cu" else [p.layer]
            mr.rect(p.net, layers, p.x, p.y, p.w, p.h, p.rot)
            if p.net.startswith("__"):
                continue  # unconnected pad: painted, never routed
            for la in layers:
                pad_cells.setdefault(p.net, []).append((la, mr.cells_of_rect(p.x, p.y, p.w, p.h)))
        for hx, hy, hd in self.res.holes:
            if hx < W + 1.0:
                mr.keepout(hx, hy, hd / 2.0 + 0.5)
        claim_stubs(mr, self.stubs, exit_layer="In2.Cu")
        # existing copper of a net inside the strip counts as connected
        track_cells: dict[str, list[tuple[str, list]]] = {}
        for net, pts, runway, via in self.stubs:
            track_cells.setdefault(net, []).append(("F.Cu", stub_cells(mr, pts, runway)))
            if via:
                vc = mr.cell(*runway_end(pts, runway))
                for la in COPPER_LAYERS:
                    track_cells.setdefault(net, []).append((la, [vc]))
                track_cells.setdefault(net, []).append(("In2.Cu", exit_cells(mr, pts, runway)))
        for t in self.res.tracks:
            for a, b in zip(t.pts, t.pts[1:], strict=False):
                if min(a[0], b[0]) < W + 1.0:
                    cells = [
                        mr.cell(px, py)
                        for k in range(41)
                        for px, py in [
                            (a[0] + (b[0] - a[0]) * k / 40.0, a[1] + (b[1] - a[1]) * k / 40.0)
                        ]
                        if px < W + 0.5
                    ]
                    if cells:
                        track_cells.setdefault(t.net, []).append((t.layer, cells))

        def span(net):
            pts = [(p.x, p.y) for p in self.res.pads if p.net == net and p.x < W + 1.0]
            return (max(x for x, _ in pts) - min(x for x, _ in pts)) + (
                max(y for _, y in pts) - min(y for _, y in pts)
            )

        nets = [
            n
            for n in pad_cells
            if n not in ("", NET_5V, NET_GND, "LED_DIN", "LED_DOUT") and not n.startswith("LED_L")
        ]
        nets.sort(key=span)
        nets += [NET_GND]
        width_of = {n: 0.4 for n in ("VIN", "5VA", "3V3", "DRIVE_BUS", "PULSE_RAIL", NET_GND)}
        for net in nets:
            groups = list(pad_cells.get(net, []))
            if len(groups) + len(track_cells.get(net, [])) < 2:
                continue
            connected = list(track_cells.get(net, []))
            if not connected:
                connected = [groups.pop(0)]
            pending = groups
            width = width_of.get(net, 0.25)
            while pending:
                starts: dict[str, list] = {}
                for la, cells in connected:
                    starts.setdefault(la, []).extend(cells)
                goals: dict[str, list] = {}
                for la, cells in pending:
                    goals.setdefault(la, []).extend(cells)
                found = mr.route(net, starts, goals, max_nodes=2_000_000)
                if found is None:
                    nid = mr.nid(net)
                    usable = [
                        sum(
                            1
                            for la, cells in groups
                            for i, j in cells
                            if mr.own[la][j, i] in (mr.FREE, nid)
                        )
                        for groups in (connected, pending)
                    ]
                    self.res.open_nets.append(
                        f"{net}: {len(pending)} pad(s) left open "
                        f"(usable start cells {usable[0]}, goal cells {usable[1]})"
                    )
                    break
                tracks, vias = found
                clash = self._route_clash(net, tracks, vias, width, rt.led_via.pad_mm)
                if clash:
                    # the lattice is conservative but not exact: a route that
                    # would fail the real clearance is dropped, never drawn
                    self.res.open_nets.append(f"{net}: route rejected, {clash}")
                    break
                for la, pts in tracks:
                    self.track(net, la, pts, width)
                    for a, b in zip(pts, pts[1:], strict=False):
                        mr.segment(net, la, a[0], a[1], b[0], b[1], width)
                    connected.append((la, [mr.cell(x, y) for x, y in pts]))
                for x, y in vias:
                    self.via(net, x, y)
                    mr.disc(net, COPPER_LAYERS, x, y, rt.led_via.pad_mm / 2.0)
                reclaim_stubs(mr, self.stubs, exit_layer="In2.Cu")
                # pads reached by the new copper are connected now
                reached = set()
                for la, pts in tracks:
                    end_cells = {mr.cell(*pts[0]), mr.cell(*pts[-1])}
                    for k, (pla, cells) in enumerate(pending):
                        if pla == la and end_cells & set(cells):
                            reached.add(k)
                if not reached:
                    reached.add(0)
                for k in sorted(reached, reverse=True):
                    connected.append(pending.pop(k))
            else:
                self.res.routed_nets += 1

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
    def _route_clash(self, net: str, tracks, vias, width: float, via_pad: float) -> str | None:
        """Exact clearance of a candidate strip route against the copper drawn
        so far (strip region only); the first clash, or None."""

        W = self.lay.strip_w
        clr = self.clr - CHECK_SLOP_MM
        key = (len(self.res.tracks), len(self.res.vias))
        if getattr(self, "_clash_key", None) != key:
            by_layer: dict[str, list] = {}
            for t in self.res.tracks:
                if min(x for x, _ in t.pts) < W + 2.0:
                    by_layer.setdefault(t.layer, []).append(
                        (t.net, LineString(t.pts).buffer(t.width / 2.0))
                    )
            for v in self.res.vias:
                if v.x < W + 2.0:
                    for la in COPPER_LAYERS:
                        by_layer.setdefault(la, []).append(
                            (v.net, Point(v.x, v.y).buffer(v.pad / 2.0))
                        )
            for p in self.res.pads:
                if p.x < W + 2.0:
                    g = p.geometry()
                    for la in COPPER_LAYERS if p.layer == "*.Cu" else [p.layer]:
                        by_layer.setdefault(la, []).append((p.net, g))
            for hx, hy, hd in self.res.holes:
                if hx < W + 2.0:
                    for la in COPPER_LAYERS:
                        by_layer.setdefault(la, []).append(
                            ("__hole__", Point(hx, hy).buffer(hd / 2.0 + 0.35))
                        )
            self._clash_key = key
            self._clash_index = {
                la: (its, STRtree([g for _n, g in its])) for la, its in by_layer.items()
            }
        new = [(la, LineString(pts).buffer(width / 2.0)) for la, pts in tracks]
        for x, y in vias:
            for la in COPPER_LAYERS:
                new.append((la, Point(x, y).buffer(via_pad / 2.0)))
        for la, g in new:
            if la not in self._clash_index:
                continue
            its, tree = self._clash_index[la]
            for j in tree.query(g.buffer(clr)):
                other = its[int(j)]
                if other[0] == net:
                    continue
                d = g.distance(other[1])
                if d < clr:
                    from shapely.ops import nearest_points

                    c = nearest_points(g, other[1])[0]
                    return f"{la}: vs {other[0]} at ({c.x:.1f},{c.y:.1f}) gap {d:.3f}"
        return None

    def clearance_check(self) -> list[str]:
        """Exact same-layer clearance between items of different nets, vias
        and holes against everything; a copper item off the board."""
        lay = self.lay
        items = []  # (net, layer, geometry, kind)
        for t in self.res.tracks:
            items.append((t.net, t.layer, LineString(t.pts).buffer(t.width / 2.0), "track"))
        for v in self.res.vias:
            for layer in COPPER_LAYERS:
                items.append((v.net, layer, Point(v.x, v.y).buffer(v.pad / 2.0), "via"))
        for p in self.res.pads:
            layers = COPPER_LAYERS if p.layer == "*.Cu" else [p.layer]
            for layer in layers:
                items.append((p.net, layer, p.geometry(), "pad"))
        for hx, hy, hd in self.res.holes:
            for layer in COPPER_LAYERS:
                items.append(("__hole__", layer, Point(hx, hy).buffer(hd / 2.0 + 0.35), "hole"))
        errors = []
        by_layer: dict[str, list] = {}
        for it in items:
            by_layer.setdefault(it[1], []).append(it)
        clr = self.clr - CHECK_SLOP_MM
        for layer, its in by_layer.items():
            geoms = [g for _n, _l, g, _k in its]
            tree = STRtree(geoms)
            for i, (net, _l, g, kind) in enumerate(its):
                for j in tree.query(g.buffer(clr)):
                    j = int(j)
                    if j <= i or its[j][0] == net:
                        continue
                    if net.startswith("__") and its[j][0].startswith("__"):
                        continue  # a footprint's own unconnected pads around its holes
                    if kind == "pad" and its[j][3] == "pad" and _tie_pair(net, its[j][0]):
                        continue  # the two touching pads of a coil net tie
                    d = g.distance(geoms[j])
                    if d < clr:
                        from shapely.ops import nearest_points

                        c = nearest_points(g, geoms[j])[0]
                        errors.append(
                            f"{layer}: {net} vs {its[j][0]} at ({c.x:.1f},{c.y:.1f}) gap {d:.3f}"
                        )
        edge = self.rt.edge_clearance_mm - CHECK_SLOP_MM
        for net, _layer, g, _kind in items:
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
        self.strip_buses()
        self.build_rasters()
        self.chain()
        self.spurs()
        self.strip_parts()
        if self.with_strip:
            self.strip_routing()
        self.outline()
        self.res.clearance_errors = self.clearance_check()
        return self.res


def _tie_pair(a: str, b: str) -> bool:
    """C{k}_A against C{k}_B: the two nets of one coil, joined on purpose
    by the two touching pads of its net tie and nowhere else."""
    return (
        (a.endswith("_A") and b.endswith("_B") or a.endswith("_B") and b.endswith("_A"))
        and a[:-2] == b[:-2]
        and a.startswith("C")
    )


def _offset_junctions(paths, center, r_in: float, r_out: float):
    """Every layer junction moved radially off the turn bands: inward at
    the inner radius, outward at the outer one, joined to both spirals
    by a radial run of the same track. Returns the new paths (still
    sharing their junction points) and the via positions."""
    cx, cy = center
    pts = [np.asarray(p.points, dtype=float) for p in paths]
    vias = []
    for i in range(len(paths) - 1):
        px, py = pts[i][-1]
        r = math.hypot(px - cx, py - cy)
        inner = r < (r_in + r_out) / 2.0
        last = i == len(paths) - 2
        d = -(TIE_VIA_OFFSET_MM if last else VIA_OFFSET_MM) if inner else VIA_OFFSET_MM
        vx, vy = cx + (px - cx) * (r + d) / r, cy + (py - cy) * (r + d) / r
        pts[i] = np.vstack([pts[i], [[vx, vy]]])
        pts[i + 1] = np.vstack([[[vx, vy]], pts[i + 1]])
        vias.append((float(vx), float(vy)))
    return [dataclasses.replace(p, points=q) for p, q in zip(paths, pts, strict=True)], vias


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


def build_quadrant(cfg: BoardConfig, strip: bool = True) -> BuildResult:
    """`strip=False` places the front end but skips its routing (seconds
    instead of minutes): what the geometry tests need."""
    return Builder(cfg, strip=strip).build()


def design_rules(cfg: BoardConfig, result: BuildResult) -> DesignRules:
    """What the DRC must accept: every track width and via size the build
    drew, the fanout vias of the fine-pitch packages included."""
    rt = cfg.plateau.quadrant.routing
    coil_via_pad = 2.0 * cfg.sense_coil.via_drill_mm
    widths = sorted({round(t.width, 3) for t in result.tracks})
    vias = sorted({(round(v.pad, 3), round(v.drill, 3)) for v in result.vias}) or [
        (coil_via_pad, cfg.sense_coil.via_drill_mm)
    ]
    return DesignRules(
        clearance_mm=rt.track_clearance_mm,
        track_width_mm=rt.route_track_mm,
        via_diameter_mm=rt.led_via.pad_mm,
        via_drill_mm=rt.led_via.drill_mm,
        min_track_width_mm=min(widths),
        min_via_diameter_mm=min(pad for pad, _drill in vias),
        min_hole_mm=min(drill for _pad, drill in vias),
        edge_clearance_mm=rt.edge_clearance_mm,
        track_widths_mm=tuple(widths),
        via_sizes_mm=tuple(vias),
    )


def summary(result: BuildResult) -> str:
    n_tracks = sum(len(t.pts) - 1 for t in result.tracks)
    return (
        f"{len(result.coils)} coils, {len(result.leds)} LEDs, {n_tracks} segments, "
        f"{len(result.vias)} vias, open routes {len(result.open_routes)}, "
        f"clearance errors {len(result.clearance_errors)}"
    )


_ = np  # numpy is used by the router; keep the import explicit for type hints
