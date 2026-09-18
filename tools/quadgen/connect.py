"""Connectivity bookkeeping shared by the board generators: the front-end
strip of quadgen and the generic boards of boardgen.

The lattice router joins cells; KiCad joins copper. What turns one into
the other lives here, once:

- the copper of a pad as KiCad draws it (`pad_copper`) and the lattice
  cells inside it (`pad_cells`), never a corner the shape cuts off;
- the pieces of copper a net is made of before it is routed
  (`net_pieces`): one per connected component of its pads, escape
  stubs, hand-drawn tracks, buses and vias, in exact geometry, with the
  cells a route may start from or end on, on every layer the piece
  reaches;
- the loop that joins the pieces of one net (`close_net`): the router
  runs from the connected pieces to the pending ones; a piece counts as
  reached only when a route ends in it or a via lands in it, and a net
  whose route lands nowhere stays open, whatever the router believed;
- the copper a route owes to the escape stubs it lands on
  (`stub_copper`): the runway of a stub without fanout via and the exit
  corridor behind a fanout via are claims on cells, not copper, and a
  route that starts, ends or drops a via inside one gets the thin track
  that joins it to the stub or the via;
- the drops of a ground net to its pour (`ground_drops`): one short
  route per piece of copper that does not reach the pour's layer, to a
  spot the pour can reach;
- the exact check at the end (`connectivity_check`): every net one
  piece of copper, which is what KiCad reports as unconnected items.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from shapely import affinity, get_coordinates
from shapely.geometry import LineString, Point, box
from shapely.ops import unary_union
from shapely.strtree import STRtree

from .escape import EXIT_MM, STUB_WIDTH_MM, runway_end, stub_reach

CHECK_SLOP_MM = 0.001  # numerical slop of the exact geometry checks
Cell = tuple[int, int]


# ------------------------------------------------------------ pads
def pad_copper(p):
    """The copper of a pad as a shapely shape: the stadium of an oval or
    circular pad (a through pad of a pin header), the rounded rectangle of
    a roundrect pad (most SMD pads), else its rectangle. `p` carries x, y,
    w, h and, unless it is a plain rectangle, rot, shape and rratio. A
    track that ends on a corner the shape cuts off is open for KiCad."""
    shape = getattr(p, "shape", "rect")
    rratio = getattr(p, "rratio", 0.0)
    rot = getattr(p, "rot", 0.0)
    if shape in ("circle", "oval"):
        r = min(p.w, p.h) / 2.0
        if p.w >= p.h:
            g = LineString([(-p.w / 2.0 + r, 0.0), (p.w / 2.0 - r, 0.0)]).buffer(r)
        else:
            g = LineString([(0.0, -p.h / 2.0 + r), (0.0, p.h / 2.0 - r)]).buffer(r)
    elif shape == "roundrect" and rratio > 0:
        r = min(p.w, p.h) * rratio
        g = box(-p.w / 2.0 + r, -p.h / 2.0 + r, p.w / 2.0 - r, p.h / 2.0 - r).buffer(r)
    else:
        g = box(-p.w / 2.0, -p.h / 2.0, p.w / 2.0, p.h / 2.0)
    if rot:
        g = affinity.rotate(g, -rot, origin=(0, 0))
    return affinity.translate(g, p.x, p.y)


def _inside(mr, x: float, y: float) -> bool:
    """Whether a board point falls on the router's lattice."""
    eps = 0.5 * mr.grid
    return (
        mr.x0 - eps <= x <= mr.x0 + (mr.nx - 1) * mr.grid + eps
        and mr.y0 - eps <= y <= mr.y0 + (mr.ny - 1) * mr.grid + eps
    )


def pad_cells(mr, p) -> list[Cell]:
    """Lattice cells a route may start or end on inside the pad: cells of
    its copper, never a corner of the bounding box of a round pad."""
    cells = mr.cells_of_rect(p.x, p.y, p.w, p.h, getattr(p, "rot", 0.0))
    shape = getattr(p, "shape", "rect")
    if shape in ("circle", "oval") or (shape == "roundrect" and getattr(p, "rratio", 0.0) > 0):
        g = pad_copper(p).buffer(-0.02)
        cells = [
            (i, j) for i, j in cells if g.covers(Point(mr.x0 + i * mr.grid, mr.y0 + j * mr.grid))
        ]
    return cells


