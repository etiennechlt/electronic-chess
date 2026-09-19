"""Bills of materials of the coil board.

The board is mostly copper, four spiral layers and their joint, plus the
camp LEDs and their decoupling: those are the only parts a factory can
place. The LED carries a supplier code (declared once for the whole
repository in `quadgen.circuit`), the capacitors do not yet, so they are
in `bom.csv` and go on by hand like the other passives (note 15). The
assembly files hold the coded parts alone: JLCPCB refuses a placement
file whose designators are not all in the bill.
"""

from __future__ import annotations

import csv
from io import StringIO

from quadgen.circuit import LED

from chessboard_calc.config import BoardConfig

CAP_FOOTPRINT = "Capacitor_SMD:C_0603_1608Metric"


def _rows(cfg: BoardConfig, placements: dict[str, tuple[float, float, float]]) -> list[dict]:
    """One row per part, in the order a human reads the board."""
    leds = cfg.mockup.coil_board.leds
    rows = []
    refs = sorted((r for r in placements if r.startswith("LD")), key=lambda r: int(r[2:]))
    caps = sorted((r for r in placements if r.startswith("CL")), key=lambda r: int(r[2:]))
    if refs:
        rows.append(
            {
                "refs": refs,
                "value": leds.part,
                "footprint": LED.footprint.split(":")[-1],
                "mpn": LED.mpn,
                "lcsc": LED.lcsc,
            }
        )
    if caps:
        rows.append(
            {
                "refs": caps,
                "value": f"{leds.decoupling_nf:.0f}n",
                "footprint": CAP_FOOTPRINT.split(":")[-1],
                "mpn": "",
                "lcsc": "",
            }
        )
    return rows


def bom_csv(cfg: BoardConfig, placements: dict[str, tuple[float, float, float]]) -> str:
    """Every part, coded or not."""
    out = StringIO()
    w = csv.writer(out)
    w.writerow(["References", "Qty", "Value", "Footprint", "MPN", "LCSC"])
    for r in _rows(cfg, placements):
        w.writerow(
            [" ".join(r["refs"]), len(r["refs"]), r["value"], r["footprint"], r["mpn"], r["lcsc"]]
        )
    return out.getvalue()


def jlc_bom_csv(cfg: BoardConfig, placements: dict[str, tuple[float, float, float]]) -> str:
    """The parts a factory can order, in the columns JLCPCB reads."""
    out = StringIO()
    w = csv.writer(out)
    w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
    for r in _rows(cfg, placements):
        if r["lcsc"]:
            w.writerow([r["mpn"] or r["value"], ",".join(r["refs"]), r["footprint"], r["lcsc"]])
    return out.getvalue()


def jlc_cpl_csv(cfg: BoardConfig, placements: dict[str, tuple[float, float, float]]) -> str:
    """Where those parts sit, in the frame JLCPCB reads: the origin at the
    bottom left corner of the board, so the ordinate is turned over."""
    height = cfg.mockup.coil_board.size_mm[1]
    coded = {ref for r in _rows(cfg, placements) if r["lcsc"] for ref in r["refs"]}
    out = StringIO()
    w = csv.writer(out)
    w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
    for ref in sorted(coded, key=lambda r: (r[:2], int(r[2:]))):
        x, y, rot = placements[ref]
        w.writerow([ref, f"{x:.3f}mm", f"{height - y:.3f}mm", "Top", f"{rot:g}"])
    return out.getvalue()
