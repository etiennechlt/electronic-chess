"""Audit a generated board against the routing rules of the trade:
`routing_audit.py BOARD [BOARD ...]`.

What it measures, board by board: orthogonal placement, the keepout of
the non-plated holes, the fabrication gates (track width, via sizes,
clearance), the 2W rule between the measurement nets and the switching
ones, the length match of the pairs that reach the instrumentation
amplifier, the distance from every supply pin to its decoupling and from
every ground pad to its drop. It reads the board file our own generators
write, with no KiCad and no pcbnew, so it runs anywhere shapely does.

Numbers only: what they mean for this project, and which rule they honour
or bend on purpose, is note 21 of docs/notes.
"""

from __future__ import annotations

import math
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from shapely.geometry import LineString, Point, box
from shapely.strtree import STRtree

CLEARANCE_MM = 0.15
WIDTH_MM = 0.25  # the width the 2W rule is read against
# the nets that carry the measurement: the coil taps, the mux outputs and
# everything inside the amplifier chain
SENSITIVE = re.compile(
    r"^(M\d+_[AB]|MUX[AB]_OUT|INA_IN[PM]|INA_OUT|RG_[AB]|HP_\w+|LP_\w+|AMP_OUT|VREF|C\d+_[AB])$"
)
# the nets that switch while the board works: the excitation, the damping,
# the selection logic and the LED chain
AGGRESSOR = re.compile(
    r"^(DRIVE\w*|DAMP\w*|DMP\d*|PULSE\w*|MUX_A\d|MUX_EN\w*|LED_D\w+|5V_LED|VIN|Q\d_G)$"
)
SUPPLY = ("5VA", "3V3", "VIN", "5V_LED", "PULSE_RAIL", "DRIVE_BUS")


@dataclass
class Pad:
    ref: str
    number: str
    net: str
    layers: str
    x: float
    y: float
    w: float
    h: float


@dataclass
class Hole:
    ref: str
    x: float
    y: float
    d: float


@dataclass
class Track:
    net: str
    layer: str
    width: float
    a: tuple[float, float]
    b: tuple[float, float]


@dataclass
class Via:
    net: str
    x: float
    y: float
    pad: float
    drill: float


@dataclass
class Board:
    name: str
    pads: list[Pad]
    holes: list[Hole]
    tracks: list[Track]
    vias: list[Via]
    rotations: dict[str, float]


FP_RE = re.compile(r'^  \(footprint "[^"]*"')
AT_RE = re.compile(r"^\s*\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)")
FP_AT_RE = re.compile(r"\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)\s*$")
REF_RE = re.compile(r'\(fp_text reference "([^"]*)"')
# the pad number is quoted in the footprints we write and bare in some of
# the library ones
PAD_RE = re.compile(
    r'\(pad "?([^"\s]*)"? (\S+) \S+ \(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\) '
    r"\(size ([\d.]+) ([\d.]+)\)"
)
DRILL_RE = re.compile(r"\(drill ([\d.]+)\)")
LAYERS_RE = re.compile(r"\(layers ([^)]*)\)")
SEG_RE = re.compile(
    r"^  \(segment \(start ([-\d.]+) ([-\d.]+)\) \(end ([-\d.]+) ([-\d.]+)\) "
    r'\(width ([\d.]+)\) \(layer "([^"]+)"\)(?: \(net (\d+)\))?'
)
VIA_RE = re.compile(
    r"^  \(via \(at ([-\d.]+) ([-\d.]+)\) \(size ([\d.]+)\) \(drill ([\d.]+)\) "
    r"\(layers [^)]*\)(?: \(net (\d+)\))?"
)
NET_RE = re.compile(r'\(net (\d+) "([^"]*)"\)')


def place(x: float, y: float, rot: float, dx: float, dy: float) -> tuple[float, float]:
    """A footprint-local offset in board coordinates (KiCad turns the
    offset counter-clockwise in a y-down frame)."""
    t = math.radians(rot)
    return (x + dx * math.cos(t) + dy * math.sin(t), y - dx * math.sin(t) + dy * math.cos(t))


