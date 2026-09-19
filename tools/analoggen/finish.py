"""Exact-geometry finishing pass.

The grid router is saturated by its own caution: 0.125 mm lattice,
cell-rounded pad marks, margins with slack. The remaining gaps are
tiny (a stripped stub, a pad 0.2 mm away from its net) and the real
channels are wide enough at the fab clearance. This pass works on the
finished copper with exact shapely geometry, no raster: for each net
still in pieces it tries a small family of joints (straight, L, swept
Z, then back-side variants through one or two vias) and keeps the
first one that stays clear of every foreign copper. Anything it adds
therefore never degrades the exact DRC; anything it cannot close is
left open and listed.
"""

from __future__ import annotations

import math
from itertools import islice

from shapely.geometry import LineString, Point, box
from shapely.ops import nearest_points, unary_union
from shapely.strtree import STRtree

from . import connect, maze

CLEAR = 0.15  # the netclass clearance: what the KiCad DRC calls an error
W_JOIN = 0.25
VIA_R = 0.3
EDGE = 0.55  # edge keepout + half width
MAX_JOINTS = 90
MAX_ROUNDS = 26  # the ground alone can owe one joint per stranded group
MAX_PAIRS = 40  # pairs of pieces tried per round, nearest first
RING_RADII = (0.4, 0.6, 0.8, 1.0, 1.3, 1.6, 2.0, 2.4, 2.9, 3.5, 4.2, 5.0, 6.0)
RING_ANGLES = 12
STUB_PATHS = 9  # straight, both corners, then the first sweeps
THERMAL_PAD_MM = 1.2  # a pad this wide both ways takes stitching vias
MAZE_PAIRS = 6  # pairs offered to the maze once the simple joints fail


def _layers_of_pad(pad):
    return ("F.Cu", "B.Cu") if pad.tht else ("F.Cu",)


class _Obstacles:
    """Foreign copper per layer, indexed for fast clearance queries."""

    def __init__(self, pads, tracks, vias):
        self.items = {"F.Cu": [], "B.Cu": []}
        for q in pads:
            g = box(q.x - q.w / 2, q.y - q.h / 2, q.x + q.w / 2, q.y + q.h / 2)
            name = q.net or f"NC:{q.ref}.{q.number}"
            for la in _layers_of_pad(q):
                self.items[la].append((name, g))
        for net, w, pts, layer in tracks:
            self.items[layer].append((net, LineString(pts).buffer(w / 2.0)))
        for net, x, y in vias:
            g = Point(x, y).buffer(VIA_R)
            self.items["F.Cu"].append((net, g))
            self.items["B.Cu"].append((net, g))
        self.pads = list(pads)
        self.pad_boxes = [
            box(q.x - q.w / 2, q.y - q.h / 2, q.x + q.w / 2, q.y + q.h / 2) for q in pads
        ]
        self.pad_tree = STRtree(self.pad_boxes)
        self._trees = {}
        self._geoms = {}
        for la in ("F.Cu", "B.Cu"):
            self._rebuild(la)

    def _rebuild(self, layer):
        self._geoms[layer] = self.items[layer]
        self._trees[layer] = STRtree([g for _, g in self.items[layer]])

    def clear_of_foreign(self, net, layer, geom) -> bool:
        tree = self._trees[layer]
        for idx in tree.query(geom.buffer(CLEAR)):
            oname, og = self._geoms[layer][int(idx)]
            if oname != net and geom.distance(og) < CLEAR:
                return False
        return True

    def via_ok(self, net, x, y) -> bool:
        disc = Point(x, y).buffer(VIA_R)
        if not (
            EDGE + VIA_R - W_JOIN / 2 <= x <= 100.0 - EDGE - VIA_R + W_JOIN / 2
            and EDGE + VIA_R - W_JOIN / 2 <= y <= 62.0 - EDGE - VIA_R + W_JOIN / 2
        ):
            return False
        for la in ("F.Cu", "B.Cu"):
            if not self.clear_of_foreign(net, la, disc):
                return False
        # never inside a pad the paste will cover, its own included; a
        # thermal pad is the exception the datasheets ask for, its
        # stitching vias are how the heat and the ground get out
        for idx in self.pad_tree.query(disc):
            k = int(idx)
            if disc.intersection(self.pad_boxes[k]).area <= 1e-9:
                continue
            q = self.pads[k]
            if q.net == net and not q.tht and min(q.w, q.h) >= THERMAL_PAD_MM:
                continue
            return False
        return True

    def add_track(self, net, pts, layer):
        self.items[layer].append((net, LineString(pts).buffer(W_JOIN / 2.0)))
        self._rebuild(layer)

    def add_via(self, net, x, y):
        g = Point(x, y).buffer(VIA_R)
        for la in ("F.Cu", "B.Cu"):
            self.items[la].append((net, g))
            self._rebuild(la)


