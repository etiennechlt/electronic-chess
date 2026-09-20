"""Generic board builder.

A board is a Circuit (analoggen.circuit), a dict of placements, a few
seed tracks and pours, and a spec (size, layer count, rules). Every net
is routed by the multi-layer grid router of quadgen; GND pads reach the
ground pour by a short via drop found by the same router. The exact
clearance check of quadgen runs on the result and the open nets are
listed for pcbnew, like on the mockup analog board.
"""

from __future__ import annotations

import dataclasses
import functools
import math
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass, field

import numpy as np
from analoggen.circuit import Circuit, Part
from analoggen.fplib import Footprint, load_footprint, pad_abs_pos, place_footprint
from analoggen.symlib import load_symbol
from coilgen.kicad import Board
from coilgen.project import DesignRules
from quadgen.connect import (
    CHECK_SLOP_MM,
    close_net,
    connectivity_check,
    ground_drops,
    net_pieces,
    pad_copper,
    stub_copper,
    track_cells,
    trim_corridors,
)
from quadgen.escape import (
    FANOUT_VIA_DRILL_MM,
    FANOUT_VIA_PAD_MM,
    STUB_WIDTH_MM,
    claim_stubs,
    escape_stubs,
    free_stubs,
    plain_stub,
    reclaim_stubs,
    runway_end,
)
from quadgen.router import MultiRouter
from quadgen.strip import courtyard, courtyard_box, placed_box
from shapely.geometry import LineString, Point
from shapely.ops import nearest_points
from shapely.strtree import STRtree

LAYERS4 = ["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"]
LAYERS2 = ["F.Cu", "B.Cu"]


def pins_by_name(part: Part, mapping: dict[str, str], nc: tuple[str, ...] = ()) -> dict[str, str]:
    """Pin numbers from pin names of the official symbol: every pin whose
    name matches a key gets that net (several GND pins map at once).
    Names are matched case-insensitively, braces and tildes stripped."""
    sym = load_symbol(part.lib, part.symbol)

    def norm(name: str) -> str:
        return re.sub(r"[{}~\s]", "", name).upper()

    wanted = {norm(k): v for k, v in mapping.items()}
    out: dict[str, str] = {}
    seen: set[str] = set()
    for pin in sym.pins:
        key = norm(pin.name)
        if key in wanted:
            out[pin.number] = wanted[key]
            seen.add(key)
        elif norm(pin.number) in wanted:
            out[pin.number] = wanted[norm(pin.number)]
            seen.add(norm(pin.number))
    missing = set(wanted) - seen
    if missing:
        names = sorted({pin.name for pin in sym.pins})
        raise ValueError(f"{part.symbol}: pins {sorted(missing)} not found among {names}")
    return out


@dataclass
class Spec:
    name: str
    title: str
    width: float
    height: float
    layers: int = 2
    clearance: float = 0.2
    edge_clearance: float = 0.5
    track: float = 0.3
    power_track: float = 0.6
    via_pad: float = 0.8
    via_drill: float = 0.4
    grid: float = 0.15
    gnd_layer: str = "B.Cu"  # ground pour
    power_nets: tuple[str, ...] = ()
    outer_cost: float = 1.2


@dataclass
class Track:
    net: str
    layer: str
    width: float
    pts: list[tuple[float, float]]
    # the lines written to the board file, so a rip-up can lift the item
    body: list[str] = field(default_factory=list, compare=False, repr=False)


@dataclass
class Via:
    net: str
    x: float
    y: float
    pad: float
    drill: float
    body: list[str] = field(default_factory=list, compare=False, repr=False)


@dataclass
class PadItem:
    net: str
    layer: str
    x: float
    y: float
    w: float
    h: float
    rot: float
    ref: str
    number: str
    drill: float = 0.0  # plated hole of a through pad, 0 for SMD
    shape: str = "rect"  # KiCad pad shape: rect, roundrect, oval, circle, custom
    rratio: float = 0.0  # corner radius of a roundrect pad over its smaller side


HOLE_TO_HOLE_MM = 0.25  # fabrication: drill edge to drill edge
PAD_GUARD_MM = 0.1  # free ring the lattice keeps around an SMD pad, beyond the clearance
POUR_REACH_MM = 0.9  # free lattice around a ground drop so the pour reaches it
# rip-up and reroute (GenericBoard.reroute_walled): how many rounds, the
# budget of a route in them, and how far around the pieces of a net still
# open the routes of its neighbours count as its walls
RIP_UP_ROUNDS = 3
RIP_UP_NODES = 2_000_000
RIP_UP_REACH_MM = 0.6


@dataclass
class Result:
    board: Board
    spec: Spec
    circuit: Circuit
    placements: dict
    tracks: list[Track] = field(default_factory=list)
    vias: list[Via] = field(default_factory=list)
    pads: list[PadItem] = field(default_factory=list)
    holes: list[tuple[float, float, float]] = field(default_factory=list)
    open_nets: list[str] = field(default_factory=list)
    routed_nets: int = 0
    clearance_errors: list[str] = field(default_factory=list)
    unconnected: list[str] = field(default_factory=list)  # nets in pieces after routing
    finish_log: list[str] = field(default_factory=list)  # joints of the finishing pass
    rip_up_log: list[str] = field(default_factory=list)  # rounds of rip-up and reroute


