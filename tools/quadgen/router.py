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
