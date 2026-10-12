"""Filament models of planar coils, the reference the NFC formulas are
checked against (note 25, paragraph 2, point 10).

Square reader loops are concentric closed squares on one copper layer
(the spiral pitch and the back-side bridge are ignored), each track split
into sub-filaments across its width that share the current evenly. Their
inductance and mutual inductances come from the exact Neumann integral of
parallel straight filaments (Grover); perpendicular pairs contribute
nothing, and coincident filaments use the geometric mean distance of the
sub-track section. The field comes from Biot-Savart on the same segments,
the flux through a circular tag turn from a polar integration of Bz over
its disc.

Round tag coils are coaxial circular filaments (Maxwell's formula), one
per turn and per layer, every turn in series with the same sense.

The AC resistance of a set of strips that carry the same current (the
turns of one coil, seen in a cross-section through two opposite sides)
comes from a two-dimensional partial-element (PEEC) solve at the carrier:
each strip is meshed into rectangular cells, cosine-graded across the
width, and the opposite side of the coil is folded in by mirror symmetry
(it carries the opposite current). Skin and proximity effects follow;
corners, pads and the bridge are ignored.

Units: lengths in mm at the interface, SI inside; inductances in H.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from scipy.special import ellipe, ellipk

from .physics import MU0_H_PER_M, RHO_CU_OHM_M

# Geometric mean distance of a rectangle from itself, over (width + height)
GMD_RECT = 0.2235

# Discretization of the models, not design numbers
FLUX_RINGS = 60          # radial cells of the polar flux integration
FLUX_SECTORS = 72        # angular cells
PEEC_CELLS_WIDTH = 12    # cells across a strip, cosine-graded towards the edges
PEEC_CELLS_THICK = 6     # cells through the copper thickness
_COLLINEAR_D_M = 1e-9    # stands for d = 0 between disjoint collinear filaments
_PEEC_NEAR = 4.0         # cells closer than this many sizes use the exact formula


@dataclass(frozen=True)
class Filaments:
    """Straight current filaments: start and end points (m), current share."""

    start: np.ndarray
    end: np.ndarray
    weight: np.ndarray

    def shifted(self, dx_mm: float = 0.0, dy_mm: float = 0.0, dz_mm: float = 0.0) -> Filaments:
        d = np.array([dx_mm, dy_mm, dz_mm]) * 1e-3
        return Filaments(self.start + d, self.end + d, self.weight)


def square_loop(
    side_mm: float,
    turns: int,
    track_mm: float,
    gap_mm: float,
    nsub: int = 3,
    centre_mm: tuple[float, float] = (0.0, 0.0),
    z_mm: float = 0.0,
) -> Filaments:
    """Concentric closed squares, counter-clockwise seen from above (+z),
    outer edge of the outer turn at side_mm, every track split in nsub."""
    cx, cy = centre_mm
    starts, ends = [], []
    for t in range(turns):
        outer = side_mm / 2.0 - t * (track_mm + gap_mm)
        for s in range(nsub):
            h = outer - (s + 0.5) * track_mm / nsub
            corners = [(cx - h, cy - h), (cx + h, cy - h), (cx + h, cy + h), (cx - h, cy + h)]
            for k in range(4):
                (x1, y1), (x2, y2) = corners[k], corners[(k + 1) % 4]
                starts.append((x1, y1, z_mm))
                ends.append((x2, y2, z_mm))
    n = len(starts)
    return Filaments(
        np.array(starts) * 1e-3, np.array(ends) * 1e-3, np.full(n, 1.0 / nsub)
    )


def _neumann_g(t: np.ndarray, d: np.ndarray) -> np.ndarray:
    return t * np.arcsinh(t / d) - np.sqrt(t * t + d * d)


def mutual_h(a: Filaments, b: Filaments, gmd_m: float | None = None) -> float:
    """Mutual inductance (H) of two filament sets, each filament carrying its
    weight of a unit current. With gmd_m, coincident filaments (a set with
    itself) use that distance, which turns the result into a self inductance.
    Only parallel pairs count; perpendicular pairs have no mutual, and an
    oblique pair raises, since the formula does not cover it."""
    ua = a.end - a.start
    la = np.linalg.norm(ua, axis=1)
    ua = ua / la[:, None]
    ub = b.end - b.start
    lb = np.linalg.norm(ub, axis=1)
    ub = ub / lb[:, None]
    dot = ua @ ub.T
    parallel = np.abs(np.abs(dot) - 1.0) < 1e-9
    if np.any(~parallel & (np.abs(dot) > 1e-9)):
        raise ValueError("filaments neither parallel nor perpendicular: not modelled")
    ia, ib = np.nonzero(parallel)
    if ia.size == 0:
        return 0.0
    u = ua[ia]
    rel_s = b.start[ib] - a.start[ia]
    rel_e = b.end[ib] - a.start[ia]
    b1 = np.sum(rel_s * u, axis=1)
    b2 = np.sum(rel_e * u, axis=1)
    d = np.linalg.norm(rel_s - b1[:, None] * u, axis=1)
    c1, c2 = np.minimum(b1, b2), np.maximum(b1, b2)
    l1 = la[ia]
    overlap = np.minimum(l1, c2) - np.maximum(0.0, c1)
    on_line = d < 1e-12
    if gmd_m is not None:
        d = np.where(on_line & (overlap > 1e-12), gmd_m, d)
    elif np.any(on_line & (overlap > 1e-12)):
        raise ValueError("coincident filaments need a geometric mean distance")
    d = np.where(d < _COLLINEAR_D_M, _COLLINEAR_D_M, d)
    val = (
        _neumann_g(l1 - c1, d) - _neumann_g(l1 - c2, d) - _neumann_g(-c1, d) + _neumann_g(-c2, d)
    )
    m = MU0_H_PER_M / (4.0 * math.pi) * np.sign(dot[ia, ib]) * val
    return float(np.sum(a.weight[ia] * b.weight[ib] * m))


def self_inductance_h(f: Filaments, track_mm: float, nsub: int, copper_mm: float) -> float:
    """Inductance of a filament set built with square_loop."""
    gmd = GMD_RECT * (track_mm / nsub + copper_mm) * 1e-3
    return mutual_h(f, f, gmd_m=gmd)


def bz_t_per_a(f: Filaments, points_m: np.ndarray) -> np.ndarray:
    """Vertical field (T per A) of the filament set at points (n, 3) in m."""
    r1 = f.start[None, :, :] - points_m[:, None, :]
    r2 = f.end[None, :, :] - points_m[:, None, :]
    n1 = np.linalg.norm(r1, axis=2)
    n2 = np.linalg.norm(r2, axis=2)
    cross_z = r1[:, :, 0] * r2[:, :, 1] - r1[:, :, 1] * r2[:, :, 0]
    den = n1 * n2 * (n1 * n2 + np.sum(r1 * r2, axis=2))
    den = np.where(np.abs(den) < 1e-30, 1e-30, den)
    return MU0_H_PER_M / (4.0 * math.pi) * np.sum(f.weight * cross_z * (n1 + n2) / den, axis=1)


def flux_through_circles_h(
    f: Filaments, centre_mm: tuple[float, float], z_mm: float, radii_mm: np.ndarray
) -> np.ndarray:
    """Flux per ampere (H) of the filament set through horizontal circles
    of the given radii, all centred at (centre, z)."""
    radii = np.asarray(radii_mm, dtype=float)
    rmax = float(np.max(radii)) * 1e-3
    edges = np.linspace(0.0, rmax, FLUX_RINGS + 1)
    r = 0.5 * (edges[:-1] + edges[1:])
    th = (np.arange(FLUX_SECTORS) + 0.5) * 2.0 * math.pi / FLUX_SECTORS
    rr, tt = np.meshgrid(r, th, indexing="ij")
    pts = np.stack(
        [
            centre_mm[0] * 1e-3 + (rr * np.cos(tt)).ravel(),
            centre_mm[1] * 1e-3 + (rr * np.sin(tt)).ravel(),
            np.full(rr.size, z_mm * 1e-3),
        ],
        axis=1,
    )
    bz = bz_t_per_a(f, pts).reshape(rr.shape)
    ring = np.sum(bz, axis=1) * (2.0 * math.pi / FLUX_SECTORS) * r * (edges[1] - edges[0])
    cum = np.concatenate([[0.0], np.cumsum(ring)])
    return np.interp(radii * 1e-3, edges, cum)


def coaxial_mutual_h(r1_m: np.ndarray, r2_m: np.ndarray, dz_m: np.ndarray) -> np.ndarray:
    """Maxwell mutual inductance (H) of coaxial circular filaments."""
    m = 4.0 * r1_m * r2_m / ((r1_m + r2_m) ** 2 + dz_m * dz_m)
    k = np.sqrt(m)
    return MU0_H_PER_M * np.sqrt(r1_m * r2_m) * ((2.0 / k - k) * ellipk(m) - 2.0 / k * ellipe(m))


def circular_coil_h(
    radii_mm: tuple[float, ...], layers_z_mm: tuple[float, ...], track_mm: float, copper_mm: float
) -> float:
    """Inductance (H) of concentric round turns on stacked layers, all in
    series with the same sense: every turn's self term plus every mutual."""
    r = np.array([ri for _ in layers_z_mm for ri in radii_mm]) * 1e-3
    z = np.array([zi for zi in layers_z_mm for _ in radii_mm]) * 1e-3
    gmd = GMD_RECT * (track_mm + copper_mm) * 1e-3
    self_terms = MU0_H_PER_M * r * (np.log(8.0 * r / gmd) - 2.0)
    i, j = np.triu_indices(r.size, k=1)
    mutual = coaxial_mutual_h(r[i], r[j], np.abs(z[i] - z[j]))
    return float(np.sum(self_terms) + 2.0 * np.sum(mutual))


