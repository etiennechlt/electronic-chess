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

import math
from dataclasses import dataclass

from analoggen.circuit import Circuit
from analoggen.fplib import Footprint, load_footprint

from chessboard_calc.config import BoardConfig

from .circuit import cell_refs
from .layout import Layout

Placement = tuple[float, float, float]  # x, y, rotation

# Cell template, x absolute within the strip, y relative to the cell center.
CELL_TEMPLATE: dict[str, tuple[float, float, float]] = {
    # cell height 7.4 (y within +-3.7); left column, 0603, pitch 1.6 (courtyard 1.46)
    "clamp_a": (5.4, -2.4, 0.0),
    "bleed_a": (5.4, -0.8, 0.0),
    "bleed_b": (5.4, 0.8, 0.0),
    "clamp_b": (5.4, 2.4, 0.0),
    # two columns of SOT-23 (courtyard 3.85 x 3.00), 0402 pulldowns between the rows
    "dual_a": (8.9, -2.15, 0.0),
    "pfet": (12.9, -2.15, 0.0),
    "dual_b": (8.9, 2.15, 0.0),
    "nfet": (12.9, 2.15, 0.0),
    "damp_pu": (8.9, 0.0, 0.0),
    "gate_pd": (12.9, 0.0, 0.0),
    # right column: the two diodes (SOD-123, 4.7 x 1.7) and the 0805 damping resistor
    "bus": (17.4, -2.85, 0.0),
    "fly": (17.4, -1.05, 0.0),
    "damp_r": (17.4, 0.85, 0.0),
}

# In1 supply buses (net, x, width) and In2 logic rail, along the strip.
BUSES_IN1 = (("5VA", 15.4, 0.6), ("VREF", 16.2, 0.4), ("DRIVE_BUS", 17.0, 0.5), ("VIN", 17.9, 0.6))
BUS_3V3_IN2 = ("3V3", 16.4, 0.4)

SHELF_GAP = 0.25


@dataclass
class Box:
    ref: str
    w: float
    h: float
    rot: float


def courtyard_box(fp: Footprint) -> tuple[float, float, float, float]:
    """(xmin, ymin, xmax, ymax) of the footprint's courtyard in its own
    frame (fallback: pads plus 0.5 mm). The origin is not always the
    center: the ESP32 modules keep theirs near the pads."""
    import re

    xs, ys = [], []
    for m in re.finditer(
        r"\(fp_line \(start ([-\d.]+) ([-\d.]+)\) \(end ([-\d.]+) ([-\d.]+)\)"
        r' \(layer "F\.CrtYd"\)',
        fp.raw,
    ):
        xs += [float(m.group(1)), float(m.group(3))]
        ys += [float(m.group(2)), float(m.group(4))]
    if xs:
        return min(xs), min(ys), max(xs), max(ys)
    xs = [p.dx + s * p.size[0] / 2 for p in fp.pads for s in (-1, 1)]
    ys = [p.dy + s * p.size[1] / 2 for p in fp.pads for s in (-1, 1)]
    return min(xs) - 0.25, min(ys) - 0.25, max(xs) + 0.25, max(ys) + 0.25


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
        row_h = boxes[0].h
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


def strip_placements(cfg: BoardConfig, lay: Layout, circuit: Circuit) -> dict[str, Placement]:
    q = cfg.plateau.quadrant
    by_ref = {c.ref: c for c in circuit.components}
    out: dict[str, Placement] = {}
    # coil cells
    for coil in lay.coils:
        cr = cell_refs(coil.idx + 1)
        for role, (x, dy, rot) in CELL_TEMPLATE.items():
            out[cr[role]] = (x, round(coil.cell_y + dy, 3), rot)
    # middle zone: the two TSSOP decoders stacked on the strip axis (pads
    # east and west, fanout 1.9 mm past the pad tips), the two LFCSP muxes
    # side by side below them, the amplifiers under the muxes, and the
    # passives in the side columns the decoder fanouts leave free
    st = q.strip
    top = lay.cell_ys[7] + st.cell_pitch_mm / 2.0  # middle zone starts under band 0 cells
    xc = lay.strip_w / 2.0
    x_lo, x_hi = 0.8, lay.strip_w - 0.8
    out["U1"] = (xc, top + 4.6, 0.0)  # 74HC4514, TSSOP-24 upright
    out["U2"] = (xc, top + 13.2, 0.0)  # 74HC154
    # the muxes face each other: half a pitch of offset interleaves their vias
    out["U3"] = (5.4, top + 22.8, 0.0)  # ADG1607 coils 1..8
    out["U4"] = (lay.strip_w - 5.4, top + 23.3, 0.0)  # ADG1607 coils 9..16
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
    # decoupling and the inverter first, close to their packages, then the
    # rest: side columns beside the decoders, a row under the amplifiers
    first = ["U6", "C5", "C6", "C3", "C7", "C8"]
    rest = [box_of(by_ref[r]) for r in first] + sorted(
        (
            box_of(comp)
            for comp in circuit.components
            if comp.ref not in out
            and comp.ref not in first
            and not comp.ref.startswith(("LD", "CL", "NT", "J"))
        ),
        key=lambda b: -(b.w * b.h),
    )
    # the FPC connector sits at lay.connector_xy rotated 270: its courtyard
    # width runs down the strip
    fpc_w, fpc_h = courtyard(load_footprint(q.link.footprint))
    fpc_bottom = lay.connector_xy[1] + fpc_w / 2.0
    link_bottom = max(y + 2.0 for _x, y, _r in packed.values())
    # decoder fanout (one via row) reaches 1.5 mm past the pad tips at 3.6
    columns = [
        (x_lo, xc - 5.2, top + 0.8, top + 17.6),
        (xc + 5.2, x_hi, top + 0.8, top + 17.6),
        (x_lo, 10.0, fpc_bottom + 0.8, st.connector_zone_mm - 0.8),
        (10.4, x_hi, link_bottom + 0.8, st.connector_zone_mm - 0.8),
        (16.7, x_hi, top + 29.5, top + 40.6),
        (x_lo, x_hi, top + 41.2, top + st.middle_zone_mm - 0.8),
    ]
    pending = list(rest)
    for cx0, cx1, cy0, cy1 in columns:
        if not pending:
            break
        placed = shelf_pack(pending, cx0, cx1, cy0, upright=True)
        kept = {}
        for ref, (x, y, r) in placed.items():
            box = next(b for b in pending if b.ref == ref)
            h = max(box.w, box.h)  # upright: the long side runs down the column
            if y + h / 2.0 <= cy1:
                kept[ref] = (x, y, r)
        out.update(kept)
        pending = [b for b in pending if b.ref not in kept]
    if pending:
        raise ValueError(f"middle zone overflow: {[b.ref for b in pending]} do not fit")
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