def track_cells(mr, pts) -> list[Cell]:
    """Lattice cells along a polyline, sampled at half the grid, those on
    the lattice only (copper outside the routed region has no cell)."""
    out: set[Cell] = set()
    pts = list(pts)
    if len(pts) == 1 and _inside(mr, *pts[0]):
        out.add(mr.cell(*pts[0]))
    for a, b in zip(pts, pts[1:], strict=False):
        n = max(2, int(math.hypot(b[0] - a[0], b[1] - a[1]) / mr.grid * 2))
        for k in range(n + 1):
            x, y = a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n
            if _inside(mr, x, y):
                out.add(mr.cell(x, y))
    return sorted(out)


# ------------------------------------------------------------ pieces
@dataclass
class Piece:
    """One connected piece of copper of a net, as lattice cells per layer:
    where a route may start from it, or end in it."""

    cells: dict[str, list[Cell]]
    label: str = "copper"

    def touches(self, starts: dict[str, set[Cell]]) -> bool:
        return any(set(cells) & starts.get(la, set()) for la, cells in self.cells.items())


def cells_of(pieces) -> dict[str, set[Cell]]:
    """Every cell of the given pieces, by layer."""
    out: dict[str, set[Cell]] = {}
    for pc in pieces:
        for la, cells in pc.cells.items():
            out.setdefault(la, set()).update(cells)
    return out


def find(parent: list[int], a: int) -> int:
    while parent[a] != a:
        parent[a] = parent[parent[a]]
        a = parent[a]
    return a


def union(parent: list[int], a: int, b: int) -> None:
    ra, rb = find(parent, a), find(parent, b)
    if ra != rb:
        parent[ra] = rb


def copper_components(items, slop: float = CHECK_SLOP_MM) -> list[list[int]]:
    """Indices of `items` (tuples starting with the layers and the shapely
    copper of one item of one net) grouped by contact: two items touch
    when they share a layer and their copper is within `slop`. Components
    come in the order of their first item."""
    parent = list(range(len(items)))
    if not items:
        return []
    tree = STRtree([it[1] for it in items])
    for k, it in enumerate(items):
        layers = set(it[0])
        for j in tree.query(it[1]):
            j = int(j)
            if j <= k or not layers & set(items[j][0]):
                continue
            if it[1].distance(items[j][1]) <= slop:
                union(parent, k, j)
    groups: dict[int, list[int]] = {}
    for k in range(len(items)):
        groups.setdefault(find(parent, k), []).append(k)
    return sorted(groups.values(), key=lambda g: g[0])


def net_pieces(
    mr,
    layers,
    pads,
    tracks,
    vias,
    stubs=(),
    exit_layer: str | None = None,
    first=(),
) -> list[Piece]:
    """The pieces of copper of one net before it is routed: one per
    connected component of its pads, tracks and vias (exact geometry),
    with the lattice cells a route may use. A pad gives the cells of its
    copper, its escape stub and runway, and the exit corridor of its
    fanout via on `exit_layer`; a track its samples; a via its cell on
    every layer. A component with no cell on the lattice (copper outside
    the routed region) is left out. The component holding the first item
    of `first` (a track drawn by hand, a bus) leads; the others follow in
    item order, pads first."""
    stub_at = {(round(s[1][0][0], 2), round(s[1][0][1], 2)): s for s in stubs}
    items: list[tuple] = []  # layers, copper, cells by layer, pad label, source object
    for p in pads:
        pl = list(layers) if p.layer == "*.Cu" else [p.layer]
        cells = pad_cells(mr, p)
        by: dict[str, list[Cell]] = {la: list(cells) for la in pl} if cells else {}
        stub = stub_at.get((round(p.x, 2), round(p.y, 2)))
        if stub is not None and "F.Cu" in pl:
            _net, pts, rw, via = stub[:4]
            by.setdefault("F.Cu", []).extend(track_cells(mr, [pts[0], runway_end(pts, rw)]))
            if via and exit_layer is not None:
                corridor = [runway_end(pts, rw), runway_end(pts, rw + stub_reach(stub))]
                by.setdefault(exit_layer, []).extend(track_cells(mr, corridor))
        ref = getattr(p, "ref", "")
        label = f"{ref}.{p.number}" if ref else "pad"
        items.append((pl, pad_copper(p), by, label, p))
    for t in tracks:
        cells = track_cells(mr, t.pts)
        g = LineString(t.pts).buffer(t.width / 2.0)
        items.append(([t.layer], g, {t.layer: cells} if cells else {}, None, t))
    for v in vias:
        by = {}
        if _inside(mr, v.x, v.y):
            c = mr.cell(v.x, v.y)
            by = {la: [c] for la in layers}
        items.append((list(layers), Point(v.x, v.y).buffer(v.pad / 2.0), by, None, v))
    first = list(first)

    def rank(comp):
        lead = [pos for pos, f in enumerate(first) if any(items[k][4] is f for k in comp)]
        return (0, min(lead)) if lead else (1, comp[0])

    pieces = []
    for comp in sorted(copper_components(items), key=rank):
        cells: dict[str, list[Cell]] = {}
        labels = []
        for k in comp:
            for la, cs in items[k][2].items():
                cells.setdefault(la, []).extend(cs)
            if items[k][3]:
                labels.append(items[k][3])
        if not cells:
            continue
        cells = {la: sorted(set(cs)) for la, cs in cells.items()}
        pieces.append(Piece(cells, " ".join(sorted(labels)) if labels else "copper"))
    return pieces


