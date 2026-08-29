"""Generated KiCad 7 schematic for the analog board.

Style: official symbols embedded verbatim, instances grouped by
function, every pin fitted with a short stub and a global label named
after its net. Connectivity is therefore label-based and exactly
mirrors circuit.py; reviewers read nets by name, ERC sees every pin
attached.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass

from .circuit import Circuit, Component

GRID = 2.54
STUB = 2.54


def _u() -> str:
    return str(uuid.uuid4())


def _snap(v: float) -> float:
    return round(v / GRID) * GRID


@dataclass
class PlacedUnit:
    comp: Component
    unit: int
    x: float
    y: float


# Functional grouping: (title, y_mm, list of refs). Components absent
# from the map land in the last group. Multi-unit symbols place each
# unit side by side automatically.
GROUPS: list[tuple[str, float, list[str]]] = [
    ("POWER", 40.0,
     ["J1", "D1", "D2", "C1", "C2", "C3", "U1", "L1", "R1", "R2", "R3", "R4",
      "C4", "C5", "C6", "JP3", "FB1", "C7", "C8", "U2", "C9", "C10", "C11",
      "JP1", "C12", "R5", "R6", "C13"]),
    ("DRIVE RAIL", 105.0, ["Q1", "R7", "Q2", "R8", "R9", "R10"]),
    ("COIL CELL 1", 150.0,
     ["R21", "R22", "R23", "R24", "D11", "D21", "D31", "D41", "Q11", "R25",
      "Q21", "R26", "R27"]),
    ("COIL CELL 2", 195.0,
     ["R31", "R32", "R33", "R34", "D12", "D22", "D32", "D42", "Q12", "R35",
      "Q22", "R36", "R37"]),
    ("COIL CELL 3", 240.0,
     ["R41", "R42", "R43", "R44", "D13", "D23", "D33", "D43", "Q13", "R45",
      "Q23", "R46", "R47"]),
    ("COIL CELL 4", 285.0,
     ["R51", "R52", "R53", "R54", "D14", "D24", "D34", "D44", "Q14", "R55",
      "Q24", "R56", "R57"]),
    ("MUX AND AMPLIFIER", 340.0,
     ["U3", "R11", "C14", "C15", "R12", "R13", "U4", "R14", "C16"]),
    ("FILTERS AND OUTPUT", 395.0,
     ["C17", "C18", "R15", "R16", "R17", "R18", "R19", "R20", "C19", "C20",
      "R61", "R62", "U5", "C21", "R63", "R64", "U6", "C22", "C23", "R65",
      "C24", "D3"]),
    ("UART AND HEADERS", 450.0,
     ["U7", "C25", "C26", "R66", "R67", "J5", "J2", "J4"]),
    ("TEST AND MECHANICAL", 505.0,
     ["TP1", "TP2", "TP3", "TP4", "TP5", "TP6", "H1", "H2", "H3", "H4"]),
]


def _unit_extent(comp: Component, unit: int) -> tuple[float, float, float, float]:
    pins = comp.sym.pins_of_unit(unit) or comp.sym.pins_of_unit(0)
    xs = [p.x for p in pins] or [0.0]
    ys = [p.y for p in pins] or [0.0]
    return min(xs), max(xs), min(ys), max(ys)


def _place(circuit: Circuit) -> list[PlacedUnit]:
    by_ref = {c.ref: c for c in circuit.components}
    placed: list[PlacedUnit] = []
    listed: set[str] = set()
    for _title, y, refs in GROUPS:
        x = 30.0
        for ref in refs:
            comp = by_ref.get(ref)
            if comp is None:
                continue
            listed.add(ref)
            units = [u for u in comp.sym.units if comp.sym.pins_of_unit(u)] or [1]
            for unit in units:
                x0, x1, _y0, _y1 = _unit_extent(comp, unit)
                width = (x1 - x0) + 2 * STUB + 12.0
                cx = _snap(x - x0 + STUB + 4.0)
                placed.append(PlacedUnit(comp=comp, unit=unit, x=cx, y=_snap(y)))
                x += width
    leftovers = [c for c in circuit.components if c.ref not in listed]
    x = 30.0
    for comp in leftovers:
        placed.append(PlacedUnit(comp=comp, unit=1, x=_snap(x), y=_snap(560.0)))
        x += 25.0
    return placed


def _label_rot_and_justify(dx: float, dy: float) -> tuple[int, str]:
    if dx > 0:
        return 0, "left"
    if dx < 0:
        return 180, "right"
    if dy < 0:
        return 90, "left"
    return 270, "left"


def emit_schematic(circuit: Circuit, title: str) -> str:
    placed = _place(circuit)
    root = _u()
    out: list[str] = []
    out.append('(kicad_sch (version 20230121) (generator analoggen)')
    out.append(f'  (uuid {root})')
    out.append('  (paper "A1")')
    out.append(f'  (title_block (title "{title}"))')

    libs: dict[str, str] = {}
    for pu in placed:
        libs.setdefault(pu.comp.sym.lib_id, pu.comp.sym.raw)
    out.append("  (lib_symbols")
    for raw in libs.values():
        out.append("    " + raw.replace("\n", "\n"))
    out.append("  )")

    wires: list[str] = []
    labels: list[str] = []
    instances: list[str] = []

    for pu in placed:
        comp, unit = pu.comp, pu.unit
        sym = comp.sym
        inst = [
            f'  (symbol (lib_id "{sym.lib_id}") (at {pu.x:g} {pu.y:g} 0) (unit {unit})',
            f'    (in_bom yes) (on_board yes) (dnp {"yes" if comp.dnp else "no"})',
            f'    (uuid {_u()})',
            f'    (property "Reference" "{comp.ref}" (at {pu.x:g} {pu.y - 10:g} 0)',
            '      (effects (font (size 1.27 1.27)))',
            '    )',
            f'    (property "Value" "{comp.value}" (at {pu.x:g} {pu.y + 10:g} 0)',
            '      (effects (font (size 1.27 1.27)))',
            '    )',
            f'    (property "Footprint" "{comp.part.footprint}" (at {pu.x:g} {pu.y:g} 0)',
            '      (effects (font (size 1.27 1.27)) hide)',
            '    )',
            f'    (property "Datasheet" "" (at {pu.x:g} {pu.y:g} 0)',
            '      (effects (font (size 1.27 1.27)) hide)',
            '    )',
            f'    (property "MPN" "{comp.part.mpn}" (at {pu.x:g} {pu.y:g} 0)',
            '      (effects (font (size 1.27 1.27)) hide)',
            '    )',
            f'    (property "LCSC" "{comp.part.lcsc}" (at {pu.x:g} {pu.y:g} 0)',
            '      (effects (font (size 1.27 1.27)) hide)',
            '    )',
        ]
        for pin in sym.pins_of_unit(unit) + sym.pins_of_unit(0):
            inst.append(f'    (pin "{pin.number}" (uuid {_u()}))')
        inst.append(
            '    (instances (project "analog-board" '
            f'(path "/{root}" (reference "{comp.ref}") (unit {unit})))'
            ')'
        )
        inst.append("  )")
        instances.append("\n".join(inst))

        for pin in sym.pins_of_unit(unit) + sym.pins_of_unit(0):
            px = pu.x + pin.x
            py = pu.y - pin.y
            theta = math.radians(pin.rot)
            dx = -round(math.cos(theta))
            dy = round(math.sin(theta))
            ex, ey = px + dx * STUB, py + dy * STUB
            net = comp.pins.get(pin.number)
            if net is None:
                out_nc = f'  (no_connect (at {px:g} {py:g}) (uuid {_u()}))'
                labels.append(out_nc)
                continue
            wires.append(
                f'  (wire (pts (xy {px:g} {py:g}) (xy {ex:g} {ey:g})) '
                f'(stroke (width 0) (type default)) (uuid {_u()}))'
            )
            rot, justify = _label_rot_and_justify(dx, dy)
            labels.append(
                f'  (global_label "{net}" (shape passive) (at {ex:g} {ey:g} {rot}) '
                f'(effects (font (size 1.27 1.27)) (justify {justify})) (uuid {_u()}))'
            )

    for _title_g, y, _refs in GROUPS:
        labels.append(
            f'  (text "{_title_g}" (at 20 {y - 20:g} 0) '
            f'(effects (font (size 3 3) (thickness 0.6) bold) (justify left)) (uuid {_u()}))'
        )

    out.extend(wires)
    out.extend(labels)
    out.extend(instances)
    out.append('  (sheet_instances (path "/" (page "1")))')
    out.append(")")
    return "\n".join(out) + "\n"
