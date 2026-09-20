"""Exact-geometry finishing pass, shared by the generators.

The lattice router is saturated by its own caution: cells, rounded pad
marks, margins with slack. What it leaves open is usually tiny (a pad a
few tenths of a millimetre from its net, a stub walled in by a via) and
the real channel is wide enough at the fabrication clearance. This pass
works on the finished copper with exact shapely geometry: for every net
still in pieces it tries a small family of joints (straight, L, swept Z
on one layer, then the same through one or two vias, then a local maze
on a fine raster) and keeps the first one clear of every foreign copper.
What it adds never degrades the exact clearance check; what it cannot
close stays open and listed.

It is the port of the pass that closed the analog board of the mockup
(`analoggen.finish`, `analoggen.maze`, two layers, a fixed outline) to
the shared copper model of `quadgen.connect`: any stack, a plane layer
no signal may run on, the outline and the rules of the board it serves.
Every generator adapts its own copper to the plain tuples below and
draws back the plan the pass returns.

Copper model of one board:

- pads: objects with net, layer ("*.Cu" for a plated pad), x, y, w, h,
  rot, shape, rratio, drill, ref, number (the PadItem of each generator);
- tracks: (net, layer, width, points);
- vias: (net, x, y, pad, drill);
- holes: (x, y, drill) of the unplated holes;
- keepouts: (x0, y0, x1, y1) rectangles, or shapely shapes, no copper may
  enter on any layer;
- pour: (layer, geometry) of the ground pour, the geometry None when the
  pour covers the board (a plane layer), else its islands.
"""

from __future__ import annotations

import heapq
import math
import time
from dataclasses import dataclass
from itertools import islice

import numpy as np
import shapely
from shapely.geometry import LineString, Point, box
from shapely.ops import nearest_points, unary_union
from shapely.strtree import STRtree

from .connect import copper_components, pad_copper

MAX_JOINTS = 120
MAX_ROUNDS = 26  # the ground alone can owe one joint per stranded group
MAX_PAIRS = 40  # pairs of pieces tried per round, nearest first
RING_RADII = (0.4, 0.6, 0.8, 1.0, 1.3, 1.6, 2.0, 2.4, 2.9, 3.5, 4.2, 5.0, 6.0)
RING_ANGLES = 12
STUB_PATHS = 9  # straight, both corners, then the first sweeps
VIA_SPOTS = 6  # via spots tried on each side of a two-via joint
THERMAL_PAD_MM = 1.2  # a pad this wide both ways takes stitching vias
MAZE_PAIRS = 6  # pairs offered to the maze once the simple joints fail
SLOP = 1e-9

# ---- the maze of the last resort
MAZE_GRID = 0.05  # raster step of the search, coarsened for a long haul
MAZE_MARGIN_MM = 10.0  # how far around the two pieces the search may wander
DIAG = math.sqrt(2.0)
VIA_COST = 10.0  # cells: a via is worth half a millimetre of detour
TURN_COST = 1.5  # cells: prefer the straight run, then the single corner
MAX_CELLS = 400_000  # ceiling on the exploration of one link
MAX_GRID = 0.2  # coarsest raster: past it the gaps of a pad row close


@dataclass(frozen=True)
class Rules:
    """What the board allows the pass to draw."""

    layers: tuple[str, ...]  # the copper stack, outside in
    board: tuple[float, float]  # width, height
    edge: float  # copper to board edge
    clearance: float  # copper to copper of another net
    width: float  # of a joint
    via: tuple[float, float]  # pad, drill of a joint via
    plane: str | None = None  # the plane layer: no joint runs on it
    hole_to_hole: float = 0.25  # drill edge to drill edge
    thin: float | None = None  # a thinner joint tried when the first fails
    small_via: tuple[float, float] | None = None  # a finer via tried when the first fails
    budget_s: float = 60.0  # seconds spent on one net before it is left open

    @property
    def route_layers(self) -> tuple[str, ...]:
        return tuple(la for la in self.layers if la != self.plane)

    def widths(self) -> tuple[float, ...]:
        if self.thin is None or self.thin >= self.width:
            return (self.width,)
        return (self.width, self.thin)

    def vias(self) -> tuple[tuple[float, float], ...]:
        if self.small_via is None or self.small_via[0] >= self.via[0]:
            return (self.via,)
        return (self.via, self.small_via)


def _pad_layers(pad, layers) -> tuple[str, ...]:
    return tuple(layers) if pad.layer == "*.Cu" else (pad.layer,)