def read_board(path: Path) -> Board:
    """Everything the audit needs from a board our generators wrote. The
    footprints carry their origin either on the opening line or on the next
    one, and their pads an offset in the footprint's own frame."""
    nets: dict[int, str] = {}
    pads: list[Pad] = []
    holes: list[Hole] = []
    tracks: list[Track] = []
    vias: list[Via] = []
    rotations: dict[str, float] = {}
    origin: tuple[float, float, float] | None = None
    inside = False
    ref = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        for num, name in NET_RE.findall(line):
            nets.setdefault(int(num), name)
        if FP_RE.match(line):
            inside, ref, origin = True, "", None
            m = FP_AT_RE.search(line)
            if m:
                origin = (float(m.group(1)), float(m.group(2)), float(m.group(3) or 0.0))
            continue
        if inside:
            if origin is None:
                m = AT_RE.match(line)
                if m:
                    origin = (float(m.group(1)), float(m.group(2)), float(m.group(3) or 0.0))
                    continue
            m = REF_RE.search(line)
            if m and not ref:
                ref = m.group(1)
                rotations[ref] = origin[2] if origin else 0.0
                continue
            m = PAD_RE.search(line)
            if m and origin is not None:
                num, kind, dx, dy, prot, w, h = m.groups()
                gx, gy = place(origin[0], origin[1], origin[2], float(dx), float(dy))
                # the angle a pad carries is its own, absolute; without one it
                # turns with its footprint
                turn = (float(prot) if prot else origin[2]) % 180.0
                pw, ph = float(w), float(h)
                if abs(turn - 90.0) < 1.0:
                    pw, ph = ph, pw
                if kind == "np_thru_hole":
                    d = DRILL_RE.search(line)
                    holes.append(Hole(ref, gx, gy, float(d.group(1)) if d else pw))
                else:
                    net = NET_RE.search(line)
                    layers = LAYERS_RE.search(line)
                    pads.append(
                        Pad(
                            ref,
                            num,
                            net.group(2) if net else "",
                            layers.group(1) if layers else "",
                            gx,
                            gy,
                            pw,
                            ph,
                        )
                    )
                continue
            if line.startswith("  )"):
                inside = False
            continue
        m = SEG_RE.match(line)
        if m:
            x1, y1, x2, y2, w, layer, net = m.groups()
            tracks.append(
                Track(
                    nets.get(int(net or 0), ""),
                    layer,
                    float(w),
                    (float(x1), float(y1)),
                    (float(x2), float(y2)),
                )
            )
            continue
        m = VIA_RE.match(line)
        if m:
            x, y, size, drill, net = m.groups()
            vias.append(
                Via(nets.get(int(net or 0), ""), float(x), float(y), float(size), float(drill))
            )
    return Board(path.name, pads, holes, tracks, vias, rotations)


def pad_shape(p: Pad):
    return box(p.x - p.w / 2, p.y - p.h / 2, p.x + p.w / 2, p.y + p.h / 2)


def copper(b: Board, net_filter=None, layer: str | None = None) -> list:
    """Copper shapes, optionally of the nets a predicate accepts."""
    out = []
    for t in b.tracks:
        if (net_filter is None or net_filter(t.net)) and (layer is None or t.layer == layer):
            out.append(LineString([t.a, t.b]).buffer(t.width / 2))
    for v in b.vias:
        if net_filter is None or net_filter(v.net):
            out.append(Point(v.x, v.y).buffer(v.pad / 2))
    for p in b.pads:
        if net_filter is None or net_filter(p.net):
            out.append(pad_shape(p))
    return out


def track_length(b: Board, net: str) -> float:
    return sum(math.dist(t.a, t.b) for t in b.tracks if t.net == net)


