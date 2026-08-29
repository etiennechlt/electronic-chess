"""Access to the installed official KiCad symbol libraries.

Extracts a symbol's raw s-expression block (for verbatim embedding in a
generated schematic), resolves `extends` chains to the base symbol so
pin definitions are always authoritative, and returns pin positions for
wiring. Pin coordinates are in symbol space (y up); the schematic
generator flips y when placing.
"""

from __future__ import annotations

import functools
import re
from dataclasses import dataclass
from pathlib import Path

from .sexp import atom, find_all, find_one, parse

SYMBOL_DIR = Path("/usr/share/kicad/symbols")


@dataclass(frozen=True)
class Pin:
    number: str
    name: str
    x: float
    y: float
    rot: float
    unit: int


@dataclass(frozen=True)
class Symbol:
    lib: str
    name: str          # base symbol name actually embedded
    lib_id: str        # "Lib:Name"
    raw: str           # block ready for lib_symbols (name already prefixed)
    pins: tuple[Pin, ...]
    units: tuple[int, ...]

    def pins_of_unit(self, unit: int) -> list[Pin]:
        return [p for p in self.pins if p.unit == unit]


def _extract_block(text: str, symbol_name: str) -> str:
    needle = f'(symbol "{symbol_name}"'
    start = text.find(needle)
    if start < 0:
        raise KeyError(symbol_name)
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    raise ValueError(f"unbalanced block for {symbol_name}")


@functools.cache
def _lib_text(lib: str) -> str:
    return (SYMBOL_DIR / f"{lib}.kicad_sym").read_text(encoding="utf-8")


def _pins_from_block(block_text: str, base_name: str) -> tuple[tuple[Pin, ...], tuple[int, ...]]:
    tree = parse(block_text)
    pins: list[Pin] = []
    units: set[int] = set()
    for child in find_all(tree, "symbol"):
        child_name = atom(child[1])
        m = re.match(re.escape(base_name) + r"_(\d+)_(\d+)$", child_name)
        if not m:
            continue
        unit = int(m.group(1))
        for pin in find_all(child, "pin"):
            at = find_one(pin, "at")
            name = find_one(pin, "name")
            number = find_one(pin, "number")
            pins.append(
                Pin(
                    number=str(atom(number[1])),
                    name=str(atom(name[1])),
                    x=float(at[1]),
                    y=float(at[2]),
                    rot=float(at[3]) if len(at) > 3 else 0.0,
                    unit=unit,
                )
            )
        if unit > 0:
            units.add(unit)
    return tuple(pins), tuple(sorted(units)) or (1,)


@functools.cache
def load_symbol(lib: str, name: str) -> Symbol:
    """Load `name` from `lib`, following `extends` to the base symbol."""
    text = _lib_text(lib)
    block = _extract_block(text, name)
    tree = parse(block)
    extends = find_one(tree, "extends")
    if extends is not None:
        return load_symbol(lib, str(atom(extends[1])))
    prefixed = block.replace(f'(symbol "{name}"', f'(symbol "{lib}:{name}"', 1)
    pins, units = _pins_from_block(block, name)
    if not pins:
        raise ValueError(f"symbol {lib}:{name} has no pins")
    return Symbol(lib=lib, name=name, lib_id=f"{lib}:{name}", raw=prefixed,
                  pins=pins, units=units)