class _Obstacles:
    """Foreign copper per layer, indexed for fast clearance queries, plus
    what a via must keep away from on every layer: the holes."""

    def __init__(self, rules: Rules, pads, tracks, vias, holes, keepouts):
        self.rules = rules
        self.items: dict[str, list] = {la: [] for la in rules.layers}
        self.pads = list(pads)
        self.pad_geoms = [pad_copper(q) for q in self.pads]
        for q, g in zip(self.pads, self.pad_geoms, strict=True):
            name = q.net or f"NC:{q.ref}.{q.number}"
            for la in _pad_layers(q, rules.layers):
                self.items[la].append((name, g))
        for net, layer, w, pts in tracks:
            self.items[layer].append((net, LineString(pts).buffer(w / 2.0)))
        for net, x, y, pad, _drill in vias:
            g = Point(x, y).buffer(pad / 2.0)
            for la in rules.layers:
                self.items[la].append((net, g))
        # an unplated hole: no copper of any net over it, on any layer
        for x, y, d in holes:
            g = Point(x, y).buffer(d / 2.0 + 0.3)
            for la in rules.layers:
                self.items[la].append(("__hole__", g))
        for keep in keepouts:
            g = box(*keep) if isinstance(keep, tuple) else keep
            for la in rules.layers:
                self.items[la].append(("__keepout__", g))
        # drills a via's own drill must keep away from, whatever the net
        drills = [(q.x, q.y, q.drill) for q in self.pads if q.drill] + list(holes)
        drills += [(x, y, d) for _n, x, y, _p, d in vias]
        self.drill_geoms = [Point(x, y).buffer(d / 2.0) for x, y, d in drills]
        self.drill_tree = STRtree(self.drill_geoms) if self.drill_geoms else None
        self.pad_tree = STRtree(self.pad_geoms) if self.pad_geoms else None
        self._trees: dict[str, STRtree] = {}
        self._geoms: dict[str, list] = {}
        for la in rules.layers:
            self._rebuild(la)

    def _rebuild(self, layer: str) -> None:
        self._geoms[layer] = list(self.items[layer])
        self._trees[layer] = STRtree([g for _, g in self.items[layer]])

    def clear_of_foreign(self, net: str, layer: str, geom) -> bool:
        clr = self.rules.clearance
        tree = self._trees[layer]
        for idx in tree.query(geom.buffer(clr)):
            oname, og = self._geoms[layer][int(idx)]
            if oname != net and geom.distance(og) < clr:
                return False
        return True

    def in_board(self, pts, half: float) -> bool:
        w, h = self.rules.board
        e = self.rules.edge + half
        return all(e <= x <= w - e and e <= y <= h - e for x, y in pts)

    def via_ok(self, net: str, x: float, y: float, via: tuple[float, float] | None = None) -> bool:
        pad, drill = via or self.rules.via
        r = pad / 2.0
        w, h = self.rules.board
        e = self.rules.edge
        if not (e + r <= x <= w - e - r and e + r <= y <= h - e - r):
            return False
        disc = Point(x, y).buffer(r)
        for la in self.rules.layers:
            if not self.clear_of_foreign(net, la, disc):
                return False
        # its drill against every other drill, whatever the net
        if self.drill_tree is not None:
            hole = Point(x, y).buffer(drill / 2.0)
            for idx in self.drill_tree.query(hole.buffer(self.rules.hole_to_hole)):
                if hole.distance(self.drill_geoms[int(idx)]) < self.rules.hole_to_hole:
                    return False
        # never inside a pad the paste will cover, its own included; a
        # thermal pad is the exception the datasheets ask for, its
        # stitching vias are how the heat and the ground get out
        if self.pad_tree is not None:
            for idx in self.pad_tree.query(disc):
                k = int(idx)
                if disc.intersection(self.pad_geoms[k]).area <= SLOP:
                    continue
                q = self.pads[k]
                if q.net == net and not q.drill and min(q.w, q.h) >= THERMAL_PAD_MM:
                    continue
                return False
        return True

    def add_track(self, net: str, pts, layer: str, width: float) -> None:
        self.items[layer].append((net, LineString(pts).buffer(width / 2.0)))
        self._rebuild(layer)

    def add_via(self, net: str, x: float, y: float, via: tuple[float, float] | None = None) -> None:
        pad, drill = via or self.rules.via
        g = Point(x, y).buffer(pad / 2.0)
        for la in self.rules.layers:
            self.items[la].append((net, g))
            self._rebuild(la)
        self.drill_geoms.append(Point(x, y).buffer(drill / 2.0))
        self.drill_tree = STRtree(self.drill_geoms)


