"""Last-resort maze between two pieces of one net, on exact copper.

The grid router works at 0.125 mm with margins that round outwards, and
the finishing pass only knows straight lines, corners and sweeps. What
is left after both is a short link whose direct corridor is taken and
whose detour needs several turns: the kind of route a human draws in
pcbnew in a minute, and the kind this module finds.

It rasterizes only what matters, and only where it matters: around the
two pieces, every foreign item paints the cells closer to it than half
a track plus the clearance, analytically (a segment, a rectangle and a
disc all have a closed-form distance), so no cell is ever mistaken for
free. A* then walks the two layers, pays for a via and for a corner,
and the path comes back as the same plan the finishing pass commits,
which re-checks it against the exact geometry before it is kept.
"""

from __future__ import annotations

import heapq
import math

import numpy as np
import shapely
from shapely.geometry import LineString, Point, box
from shapely.ops import nearest_points, unary_union

GRID = 0.05  # raster step of the search, coarsened for a long haul
MARGIN_MM = 10.0  # how far around the two pieces the search may wander
DIAG = math.sqrt(2.0)
VIA_COST = 10.0  # cells: a via is worth half a millimetre of detour
TURN_COST = 1.5  # cells: prefer the straight run, then the single corner
MAX_CELLS = 400_000  # ceiling on the exploration of one link
MAX_GRID = 0.2  # coarsest raster: past it the gaps of a pad row close


def _dist_to_segment(xs, ys, p0, p1):
    """Distance from a grid of points to one segment, vectorized."""
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    length2 = dx * dx + dy * dy
    if length2 < 1e-12:
        return np.hypot(xs - x0, ys - y0)
    t = ((xs - x0) * dx + (ys - y0) * dy) / length2
    np.clip(t, 0.0, 1.0, out=t)
    return np.hypot(xs - (x0 + t * dx), ys - (y0 + t * dy))


class _Field:
    """Cells of a window, and what blocks them on each layer."""

    def __init__(self, x0, y0, x1, y1, grid=GRID):
        self.x0, self.y0, self.grid = x0, y0, grid
        self.nx = int(math.ceil((x1 - x0) / grid)) + 1
        self.ny = int(math.ceil((y1 - y0) / grid)) + 1
        self.xs = x0 + grid * np.arange(self.nx)
        self.ys = y0 + grid * np.arange(self.ny)
        self.gx, self.gy = np.meshgrid(self.xs, self.ys)
        self.blocked = [np.zeros((self.ny, self.nx), dtype=bool) for _ in range(2)]
        self.via_blocked = np.zeros((self.ny, self.nx), dtype=bool)

    def cell(self, x, y):
        return (
            int(round((y - self.y0) / self.grid)),
            int(round((x - self.x0) / self.grid)),
        )

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

    def _segment_distance(self, window, p0, p1):
        i0, i1, j0, j1 = window
        return _dist_to_segment(
            self.gx[i0 : i1 + 1, j0 : j1 + 1], self.gy[i0 : i1 + 1, j0 : j1 + 1], p0, p1
        )

    def _box_distance(self, window, x, y, w, h):
        i0, i1, j0, j1 = window
        dx = np.abs(self.gx[i0 : i1 + 1, j0 : j1 + 1] - x) - w / 2.0
        dy = np.abs(self.gy[i0 : i1 + 1, j0 : j1 + 1] - y) - h / 2.0
        return np.hypot(np.maximum(dx, 0.0), np.maximum(dy, 0.0))

    def paint_segment(self, targets, p0, p1, half, reach):
        """Cells closer than `reach` to a track of half-width `half`."""
        x0, x1 = sorted((p0[0], p1[0]))
        y0, y1 = sorted((p0[1], p1[1]))
        window = self._window(x0, y0, x1, y1, half + reach)
        if window[1] < window[0] or window[3] < window[2]:
            return
        self._mark(targets, window, self._segment_distance(window, p0, p1), half + reach)

    def paint_box(self, targets, x, y, w, h, reach):
        """Cells closer than `reach` to a pad rectangle."""
        window = self._window(x - w / 2, y - h / 2, x + w / 2, y + h / 2, reach)
        if window[1] < window[0] or window[3] < window[2]:
            return
        self._mark(targets, window, self._box_distance(window, x, y, w, h), reach)

    def mark_inside(self, geom):
        """Cells of the window whose centre sits in `geom`."""
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


