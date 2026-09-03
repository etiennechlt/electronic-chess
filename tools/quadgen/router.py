"""Single-layer grid router (A*, 4-connected) over a rasterized obstacle
map, for the short LED chain hops and the supply spurs of the quadrant.

The board is a boolean lattice of `grid_mm` cells. Copper of foreign
nets is painted with its half width plus the clearance plus the half
width of the track to route, so any free cell is a legal centerline.
Paths prefer straight runs (a small turn penalty) and are returned as
simplified polylines in millimeters.
"""

from __future__ import annotations

import heapq
import math

import numpy as np


class Raster:
    def __init__(self, w_mm: float, h_mm: float, grid_mm: float) -> None:
        self.grid = grid_mm
        self.nx = int(math.ceil(w_mm / grid_mm)) + 1
        self.ny = int(math.ceil(h_mm / grid_mm)) + 1
        self.blocked = np.zeros((self.ny, self.nx), dtype=bool)
        ys, xs = np.mgrid[0 : self.ny, 0 : self.nx]
        self._xs = xs * grid_mm
        self._ys = ys * grid_mm

    def block_outside(self, margin_mm: float, w_mm: float, h_mm: float) -> None:
        self.blocked |= (self._xs < margin_mm) | (self._xs > w_mm - margin_mm)
        self.blocked |= (self._ys < margin_mm) | (self._ys > h_mm - margin_mm)

    def _window(self, x0: float, y0: float, x1: float, y1: float, r: float):
        i0 = max(0, int((min(x0, x1) - r) / self.grid) - 1)
        i1 = min(self.nx, int((max(x0, x1) + r) / self.grid) + 2)
        j0 = max(0, int((min(y0, y1) - r) / self.grid) - 1)
        j1 = min(self.ny, int((max(y0, y1) + r) / self.grid) + 2)
        return i0, i1, j0, j1

    def disc(self, cx: float, cy: float, r: float) -> None:
        i0, i1, j0, j1 = self._window(cx, cy, cx, cy, r)
        xs, ys = self._xs[j0:j1, i0:i1], self._ys[j0:j1, i0:i1]
        self.blocked[j0:j1, i0:i1] |= (xs - cx) ** 2 + (ys - cy) ** 2 <= r * r

    def segment(self, ax: float, ay: float, bx: float, by: float, r: float) -> None:
        i0, i1, j0, j1 = self._window(ax, ay, bx, by, r)
        xs, ys = self._xs[j0:j1, i0:i1], self._ys[j0:j1, i0:i1]
        vx, vy = bx - ax, by - ay
        ll = vx * vx + vy * vy
        if ll < 1e-12:
            self.disc(ax, ay, r)
            return
        t = np.clip(((xs - ax) * vx + (ys - ay) * vy) / ll, 0.0, 1.0)
        qx, qy = ax + t * vx, ay + t * vy
        self.blocked[j0:j1, i0:i1] |= (xs - qx) ** 2 + (ys - qy) ** 2 <= r * r

    def rect(self, cx: float, cy: float, w: float, h: float, r: float) -> None:
        """Axis-aligned rectangle (pad) inflated by r."""
        i0, i1, j0, j1 = self._window(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, r)
        xs, ys = self._xs[j0:j1, i0:i1], self._ys[j0:j1, i0:i1]
        dx = np.maximum(np.abs(xs - cx) - w / 2, 0.0)
        dy = np.maximum(np.abs(ys - cy) - h / 2, 0.0)
        self.blocked[j0:j1, i0:i1] |= dx * dx + dy * dy <= r * r

    def cell(self, x: float, y: float) -> tuple[int, int]:
        return int(round(x / self.grid)), int(round(y / self.grid))

    def route(
        self, start: tuple[float, float], goals, turn_penalty: float = 3.0, max_nodes: int = 400_000
    ) -> list[tuple[float, float]] | None:
        """A* from start to the nearest goal (a point or an iterable of
        points); start and goal cells are always allowed."""
        goal_pts = [goals] if isinstance(goals[0], (int, float)) else list(goals)
        sx, sy = self.cell(*start)
        goal_cells = {self.cell(*g) for g in goal_pts}
        gx = np.array([g[0] for g in goal_cells])
        gy = np.array([g[1] for g in goal_cells])

        def h(x, y):
            return float(np.min(np.abs(gx - x) + np.abs(gy - y)))

        open_heap = [(h(sx, sy), 0.0, sx, sy, 0)]  # (f, g, x, y, direction)
        best: dict[tuple[int, int, int], float] = {(sx, sy, 0): 0.0}
        parent: dict[tuple[int, int, int], tuple[int, int, int]] = {}
        moves = ((1, 0, 1), (-1, 0, 2), (0, 1, 3), (0, -1, 4))
        expanded = 0
        while open_heap:
            f, g, x, y, d = heapq.heappop(open_heap)
            if (x, y) in goal_cells:
                pts = [(x, y)]
                key = (x, y, d)
                while key in parent:
                    key = parent[key]
                    pts.append((key[0], key[1]))
                pts.reverse()
                return self._simplify([(px * self.grid, py * self.grid) for px, py in pts])
            if g > best.get((x, y, d), math.inf):
                continue
            expanded += 1
            if expanded > max_nodes:
                return None
            for dx, dy, nd in moves:
                nx_, ny_ = x + dx, y + dy
                if not (0 <= nx_ < self.nx and 0 <= ny_ < self.ny):
                    continue
                if self.blocked[ny_, nx_] and (nx_, ny_) not in goal_cells:
                    continue
                ng = g + 1.0 + (turn_penalty if d and nd != d else 0.0)
                key = (nx_, ny_, nd)
                if ng < best.get(key, math.inf):
                    best[key] = ng
                    parent[key] = (x, y, d)
                    heapq.heappush(open_heap, (ng + h(nx_, ny_), ng, nx_, ny_, nd))
        return None

    @staticmethod
    def _simplify(pts: list[tuple[float, float]]) -> list[tuple[float, float]]:
        out = [pts[0]]
        for a, b, c in zip(pts, pts[1:], pts[2:], strict=False):
            if (b[0] - a[0]) * (c[1] - b[1]) != (b[1] - a[1]) * (c[0] - b[0]):
                out.append(b)
        out.append(pts[-1])
        return [(round(x, 3), round(y, 3)) for x, y in out]