def reached(pending, tracks, vias, mr) -> set[int]:
    """Indices of the pending pieces a route (per-layer polylines and via
    positions) lands in: a track end or a via on one of their cells."""
    ends: dict[str, set[Cell]] = {}
    for la, pts in tracks:
        ends.setdefault(la, set()).update({mr.cell(*pts[0]), mr.cell(*pts[-1])})
    via_cells = {mr.cell(x, y) for x, y in vias}
    out = set()
    for k, pc in enumerate(pending):
        for la, cells in pc.cells.items():
            if (ends.get(la, set()) | via_cells) & set(cells):
                out.add(k)
                break
    return out


def close_net(net: str, pieces: list[Piece], attempt, open_nets: list[str]) -> bool:
    """Joins the pieces of `net` one route at a time. `attempt(starts,
    goals)` runs the router between two sets of cells (by layer) and, when
    it finds a legal route, draws it and returns (tracks, vias, router);
    otherwise it returns the reason as a string. A pending piece the
    connected copper already touches needs no route; a route that lands
    in no pending piece leaves the net open, never a piece assumed
    reached. Returns True when every piece is joined; the reason a net
    stays open is appended to `open_nets`."""
    if len(pieces) < 2:
        return True
    connected = [pieces[0]]
    pending = list(pieces[1:])
    while pending:
        starts = cells_of(connected)
        touching = [k for k, pc in enumerate(pending) if pc.touches(starts)]
        if touching:
            for k in sorted(touching, reverse=True):
                connected.append(pending.pop(k))
            continue
        labels = ", ".join(pc.label for pc in pending)
        out = attempt(starts, cells_of(pending))
        if isinstance(out, str):
            open_nets.append(f"{net}: {len(pending)} piece(s) left open ({labels}): {out}")
            return False
        tracks, vias, mr = out
        if not tracks and not vias:
            open_nets.append(
                f"{net}: pieces share a lattice cell but their copper does not touch ({labels})"
            )
            return False
        got = reached(pending, tracks, vias, mr)
        if not got:
            last = tracks[-1][1][-1] if tracks else vias[-1]
            open_nets.append(f"{net}: route ended off every piece at {last} ({labels})")
            return False
        cells: dict[str, list[Cell]] = {}
        for la, pts in tracks:
            cells.setdefault(la, []).extend(track_cells(mr, pts))
        for x, y in vias:
            c = mr.cell(x, y)
            for la in mr.layers:
                cells.setdefault(la, []).append(c)
        connected.append(Piece(cells, "route"))
        for k in sorted(got, reverse=True):
            connected.append(pending.pop(k))
    return True


