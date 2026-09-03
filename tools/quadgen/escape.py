"""Escape stubs for fine-pitch pads.

A grid router cannot leave a 0.5 mm pitch pad: the cells right outside
the pad sit within the clearance of the neighbouring pads. Every pad of a
fine-pitch footprint therefore gets a short straight stub, along the
pad's long axis and away from the footprint center, drawn with the pad's
net before routing; the router then starts from the free end of the
stub. Stubs of neighbouring pads run parallel at the pad pitch, which is
legal for the stub width. A stub that would touch copper of another net
(a via, a track, a pad of the part next door) is not drawn.
"""

from __future__ import annotations

import math

from analoggen.fplib import Footprint, pad_abs_pos
from shapely.geometry import LineString, Point, box
from shapely.strtree import STRtree

FINE_PITCH_MM = 0.8
STUB_WIDTH_MM = 0.2
STUB_BEYOND_MM = 0.3
STUB_BEYOND_MIN_MM = 0.15
STUB_RUNWAY_MIN_MM = 0.3  # plain runway (lattice cells only) when no via fits
FANOUT_ROWS_MM = (0.8, 1.5)  # via rows past the stub end, alternating along the row
FANOUT_VIA_PAD_MM = 0.45  # small via: a 0.2 mm track passes one at the 0.5 mm pitch
FANOUT_VIA_DRILL_MM = 0.2
BAND_WIDTH_MM = 0.7  # escape band around each runway, closed to other nets
EXIT_MM = 2.0  # corridor claimed past the fanout via on the exit layer, no copper

# net, pad number, [start, end], runway length, fanout via at the runway end
Stub = tuple[str, str, list[tuple[float, float]], float, bool]


def _variant(stub: Stub, beyond: float, runway: float, via: bool) -> Stub:
    """The same stub ending `beyond` mm past the pad with the given runway."""
    net, num, (a, b), _rw, _via = stub
    full = math.hypot(b[0] - a[0], b[1] - a[1])
    k = (full - STUB_BEYOND_MM + beyond) / full
    end = (round(a[0] + (b[0] - a[0]) * k, 3), round(a[1] + (b[1] - a[1]) * k, 3))
    return (net, num, [a, end], runway, via)


def pad_pitch(fp: Footprint) -> float:
    """Smallest center distance between two SMD pads of the footprint."""
    pads = [p for p in fp.pads if p.kind == "smd"]
    best = math.inf
    for i, a in enumerate(pads):
        for b in pads[i + 1 :]:
            best = min(best, math.hypot(a.dx - b.dx, a.dy - b.dy))
    return best


def escape_stubs(
    fp: Footprint, x: float, y: float, rot: float, pad_nets: dict[str, str]
) -> list[Stub]:
    """Stubs for every connected pad of a fine-pitch footprint placed at
    (x, y, rot); empty for a coarse footprint."""
    if pad_pitch(fp) >= FINE_PITCH_MM:
        return []
    out: list[Stub] = []
    lateral: list[float] = []  # position along the row, to alternate the via rows
    for pad in fp.pads:
        if pad.kind != "smd" or not pad_nets.get(pad.number):
            continue
        if math.hypot(pad.dx, pad.dy) < 0.3 or max(pad.size) > 1.6 and min(pad.size) > 0.5:
            continue  # exposed pad (at the origin, or large): no stub
        px, py = pad_abs_pos(x, y, rot, pad)
        rx, ry = px - x, py - y
        th = math.radians(rot + pad.rot)
        # unit vectors of the pad's local axes in board coordinates
        ux, uy = math.cos(th), -math.sin(th)
        vx, vy = math.sin(th), math.cos(th)
        sw, sh = pad.size
        if abs(sw - sh) < 0.05:
            # square pad: radial, snapped to the dominant axis
            if abs(rx) > abs(ry):
                dx, dy = math.copysign(1.0, rx), 0.0
            else:
                dx, dy = 0.0, math.copysign(1.0, ry)
        else:
            dx, dy = (ux, uy) if sw > sh else (vx, vy)
            if dx * rx + dy * ry < 0:
                dx, dy = -dx, -dy
        length = max(sw, sh) / 2.0 + STUB_BEYOND_MM
        out.append(
            (
                pad_nets[pad.number],
                pad.number,
                [(px, py), (round(px + dx * length, 3), round(py + dy * length, 3))],
                0.0,
                True,
            )
        )
        # lateral coordinate: perpendicular to the stub, keyed by side
        lateral.append((round(dx, 3), round(dy, 3), -dy * px + dx * py))
    # alternate the two via rows along every side so neighbouring vias sit
    # two pitches apart and a runway track passes the other row's via
    # (one row is enough from a 0.6 mm pitch: a via and its clearance fit)
    one_row = pad_pitch(fp) >= 0.6
    by_side: dict[tuple[float, float], list[int]] = {}
    for k, (dx, dy, _t) in enumerate(lateral):
        by_side.setdefault((dx, dy), []).append(k)
    for ks in by_side.values():
        ks.sort(key=lambda k: lateral[k][2])
        for rank, k in enumerate(ks):
            net, num, pts, _rw, via = out[k]
            out[k] = (net, num, pts, FANOUT_ROWS_MM[0 if one_row else rank % 2], via)
    return out