# ------------------------------------------------------------ pieces
def net_items(net: str, rules: Rules, pads, tracks, vias, pour=None) -> tuple[list, int]:
    """The copper of one net as (layers, geometry) items, the pour's
    islands last; returns the items and how many of them are drawn
    copper (the rest is pour, which the filler drops when alone)."""
    items = []
    for q in pads:
        if q.net == net:
            items.append((_pad_layers(q, rules.layers), pad_copper(q)))
    for tnet, layer, w, pts in tracks:
        if tnet == net:
            items.append(((layer,), LineString(pts).buffer(w / 2.0)))
    for vnet, x, y, pad, _drill in vias:
        if vnet == net:
            items.append((tuple(rules.layers), Point(x, y).buffer(pad / 2.0)))
    drawn = len(items)
    if pour is not None:
        layer, geom = pour
        if geom is None:
            w, h = rules.board
            geom = box(rules.edge, rules.edge, w - rules.edge, h - rules.edge)
        for island in getattr(geom, "geoms", [geom]):
            items.append(((layer,), island))
    return items, drawn


def net_pieces(net: str, rules: Rules, pads, tracks, vias, pour=None) -> list[dict]:
    """Connected components of a net's copper, each a dict layer to its
    exact copper on that layer; pieces made of pour alone are dropped."""
    items, drawn = net_items(net, rules, pads, tracks, vias, pour)
    pieces = []
    for comp in copper_components(items):
        if not any(k < drawn for k in comp):
            continue
        piece: dict[str, list] = {}
        for k in comp:
            for la in items[k][0]:
                piece.setdefault(la, []).append(items[k][1])
        pieces.append({la: unary_union(gs) for la, gs in piece.items()})
    return pieces


def _bounds(piece: dict) -> tuple[float, float, float, float]:
    sides = [g.bounds for g in piece.values() if not g.is_empty]
    return (
        min(b[0] for b in sides),
        min(b[1] for b in sides),
        max(b[2] for b in sides),
        max(b[3] for b in sides),
    )


# ------------------------------------------------------------ joints
def _paths(pa, pb):
    """Candidate polylines from pa to pb on one layer, simplest first."""
    (xa, ya), (xb, yb) = pa, pb
    yield [pa, pb]
    if abs(xa - xb) > 1e-6 and abs(ya - yb) > 1e-6:
        yield [pa, (xb, ya), pb]
        yield [pa, (xa, yb), pb]
    for off in (0.2, -0.2, 0.4, -0.4, 0.6, -0.6, 0.9, -0.9, 1.3, -1.3, 1.8, -1.8, 2.4, -2.4):
        ym = (ya + yb) / 2.0 + off
        yield [pa, (xa, ym), (xb, ym), pb]
        xm = (xa + xb) / 2.0 + off
        yield [pa, (xm, ya), (xm, yb), pb]
    for off in (3.2, -3.2, 4.0, -4.0, 4.8, -4.8, 5.6, -5.6, 6.4, -6.4):
        ym = (ya + yb) / 2.0 + off
        yield [pa, (xa, ym), (xb, ym), pb]
        xm = (xa + xb) / 2.0 + off
        yield [pa, (xm, ya), (xm, yb), pb]


def _ring(p, radii=RING_RADII, angles=RING_ANGLES):
    """Via spots around a point, nearest ring first, every direction."""
    x, y = p
    for r in radii:
        for k in range(angles):
            a = 2.0 * math.pi * k / angles
            yield (x + r * math.cos(a), y + r * math.sin(a))


def _contacts(geom, other, n_extra=3):
    """Contact points on geom: nearest to other, then boundary walks."""
    p0 = nearest_points(geom, other)[0]
    pts = [(p0.x, p0.y)]
    b = geom.boundary
    if b.is_empty or b.length < 1e-6:
        return pts
    s0 = b.project(p0)
    for ds in (1.0, -1.0, 2.5, -2.5, 5.0, -5.0)[: 2 * n_extra]:
        q = b.interpolate((s0 + ds) % b.length)
        if all(abs(q.x - x) + abs(q.y - y) > 0.3 for x, y in pts):
            pts.append((q.x, q.y))
    return pts


