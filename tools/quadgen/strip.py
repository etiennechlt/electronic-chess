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
    # 0603 clamps and bleeds in front of the entries (A above, B below), one 0402
    (5.4, ("clamp_a", "bleed_a", "bleed_b", "clamp_b", "damp_pu")),
    # SOT-23 pairs: the clamp diodes, then the FETs
    (8.9, ("dual_a", "dual_b")),
    (12.9, ("pfet", "nfet")),
    # the two SOD-123 diodes, then the 0805 damping resistor beside the upright
    # 0402 gate pulldown (the column is as wide as a SOD-123)
    (17.4, ("bus", "fly", (("gate_pd", -1.88, 90.0), ("damp_r", 0.67, 0.0)))),
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
BUSES_IN1 = (("5VA", 15.4, 0.6), ("VREF", 16.2, 0.4), ("DRIVE_BUS", 17.0, 0.5), ("VIN", 17.9, 0.6))
BUS_3V3_IN2 = ("3V3", 16.4, 0.4)

SHELF_GAP = 0.25


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
    # the FPC connector sits at lay.connector_xy rotated 270: its courtyard
    # width runs down the strip
    fpc_w, fpc_h = courtyard(load_footprint(q.link.footprint))
    fpc_bottom = lay.connector_xy[1] + fpc_w / 2.0
    link_bottom = max(y + 2.0 for _x, y, _r in packed.values())
    # test points: three at the bottom of the connector zone (VREF and the
    # buses run the whole strip on In1), one between the two muxes
    zone_bottom = st.connector_zone_mm - 0.5  # the first cell's parts start 0.4 mm lower
    tp_y = zone_bottom - 1.25
    tps = {"TP1": (2.05, tp_y), "TP2": (4.8, tp_y), "TP3": (7.55, tp_y), "TP4": (xc, top + 21.5)}
    for ref, (x, y) in tps.items():
        out[ref] = (x, y, 0.0)
    # decoupling and the inverter first, close to their packages, then the
    # rest: side columns beside the decoders, the gaps around the muxes, the
    # rows left in the connector zone, a column beside the amplifiers and a
    # flat row under them
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
    # decoder fanout (one via row) reaches 1.5 mm past the pad tips at 3.6;
    # (x0, x1, y0, y1, upright)
    mux_lo, mux_hi = out["U3"][1] - 3.1, out["U4"][1] + 3.1
    columns = [
        (x_lo, xc - 5.2, top + 0.8, top + 17.6, True),
        (xc + 5.2, x_hi, top + 0.8, top + 17.6, True),
        (x_lo, 10.0, fpc_bottom + 0.8, tp_y - 1.25 - 0.4, True),
        (10.4, x_hi, link_bottom + 0.8, zone_bottom, True),
        (16.7, x_hi, top + 29.5, top + 40.6, True),
        (x_lo, x_hi, top + 41.2, top + st.middle_zone_mm - 0.8, False),
        (x_lo, out["U3"][0] - 3.1 - 0.3, mux_lo, mux_hi, True),
        (out["U4"][0] + 3.1 + 0.3, x_hi, mux_lo, mux_hi, True),
        (out["U3"][0] + 3.1 + 0.3, out["U4"][0] - 3.1 - 0.3, top + 23.0, mux_hi, True),
    ]
    pending = list(rest)
    for cx0, cx1, cy0, cy1, upright in columns:
        if not pending:
            break
        placed = shelf_pack(pending, cx0, cx1, cy0, upright=upright)
        kept = {}
        for ref, (x, y, r) in placed.items():
            box = next(b for b in pending if b.ref == ref)
            h = box.w if abs(math.sin(math.radians(r))) > 0.5 else box.h
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
