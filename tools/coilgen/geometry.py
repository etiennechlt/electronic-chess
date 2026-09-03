"""Spiral path geometry for stacked series-connected PCB coils.

Convention: KiCad coordinates, x to the right, y downward. A positive
angular step turns clockwise on screen. All layers of one coil must
carry the current in the same rotational direction when traversed
electrically, otherwise the stacked fields cancel; tests assert it.

Winding plan for an even layer count, entering and exiting on the rim:
layer 1 spirals inward from the entry terminal; each following layer
starts with a 90 degree constant-radius lead-in arc (so the stacking
vias land on distinct angular positions instead of shorting the
terminals) then spirals the other way; a trailing arc on the last
layer brings the exit terminal back to the entry angle, so the two
terminals stack vertically and route away as a tight pair. The four
arcs sum to one extra effective turn, which the inductance target
absorbs (the stack model is a few percent approximate anyway).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class LayerPath:
    layer: str
    points: np.ndarray  # (N, 2) polyline, electrical order
    start_r_mm: float
    end_r_mm: float

    def total_turning_deg(self, center_xy: tuple[float, float]) -> float:
        """Signed angular sweep around the coil center, electrical order."""
        d = self.points - np.asarray(center_xy)
        ang = np.unwrap(np.arctan2(d[:, 1], d[:, 0]))
        return float(np.degrees(ang[-1] - ang[0]))


def spiral_points(
    center_xy: tuple[float, float],
    r_from_mm: float,
    r_to_mm: float,
    turns: float,
    start_angle_deg: float,
    angular_sign: int,
    points_per_turn: int = 90,
) -> np.ndarray:
    """Archimedean spiral polyline from r_from to r_to over `turns` turns."""
    n = max(2, int(round(points_per_turn * turns)))
    theta = np.radians(start_angle_deg) + angular_sign * np.linspace(0.0, 2.0 * np.pi * turns, n)
    r = np.linspace(r_from_mm, r_to_mm, n)
    x = center_xy[0] + r * np.cos(theta)
    y = center_xy[1] + r * np.sin(theta)
    return np.column_stack([x, y])


def arc_points(
    center_xy: tuple[float, float],
    r_mm: float,
    start_angle_deg: float,
    sweep_deg: float,
    points: int = 24,
) -> np.ndarray:
    theta = np.radians(np.linspace(start_angle_deg, start_angle_deg + sweep_deg, points))
    x = center_xy[0] + r_mm * np.cos(theta)
    y = center_xy[1] + r_mm * np.sin(theta)
    return np.column_stack([x, y])


def spiral_stack(
    center_xy: tuple[float, float],
    layers: list[str],
    r_in_mm: float,
    r_out_mm: float,
    turns_per_layer: int,
    start_angle_deg: float = -90.0,
    angular_sign: int = 1,
    lead_arc_deg: float = 90.0,
    points_per_turn: int = 90,
) -> list[LayerPath]:
    """Series-connected stack per the winding plan in the module docstring.

    Consecutive paths share their junction point exactly (the stacking
    via location). The first point of layer 1 and the last point of the
    last layer both sit at (start_angle_deg, r_out): the coil terminals,
    vertically stacked.
    """
    if len(layers) % 2 != 0:
        raise ValueError("series stack expects an even number of layers")
    paths: list[LayerPath] = []
    angle = start_angle_deg
    for i, layer in enumerate(layers):
        inward = i % 2 == 0
        r_from, r_to = (r_out_mm, r_in_mm) if inward else (r_in_mm, r_out_mm)
        pieces = []
        if i > 0:
            pieces.append(arc_points(center_xy, r_from, angle, angular_sign * lead_arc_deg))
            angle += angular_sign * lead_arc_deg
        pieces.append(
            spiral_points(
                center_xy, r_from, r_to, turns_per_layer, angle, angular_sign, points_per_turn
            )
        )
        angle += angular_sign * 360.0 * turns_per_layer
        if i == len(layers) - 1:
            # Trailing arc back to the entry angle so terminals stack.
            done = (angle - start_angle_deg) % 360.0
            if angular_sign > 0:
                back = (360.0 - done) % 360.0
            else:
                back = -done
            if abs(back) > 1e-9:
                pieces.append(arc_points(center_xy, r_to, angle, back))
                angle += back
        pts = np.vstack(pieces)
        # Drop duplicated seam points between pieces.
        keep = np.ones(len(pts), dtype=bool)
        keep[1:] = np.linalg.norm(np.diff(pts, axis=0), axis=1) > 1e-9
        pts = pts[keep]
        paths.append(LayerPath(layer=layer, points=pts, start_r_mm=r_from, end_r_mm=r_to))
    return paths


def polyline_segments(points: np.ndarray) -> list[tuple[float, float, float, float]]:
    return [
        (float(points[i, 0]), float(points[i, 1]), float(points[i + 1, 0]), float(points[i + 1, 1]))
        for i in range(len(points) - 1)
    ]


def min_adjacent_turn_gap_mm(r_in_mm: float, r_out_mm: float, turns: int, width_mm: float) -> float:
    pitch = (r_out_mm - r_in_mm) / turns
    return pitch - width_mm
