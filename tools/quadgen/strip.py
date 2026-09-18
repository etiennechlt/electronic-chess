"""Placement of the front-end strip: coil cells, decoders, muxes, chain,
rail switch, test points. Positions in board millimeters (y down).

A coil cell is a fixed template repeated in front of every coil's
escape (layout.cell_ys); everything else is shelf-packed into the
middle zone from the footprint courtyards, so nothing overlaps by
construction. Signal hygiene: the sensitive M lines (after the clamps,
before the muxes) run on B.Cu, the gate lines on In2, the pulse rail
and the supplies on In1 along the east side of the strip.
"""

from __future__ import annotations

import functools
import math
from dataclasses import dataclass

from analoggen.circuit import Circuit
from analoggen.fplib import Footprint, load_footprint
from analoggen.sexp import atom, find_all, find_one, parse

from chessboard_calc.config import BoardConfig

from .circuit import cell_refs
from .layout import Layout

Placement = tuple[float, float, float]  # x, y, rotation

# Cell floor plan: columns of parts stacked top to bottom from their real
# courtyards, centered on the cell (x of the column center, then rows; a
# row is one role centered in the column, or several (role, dx, rot)
# side by side). Column heights are checked against the cell pitch.
CELL_COLUMNS: tuple[tuple[float, tuple], ...] = (
    # 0603 clamps and bleeds in front of the entries (A above, B below), the
    # 0402 gate pulldown under them
    (5.4, ("clamp_a", "bleed_a", "bleed_b", "clamp_b", "gate_pd")),
    # the two SOT-323 clamp diodes and the 0805 damping resistor
    (8.9, ("dual_a", "dual_b", "damp_r")),
    # SOT-23 FETs
    (12.9, ("pfet", "nfet")),
    # the three SOD-123 diodes: bus, flyback, freewheel
    (17.4, ("bus", "fly", "free")),
)
CELL_STACK_GAP = 0.1


def cell_template(cfg: BoardConfig, circuit: Circuit) -> dict[str, tuple[float, float, float]]:
    """Role -> (x, dy, rot) of every part of a coil cell, dy from the cell
    center; every cell uses the same parts so cell 1 sizes the template."""
    pitch = cfg.plateau.quadrant.strip.cell_pitch_mm
    by_ref = {c.ref: c for c in circuit.components}
    cr = cell_refs(1)
    out: dict[str, tuple[float, float, float]] = {}
    for x, rows in CELL_COLUMNS:
        items = [((row,) if isinstance(row, str) else row) for row in rows]
        heights = []
        for row in items:
            hs = []
            for it in row:
                role, rot = (it, 0.0) if isinstance(it, str) else (it[0], it[2])
                w, h = courtyard(load_footprint(by_ref[cr[role]].part.footprint))
                hs.append(w if abs(math.sin(math.radians(rot))) > 0.5 else h)
            heights.append(max(hs))
        total = sum(heights) + CELL_STACK_GAP * (len(heights) - 1)
        if total > pitch:
            raise ValueError(f"cell column at x = {x}: {total:.2f} mm tall for a {pitch} mm cell")
        y = -total / 2.0
        for row, h in zip(items, heights, strict=True):
            for it in row:
                role, dx, rot = (it, 0.0, 0.0) if isinstance(it, str) else it
                out[role] = (round(x + dx, 3), round(y + h / 2.0, 3), rot)
            y += h + CELL_STACK_GAP
    return out


# In1 supply buses (net, x, width) and In2 logic rail, along the strip.
# Every bus needs a via channel: a via on it crosses all four layers, so
# the buses of the other layer must stay 0.375 mm away from its center
# (via pad 0.225 plus the clearance) and those of its own layer as far as
# the pads demand. Packed tighter, a bus is drawn but unreachable: the
# cells and the chain then hang off it, which is what the DRC counted.
# East of VIN the top layer carries the diode pads of the cells (to
# x = 19.5) and In2 the 5 V grid of the LEDs (from x = 17.1).
BUSES_IN1 = (
    ("5VA", 13.2, 0.6),
    ("VREF", 14.2, 0.4),  # clear of the east fanout vias of the decoders
    ("DRIVE_BUS", 15.6, 0.5),
    ("VIN", 16.55, 0.6),
)
BUS_3V3_IN2 = ("3V3", 12.2, 0.4)

SHELF_GAP = 0.25