class _Joiner:
    """The joint families, in the order they are tried."""

    def __init__(self, rules: Rules, obs: _Obstacles, width: float, via: tuple[float, float]):
        self.rules, self.obs, self.width, self.via = rules, obs, width, via

    def _legal(self, net, layer, pts, touch=()):
        g = LineString(pts).buffer(self.width / 2.0)
        if not self.obs.in_board(pts, self.width / 2.0):
            return None
        for other in touch:
            if other is not None and g.distance(other) > SLOP:
                return None
        return g if self.obs.clear_of_foreign(net, layer, g) else None

    def layer_join(self, net, layer, pa, pb, ga, gb):
        """One-layer joint from pa to pb touching both true geometries."""
        for pts in _paths(pa, pb):
            if self._legal(net, layer, pts, (ga, gb)) is not None:
                return [("T", pts, layer)]
        return None

    def stub_via(self, net, layer, p, contact):
        """Legal stub on `layer` from p to a nearby via; yields (plan, via)."""
        for v in _ring(p):
            if not self.obs.via_ok(net, *v, via=self.via):
                continue
            for stub in islice(_paths(p, v), STUB_PATHS):
                if self._legal(net, layer, stub, (contact,)) is not None:
                    yield [("T", stub, layer), ("V", v, self.via)], v
                    break

    def single_via(self, net, layer_a, pa, ga, layer_b, gb):
        """Stub and via on layer A, run on layer B straight onto B copper;
        a few via spots, then the maze is the better search."""
        for head, va in islice(self.stub_via(net, layer_a, pa, ga), VIA_SPOTS):
            p2 = nearest_points(Point(va), gb)[1]
            for run in _paths(va, (p2.x, p2.y)):
                if self._legal(net, layer_b, run, (gb,)) is not None:
                    return head + [("T", run, layer_b)]
        return None

    def via_join(self, net, layer_a, pa, ga, layer_b, pb, gb, layer_run):
        """Stub, via, run on a third layer, via, stub. A few via spots on
        each side: past them the maze is the better search."""
        heads = list(islice(self.stub_via(net, layer_a, pa, ga), VIA_SPOTS))
        tails = list(islice(self.stub_via(net, layer_b, pb, gb), VIA_SPOTS))
        for head, va in heads:
            for tail, vb in tails:
                if abs(va[0] - vb[0]) < 0.75 and abs(va[1] - vb[1]) < 0.75:
                    continue
                for run in _paths(va, vb):
                    if self._legal(net, layer_run, run) is not None:
                        stub_b, via_b = tail
                        return head + [("T", run, layer_run), via_b, stub_b]
        return None

    def check_plan(self, net, plan) -> list | None:
        """A plan from the maze, re-checked on the exact geometry, its
        vias sized; None when the copper forbids it."""
        out = []
        for kind, payload, layer in plan:
            if kind == "T":
                if self._legal(net, layer, payload) is None:
                    return None
                out.append((kind, payload, layer))
            elif not self.obs.via_ok(net, *payload, via=self.via):
                return None
            else:
                out.append((kind, payload, self.via))
        return out


def _try_pair(net, rules, joiner, pa_piece, pb_piece):
    """The first joint between two pieces, families in order."""
    routable = rules.route_layers
    whole_a = unary_union(list(pa_piece.values()))
    whole_b = unary_union(list(pb_piece.values()))
    # same layer, both pieces have copper there
    for la in routable:
        ga, gb = pa_piece.get(la), pb_piece.get(la)
        if ga is None or gb is None:
            continue
        for pa in _contacts(ga, gb):
            for pb in _contacts(gb, ga):
                plan = joiner.layer_join(net, la, pa, pb, ga, gb)
                if plan:
                    return plan
    # one via: from any layer of a, to any layer of b
    for la in routable:
        ga = pa_piece.get(la)
        if ga is None:
            continue
        for lb in routable:
            gb = pb_piece.get(lb)
            if gb is None or lb == la:
                continue
            for pa in _contacts(ga, whole_b):
                plan = joiner.single_via(net, la, pa, ga, lb, gb)
                if plan:
                    return plan
    for lb in routable:
        gb = pb_piece.get(lb)
        if gb is None:
            continue
        for la in routable:
            ga = pa_piece.get(la)
            if ga is None or la == lb:
                continue
            for pb in _contacts(gb, whole_a):
                plan = joiner.single_via(net, lb, pb, gb, la, ga)
                if plan:
                    return plan
    # two vias and a run on a third layer (a run on the layer of a stub is
    # a longer version of what the joints above tried)
    for la in routable:
        ga = pa_piece.get(la)
        if ga is None:
            continue
        for lb in routable:
            gb = pb_piece.get(lb)
            if gb is None:
                continue
            for lr in routable:
                if lr in (la, lb):
                    continue
                for pa in _contacts(ga, gb, n_extra=1):
                    for pb in _contacts(gb, ga, n_extra=1):
                        plan = joiner.via_join(net, la, pa, ga, lb, pb, gb, lr)
                        if plan:
                            return plan
    return None


