"""Shared helpers for the documentation figures.

Every figure is an inline SVG string built from classes; `standalone`
wraps it with an embedded style sheet and a white background so the same
drawing renders on its own in `docs/images/` (GitHub, image viewers).
"""

from __future__ import annotations

import math
import re

# Light palette of the documentation figures (validated for colour vision
# deficiencies on a white surface: worst adjacent pair delta E 24.7).
INK = "#1a1e1d"
INK_2 = "#4f5754"
INK_3 = "#7d8582"
RULE = "#d3d8d4"
SURFACE = "#ffffff"
Q_HIGH = "#2a78d6"
Q_LOW = "#eb6834"
BAND = "rgba(42,120,214,.09)"
TINT = "#e9eef4"
WOOD = "#e6d3b1"
FELT = "#c9ccc4"
AIR = "#f7f9f7"
PCB = "#c4d9c0"
COPPER = "#c8843a"
MAGNET = "#8b8f92"
PIECE = "#efe6d6"

FONT = '"IBM Plex Sans", "Segoe UI", "DejaVu Sans", Helvetica, Arial, sans-serif'
MONO = '"IBM Plex Mono", Menlo, Consolas, "DejaVu Sans Mono", monospace'
GLYPH = '"Segoe UI Symbol", "Apple Symbols", "Noto Sans Symbols 2", "DejaVu Sans", sans-serif'

# Class sheet shared by the standalone files; the HTML pages restate the
# same classes with theme tokens so a figure looks the same in both.
STYLE = f"""
svg.docfig{{font-family:{FONT};color:{INK}}}
.lbl{{font-size:12.5px;fill:{INK}}}
.lbl.small{{font-size:11px}}
.lbl.strong{{font-weight:600}}
.muted{{fill:{INK_2}}}
.mono{{font-family:{MONO}}}
.glyph{{font-size:20px;font-family:{GLYPH}}}
.title{{font-size:14px;font-weight:600;fill:{INK}}}
.axis{{stroke:currentColor;stroke-width:1.2;fill:none;opacity:.55}}
.tick{{stroke:currentColor;stroke-width:1;opacity:.55}}
.grid{{stroke:currentColor;stroke-width:1;opacity:.12}}
.dash{{stroke:currentColor;stroke-width:1;stroke-dasharray:5 4;opacity:.5;fill:none}}
.brk{{stroke:currentColor;stroke-width:1.2;opacity:.6;fill:none}}
.trace{{fill:none;stroke-width:2;stroke-linejoin:round;stroke-linecap:round}}
.trace.ghost{{opacity:.35;stroke-dasharray:3 3}}
.env{{fill:none;stroke-width:1.2;stroke-dasharray:4 4;opacity:.7}}
.q-high{{stroke:{Q_HIGH}}}
.q-low{{stroke:{Q_LOW}}}
.q-high-t{{fill:{Q_HIGH};font-weight:600}}
.q-low-t{{fill:{Q_LOW};font-weight:600}}
.mark{{stroke-width:1.6}}
.dot{{fill:{SURFACE};stroke-width:2.5}}
.band{{fill:{BAND}}}
.peak-black{{fill:{Q_HIGH};stroke:{Q_HIGH};stroke-width:1.5;stroke-linejoin:round;opacity:.9}}
.peak-white{{fill:{SURFACE};stroke:{Q_HIGH};stroke-width:1.8;stroke-linejoin:round}}
.tipbox{{fill:{SURFACE};stroke:{RULE}}}
.lay-pcb{{fill:{PCB}}} .lay-air{{fill:{AIR}}} .lay-wood{{fill:{WOOD}}} .lay-felt{{fill:{FELT}}}
.copper{{fill:{COPPER}}}
.piece{{fill:{PIECE};stroke:currentColor;stroke-width:1.2;opacity:.95}}
.bundle{{fill:url(#wire);stroke:currentColor;stroke-width:1}}
.cap{{fill:{Q_LOW};stroke:none}}
.magnet{{fill:{MAGNET};opacity:.75}}
.field{{fill:none;stroke:{Q_HIGH};stroke-width:1.6;opacity:.8}}
.seg{{fill:{TINT};stroke:{RULE}}}
.seg-pulse{{fill:{Q_LOW};opacity:.35;stroke:{Q_LOW}}}
.seg-listen{{fill:{BAND};stroke:{Q_HIGH}}}
.box{{fill:{SURFACE};stroke:{RULE};stroke-width:1.2}}
.box-piece{{stroke:{Q_HIGH};stroke-width:1.8}}
.box-mcu{{fill:{TINT};stroke:{Q_HIGH};stroke-width:1.8}}
.box-soft{{fill:{TINT};stroke:{RULE};stroke-width:1.2}}
.box-warm{{fill:{SURFACE};stroke:{Q_LOW};stroke-width:1.6}}
.wire{{stroke:currentColor;stroke-width:1.4;fill:none;opacity:.7}}
.wire-a{{stroke:{Q_HIGH};stroke-width:2;fill:none}}
.wire-p{{stroke:{Q_LOW};stroke-width:2;fill:none}}
.zone{{fill:none;stroke:{RULE};stroke-width:1.2;stroke-dasharray:6 4}}
.coil{{fill:none;stroke:{COPPER};stroke-width:2}}
.puck{{fill:{PIECE};stroke:currentColor;stroke-width:1.2}}
"""