# ------------------------------------------------------------ stub copper
def stub_copper(mr, exit_layer: str, tracks, vias, stubs) -> list:
    """The copper a route owes to the escape stubs it lands on. The runway
    of a stub whose fanout via did not fit, and the exit corridor behind a
    fanout via, are claims on lattice cells, not copper: a route that
    starts or ends inside one, or drops a via into it, gets a thin track
    along the claim's axis from its copper end (the stub end, the via) to
    that point; thin, it passes the other via row of a fanout at the pad
    pitch. `stubs` holds (net, points, runway, via) of the net's stubs;
    returns (layer, points) tracks to draw."""
    landings = [(la, pts[0]) for la, pts in tracks] + [(la, pts[-1]) for la, pts in tracks]
    landings += [(None, (x, y)) for x, y in vias]  # a via reaches every layer
    out = []
    seen = set()
    for stub in stubs:
        _net, spts, rw, via = stub[:4]
        if via:
            origin, far = runway_end(spts, rw), runway_end(spts, rw + stub_reach(stub))
            layer = exit_layer
        else:
            origin, far, layer = spts[1], runway_end(spts, rw), "F.Cu"
        cells = set(track_cells(mr, [origin, far]))
        if not cells:
            continue
        dx, dy = spts[1][0] - spts[0][0], spts[1][1] - spts[0][1]
        n = math.hypot(dx, dy)
        dx, dy = dx / n, dy / n
        for la, (x, y) in landings:
            if la is not None and la != layer:
                continue
            ce = mr.cell(x, y)
            if ce == mr.cell(*origin) or ce not in cells:
                continue
            key = (ce, origin)
            if key in seen:
                continue
            seen.add(key)
            along = (x - origin[0]) * dx + (y - origin[1]) * dy
            on_axis = (round(origin[0] + dx * along, 3), round(origin[1] + dy * along, 3))
            path = [origin, on_axis]
            if math.hypot(on_axis[0] - x, on_axis[1] - y) > 0.001:
                path.append((x, y))
            out.append((layer, path))
    return out


def trim_corridors(stubs, foreign, clearance: float, track_width: float = STUB_WIDTH_MM) -> list:
    """The stubs with their exit corridor cut to what the copper of other
    nets on the exit layer leaves legal for the corridor's thin track and
    for a route of `track_width` ending on it: `foreign` is (net, shapely
    copper) of everything drawn so far on that layer, vias and through
    pads included. A corridor stops one clearance before the first
    foreign item on its axis; later routes stop it by ownership
    (`reclaim_stubs`). Returns five-element stubs (net, points, runway,
    via, reach)."""
    tree = STRtree([g for _n, g in foreign]) if foreign else None
    r = clearance + max(STUB_WIDTH_MM, track_width) / 2.0
    out = []
    for stub in stubs:
        net, pts, rw, via = stub[:4]
        reach = EXIT_MM
        if via and tree is not None:
            line = LineString([runway_end(pts, rw), runway_end(pts, rw + EXIT_MM)])
            for j in tree.query(line.buffer(r)):
                other, g = foreign[int(j)]
                if other == net:
                    continue
                hit = line.intersection(g.buffer(r))
                if hit.is_empty:
                    continue
                t = min(line.project(Point(c)) for c in get_coordinates(hit))
                reach = min(reach, max(0.0, t - CHECK_SLOP_MM))
        out.append((net, pts, rw, via, round(reach, 3)))
    return out


# ------------------------------------------------------------ ground drops
def erode(mask, r: int):
    """The cells whose whole disc of radius r (in cells) is inside the mask."""
    out = mask.copy()
    ny, nx = mask.shape
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy > r * r:
                continue
            shifted = np.zeros_like(mask)
            ys = slice(max(0, dy), min(ny, ny + dy))
            xs = slice(max(0, dx), min(nx, nx + dx))
            ys_src = slice(max(0, -dy), min(ny, ny - dy))
            xs_src = slice(max(0, -dx), min(nx, nx - dx))
            shifted[ys, xs] = mask[ys_src, xs_src]
            out &= shifted
    return out


def ground_drops(
    mr,
    net: str,
    pieces: list[Piece],
    layer: str,
    reach: int,
    attempt,
    open_nets: list[str],
    within: tuple[float, float, float, float] | None = None,
) -> None:
    """Every piece of `net` without copper on `layer`, the layer of its
    pour, gets a short drop to it: goal is any free cell of that layer
    near the piece with `reach` cells of free lattice around it (the
    pour must reach the via, a via boxed in by tracks stays an island),
    the router puts the via. `attempt(starts, goals)` runs the router
    and draws the route, as for `close_net`; `within` (x0, y0, x1, y1)
    bounds the goals to the pour. A piece that reaches the layer already
    (a fanout via, a via or a track drawn by hand) needs none."""
    n = mr.nid(net)
    for pc in pieces:
        if layer in pc.cells:
            continue
        free = (mr.own[layer] == mr.FREE) | (mr.own[layer] == n)
        free &= (mr.own_via[layer] == mr.FREE) | (mr.own_via[layer] == n)
        free = erode(free, reach)
        cells = [c for cs in pc.cells.values() for c in cs]
        i0 = max(0, min(c[0] for c in cells) - 60)
        i1 = min(mr.nx, max(c[0] for c in cells) + 60)
        j0 = max(0, min(c[1] for c in cells) - 60)
        j1 = min(mr.ny, max(c[1] for c in cells) + 60)
        jj, ii = free[j0:j1, i0:i1].nonzero()
        goals = [(int(i) + i0, int(j) + j0) for i, j in zip(ii, jj, strict=True)]
        if within is not None:
            x0, y0, x1, y1 = within
            goals = [
                (i, j)
                for i, j in goals
                if x0 <= mr.x0 + i * mr.grid <= x1 and y0 <= mr.y0 + j * mr.grid <= y1
            ]
        out = attempt({la: set(cs) for la, cs in pc.cells.items()}, {layer: goals})
        if isinstance(out, str):
            open_nets.append(f"{net}: {pc.label} has no drop to the pour: {out}")