class GenericBoard:
    def __init__(
        self,
        spec: Spec,
        circuit: Circuit,
        placements: dict[str, tuple[float, float, float]],
        generator: str = "boardgen",
        overhang: tuple[str, ...] = (),
        courtyards: dict[str, tuple[float, float, float, float]] | None = None,
        plain_fanout: tuple[str, ...] = (),
    ) -> None:
        self.spec = spec
        # fine-pitch parts whose stubs get no fanout via: their escapes are
        # drawn by hand as seeds (a connector row fanned out on the top layer)
        self.plain_fanout = set(plain_fanout)
        self.circuit = circuit
        self.placements = placements
        # parts whose courtyard may leave the board: a radio module whose
        # antenna, and the clearance area around it, hang past the edge
        self.overhang = set(overhang)
        # reference -> (x0, y0, x1, y1) in the footprint frame, replacing the
        # library courtyard on the board and in the checks (a deliberately
        # reduced antenna clearance, stated where it is decided)
        self.courtyards = dict(courtyards or {})
        self.layers = LAYERS4 if spec.layers == 4 else LAYERS2
        self.board = Board(
            thickness_mm=1.6, title=spec.title, copper_layers=spec.layers, generator=generator
        )
        self.res = Result(board=self.board, spec=spec, circuit=circuit, placements=placements)
        self.by_ref = {c.ref: c for c in circuit.components}
        self.seeds: list[tuple[str, str, float, list]] = []
        self.seed_vias: list[tuple[str, float, float, float | None, float | None]] = []
        self.stubs: list[tuple[str, list, float, bool]] = []
        # fanout exits continue on the first inner signal layer (or the back)
        self.exit_layer = "In2.Cu" if "In2.Cu" in self.layers else self.layers[-1]
        self.keepouts: list[tuple[float, float, float]] = []  # x, y, radius, all layers
        self.keepout_rects: list[tuple[float, float, float, float, str]] = []  # x0 y0 x1 y1 name

    # ------------------------------------------------------------ emitters
    def track(self, net: str, layer: str, pts, width: float) -> Track:
        pts = [(float(x), float(y)) for x, y in pts]
        n0 = len(self.board.body)
        self.board.polyline(pts, width, layer, self.board.net(net))
        item = Track(net, layer, width, pts, body=self.board.body[n0:])
        self.res.tracks.append(item)
        return item

    def via(
        self, net: str, x: float, y: float, pad: float | None = None, drill: float | None = None
    ) -> Via | None:
        """A via, unless one of the same net already overlaps it (the router
        restarts from a fanout via and may put its own next to it): two
        overlapping pads are one piece of copper, and two drills that
        close are a fabrication error. Returns the via placed, None when
        an existing one stands for it."""
        pad = self.spec.via_pad if pad is None else pad
        drill = self.spec.via_drill if drill is None else drill
        for v in self.res.vias:
            reach = (v.pad + pad) / 2.0 - 0.02
            if v.net == net and (v.x - x) ** 2 + (v.y - y) ** 2 <= reach * reach:
                return None
        n0 = len(self.board.body)
        self.board.via(x, y, pad, drill, self.board.net(net))
        item = Via(net, float(x), float(y), pad, drill, body=self.board.body[n0:])
        self.res.vias.append(item)
        return item

    def seed(self, net: str, layer: str, pts, width: float | None = None) -> None:
        """A track drawn by hand before routing: the router starts from it
        and connects the net's pads to it (an escape the lattice cannot
        find, a corridor kept free for a net routed late)."""
        self.seeds.append((net, layer, width or self.spec.power_track, list(pts)))

    def seed_via(
        self, net: str, x: float, y: float, pad: float | None = None, drill: float | None = None
    ) -> None:
        """A via drawn by hand before routing, part of the net's seed."""
        self.seed_vias.append((net, float(x), float(y), pad, drill))

    def hole(self, x: float, y: float, d: float, ref: str) -> None:
        self.board.npth_hole(x, y, d, ref=ref)
        self.res.holes.append((x, y, d))

    def footprint(self, comp) -> Footprint:
        """The component's footprint, its courtyard replaced when overridden."""
        fp = load_footprint(comp.part.footprint)
        if comp.ref not in self.courtyards:
            return fp
        x0, y0, x1, y1 = self.courtyards[comp.ref]
        raw = _strip_courtyard(fp.raw)
        rect = (
            f"  (fp_rect (start {x0:g} {y0:g}) (end {x1:g} {y1:g}) "
            '(stroke (width 0.05) (type default)) (fill none) (layer "F.CrtYd"))\n'
        )
        return dataclasses.replace(fp, raw=raw.rstrip()[:-1] + rect + ")\n")

    def place_all(self) -> None:
        missing = [c.ref for c in self.circuit.components if c.ref not in self.placements]
        if missing:
            raise ValueError(f"unplaced components: {missing}")
        pending: list = []
        for comp in self.circuit.components:
            x, y, rot = self.placements[comp.ref]
            fp = self.footprint(comp)
            nets = {num: (self.board.net(n), n) for num, n in comp.pins.items()}
            self.board.body.append(place_footprint(fp, comp.ref, comp.value, x, y, rot, nets))
            for pad in fp.pads:
                px, py = pad_abs_pos(x, y, rot, pad)
                sw, sh = pad.size
                net = comp.pins.get(pad.number, "")
                drill = pad.drill if pad.kind == "thru_hole" and pad.drill else 0.0
                for layer in pad.layers:
                    if layer in self.layers or layer == "*.Cu":
                        item = PadItem(
                            net,
                            layer,
                            px,
                            py,
                            sw,
                            sh,
                            rot + pad.rot,
                            comp.ref,
                            pad.number,
                            drill,
                            pad.shape,
                            pad.rratio,
                        )
                        self.res.pads.append(item)
                        break
                if pad.kind == "np_thru_hole" and pad.drill:
                    self.res.holes.append((px, py, pad.drill))
            stubs = escape_stubs(fp, x, y, rot, dict(comp.pins))
            if comp.ref in self.plain_fanout:
                stubs = [plain_stub(st) for st in stubs]
            pending.extend(stubs)
        self._check_courtyards()
        sp = self.spec
        kept = free_stubs(
            pending, self.res, sp.clearance, board=(sp.width, sp.height, sp.edge_clearance)
        )
        if len(kept) != len(pending):
            print(f"escape stubs: {len(kept)} of {len(pending)} drawn", file=sys.stderr)
        for net, _num, pts, runway, via in kept:
            self.track(net, "F.Cu", pts, STUB_WIDTH_MM)
            if via:
                end = runway_end(pts, runway)
                self.track(net, "F.Cu", [pts[1], end], STUB_WIDTH_MM)
                self.via(net, end[0], end[1], FANOUT_VIA_PAD_MM, FANOUT_VIA_DRILL_MM)
            self.stubs.append((net, pts, runway, via))

    def _check_courtyards(self) -> None:
        boxes = []
        for comp in self.circuit.components:
            x, y, rot = self.placements[comp.ref]
            x0, y0, x1, y1 = placed_box(self.footprint(comp), x, y, rot)
            boxes.append((comp.ref, x0, y0, x1, y1))
            if comp.ref in self.overhang:
                continue
            if x0 < 0 or y0 < 0 or x1 > self.spec.width or y1 > self.spec.height:
                raise ValueError(f"{comp.ref} courtyard leaves the board")
        for i, a in enumerate(boxes):
            for b in boxes[i + 1 :]:
                if (
                    a[1] < b[3] - 0.01
                    and b[1] < a[3] - 0.01
                    and a[2] < b[4] - 0.01
                    and b[2] < a[4] - 0.01
                ):
                    raise ValueError(f"courtyards overlap: {a[0]} and {b[0]}")

    # ------------------------------------------------------------ routing
    def _new_router(self, track_half: float) -> MultiRouter:
        sp = self.spec
        mr = MultiRouter(
            self.layers,
            0.0,
            0.0,
            sp.width,
            sp.height,
            sp.grid,
            sp.clearance,
            sp.via_pad,
            track_half=track_half,
            outer_cost=sp.outer_cost,
            plane_layers=(sp.gnd_layer,) if len(self.layers) > 2 else (),
            h_weight=1.3,
        )
        m = int(sp.edge_clearance / sp.grid) + 3
        for la in self.layers:
            for arr in (mr.own[la], mr.own_via[la]):
                arr[:, :m] = MultiRouter.MULTI
                arr[:, -m:] = MultiRouter.MULTI
                arr[:m, :] = MultiRouter.MULTI
                arr[-m:, :] = MultiRouter.MULTI
        for t in self.res.tracks:
            for a, b in zip(t.pts, t.pts[1:], strict=False):
                mr.segment(t.net, t.layer, a[0], a[1], b[0], b[1], t.width)
        for v in self.res.vias:
            mr.disc(v.net, self.layers, v.x, v.y, v.pad / 2.0)
        for p in self.res.pads:
            layers = self.layers if p.layer == "*.Cu" else [p.layer]
            net = p.net or ("__nc__" + p.ref + p.number)
            # an SMD pad keeps a guard ring beyond the clearance: a track
            # hugging it at the bare clearance walls it in, and its own
            # escape (a thin stub to a via) then fits nowhere
            guard = 0.0 if p.drill else PAD_GUARD_MM
            mr.rect(net, layers, p.x, p.y, p.w + 2.0 * guard, p.h + 2.0 * guard, p.rot)
            if p.drill:
                # a via of the pad's own net may touch its copper, never its hole
                mr.via_keepout(p.x, p.y, p.drill / 2.0 + sp.via_drill / 2.0 + HOLE_TO_HOLE_MM)
        for hx, hy, hd in self.res.holes:
            mr.keepout(hx, hy, hd / 2.0 + 0.3 + sp.clearance + 0.1)
        for x, y, r in self.keepouts:
            mr.keepout(x, y, r)
        for x0, y0, x1, y1, _name in self.keepout_rects:
            # owned by a net nobody routes: blocked for every real net
            mr.rect("__keepout__", self.layers, (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0)
        claim_stubs(mr, self.stubs, exit_layer=self.exit_layer)
        return mr

    def keepout_rect(self, x0: float, y0: float, x1: float, y1: float, name: str) -> None:
        """Copper-free rule area on every layer (antenna of a radio module)."""
        self.keepout_rects.append((x0, y0, x1, y1, name))
        self.board.keepout_zone(self.layers, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], name)

    def route_all(
        self,
        gnd: str = "GND",
        max_nodes: int = 1_500_000,
        only: set[str] | None = None,
        first: tuple[str, ...] = (),
    ) -> None:
        """Power nets first on a lattice inflated for the wide track, then
        the signals on a lattice inflated for the thin one; every result is
        painted into both so the two views never disagree. `first` names
        nets routed before every other (a net the fanout of its package
        walls in once its neighbours are out). Every net is a set of
        pieces of copper (quadgen.connect) joined one route at a time.
        What the round leaves in pieces gets the rip-up rounds of
        `reroute_walled` (BOARDGEN_RIP_UP=0 skips them)."""
        sp = self.spec
        self.route_first = tuple(first)
        self._gnd = gnd
        self._seed_tracks = {}
        self._routed = {}
        for net, layer, width, pts in self.seeds:
            self._seed_tracks.setdefault(net, []).append(self.track(net, layer, pts, width))
        for net, x, y, pad, drill in self.seed_vias:
            self.via(net, x, y, pad, drill)
        # the exit corridors of the fanout vias, cut to what the copper drawn
        # so far leaves legal on the exit layer (a via of another net beside)
        foreign = [(n, g) for n, la, g in self._copper_items() if la == self.exit_layer]
        self.stubs = trim_corridors(
            self.stubs, foreign, sp.clearance, sp.track, margin=1.5 * sp.grid
        )
        routers = {
            "power": self._new_router(sp.power_track / 2.0),
            "signal": self._new_router(sp.track / 2.0),
        }
        self._routers = routers  # kept for inspection after a run
        # BOARDGEN_MAX_NODES overrides the budget of a route
        max_nodes = int(os.environ.get("BOARDGEN_MAX_NODES", max_nodes))
        self._route_round(routers, gnd, max_nodes, only, ground=True)
        if os.environ.get("BOARDGEN_RIP_UP", "1") != "0":
            self.reroute_walled(gnd)
        self._gnd_pour(gnd)

    def _route_round(
        self,
        routers: dict[str, MultiRouter],
        gnd: str,
        max_nodes: int,
        only: set[str] | None,
        ground: bool,
        lead: tuple[str, ...] = (),
    ) -> None:
        """One round of the lattice router over `only` (every net with
        pads when None): the ground drops first when `ground`, then
        `lead`, the nets named `first` by `route_all`, the nets leaving a
        fine-pitch package, the power nets, the rest, shortest span first
        inside each group. The copper each route draws is remembered per
        net, so a rip-up can lift it again."""
        sp = self.spec
        ref = routers["signal"]
        pads_of: dict[str, list[PadItem]] = {}
        for p in self.res.pads:
            if p.net:
                pads_of.setdefault(p.net, []).append(p)
        tracks_of: dict[str, list[Track]] = {}
        for t in self.res.tracks:
            tracks_of.setdefault(t.net, []).append(t)
        vias_of: dict[str, list[Via]] = {}
        for v in self.res.vias:
            vias_of.setdefault(v.net, []).append(v)
        # the pieces of copper of every net: a pad with its escape stub, a
        # seed drawn by hand, a bus; the component of the first seed leads
        pieces_of = {
            net: net_pieces(
                ref,
                self.layers,
                pads,
                tracks_of.get(net, []),
                vias_of.get(net, []),
                self.stubs,
                self.exit_layer,
                first=self._seed_tracks.get(net, []),
            )
            for net, pads in pads_of.items()
            if only is None or net in only or net == gnd
        }
        # like the stubs, a seed keeps its own cells whatever the neighbours'
        # inflation says: a fan drawn by hand at the pad pitch is legal for
        # the exact rule, not for the lattice, whose slack exceeds the pitch
        seed_claims = [
            (net, layer, track_cells(ref, pts)) for net, layer, _w, pts in self.seeds
        ] + [
            (net, la, [ref.cell(x, y)])
            for net, x, y, _pad, _drill in self.seed_vias
            for la in self.layers
        ]

        def reclaim_seeds(mr):
            for net, la, cells in seed_claims:
                nid = mr.nid(net)
                own = mr.own[la]
                for i, j in cells:
                    own[j, i] = nid

        for mr in routers.values():
            reclaim_seeds(mr)
        # the escape stubs of every net: a route that lands on a plain runway
        # or in the exit corridor of a fanout via owes them their copper
        stubs_of: dict[str, list] = {}
        for stub in self.stubs:
            stubs_of.setdefault(stub[0], []).append(stub)

        def span(net):
            pts = [(p.x, p.y) for p in pads_of[net]]
            return (max(x for x, _ in pts) - min(x for x, _ in pts)) + (
                max(y for _, y in pts) - min(y for _, y in pts)
            )

        def paint(net, tracks, vias, width):
            for mr in routers.values():
                for la, pts in tracks:
                    for a, b in zip(pts, pts[1:], strict=False):
                        mr.segment(net, la, a[0], a[1], b[0], b[1], width)
                for x, y in vias:
                    mr.disc(net, self.layers, x, y, sp.via_pad / 2.0)
                reclaim_stubs(mr, self.stubs, exit_layer=self.exit_layer)
                reclaim_seeds(mr)

        def usable(mr, net, cells):
            nid = mr.nid(net)
            return sum(
                1 for la, cs in cells.items() for i, j in cs if mr.own[la][j, i] in (mr.FREE, nid)
            )

        def legal(mr, net, cells):
            """The cells of a piece a route may start or end on now: those
            the net owns or nobody does (a corridor cell another net's route
            has taken since would put the stub copper against it)."""
            nid = mr.nid(net)
            return {
                la: {(i, j) for i, j in cs if mr.own[la][j, i] in (mr.FREE, nid)}
                for la, cs in cells.items()
            }

        def attempt(net, starts, goals, drop=False):
            """One route of `net` between two sets of cells, drawn and
            painted when legal: wide on the power lattice for a power net,
            thin again when the wide track finds no way or brushes a pad
            or a stub of the fine-pitch package it leaves. A ground drop
            is thin and short."""
            power = net in sp.power_nets and not drop
            mr = routers["power"] if power else routers["signal"]
            width = sp.power_track if power else sp.track
            budget = 120_000 if drop else max_nodes
            starts, goals = legal(mr, net, starts), legal(mr, net, goals)
            found = mr.route(net, starts, goals, max_nodes=budget)
            if found is None and power:
                # a wide track cannot reach a fine-pitch pad: finish thin
                mr, width = routers["signal"], sp.track
                found = mr.route(net, starts, goals, max_nodes=max_nodes)
            if found is None:
                return (
                    f"no route (usable start cells {usable(mr, net, starts)}, "
                    f"goal cells {usable(mr, net, goals)})"
                )
            tracks, vias = found
            clash = self._route_clash(net, tracks, vias, width)
            if clash and mr is routers["power"]:
                mr, width = routers["signal"], sp.track
                found = mr.route(net, starts, goals, max_nodes=max_nodes)
                if found is not None:
                    tracks, vias = found
                    clash = self._route_clash(net, tracks, vias, width)
            if clash:
                # the lattice is conservative but not exact: a route that
                # would fail the real clearance is dropped, never drawn
                return f"route rejected, {clash}"
            exits = stub_copper(mr, self.exit_layer, tracks, vias, stubs_of.get(net, []))
            clash = self._route_clash(net, exits, [], STUB_WIDTH_MM) if exits else None
            if clash:
                return f"stub copper blocked, {clash}"
            drawn = [self.track(net, la, pts, width) for la, pts in tracks]
            drawn += [self.track(net, la, pts, STUB_WIDTH_MM) for la, pts in exits]
            placed = [v for v in (self.via(net, x, y) for x, y in vias) if v is not None]
            self._routed.setdefault(net, []).append((drawn, placed))
            paint(net, tracks, vias, width)
            if exits:
                paint(net, exits, [], STUB_WIDTH_MM)
            return tracks, vias, mr

        nets = [n for n in pads_of if only is None or n in only]
        power = [n for n in nets if n in sp.power_nets and n != gnd]
        signals = [n for n in nets if n not in sp.power_nets and n != gnd]
        # nets leaving a fine-pitch package first, while the board is empty
        # around it (routed later they end up walled in by the power
        # tracks), then the power nets, then the rest; shortest span first
        # inside each group
        fine = {stub[0] for stub in self.stubs}
        first_nets = [n for n in signals if n in fine]
        rest = [n for n in signals if n not in fine]
        order = sorted(first_nets, key=span) + sorted(power, key=span) + sorted(rest, key=span)
        ahead = [n for n in lead if n in order] + [
            n for n in self.route_first if n in order and n not in lead
        ]
        order = ahead + [n for n in order if n not in ahead]
        if ground and sp.gnd_layer in self.layers:
            # Ground first: every piece of it without copper on the pour's
            # layer gets its short drop while the board is still empty. A
            # decoupling capacitor whose ground via is placed last is a
            # capacitor with no ground: its neighbours have walled it in.
            ground_drops(
                routers["signal"],
                gnd,
                pieces_of.get(gnd, []),
                sp.gnd_layer,
                int(round(POUR_REACH_MM / sp.grid)),
                functools.partial(attempt, gnd, drop=True),
                self.res.open_nets,
            )
            self.res.routed_nets += 1
        for net in order:
            pieces = pieces_of[net]
            if len(pieces) < 2:
                if len(pads_of[net]) >= 2:
                    self.res.routed_nets += 1  # one piece already
                continue
            if close_net(net, pieces, functools.partial(attempt, net), self.res.open_nets):
                self.res.routed_nets += 1

    # ---------------------------------------------------- rip-up and reroute
    def _nets_in_pieces(self, gnd: str) -> set[str]:
        """The nets the exact connectivity check finds in pieces now."""
        sp = self.spec
        pours = {gnd: sp.gnd_layer} if sp.gnd_layer in self.layers else None
        lines = connectivity_check(
            self.res.tracks, self.res.vias, self.res.pads, self.layers, pours=pours
        )
        return {line.split(":", 1)[0] for line in lines}

    def _blockers(self, mr: MultiRouter, net: str, reach: int) -> set[str]:
        """The nets whose copper owns the lattice within `reach` cells of
        the pieces of `net`: what walls it in, on the signal lattice."""
        names = {v: k for k, v in mr.net_ids.items()}
        nid = mr.nid(net)
        pieces = net_pieces(
            mr,
            self.layers,
            [p for p in self.res.pads if p.net == net],
            [t for t in self.res.tracks if t.net == net],
            [v for v in self.res.vias if v.net == net],
            self.stubs,
            self.exit_layer,
            first=self._seed_tracks.get(net, []),
        )
        owners: set[int] = set()
        for pc in pieces:
            for la, cells in pc.cells.items():
                own = mr.own[la]
                for i, j in cells:
                    window = own[
                        max(0, j - reach) : j + reach + 1, max(0, i - reach) : i + reach + 1
                    ]
                    owners.update(int(v) for v in np.unique(window) if v >= 0 and v != nid)
        return {names[k] for k in owners if k in names and not names[k].startswith("__")}

    def _lift(self, nets: set[str]) -> None:
        """Removes every route the rounds drew for `nets`, from the result
        and from the board file; seeds, escape stubs and pads stay."""
        tracks: list[Track] = []
        vias: list[Via] = []
        for net in nets:
            for drawn, placed in self._routed.pop(net, []):
                tracks += drawn
                vias += placed
        gone_t = {id(t) for t in tracks}
        gone_v = {id(v) for v in vias}
        self.res.tracks = [t for t in self.res.tracks if id(t) not in gone_t]
        self.res.vias = [v for v in self.res.vias if id(v) not in gone_v]
        counts = Counter(line for item in tracks + vias for line in getattr(item, "body", ()))
        body = []
        for line in self.board.body:
            if counts.get(line, 0) > 0:
                counts[line] -= 1
                continue
            body.append(line)
        self.board.body = body
        if hasattr(self, "_items_cache"):
            delattr(self, "_items_cache")

    def reroute_walled(
        self, gnd: str, rounds: int = RIP_UP_ROUNDS, max_nodes: int = RIP_UP_NODES
    ) -> None:
        """Rip-up and reroute for what the round left in pieces. A net
        still in pieces is usually walled in: the routes of its neighbours,
        laid earlier, own the lattice around one of its pads (the corridor
        of a fine-pitch pin, a resistor between two vias), and no budget
        finds a way that does not exist. One net at a time: its routes and
        those of the routed neighbours owning the lattice within
        RIP_UP_REACH_MM of its pieces are lifted (seeds, escape stubs,
        ground drops, the power nets and the nets routed first stay) and
        routed again on the board as it is, the net first, with a larger
        budget; the lift is kept when fewer nets are in pieces after it,
        undone otherwise. Up to `rounds` sweeps over the nets in pieces,
        stopped by a sweep that closes nothing; `res.rip_up_log` tells
        what each lift did."""
        sp = self.spec
        reach = int(round(RIP_UP_REACH_MM / sp.grid))
        fixed = {gnd, *sp.power_nets, *self.route_first}
        for k in range(1, rounds + 1):
            open_nets = self._nets_in_pieces(gnd) - {gnd}
            if not open_nets:
                return
            count = len(open_nets)
            for net in sorted(open_nets):
                if net not in self._nets_in_pieces(gnd):
                    continue  # closed by an earlier lift of this sweep
                blockers = self._blockers(self._routers["signal"], net, reach) - fixed - {net}
                ripped = blockers | {net}
                saved = (
                    list(self.res.tracks),
                    list(self.res.vias),
                    list(self.board.body),
                    {n: list(r) for n, r in self._routed.items()},
                    list(self.res.open_nets),
                    self._routers,
                )
                self._lift(ripped)
                self.res.open_nets = [
                    line for line in self.res.open_nets if line.split(":", 1)[0] not in ripped
                ]
                routers = {
                    "power": self._new_router(sp.power_track / 2.0),
                    "signal": self._new_router(sp.track / 2.0),
                }
                self._routers = routers
                self._route_round(routers, gnd, max_nodes, ripped, ground=False, lead=(net,))
                after = len(self._nets_in_pieces(gnd) - {gnd})
                line = (
                    f"rip-up {k}, {net}: {len(blockers)} neighbour(s) lifted "
                    f"({', '.join(sorted(blockers))}), nets in pieces {count} -> {after}"
                )
                if after >= count:
                    tracks, vias, body, routed, kept, routers = saved
                    self.res.tracks, self.res.vias, self.board.body = tracks, vias, body
                    self._routed, self.res.open_nets, self._routers = routed, kept, routers
                    if hasattr(self, "_items_cache"):
                        delattr(self, "_items_cache")
                    self.res.rip_up_log.append(line + ", undone")
                    continue
                count = after
                self.res.rip_up_log.append(line)
            if count >= len(open_nets):
                return

    def _gnd_pour(self, gnd: str) -> None:
        sp = self.spec
        e = sp.edge_clearance
        self.board.zone(
            self.board.net(gnd),
            gnd,
            sp.gnd_layer,
            [(e, e), (sp.width - e, e), (sp.width - e, sp.height - e), (e, sp.height - e)],
            clearance_mm=sp.clearance + 0.1,
        )

    # ------------------------------------------------------------ checks
    def _copper_items(self) -> list[tuple[str, str, object]]:
        """(net, layer, geometry) of every copper item drawn so far."""
        items = []
        for t in self.res.tracks:
            items.append((t.net, t.layer, LineString(t.pts).buffer(t.width / 2.0)))
        for v in self.res.vias:
            for layer in self.layers:
                items.append((v.net, layer, Point(v.x, v.y).buffer(v.pad / 2.0)))
        for p in self.res.pads:
            layers = self.layers if p.layer == "*.Cu" else [p.layer]
            g = pad_copper(p)
            for layer in layers:
                items.append((p.net or f"__nc_{p.ref}_{p.number}", layer, g))
        for hx, hy, hd in self.res.holes:
            for layer in self.layers:
                items.append(("__hole__", layer, Point(hx, hy).buffer(hd / 2.0 + 0.3)))
        return items

    def _route_clash(self, net: str, tracks, vias, width: float) -> str | None:
        """Exact clearance of a candidate route against the copper drawn so
        far; returns a description of the first clash, or None."""
        clr = self.spec.clearance - CHECK_SLOP_MM
        new = []
        for la, pts in tracks:
            new.append((la, LineString(pts).buffer(width / 2.0)))
        for x, y in vias:
            for la in self.layers:
                new.append((la, Point(x, y).buffer(self.spec.via_pad / 2.0)))
        if not hasattr(self, "_items_cache") or self._items_cache[0] != len(self.res.tracks) + len(
            self.res.vias
        ):
            items = self._copper_items()
            by_layer: dict[str, list] = {}
            for it in items:
                by_layer.setdefault(it[1], []).append(it)
            trees = {la: STRtree([g for _n, _l, g in its]) for la, its in by_layer.items()}
            self._items_cache = (len(self.res.tracks) + len(self.res.vias), by_layer, trees)
        _n, by_layer, trees = self._items_cache
        for la, g in new:
            if la not in trees:
                continue
            its = by_layer[la]
            for j in trees[la].query(g.buffer(clr)):
                other = its[int(j)]
                if other[0] == net:
                    continue
                d = g.distance(other[2])
                if d < clr:
                    c = nearest_points(g, other[2])[0]
                    return f"{la}: vs {other[0]} at ({c.x:.1f},{c.y:.1f}) gap {d:.3f}"
        return None

    def clearance_check(self) -> list[str]:
        sp = self.spec
        items = []
        for t in self.res.tracks:
            items.append((t.net, t.layer, LineString(t.pts).buffer(t.width / 2.0)))
        for v in self.res.vias:
            for layer in self.layers:
                items.append((v.net, layer, Point(v.x, v.y).buffer(v.pad / 2.0)))
        for p in self.res.pads:
            layers = self.layers if p.layer == "*.Cu" else [p.layer]
            g = pad_copper(p)
            for layer in layers:
                items.append((p.net or f"__nc_{p.ref}_{p.number}", layer, g))
        for hx, hy, hd in self.res.holes:
            for layer in self.layers:
                items.append(("__hole__", layer, Point(hx, hy).buffer(hd / 2.0 + 0.3)))
        errors = []
        by_layer: dict[str, list] = {}
        for it in items:
            by_layer.setdefault(it[1], []).append(it)
        clr = sp.clearance - CHECK_SLOP_MM
        for layer, its in by_layer.items():
            geoms = [g for _n, _l, g in its]
            tree = STRtree(geoms)
            for i, (net, _l, g) in enumerate(its):
                for j in tree.query(g.buffer(clr)):
                    j = int(j)
                    if j <= i or its[j][0] == net:
                        continue
                    if net.startswith("__") and its[j][0].startswith("__"):
                        continue  # a footprint's own unconnected pads around its holes
                    d = g.distance(geoms[j])
                    if d < clr:
                        c = nearest_points(g, geoms[j])[0]
                        errors.append(
                            f"{layer}: {net} vs {its[j][0]} at ({c.x:.1f},{c.y:.1f}) gap {d:.3f}"
                        )
        return sorted(set(errors))

    # ------------------------------------------------------------ finish
    def finish_routes(self, gnd: str = "GND") -> None:
        """Exact-geometry joints for what the lattice left open (the
        shared pass of `quadgen.finish`): the signal nets first, then the
        ground, whose pieces without copper on the pour's layer each get
        a drop. Everything drawn here is checked against the real
        clearance before it lands, like a route."""
        from quadgen.finish import Rules, finish_pass

        sp = self.spec
        plane = sp.gnd_layer if len(self.layers) > 2 else None
        rules = Rules(
            layers=tuple(self.layers),
            board=(sp.width, sp.height),
            edge=sp.edge_clearance,
            clearance=sp.clearance,
            width=sp.track,
            via=(sp.via_pad, sp.via_drill),
            plane=plane,
            hole_to_hole=HOLE_TO_HOLE_MM,
            thin=STUB_WIDTH_MM,
            small_via=(FANOUT_VIA_PAD_MM, FANOUT_VIA_DRILL_MM),
        )
        keepouts = [(x0, y0, x1, y1) for x0, y0, x1, y1, _name in self.keepout_rects]
        pour = (sp.gnd_layer, None) if sp.gnd_layer in self.layers else None
        log: list[str] = []
        for nets in (None, [gnd]):
            tracks = [(t.net, t.layer, t.width, t.pts) for t in self.res.tracks]
            vias = [(v.net, v.x, v.y, v.pad, v.drill) for v in self.res.vias]
            new_tracks, new_vias, lines = finish_pass(
                rules,
                self.res.pads,
                tracks,
                vias,
                self.res.holes,
                keepouts,
                nets=nets,
                pour=pour,
                pour_net=gnd,
            )
            for net, layer, width, pts in new_tracks:
                self.track(net, layer, pts, width)
            for net, x, y, pad, drill in new_vias:
                self.via(net, x, y, pad, drill)
            log += lines
        self.res.finish_log = log

    def finish(self, texts: list[tuple[str, float, float, str, float]] = ()) -> Result:
        self._texts = list(texts)
        self.dump(os.environ.get("BOARDGEN_DUMP"))
        return self._finish_tail()

    def dump(self, path: str | None) -> None:
        """Pickles the board once routed (BOARDGEN_DUMP=path): the finishing
        pass and the checks, seconds, can then be rerun from the file
        (`resume`) without the routing."""
        if not path:
            return
        import pickle

        if hasattr(self, "_items_cache"):
            delattr(self, "_items_cache")
        with open(path, "wb") as fh:
            pickle.dump(self, fh, protocol=pickle.HIGHEST_PROTOCOL)

    @classmethod
    def resume(cls, path: str) -> Result:
        """The build from a dump: finishing pass, outline, checks."""
        import pickle

        with open(path, "rb") as fh:
            gb = pickle.load(fh)
        return gb._finish_tail()

    def _finish_tail(self) -> Result:
        sp = self.spec
        self.board.gr_rect(0.0, 0.0, sp.width, sp.height, "Edge.Cuts")
        for text, x, y, layer, size in getattr(self, "_texts", ()):
            self.board.gr_text(text, x, y, layer, size)
        gnd = getattr(self, "_gnd", "GND")
        self.finish_routes(gnd)
        self.res.clearance_errors = self.clearance_check()
        pours = {gnd: sp.gnd_layer} if sp.gnd_layer in self.layers else None
        self.res.unconnected = connectivity_check(
            self.res.tracks, self.res.vias, self.res.pads, self.layers, pours=pours
        )
        # a net in pieces is open whatever the router believed, and a net
        # the finishing pass closed is closed whatever the router said
        still = {line.split(":", 1)[0] for line in self.res.unconnected}
        kept = [line for line in self.res.open_nets if line.split(":", 1)[0] in still]
        kept += list(self.res.unconnected)  # the pieces really left, after the pass
        self.res.open_nets = kept
        pads_of: dict[str, int] = {}
        for p in self.res.pads:
            if p.net:
                pads_of[p.net] = pads_of.get(p.net, 0) + 1
        self.res.routed_nets = sum(1 for n, k in pads_of.items() if k >= 2 and n not in still)
        return self.res