_OPEN_TAG = re.compile(r"<svg\b[^>]*>")


def fr_num(x: float, digits: int = 1) -> str:
    """French number: comma decimal, narrow space thousands, no dead zeros."""
    s = f"{x:,.{digits}f}".replace(",", " ").replace(".", ",")
    if digits > 0:
        s = s.rstrip("0").rstrip(",")
    return s


def lorentz(f: float, f0: float, q: float) -> float:
    """Normalised amplitude response of a resonator at frequency f."""
    return 1.0 / math.sqrt(1.0 + (q * (f / f0 - f0 / f)) ** 2)


def svg_open(width: int, height: int, label: str, extra: str = "") -> str:
    """Opening tag with the shared class and the accessibility label."""
    attrs = f'class="docfig" viewBox="0 0 {width} {height}" role="img" aria-label="{label}"'
    if extra:
        attrs += " " + extra
    return f"<svg {attrs}>"


def arrow_marker(marker_id: str, size: int = 6, both: bool = False) -> str:
    orient = "auto-start-reverse" if both else "auto"
    return (
        f'<marker id="{marker_id}" viewBox="0 0 10 10" refX="9" refY="5" '
        f'markerWidth="{size}" markerHeight="{size}" orient="{orient}">'
        '<path d="M0 0L10 5L0 10z" fill="currentColor"/></marker>'
    )


def text(x: float, y: float, s: str, cls: str = "lbl", anchor: str | None = None) -> str:
    a = f' text-anchor="{anchor}"' if anchor else ""
    return f'<text class="{cls}" x="{x:.1f}" y="{y:.1f}"{a}>{s}</text>'


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def standalone(svg: str) -> str:
    """Self-contained SVG file: xmlns, embedded style, white background."""
    m = _OPEN_TAG.search(svg)
    if m is None:
        raise ValueError("not an svg fragment")
    open_tag = m.group(0)
    if "xmlns=" not in open_tag:
        open_tag = open_tag.replace("<svg ", '<svg xmlns="http://www.w3.org/2000/svg" ', 1)
    vb = re.search(r'viewBox="0 0 (\d+) (\d+)"', open_tag)
    if vb is None:
        raise ValueError("viewBox missing")
    w, h = vb.group(1), vb.group(2)
    head = (
        f'{open_tag}\n<style>{STYLE}</style>\n<rect width="{w}" height="{h}" fill="{SURFACE}"/>\n'
    )
    return head + svg[m.end() :].lstrip("\n")
