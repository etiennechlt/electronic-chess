"""Courtyards: the room each footprint claims, and the pairs that clash.

A courtyard is the area a part needs for itself, nozzle and fingers
included. Two that overlap are not a short circuit, so no connectivity
check and no copper DRC says a word about them, and yet they are what
turns an assembly into a rework: parts that cannot both be placed, or
a capacitor a reflow nozzle pushes off its pads.

KiCad reports them, so the build does too, from the same geometry: the
`F.CrtYd` lines, rectangles, circles and polygons of each footprint,
closed into a polygon, rotated and placed. The rule is KiCad's own,
any overlapping area at all, and the answer has matched it pair for
pair.
"""

from __future__ import annotations

import functools
import math

from shapely import affinity
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import polygonize, unary_union

from .fplib import load_footprint
from .sexp import atom, find_one, parse

SHAPES = ("fp_line", "fp_rect", "fp_circle", "fp_arc", "fp_poly")
FRONT = "F.CrtYd"


def _xy(node) -> tuple[float, float]:
    return float(node[1]), float(node[2])


def _on_front(node) -> bool:
    layer = find_one(node, "layer")
    return layer is not None and atom(layer[1]) == FRONT


@functools.cache
def footprint_courtyard(lib_id: str) -> Polygon | None:
    """The front courtyard of a footprint, in its own frame."""
    tree = parse(load_footprint(lib_id).raw)
    segments, shapes = [], []
    for node in tree:
        if not isinstance(node, list) or not node or node[0] not in SHAPES:
            continue
        if not _on_front(node):
            continue
        if node[0] in ("fp_line", "fp_arc"):
            start, end = find_one(node, "start"), find_one(node, "end")
            if start and end:
                segments.append(LineString([_xy(start), _xy(end)]))
        elif node[0] == "fp_rect":
            (x0, y0), (x1, y1) = _xy(find_one(node, "start")), _xy(find_one(node, "end"))
            shapes.append(box(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)))
        elif node[0] == "fp_circle":
            (cx, cy), (ex, ey) = _xy(find_one(node, "center")), _xy(find_one(node, "end"))
            shapes.append(Point(cx, cy).buffer(math.hypot(ex - cx, ey - cy)))
        else:
            pts = find_one(node, "pts")
            xy = [_xy(p) for p in pts[1:]] if pts else []
            if len(xy) >= 3:
                shapes.append(Polygon(xy))
    if segments:
        closed = list(polygonize(unary_union(segments)))
        # an outline drawn open (a connector that reaches past its pads)
        # still claims what it encloses
        shapes.extend(closed or [unary_union(segments).convex_hull])
    if not shapes:
        return None
    merged = unary_union(shapes)
    if merged.geom_type == "Polygon":
        return merged
    return unary_union([g.convex_hull for g in merged.geoms])


def placed_courtyards(circuit, placements) -> dict:
    """The courtyard of every component, placed on the board."""
    out = {}
    for comp in circuit.components:
        g = footprint_courtyard(comp.part.footprint)
        if g is None or g.is_empty:
            continue
        x, y, rot = placements[comp.ref]
        if rot:
            g = affinity.rotate(g, -rot, origin=(0, 0))
        out[comp.ref] = affinity.translate(g, x, y)
    return out


def courtyard_errors(circuit, placements) -> list[str]:
    """Pairs of parts whose courtyards overlap, worst first."""
    yards = placed_courtyards(circuit, placements)
    refs = sorted(yards)
    found = []
    for i, a in enumerate(refs):
        for b in refs[i + 1 :]:
            ga, gb = yards[a], yards[b]
            if not ga.intersects(gb):
                continue
            area = ga.intersection(gb).area
            if area > 1e-9:
                found.append((area, a, b))
    return [
        f"{a} and {b}: courtyards overlap by {area:.3f} mm2"
        for area, a, b in sorted(found, reverse=True)
    ]