def audit(b: Board) -> None:
    print(f"\n=== {b.name}")
    print(
        f"    {len(b.pads)} pads, {len(b.tracks)} segments, "
        f"{len(b.vias)} vias, {len(b.holes)} holes"
    )

    # 1. orthogonal placement
    odd = {r: a for r, a in b.rotations.items() if abs(a % 90.0) > 1e-6}
    print(
        f"[placement] orthogonal: {len(b.rotations) - len(odd)}/{len(b.rotations)} footprints"
        + (f", off-axis: {sorted(odd)[:5]}" if odd else "")
    )

    # 2. keepout of the non-plated holes
    shapes = copper(b)
    tree = STRtree(shapes)
    for h in b.holes:
        centre = Point(h.x, h.y)
        near = [shapes[i] for i in tree.query(centre.buffer(6.0))]
        gap = min((centre.distance(s) for s in near), default=float("inf"))
        print(
            f"[keepout]   {h.ref} d{h.d} mm: nearest copper {gap:.2f} mm from the axis"
            f" (annular ring {gap - h.d / 2:.2f} mm)"
        )

    # 3. fabrication gates
    widths = sorted({t.width for t in b.tracks})
    print(
        f"[dfm]       track widths {widths[0]:.2f} to {widths[-1]:.2f} mm, "
        f"vias {sorted({(v.pad, v.drill) for v in b.vias})}"
    )

    # 4. the 2W rule between the measurement nets and the switching ones
    per_layer: dict[str, list] = defaultdict(list)
    per_layer_net: dict[str, list[str]] = defaultdict(list)
    for t in b.tracks:
        if AGGRESSOR.match(t.net):
            per_layer[t.layer].append(LineString([t.a, t.b]).buffer(t.width / 2))
            per_layer_net[t.layer].append(t.net)
    trees = {la: STRtree(shapes) for la, shapes in per_layer.items()}
    worst: list[tuple[float, str, str, str]] = []
    for t in b.tracks:
        if not SENSITIVE.match(t.net) or t.layer not in trees:
            continue
        me = LineString([t.a, t.b]).buffer(t.width / 2)
        for i in trees[t.layer].query(me.buffer(2 * WIDTH_MM)):
            other, net = per_layer[t.layer][i], per_layer_net[t.layer][i]
            if net == t.net:
                continue
            worst.append((me.distance(other), t.net, net, t.layer))
    worst.sort()
    close = [w for w in worst if w[0] < 2 * WIDTH_MM]
    print(
        f"[2W rule]   {len(close)} places where a measurement net runs closer than "
        f"{2 * WIDTH_MM:.2f} mm to a switching one; worst:"
    )
    seen = set()
    for gap, a, c, la in worst:
        if (a, c) in seen:
            continue
        seen.add((a, c))
        print(f"              {gap:.3f} mm  {a} vs {c} on {la}")
        if len(seen) >= 6:
            break

    # 5. the pairs that reach the amplifier
    for a, c in (("MUXA_OUT", "MUXB_OUT"), ("INA_INP", "INA_INM"), ("RG_A", "RG_B")):
        la, lc = track_length(b, a), track_length(b, c)
        if la and lc:
            print(
                f"[pair]      {a} {la:.1f} mm vs {c} {lc:.1f} mm, "
                f"difference {abs(la - lc):.1f} mm ({abs(la - lc) / max(la, lc) * 100:.0f} %)"
            )

    # 6. decoupling and ground drops
    caps = defaultdict(list)
    for p in b.pads:
        if p.ref.startswith("C") and p.net:
            caps[p.net].append(pad_shape(p))
    for rail in SUPPLY:
        pins = [p for p in b.pads if p.net == rail and p.ref.startswith("U")]
        if not pins or rail not in caps:
            continue
        gaps = [min(pad_shape(p).distance(c) for c in caps[rail]) for p in pins]
        print(
            f"[decoupling] {rail}: {len(pins)} package pins, nearest capacitor "
            f"{min(gaps):.1f} to {max(gaps):.1f} mm away"
        )
    drops = [Point(v.x, v.y) for v in b.vias if v.net == "GND"]
    if drops:
        tree = STRtree(drops)
        gnd = [p for p in b.pads if p.net == "GND"]
        far = sorted(
            (
                (pad_shape(p).distance(drops[tree.nearest(pad_shape(p))]), p.ref, p.number)
                for p in gnd
            ),
            reverse=True,
        )
        print(
            f"[ground]    {len(drops)} ground vias for {len(gnd)} ground pads; farthest pad "
            f"{far[0][0]:.2f} mm from a via ({far[0][1]}.{far[0][2]})"
        )


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    for name in argv:
        audit(read_board(Path(name)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