def _in_board(pts) -> bool:
    return all(EDGE <= x <= 100.0 - EDGE and EDGE <= y <= 62.0 - EDGE for x, y in pts)


def _piece_bounds(piece):
    """The box around a piece, from its sides, without unioning them."""
    sides = [g.bounds for g in piece if g is not None and not g.is_empty]
    return (
        min(b[0] for b in sides),
        min(b[1] for b in sides),
        max(b[2] for b in sides),
        max(b[3] for b in sides),
    )


def _net_pieces(net, pads, tracks, vias, islands=None):
    """Connected components of a net's copper, per layer and exact.

    The same bookkeeping the build checks against (`connect.net_parts`),
    so the pass sees a gap exactly when KiCad would: copper touching on
    a shared layer, a via joining the two, and, for the ground, the
    islands its pour really fills. Pieces made of pour alone are dropped
    by the filler and owe nothing.
    """
    parts = connect.net_parts(net, pads, tracks, vias, 2 * VIA_R, islands)
    return [(front, back) for front, back, anchored in parts if anchored]


def _f_paths(pa, pb):
    """Candidate polylines from pa to pb on one layer, simplest first."""
    (xa, ya), (xb, yb) = pa, pb
    yield [pa, pb]
    if abs(xa - xb) > 1e-6 and abs(ya - yb) > 1e-6:
        yield [pa, (xb, ya), pb]
        yield [pa, (xa, yb), pb]
    for off in (
        0.2,
        -0.2,
        0.4,
        -0.4,
        0.6,
        -0.6,
        0.9,
        -0.9,
        1.3,
        -1.3,
        1.8,
        -1.8,
        2.4,
        -2.4,
        3.2,
        -3.2,
        4.0,
        -4.0,
        4.8,
        -4.8,
        5.6,
        -5.6,
        6.4,
        -6.4,
    ):
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


def _layer_join(net, layer, pa, pb, ga_true, gb_true, obs):
    """One-layer joint from pa to pb touching both true geometries."""
    for pts in _f_paths(pa, pb):
        if not _in_board(pts):
            continue
        g = LineString(pts).buffer(W_JOIN / 2.0)
        if ga_true is not None and g.distance(ga_true) > 1e-9:
            continue
        if gb_true is not None and g.distance(gb_true) > 1e-9:
            continue
        if obs.clear_of_foreign(net, layer, g):
            return [("T", pts, layer)]
    return None


def _stub_via(net, p, contact_true, obs):
    """Legal F stub from p to a nearby via; yields (plan, via_xy).

    The stub turns a corner when the straight line is taken: a ground
    pad boxed in on one side still reaches a spot the pour can hold.
    """
    for v in _ring(p):
        if not obs.via_ok(net, *v):
            continue
        for stub in islice(_f_paths(p, v), STUB_PATHS):
            if not _in_board(stub):
                continue
            g = LineString(stub).buffer(W_JOIN / 2.0)
            if not obs.clear_of_foreign(net, "F.Cu", g):
                continue
            if contact_true is not None and g.distance(contact_true) > 1e-9:
                continue
            yield [("T", stub, "F.Cu"), ("V", v, None)], v
            break


def _try_single_via(net, pa, pb_true_b, fa, obs):
    """F stub + via on side A, back-side run straight onto B copper."""
    for head, va in _stub_via(net, pa, fa, obs):
        p2 = nearest_points(Point(va), pb_true_b)[1]
        for run in _f_paths(va, (p2.x, p2.y)):
            if not _in_board(run):
                continue
            gr = LineString(run).buffer(W_JOIN / 2.0)
            if gr.distance(pb_true_b) > 1e-9:
                continue
            if obs.clear_of_foreign(net, "B.Cu", gr):
                return head + [("T", run, "B.Cu")]
    return None


def _try_via_join(net, pa, pb, fa, fb, obs):
    """F stub, via, back-side run, via, F stub."""
    for head, va in _stub_via(net, pa, fa, obs):
        for tail_rev, vb in _stub_via(net, pb, fb, obs):
            if abs(va[0] - vb[0]) < 0.75 and abs(va[1] - vb[1]) < 0.75:
                continue
            for run in _f_paths(va, vb):
                if not _in_board(run):
                    continue
                gr = LineString(run).buffer(W_JOIN / 2.0)
                if obs.clear_of_foreign(net, "B.Cu", gr):
                    stub_b, via_b = tail_rev
                    return head + [("T", run, "B.Cu"), via_b, stub_b]
    return None