class MultiRouter:
    """Multi-layer A* over a rectangular region with net-aware ownership.

    Two int16 lattices per layer: `own` (copper inflated for a track
    centerline) and `own_via` (copper inflated for a via barrel). A cell
    holds the id of the single net whose copper covers it, -1 when free,
    -2 when two nets do (blocked for everyone). A route of net n may use
    cells owned by -1 or n; it may change layer where every layer's
    via lattice is free for n. Paths come back as per-layer polylines
    plus via positions, in board millimeters.
    """

    FREE, MULTI = -1, -2

    def __init__(
        self,
        layers: list[str],
        x0: float,
        y0: float,
        w: float,
        h: float,
        grid: float,
        clearance: float,
        via_pad: float,
        track_half: float = 0.2,
        via_cost: float = 25.0,
        outer_layers: tuple[str, ...] = ("F.Cu", "B.Cu"),
        outer_cost: float = 1.4,
        plane_layers: tuple[str, ...] = (),
        h_weight: float = 1.0,
    ):
        self.layers = layers
        self.track_half = track_half
        self.x0, self.y0, self.grid = x0, y0, grid
        self.nx = int(math.ceil(w / grid)) + 1
        self.ny = int(math.ceil(h / grid)) + 1
        self.clr, self.via_pad, self.via_cost = clearance, via_pad, via_cost
        # a plane layer is crossed by vias but never travelled along
        self.step_cost = [
            50.0 if la in plane_layers else outer_cost if la in outer_layers else 1.0
            for la in layers
        ]
        # > 1 weights the heuristic (greedier, faster, slightly longer routes)
        self.h_weight = h_weight
        self.own = {la: np.full((self.ny, self.nx), self.FREE, dtype=np.int16) for la in layers}
        self.own_via = {la: np.full((self.ny, self.nx), self.FREE, dtype=np.int16) for la in layers}
        self.net_ids: dict[str, int] = {}
        ys, xs = np.mgrid[0 : self.ny, 0 : self.nx]
        self._xs = x0 + xs * grid
        self._ys = y0 + ys * grid

    def nid(self, net: str) -> int:
        if net not in self.net_ids:
            self.net_ids[net] = len(self.net_ids)
        return self.net_ids[net]

    # ------------------------------------------------------------ painting
    def _window(self, xa, ya, xb, yb, r):
        i0 = max(0, int((min(xa, xb) - r - self.x0) / self.grid) - 1)
        i1 = min(self.nx, int((max(xa, xb) + r - self.x0) / self.grid) + 2)
        j0 = max(0, int((min(ya, yb) - r - self.y0) / self.grid) - 1)
        j1 = min(self.ny, int((max(ya, yb) + r - self.y0) / self.grid) + 2)
        return i0, i1, j0, j1

    def _claim(self, arr, mask, i0, i1, j0, j1, n):
        zone = arr[j0:j1, i0:i1]
        zone[mask & (zone == self.FREE)] = n
        zone[mask & (zone != n)] = self.MULTI

    def _shape(self, net: str, kind: str, fn):
        """Paint a shape into both lattices of the given layers. `fn(r)`
        returns (mask, window) for an inflation radius r."""
        n = self.nid(net)
        for arr, extra in ((self.own, self.track_half), (self.own_via, self.via_pad / 2.0)):
            mask, (i0, i1, j0, j1) = fn(self.clr + extra + 0.5 * self.grid)
            if mask is None:
                continue
            for la in kind:
                self._claim(arr[la], mask, i0, i1, j0, j1, n)

    def segment(self, net: str, layer: str, ax, ay, bx, by, width: float) -> None:
        def fn(r):
            rr = width / 2.0 + r
            i0, i1, j0, j1 = self._window(ax, ay, bx, by, rr)
            if i1 <= i0 or j1 <= j0:
                return None, (i0, i1, j0, j1)
            xs, ys = self._xs[j0:j1, i0:i1], self._ys[j0:j1, i0:i1]
            vx, vy = bx - ax, by - ay
            ll = vx * vx + vy * vy
            t = 0.0 if ll < 1e-12 else np.clip(((xs - ax) * vx + (ys - ay) * vy) / ll, 0.0, 1.0)
            qx, qy = ax + t * vx, ay + t * vy
            return (xs - qx) ** 2 + (ys - qy) ** 2 <= rr * rr, (i0, i1, j0, j1)

        self._shape(net, [layer], fn)

    def soft_segment(self, net: str, layer: str, ax, ay, bx, by, width: float) -> None:
        """Like `segment` but claims only free cells of the track lattice,
        leaving pads and copper painted before it untouched (used for the
        escape bands in front of fine-pitch rows)."""
        n = self.nid(net)
        rr = width / 2.0 + self.clr + self.track_half + 0.5 * self.grid
        i0, i1, j0, j1 = self._window(ax, ay, bx, by, rr)
        if i1 <= i0 or j1 <= j0:
            return
        xs, ys = self._xs[j0:j1, i0:i1], self._ys[j0:j1, i0:i1]
        vx, vy = bx - ax, by - ay
        ll = vx * vx + vy * vy
        t = 0.0 if ll < 1e-12 else np.clip(((xs - ax) * vx + (ys - ay) * vy) / ll, 0.0, 1.0)
        qx, qy = ax + t * vx, ay + t * vy
        mask = (xs - qx) ** 2 + (ys - qy) ** 2 <= rr * rr
        zone = self.own[layer][j0:j1, i0:i1]
        zone[mask & (zone == self.FREE)] = n

    def disc(self, net: str, layers, cx, cy, radius: float) -> None:
        def fn(r):
            rr = radius + r
            i0, i1, j0, j1 = self._window(cx, cy, cx, cy, rr)
            if i1 <= i0 or j1 <= j0:
                return None, (i0, i1, j0, j1)
            xs, ys = self._xs[j0:j1, i0:i1], self._ys[j0:j1, i0:i1]
            return (xs - cx) ** 2 + (ys - cy) ** 2 <= rr * rr, (i0, i1, j0, j1)

        self._shape(net, list(layers), fn)

    def rect(self, net: str, layers, cx, cy, w, h, rot_deg: float = 0.0) -> None:
        def fn(r):
            half = math.hypot(w, h) / 2.0 + r
            i0, i1, j0, j1 = self._window(cx, cy, cx, cy, half)
            if i1 <= i0 or j1 <= j0:
                return None, (i0, i1, j0, j1)
            xs, ys = self._xs[j0:j1, i0:i1] - cx, self._ys[j0:j1, i0:i1] - cy
            th = math.radians(rot_deg)
            u = xs * math.cos(th) - ys * math.sin(th)
            v = xs * math.sin(th) + ys * math.cos(th)
            dx = np.maximum(np.abs(u) - w / 2.0, 0.0)
            dy = np.maximum(np.abs(v) - h / 2.0, 0.0)
            return dx * dx + dy * dy <= r * r, (i0, i1, j0, j1)

        self._shape(net, list(layers), fn)

    def via_keepout(self, cx, cy, radius: float) -> None:
        """A drilled hole of a pad: no via center within `radius` (the
        hole to hole clearance), tracks unaffected."""
        i0, i1, j0, j1 = self._window(cx, cy, cx, cy, radius)
        xs, ys = self._xs[j0:j1, i0:i1], self._ys[j0:j1, i0:i1]
        m = (xs - cx) ** 2 + (ys - cy) ** 2 <= (radius + 0.5 * self.grid) ** 2
        for la in self.layers:
            self.own_via[la][j0:j1, i0:i1][m] = self.MULTI

    def keepout(self, cx, cy, radius: float) -> None:
        """A hole: blocked for every net on every layer."""
        i0, i1, j0, j1 = self._window(cx, cy, cx, cy, radius + self.via_pad)
        xs, ys = self._xs[j0:j1, i0:i1], self._ys[j0:j1, i0:i1]
        m = (xs - cx) ** 2 + (ys - cy) ** 2 <= (radius + self.clr) ** 2
        mv = (xs - cx) ** 2 + (ys - cy) ** 2 <= (radius + self.clr + self.via_pad / 2.0) ** 2
        for la in self.layers:
            self.own[la][j0:j1, i0:i1][m] = self.MULTI
            self.own_via[la][j0:j1, i0:i1][mv] = self.MULTI

    # ------------------------------------------------------------ routing
    def cell(self, x: float, y: float) -> tuple[int, int]:
        i = min(self.nx - 1, max(0, int(round((x - self.x0) / self.grid))))
        j = min(self.ny - 1, max(0, int(round((y - self.y0) / self.grid))))
        return i, j

    def cells_of_rect(self, cx, cy, w, h, rot_deg=0.0) -> list[tuple[int, int]]:
        """Lattice cells inside a rotated rectangle (a pad)."""
        half = math.hypot(w, h) / 2.0
        i0, i1, j0, j1 = self._window(cx, cy, cx, cy, half)
        xs, ys = self._xs[j0:j1, i0:i1] - cx, self._ys[j0:j1, i0:i1] - cy
        th = math.radians(rot_deg)
        u = xs * math.cos(th) - ys * math.sin(th)
        v = xs * math.sin(th) + ys * math.cos(th)
        inside = (np.abs(u) <= w / 2.0) & (np.abs(v) <= h / 2.0)
        jj, ii = np.nonzero(inside)
        return [(int(i + i0), int(j + j0)) for i, j in zip(ii, jj, strict=True)]

    def route(
        self,
        net: str,
        starts: dict[str, list[tuple[int, int]]],
        goals: dict[str, list[tuple[int, int]]],
        max_nodes: int = 250_000,
    ):
        """A* from any start cell to any goal cell; cells keyed by layer.
        Costs and parents live in flat preallocated arrays indexed by
        (layer, row, column, direction), so a long search costs no Python
        memory. Returns (tracks, vias) or None."""
        n = self.nid(net)
        nl, ny, nx = len(self.layers), self.ny, self.nx
        free = np.stack([(self.own[la] == self.FREE) | (self.own[la] == n) for la in self.layers])
        via_ok = np.ones((ny, nx), dtype=bool)
        for la in self.layers:
            via_ok &= (self.own_via[la] == self.FREE) | (self.own_via[la] == n)
        goal = np.zeros((nl, ny, nx), dtype=bool)
        for la, cells in goals.items():
            li = self.layers.index(la)
            for i, j in cells:
                goal[li, j, i] = True
        if not goal.any():
            return None
        gj, gi = np.nonzero(goal.any(axis=0))
        size = nl * ny * nx * 5
        if not hasattr(self, "_best") or self._best.size != size:
            self._best = np.empty(size, dtype=np.float32)
            self._parent = np.empty(size, dtype=np.int32)
        best, parent = self._best, self._parent
        best.fill(np.inf)
        parent.fill(-1)

        def idx(li, i, j, d):
            return ((li * ny + j) * nx + i) * 5 + d

        hw = self.h_weight

        def h(i, j):
            return hw * float(np.min(np.abs(gi - i) + np.abs(gj - j)))

        heap = []
        for la, cells in starts.items():
            li = self.layers.index(la)
            for i, j in cells:
                k = idx(li, i, j, 0)
                best[k] = 0.0
                heapq.heappush(heap, (h(i, j), 0.0, li, i, j, 0))
        moves = ((1, 0, 1), (-1, 0, 2), (0, 1, 3), (0, -1, 4))
        expanded = 0
        while heap:
            f, g, li, i, j, d = heapq.heappop(heap)
            k = idx(li, i, j, d)
            if g > best[k]:
                continue
            if goal[li, j, i]:
                return self._unwind(parent, k)
            expanded += 1
            if expanded > max_nodes:
                return None
            for dx, dy, nd in moves:
                ni, nj = i + dx, j + dy
                if not (0 <= ni < nx and 0 <= nj < ny):
                    continue
                if not free[li, nj, ni] and not goal[li, nj, ni]:
                    continue
                ng = g + self.step_cost[li] + (3.0 if d and nd != d else 0.0)
                nk = idx(li, ni, nj, nd)
                if ng < best[nk]:
                    best[nk] = ng
                    parent[nk] = k
                    heapq.heappush(heap, (ng + h(ni, nj), ng, li, ni, nj, nd))
            if via_ok[j, i]:
                for l2 in range(nl):
                    if l2 == li or not free[l2, j, i]:
                        continue
                    ng = g + self.via_cost
                    nk = idx(l2, i, j, 0)
                    if ng < best[nk]:
                        best[nk] = ng
                        parent[nk] = k
                        heapq.heappush(heap, (ng + h(i, j), ng, l2, i, j, 0))
        return None

    def _unwind(self, parent, k: int):
        ny, nx = self.ny, self.nx
        cells = []
        while k >= 0:
            d = k % 5
            rest = k // 5
            i = rest % nx
            rest //= nx
            j = rest % ny
            li = rest // ny
            cells.append((li, i, j, d))
            k = int(parent[k])
        cells.reverse()
        tracks, vias = [], []
        run: list[tuple[float, float]] = []
        cur_l = cells[0][0]
        for li, i, j, _d in cells:
            x, y = self.x0 + i * self.grid, self.y0 + j * self.grid
            if li != cur_l:
                if len(run) > 1:
                    tracks.append((self.layers[cur_l], Raster._simplify(run)))
                vias.append((round(x, 3), round(y, 3)))
                run = [(x, y)]
                cur_l = li
            else:
                run.append((x, y))
        if len(run) > 1:
            tracks.append((self.layers[cur_l], Raster._simplify(run)))
        return tracks, vias