def runway_end(pts: list[tuple[float, float]], runway: float) -> tuple[float, float]:
    """Point `runway` mm past the stub end, on its axis."""
    a, b = pts
    full = math.hypot(b[0] - a[0], b[1] - a[1])
    k = (full + runway) / full
    return (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k)


def stub_cells(router, pts: list[tuple[float, float]], runway: float) -> list[tuple[int, int]]:
    """Lattice cells along the stub and its runway."""
    a = pts[0]
    b = runway_end(pts, runway)
    n = max(4, int(math.hypot(b[0] - a[0], b[1] - a[1]) / router.grid * 2))
    return [
        router.cell(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n)
        for k in range(n + 1)
    ]


def exit_cells(router, pts: list[tuple[float, float]], runway: float) -> list[tuple[int, int]]:
    """Lattice cells of the exit corridor: from the fanout via onward, on
    the layer the route continues on."""
    a = runway_end(pts, runway)
    b = runway_end(pts, runway + EXIT_MM)
    n = max(4, int(EXIT_MM / router.grid * 2))
    return [
        router.cell(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n)
        for k in range(n + 1)
    ]


def claim_stubs(router, stubs, layer: str = "F.Cu", exit_layer: str | None = None) -> None:
    """Closes an escape band around every stub and runway to other nets on
    the top layer (free cells only: pads placed inside it keep their
    owner), then gives the stub and runway cells to their net, overriding
    the neighbours' inflation: on a 0.5 mm pitch every cell of a stub
    lies within the clearance of the next stub, so without this the
    router could never start, and without a deep band a bus routed
    earlier in front of the row walls it off (a bus must cross on another
    layer). `stubs` holds (net, [start, end], runway)."""
    # the painted band grows by its own inflation at both ends: stop it
    # short so the last runway cells and the cells past them stay free
    spill = BAND_WIDTH_MM / 2.0 + router.clr + router.track_half + router.grid
    for _net, pts, runway, via in stubs:
        if runway > spill + 0.2:
            a, b = pts[0], runway_end(pts, runway - spill - 0.2)
            router.soft_segment("__escape__", layer, a[0], a[1], b[0], b[1], BAND_WIDTH_MM)
        if via and exit_layer is not None and EXIT_MM > spill + 0.2:
            # the same band around the exit corridor: a route weaving between
            # two corridors would sit too close to the one routed later
            a, b = runway_end(pts, runway), runway_end(pts, runway + EXIT_MM - spill - 0.2)
            router.soft_segment("__escape__", exit_layer, a[0], a[1], b[0], b[1], BAND_WIDTH_MM)
    reclaim_stubs(router, stubs, layer, exit_layer)