def _drop_to_plane(net, rules, joiner, piece):
    """A piece of the plane's net without copper on the plane: a stub and
    a via, anywhere legal near it, is the joint (the via reaches the plane)."""
    for la in rules.route_layers:
        g = piece.get(la)
        if g is None:
            continue
        c = g.centroid
        p0 = nearest_points(g, c)[0]
        for p in [(p0.x, p0.y)] + _contacts(g, Point(p0.x, p0.y), n_extra=3)[1:]:
            for head, _v in joiner.stub_via(net, la, p, g):
                return head
    return None


def finish_pass(
    rules: Rules,
    pads,
    tracks,
    vias,
    holes=(),
    keepouts=(),
    nets=None,
    pour=None,
    pour_net: str = "GND",
) -> tuple[list, list, list[str]]:
    """Close the remaining gaps of `nets` (every net but the pour's by
    default) with exact-geometry joints. Returns the tracks and vias to
    draw, as (net, layer, width, points) and (net, x, y, pad, drill), and
    the log of the joints. `tracks` and `vias` are read, never changed.
    The pour's net is finished when named in `nets`, against `pour`."""
    tracks = [tuple(t) for t in tracks]
    vias = [tuple(v) for v in vias]
    obs = _Obstacles(rules, pads, tracks, vias, holes, keepouts)
    if nets is None:
        nets = sorted({q.net for q in pads if q.net and q.net != pour_net})
    new_tracks: list = []
    new_vias: list = []
    log: list[str] = []
    joints = 0
    for net in nets:
        this_pour = pour if net == pour_net else None
        t0 = time.monotonic()
        for _ in range(MAX_ROUNDS):
            if joints >= MAX_JOINTS:
                return new_tracks, new_vias, log
            pieces = net_pieces(net, rules, pads, tracks + new_tracks, vias + new_vias, this_pour)
            if len(pieces) <= 1:
                break
            plan = None
            if time.monotonic() - t0 > rules.budget_s:
                log.append(f"{net}: budget spent, left open")
                break
            if this_pour is not None and this_pour[1] is None:
                # a plane: every piece without copper on it owes one drop
                stranded = [pc for pc in pieces if this_pour[0] not in pc]
                if not stranded:
                    break
                for width, via in _attempts(rules):
                    plan = _drop_to_plane(net, rules, _Joiner(rules, obs, width, via), stranded[0])
                    if plan:
                        break
                dist = 0.0
            else:
                boxes = [box(*_bounds(pc)) for pc in pieces]
                pairs = sorted(
                    (
                        (boxes[i].distance(boxes[j]), i, j)
                        for i in range(len(pieces))
                        for j in range(i + 1, len(pieces))
                    ),
                    key=lambda t: t[0],
                )[:MAX_PAIRS]
                dist = 0.0
                # the simple joints of every width and via first, the mazes
                # only once none of them passes: a maze costs seconds
                for width, via in _attempts(rules):
                    joiner = _Joiner(rules, obs, width, via)
                    for d, i, j in pairs:
                        plan = _try_pair(net, rules, joiner, pieces[i], pieces[j])
                        if plan:
                            dist = d
                            break
                    if plan:
                        break
                for width, via in _attempts(rules) if plan is None else ():
                    joiner = _Joiner(rules, obs, width, via)
                    for d, i, j in pairs[:MAZE_PAIRS]:
                        plan = maze_join(
                            net,
                            rules,
                            pieces[i],
                            pieces[j],
                            pads,
                            tracks + new_tracks,
                            vias + new_vias,
                            holes,
                            keepouts,
                            width,
                            via,
                        )
                        plan = joiner.check_plan(net, plan) if plan is not None else None
                        if plan:
                            dist = d
                            break
                    if plan:
                        break
            if plan is None:
                break
            for kind, payload, layer in plan:
                if kind == "T":
                    pts = [tuple(p) for p in payload]
                    new_tracks.append((net, layer, width, pts))
                    obs.add_track(net, pts, layer, width)
                else:
                    x, y = payload
                    pad, drill = layer or rules.via
                    new_vias.append((net, x, y, pad, drill))
                    obs.add_via(net, x, y, (pad, drill))
            joints += 1
            log.append(f"{net}: joint ({dist:.2f} mm, {width:g} mm)")
    return new_tracks, new_vias, log


