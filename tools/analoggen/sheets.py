"""Drawn, hierarchical KiCad schematics generated from a Circuit.

analoggen.schematic emits one global label per pin and no wire: exact
but unreadable. Here a Sheet places symbol units at template positions
and draws the wires between their pins; rails, buses and nets shared
between sheets carry global labels, nets local to one sheet carry a
local label. The drawing is checked against the Circuit before it is
written: every wire joins pins of one net, every net of the Circuit is
one connected component, no two nets touch, every net carries its name,
so a template mistake fails the build instead of shorting the board
silently.

Coordinates are sheet millimeters (y down) on KiCad's 1.27 mm grid.
Symbol pin offsets come from the library (y up) and go through KiCad's
own orientation matrix (sch_symbol.cpp, SetOrientation), so rotated and
mirrored units land their pins where KiCad draws them.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field

from .circuit import Circuit, Component
from .symlib import Pin

GRID = 1.27
STUB = 2.54
FONT = 1.27

# KiCad y-down TRANSFORM (x1, y1, x2, y2) per symbol angle; a mirror is
# composed on the right: mirror x negates (x2, y2), mirror y negates (x1, y1).
_ANGLE = {0: (1, 0, 0, 1), 90: (0, 1, -1, 0), 180: (-1, 0, 0, -1), 270: (0, -1, 1, 0)}
_DIR = {"r": (1, 0), "l": (-1, 0), "u": (0, -1), "d": (0, 1)}
_GLOBAL_ROT = {"r": (0, "left"), "l": (180, "right"), "u": (90, "left"), "d": (270, "left")}
_LOCAL_ROT = {"r": (0, "left bottom"), "u": (90, "left bottom")}


class SchematicError(ValueError):
    """The drawing does not carry the circuit (split, joined or unnamed nets)."""


def _u() -> str:
    return str(uuid.uuid4())


def _key(x: float, y: float) -> tuple[float, float]:
    return (round(x, 2), round(y, 2))


def _fmt(v: float) -> str:
    return f"{round(v, 4):g}"


@dataclass(frozen=True)
class Placed:
    """One symbol unit on a sheet."""

    comp: Component
    unit: int
    x: float
    y: float
    rot: int = 0
    mirror: str | None = None  # "x" (flip top/bottom) or "y" (flip left/right)
    fields: str = "right"  # side of a two-pin vertical part that carries its texts

    @property
    def pins(self) -> list[Pin]:
        sym = self.comp.sym
        return sym.pins_of_unit(self.unit) + sym.pins_of_unit(0)

    def pin(self, number: str) -> Pin:
        for pin in self.pins:
            if pin.number == number:
                return pin
        raise KeyError(f"{self.comp.ref}: no pin {number} in unit {self.unit}")

    def _matrix(self) -> tuple[int, int, int, int]:
        x1, y1, x2, y2 = _ANGLE[self.rot % 360]
        if self.mirror == "x":
            x1, y1, x2, y2 = x1, y1, -x2, -y2
        elif self.mirror == "y":
            x1, y1, x2, y2 = -x1, -y1, x2, y2
        return x1, y1, x2, y2

    def _map(self, px: float, py: float) -> tuple[float, float]:
        """Symbol offset (y up) to sheet offset (rpx right, rpy up)."""
        x1, y1, x2, y2 = self._matrix()
        return x1 * px - y1 * py, -x2 * px + y2 * py

    def pin_pos(self, number: str) -> tuple[float, float]:
        pin = self.pin(number)
        rpx, rpy = self._map(pin.x, pin.y)
        return round(self.x + rpx, 4), round(self.y - rpy, 4)

    def pin_away(self, number: str) -> tuple[int, int]:
        """Unit vector on the sheet from the pin end away from the body."""
        pin = self.pin(number)
        th = math.radians(pin.rot)
        rdx, rdy = self._map(-math.cos(th), -math.sin(th))
        return round(rdx), round(-rdy)

    def extent(self) -> tuple[float, float, float, float]:
        xs = [self.pin_pos(p.number)[0] for p in self.pins] or [self.x]
        ys = [self.pin_pos(p.number)[1] for p in self.pins] or [self.y]
        return min(xs), min(ys), max(xs), max(ys)


@dataclass(frozen=True)
class Label:
    net: str
    x: float
    y: float
    direction: str  # r l u d: where the flag or the text extends
    kind: str  # global | local


@dataclass
class Sheet:
    name: str  # file stem
    title: str
    paper: str = "A3"
    placed: list[Placed] = field(default_factory=list)
    wires: list[tuple[tuple[float, float], tuple[float, float]]] = field(default_factory=list)
    junctions: list[tuple[float, float]] = field(default_factory=list)
    labels: list[Label] = field(default_factory=list)
    no_connects: list[tuple[float, float]] = field(default_factory=list)
    texts: list[tuple[str, float, float, float, bool]] = field(default_factory=list)
    subsheets: list[tuple[Sheet, float, float, float, float]] = field(default_factory=list)
    uuid: str = field(default_factory=_u)  # the sheet file
    sheet_uuid: str = field(default_factory=_u)  # the (sheet ...) element in the parent

    # ---- drawing primitives
    def place(
        self, comp: Component, x: float, y: float, rot: int = 0, mirror: str | None = None,
        unit: int = 1, fields: str = "right",
    ) -> Placed:
        pl = Placed(comp, unit, round(x, 4), round(y, 4), rot, mirror, fields)
        self.placed.append(pl)
        return pl

    def wire(self, *pts: tuple[float, float]) -> None:
        for a, b in zip(pts, pts[1:], strict=False):
            if _key(*a) != _key(*b):
                self.wires.append((a, b))

    def route(self, a: tuple[float, float], b: tuple[float, float], bend: str = "hv") -> None:
        """Orthogonal wire from a to b: horizontal first ("hv") or vertical first."""
        if abs(a[0] - b[0]) < 1e-6 or abs(a[1] - b[1]) < 1e-6:
            self.wire(a, b)
        elif bend == "hv":
            self.wire(a, (b[0], a[1]), b)
        else:
            self.wire(a, (a[0], b[1]), b)

    def junction(self, x: float, y: float) -> None:
        self.junctions.append((x, y))

    def label(self, net: str, x: float, y: float, direction: str, kind: str = "global") -> None:
        self.labels.append(Label(net, x, y, direction, kind))

    def stub(self, pl: Placed, number: str, length: float = STUB) -> tuple[float, float]:
        """Wire from a pin end straight away from the body; returns its free end."""
        x, y = pl.pin_pos(number)
        dx, dy = pl.pin_away(number)
        end = (round(x + dx * length, 4), round(y + dy * length, 4))
        self.wire((x, y), end)
        return end

    def pin_label(
        self, pl: Placed, number: str, net: str | None = None, kind: str = "global",
        length: float = STUB,
    ) -> None:
        """Stub plus label at its end, pointing away from the body."""
        net = pl.comp.pins[number] if net is None else net
        end = self.stub(pl, number, length)
        dx, dy = pl.pin_away(number)
        direction = {(1, 0): "r", (-1, 0): "l", (0, -1): "u", (0, 1): "d"}[(dx, dy)]
        self.label(net, end[0], end[1], direction, kind)

    def pin_nc(self, pl: Placed, number: str) -> None:
        self.no_connects.append(pl.pin_pos(number))

    def text(self, s: str, x: float, y: float, size: float = 2.0, bold: bool = True) -> None:
        self.texts.append((s, x, y, size, bold))

    def subsheet(self, sheet: Sheet, x: float, y: float, w: float, h: float) -> None:
        self.subsheets.append((sheet, x, y, w, h))


class _UnionFind:
    def __init__(self) -> None:
        self.parent: dict = {}

    def find(self, k):
        self.parent.setdefault(k, k)
        while self.parent[k] != k:
            self.parent[k] = self.parent[self.parent[k]]
            k = self.parent[k]
        return k

    def union(self, a, b) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


def _split_segments(sh: Sheet, points: list[tuple[float, float]]) -> None:
    """Break every wire segment of the sheet at the given points lying inside it."""
    out = []
    for a, b in sh.wires:
        inside = sorted(
            {pt for pt in points if _interior(a, b, pt[0], pt[1])},
            key=lambda pt: math.hypot(pt[0] - a[0], pt[1] - a[1]),
        )
        prev = a
        for pt in inside:
            out.append((prev, pt))
            prev = pt
        out.append((prev, b))
    sh.wires = out


def _interior(p, q, x, y, tol: float = 0.01) -> bool:
    """(x, y) strictly inside segment p-q."""
    (x1, y1), (x2, y2) = p, q
    if abs(x1 - x2) < tol and abs(x - x1) < tol:
        lo, hi = sorted((y1, y2))
        return lo + tol < y < hi - tol
    if abs(y1 - y2) < tol and abs(y - y1) < tol:
        lo, hi = sorted((x1, x2))
        return lo + tol < x < hi - tol
    return False


@dataclass
class Schematic:
    """A root sheet and its sub-sheets, checked against a Circuit."""

    project: str
    root: Sheet

    @property
    def sheets(self) -> list[Sheet]:
        return [self.root] + [s for s, *_ in self.root.subsheets]

    def verify(self, circuit: Circuit) -> None:
        uf = _UnionFind()
        pin_key: dict[tuple[str, str], tuple] = {}
        labels_at: dict[tuple, list[Label]] = {}
        nc_at: set[tuple] = set()
        for sh in self.sheets:
            pk = ("pt", sh.name)
            segs = sh.wires
            for a, b in segs:
                uf.union(pk + (_key(*a),), pk + (_key(*b),))
            pois: list[tuple[tuple, str]] = []
            for pl in sh.placed:
                for pin in pl.pins:
                    k = pk + (_key(*pl.pin_pos(pin.number)),)
                    pin_key[(pl.comp.ref, pin.number)] = k
                    pois.append((k, "pin"))
            for lb in sh.labels:
                k = pk + (_key(lb.x, lb.y),)
                labels_at.setdefault(k, []).append(lb)
                pois.append((k, "label"))
                if lb.kind == "global":
                    uf.union(k, ("global", lb.net))
                else:
                    uf.union(k, ("local", sh.name, lb.net))
            for a, b in segs:
                pois.append((pk + (_key(*a),), "wire"))
                pois.append((pk + (_key(*b),), "wire"))
            for x, y in sh.no_connects:
                nc_at.add(pk + (_key(x, y),))
            needed: set[tuple[float, float]] = set()
            ends: dict[tuple, int] = {}
            for k, kind in pois:
                x, y = k[2]
                if kind in ("pin", "wire"):
                    ends[k] = ends.get(k, 0) + 1
                for a, b in segs:
                    if _interior(a, b, x, y):
                        uf.union(k, pk + (_key(*a),))
                        if kind in ("pin", "wire"):
                            needed.add((x, y))
            for k, count in ends.items():
                if count >= 3:
                    needed.add(k[2])
            have = {_key(*j) for j in sh.junctions}
            for x, y in sorted(needed):
                if (x, y) not in have:
                    sh.junctions.append((x, y))
            # KiCad only connects segment ends: a pin or a wire ending on the
            # middle of a segment stays open even under a junction dot, so
            # every segment is broken at the points that touch it, as the
            # editor does when it inserts a junction.
            _split_segments(sh, [k[2] for k, _kind in pois])
        # every mapped pin placed, every net one component, no two nets joined
        problems: list[str] = []
        class_of: dict[tuple[str, str], tuple] = {}
        for comp in circuit.components:
            for number in comp.pins:
                k = pin_key.get((comp.ref, number))
                if k is None:
                    problems.append(f"{comp.ref} pin {number} is not on any sheet")
                else:
                    class_of[(comp.ref, number)] = uf.find(k)
            for number in comp.nc:
                k = pin_key.get((comp.ref, number))
                if k is None:
                    problems.append(f"{comp.ref} pin {number} (no connect) is not on any sheet")
                elif k not in nc_at:
                    problems.append(f"{comp.ref} pin {number} needs a no-connect marker")
        nets_of_class: dict[tuple, set[str]] = {}
        for net, nodes in circuit.nets.items():
            classes = {class_of[n] for n in nodes if n in class_of}
            for cl in classes:
                nets_of_class.setdefault(cl, set()).add(net)
            if len(classes) > 1:
                parts = []
                for cl in classes:
                    members = [f"{r}.{p}" for r, p in nodes if class_of.get((r, p)) == cl]
                    parts.append("{" + ", ".join(members) + "}")
                problems.append(f"net {net} is split into " + " and ".join(parts))
        for nets in nets_of_class.values():
            if len(nets) > 1:
                problems.append("nets joined on the sheets: " + ", ".join(sorted(nets)))
        # names: every net carries at least one label, and only its own
        names_of_class: dict[tuple, set[str]] = {}
        for k, lbs in labels_at.items():
            cl = uf.find(k)
            for lb in lbs:
                names_of_class.setdefault(cl, set()).add(lb.net)
                if cl not in nets_of_class:
                    problems.append(f"label {lb.net} at {k[2]} on {k[1]} touches no pin")
        for cl, nets in nets_of_class.items():
            names = names_of_class.get(cl, set())
            if len(nets) == 1:
                (net,) = tuple(nets)
                if not names:
                    problems.append(f"net {net} has no label")
                elif names != {net}:
                    problems.append(f"net {net} is labelled {sorted(names)}")
        if problems:
            raise SchematicError("\n".join(problems))

    # ---- emission
    def emit(self) -> dict[str, str]:
        """File name -> content, root first."""
        out = {}
        out[f"{self.root.name}.kicad_sch"] = self._emit_sheet(self.root, f"/{self.root.uuid}", True)
        for page, (sh, *_rest) in enumerate(self.root.subsheets, start=2):
            out[f"{sh.name}.kicad_sch"] = self._emit_sheet(
                sh, f"/{self.root.uuid}/{sh.sheet_uuid}", False, page
            )
        return out

    def _emit_sheet(self, sh: Sheet, path: str, is_root: bool, page: int = 1) -> str:
        out: list[str] = []
        out.append("(kicad_sch (version 20230121) (generator quadgen)")
        out.append(f"  (uuid {sh.uuid})")
        out.append(f'  (paper "{sh.paper}")')
        out.append(f'  (title_block (title "{sh.title}") (comment 1 "{self.project}"))')
        libs: dict[str, str] = {}
        for pl in sh.placed:
            libs.setdefault(pl.comp.sym.lib_id, pl.comp.sym.raw)
        out.append("  (lib_symbols")
        for raw in libs.values():
            out.append("    " + raw)
        out.append("  )")
        for x, y in sh.junctions:
            out.append(
                f"  (junction (at {_fmt(x)} {_fmt(y)}) (diameter 0) (color 0 0 0 0) (uuid {_u()}))"
            )
        for x, y in sh.no_connects:
            out.append(f"  (no_connect (at {_fmt(x)} {_fmt(y)}) (uuid {_u()}))")
        for (x1, y1), (x2, y2) in sh.wires:
            out.append(
                f"  (wire (pts (xy {_fmt(x1)} {_fmt(y1)}) (xy {_fmt(x2)} {_fmt(y2)})) "
                f"(stroke (width 0) (type default)) (uuid {_u()}))"
            )
        for s, x, y, size, bold in sh.texts:
            weight = " (thickness 0.5) bold" if bold else ""
            out.append(
                f'  (text "{s}" (at {_fmt(x)} {_fmt(y)} 0) '
                f"(effects (font (size {size:g} {size:g}){weight}) (justify left)) (uuid {_u()}))"
            )
        for lb in sh.labels:
            if lb.kind == "global":
                rot, justify = _GLOBAL_ROT[lb.direction]
                at = f"(at {_fmt(lb.x)} {_fmt(lb.y)} {rot})"
                out.append(
                    f'  (global_label "{lb.net}" (shape passive) {at} (fields_autoplaced) '
                    f"(effects (font (size {FONT} {FONT})) (justify {justify})) (uuid {_u()})"
                )
                out.append(
                    '    (property "Intersheetrefs" "${INTERSHEET_REFS}" (at 0 0 0) '
                    f"(effects (font (size {FONT} {FONT})) hide))"
                )
                out.append("  )")
            else:
                rot, justify = _LOCAL_ROT[lb.direction]
                out.append(
                    f'  (label "{lb.net}" (at {_fmt(lb.x)} {_fmt(lb.y)} {rot}) (fields_autoplaced) '
                    f"(effects (font (size {FONT} {FONT})) (justify {justify})) (uuid {_u()}))"
                )
        for pl in sh.placed:
            out.append(self._emit_symbol(pl, path))
        for sub, x, y, w, h in sh.subsheets:
            out.append(self._emit_subsheet(sub, x, y, w, h, path))
        if is_root:
            out.append('  (sheet_instances (path "/" (page "1")))')
        out.append(")")
        return "\n".join(out) + "\n"

    def _emit_symbol(self, pl: Placed, path: str) -> str:
        comp, sym = pl.comp, pl.comp.sym
        x0, y0, x1, y1 = pl.extent()
        pins = [pl.pin_pos(p.number) for p in pl.pins]
        n_pins = len(pins)
        ys = sorted({round(y, 2) for _x, y in pins})
        ref, val = comp.ref, comp.value

        def width(s: str) -> float:  # stroke font advance, about 0.9 em per character
            return 0.9 * FONT * len(s)

        # Text centers (KiCad re-justifies a field with the symbol orientation,
        # so every text is centered on a computed point instead).
        if n_pins == 2 and abs(x0 - x1) < 0.01:  # vertical two-pin part: texts beside it
            side = -1.0 if pl.fields == "left" else 1.0
            fields = [
                (pl.x + side * (1.6 + width(ref) / 2), pl.y - 1.0),
                (pl.x + side * (1.6 + width(val) / 2), pl.y + 1.5),
            ]
        elif n_pins == 2:  # horizontal: above and below
            fields = [(pl.x, pl.y - 2.3), (pl.x, pl.y + 2.5)]
        elif n_pins == 3 and len(ys) == 2:
            pair_on_top = sum(1 for _x, y in pins if round(y, 2) == ys[0]) == 2
            if pair_on_top:  # dual diode, third pin below: texts above the body
                fields = [(pl.x, y0 - 4.0), (pl.x, y0 - 2.4)]
            else:  # mirrored: third pin above, texts below
                fields = [(pl.x, y1 + 2.6), (pl.x, y1 + 4.2)]
        elif n_pins <= 3:  # transistors, test points: to the right of the pins
            fields = [
                (x1 + 1.2 + width(ref) / 2, pl.y - 1.3),
                (x1 + 1.2 + width(val) / 2, pl.y + 1.3),
            ]
        else:
            fields = [(x0 + width(ref) / 2, y0 - 1.8), (x0 + width(val) / 2, y1 + 2.2)]
        # KiCad swaps the text orientation of a field on a symbol rotated by
        # 90 or 270 degrees, so a horizontal text needs a 90 degree angle there
        angle = 90 if pl.rot in (90, 270) else 0
        mirror = f" (mirror {pl.mirror})" if pl.mirror else ""
        lines = [
            f'  (symbol (lib_id "{sym.lib_id}") (at {_fmt(pl.x)} {_fmt(pl.y)} {pl.rot}){mirror} '
            f"(unit {pl.unit})",
            f"    (in_bom yes) (on_board yes) (dnp {'yes' if comp.dnp else 'no'})",
            f"    (uuid {_u()})",
        ]
        for (fx, fy), (name, value) in zip(
            fields, (("Reference", ref), ("Value", val)), strict=True
        ):
            lines.append(
                f'    (property "{name}" "{value}" (at {_fmt(fx)} {_fmt(fy)} {angle})\n'
                f"      (effects (font (size {FONT} {FONT})))\n    )"
            )
        for name, value in (
            ("Footprint", comp.part.footprint),
            ("Datasheet", ""),
            ("MPN", comp.part.mpn),
            ("LCSC", comp.part.lcsc),
        ):
            lines.append(
                f'    (property "{name}" "{value}" (at {_fmt(pl.x)} {_fmt(pl.y)} 0)\n'
                f"      (effects (font (size {FONT} {FONT})) hide)\n    )"
            )
        for pin in pl.pins:
            lines.append(f'    (pin "{pin.number}" (uuid {_u()}))')
        lines.append(
            f'    (instances (project "{self.project}" '
            f'(path "{path}" (reference "{comp.ref}") (unit {pl.unit})))'
            ")"
        )
        lines.append("  )")
        return "\n".join(lines)

    def _emit_subsheet(self, sub: Sheet, x: float, y: float, w: float, h: float, path: str) -> str:
        page = 2 + [s for s, *_ in self.root.subsheets].index(sub)
        return "\n".join(
            [
                f"  (sheet (at {_fmt(x)} {_fmt(y)}) (size {_fmt(w)} {_fmt(h)})",
                "    (stroke (width 0.1524) (type solid))",
                "    (fill (color 0 0 0 0.0000))",
                f"    (uuid {sub.sheet_uuid})",
                f'    (property "Sheetname" "{sub.title}" (at {_fmt(x)} {_fmt(y - 0.7)} 0)',
                f"      (effects (font (size {FONT} {FONT})) (justify left bottom))",
                "    )",
                f'    (property "Sheetfile" "{sub.name}.kicad_sch" '
                f"(at {_fmt(x)} {_fmt(y + h + 0.6)} 0)",
                f"      (effects (font (size {FONT} {FONT})) (justify left top))",
                "    )",
                f'    (instances (project "{self.project}" (path "{path}" (page "{page}"))))',
                "  )",
            ]
        )
