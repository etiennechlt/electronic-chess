"""Placed and routed PCB of the mockup analog board.

Two layers. F.Cu carries most routing; B.Cu is the ground plane,
computed as overlapping scanline strips (kicad-cli 7 does not refill
zones at export), locally interrupted by the few B.Cu escape segments
the router places, each kept short by a strong layer penalty.

Routing is a grid A* on a 0.125 mm lattice, two layers. Legality is
distance-based: euclidean distance transforms of foreign copper
(pads, and routed centerlines by width class) give the exact margin a
centerline must keep, so fine-pitch escapes (TSSOP 0.65, QFN 0.5)
stay routable without ever overlapping. Near its two endpoints a
connection may dip below the design clearance but never below the
hard overlap guard; the final authority is the exact shapely DRC run
afterwards at the fab minimum, together with a per-net connectivity
check and a plane integrity check.

Floor plan (origin top-left, y down, 100 x 56 mm): MCU header and
test points on the north edge, power down the west side with the Pi
header and UART isolator below, drive rail in the south-west corner,
amplifier chain flowing west to east across the middle, four coil
cells along the south band with the mux between cells 2 and 3, and
the J2 coil-board socket on the south edge.
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field

import numpy as np
from coilgen.kicad import Board
from scipy import ndimage
from shapely.geometry import LineString, Point, box
from shapely.ops import unary_union

from chessboard_calc.config import BoardConfig

from .circuit import Circuit
from .fplib import load_footprint, pad_abs_pos, place_footprint

BOARD_W, BOARD_H = 100.0, 62.0
GRID = 0.125
CLR = 0.15          # routing design clearance
FAB_CLR = 0.127     # exact DRC gate
SLOP = 0.09         # rasterization slack (half cell diagonal)
W_SIG = 0.4
W_PWR = 0.8
W_FINE = 0.25       # entries into fine-pitch pads
VIA_D, VIA_DRILL = 0.6, 0.3
EDGE_KEEPOUT = 0.4

POWER_NETS = {"VIN", "VIN_JACK", "5V_BUCK", "5V_BUCK_FILT", "5V_LDO", "5VA",
              "SW", "PULSE_RAIL", "DRIVE_BUS"}


def net_width(net: str) -> float:
    return W_PWR if net in POWER_NETS else W_SIG


@dataclass
class PcbResult:
    board: Board
    placements: dict[str, tuple[float, float, float]]
    pad_pos: dict[tuple[str, str], tuple[float, float]]
    tracks: list = field(default_factory=list)   # (net, width, pts, layer)
    vias: list = field(default_factory=list)     # (net, x, y)
    plane_polys: list = field(default_factory=list)
    finish_log: list = field(default_factory=list)
    drc_errors: list = field(default_factory=list)
    open_nets: list = field(default_factory=list)
    plane_islands: int = 0


# ----------------------------------------------------------------------
# Placement. Cells straddle the mux; the router connects everything.
# ----------------------------------------------------------------------
CELL_X = {1: 21.0, 2: 33.5, 3: 55.0, 4: 67.5}
CELL_Y = 38.0

PLACEMENTS: dict[str, tuple[float, float, float]] = {
    # North edge: MCU header and test points.
    "J4": (64.0, 6.0, 90.0),
    "TP1": (59.5, 3.0, 0.0), "TP2": (59.5, 7.5, 0.0), "TP3": (55.5, 3.0, 0.0),
    "TP4": (55.5, 7.5, 0.0), "TP5": (51.5, 3.0, 0.0), "TP6": (51.5, 7.5, 0.0),
    # Power entry, west.
    "J1": (5.0, 9.5, 0.0),
    "D1": (15.5, 4.5, 180.0),
    "D2": (16.0, 10.5, 90.0),
    "C1": (15.5, 15.0, 0.0),
    "C2": (21.0, 4.5, 90.0),
    "C3": (23.8, 4.5, 90.0),
    "U1": (22.5, 11.5, 0.0),
    "R1": (17.0, 20.0, 90.0),
    "C4": (27.2, 15.0, 90.0),
    "L1": (22.5, 19.5, 0.0),
    "C5": (27.5, 20.0, 90.0),
    "C6": (30.3, 20.0, 90.0),
    "R3": (27.2, 9.0, 90.0),
    "R4": (30.0, 9.0, 90.0),
    "R2": (26.2, 4.5, 90.0),
    "JP3": (33.5, 4.0, 90.0),
    "FB1": (34.0, 10.0, 90.0),
    "C7": (36.8, 10.0, 90.0),
    "C8": (39.6, 10.0, 90.0),
    "U2": (35.5, 17.0, 180.0),
    "C9": (40.8, 18.5, 90.0),
    "C10": (43.6, 18.5, 90.0),
    "C11": (30.5, 15.0, 90.0),
    "JP1": (44.0, 8.5, 90.0),
    "C12": (46.4, 18.5, 90.0),
    "R5": (49.2, 18.5, 90.0),
    "R6": (52.0, 18.5, 90.0),
    "C13": (54.8, 18.5, 90.0),
    # Pi header and UART isolator.
    "J5": (4.5, 25.0, 0.0),
    "U7": (13.5, 27.5, 270.0),
    "C25": (17.8, 23.0, 90.0),
    "C26": (17.8, 31.5, 90.0),
    "R66": (9.0, 35.5, 0.0),
    "R67": (13.5, 35.5, 0.0),
    # Drive rail, south-west corner.
    "Q2": (5.5, 41.0, 0.0),
    "R8": (9.5, 44.5, 0.0),
    "R7": (9.5, 41.0, 90.0),
    "Q1": (13.5, 41.0, 0.0),
    "R9": (13.0, 47.5, 0.0),
    "R10": (11.5, 51.5, 0.0),
    # Chain band, west to east.
    "C14": (47.0, 32.6, 90.0),
    "C15": (50.0, 32.6, 90.0),
    "R12": (53.0, 32.6, 90.0),
    "R13": (44.2, 32.6, 90.0),
    "U4": (54.0, 26.0, 0.0),
    "R14": (54.0, 22.2, 0.0),
    "C16": (59.6, 22.5, 90.0),
    "C17": (62.5, 23.5, 0.0),
    "C18": (67.0, 23.5, 0.0),
    "R15": (64.8, 26.0, 0.0),
    "R16": (70.0, 26.5, 90.0),
    "R17": (62.5, 28.5, 0.0),
    "R18": (59.8, 30.0, 90.0),
    "U5": (66.5, 31.5, 180.0),
    "R19": (75.0, 23.5, 0.0),
    "R20": (79.5, 23.5, 0.0),
    "C19": (77.3, 26.0, 0.0),
    "C20": (82.5, 26.5, 90.0),
    "R61": (75.0, 28.5, 0.0),
    "R62": (72.5, 31.5, 90.0),
    "C21": (79.5, 31.5, 90.0),
    "U6": (89.0, 28.5, 0.0),
    "R63": (84.6, 23.2, 90.0),
    "R64": (89.0, 23.2, 0.0),
    "C22": (94.0, 28.5, 90.0),
    "C23": (56.5, 32.6, 90.0),
    "R65": (95.8, 17.5, 90.0),
    "C24": (95.8, 12.5, 90.0),
    "D3": (92.0, 12.5, 90.0),
    # Mux between the cell pairs.
    "U3": (48.5, 42.0, 90.0),
    "R11": (38.0, 31.5, 90.0),
    # South joint socket: pin 1 x is computed from the yaml joint so it
    # always matches the coil board (see full_placements).
    "J2": (0.0, 56.4, 90.0),
    # WS2812 level shifter next to the MCU header: LED_DIN stays a
    # short hop, the buffered 5V line runs down the free east edge.
    "U8": (80.0, 11.0, 0.0),
    "R68": (84.0, 11.0, 0.0),
    "C27": (76.5, 11.0, 90.0),
    # Mechanics.
    "H1": (3.6, 3.6, 0.0),
    "H2": (3.6, 52.0, 0.0),
    "H3": (96.4, 3.6, 0.0),
    "H4": (96.4, 52.0, 0.0),
}

CELL_PARTS: dict[str, tuple[float, float, float]] = {
    "Rb+3": (1.2, 0.4, 90.0),    # clamp A -> MkA node at top
    "Rb+4": (3.6, 0.4, 90.0),    # clamp B
    "Rb+1": (6.0, 0.4, 90.0),    # bleed A (mux-side node)
    "Rb+2": (8.4, 0.4, 90.0),    # bleed B
    "Dd+10": (2.2, 3.4, 180.0),  # BAV99 A, common west
    "Dd+20": (8.0, 3.4, 0.0),    # BAV99 B, common east
    "Dd+30": (1.4, 6.4, 90.0),   # bus diode, K south
    "Qq+10": (8.6, 6.6, 0.0),    # drive FET
    "Rb+5": (11.0, 6.6, 90.0),   # drive gate pulldown
    "Dd+40": (5.6, 9.6, 0.0),    # flyback SS34, A pad east near the FET drain
    "Qq+20": (1.6, 12.6, 180.0),  # damp FET, source on the A node
    "Rb+6": (5.4, 12.8, 0.0),    # damp resistor 0805
    "Rb+7": (8.8, 12.6, 90.0),   # damp gate pullup
}


def cell_ref(kind: str, k: int) -> str:
    base = 10 + 10 * k
    if kind.startswith("Rb+"):
        return f"R{base + int(kind[3:])}"
    if kind.startswith("Dd+"):
        return f"D{k + int(kind[3:])}"
    return f"Q{k + int(kind[3:])}"


def full_placements(cfg: BoardConfig) -> dict[str, tuple[float, float, float]]:
    placements = dict(PLACEMENTS)
    joint = cfg.mockup.coil_board.joint
    x0 = BOARD_W / 2.0 - (joint.pins - 1) * joint.pitch_mm / 2.0
    placements["J2"] = (x0, 56.4, 90.0)
    for k, cx in CELL_X.items():
        for kind, (dx, dy, rot) in CELL_PARTS.items():
            placements[cell_ref(kind, k)] = (cx + dx, CELL_Y + dy, rot)
    return placements


# ----------------------------------------------------------------------
# Pad geometry.
# ----------------------------------------------------------------------
@dataclass(frozen=True)
class PadInst:
    ref: str
    number: str
    net: str | None
    x: float
    y: float
    w: float           # bounding box after rotation
    h: float
    tht: bool

    @property
    def fine(self) -> bool:
        return min(self.w, self.h) <= 0.45 and not self.tht


def _pad_instances(circuit: Circuit, placements) -> list[PadInst]:
    out = []
    for comp in circuit.components:
        x, y, rot = placements[comp.ref]
        fp = load_footprint(comp.part.footprint)
        for pad in fp.pads:
            if not any(la.endswith(".Cu") or la == "*.Cu" for la in pad.layers):
                continue
            px, py = pad_abs_pos(x, y, rot, pad)
            total = pad.rot + rot
            w, h = pad.size
            if abs(math.sin(math.radians(total))) > 0.5:
                w, h = h, w
            net = comp.pins.get(pad.number)
            out.append(PadInst(
                ref=comp.ref, number=pad.number, net=net, x=px, y=py,
                w=w, h=h, tht=pad.kind != "smd",
            ))
    return out


# ----------------------------------------------------------------------
# Grid A* router with distance-transform legality.
# ----------------------------------------------------------------------
class Router:
    def __init__(self, pads: list[PadInst]):
        self.nx = int(round(BOARD_W / GRID)) + 1
        self.ny = int(round(BOARD_H / GRID)) + 1
        self.pads = pads
        self.net_ids: dict[str, int] = {}
        # Pad ownership per layer (-1 free, -2 no-net keepout, else net id).
        self.pad_grid = [np.full((self.ny, self.nx), -1, dtype=np.int32)
                         for _ in range(2)]
        self.smd_top = np.zeros((self.ny, self.nx), dtype=bool)
        # Routed copper: true-extent mask plus first-come ownership.
        self.track_grid = [np.full((self.ny, self.nx), -1, dtype=np.int32)
                           for _ in range(2)]
        self.copper = [np.zeros((self.ny, self.nx), dtype=bool)
                       for _ in range(2)]
        self.tracks: list[tuple[str, float, list[tuple[float, float]], str]] = []
        self.vias: list[tuple[str, float, float]] = []
        self.failed: list[str] = []
        self.failed_pads: list = []

        for pad in pads:
            nid = self._nid(pad.net) if pad.net else -2
            i0, i1, j0, j1 = self._cells_inside(
                pad.x - pad.w / 2, pad.y - pad.h / 2,
                pad.x + pad.w / 2, pad.y + pad.h / 2)
            for la in ((0, 1) if pad.tht else (0,)):
                zone = self.pad_grid[la][i0:i1 + 1, j0:j1 + 1]
                clash = (zone != -1) & (zone != nid)
                self.pad_grid[la][i0:i1 + 1, j0:j1 + 1] = np.where(
                    clash, np.int32(-2), np.where(zone == -1, nid, zone))
            if not pad.tht:
                self.smd_top[i0:i1 + 1, j0:j1 + 1] = True

    def _nid(self, net: str) -> int:
        if net not in self.net_ids:
            self.net_ids[net] = len(self.net_ids)
        return self.net_ids[net]

    def _cells_inside(self, x0, y0, x1, y1):
        """Cells intersecting the rectangle (over-approximation, so
        distance-to-marks under-estimates distance-to-copper and the
        legality thresholds need no rasterization slack)."""
        i0 = max(0, int(math.floor(y0 / GRID + 0.5)) - 0)
        i0 = max(0, int(math.floor(y0 / GRID)))
        i1 = min(self.ny - 1, int(math.ceil(y1 / GRID)))
        j0 = max(0, int(math.floor(x0 / GRID)))
        j1 = min(self.nx - 1, int(math.ceil(x1 / GRID)))
        return i0, i1, j0, j1

    def _legal_masks(self, nid: int, width: float):
        """(soft_free, hard_free, via_ok) for a centerline of `width`.

        Pads are rasterized center-inside (under-covering by up to SLOP)
        and routed copper is marked at its true extent, so a single
        distance transform per kind gives sound clearances.
        """
        soft, hard = [], []
        via_ok = None
        big = np.float32(1e6)
        for la in range(2):
            foreign_pad = (self.pad_grid[la] != -1) & (self.pad_grid[la] != nid)
            d_pad = ndimage.distance_transform_edt(~foreign_pad) * GRID \
                if foreign_pad.any() else np.full((self.ny, self.nx), big)
            foreign_cu = self.copper[la] & (self.track_grid[la] != nid)
            d_cu = ndimage.distance_transform_edt(~foreign_cu) * GRID \
                if foreign_cu.any() else np.full((self.ny, self.nx), big)

            def masks(margin, half, dp=d_pad, dc=d_cu):
                # Marks over-approximate the copper, no slack needed.
                return (dp >= half + margin) & (dc >= half + margin)

            s = masks(CLR, width / 2.0)
            h = masks(FAB_CLR + 0.02, width / 2.0)
            v = masks(CLR, VIA_D / 2.0)
            edge = int(math.ceil((EDGE_KEEPOUT + width / 2.0) / GRID))
            for m in (s, h, v):
                m[:edge, :] = False
                m[-edge:, :] = False
                m[:, :edge] = False
                m[:, -edge:] = False
            soft.append(s)
            hard.append(h)
            via_ok = v if via_ok is None else (via_ok & v)
        return soft, hard, via_ok

    def _pad_cells(self, pad: PadInst):
        i0, i1, j0, j1 = self._cells_inside(
            pad.x - pad.w / 2, pad.y - pad.h / 2,
            pad.x + pad.w / 2, pad.y + pad.h / 2)
        layers = (0, 1) if pad.tht else (0,)
        cells = [(la, i, j) for la in layers
                 for i in range(i0, i1 + 1) for j in range(j0, j1 + 1)]
        if not cells:
            ci, cj = int(round(pad.y / GRID)), int(round(pad.x / GRID))
            cells = [(la, ci, cj) for la in layers]
        return cells

    def _mark_path(self, nid: int, width: float, cells):
        r = int(math.ceil(width / 2.0 / GRID))
        rv = int(math.ceil(VIA_D / 2.0 / GRID))
        prev = None
        for la, i, j in cells:
            i0, i1 = max(0, i - r), min(self.ny - 1, i + r)
            j0, j1 = max(0, j - r), min(self.nx - 1, j + r)
            self.copper[la][i0:i1 + 1, j0:j1 + 1] = True
            zone = self.track_grid[la][i0:i1 + 1, j0:j1 + 1]
            self.track_grid[la][i0:i1 + 1, j0:j1 + 1] = np.where(
                zone == -1, nid, zone)
            if prev is not None and prev[0] != la and prev[1:] == (i, j):
                vi0, vi1 = max(0, i - rv), min(self.ny - 1, i + rv)
                vj0, vj1 = max(0, j - rv), min(self.nx - 1, j + rv)
                for vla in range(2):
                    self.copper[vla][vi0:vi1 + 1, vj0:vj1 + 1] = True
                    vz = self.track_grid[vla][vi0:vi1 + 1, vj0:vj1 + 1]
                    self.track_grid[vla][vi0:vi1 + 1, vj0:vj1 + 1] = np.where(
                        vz == -1, nid, vz)
            prev = (la, i, j)

    def _emit(self, net: str, width: float, path,
              snap_first=None, snap_last=None):
        segs = []
        cur_layer = path[0][0]
        cur = [(path[0][2] * GRID, path[0][1] * GRID)]
        for la, i, j in path[1:]:
            pt = (j * GRID, i * GRID)
            if la != cur_layer:
                self.vias.append((net, cur[-1][0], cur[-1][1]))
                segs.append((cur_layer, cur))
                cur = [cur[-1]]
                cur_layer = la
            cur.append(pt)
        segs.append((cur_layer, cur))
        if snap_first is not None and len(segs[0][1]) >= 2:
            segs[0][1][0] = snap_first
        if snap_last is not None and len(segs[-1][1]) >= 2:
            segs[-1][1][-1] = snap_last
        for la, pts in segs:
            simple = [pts[0]]
            for prev_pt, a, b in zip(pts, pts[1:], pts[2:], strict=False):
                _ = prev_pt
                last = simple[-1]
                if (abs(a[0] - last[0]) < 1e-9 and abs(a[0] - b[0]) < 1e-9) or \
                        (abs(a[1] - last[1]) < 1e-9 and abs(a[1] - b[1]) < 1e-9):
                    continue
                simple.append(a)
            if pts[-1] != simple[-1]:
                simple.append(pts[-1])
            simple = [p for k, p in enumerate(simple)
                      if k == 0 or p != simple[k - 1]]
            if len(simple) >= 2:
                self.tracks.append(
                    (net, width, simple, "F.Cu" if la == 0 else "B.Cu"))

    def _pad_at_cell(self, net: str, la: int, i: int, j: int):
        x, y = j * GRID, i * GRID
        for q in self.pads:
            if q.net != net or (la == 1 and not q.tht):
                continue
            if abs(x - q.x) <= q.w / 2 + GRID + 1e-9 \
                    and abs(y - q.y) <= q.h / 2 + GRID + 1e-9:
                return q
        return None

    def emit_routed(self, net: str, width: float, path) -> None:
        """Emit a found cell path, collapsing the run of cells inside the
        start and end pads onto the pad's long axis.

        Pad cells are rasterized one cell beyond the copper, so a path
        entering the grid box of a small pad can otherwise sweep its
        half-width into the neighbouring pad (0.5 mm pitch parts)."""
        def trim(p):
            la0, i0, j0 = p[0]
            pad = self._pad_at_cell(net, la0, i0, j0)
            if pad is None:
                return p, None
            k = 0
            while (k + 1 < len(p) and p[k + 1][0] == la0
                   and self._pad_at_cell(net, *p[k + 1]) is pad):
                k += 1
            p = p[k:]
            x, y = p[0][2] * GRID, p[0][1] * GRID
            if pad.w >= pad.h:
                span = max(0.0, (pad.w - width) / 2.0)
                sx = min(max(x, pad.x - span), pad.x + span)
                sy = pad.y
            else:
                span = max(0.0, (pad.h - width) / 2.0)
                sx = pad.x
                sy = min(max(y, pad.y - span), pad.y + span)
            return p, (sx, sy)

        path, first_xy = trim(list(path))
        rev, last_xy = trim(path[::-1])
        path = rev[::-1]
        if len(path) >= 2:
            self._emit(net, width, path, snap_first=first_xy,
                       snap_last=last_xy)

    def _astar(self, nid, width, start_cells, target, endpoint_xy,
               relax_all=False, no_relax=False, max_pops=500_000):
        soft, hard, via_ok = self._legal_masks(nid, width)
        # Own pads are free passage; own tracks are NOT: riding the edge
        # of an earlier same-net mark would push this half-width into
        # territory the earlier legality never cleared.
        own = np.zeros((2, self.ny, self.nx), dtype=bool)
        for la in range(2):
            own[la] = self.pad_grid[la] == nid
        relax = np.zeros((2, self.ny, self.nx), dtype=bool)
        if no_relax:
            pass
        elif relax_all:
            relax[:, :, :] = True
        else:
            ex, ey = endpoint_xy
            i0, i1, j0, j1 = self._cells_inside(ex - 1.6, ey - 1.6,
                                                ex + 1.6, ey + 1.6)
            relax[:, i0:i1 + 1, j0:j1 + 1] = True

        tgt_idx = np.argwhere(target.any(axis=0))
        if len(tgt_idx) == 0:
            return None
        tminy, tminx = tgt_idx.min(axis=0)
        tmaxy, tmaxx = tgt_idx.max(axis=0)

        def hcost(i, j):
            dy = 0 if tminy <= i <= tmaxy else min(abs(i - tminy), abs(i - tmaxy))
            dx = 0 if tminx <= j <= tmaxx else min(abs(j - tminx), abs(j - tmaxx))
            return (dx + dy) * 1.0

        def passable(la, i, j):
            if own[la, i, j]:
                return True
            if soft[la][i, j]:
                return True
            return bool(relax[la, i, j] and hard[la][i, j])

        dist = np.full((2, self.ny, self.nx), np.float32(np.inf), dtype=np.float32)
        prev: dict[tuple[int, int, int], tuple[int, int, int]] = {}
        heap = []
        for la, i, j in start_cells:
            dist[la, i, j] = 0.0
            heapq.heappush(heap, (hcost(i, j), 0.0, (la, i, j)))
        found = None
        pops = 0
        while heap:
            pops += 1
            if pops > max_pops:
                break
            _f, d, (la, i, j) = heapq.heappop(heap)
            if d > dist[la, i, j]:
                continue
            if target[la, i, j]:
                found = (la, i, j)
                break
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ni, nj = i + di, j + dj
                if not (0 <= ni < self.ny and 0 <= nj < self.nx):
                    continue
                if not passable(la, ni, nj):
                    continue
                nd = d + (1.0 if la == 0 else 1.6)
                if nd < dist[la, ni, nj]:
                    dist[la, ni, nj] = nd
                    prev[(la, ni, nj)] = (la, i, j)
                    heapq.heappush(heap, (nd + hcost(ni, nj), nd, (la, ni, nj)))
            ol = 1 - la
            if passable(ol, i, j) and not self.smd_top[i, j] \
                    and via_ok[i, j] \
                    and self.pad_grid[0][i, j] in (-1, nid) \
                    and self.pad_grid[1][i, j] in (-1, nid):
                nd = d + 28.0
                if nd < dist[ol, i, j]:
                    dist[ol, i, j] = nd
                    prev[(ol, i, j)] = (la, i, j)
                    heapq.heappush(heap, (nd + hcost(i, j), nd, (ol, i, j)))
        if found is None:
            return None
        path = [found]
        key = found
        starts = set(start_cells)
        while key not in starts:
            key = prev[key]
            path.append(key)
        path.reverse()
        return path

    def seed_track(self, net: str, pts, width: float, layer: str = "F.Cu") -> None:
        """Pre-place a structural track (a rail) before routing."""
        nid = self._nid(net)
        cells = []
        la = 0 if layer == "F.Cu" else 1
        for (x0, y0), (x1, y1) in zip(pts, pts[1:], strict=False):
            n = max(2, int(math.hypot(x1 - x0, y1 - y0) / GRID) + 1)
            for k in range(n):
                t = k / (n - 1)
                x = x0 + (x1 - x0) * t
                y = y0 + (y1 - y0) * t
                cells.append((la, int(round(y / GRID)), int(round(x / GRID))))
        self._mark_path(nid, width, cells)
        self.tracks.append((net, width, [tuple(p) for p in pts], layer))

    def seed_via(self, net: str, x: float, y: float) -> None:
        nid = self._nid(net)
        i, j = int(round(y / GRID)), int(round(x / GRID))
        rv = int(math.ceil(VIA_D / 2.0 / GRID))
        for la in range(2):
            self.copper[la][max(0, i - rv):i + rv + 1,
                            max(0, j - rv):j + rv + 1] = True
            z = self.track_grid[la][max(0, i - rv):i + rv + 1,
                                    max(0, j - rv):j + rv + 1]
            self.track_grid[la][max(0, i - rv):i + rv + 1,
                                max(0, j - rv):j + rv + 1] = np.where(
                z == -1, nid, z)
        self.vias.append((net, x, y))

    def route_net(self, net: str) -> None:
        """Connect every pad to the component grown from the seed pad."""
        nid = self._nid(net)
        pads = sorted((p for p in self.pads if p.net == net),
                      key=lambda p: (p.x, p.y))
        if len(pads) < 2:
            return
        connected = np.zeros((2, self.ny, self.nx), dtype=bool)
        for la in range(2):
            connected[la] = self.track_grid[la] == nid
        for la, i, j in self._pad_cells(pads[0]):
            connected[la, i, j] = True
        for pad in pads[1:]:
            cells = self._pad_cells(pad)
            width = W_FINE if pad.fine else net_width(net)
            target = connected.copy()
            for la, i, j in cells:
                target[la, i, j] = False
            if target.any() and self._touches_net(net, pad):
                # Already in real contact with this net's copper (a seed
                # under the pad, say): nothing to route, and no failure.
                for la, i, j in cells:
                    connected[la, i, j] = True
                continue
            if target.any():
                path = self._astar(nid, width, cells, target, (pad.x, pad.y))
                if path is None and width > W_FINE:
                    width = W_FINE
                    path = self._astar(nid, width, cells, target, (pad.x, pad.y))
                if path is None:
                    self.failed.append(f"{net}:{pad.ref}.{pad.number}")
                    self.failed_pads.append((net, pad))
                    continue
                self._mark_path(nid, width, path)
                if len(path) >= 2:
                    self.emit_routed(net, width, path)
                for la, i, j in path:
                    connected[la, i, j] = True
            for la, i, j in cells:
                connected[la, i, j] = True

    def cleanup_pass(self) -> None:
        """Last resort for leftover connections: allow the fab-minimum
        clearance along the whole path (still DRC-clean, logged)."""
        leftovers = self.failed_pads
        self.failed_pads = []
        still = []
        for net, pad in leftovers:
            nid = self._nid(net)
            cells = self._pad_cells(pad)
            target = self._net_target_mask(nid)
            for la, i, j in cells:
                target[la, i, j] = False
            if not target.any():
                continue
            path = self._astar(nid, W_FINE, cells, target, (pad.x, pad.y),
                               relax_all=True)
            if path is None:
                still.append(f"{net}:{pad.ref}.{pad.number}")
                continue
            self._mark_path(nid, W_FINE, path)
            if len(path) >= 2:
                self.emit_routed(net, W_FINE, path)
        self.failed = [f for f in self.failed if not self._is_conn_fail(f)] + still

    @staticmethod
    def _is_conn_fail(entry: str) -> bool:
        return ":" in entry and not entry.startswith("GND-via")

    def _touches_net(self, net: str, pad) -> bool:
        pb = box(pad.x - pad.w / 2, pad.y - pad.h / 2,
                 pad.x + pad.w / 2, pad.y + pad.h / 2)
        for tnet, w, pts, tlayer in self.tracks:
            if tnet != net or (tlayer == "B.Cu" and not pad.tht):
                continue
            if LineString(pts).buffer(w / 2.0).distance(pb) <= 1e-9:
                return True
        for vnet, x, y in self.vias:
            if vnet == net and Point(x, y).buffer(VIA_D / 2.0).distance(pb) <= 1e-9:
                return True
        return False

    def _net_target_mask(self, nid):
        t = np.zeros((2, self.ny, self.nx), dtype=bool)
        for la in range(2):
            t[la] = (self.pad_grid[la] == nid) | (self.track_grid[la] == nid)
        return t

    def gnd_to_plane(self) -> None:
        """Every SMD GND pad reaches ground copper or the B.Cu plane.

        The target is any existing GND copper (a plated pad, an earlier
        stub) or a legal virgin spot on the plane layer, so nearby GND
        pads chain onto shared vias instead of each drilling its own.
        """
        nid = self._nid("GND")
        gnd_pads = sorted(
            (p for p in self.pads if p.net == "GND" and not p.tht),
            key=lambda p: (p.x, p.y))
        for pad in gnd_pads:
            w_stub = W_FINE if pad.fine else W_SIG
            start_cells = [c for c in self._pad_cells(pad) if c[0] == 0]
            plane_free, _hard, _via = self._legal_masks(nid, w_stub)
            target = np.zeros((2, self.ny, self.nx), dtype=bool)
            target[1] = plane_free[1] & (self.pad_grid[1] == -1) \
                & (self.track_grid[1] == -1)
            for la in range(2):
                target[la] |= (self.pad_grid[la] == nid) | (self.track_grid[la] == nid)
            for la, i, j in start_cells:
                target[la, i, j] = False
            path = self._astar(nid, w_stub, start_cells, target,
                               (pad.x, pad.y), no_relax=True)
            if path is None:
                self.failed.append(f"GND-via:{pad.ref}.{pad.number}")
                continue
            self._mark_path(nid, w_stub, path)
            if len(path) >= 2:
                self.emit_routed("GND", w_stub, path)
        # THT GND pads connect through the plane itself.




def _hand_seeds(r: Router, pads) -> None:
    """Structural routes for the links the maze router cannot close.

    Waypoints were tuned against the real pad geometry; the guard below
    re-checks each path against every foreign pad at build time so a
    placement change fails loudly instead of overlapping silently.
    """
    from shapely.geometry import LineString, Point
    from shapely.geometry import box as _box

    pp = {(q.ref, q.number): (q.x, q.y) for q in pads}

    def P(ref, num):
        return pp[(ref, num)]

    laid: list[tuple[str, str, object]] = []
    for pnet, pw, ppts, playr in r.tracks:
        laid.append((pnet, playr, LineString(ppts).buffer(pw / 2.0)))
    for pnet, px, py in r.vias:
        disc = Point(px, py).buffer(VIA_D / 2.0)
        laid.append((pnet, "F.Cu", disc))
        laid.append((pnet, "B.Cu", disc))

    def T(net, pts, layer="F.Cu", w=W_FINE):
        line = LineString(pts).buffer(w / 2.0)
        if layer == "F.Cu":
            for q in pads:
                if q.net == net:
                    continue
                g = _box(q.x - q.w / 2, q.y - q.h / 2,
                         q.x + q.w / 2, q.y + q.h / 2)
                if line.distance(g) < FAB_CLR:
                    raise ValueError(
                        f"seed {net} clashes {q.ref}.{q.number} ({q.net})")
        for onet, olayer, og in laid:
            if onet != net and olayer == layer and line.distance(og) < FAB_CLR:
                raise ValueError(f"seed {net} crosses seed {onet} on {layer}")
        laid.append((net, layer, line))
        r.seed_track(net, pts, w, layer=layer)

    def V(net, x, y):
        disc = Point(x, y).buffer(VIA_D / 2.0)
        for q in pads:
            if q.net == net:
                continue
            g = _box(q.x - q.w / 2, q.y - q.h / 2,
                     q.x + q.w / 2, q.y + q.h / 2)
            if disc.distance(g) < FAB_CLR:
                raise ValueError(
                    f"seed via {net} clashes {q.ref}.{q.number} ({q.net})")
        for onet, _olayer, og in laid:
            if onet != net and disc.distance(og) < FAB_CLR:
                raise ValueError(f"seed via {net} crosses seed {onet}")
        laid.append((net, "F.Cu", disc))
        laid.append((net, "B.Cu", disc))
        r.seed_via(net, x, y)

    # BUCK_EN: axis exit north of U1 pin 13, around the input capacitors,
    # down the far west lane to R1.
    x13, y13 = P("U1", "13")
    xr1, yr1 = P("R1", "1")
    T("BUCK_EN", [(x13, y13), (x13, 8.8), (22.4, 8.2), (22.4, 2.1),
                  (10.7, 2.1), (10.7, yr1), (xr1, yr1)])

    # VIN: LDO input joins the C11 vin pad below the output capacitors.
    xu2, yu2 = P("U2", "1")
    xc11, yc11 = P("C11", "1")
    T("VIN", [(xu2, yu2), (xu2, 20.1), (28.9, 20.1), (28.9, 16.9),
              (xc11, 16.9), (xc11, yc11)], w=W_SIG)

    # M2_A: cell 2 clamp top to mux X1 over the cell-top corridor.
    xa, ya = P("R33", "2")
    xm, ym = P("U3", "14")
    T("M2_A", [(xa, ya), (xa, 36.4), (xm, 36.4), (xm, ym)])

    # M4_B: cell 4 clamp top, west below the VREF rail, around the mux
    # to its south row.
    xb, yb = P("R54", "2")
    xy3, yy3 = P("U3", "4")
    T("M4_B", [(xb, yb), (xb, 36.05), (61.5, 36.05)])
    V("M4_B", 61.5, 36.05)
    T("M4_B", [(61.5, 36.05), (61.5, 46.4), (xy3, 46.4)], layer="B.Cu")
    V("M4_B", xy3, 46.4)
    T("M4_B", [(xy3, 46.4), (xy3, yy3)])

    # LP_OUT spine: through the channel between the U5 pad columns,
    # then along y = 34.3 to the U6 non-inverting input.
    x57, y57 = P("U5", "7")
    x65, y65 = P("U6", "5")
    T("LP_OUT", [(x57, y57), (66.5, y57), (66.5, 34.3), (x65, 34.3),
                 (x65, y65)], w=W_SIG)

    # MUX_A0 and MUX_A1: J4 to the mux select pins, with underpasses
    # below the 5VA rail (y 20.6) and the VREF rail (y 35.4).
    def control(net, jpad, drop_x, lane_y, mux_pin, top_y, south_first):
        xj, yj = P("J4", jpad)
        xm_, ym_ = P("U3", mux_pin)
        T(net, [(xj, yj), (xj, top_y), (drop_x, top_y), (drop_x, 19.5)])
        V(net, drop_x, 19.5)
        T(net, [(drop_x, 19.5), (drop_x, 21.9)], layer="B.Cu")
        V(net, drop_x, 21.9)
        T(net, [(drop_x, 21.9), (drop_x, 34.6)])
        V(net, drop_x, 34.6)
        T(net, [(drop_x, 34.6), (drop_x, 36.6)], layer="B.Cu")
        V(net, drop_x, 36.6)
        T(net, [(drop_x, 36.6), (drop_x, lane_y), (xm_, lane_y), (xm_, ym_)])
        _ = south_first

    control("MUX_A0", "5", 60.6, 36.0, "10", 8.6, True)
    control("MUX_A1", "6", 58.1, 36.75, "9", 1.9, False)

    # Buck corner escapes: rehearsed against real pad geometry, all
    # margins >= 0.225 mm (see the board README for the method).
    T("BUCK_SS", [P("C4", "1"), (28.3, P("C4", "1")[1]), (28.3, 13.35),
                  (25.2, 13.35), (25.2, 12.25), P("U1", "9")])
    T("BUCK_DEF", [P("JP3", "2"), (36.04, 6.5), (31.6, 6.5), (31.6, 13.9),
                   (23.25, 13.9)], layer="B.Cu")
    V("BUCK_DEF", 23.25, 13.9)
    T("BUCK_DEF", [(23.25, 13.9), P("U1", "8")])
    # Pi 3V3 drops to the plane side right at the isolator pin.
    T("PI_3V3", [P("U7", "8"), (15.4, 31.6)])
    V("PI_3V3", 15.4, 31.6)
    # M1_A (mux pin 12 to cell 1) stays on the finish list: any seeded
    # crossing of the cell band displaces more links than it closes.


# ----------------------------------------------------------------------
# Plane, checks and assembly.
# ----------------------------------------------------------------------
def _plane_strips(pads, tracks, vias):
    keep_out = []
    for pad in pads:
        if pad.tht and pad.net != "GND":
            keep_out.append(box(pad.x - pad.w / 2 - PLANE_CLR,
                                pad.y - pad.h / 2 - PLANE_CLR,
                                pad.x + pad.w / 2 + PLANE_CLR,
                                pad.y + pad.h / 2 + PLANE_CLR))
    for net, width, pts, layer in tracks:
        if layer == "B.Cu" and net != "GND":
            keep_out.append(LineString(pts).buffer(width / 2.0 + PLANE_CLR))
    for net, x, y in vias:
        if net != "GND":
            keep_out.append(Point(x, y).buffer(VIA_D / 2.0 + PLANE_CLR))
    holes = unary_union(keep_out) if keep_out else None
    outline = box(EDGE_KEEPOUT, EDGE_KEEPOUT,
                  BOARD_W - EDGE_KEEPOUT, BOARD_H - EDGE_KEEPOUT)
    fill = outline.difference(holes) if holes is not None else outline

    strips = []
    step, overlap = 0.5, 0.06
    y = EDGE_KEEPOUT
    while y < BOARD_H - EDGE_KEEPOUT:
        band = box(EDGE_KEEPOUT, y - overlap,
                   BOARD_W - EDGE_KEEPOUT, y + step + overlap)
        inter = fill.intersection(band)
        for g in getattr(inter, "geoms", [inter]):
            if g.is_empty or g.area < 0.05:
                continue
            strips.append([(round(px, 3), round(py, 3))
                           for px, py in g.exterior.coords])
        y += step
    return fill, strips


PLANE_CLR = 0.3


def _connectivity_errors(circuit: Circuit, pads, tracks, vias) -> list[str]:
    from collections import defaultdict

    errors = []
    by_net_pads = defaultdict(list)
    for pad in pads:
        if pad.net:
            by_net_pads[pad.net].append(pad)
    for net, net_pads in by_net_pads.items():
        if net == "GND" or len(net_pads) < 2:
            continue
        geoms = [box(p.x - p.w / 2 - 0.05, p.y - p.h / 2 - 0.05,
                     p.x + p.w / 2 + 0.05, p.y + p.h / 2 + 0.05)
                 for p in net_pads]
        for tnet, width, pts, _layer in tracks:
            if tnet == net:
                geoms.append(LineString(pts).buffer(width / 2.0 + 0.02))
        for vnet, x, y in vias:
            if vnet == net:
                geoms.append(Point(x, y).buffer(VIA_D / 2.0))
        merged = unary_union(geoms)
        n_parts = len(getattr(merged, "geoms", [merged]))
        if n_parts != 1:
            errors.append(f"{net}: {n_parts} pieces")
    return errors


def _drc_errors(pads, tracks, vias) -> list[str]:
    from collections import defaultdict

    items = defaultdict(list)
    for pad in pads:
        geom = box(pad.x - pad.w / 2, pad.y - pad.h / 2,
                   pad.x + pad.w / 2, pad.y + pad.h / 2)
        for la in (("F.Cu", "B.Cu") if pad.tht else ("F.Cu",)):
            items[la].append((pad.net or f"NC:{pad.ref}.{pad.number}", geom))
    for net, width, pts, layer in tracks:
        items[layer].append((net, LineString(pts).buffer(width / 2.0)))
    for net, x, y in vias:
        for la in ("F.Cu", "B.Cu"):
            items[la].append((net, Point(x, y).buffer(VIA_D / 2.0)))

    errors = []
    for layer, entries in items.items():
        merged = defaultdict(list)
        for net, geom in entries:
            merged[net].append(geom)
        nets = {net: unary_union(gs) for net, gs in merged.items()}
        names = sorted(nets)
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                d = nets[a].distance(nets[b])
                if d < FAB_CLR - 1e-6:
                    errors.append(f"{layer}: {a} vs {b}: {d:.3f} mm")
    return errors


def _strip_subclearance(pads, router) -> list[str]:
    """Remove any copper below the fab clearance, reopening its link.

    Returns the stripped nets (one entry per removed piece). After this
    the exact DRC is clean up to pad-against-pad placement pairs."""
    from collections import defaultdict

    def _net_geoms(net_a, net_b, layer_name):
        geoms = defaultdict(list)
        for q in pads:
            if q.net in (net_a, net_b):
                layers = ("F.Cu", "B.Cu") if q.tht else ("F.Cu",)
                if layer_name in layers:
                    geoms[q.net].append(box(q.x - q.w / 2, q.y - q.h / 2,
                                            q.x + q.w / 2, q.y + q.h / 2))
        for vnet, x, y in router.vias:
            if vnet in (net_a, net_b):
                geoms[vnet].append(Point(x, y).buffer(VIA_D / 2.0))
        for tnet, w, pts, tlayer in router.tracks:
            if tnet in (net_a, net_b) and tlayer == layer_name:
                geoms[tnet].append(LineString(pts).buffer(w / 2.0))
        return geoms

    stripped: list[str] = []
    skipped_pairs: set[tuple[str, str, str]] = set()
    for _ in range(64):
        errors = _drc_errors(pads, router.tracks, router.vias)
        target = None
        for err in errors:
            layer_name, rest = err.split(": ", 1)
            nets_part = rest.rsplit(":", 1)[0]
            net_a, net_b = nets_part.split(" vs ")
            if (layer_name, net_a, net_b) not in skipped_pairs:
                target = (layer_name, net_a, net_b)
                break
        if target is None:
            break
        layer_name, net_a, net_b = target
        geoms = _net_geoms(net_a, net_b, layer_name)
        best = (None, None, 1e9)
        for idx, (tnet, w, pts, tlayer) in enumerate(router.tracks):
            if tlayer != layer_name or tnet not in (net_a, net_b):
                continue
            other = net_b if tnet == net_a else net_a
            if not geoms[other]:
                continue
            g = LineString(pts).buffer(w / 2.0)
            d = min(g.distance(og) for og in geoms[other])
            if d < FAB_CLR - 1e-6 and len(pts) < best[2]:
                best = ("track", idx, len(pts))
        if best[0] is None:
            # No offending track: try a via (a via barrel exists on both
            # layers, so its removal can clear the pair as well).
            for jdx, (vnet, x, y) in enumerate(router.vias):
                if vnet not in (net_a, net_b):
                    continue
                other = net_b if vnet == net_a else net_a
                if not geoms[other]:
                    continue
                g = Point(x, y).buffer(VIA_D / 2.0)
                d = min(g.distance(og) for og in geoms[other])
                if d < FAB_CLR - 1e-6:
                    best = ("via", jdx, 0)
                    break
        if best[0] == "track":
            stripped.append(router.tracks[best[1]][0])
            del router.tracks[best[1]]
        elif best[0] == "via":
            stripped.append(router.vias[best[1]][0])
            del router.vias[best[1]]
        else:
            # Pad against pad: a placement issue, not copper we can strip.
            skipped_pairs.add((layer_name, net_a, net_b))
    return stripped


def build_pcb(cfg: BoardConfig, circuit: Circuit) -> PcbResult:
    placements = full_placements(cfg)
    missing = [c.ref for c in circuit.components if c.ref not in placements]
    if missing:
        raise ValueError(f"unplaced components: {missing}")
    pads = _pad_instances(circuit, placements)

    def net_span(net):
        ps = [p for p in pads if p.net == net]
        xs = [p.x for p in ps]
        ys = [p.y for p in ps]
        return (max(xs) - min(xs)) + (max(ys) - min(ys)) if ps else 0.0

    base_order = sorted(
        (n for n in circuit.nets if n != "GND"),
        key=lambda n: (n not in POWER_NETS, net_span(n)),
    )

    def run(order):
        r = Router(pads)
        # Structural rails: VREF along the south of the chain band with a
        # B.Cu window where the mux commons rise; 5VA along its north.
        r.seed_track("VREF", [(26.0, 35.4), (44.5, 35.4)], W_SIG)
        r.seed_via("VREF", 44.5, 35.4)
        r.seed_track("VREF", [(44.5, 35.4), (53.0, 35.4)], W_SIG, layer="B.Cu")
        r.seed_via("VREF", 53.0, 35.4)
        r.seed_track("VREF", [(53.0, 35.4), (92.0, 35.4)], W_SIG)
        r.seed_track("5VA", [(44.0, 20.6), (96.0, 20.6)], W_PWR)
        _hand_seeds(r, pads)
        r.gnd_to_plane()
        for net in order:
            r.route_net(net)
        return r

    # Congestion is order-dependent: promote whatever failed to the front
    # and keep the best round.
    promoted: list[str] = []
    router = None
    for _round in range(2):
        order = promoted + [n for n in base_order if n not in promoted]
        cand = run(order)
        if router is None or len(cand.failed) < len(router.failed):
            router = cand
        if not cand.failed:
            break
        newly = []
        for f in cand.failed:
            net = f.split(":")[0]
            if net not in promoted and net != "GND-via":
                newly.append(net)
        promoted = list(dict.fromkeys(newly + promoted))
    if router.failed:
        router.cleanup_pass()

    # Guarantee order: strip sub-clearance copper, then close remaining
    # gaps with the exact-geometry finishing pass, then compute the
    # plane over the final copper and assemble the file once.
    stripped = _strip_subclearance(pads, router)
    from .finish import finish_pass
    finish_log = finish_pass(pads, router.tracks, router.vias)

    fill, strips = _plane_strips(pads, router.tracks, router.vias)

    board = Board(thickness_mm=1.6,
                  title="Damier LC, maquette 2x2, carte analogique")
    net_index = {"": 0}
    for comp in circuit.components:
        for net in comp.pins.values():
            if net not in net_index:
                net_index[net] = board.net(net)
    for comp in circuit.components:
        x, y, rot = placements[comp.ref]
        fp = load_footprint(comp.part.footprint)
        pad_nets = {num: (net_index[net], net) for num, net in comp.pins.items()}
        board.body.append(place_footprint(fp, comp.ref, comp.value, x, y, rot, pad_nets))
    for net, width, pts, layer in router.tracks:
        board.polyline(pts, width, layer, net_index[net])
    for net, x, y in router.vias:
        board.via(x, y, VIA_D, VIA_DRILL, net_index[net])

    gnd = net_index["GND"]
    poly_lines = []
    for strip in strips:
        pts_txt = " ".join(f"(xy {px} {py})" for px, py in strip)
        poly_lines.append(
            "    (filled_polygon (layer \"B.Cu\") (island) (pts " + pts_txt + "))"
        )
    zone = (
        f"  (zone (net {gnd}) (net_name \"GND\") (layer \"B.Cu\") "
        "(hatch edge 0.5)\n"
        "    (connect_pads yes (clearance 0.3))\n"
        "    (min_thickness 0.2) (filled_areas_thickness no)\n"
        "    (fill yes (thermal_gap 0.3) (thermal_bridge_width 0.4))\n"
        f"    (polygon (pts (xy {EDGE_KEEPOUT} {EDGE_KEEPOUT}) "
        f"(xy {BOARD_W - EDGE_KEEPOUT} {EDGE_KEEPOUT}) "
        f"(xy {BOARD_W - EDGE_KEEPOUT} {BOARD_H - EDGE_KEEPOUT}) "
        f"(xy {EDGE_KEEPOUT} {BOARD_H - EDGE_KEEPOUT})))\n"
        + "\n".join(poly_lines) + "\n  )"
    )
    board.body.append(zone)

    board.gr_rect(0.0, 0.0, BOARD_W, BOARD_H, "Edge.Cuts")
    board.gr_text("DAMIER LC / MAQUETTE 2x2 / ANALOG", 22.0, 59.5, "F.SilkS", 1.5)
    board.gr_text("vers carte bobines", 80.0, 59.5, "F.SilkS", 1.2)

    result = PcbResult(board=board, placements=placements,
                       pad_pos={(p.ref, p.number): (p.x, p.y) for p in pads},
                       tracks=router.tracks, vias=router.vias,
                       plane_polys=strips)
    conn = _connectivity_errors(circuit, pads, router.tracks, router.vias)
    still_split = {e.split(":")[0] for e in conn}
    kept_fails = [f for f in router.failed
                  if f.startswith("GND-via") or f.split(":")[0] in still_split]
    result.open_nets = kept_fails + conn
    for net in dict.fromkeys(stripped):
        if net in still_split:
            result.open_nets.append(f"{net}: cuivre retire (sous-garde), a finir")
    result.finish_log = finish_log
    result.drc_errors = _drc_errors(pads, router.tracks, router.vias)
    parts = list(getattr(fill, "geoms", [fill]))
    result.plane_islands = len(parts)
    return result