def _attempts(rules: Rules):
    """(width, via) pairs, the standard ones first, the finer ones after."""
    for via in rules.vias():
        for width in rules.widths():
            yield width, via


# ------------------------------------------------------------ the maze
def _dist_to_segment(xs, ys, p0, p1):
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    length2 = dx * dx + dy * dy
    if length2 < 1e-12:
        return np.hypot(xs - x0, ys - y0)
    t = ((xs - x0) * dx + (ys - y0) * dy) / length2
    np.clip(t, 0.0, 1.0, out=t)
    return np.hypot(xs - (x0 + t * dx), ys - (y0 + t * dy))


class _Field:
    """Cells of a window, and what blocks them on each routable layer."""

    def __init__(self, layers, x0, y0, x1, y1, grid):
        self.layers = tuple(layers)
        self.x0, self.y0, self.grid = x0, y0, grid
        self.nx = int(math.ceil((x1 - x0) / grid)) + 1
        self.ny = int(math.ceil((y1 - y0) / grid)) + 1
        self.xs = x0 + grid * np.arange(self.nx)
        self.ys = y0 + grid * np.arange(self.ny)
        self.gx, self.gy = np.meshgrid(self.xs, self.ys)
        self.blocked = {la: np.zeros((self.ny, self.nx), dtype=bool) for la in self.layers}
        self.via_blocked = np.zeros((self.ny, self.nx), dtype=bool)

    def point(self, i, j):
        return (self.x0 + j * self.grid, self.y0 + i * self.grid)

    def _window(self, x0, y0, x1, y1, reach):
        j0 = max(0, int(math.floor((x0 - reach - self.x0) / self.grid)))
        j1 = min(self.nx - 1, int(math.ceil((x1 + reach - self.x0) / self.grid)))
        i0 = max(0, int(math.floor((y0 - reach - self.y0) / self.grid)))
        i1 = min(self.ny - 1, int(math.ceil((y1 + reach - self.y0) / self.grid)))
        return i0, i1, j0, j1

    def _mark(self, targets, window, d, reach):
        i0, i1, j0, j1 = window
        hit = d <= reach
        for m in targets:
            m[i0 : i1 + 1, j0 : j1 + 1] |= hit

    def paint_segment(self, targets, p0, p1, half, reach):
        x0, x1 = sorted((p0[0], p1[0]))
        y0, y1 = sorted((p0[1], p1[1]))
        window = self._window(x0, y0, x1, y1, half + reach)
        if window[1] < window[0] or window[3] < window[2]:
            return
        i0, i1, j0, j1 = window
        d = _dist_to_segment(
            self.gx[i0 : i1 + 1, j0 : j1 + 1], self.gy[i0 : i1 + 1, j0 : j1 + 1], p0, p1
        )
        self._mark(targets, window, d, half + reach)

    def paint_geom(self, targets, geom, reach):
        """Cells closer than `reach` to an exact shape (a pad, a keepout)."""
        if geom is None or geom.is_empty:
            return
        gx0, gy0, gx1, gy1 = geom.bounds
        window = self._window(gx0, gy0, gx1, gy1, reach)
        if window[1] < window[0] or window[3] < window[2]:
            return
        i0, i1, j0, j1 = window
        pts = shapely.points(self.gx[i0 : i1 + 1, j0 : j1 + 1], self.gy[i0 : i1 + 1, j0 : j1 + 1])
        d = shapely.distance(geom, pts)
        self._mark(targets, window, d, reach)

    def mark_inside(self, geom):
        mask = np.zeros((self.ny, self.nx), dtype=bool)
        if geom is None or geom.is_empty:
            return mask
        gx0, gy0, gx1, gy1 = geom.bounds
        i0, i1, j0, j1 = self._window(gx0, gy0, gx1, gy1, 0.0)
        if i1 < i0 or j1 < j0:
            return mask
        pts = shapely.points(self.gx[i0 : i1 + 1, j0 : j1 + 1], self.gy[i0 : i1 + 1, j0 : j1 + 1])
        mask[i0 : i1 + 1, j0 : j1 + 1] = shapely.intersects(geom, pts)
        return mask