def _strip_courtyard(raw: str) -> str:
    """The footprint text without its F.CrtYd primitives."""
    out = []
    i = 0
    for m in re.finditer(r"\(fp_(?:line|rect|poly|circle|arc)\b", raw):
        if m.start() < i:
            continue
        depth, k = 0, m.start()
        while True:
            if raw[k] == "(":
                depth += 1
            elif raw[k] == ")":
                depth -= 1
                if depth == 0:
                    break
            k += 1
        block = raw[m.start() : k + 1]
        if "F.CrtYd" in block:
            out.append(raw[i : m.start()].rstrip(" \t"))
            i = k + 1
            if raw[i : i + 1] == "\n":
                i += 1
    out.append(raw[i:])
    return "".join(out)


def design_rules(spec: Spec) -> DesignRules:
    """What the DRC must accept: the router's tracks and vias, plus the
    fanout stubs and vias of the fine-pitch packages (the smallest items
    of the board) and the small plated holes of the radio module."""
    return DesignRules(
        clearance_mm=spec.clearance,
        track_width_mm=spec.track,
        via_diameter_mm=spec.via_pad,
        via_drill_mm=spec.via_drill,
        min_track_width_mm=min(spec.track, STUB_WIDTH_MM),
        min_via_diameter_mm=min(spec.via_pad, FANOUT_VIA_PAD_MM),
        min_hole_mm=min(spec.via_drill, FANOUT_VIA_DRILL_MM),
        edge_clearance_mm=spec.edge_clearance,
        track_widths_mm=(STUB_WIDTH_MM, spec.track, spec.power_track),
        via_sizes_mm=((spec.via_pad, spec.via_drill), (FANOUT_VIA_PAD_MM, FANOUT_VIA_DRILL_MM)),
    )