# The passives by the package they serve, with the regions of the strip
# they go to, in order of preference: the instrumentation amplifier's
# input network beside the mux, above the amplifiers; the filters, the
# output stage and the reference divider beside and under the
# amplifiers; the mux decoupling beside the mux; the decoders' decoupling
# and their inverter beside the decoders; the bulk 5VA and the 3V3 and
# 5VA decoupling of the link zone by the link. What a group's regions
# cannot hold goes wherever room is left.
GROUPS: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("C14", "C15", "R12", "R13", "R14", "C16"), ("mux", "amp_col", "bottom")),
    (
        (
            "C17",
            "C18",
            "R15",
            "R16",
            "R17",
            "R18",
            "R19",
            "R20",
            "C19",
            "C20",
            "R21",
            "R22",
            "C21",
            "R23",
            "R24",
            "C22",
            "C23",
            "R25",
            "C24",
            "R5",
            "R6",
            "C13",
        ),
        ("amp_col", "bottom", "mux"),
    ),
    (("C7", "C8"), ("mux", "dec")),
    (("U6", "C5", "C6", "C3"), ("dec",)),
    (("C2", "C4"), ("link", "dec")),
)


@dataclass
class Box:
    ref: str
    w: float
    h: float
    rot: float


@functools.cache
def _courtyard_box(lib_id: str, raw: str) -> tuple[float, float, float, float]:
    xs: list[float] = []
    ys: list[float] = []
    for item in parse(raw):
        if not isinstance(item, list) or not item:
            continue
        tag = item[0]
        if tag not in ("fp_line", "fp_rect", "fp_poly", "fp_circle", "fp_arc"):
            continue
        layer = find_one(item, "layer")
        if layer is None or atom(layer[1]) != "F.CrtYd":
            continue
        if tag == "fp_poly":
            for xy in find_all(find_one(item, "pts"), "xy"):
                xs.append(float(xy[1]))
                ys.append(float(xy[2]))
        elif tag == "fp_circle":
            c, e = find_one(item, "center"), find_one(item, "end")
            r = math.hypot(float(e[1]) - float(c[1]), float(e[2]) - float(c[2]))
            xs += [float(c[1]) - r, float(c[1]) + r]
            ys += [float(c[2]) - r, float(c[2]) + r]
        else:
            for key in ("start", "mid", "end"):
                node = find_one(item, key)
                if node is not None:
                    xs.append(float(node[1]))
                    ys.append(float(node[2]))
    if xs:
        return min(xs), min(ys), max(xs), max(ys)
    raise ValueError(f"{lib_id}: no F.CrtYd outline")


def courtyard_box(fp: Footprint) -> tuple[float, float, float, float]:
    """(xmin, ymin, xmax, ymax) of the footprint's courtyard in its own
    frame, from every F.CrtYd primitive whatever the attribute order of
    the library file (KiCad 6 and 7 differ). The origin is not always the
    center: the ESP32 modules keep theirs near the pads, and their
    courtyard is the antenna clearance area, far larger than the body."""
    return _courtyard_box(fp.lib_id, fp.raw)


def courtyard(fp: Footprint) -> tuple[float, float]:
    """Width and height of the footprint's courtyard."""
    x0, y0, x1, y1 = courtyard_box(fp)
    return x1 - x0, y1 - y0


def placed_box(fp: Footprint, x: float, y: float, rot: float) -> tuple[float, float, float, float]:
    """Axis-aligned bounds of the courtyard once placed at (x, y, rot)."""
    import math

    x0, y0, x1, y1 = courtyard_box(fp)
    th = math.radians(rot)
    pts = []
    for cx, cy in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
        pts.append(
            (x + cx * math.cos(th) + cy * math.sin(th), y - cx * math.sin(th) + cy * math.cos(th))
        )
    return (
        min(px for px, _ in pts),
        min(py for _, py in pts),
        max(px for px, _ in pts),
        max(py for _, py in pts),
    )


def shelf_pack(
    boxes: list[Box], x0: float, x1: float, y0: float, upright: bool = False
) -> dict[str, Placement]:
    """Rows top to bottom, items left to right, tallest items first.
    `upright` turns every item so its narrow side runs along the row."""
    out: dict[str, Placement] = {}
    if upright:
        boxes = [Box(b.ref, b.h, b.w, (b.rot + 90.0) % 180.0) if b.w > b.h else b for b in boxes]
    boxes = sorted(boxes, key=lambda b: (-b.h, -b.w))
    y = y0
    while boxes:
        # the tallest box that fits the column width leads the row; boxes
        # wider than the column are left out (the caller places them elsewhere)
        leader = next((b for b in boxes if b.w <= x1 - x0), None)
        if leader is None:
            break
        row_h = leader.h
        x = x0
        rest = []
        for b in boxes:
            if b.h <= row_h and x + b.w <= x1:
                out[b.ref] = (round(x + b.w / 2.0, 3), round(y + row_h / 2.0, 3), b.rot)
                x += b.w + SHELF_GAP
            else:
                rest.append(b)
        boxes = rest
        y += row_h + SHELF_GAP
    return out