def _fill(field, rules, net, pads, tracks, vias, holes, keepouts, width, via):
    """Paint every foreign item into the field, plus the via keepouts."""
    slop = field.grid * DIAG / 2.0
    half = width / 2.0
    reach = rules.clearance + slop
    via_r = via[0] / 2.0
    drill_r = via[1] / 2.0
    all_sides = [field.blocked[la] for la in field.layers]
    holes_mask = field.via_blocked
    for q in pads:
        g = pad_copper(q)
        sides = [field.blocked[la] for la in _pad_layers(q, rules.layers) if la in field.blocked]
        if q.net != net:
            field.paint_geom(sides, g, half + reach)
            field.paint_geom((holes_mask,), g, via_r + reach)
        elif q.drill or min(q.w, q.h) < THERMAL_PAD_MM:
            field.paint_geom((holes_mask,), g, via_r)
        if q.drill:
            field.paint_segment(
                (holes_mask,), (q.x, q.y), (q.x, q.y), q.drill / 2.0, drill_r + rules.hole_to_hole
            )
    for tnet, layer, w, pts in tracks:
        if tnet == net or layer not in field.blocked:
            continue
        side = field.blocked[layer]
        for p0, p1 in zip(pts, pts[1:], strict=False):
            field.paint_segment((side,), tuple(p0), tuple(p1), w / 2.0, half + reach)
            field.paint_segment((holes_mask,), tuple(p0), tuple(p1), w / 2.0, via_r + reach)
    for vnet, x, y, pad, drill in vias:
        if vnet != net:
            field.paint_segment(all_sides, (x, y), (x, y), pad / 2.0, half + reach)
            field.paint_segment((holes_mask,), (x, y), (x, y), pad / 2.0, via_r + reach)
        field.paint_segment(
            (holes_mask,), (x, y), (x, y), drill / 2.0, drill_r + rules.hole_to_hole
        )
    for x, y, d in holes:
        field.paint_segment(all_sides, (x, y), (x, y), d / 2.0 + 0.3, half + reach)
        field.paint_segment((holes_mask,), (x, y), (x, y), d / 2.0 + 0.3, via_r + reach)
    for keep in keepouts:
        g = box(*keep) if isinstance(keep, tuple) else keep
        field.paint_geom(all_sides, g, half + reach)
        field.paint_geom((holes_mask,), g, via_r + reach)
    # the board edge
    w, h = rules.board
    e = rules.edge
    for p0, p1 in (((0, 0), (w, 0)), ((w, 0), (w, h)), ((w, h), (0, h)), ((0, h), (0, 0))):
        field.paint_segment(all_sides, p0, p1, 0.0, e + half)
        field.paint_segment((holes_mask,), p0, p1, 0.0, e + via_r)


def _search(field, starts, goals, via_ok):
    """A* over the routable layers; returns cells [(layer, i, j)] or None."""
    ny, nx = field.ny, field.nx
    layers = field.layers
    goal_any = np.zeros((ny, nx), dtype=bool)
    for la in layers:
        goal_any |= goals[la]
    gi, gj = np.nonzero(goal_any)
    if not len(gi):
        return None
    tgt_i, tgt_j = float(gi.mean()), float(gj.mean())
    free = {la: ~field.blocked[la] for la in layers}
    dist: dict = {}
    prev: dict = {}
    heap: list = []
    for la in layers:
        si, sj = np.nonzero(starts[la] & free[la])
        for i, j in zip(si, sj, strict=True):
            key = (la, int(i), int(j))
            dist[key] = 0.0
            heapq.heappush(heap, (0.0, 0.0, key, None))
    steps = (
        (0, 1, 1.0),
        (0, -1, 1.0),
        (1, 0, 1.0),
        (-1, 0, 1.0),
        (1, 1, DIAG),
        (1, -1, DIAG),
        (-1, 1, DIAG),
        (-1, -1, DIAG),
    )
    seen = 0
    while heap:
        _f, g, key, came = heapq.heappop(heap)
        if g > dist.get(key, math.inf):
            continue
        la, i, j = key
        if goals[la][i, j]:
            path = [key]
            while key in prev:
                key = prev[key]
                path.append(key)
            return list(reversed(path))
        seen += 1
        if seen > MAX_CELLS:
            return None
        for di, dj, cost in steps:
            ni, nj = i + di, j + dj
            if not (0 <= ni < ny and 0 <= nj < nx) or not free[la][ni, nj]:
                continue
            turn = TURN_COST if came is not None and came != (di, dj) else 0.0
            ng = g + cost + turn
            nkey = (la, ni, nj)
            if ng < dist.get(nkey, math.inf):
                dist[nkey] = ng
                prev[nkey] = key
                h = math.hypot(ni - tgt_i, nj - tgt_j)
                heapq.heappush(heap, (ng + h, ng, nkey, (di, dj)))
        if via_ok[i, j]:
            for other in layers:
                if other == la or not free[other][i, j]:
                    continue
                ng = g + VIA_COST
                nkey = (other, i, j)
                if ng < dist.get(nkey, math.inf):
                    dist[nkey] = ng
                    prev[nkey] = key
                    h = math.hypot(i - tgt_i, j - tgt_j)
                    heapq.heappush(heap, (ng + h, ng, nkey, None))
    return None