def _fill(field, net, pads, tracks, vias, width, clearance, via_r, thermal_mm):
    """Paint every foreign item into the field, plus the via keepouts.

    Two reaches per item: what a track of this width may not come near,
    and what a via may not come near, which is wider by the difference
    of the radii. A cell is a via spot only when the whole disc fits.
    """
    slop = field.grid * DIAG / 2.0  # a cell centre stands for its whole cell
    half = width / 2.0
    reach = clearance + slop
    front, back, holes = field.blocked[0], field.blocked[1], field.via_blocked
    for q in pads:
        sides = (front, back) if q.tht else (front,)
        if q.net != net:
            field.paint_box(sides, q.x, q.y, q.w, q.h, half + reach)
            field.paint_box((holes,), q.x, q.y, q.w, q.h, via_r + reach)
        elif q.tht or min(q.w, q.h) < thermal_mm:
            # a via touching a pad the paste covers is a solder thief;
            # the thermal pad of a regulator is the wanted exception
            field.paint_box((holes,), q.x, q.y, q.w, q.h, via_r)
    for tnet, w, pts, layer in tracks:
        if tnet == net:
            continue
        side = front if layer == "F.Cu" else back
        for p0, p1 in zip(pts, pts[1:], strict=False):
            field.paint_segment((side,), tuple(p0), tuple(p1), w / 2.0, half + reach)
            field.paint_segment((holes,), tuple(p0), tuple(p1), w / 2.0, via_r + reach)
    for vnet, x, y in vias:
        if vnet == net:
            continue
        field.paint_segment((front, back), (x, y), (x, y), via_r, half + reach)
        field.paint_segment((holes,), (x, y), (x, y), via_r, via_r + reach)


def _search(field, starts, goals, via_ok):
    """A* over the two layers; returns cells [(layer, i, j)] or None."""
    ny, nx = field.ny, field.nx
    goal_any = goals[0] | goals[1]
    gi, gj = np.nonzero(goal_any)
    if not len(gi):
        return None
    tgt_i, tgt_j = float(gi.mean()), float(gj.mean())
    free = [~field.blocked[la] for la in (0, 1)]
    dist: dict[tuple[int, int, int], float] = {}
    prev: dict[tuple[int, int, int], tuple] = {}
    heap: list[tuple[float, float, tuple[int, int, int], tuple[int, int] | None]] = []
    for la in (0, 1):
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
        other = 1 - la
        if via_ok[i, j] and free[other][i, j]:
            ng = g + VIA_COST
            nkey = (other, i, j)
            if ng < dist.get(nkey, math.inf):
                dist[nkey] = ng
                prev[nkey] = key
                h = math.hypot(i - tgt_i, j - tgt_j)
                heapq.heappush(heap, (ng + h, ng, nkey, None))
    return None


def _to_plan(field, cells, layer_names=("F.Cu", "B.Cu")):
    """Cells into the plan the finishing pass commits: tracks and vias."""
    plan = []
    run = [cells[0]]
    for cell in cells[1:]:
        if cell[0] != run[-1][0]:
            plan.append(("run", run))
            x, y = field.point(cell[1], cell[2])
            plan.append(("via", (x, y)))
            run = [cell]
        else:
            run.append(cell)
    plan.append(("run", run))

    out = []
    for kind, payload in plan:
        if kind == "via":
            out.append(("V", payload, None))
            continue
        cells_run = payload
        if len(cells_run) < 2:
            continue
        pts = [field.point(cells_run[0][1], cells_run[0][2])]
        for a, b, c in zip(cells_run, cells_run[1:], cells_run[2:], strict=False):
            d1 = (b[1] - a[1], b[2] - a[2])
            d2 = (c[1] - b[1], c[2] - b[2])
            if d1 != d2:
                pts.append(field.point(b[1], b[2]))
        pts.append(field.point(cells_run[-1][1], cells_run[-1][2]))
        out.append(("T", pts, layer_names[cells_run[0][0]]))
    return out


