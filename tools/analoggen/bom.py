"""BOM and placement exports: engineering CSV, JLCPCB BOM and CPL."""

from __future__ import annotations

import csv
from collections import defaultdict
from io import StringIO

from .circuit import Circuit


def bom_rows(circuit: Circuit):
    groups = defaultdict(list)
    for comp in circuit.components:
        key = (comp.value, comp.part.footprint, comp.part.mpn, comp.part.lcsc, comp.dnp)
        groups[key].append(comp.ref)
    rows = []
    for (value, footprint, mpn, lcsc, dnp), refs in sorted(groups.items(), key=lambda kv: kv[1][0]):
        rows.append(
            {
                "refs": " ".join(sorted(refs)),
                "qty": len(refs),
                "value": value,
                "footprint": footprint.split(":")[-1],
                "mpn": mpn,
                "lcsc": lcsc,
                "dnp": "DNP" if dnp else "",
            }
        )
    return rows


def bom_csv(circuit: Circuit) -> str:
    out = StringIO()
    w = csv.writer(out)
    w.writerow(["References", "Qty", "Value", "Footprint", "MPN", "LCSC", "DNP"])
    for r in bom_rows(circuit):
        w.writerow([r["refs"], r["qty"], r["value"], r["footprint"], r["mpn"], r["lcsc"], r["dnp"]])
    return out.getvalue()


def jlc_bom_csv(circuit: Circuit) -> str:
    out = StringIO()
    w = csv.writer(out)
    w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
    for r in bom_rows(circuit):
        if r["dnp"] or not r["lcsc"]:
            continue
        w.writerow([r["mpn"] or r["value"], r["refs"].replace(" ", ","), r["footprint"], r["lcsc"]])
    return out.getvalue()


def jlc_cpl_csv(circuit: Circuit, placements, board_h_mm: float = 62.0) -> str:
    out = StringIO()
    w = csv.writer(out)
    w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
    for comp in circuit.components:
        if comp.dnp or not comp.part.lcsc:
            continue
        x, y, rot = placements[comp.ref]
        # KiCad y grows down; JLC expects y up from the bottom-left corner.
        w.writerow([comp.ref, f"{x:.3f}mm", f"{board_h_mm - y:.3f}mm", "Top", f"{rot:g}"])
    return out.getvalue()