def _to_plan(field, cells):
    """Cells into the plan the pass draws: tracks and vias."""
    runs = []
    run = [cells[0]]
    for cell in cells[1:]:
        if cell[0] != run[-1][0]:
            runs.append(("run", run))
            runs.append(("via", field.point(cell[1], cell[2])))
            run = [cell]
        else:
            run.append(cell)
    runs.append(("run", run))
    out = []
    for kind, payload in runs:
        if kind == "via":
            out.append(("V", payload, None))
            continue
        if len(payload) < 2:
            continue
        pts = [field.point(payload[0][1], payload[0][2])]
        for a, b, c in zip(payload, payload[1:], payload[2:], strict=False):
            d1 = (b[1] - a[1], b[2] - a[2])
            d2 = (c[1] - b[1], c[2] - b[2])
            if d1 != d2:
                pts.append(field.point(b[1], b[2]))
        pts.append(field.point(payload[-1][1], payload[-1][2]))
        out.append(("T", pts, payload[0][0]))
    return out


def maze_join(net, rules, piece_a, piece_b, pads, tracks, vias, holes, keepouts, width, via=None):
    """A plan joining two pieces of `net` on a fine local raster, or None.

    The window is the gap between the two pieces widened by
    `MAZE_MARGIN_MM`; a haul across the board coarsens the raster until it
    fits the ceiling, and the pass re-checks the plan in exact geometry."""
    routable = rules.route_layers
    parts_a = [g for la, g in piece_a.items() if la in routable and not g.is_empty]
    parts_b = [g for la, g in piece_b.items() if la in routable and not g.is_empty]
    if not parts_a or not parts_b:
        return None
    pa, pb = nearest_points(unary_union(parts_a), unary_union(parts_b))
    w, h = rules.board
    e = rules.edge + width / 2.0
    x0 = max(e, min(pa.x, pb.x) - MAZE_MARGIN_MM)
    y0 = max(e, min(pa.y, pb.y) - MAZE_MARGIN_MM)
    x1 = min(w - e, max(pa.x, pb.x) + MAZE_MARGIN_MM)
    y1 = min(h - e, max(pa.y, pb.y) + MAZE_MARGIN_MM)
    if x1 - x0 < MAZE_GRID or y1 - y0 < MAZE_GRID:
        return None
    grid = MAZE_GRID
    while (x1 - x0) * (y1 - y0) / (grid * grid) > MAX_CELLS:
        grid *= 2.0
        if grid > MAX_GRID:
            return None
    via = via or rules.via
    window = box(x0, y0, x1, y1)
    field = _Field(routable, x0, y0, x1, y1, grid)
    _fill(field, rules, net, pads, tracks, vias, holes, keepouts, width, via)
    via_ok = ~field.via_blocked
    for la in routable:
        via_ok &= ~field.blocked[la]
    starts = {
        la: field.mark_inside(piece_a[la].intersection(window))
        if la in piece_a
        else np.zeros((field.ny, field.nx), dtype=bool)
        for la in routable
    }
    goals = {
        la: field.mark_inside(piece_b[la].intersection(window))
        if la in piece_b
        else np.zeros((field.ny, field.nx), dtype=bool)
        for la in routable
    }
    if not any(m.any() for m in starts.values()) or not any(m.any() for m in goals.values()):
        return None
    # the search radiates from the smaller piece: seeded with the thousands
    # of cells of a pour or a bus, it would spend its budget on the seeding
    if sum(int(m.sum()) for m in starts.values()) > sum(int(m.sum()) for m in goals.values()):
        starts, goals = goals, starts
    cells = _search(field, starts, goals, via_ok)
    if cells is None:
        return None
    return _to_plan(field, cells)


__all__ = ["Rules", "finish_pass", "maze_join", "net_pieces"]