def _try_maze(net, piece_a, piece_b, pads, tracks, vias, obs):
    """The maze of the last resort, re-checked on the exact geometry."""
    plan = maze.maze_join(
        net, piece_a, piece_b, pads, tracks, vias, W_JOIN, CLEAR, VIA_R, THERMAL_PAD_MM
    )
    if plan is None:
        return None
    for kind, payload, layer in plan:
        if kind == "T":
            g = LineString(payload).buffer(W_JOIN / 2.0)
            if not _in_board(payload) or not obs.clear_of_foreign(net, layer, g):
                return None
        elif not obs.via_ok(net, *payload):
            return None
    return plan


def finish_pass(pads, tracks, vias, nets=None, islands=None) -> list[str]:
    """Close remaining gaps with exact-geometry joints.

    Mutates tracks and vias in place; returns log lines for the joints
    made. Never adds copper closer than CLEAR to any foreign copper.
    `nets` defaults to every signal net, the ground excluded: the ground
    is finished in a second call, once the pour is known, and its
    `islands` say what the filler really joins. Ground copper is not
    foreign to its own pour, so those joints never move it.
    """
    obs = _Obstacles(pads, tracks, vias)
    if nets is None:
        nets = sorted({q.net for q in pads if q.net and q.net != "GND"})
    log = []
    joints = 0
    for net in nets:
        for _ in range(MAX_ROUNDS):
            if joints >= MAX_JOINTS:
                return log
            pieces = _net_pieces(net, pads, tracks, vias, islands)
            if len(pieces) <= 1:
                break
            # every pair, nearest first: a pair the copper around it
            # forbids must not stop the pairs behind it. Pairs are
            # ranked on the boxes around the pieces, not on the copper:
            # a ground pour is a polygon of thousands of points and the
            # exact distance to it is only worth paying once a pair is
            # actually tried.
            boxes = [box(*_piece_bounds(pc)) for pc in pieces]
            pairs = sorted(
                (
                    (boxes[i].distance(boxes[j]), i, j)
                    for i in range(len(pieces))
                    for j in range(i + 1, len(pieces))
                ),
                key=lambda t: t[0],
            )[:MAX_PAIRS]
            whole: dict[int, object] = {}
            plan = None
            for _d, i, j in pairs:
                for k in (i, j):
                    if k not in whole:
                        whole[k] = unary_union([g for g in pieces[k] if g is not None])
                gi, gj = whole[i], whole[j]
                fa, ba = pieces[i]
                fb, bb = pieces[j]
                if fa is not None and fb is not None:
                    for pa in _contacts(fa, fb):
                        for pb in _contacts(fb, fa):
                            plan = _layer_join(net, "F.Cu", pa, pb, fa, fb, obs)
                            if plan:
                                break
                        if plan:
                            break
                if plan is None and ba is not None and bb is not None:
                    for pa in _contacts(ba, bb):
                        for pb in _contacts(bb, ba):
                            plan = _layer_join(net, "B.Cu", pa, pb, ba, bb, obs)
                            if plan:
                                break
                        if plan:
                            break
                if plan is None and fa is not None and bb is not None:
                    for pa in _contacts(fa, gj):
                        plan = _try_single_via(net, pa, bb, fa, obs)
                        if plan:
                            break
                if plan is None and fb is not None and ba is not None:
                    for pb in _contacts(fb, gi):
                        plan = _try_single_via(net, pb, ba, fb, obs)
                        if plan:
                            break
                if plan is None and fa is not None and fb is not None:
                    for pa in _contacts(fa, fb, n_extra=1):
                        for pb in _contacts(fb, fa, n_extra=1):
                            plan = _try_via_join(net, pa, pb, fa, fb, obs)
                            if plan:
                                break
                        if plan:
                            break
                if plan is not None:
                    break
            if plan is None:
                for _d, i, j in pairs[:MAZE_PAIRS]:
                    plan = _try_maze(net, pieces[i], pieces[j], pads, tracks, vias, obs)
                    if plan is not None:
                        break
            if plan is None:
                break
            for kind, payload, layer in plan:
                if kind == "T":
                    pts = [tuple(p) for p in payload]
                    tracks.append((net, W_JOIN, pts, layer))
                    obs.add_track(net, pts, layer)
                else:
                    x, y = payload
                    vias.append((net, x, y))
                    obs.add_via(net, x, y)
            joints += 1
            log.append(f"{net}: joint pose ({_d:.2f} mm)")
    return log