def maze_join(
    net,
    piece_a,
    piece_b,
    pads,
    tracks,
    vias,
    width,
    clearance,
    via_r,
    thermal_mm,
    board=(0.0, 0.0, 100.0, 62.0),
    edge=0.55,
):
    """A plan joining two pieces of `net`, or None if the copper forbids it.

    `piece_a` and `piece_b` are (front copper, back copper) pairs, either
    side possibly None. The plan is a list of ("T", points, layer) and
    ("V", (x, y), None) steps, in the order they must be drawn.

    The search is local: the window is the gap between the two pieces
    widened by `MARGIN_MM`, and each piece is clipped to it. A ground
    pour reaches everywhere, and rasterizing all of it to join a pad
    0.2 mm away would cost minutes for nothing.
    """
    parts_a = [g for g in piece_a if g is not None and not g.is_empty]
    parts_b = [g for g in piece_b if g is not None and not g.is_empty]
    if not parts_a or not parts_b:
        return None
    pa, pb = nearest_points(unary_union(parts_a), unary_union(parts_b))
    bx0, by0, bx1, by1 = board
    x0 = max(bx0 + edge, min(pa.x, pb.x) - MARGIN_MM)
    y0 = max(by0 + edge, min(pa.y, pb.y) - MARGIN_MM)
    x1 = min(bx1 - edge, max(pa.x, pb.x) + MARGIN_MM)
    y1 = min(by1 - edge, max(pa.y, pb.y) + MARGIN_MM)
    if x1 - x0 < GRID or y1 - y0 < GRID:
        return None
    # A haul across the board rasterizes to millions of cells at the
    # nominal step: coarsen until the window fits the ceiling. The plan
    # is checked in exact geometry afterwards either way, so a coarse
    # raster costs detail, never legality.
    grid = GRID
    while (x1 - x0) * (y1 - y0) / (grid * grid) > MAX_CELLS:
        grid *= 2.0
        if grid > MAX_GRID:
            return None

    window = box(x0, y0, x1, y1)
    piece_a = tuple(None if g is None else g.intersection(window) for g in piece_a)
    piece_b = tuple(None if g is None else g.intersection(window) for g in piece_b)
    field = _Field(x0, y0, x1, y1, grid)
    _fill(field, net, pads, tracks, vias, width, clearance, via_r, thermal_mm)
    via_ok = ~field.via_blocked & ~field.blocked[0] & ~field.blocked[1]
    starts = [field.mark_inside(piece_a[la]) for la in (0, 1)]
    goals = [field.mark_inside(piece_b[la]) for la in (0, 1)]
    if not (starts[0].any() or starts[1].any()) or not (goals[0].any() or goals[1].any()):
        return None
    cells = _search(field, starts, goals, via_ok)
    if cells is None:
        return None
    return _to_plan(field, cells)


def plan_geometry(plan, width, via_r):
    """The copper a plan would add, per layer, for a last exact check."""
    out = {"F.Cu": [], "B.Cu": []}
    for kind, payload, layer in plan:
        if kind == "T":
            out[layer].append(LineString(payload).buffer(width / 2.0))
        else:
            disc = Point(payload).buffer(via_r)
            out["F.Cu"].append(disc)
            out["B.Cu"].append(disc)
    return out


__all__ = ["GRID", "maze_join", "plan_geometry"]
