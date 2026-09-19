"""Connectivity of the analog board, counted the way KiCad counts it.

The grid router thinks in cells and the finishing pass in joints, but
what decides whether a board can be ordered is the copper KiCad sees
once its zones are filled. Turning one into the other lives here:

- the copper of the board in the shape the shared bookkeeping of the
  quadrant reads (`as_items`): a pad is a rectangle on its layers, a
  track a buffered line on one layer, a via a disc on both;
- the pour the zone filler really produces (`plane_islands`): the zone
  outline less the copper of the other nets and its clearance, with the
  necks thinner than the filler's minimum width pinched off. A pour cut
  in two by a back-side track is two islands, and two islands join
  nothing across;
- the pieces of one net (`net_parts`), true copper per layer, which the
  finishing pass joins one pair at a time;
- the check a build owes the fab (`errors`): every net one piece of
  copper, pour included, which is exactly what KiCad reports as
  unconnected items.

The union-find itself is not rewritten here: it is the quadrant's
(`quadgen.connect`), shared so that both generators count the same way.
"""

from __future__ import annotations

from dataclasses import dataclass

from quadgen.connect import connectivity_check as _connectivity_check
from quadgen.connect import copper_components, pad_copper, pour_pieces
from shapely.geometry import LineString, Point, box
from shapely.ops import unary_union

LAYERS = ("F.Cu", "B.Cu")


@dataclass(frozen=True)
class _Track:
    net: str
    width: float
    pts: tuple
    layer: str


@dataclass(frozen=True)
class _Via:
    net: str
    x: float
    y: float
    pad: float


@dataclass(frozen=True)
class _Pad:
    net: str
    number: str
    ref: str
    x: float
    y: float
    w: float
    h: float
    layer: str
    shape: str = "rect"
    rratio: float = 0.0
    rot: float = 0.0


def pad_layers(pad) -> str:
    """The layer field the shared check reads: a plated pad is on both."""
    return "*.Cu" if pad.tht else "F.Cu"


def pad_shape(pad):
    """The copper a pad really carries, not the box around it.

    A track ending on the corner a rounded pad cuts off is open for
    KiCad, and the plated pads of the connectors are discs: the box
    around them would call both of those connected.
    """
    return pad_copper(
        _Pad(
            pad.net,
            pad.number,
            pad.ref,
            pad.x,
            pad.y,
            getattr(pad, "sx", 0.0) or pad.w,
            getattr(pad, "sy", 0.0) or pad.h,
            pad_layers(pad),
            getattr(pad, "shape", "rect"),
            getattr(pad, "rratio", 0.0),
            getattr(pad, "angle", 0.0),
        )
    )


def as_items(pads, tracks, vias, via_d: float):
    """The generator's copper, adapted to the shared bookkeeping."""
    tr = [_Track(net, w, tuple(pts), layer) for net, w, pts, layer in tracks]
    vi = [_Via(net, x, y, via_d) for net, x, y in vias]
    pa = [
        _Pad(
            p.net,
            p.number,
            p.ref,
            p.x,
            p.y,
            getattr(p, "sx", 0.0) or p.w,
            getattr(p, "sy", 0.0) or p.h,
            pad_layers(p),
            getattr(p, "shape", "rect"),
            getattr(p, "rratio", 0.0),
            getattr(p, "angle", 0.0),
        )
        for p in pads
        if p.net
    ]
    return tr, vi, pa


def copper_of(net: str, pads, tracks, vias, via_d: float) -> list:
    """Items of one net as (layers, copper, label) triples."""
    items = []
    for p in pads:
        if p.net != net:
            continue
        layers = LAYERS if p.tht else ("F.Cu",)
        items.append((layers, pad_shape(p), f"{p.ref}.{p.number}"))
    for tnet, w, pts, layer in tracks:
        if tnet == net:
            items.append(((layer,), LineString(pts).buffer(w / 2.0), None))
    for vnet, x, y in vias:
        if vnet == net:
            items.append((LAYERS, Point(x, y).buffer(via_d / 2.0), None))
    return items


def foreign_back_copper(net: str, pads, tracks, vias, via_d: float) -> list:
    """Copper of the other nets on the pour's layer, holes included."""
    out = []
    for p in pads:
        if p.net == net or not p.tht:
            continue
        out.append(box(p.x - p.w / 2.0, p.y - p.h / 2.0, p.x + p.w / 2.0, p.y + p.h / 2.0))
    for tnet, w, pts, layer in tracks:
        if tnet != net and layer == "B.Cu":
            out.append(LineString(pts).buffer(w / 2.0))
    for vnet, x, y in vias:
        if vnet != net:
            out.append(Point(x, y).buffer(via_d / 2.0))
    return out


def plane_islands(
    pads,
    tracks,
    vias,
    region,
    via_d: float,
    clearance: float,
    min_width: float,
    net: str = "GND",
) -> list:
    """What the zone filler leaves of `region` for `net` on the back side."""
    return pour_pieces(
        region, foreign_back_copper(net, pads, tracks, vias, via_d), clearance, min_width
    )


def net_parts(net: str, pads, tracks, vias, via_d: float, islands=None) -> list:
    """Pieces of a net, each as (front copper, back copper, anchored).

    An island of the pour is a piece like any other: its back copper is
    the island, and what it joins is what its own copper covers. A piece
    made of pour alone is not anchored: the filler drops it and nothing
    is owed to it, so the finishing pass leaves it where it is.
    """
    items = copper_of(net, pads, tracks, vias, via_d)
    drawn = len(items)
    for island in islands or []:
        items.append((("B.Cu",), island, None))
    parts = []
    for comp in copper_components(items):
        front = [items[k][1] for k in comp if "F.Cu" in items[k][0]]
        back = [items[k][1] for k in comp if "B.Cu" in items[k][0]]
        parts.append(
            (
                unary_union(front) if front else None,
                unary_union(back) if back else None,
                any(k < drawn for k in comp),
            )
        )
    return parts


def errors(pads, tracks, vias, via_d: float, islands=None, net: str = "GND") -> list[str]:
    """Nets left in pieces, in the words the build prints and KiCad counts."""
    tr, vi, pa = as_items(pads, tracks, vias, via_d)
    pours = {net: ("B.Cu", unary_union(islands))} if islands else None
    return _connectivity_check(tr, vi, pa, LAYERS, pours)