def reclaim_stubs(router, stubs, layer: str = "F.Cu", exit_layer: str | None = None) -> None:
    """Gives the stub, runway, fanout via and exit corridor cells back to
    their nets. Called after every routed net too: a route laid along one
    runway inflates over the neighbouring runways at the 0.5 mm pitch
    although the real gap is legal, and without this they would be lost
    one after the other. The exit corridor, on `exit_layer`, guarantees a
    way out of the via row for every net whatever was routed before."""
    own = router.own[layer]
    for net, pts, runway, via in stubs:
        nid = router.nid(net)
        for i, j in stub_cells(router, pts, runway):
            own[j, i] = nid
        if via:
            i, j = router.cell(*runway_end(pts, runway))
            for la in router.layers:
                router.own[la][j, i] = nid
            if exit_layer is not None:
                # the corridor stops where another net's cells begin (two
                # packages facing each other): claims never fight
                own_x = router.own[exit_layer]
                band = router.net_ids.get("__escape__")
                for i, j in exit_cells(router, pts, runway):
                    if own_x[j, i] not in (router.FREE, router.MULTI, nid, band):
                        break
                    own_x[j, i] = nid


def free_stubs(stubs: list[Stub], res, clearance: float) -> list[Stub]:
    """Keeps the stubs whose stub, runway and fanout via stay `clearance`
    away from every F.Cu item of another net in `res` (pads, tracks, vias,
    holes) and from each other; a stub that does not fit loses its via,
    then gets shorter."""
    items: list[tuple[str, object]] = []  # top layer copper
    deep: list[tuple[str, object]] = []  # copper of any layer, for the via
    for p in res.pads:
        if p.layer not in ("F.Cu", "*.Cu"):
            deep.append((p.net, box(p.x - p.w / 2, p.y - p.h / 2, p.x + p.w / 2, p.y + p.h / 2)))
            continue
        g = box(-p.w / 2, -p.h / 2, p.w / 2, p.h / 2)
        rot = getattr(p, "rot", 0.0)
        if rot:
            from shapely import affinity

            g = affinity.rotate(g, -rot, origin=(0, 0))
        from shapely import affinity

        items.append((p.net, affinity.translate(g, p.x, p.y)))
    for t in res.tracks:
        g = LineString(t.pts).buffer(t.width / 2.0)
        (items if t.layer == "F.Cu" else deep).append((t.net, g))
    for v in res.vias:
        items.append((v.net, Point(v.x, v.y).buffer(v.pad / 2.0)))
    for hx, hy, hd in res.holes:
        items.append(("__hole__", Point(hx, hy).buffer(hd / 2.0 + 0.3)))
    tree = STRtree([g for _n, g in items])
    deep_tree = STRtree([g for _n, g in deep]) if deep else None
    kept: list[Stub] = []
    kept_geoms: list[tuple[str, object]] = []
    for full in stubs:
        net = full[0]
        # the stub with its fanout via first, then plain runways
        variants = [
            full,
            _variant(full, STUB_BEYOND_MM, STUB_RUNWAY_MIN_MM, False),
            _variant(full, STUB_BEYOND_MIN_MM, STUB_RUNWAY_MIN_MM, False),
        ]
        for stub in variants:
            # the runway is checked with the stub: a route may use it, and
            # with the via the runway is a track ending in the via
            end = runway_end(stub[2], stub[3])
            g = LineString([stub[2][0], end]).buffer(STUB_WIDTH_MM / 2.0)
            if stub[4]:
                g = g.union(Point(end).buffer(FANOUT_VIA_PAD_MM / 2.0))
            probe = g.buffer(clearance)
            blocked = any(
                items[int(j)][0] != net and items[int(j)][1].intersects(probe)
                for j in tree.query(probe)
            )
            if not blocked and stub[4] and deep_tree is not None:
                # the via crosses every layer: inner buses and back copper too
                vprobe = Point(end).buffer(FANOUT_VIA_PAD_MM / 2.0 + clearance)
                blocked = any(
                    deep[int(j)][0] != net and deep[int(j)][1].intersects(vprobe)
                    for j in deep_tree.query(vprobe)
                )
            if not blocked:
                blocked = any(n != net and kg.intersects(probe) for n, kg in kept_geoms)
            if not blocked:
                kept.append(stub)
                kept_geoms.append((net, g))
                break
    return kept