# ------------------------------------------------------------ pours
def pour_pieces(region, foreign, clearance: float, min_width: float = 0.25) -> list:
    """The polygons a copper pour actually fills inside `region`: the
    region less the copper of other nets and its clearance, with the necks
    narrower than the filler's minimum width pinched off, which is what
    KiCad's filler does. `foreign` is the copper of the other nets on the
    pour's layer, holes included. A pour cut in two by a track is two
    pieces, and the connectivity check counts them as two."""
    holes = unary_union([g.buffer(clearance) for g in foreign]) if foreign else None
    free = region.difference(holes) if holes is not None else region
    filled = free.buffer(-min_width / 2.0).buffer(min_width / 2.0)
    return [g for g in getattr(filled, "geoms", [filled]) if not g.is_empty]


# ------------------------------------------------------------ the check
def connectivity_check(
    tracks, vias, pads, layers, pours: dict | None = None, slop: float = CHECK_SLOP_MM
) -> list[str]:
    """Every net with two pads or more must be one piece of copper: pads,
    tracks and vias that touch on a layer, vias and through pads joining
    the layers, a pour (`pours`: net to its layer, or to (layer, shapely
    region)) joining everything of its net that has copper on that layer
    inside the region. What KiCad reports as unconnected items, computed
    here so a build never claims a net closed that a track ends short
    of; a track or via island of the net counts as a piece too."""
    by_net: dict[str, list] = {}
    for t in tracks:
        g = LineString(t.pts).buffer(t.width / 2.0)
        by_net.setdefault(t.net, []).append(([t.layer], g, None, t.pts[0], t.layer))
    for v in vias:
        g = Point(v.x, v.y).buffer(v.pad / 2.0)
        by_net.setdefault(v.net, []).append((list(layers), g, None, (v.x, v.y), "via"))
    for p in pads:
        if not p.net:
            continue
        pl = list(layers) if p.layer == "*.Cu" else [p.layer]
        ref = getattr(p, "ref", "")
        label = f"{ref}.{p.number}" if ref else f"pad at ({p.x:.1f},{p.y:.1f})"
        by_net.setdefault(p.net, []).append((pl, pad_copper(p), label, (p.x, p.y), p.layer))
    pours = pours or {}
    out = []
    for net, items in sorted(by_net.items()):
        if sum(1 for it in items if it[2]) < 2:
            continue
        comps = copper_components(items, slop)
        pour = pours.get(net)
        if pour is not None:
            # one node per island of the pour: what it joins is what its
            # own copper covers, and a pour cut in two joins nothing across
            pour_layer, region = pour if isinstance(pour, tuple) else (pour, None)
            islands = list(getattr(region, "geoms", [region])) if region is not None else [None]
            parent = list(range(len(comps)))
            for island in islands:
                touching = [
                    ci
                    for ci, c in enumerate(comps)
                    if any(
                        pour_layer in items[k][0]
                        and (island is None or items[k][1].intersects(island))
                        for k in c
                    )
                ]
                for ci in touching[1:]:
                    union(parent, touching[0], ci)
            grouped: dict[int, list[int]] = {}
            for ci in range(len(comps)):
                grouped.setdefault(find(parent, ci), []).extend(comps[ci])
            comps = list(grouped.values())
        pieces = []
        for c in comps:
            labels = sorted(items[k][2] for k in c if items[k][2])
            if labels:
                pieces.append(" ".join(labels))
            else:
                _l, _g, _r, (x, y), where = items[c[0]]
                pieces.append(f"island on {where} at ({x:.1f},{y:.1f})")
        if len(pieces) > 1:
            out.append(f"{net}: {len(pieces)} pieces ({'; '.join(pieces)})")
    return out
