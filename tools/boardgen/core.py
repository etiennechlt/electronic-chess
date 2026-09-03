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
import math
import os
import re
import sys
from dataclasses import dataclass, field

from analoggen.circuit import Circuit, Part
from analoggen.fplib import Footprint, load_footprint, pad_abs_pos, place_footprint
from analoggen.symlib import load_symbol
from coilgen.kicad import Board
from coilgen.project import DesignRules
from quadgen.escape import (
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
from quadgen.router import MultiRouter
from quadgen.strip import courtyard, courtyard_box, placed_box
from shapely.geometry import LineString, Point, box
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
    rot: float
    ref: str
    number: str
    drill: float = 0.0  # plated hole of a through pad, 0 for SMD


HOLE_TO_HOLE_MM = 0.25  # fabrication: drill edge to drill edge
CHECK_SLOP_MM = 0.001  # numerical slop of the exact clearance checks


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


class GenericBoard:
    def __init__(
        self,
        spec: Spec,
        circuit: Circuit,
        placements: dict[str, tuple[float, float, float]],
        generator: str = "boardgen",
        overhang: tuple[str, ...] = (),
        courtyards: dict[str, tuple[float, float, float, float]] | None = None,
    ) -> None:
        self.spec = spec
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
        self.stubs: list[tuple[str, list, float, bool]] = []
        # fanout exits continue on the first inner signal layer (or the back)
        self.exit_layer = "In2.Cu" if "In2.Cu" in self.layers else self.layers[-1]
        self.keepouts: list[tuple[float, float, float]] = []  # x, y, radius, all layers
        self.keepout_rects: list[tuple[float, float, float, float, str]] = []  # x0 y0 x1 y1 name

    # ------------------------------------------------------------ emitters
    def track(self, net: str, layer: str, pts, width: float) -> None:
        pts = [(float(x), float(y)) for x, y in pts]
        self.board.polyline(pts, width, layer, self.board.net(net))
        self.res.tracks.append(Track(net, layer, width, pts))

    def via(
        self, net: str, x: float, y: float, pad: float | None = None, drill: float | None = None
    ) -> None:
        """A via, unless one of the same net already overlaps it (the router
        restarts from a fanout via and may put its own next to it): two
        overlapping pads are one piece of copper, and two drills that
        close are a fabrication error."""
        pad = self.spec.via_pad if pad is None else pad
        drill = self.spec.via_drill if drill is None else drill
        for v in self.res.vias:
            reach = (v.pad + pad) / 2.0 - 0.02
            if v.net == net and (v.x - x) ** 2 + (v.y - y) ** 2 <= reach * reach:
                return
        self.board.via(x, y, pad, drill, self.board.net(net))
        self.res.vias.append(Via(net, float(x), float(y), pad, drill))

    def seed(self, net: str, layer: str, pts, width: float | None = None) -> None:
        self.seeds.append((net, layer, width or self.spec.power_track, list(pts)))

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
                            net, layer, px, py, sw, sh, rot + pad.rot, comp.ref, pad.number, drill
                        )
                        self.res.pads.append(item)
                        break
                if pad.kind == "np_thru_hole" and pad.drill:
                    self.res.holes.append((px, py, pad.drill))
            pending.extend(escape_stubs(fp, x, y, rot, dict(comp.pins)))
        self._check_courtyards()
        kept = free_stubs(pending, self.res, self.spec.clearance)
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
            mr.rect(net, layers, p.x, p.y, p.w, p.h, p.rot)
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
        self, gnd: str = "GND", max_nodes: int = 1_500_000, only: set[str] | None = None
    ) -> None:
        """Power nets first on a lattice inflated for the wide track, then
        the signals on a lattice inflated for the thin one; every result is
        painted into both so the two views never disagree."""
        sp = self.spec
        for net, layer, width, pts in self.seeds:
            self.track(net, layer, pts, width)
        routers = {
            "power": self._new_router(sp.power_track / 2.0),
            "signal": self._new_router(sp.track / 2.0),
        }
        self._routers = routers  # kept for inspection after a run
        pad_cells: dict[str, list] = {}
        ref = routers["signal"]
        stub_at = {
            (round(pts[0][0], 2), round(pts[0][1], 2)): (pts, rw, via)
            for _n, pts, rw, via in self.stubs
        }
        for p in self.res.pads:
            if p.net == "":
                continue
            layers = self.layers if p.layer == "*.Cu" else [p.layer]
            for la in layers:
                cells = ref.cells_of_rect(p.x, p.y, p.w, p.h, p.rot)
                # an escape stub joins its pad's group: the router may start
                # or end anywhere along it, in particular at the free end
                stub = stub_at.get((round(p.x, 2), round(p.y, 2)))
                attached: list = []  # same group, other layers (fanout via)
                if stub is not None and la == "F.Cu":
                    pts, rw, via = stub
                    cells = cells + stub_cells(ref, pts, rw)
                    if via:
                        vc = ref.cell(*runway_end(pts, rw))
                        attached = [(other, [vc]) for other in self.layers if other != la]
                        attached.append((self.exit_layer, exit_cells(ref, pts, rw)))
                if cells:
                    pad_cells.setdefault(p.net, []).append((la, cells, attached))
        seed_cells: dict[str, list] = {}
        for net, layer, _w, pts in self.seeds:
            for a, b in zip(pts, pts[1:], strict=False):
                cells = [
                    ref.cell(a[0] + (b[0] - a[0]) * k / 30.0, a[1] + (b[1] - a[1]) * k / 30.0)
                    for k in range(31)
                ]
                seed_cells.setdefault(net, []).append((layer, cells, []))

        def span(net):
            pts = [(p.x, p.y) for p in self.res.pads if p.net == net]
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

        power = [n for n in pad_cells if n in sp.power_nets and n != gnd]
        signals = [n for n in pad_cells if n not in sp.power_nets and n != gnd]
        # nets leaving a fine-pitch package first, while the board is empty
        # around it (routed later they end up walled in by the power
        # tracks), then the power nets, then the rest; shortest span first
        # inside each group. BOARDGEN_MAX_NODES overrides the budget.
        max_nodes = int(os.environ.get("BOARDGEN_MAX_NODES", max_nodes))
        fine = {net for net, _pts, _rw, _via in self.stubs}
        first = [n for n in signals if n in fine]
        rest = [n for n in signals if n not in fine]
        order = sorted(first, key=span) + sorted(power, key=span) + sorted(rest, key=span)
        if only is not None:
            order = [n for n in order if n in only]
        for net in order:
            mr = routers["power"] if net in sp.power_nets else routers["signal"]
            width = sp.power_track if net in sp.power_nets else sp.track
            groups = list(pad_cells.get(net, []))
            if len(groups) + len(seed_cells.get(net, [])) < 2:
                continue
            connected = list(seed_cells.get(net, [])) or [groups.pop(0)]
            pending = groups
            ok = True
            while pending:
                starts: dict[str, list] = {}
                for la, cells, attached in connected:
                    starts.setdefault(la, []).extend(cells)
                    for ola, ocells in attached:
                        starts.setdefault(ola, []).extend(ocells)
                goals: dict[str, list] = {}
                for la, cells, attached in pending:
                    goals.setdefault(la, []).extend(cells)
                    for ola, ocells in attached:
                        goals.setdefault(ola, []).extend(ocells)
                found = mr.route(net, starts, goals, max_nodes=max_nodes)
                if found is None and mr is routers["power"]:
                    # a wide track cannot reach a fine-pitch pad: finish thin
                    mr, width = routers["signal"], sp.track
                    found = mr.route(net, starts, goals, max_nodes=max_nodes)
                if found is None:
                    nid = mr.nid(net)
                    usable = []
                    for groups in (connected, pending):
                        usable.append(
                            sum(
                                1
                                for la, cells, _attached in groups
                                for i, j in cells
                                if mr.own[la][j, i] in (mr.FREE, nid)
                            )
                        )
                    self.res.open_nets.append(
                        f"{net}: {len(pending)} pad(s) left open "
                        f"(usable start cells {usable[0]}, goal cells {usable[1]})"
                    )
                    ok = False
                    break
                tracks, vias = found
                clash = self._route_clash(net, tracks, vias, width)
                if clash:
                    # the lattice is conservative but not exact: a route that
                    # would fail the real clearance is dropped, never drawn
                    self.res.open_nets.append(f"{net}: route rejected, {clash}")
                    ok = False
                    break
                for la, pts in tracks:
                    self.track(net, la, pts, width)
                    connected.append((la, [mr.cell(x, y) for x, y in pts], []))
                for x, y in vias:
                    self.via(net, x, y)
                paint(net, tracks, vias, width)
                reached = set()
                for la, pts in tracks:
                    ends = {mr.cell(*pts[0]), mr.cell(*pts[-1])}
                    for k, (pla, cells, attached) in enumerate(pending):
                        if pla == la and ends & set(cells):
                            reached.add(k)
                        elif any(ola == la and ends & set(oc) for ola, oc in attached):
                            reached.add(k)
                if not reached:
                    reached.add(0)
                for k in sorted(reached, reverse=True):
                    connected.append(pending.pop(k))
            if ok:
                self.res.routed_nets += 1
        if sp.gnd_layer in self.layers:
            self._route_gnd(routers["signal"], gnd, pad_cells.get(gnd, []), sp.track, paint)
        self._gnd_pour(gnd)

    def _route_gnd(self, mr: MultiRouter, gnd: str, groups, width: float, paint) -> None:
        """Every GND pad gets its own short drop to the pour layer: goal is
        any free cell of that layer near the pad, the router puts the via."""
        sp = self.spec
        gl = sp.gnd_layer
        n = mr.nid(gnd)
        for la, cells, attached in groups:
            if la == gl or not cells:
                continue
            if any(ola == gl for ola, _c in attached):
                continue  # the fanout via already reaches the pour layer
            free = (mr.own[gl] == MultiRouter.FREE) | (mr.own[gl] == n)
            free &= (mr.own_via[gl] == MultiRouter.FREE) | (mr.own_via[gl] == n)
            i0 = max(0, min(c[0] for c in cells) - 60)
            i1 = min(mr.nx, max(c[0] for c in cells) + 60)
            j0 = max(0, min(c[1] for c in cells) - 60)
            j1 = min(mr.ny, max(c[1] for c in cells) + 60)
            jj, ii = free[j0:j1, i0:i1].nonzero()
            goal_cells = [(int(i) + i0, int(j) + j0) for i, j in zip(ii, jj, strict=True)]
            found = mr.route(gnd, {la: cells}, {gl: goal_cells}, max_nodes=120_000)
            if found is None:
                self.res.open_nets.append(f"{gnd}: pad at cell {cells[0]} has no drop to the pour")
                continue
            tracks, vias = found
            for tla, pts in tracks:
                self.track(gnd, tla, pts, width)
            for x, y in vias:
                self.via(gnd, x, y)
            paint(gnd, tracks, vias, width)
        self.res.routed_nets += 1

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
        from shapely import affinity

        items = []
        for t in self.res.tracks:
            items.append((t.net, t.layer, LineString(t.pts).buffer(t.width / 2.0)))
        for v in self.res.vias:
            for layer in self.layers:
                items.append((v.net, layer, Point(v.x, v.y).buffer(v.pad / 2.0)))
        for p in self.res.pads:
            layers = self.layers if p.layer == "*.Cu" else [p.layer]
            g = box(-p.w / 2, -p.h / 2, p.w / 2, p.h / 2)
            g = affinity.translate(affinity.rotate(g, -p.rot, origin=(0, 0)), p.x, p.y)
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
            g = box(-p.w / 2, -p.h / 2, p.w / 2, p.h / 2)
            from shapely import affinity

            g = affinity.translate(affinity.rotate(g, -p.rot, origin=(0, 0)), p.x, p.y)
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
    def finish(self, texts: list[tuple[str, float, float, str, float]] = ()) -> Result:
        sp = self.spec
        self.board.gr_rect(0.0, 0.0, sp.width, sp.height, "Edge.Cuts")
        for text, x, y, layer, size in texts:
            self.board.gr_text(text, x, y, layer, size)
        self.res.clearance_errors = self.clearance_check()
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
        f"{len(res.vias)} vias, nets routed {res.routed_nets}, open {len(res.open_nets)}, "
        f"clearance errors {len(res.clearance_errors)}"
    )
