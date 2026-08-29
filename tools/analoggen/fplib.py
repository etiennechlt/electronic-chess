"""Access to the installed official KiCad footprint libraries.

Loads a .kicad_mod, extracts pad geometry for placement math and DRC,
and produces a placed instance block for a .kicad_pcb with position,
rotation, reference and per-pad net injection done by text surgery on
the verbatim upstream content.

Rotation convention (verified against kicad-cli renders): a footprint
(at x y rot) rotates pad offsets counterclockwise on screen (y down),
and each pad's own angle must carry the footprint angle added, since
the stored pad angle is absolute.
"""

from __future__ import annotations

import functools
import math
import re
from dataclasses import dataclass
from pathlib import Path

from .sexp import atom, find_all, find_one, parse

FOOTPRINT_DIR = Path("/usr/share/kicad/footprints")


@dataclass(frozen=True)
class PadSpec:
    number: str
    kind: str          # smd / thru_hole / np_thru_hole
    shape: str
    dx: float
    dy: float
    rot: float
    size: tuple[float, float]
    drill: float | None
    layers: tuple[str, ...]


@dataclass(frozen=True)
class Footprint:
    lib_id: str
    raw: str
    pads: tuple[PadSpec, ...]

    def pad(self, number: str) -> PadSpec:
        for p in self.pads:
            if p.number == number:
                return p
        raise KeyError(number)


@functools.cache
def load_footprint(lib_id: str) -> Footprint:
    lib, name = lib_id.split(":", 1)
    path = FOOTPRINT_DIR / f"{lib}.pretty" / f"{name}.kicad_mod"
    raw = path.read_text(encoding="utf-8")
    tree = parse(raw)
    pads = []
    for pad in find_all(tree, "pad"):
        number = str(atom(pad[1]))
        kind = str(pad[2])
        shape = str(pad[3])
        at = find_one(pad, "at")
        size = find_one(pad, "size")
        drill = find_one(pad, "drill")
        layers = find_one(pad, "layers")
        drill_val = None
        if drill is not None:
            nums = [float(x) for x in drill[1:] if not isinstance(x, list)
                    and re.match(r"^-?\d", str(x))]
            drill_val = nums[0] if nums else None
        pads.append(
            PadSpec(
                number=number, kind=kind, shape=shape,
                dx=float(at[1]), dy=float(at[2]),
                rot=float(at[3]) if len(at) > 3 else 0.0,
                size=(float(size[1]), float(size[2])),
                drill=drill_val,
                layers=tuple(str(atom(x)) for x in layers[1:]),
            )
        )
    return Footprint(lib_id=lib_id, raw=raw, pads=tuple(pads))


def pad_abs_pos(x: float, y: float, rot_deg: float, pad: PadSpec) -> tuple[float, float]:
    """Absolute pad center for a footprint placed at (x, y, rot_deg)."""
    th = math.radians(rot_deg)
    px = pad.dx * math.cos(th) + pad.dy * math.sin(th)
    py = -pad.dx * math.sin(th) + pad.dy * math.cos(th)
    return x + px, y + py


def place_footprint(
    fp: Footprint, ref: str, value: str, x: float, y: float, rot_deg: float,
    pad_nets: dict[str, tuple[int, str]],
) -> str:
    """Instance block for a .kicad_pcb (top side only)."""
    text = fp.raw

    # Drop any stray placement the library file might carry, then add ours.
    header_match = re.match(r'\((?:footprint|module)\s+("[^"]+"|\S+)', text)
    name_tok = header_match.group(1)
    bare = name_tok.strip('"')
    text = text.replace(header_match.group(0),
                        f'(footprint "{fp.lib_id.split(":", 1)[0]}:{bare}"', 1)
    rot_txt = f" {rot_deg:g}" if abs(rot_deg) > 1e-9 else ""
    text = re.sub(r'(\(layer\s+"?F\.Cu"?\))',
                  rf'\1\n  (at {x:g} {y:g}{rot_txt})', text, count=1)

    # Reference and value (library files may quote them or not).
    text = re.sub(r'\(fp_text reference\s+(?:"[^"]*"|\S+)',
                  f'(fp_text reference "{ref}"', text, count=1)
    text = re.sub(r'\(fp_text value\s+(?:"[^"]*"|\S+)',
                  f'(fp_text value "{value}"', text, count=1)

    # Pad angles are absolute: add the footprint angle to every pad, and
    # inject nets. Walk pad blocks one by one.
    out = []
    idx = 0
    pad_re = re.compile(r'\(pad\s+("(?:[^"\\]|\\.)*"|\S+)')
    while True:
        m = pad_re.search(text, idx)
        if not m:
            out.append(text[idx:])
            break
        start = m.start()
        depth = 0
        end = start
        for i in range(start, len(text)):
            if text[i] == "(":
                depth += 1
            elif text[i] == ")":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        block = text[start:end]
        number = m.group(1).strip('"')
        if abs(rot_deg) > 1e-9:
            def _rot(mm):
                parts = mm.group(1).split()
                if len(parts) == 2:
                    parts.append("0")
                parts[2] = f"{float(parts[2]) + rot_deg:g}"
                return f"(at {' '.join(parts)})"
            block = re.sub(r"\(at\s+([^()]*)\)", _rot, block, count=1)
        if number in pad_nets:
            net_i, net_name = pad_nets[number]
            block = block[:-1].rstrip() + f' (net {net_i} "{net_name}"))'
        out.append(text[idx:start])
        out.append(block)
        idx = end
    placed = "".join(out)
    return "  " + placed.replace("\n", "\n  ")