def shelf(
    refs: list[str],
    circuit: Circuit,
    x0: float,
    x1: float,
    y0: float,
    upright: bool = False,
    gap: float = 1.2,
) -> dict[str, tuple[float, float, float]]:
    """Shelf-pack the given references from their courtyards, `gap` apart
    so a via and its clearance fit between two neighbours."""
    from quadgen.strip import Box, shelf_pack

    by_ref = {c.ref: c for c in circuit.components}
    boxes = []
    fps: dict[str, Footprint] = {}
    for ref in refs:
        fps[ref] = fp = load_footprint(by_ref[ref].part.footprint)
        w, h = courtyard(fp)
        boxes.append(Box(ref, w + gap, h + gap, 0.0))
    packed = shelf_pack(boxes, x0, x1, y0, upright=upright)
    # the packer places courtyard centers; move each origin so that its
    # courtyard (whose center may be off the origin) lands there
    out = {}
    for ref, (x, y, rot) in packed.items():
        bx0, by0, bx1, by1 = courtyard_box(fps[ref])
        cx, cy = (bx0 + bx1) / 2.0, (by0 + by1) / 2.0
        th = math.radians(rot)
        px = cx * math.cos(th) + cy * math.sin(th)
        py = -cx * math.sin(th) + cy * math.cos(th)
        out[ref] = (round(x - px, 3), round(y - py, 3), rot)
    return out


def summary(res: Result) -> str:
    n = sum(len(t.pts) - 1 for t in res.tracks)
    return (
        f"{res.spec.name}: {len(res.circuit.components)} parts, {n} segments, "
        f"{len(res.vias)} vias, joints {len(res.finish_log)}, nets routed {res.routed_nets}, "
        f"open {len(res.open_nets)}, clearance errors {len(res.clearance_errors)}"
    )