def circular_filament_field(
    a_m: float, rho_m: np.ndarray, z_m: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Radial and axial field (T per A) of a circular filament of radius a,
    at radius rho and height z above its plane."""
    rho = np.maximum(rho_m, 1e-12)
    q = (a_m + rho) ** 2 + z_m * z_m
    m = 4.0 * a_m * rho / q
    k_m, e_m = ellipk(m), ellipe(m)
    den = (a_m - rho) ** 2 + z_m * z_m
    c = MU0_H_PER_M / (2.0 * math.pi) / np.sqrt(q)
    bz = c * (k_m + (a_m * a_m - rho * rho - z_m * z_m) / den * e_m)
    br = c * z_m / rho * (-k_m + (a_m * a_m + rho * rho + z_m * z_m) / den * e_m)
    return br, bz


def coaxial_set_mutual_h(
    ra_m: np.ndarray, za_m: np.ndarray, wa: np.ndarray,
    rb_m: np.ndarray, zb_m: np.ndarray, wb: np.ndarray,
) -> float:
    """Mutual inductance (H) of two sets of coaxial circular filaments, each
    filament carrying its weight of a unit current; the sets do not touch."""
    m = coaxial_mutual_h(ra_m[:, None], rb_m[None, :], np.abs(za_m[:, None] - zb_m[None, :]))
    return float(np.sum(wa[:, None] * wb[None, :] * m))


def coaxial_set_self_h(r_m: np.ndarray, z_m: np.ndarray, w: np.ndarray, gmd_m: np.ndarray) -> float:
    """Inductance (H) of a set of coaxial circular filaments in series, each
    carrying its weight of a unit current; gmd_m is each filament's own
    geometric mean distance (its section)."""
    self_terms = MU0_H_PER_M * r_m * (np.log(8.0 * r_m / gmd_m) - 2.0)
    i, j = np.triu_indices(r_m.size, k=1)
    mutual = coaxial_mutual_h(r_m[i], r_m[j], np.abs(z_m[i] - z_m[j]))
    return float(np.sum(w * w * self_terms) + 2.0 * np.sum(w[i] * w[j] * mutual))


def _log_r2_antiderivative(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """F with d4F / dx2 dy2 = ln(x^2 + y^2), even in x and y."""
    r2 = x * x + y * y
    safe_r2 = np.where(r2 > 0.0, r2, 1.0)
    safe_x = np.where(x != 0.0, x, 1.0)
    safe_y = np.where(y != 0.0, y, 1.0)
    log_r2 = np.where(r2 > 0.0, np.log(safe_r2), 0.0)
    atan_yx = np.where(x != 0.0, np.arctan(y / safe_x), 0.0)
    atan_xy = np.where(y != 0.0, np.arctan(x / safe_y), 0.0)
    return (
        -(x**4 - 6.0 * x * x * y * y + y**4) * log_r2 / 24.0
        + (x**3 * y * atan_yx + x * y**3 * atan_xy) / 3.0
        - 25.0 / 24.0 * x * x * y * y
    )


def _mean_log_distance(
    xa: np.ndarray, ya: np.ndarray, wa: np.ndarray, ha: np.ndarray,
    xb: np.ndarray, yb: np.ndarray, wb: np.ndarray, hb: np.ndarray,
) -> np.ndarray:
    """Exact mean of ln(r) between two rectangles (centres, widths, heights),
    the logarithm of their geometric mean distance."""
    total = np.zeros(np.broadcast(xa, xb).shape)
    for sx, dx in ((1.0, (wa + wb) / 2.0), (-1.0, (wa - wb) / 2.0),
                   (-1.0, (wb - wa) / 2.0), (1.0, -(wa + wb) / 2.0)):
        for sy, dy in ((1.0, (ha + hb) / 2.0), (-1.0, (ha - hb) / 2.0),
                       (-1.0, (hb - ha) / 2.0), (1.0, -(ha + hb) / 2.0)):
            total = total + sx * sy * _log_r2_antiderivative(xa - xb + dx, ya - yb + dy)
    return total / (2.0 * wa * ha * wb * hb)


def _strip_cells(track_m: float, copper_m: float) -> tuple[np.ndarray, ...]:
    """Cell centres (x, y) and sizes (w, h) of one strip section, centred."""
    xe = (1.0 - np.cos(np.linspace(0.0, math.pi, PEEC_CELLS_WIDTH + 1))) / 2.0 - 0.5
    xe = xe * track_m
    ye = np.linspace(-copper_m / 2.0, copper_m / 2.0, PEEC_CELLS_THICK + 1)
    gx, gy = np.meshgrid(0.5 * (xe[:-1] + xe[1:]), 0.5 * (ye[:-1] + ye[1:]), indexing="ij")
    gw, gh = np.meshgrid(np.diff(xe), np.diff(ye), indexing="ij")
    return gx.ravel(), gy.ravel(), gw.ravel(), gh.ravel()


def _log_distance(
    xa: np.ndarray, ya: np.ndarray, wa: np.ndarray, ha: np.ndarray,
    xb: np.ndarray, yb: np.ndarray, wb: np.ndarray, hb: np.ndarray,
) -> np.ndarray:
    """ln of the geometric mean distance between every cell a and every
    cell b: exact for neighbours, centre distance for the others."""
    dx = xa[:, None] - xb[None, :]
    dy = ya[:, None] - yb[None, :]
    d = np.hypot(dx, dy)
    out = np.log(np.maximum(d, 1e-30))
    size_a, size_b = np.maximum(wa, ha), np.maximum(wb, hb)
    i, j = np.nonzero(d < _PEEC_NEAR * (size_a[:, None] + size_b[None, :]))
    if i.size:
        out[i, j] = _mean_log_distance(xa[i], ya[i], wa[i], ha[i], xb[j], yb[j], wb[j], hb[j])
    return out


@lru_cache(maxsize=256)
def strip_resistance_per_m(
    x_mm: tuple[float, ...],
    y_mm: tuple[float, ...],
    track_mm: float,
    copper_mm: float,
    f_hz: float,
    mirror_y_mm: float | None = None,
) -> tuple[float, ...]:
    """AC resistance per unit length (ohm/m) of each strip of a coil cross-
    section, all strips in series (same current), their mirror images at
    (-x, y) carrying the opposite current. x is the distance from the coil
    axis to the strip centre, y the height of the strip's copper centre.
    With mirror_y_mm, the strips are the lower half of a section symmetric
    about that height, the upper half carrying the same current: the
    problem is folded, half the size, and the result holds for both halves.

    Cells interact through the exact geometric mean distance of two
    rectangles when they are close, through their centre distance when
    they are far (where the exact formula would lose its digits); images
    are always far."""
    cx, cy, cw, ch = _strip_cells(track_mm * 1e-3, copper_mm * 1e-3)
    per_strip = cx.size
    n_strips = len(x_mm)
    xs = np.concatenate([xk * 1e-3 + cx for xk in x_mm])
    ys = np.concatenate([yk * 1e-3 + cy for yk in y_mm])
    ws = np.tile(cw, n_strips)
    hs = np.tile(ch, n_strips)
    owner = np.repeat(np.arange(n_strips), per_strip)
    dx = xs[:, None] - xs[None, :]
    dy = ys[:, None] - ys[None, :]
    d = np.hypot(dx, dy)
    log_d = np.log(np.maximum(d, 1e-30))
    # every strip has the same mesh: its own block is computed once
    block = _log_distance(cx, cy, cw, ch, cx, cy, cw, ch)
    for k in range(n_strips):
        sl = slice(k * per_strip, (k + 1) * per_strip)
        log_d[sl, sl] = block
    size = np.maximum(ws, hs)
    near = d < _PEEC_NEAR * (size[:, None] + size[None, :])
    i, j = np.nonzero(near & (owner[:, None] != owner[None, :]))
    if i.size:
        log_d[i, j] = _mean_log_distance(xs[i], ys[i], ws[i], hs[i], xs[j], ys[j], ws[j], hs[j])
    log_mirror = 0.5 * np.log((xs[:, None] + xs[None, :]) ** 2 + dy * dy)
    lp = -MU0_H_PER_M / (2.0 * math.pi) * (log_d - log_mirror)
    if mirror_y_mm is not None:
        ym = 2.0 * mirror_y_mm * 1e-3 - ys          # the upper half, same current
        dy_m = ys[:, None] - ym[None, :]
        if np.min(np.abs(dy_m)) < _PEEC_NEAR * 2.0 * np.max(size):
            raise ValueError("the folded halves are too close for the image model")
        log_up = 0.5 * np.log(dx * dx + dy_m * dy_m)
        log_up_mirror = 0.5 * np.log((xs[:, None] + xs[None, :]) ** 2 + dy_m * dy_m)
        lp = lp - MU0_H_PER_M / (2.0 * math.pi) * (log_up - log_up_mirror)
    z = np.diag(RHO_CU_OHM_M / (ws * hs)) + 1j * 2.0 * math.pi * f_hz * lp
    s = np.zeros((xs.size, n_strips))
    s[np.arange(xs.size), owner] = 1.0
    y = np.linalg.solve(z, s)          # cell currents per unit strip voltage
    v = np.linalg.solve(s.T @ y, np.ones(n_strips))   # strip voltages for unit currents
    return tuple(float(r) for r in np.real(v))
