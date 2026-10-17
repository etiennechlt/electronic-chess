"""The tag panel of the Hall plus RFID demonstrator (`tag-demo`, note 27):
one round tag per piece base size and trim, `demo.tags.per_variant`
discs of each, held in a frame by mouse-bite tabs, plus the field pickup
tag of note 25 (paragraph 5). Geometry from `chessboard_calc.nfc`
(tag_geometry: disc, copper diameters, turns, track) and the yaml
(`hall_rfid.mockup.tags`, `hall_rfid.demo.tags`, `hall_rfid.mockup.pickup`).

One tag: a two-layer coil, the top spiral from the centre outward, a via
on the rim, the bottom spiral back inward, both ends at the centre where
the chip sits (NT3H2111 in TSSOP8, LA pin 1 and LB pin 8 on the same
side of the package), and an 0402 trim capacitor across LA and LB
(not fitted on the bare variant). The coil copper and both chip pins are
one net: a copper inductor is a trace to KiCad.

The panel: side rails for the assembly machine, top and bottom bars,
discs in rows joined to their neighbours and to the rails by 2.5 mm
tabs, each tab bitten at both ends by 0.5 mm holes so a disc snaps out
without a nub. The outline is the union of frame, tabs and discs, drawn
on Edge.Cuts as closed polylines (its voids included).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from analoggen.fplib import load_footprint, pad_abs_pos, place_footprint
from coilgen.geometry import spiral_points
from coilgen.kicad import Board
from coilgen.project import DesignRules
from shapely.geometry import Point, box
from shapely.ops import unary_union

from chessboard_calc import nfc
from chessboard_calc.config import BoardConfig

NAME = "tag-demo"
RAIL_MM = 5.0
BAR_MM = 3.0
GAP_MM = 2.5  # between two discs, and disc to rail or bar
TAB_MM = 2.5  # tab width across the gap
BITE_D_MM = 0.5  # mouse bite holes
BITE_PITCH_MM = 0.75
BITE_IN_MM = 0.2  # hole centre outside the disc edge: half a hole in the tab
VIA_PAD_MM = 0.5
VIA_DRILL_MM = 0.3
LEAD_MM = 0.25  # the leads between coil ends, chip and capacitor
CLEARANCE_MM = 0.15
EDGE_CLEARANCE_MM = 0.3
CIRCLE_SEGMENTS = 32  # per quarter, Edge.Cuts polygon of a disc
CHIP_FP = "Package_SO:TSSOP-8_3x3mm_P0.65mm"
TRIM_FP = "Capacitor_SMD:C_0402_1005Metric"
FIDUCIAL_FP = "Fiducial:Fiducial_1mm_Mask2mm"
PICKUP_FP = {
    "D": "Diode_SMD:D_SOD-323",
    "R": "Resistor_SMD:R_0603_1608Metric",
    "C": "Capacitor_SMD:C_0603_1608Metric",
    "TP": "TestPoint:TestPoint_Pad_1.5x1.5mm",
}
PICKUP_PARTS = {"D": ("BAT15-03W", ""), "R": ("100k", "C25803"), "C": ("1n", "C1588")}
PICKUP_PIECE_MM = (17.0, 14.5)  # fits the free end of the last row of small discs
START_ANGLE_DEG = -90.0  # coil ends at the top of the disc (north), chip pins LA and LB there
TRIM_CODES: dict[str, str] = {}  # 0402 C0G trims: LCSC codes read in the order preview


@dataclass(frozen=True)
class TagSpec:
    index: int
    size: str
    trim_pF: float
    centre: tuple[float, float]
    disc_mm: float
    geometry: object  # nfc.TagGeometry

    @property
    def ref(self) -> str:
        return f"U{self.index}"

    @property
    def variant(self) -> str:
        return self.size if self.trim_pF == 0.0 else f"{self.size}+{self.trim_pF:g}pF"


@dataclass
class PanelResult:
    board: Board
    panel_mm: tuple[float, float]
    tags: list[TagSpec]
    bites: list[tuple[float, float]]
    placements: dict[str, tuple[float, float, float]]
    parts: dict[str, tuple[str, str, str, str, bool]]  # ref -> value, footprint, mpn, lcsc, dnp
    outline_rings: list[list[tuple[float, float]]] = field(default_factory=list)
    pickup_at: tuple[float, float, float, float] | None = None
    chip_mpn: str = ""
    chip_lcsc: str = ""


def fmt_c(pf: float) -> str:
    return f"{pf:g}p" if pf == int(pf) else f"{pf:.1f}".replace(".", "p")


def tag_specs(cfg: BoardConfig, pitch_mm: float) -> list[tuple[str, float]]:
    """(size, trim) of every disc, large discs first, by variant."""
    tags = cfg.hall_rfid.mockup.tags
    n = cfg.hall_rfid.demo.tags.per_variant
    out = []
    sizes = sorted(tags.trims_pF, key=lambda s: -nfc.tag_geometry(cfg, pitch_mm, s).disc_mm)
    for size in sizes:
        for trim in tags.trims_pF[size]:
            out += [(size, trim)] * n
    return out


def _rows(cfg: BoardConfig, pitch_mm: float) -> tuple[list[list[TagSpec]], tuple[float, float]]:
    """Discs in rows of equal diameter, left to right, as many per row as
    the inner width takes; returns the rows and the panel size."""
    width = cfg.hall_rfid.demo.tags.panel_mm[0]
    inner = width - 2.0 * RAIL_MM
    specs = tag_specs(cfg, pitch_mm)
    rows: list[list[TagSpec]] = []
    y = BAR_MM + GAP_MM
    k = 0
    i = 0
    while i < len(specs):
        size, trim = specs[i]
        geo = nfc.tag_geometry(cfg, pitch_mm, size)
        d = geo.disc_mm
        per_row = int((inner - GAP_MM) // (d + GAP_MM))
        row = []
        x = RAIL_MM + GAP_MM + d / 2.0
        while i < len(specs) and len(row) < per_row:
            s, t = specs[i]
            g = nfc.tag_geometry(cfg, pitch_mm, s)
            if g.disc_mm != d:
                break
            k += 1
            row.append(TagSpec(k, s, t, (round(x, 3), round(y + d / 2.0, 3)), d, g))
            x += d + GAP_MM
            i += 1
        rows.append(row)
        y += d + GAP_MM
    height = y + BAR_MM
    return rows, (width, round(height, 3))


def _pickup_place(rows, panel) -> tuple[float, float, float, float]:
    """The pickup piece: in the last row's free east end when it fits,
    else in a row of its own."""
    w, h = PICKUP_PIECE_MM
    last = rows[-1]
    x_free = last[-1].centre[0] + last[-1].disc_mm / 2.0 + GAP_MM
    x1 = panel[0] - RAIL_MM - GAP_MM
    y0 = last[0].centre[1] - last[0].disc_mm / 2.0
    if x1 - x_free >= w and last[0].disc_mm >= h:
        return (x1 - w, y0, x1, y0 + h)
    return (x1 - w, panel[1] - BAR_MM - GAP_MM - h, x1, panel[1] - BAR_MM - GAP_MM)


def _bites(x: float, y: float, along: str, width: float) -> list[tuple[float, float]]:
    n = int(width // BITE_PITCH_MM)
    offs = [(j - (n - 1) / 2.0) * BITE_PITCH_MM for j in range(n)]
    return [(x + o, y) if along == "x" else (x, y + o) for o in offs]


def build_tag_panel(cfg: BoardConfig, pitch_mm: float | None = None) -> PanelResult:
    pitch = cfg.pitch.mockup_mm if pitch_mm is None else pitch_mm
    tags_cfg = cfg.hall_rfid.mockup.tags
    rows, panel = _rows(cfg, pitch)
    width, height = panel
    if height > cfg.hall_rfid.demo.tags.panel_mm[1]:
        raise ValueError(
            f"tag panel {height:g} mm tall, over {cfg.hall_rfid.demo.tags.panel_mm[1]:g}"
        )
    board = Board(
        thickness_mm=tags_cfg.board_mm,
        title="Demonstrateur Hall + RFID, planche d'etiquettes",
        copper_layers=2,
        generator="taggen",
    )
    chip = cfg.hall_rfid.demo.tags.chip
    res = PanelResult(
        board=board,
        panel_mm=panel,
        tags=[t for r in rows for t in r],
        bites=[],
        placements={},
        parts={},
        chip_mpn=chip.mpn,
        chip_lcsc=chip.lcsc,
    )

    # ---- outline: frame, tabs and discs
    shapes = [
        box(0.0, 0.0, RAIL_MM, height),
        box(width - RAIL_MM, 0.0, width, height),
        box(0.0, 0.0, width, BAR_MM),
        box(0.0, height - BAR_MM, width, height),
    ]
    tabs = []
    bites: list[tuple[float, float]] = []
    o = 0.5  # every tab runs this far into what it joins, so the union merges them

    def tab_x(xa: float, xb: float, y: float) -> None:
        tabs.append(box(xa - o, y - TAB_MM / 2.0, xb + o, y + TAB_MM / 2.0))

    def tab_y(x: float, ya: float, yb: float) -> None:
        tabs.append(box(x - TAB_MM / 2.0, ya - o, x + TAB_MM / 2.0, yb + o))

    for ri, row in enumerate(rows):
        for j, t in enumerate(row):
            cx, cy = t.centre
            r = t.disc_mm / 2.0
            shapes.append(Point(cx, cy).buffer(r, quad_segs=CIRCLE_SEGMENTS))
            # tab west: to the previous disc or the rail
            x_w = row[j - 1].centre[0] + row[j - 1].disc_mm / 2.0 if j else RAIL_MM
            tab_x(x_w, cx - r, cy)
            bites += _bites(cx - r - BITE_IN_MM, cy, "y", TAB_MM)
            if j:
                bites += _bites(x_w + BITE_IN_MM, cy, "y", TAB_MM)
            if j == len(row) - 1:  # tab east, to the rail
                tab_x(cx + r, width - RAIL_MM, cy)
                bites += _bites(cx + r + BITE_IN_MM, cy, "y", TAB_MM)
            if ri == 0:  # tab north, to the bar
                tab_y(cx, BAR_MM, cy - r)
                bites += _bites(cx, cy - r - BITE_IN_MM, "x", TAB_MM)
            if ri == len(rows) - 1:  # tab south, to the bar
                tab_y(cx, cy + r, height - BAR_MM)
                bites += _bites(cx, cy + r + BITE_IN_MM, "x", TAB_MM)
    px0, py0, px1, py1 = _pickup_place(rows, panel)
    res.pickup_at = (px0, py0, px1, py1)
    shapes.append(box(px0, py0, px1, py1))
    pcx, pcy = (px0 + px1) / 2.0, (py0 + py1) / 2.0
    tab_x(px1, width - RAIL_MM, pcy)
    bites += _bites(px1 + BITE_IN_MM, pcy, "y", TAB_MM)
    tab_y(pcx, py1, height - BAR_MM)
    bites += _bites(pcx, py1 + BITE_IN_MM, "x", TAB_MM)
    outline = unary_union(shapes + tabs)
    if outline.geom_type != "Polygon":
        raise ValueError(f"the panel outline is in {len(outline.geoms)} pieces: a tab misses")
    rings = [list(outline.exterior.coords)] + [list(i.coords) for i in outline.interiors]
    for ring in rings:
        pts = [(round(x, 4), round(y, 4)) for x, y in ring]
        for (x1, y1), (x2, y2) in zip(pts, pts[1:], strict=False):
            if (x1, y1) != (x2, y2):
                board.gr_line(x1, y1, x2, y2, "Edge.Cuts", 0.05)
        res.outline_rings.append(pts)
    for i, (bx, by) in enumerate(bites, start=1):
        board.npth_hole(bx, by, BITE_D_MM, ref=f"MB{i}")
    res.bites = bites

    # ---- the tags
    chip_fp = load_footprint(CHIP_FP)
    trim_fp = load_footprint(TRIM_FP)
    for t in res.tags:
        _draw_tag(res, t, chip_fp, trim_fp)

    # ---- the field pickup tag
    _draw_pickup(res, cfg, (px0, py0, px1, py1))

    # ---- fiducials on the rails, texts
    fid = load_footprint(FIDUCIAL_FP)
    for i, (fx, fy) in enumerate(
        (
            (RAIL_MM / 2.0, BAR_MM + 3.0),
            (width - RAIL_MM / 2.0, BAR_MM + 3.0),
            (RAIL_MM / 2.0, height - BAR_MM - 3.0),
        ),
        start=1,
    ):
        board.body.append(place_footprint(fid, f"FID{i}", "Fiducial", fx, fy, 0.0, {}))
    board.gr_text("ETIQUETTES NFC, DEMONSTRATEUR", width / 2.0, BAR_MM / 2.0, "F.SilkS", 1.0)
    return res


def _draw_tag(res: PanelResult, t: TagSpec, chip_fp, trim_fp) -> None:
    board = res.board
    g = t.geometry
    cx, cy = t.centre
    net_name = f"T{t.index}"
    net = board.net(net_name)
    r_out, r_in = g.radii_mm[0], g.radii_mm[-1]
    turns = g.turns_per_layer
    w = g.track_mm
    # top spiral outward, via on the rim, bottom spiral inward: the current
    # turns the same way on both layers when traversed electrically
    top = spiral_points((cx, cy), r_in, r_out, turns, START_ANGLE_DEG, -1)
    bottom = spiral_points((cx, cy), r_out, r_in, turns, START_ANGLE_DEG, -1)
    board.polyline(top, w, "F.Cu", net)
    board.polyline(bottom, w, "B.Cu", net)
    rim = tuple(float(v) for v in top[-1])
    board.via(rim[0], rim[1], VIA_PAD_MM, VIA_DRILL_MM, net)
    # the chip at the centre, LA (1) and LB (8) on its north side
    res.placements[t.ref] = (cx, cy, 0.0)
    nets = {"1": (net, net_name), "8": (net, net_name)}
    board.body.append(place_footprint(chip_fp, t.ref, t.variant, cx, cy, 0.0, nets))
    la = pad_abs_pos(cx, cy, 0.0, chip_fp.pad("1"))
    lb = pad_abs_pos(cx, cy, 0.0, chip_fp.pad("8"))
    inner = (cx, cy - r_in)  # both inner ends, north of the chip
    # top inner end to LA on the top layer; bottom inner end down a radial
    # lead to a via north of the chip, then to LB
    board.polyline([inner, la], LEAD_MM, "F.Cu", net)
    via2 = (cx, cy - 3.0)
    board.polyline([inner, via2], LEAD_MM, "B.Cu", net)
    board.via(via2[0], via2[1], VIA_PAD_MM, VIA_DRILL_MM, net)
    # the trim capacitor between the leads, north of the via
    cap_ref = f"C{t.index}"
    cap_at = (cx, cy - 3.9)
    res.placements[cap_ref] = (cap_at[0], cap_at[1], 0.0)
    cap_nets = {"1": (net, net_name), "2": (net, net_name)}
    value = fmt_c(t.trim_pF) if t.trim_pF else "non montee"
    board.body.append(place_footprint(trim_fp, cap_ref, value, cap_at[0], cap_at[1], 0.0, cap_nets))
    p1 = pad_abs_pos(cap_at[0], cap_at[1], 0.0, trim_fp.pad("1"))
    p2 = pad_abs_pos(cap_at[0], cap_at[1], 0.0, trim_fp.pad("2"))
    board.polyline([inner, p1], LEAD_MM, "F.Cu", net)
    board.polyline([via2, p2, lb], LEAD_MM, "F.Cu", net)
    res.parts[t.ref] = (t.variant, CHIP_FP, res.chip_mpn, res.chip_lcsc, False)
    res.parts[cap_ref] = (value, TRIM_FP, "", TRIM_CODES.get(value, ""), not t.trim_pF)
    board.gr_text(t.variant, cx, cy + r_in / 2.0 + 0.6, "F.SilkS", 0.8)


def _draw_pickup(res: PanelResult, cfg: BoardConfig, rect) -> None:
    """The field tag of note 25, paragraph 5: a small two-layer coil whose
    two ends leave at the rim (top spiral inward, via, bottom spiral back
    out), a detector diode on the hot end, the RC load across the output
    and the coil return, two pads for the twisted leads."""
    pk = cfg.hall_rfid.mockup.pickup
    board = res.board
    x0, y0, x1, y1 = rect
    cx, cy = x0 + 6.0, (y0 + y1) / 2.0
    # the coil copper is one conductor: both its ends, the return pads of
    # the load and the return lead pad share its net; the detector output
    # is the other net
    coil_name, out_name = "PK_COIL", "PK_OUT"
    coil, out = (board.net(n) for n in (coil_name, out_name))
    ret_name, ret = coil_name, coil
    turns = pk.turns // pk.layers
    r_out = pk.d_mm / 2.0 - pk.track_mm / 2.0
    r_in = r_out - (turns - 1) * 2.0 * pk.track_mm
    top = spiral_points((cx, cy), r_out, r_in, turns, START_ANGLE_DEG, -1)
    bottom = spiral_points((cx, cy), r_in, r_out, turns, START_ANGLE_DEG, -1)
    board.polyline(top, pk.track_mm, "F.Cu", coil)
    inner = tuple(float(v) for v in top[-1])
    board.via(inner[0], inner[1], VIA_PAD_MM, VIA_DRILL_MM, coil)
    board.polyline(bottom, pk.track_mm, "B.Cu", coil)
    rim = (cx, cy - r_out)
    fps = {k: load_footprint(v) for k, v in PICKUP_FP.items()}
    x_col = x0 + 13.4
    col = {"D1": y0 + 3.0, "C50": y0 + 6.6, "R50": y0 + 10.2}
    # KiCad footprints at rotation 90: pad 2 (diode anode, 0603 second pad)
    # is the upper pad, pad 1 (diode cathode) the lower one
    nets = {
        "D1": {"1": (out, out_name), "2": (coil, coil_name)},
        "C50": {"1": (ret, ret_name), "2": (out, out_name)},
        "R50": {"1": (ret, ret_name), "2": (out, out_name)},
    }
    for ref, key in (("D1", "D"), ("C50", "C"), ("R50", "R")):
        value, lcsc = PICKUP_PARTS[key]
        at = (x_col, col[ref])
        board.body.append(place_footprint(fps[key], ref, value, at[0], at[1], 90.0, nets[ref]))
        res.placements[ref] = (*at, 90.0)
        res.parts[ref] = (value, PICKUP_FP[key], value if key == "D" else "", lcsc, False)

    def pad(ref, key, num):
        return pad_abs_pos(x_col, col[ref], 90.0, fps[key].pad(num))

    anode, cathode = pad("D1", "D", "2"), pad("D1", "D", "1")
    c_out, c_ret = pad("C50", "C", "2"), pad("C50", "C", "1")
    r_out_pad, r_ret = pad("R50", "R", "2"), pad("R50", "R", "1")
    # hot end: top-layer rim end, up, east along the top edge, down into the anode
    board.polyline([rim, (cx, y0 + 1.2), (x_col, y0 + 1.2), anode], LEAD_MM, "F.Cu", coil)
    # coil return: back-layer rim end, up, east past the column, down, then
    # up through a via into the lower pad of the resistor
    x_ret = x0 + 16.0
    board.polyline(
        [rim, (cx, y0 + 0.8), (x_ret, y0 + 0.8), (x_ret, r_ret[1])], LEAD_MM, "B.Cu", coil
    )
    board.via(x_ret, r_ret[1], VIA_PAD_MM, VIA_DRILL_MM, coil)
    board.polyline([(x_ret, r_ret[1]), r_ret], LEAD_MM, "F.Cu", ret)
    # output: cathode down into the capacitor, then beside the column to the resistor
    board.polyline([cathode, c_out], LEAD_MM, "F.Cu", out)
    board.polyline(
        [c_out, (x_col + 1.0, c_out[1]), (x_col + 1.0, r_out_pad[1]), r_out_pad],
        LEAD_MM,
        "F.Cu",
        out,
    )
    # return: capacitor lower pad to resistor lower pad, west of the column
    board.polyline(
        [c_ret, (x_col - 1.0, c_ret[1]), (x_col - 1.0, r_ret[1]), r_ret], LEAD_MM, "F.Cu", ret
    )
    # the lead pads: output east of the diode, return under the coil
    tp_out, tp_ret = (x0 + 15.6, y0 + 3.0), (x0 + 9.5, y0 + 12.8)
    for ref, nm, n, at in (("TP50", out_name, out, tp_out), ("TP51", ret_name, ret, tp_ret)):
        board.body.append(place_footprint(fps["TP"], ref, nm, at[0], at[1], 0.0, {"1": (n, nm)}))
        res.placements[ref] = (*at, 0.0)
    board.polyline([cathode, (tp_out[0], cathode[1]), tp_out], LEAD_MM, "F.Cu", out)
    board.polyline(
        [r_ret, (x_col - 1.0, r_ret[1]), (x_col - 1.0, tp_ret[1]), tp_ret], LEAD_MM, "F.Cu", ret
    )
    board.gr_text("VIGNETTE", x0 + 3.0, y1 - 1.2, "F.SilkS", 0.8)


def design_rules() -> DesignRules:
    return DesignRules(
        clearance_mm=CLEARANCE_MM,
        track_width_mm=0.2,
        via_diameter_mm=VIA_PAD_MM,
        via_drill_mm=VIA_DRILL_MM,
        min_track_width_mm=0.2,
        min_via_diameter_mm=VIA_PAD_MM,
        min_hole_mm=VIA_DRILL_MM,
        edge_clearance_mm=EDGE_CLEARANCE_MM,
        track_widths_mm=(0.2, LEAD_MM),
        via_sizes_mm=((VIA_PAD_MM, VIA_DRILL_MM),),
    )


def bom_rows(res: PanelResult):
    groups: dict[tuple, list[str]] = {}
    for ref, (value, fp, mpn, lcsc, dnp) in res.parts.items():
        groups.setdefault((value, fp, mpn, lcsc, dnp), []).append(ref)
    rows = []
    for (value, fp, mpn, lcsc, dnp), refs in sorted(groups.items(), key=lambda kv: kv[1][0]):
        rows.append((" ".join(sorted(refs)), len(refs), value, fp.split(":")[-1], mpn, lcsc, dnp))
    return rows


def bom_csv(res: PanelResult) -> str:
    import csv
    from io import StringIO

    out = StringIO()
    w = csv.writer(out)
    w.writerow(["References", "Qty", "Value", "Footprint", "MPN", "LCSC", "DNP"])
    for refs, qty, value, fp, mpn, lcsc, dnp in bom_rows(res):
        w.writerow([refs, qty, value, fp, mpn, lcsc, "DNP" if dnp else ""])
    return out.getvalue()


def jlc_bom_csv(res: PanelResult) -> str:
    import csv
    from io import StringIO

    out = StringIO()
    w = csv.writer(out)
    w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
    for refs, _qty, value, fp, mpn, lcsc, dnp in bom_rows(res):
        if dnp or not lcsc:
            continue
        w.writerow([mpn or value, refs.replace(" ", ","), fp, lcsc])
    return out.getvalue()


def jlc_cpl_csv(res: PanelResult) -> str:
    import csv
    from io import StringIO

    out = StringIO()
    w = csv.writer(out)
    w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
    h = res.panel_mm[1]
    for ref, (x, y, rot) in res.placements.items():
        value, _fp, _mpn, lcsc, dnp = res.parts.get(ref, ("", "", "", "", True))
        if dnp or not lcsc:
            continue
        w.writerow([ref, f"{x:.3f}mm", f"{h - y:.3f}mm", "Top", f"{rot:g}"])
    return out.getvalue()


def coil_turning_deg(points: np.ndarray, centre: tuple[float, float]) -> float:
    d = points - np.asarray(centre)
    ang = np.unwrap(np.arctan2(d[:, 1], d[:, 0]))
    return float(math.degrees(ang[-1] - ang[0]))