def _pack_regions(boxes: list[Box], keys, regions, next_y: dict, out: dict) -> list[Box]:
    """Packs `boxes` into the regions named by `keys`, in order, each from
    its next free row (`next_y`, kept across calls); returns the boxes
    that fit nowhere."""
    pending = list(boxes)
    for key in keys:
        for k, (cx0, cx1, cy0, cy1, upright) in enumerate(regions[key]):
            if not pending:
                return pending
            y0 = next_y.get((key, k), cy0)
            if y0 >= cy1:
                continue
            placed = shelf_pack(pending, cx0, cx1, y0, upright=upright)
            kept = {}
            for ref, (x, y, r) in placed.items():
                box = next(b for b in pending if b.ref == ref)
                h = box.w if abs(math.sin(math.radians(r))) > 0.5 else box.h
                if y + h / 2.0 <= cy1:
                    kept[ref] = (x, y, r)
                    next_y[(key, k)] = max(next_y.get((key, k), cy0), y + h / 2.0 + SHELF_GAP)
            out.update(kept)
            pending = [b for b in pending if b.ref not in kept]
    return pending


def strip_placements(cfg: BoardConfig, lay: Layout, circuit: Circuit) -> dict[str, Placement]:
    q = cfg.plateau.quadrant
    by_ref = {c.ref: c for c in circuit.components}
    out: dict[str, Placement] = {}
    # coil cells
    template = cell_template(cfg, circuit)
    for coil in lay.coils:
        cr = cell_refs(coil.idx + 1)
        for role, (x, dy, rot) in template.items():
            out[cr[role]] = (x, round(coil.cell_y + dy, 3), rot)
    # middle zone: the two TSSOP decoders stacked on the strip axis (pads
    # east and west, fanout 1.9 mm past the pad tips), the two LFCSP muxes
    # side by side below them, the amplifiers under the muxes, and the
    # passives in the side columns the decoder fanouts leave free
    st = q.strip
    # middle zone starts under the cells of band 0 (2 n of them)
    top = lay.cell_ys[2 * lay.n - 1] + st.cell_pitch_mm / 2.0
    xc = lay.strip_w / 2.0
    x_lo, x_hi = 0.8, lay.strip_w - 0.8
    out["U1"] = (xc, top + 4.6, 0.0)  # 74HC4514, TSSOP-24 upright
    out["U2"] = (xc, top + 13.2, 0.0)  # 74HC154
    # the muxes face each other: half a pitch of offset interleaves their vias
    # the muxes stand 5.6 mm from their edge: their fine pads escape west
    # and east with a fanout via 4.65 mm out, which needs 0.875 mm of board
    out["U3"] = (5.6, top + 22.8, 0.0)  # ADG1607 coils 1..8
    two_muxes = "U4" in by_ref
    if two_muxes:
        out["U4"] = (lay.strip_w - 5.6, top + 23.3, 0.0)  # ADG1607 coils 9..16
    out["U5"] = (5.0, top + 32.2, 0.0)  # AD8421
    out["U7"] = (12.6, top + 32.2, 0.0)  # OPA2810 HP + LP
    out["U8"] = (5.0, top + 38.0, 0.0)  # OPA2810 VREF buffer + output
    out["R9"] = (13.5, top + 38.0, 0.0)  # 10R 2010 on the pulse rail, beside U8

    def box_of(comp):
        w, h = courtyard(load_footprint(comp.part.footprint))
        return Box(comp.ref, w, h, 0.0)

    # rail switch, bulk capacitor and output clamp next to the FPC, east of
    # the locating pin hole: VIN, PULSE_EN and AMP_OUT arrive there
    near_link = ["Q1", "Q2", "R7", "R8", "R10", "C1", "D3"]
    hole_x, hole_y = lay.pin_hole_xy
    packed = shelf_pack(
        [box_of(by_ref[r]) for r in near_link], 10.4, x_hi, hole_y + 2.6, upright=True
    )
    out.update(packed)
    if max(y for _x, y, _r in packed.values()) > st.connector_zone_mm - 1.0:
        raise ValueError("connector zone overflow")
    # the FPC connector sits at lay.connector_xy rotated 270: its courtyard
    # width runs down the strip
    fpc_w, fpc_h = courtyard(load_footprint(q.link.footprint))
    fpc_bottom = lay.connector_xy[1] + fpc_w / 2.0
    link_bottom = max(y + 2.0 for _x, y, _r in packed.values())
    # test points: three at the bottom of the connector zone (VREF and the
    # buses run the whole strip on In1), one between the two muxes
    zone_bottom = st.connector_zone_mm - 0.5  # the first cell's parts start 0.4 mm lower
    tp_y = zone_bottom - 1.25
    # the rows under the amplifiers stop where the middle zone does, unless
    # no cell follows it (the reduced quadrant, whose strip is longer than
    # its play area): there they run to the board edge
    zone_end = top + st.middle_zone_mm - 0.8
    tail = lay.board_h - q.routing.edge_clearance_mm - 0.8
    bottom = zone_end if any(y > zone_end for y in lay.cell_ys) else tail
    tps = {
        "TP1": (2.05, tp_y),
        "TP2": (4.8, tp_y),
        "TP3": (7.55, tp_y),
        "TP4": (xc, top + 21.0),
    }
    for ref, (x, y) in tps.items():
        out[ref] = (x, y, 0.0)
    # the rest by affinity: every passive near the package it serves, in
    # the regions the fixed parts leave free (x0, x1, y0, y1, upright).
    # Decoder fanout (one via row) reaches 1.5 mm past the pad tips at 3.6;
    # the mux fanout (two via rows) reaches 4.7 from the package center.
    mux_lo = out["U3"][1] - 3.1
    mux_hi = (out["U4"][1] if two_muxes else out["U3"][1]) + 3.1
    # one mux leaves its whole east side free, two leave the gap between
    # them and the strip of board east of the second
    mux_side = [(x_lo, out["U3"][0] - 3.4, mux_lo, mux_hi, True)] + (
        [
            (out["U4"][0] + 3.4, x_hi, mux_lo, mux_hi, True),
            (out["U3"][0] + 3.4, out["U4"][0] - 3.4, top + 23.0, mux_hi, True),
        ]
        if two_muxes
        else [(max(out["U3"][0] + 5.2, xc + 1.5), x_hi, mux_lo, mux_hi, True)]
    )
    regions = {
        "link": [
            (x_lo, 10.0, fpc_bottom + 0.8, tp_y - 1.25 - 0.4, True),
            (10.4, x_hi, link_bottom + 0.8, zone_bottom, True),
        ],
        "dec": [
            (x_lo, xc - 5.2, top + 0.8, top + 17.6, True),
            (xc + 5.2, x_hi, top + 0.8, top + 17.6, True),
            (x_lo, x_hi, top + 17.8, top + 19.6, False),  # the row under them
        ],
        "mux": mux_side,
        "amp_col": [
            (x_lo, x_hi, top + 26.65, top + 29.25, False),  # the row between muxes and amplifiers
            (16.7, x_hi, top + 29.5, top + 40.6, True),
            (8.75, 10.3, top + 35.2, top + 40.6, True),  # between the buffer and the rail resistor
        ],
        # the rows under the amplifiers, flat so a short one still holds a
        # row of passives; they run to the board edge when nothing follows
        "bottom": [(x_lo, x_hi, top + 41.2, bottom, False)],
    }
    next_y: dict[tuple[str, int], float] = {}
    known = {ref for refs, _regions in GROUPS for ref in refs}
    leftovers: list[Box] = []
    for refs, keys in GROUPS:
        boxes = [box_of(by_ref[r]) for r in refs if r in by_ref and r not in out]
        leftovers += _pack_regions(boxes, keys, regions, next_y, out)
    leftovers += sorted(
        (
            box_of(comp)
            for comp in circuit.components
            if comp.ref not in out
            and comp.ref not in known
            and not comp.ref.startswith(("LD", "CL", "NT", "J"))
        ),
        key=lambda b: -(b.w * b.h),
    )
    # what a group's own regions could not hold goes to any room left
    leftovers = _pack_regions(leftovers, tuple(regions), regions, next_y, out)
    if leftovers:
        raise ValueError(f"middle zone overflow: {[b.ref for b in leftovers]} do not fit")
    # fixed places overlap guard
    _check_no_overlap(out, by_ref)
    return out


def _check_no_overlap(placements: dict[str, Placement], by_ref) -> None:
    boxes = []
    for ref, (x, y, rot) in placements.items():
        comp = by_ref.get(ref)
        if comp is None:
            continue
        w, h = courtyard(load_footprint(comp.part.footprint))
        if abs(math.sin(math.radians(rot))) > 0.5:
            w, h = h, w
        boxes.append((ref, x - w / 2, y - h / 2, x + w / 2, y + h / 2))
    for i, a in enumerate(boxes):
        for b in boxes[i + 1 :]:
            if (
                a[1] < b[3] - 0.01
                and b[1] < a[3] - 0.01
                and a[2] < b[4] - 0.01
                and b[2] < a[4] - 0.01
            ):
                raise ValueError(f"courtyards overlap: {a[0]} and {b[0]}")
