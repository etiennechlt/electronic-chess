"""The Hall plus RFID test board of note 25 (`hallrfid`): its geometry,
the timing of its Hall chain, its 3.3 V budget and the design guards of
lot 2. Pure arithmetic on the config, no CAD: the board generator of lot
5 draws what layout() returns, check() refuses a layout that does not
hold, at either pitch, the guards of its RFID chain (nfc.mockup_check)
included.

Frame: origin at the outer corner of square A1, x along the columns (A,
B), y along the rows (1, 2), away from the player. The play area is
[0, n_cols p] x [0, n_rows p]; the electronics strip lies past the last
row, and the useful board is the play area plus the strip. The assembly
rails run along its two long sides. All lengths are in mm.

Layout rules (note 25, paragraphs 4.1 and 4.2):

- Each square carries one square loop, centred, of the geometry of its
  column (loop_by_column); the loop opening is the side minus N tracks
  and N - 1 gaps on each side.
- A corridor is the band between two facing loops: between two columns
  over the span of one row, or between two rows over the span of one
  column (stopping at the inter-column bands, so the bands do not
  overlap). Its free width is the loop-to-loop width minus the ground
  keepout on both sides.
- The own margin of a square, what a reader would get inside it without
  the corridors, is the largest axis-aligned square left once the loop
  keepouts, the edge clearance and the holes are removed. It sits in an
  inner corner, against the rounded keepout corner: the margin m from
  loop to square edge minus keepout / sqrt 2, under the reader's free
  square at both pitches, which is why readers go in the corridors.
- Each reader sits in the adjacent corridor of widest free width, on the
  corridor centreline, facing its own loop; readers sharing a corridor
  spread evenly along the stretch where its two loops face each other.
  A reader fits when its free square (reader.footprint_square_mm) lies
  in the free region: the play area outside every loop keepout, the
  edge clearance of the three outer edges and the M3 holes.
- Ground is a tree drawn along the corridor centrelines: the
  inter-column corridors from the strip down to the far edge clearance,
  the inter-row corridors across each column. It never runs along an
  outer edge. A closed face of the ground copper, the strip pour
  included, would be a shorted turn: check() polygonizes the ground and
  names the loops a face encloses.
- The four M3 holes sit at the play-area corners, at half the smallest
  loop-to-edge margin from both edges; the fiducials sit on the rails,
  at fiducial_edge_mm from the two edges of their corner.

The Hall chain (paragraph 4.3) is a first-order RC per sensor (1 k near
the sensor, 10 nF at the ADC pin or mux input). At each mux switch the
common node of the CD74HC4067 (mux.c_on_pF) shares its charge with that
10 nF; the kick then decays with the RC time constant. A reading is
valid once within settle_lsb counts of its final value.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from itertools import combinations

from shapely.geometry import LineString, Point, box
from shapely.geometry.base import BaseGeometry
from shapely.ops import polygonize, unary_union

from .config import (
    BoardConfig,
    HallRfidMockupCfg,
    HallSensorCfg,
    NfcLoopCfg,
    ReaderPartCfg,
)
from .hall import OffsetCoverage, adc_lsb_mv, hall_budget, offset_coverage, sensor_index
from .nfc import mockup_check as nfc_mockup_check

Rect = tuple[float, float, float, float]   # x0, y0, x1, y1
XY = tuple[float, float]

_ARC_SEGMENTS = 32        # polygon segments per quarter circle of the keepout corners
_TOL_MM = 1e-6            # geometric tolerance of the fit tests
_CLUSTER_SIGNS = ((-1.0, -1.0), (1.0, -1.0), (-1.0, 1.0), (1.0, 1.0))   # SW, SE, NW, NE


@dataclass(frozen=True)
class MockupSquare:
    name: str
    column: str
    row: int
    centre_mm: XY
    rect: Rect
    free_square_mm: float = 0.0   # largest square left inside it for a reader (own margin)


@dataclass(frozen=True)
class MockupLoop:
    square: str
    kind: str              # loop name in mockup.loops, L60x3 or L70x2
    side_mm: float
    turns: int
    track_mm: float
    gap_mm: float
    opening_mm: float      # clear side inside the innermost turn
    outline: Rect          # outer copper edge
    feed_side: str         # N, E, S or W: both ends leave there, facing the reader corridor


@dataclass(frozen=True)
class MockupCorridor:
    name: str              # "A1|B1" between columns, "A1|A2" between rows
    squares: tuple[str, str]
    runs_along: str        # "y" between columns, "x" between rows
    band: Rect             # loop to loop, over the span of the row or column
    width_mm: float        # loop to loop
    free_width_mm: float   # minus the ground keepout on both sides
    facing: tuple[float, float]   # stretch, along the band, where both loops face each other
    free_area_mm2: float   # band area in the free region


@dataclass(frozen=True)
class MockupReader:
    square: str
    row: int
    part: ReaderPartCfg
    corridor: str
    faces: str             # side of its own loop it faces
    centre_mm: XY
    footprint: Rect        # the free square the QFN and its fan-out need
    fits: bool


@dataclass(frozen=True)
class HallSite:
    square: str
    role: str                      # "centre" or "cluster"
    offset_mm: XY                  # from the square centre
    centre_mm: XY
    mux_channel: int | None
    direct_signal: str | None      # ESP32 signal of the direct ADC path, centre sensors


@dataclass(frozen=True)
class MockupHole:
    centre_mm: XY
    d_mm: float
    loop_clearance_mm: float   # hole edge to the nearest loop copper
    edge_clearance_mm: float   # hole edge to the nearest edge of the useful board


@dataclass(frozen=True)
class GroundSegment:
    corridor: str          # "A|B" along an inter-column corridor, "A1|A2" across a column
    start: XY
    end: XY


@dataclass(frozen=True)
class Fiducial:
    centre_mm: XY
    d_mm: float
    mask_d_mm: float
    on_rail: bool          # the whole mask opening lies on a rail


@dataclass(frozen=True)
class MockupLayout:
    pitch_mm: float
    keepout_mm: float
    squares: tuple[MockupSquare, ...]
    loops: tuple[MockupLoop, ...]
    corridors: tuple[MockupCorridor, ...]
    readers: tuple[MockupReader, ...]
    hall_sites: tuple[HallSite, ...]
    play_area: Rect
    strip: Rect
    useful: Rect           # play area plus strip
    board: Rect            # with the rails
    rails: tuple[Rect, ...]
    holes: tuple[MockupHole, ...]
    ground: tuple[GroundSegment, ...]
    fiducials: tuple[Fiducial, ...]
    hole_inset_mm: float   # hole centre to both edges of its corner
    free_area_mm2: float   # play area outside keepouts, edge clearance and holes

    def loop(self, square: str) -> MockupLoop:
        return next(lp for lp in self.loops if lp.square == square)

    def corridor(self, name: str) -> MockupCorridor:
        return next(c for c in self.corridors if c.name == name)

    def reader(self, square: str) -> MockupReader:
        return next(r for r in self.readers if r.square == square)


def _opening_mm(loop: NfcLoopCfg, side_mm: float) -> float:
    return side_mm - 2.0 * (loop.turns * loop.track_mm + (loop.turns - 1) * loop.gap_mm)


def _keepout(outline: Rect, keepout_mm: float) -> BaseGeometry:
    return box(*outline).buffer(keepout_mm, quad_segs=_ARC_SEGMENTS)


def largest_free_square_mm(bounds: Rect, obstacles: list[tuple[Rect, float]]) -> float:
    """Side of the largest axis-aligned square inside bounds that keeps
    clear of every obstacle, a rectangle (a point for a hole) with its
    Euclidean clearance. Bisection on the half-side t: a square fits where
    its centre lies in bounds shrunk by t and outside every obstacle grown
    by t, then by its clearance."""
    x0, y0, x1, y1 = bounds
    # an obstacle whose clearance zone stays outside the bounds never
    # touches a square inside them
    near = [
        (r, c) for r, c in obstacles
        if math.hypot(max(r[0] - x1, x0 - r[2], 0.0), max(r[1] - y1, y0 - r[3], 0.0)) < c
    ]

    def fits(t: float) -> bool:
        if x0 + t >= x1 - t or y0 + t >= y1 - t:
            return False
        room = box(x0 + t, y0 + t, x1 - t, y1 - t)
        if not near:
            return True
        grown = [
            box(r[0] - t, r[1] - t, r[2] + t, r[3] + t).buffer(c, quad_segs=_ARC_SEGMENTS)
            for r, c in near
        ]
        return not room.difference(unary_union(grown)).is_empty

    lo, hi = 0.0, min(x1 - x0, y1 - y0) / 2.0
    if not fits(_TOL_MM):
        return 0.0
    for _ in range(30):
        mid = 0.5 * (lo + hi)
        if fits(mid):
            lo = mid
        else:
            hi = mid
    return 2.0 * lo


def cluster_offsets(cfg: BoardConfig, pitch_mm: float) -> tuple[XY, ...]:
    """The four cluster sensors around the centre, on the diagonals."""
    d = cfg.hall_rfid.mockup.hall.cluster_offset_ratio * pitch_mm
    return tuple((sx * d, sy * d) for sx, sy in _CLUSTER_SIGNS)


def cluster_coverage(cfg: BoardConfig, pitch_mm: float | None = None) -> OffsetCoverage:
    """Offset coverage of the cluster square: centre sensor plus the four
    on the diagonals, with the mockup sensor."""
    if pitch_mm is None:
        pitch_mm = cfg.pitch.mockup_mm
    hall = cfg.hall_rfid.mockup.hall
    positions = ((0.0, 0.0), *cluster_offsets(cfg, pitch_mm))
    return offset_coverage(cfg, pitch_mm, hall.sensor, positions)


def _corridors(
    mk: HallRfidMockupCfg,
    p: float,
    loops: dict[str, MockupLoop],
    free: BaseGeometry,
    keepout: float,
) -> list[MockupCorridor]:
    cols, rows = mk.columns, mk.rows
    out = []
    for ri, row in enumerate(rows):
        for ci in range(len(cols) - 1):
            a, b = loops[f"{cols[ci]}{row}"], loops[f"{cols[ci + 1]}{row}"]
            band = (a.outline[2], ri * p, b.outline[0], (ri + 1) * p)
            facing = (max(a.outline[1], b.outline[1]), min(a.outline[3], b.outline[3]))
            out.append(_corridor(a, b, "y", band, facing, free, keepout))
    for ci, col in enumerate(cols):
        for ri in range(len(rows) - 1):
            a, b = loops[f"{col}{rows[ri]}"], loops[f"{col}{rows[ri + 1]}"]
            x0 = ci * p if ci == 0 else a.outline[0]
            x1 = (ci + 1) * p if ci == len(cols) - 1 else a.outline[2]
            band = (x0, a.outline[3], x1, b.outline[1])
            facing = (max(a.outline[0], b.outline[0]), min(a.outline[2], b.outline[2]))
            out.append(_corridor(a, b, "x", band, facing, free, keepout))
    return out


def _corridor(
    a: MockupLoop,
    b: MockupLoop,
    runs_along: str,
    band: Rect,
    facing: tuple[float, float],
    free: BaseGeometry,
    keepout: float,
) -> MockupCorridor:
    width = band[2] - band[0] if runs_along == "y" else band[3] - band[1]
    area = box(*band).intersection(free).area if width > 0.0 else 0.0
    return MockupCorridor(
        name=f"{a.square}|{b.square}",
        squares=(a.square, b.square),
        runs_along=runs_along,
        band=band,
        width_mm=width,
        free_width_mm=width - 2.0 * keepout,
        facing=facing,
        free_area_mm2=area,
    )


def _faces(corridor: MockupCorridor, square: str) -> str:
    first = corridor.squares[0] == square
    if corridor.runs_along == "y":
        return "E" if first else "W"
    return "N" if first else "S"


def _readers(
    mk: HallRfidMockupCfg,
    squares: list[MockupSquare],
    corridors: list[MockupCorridor],
    free: BaseGeometry,
) -> list[MockupReader]:
    """Widest adjacent corridor first; readers sharing one spread along the
    stretch where its two loops face each other, in square order."""
    f = mk.reader.footprint_square_mm
    chosen: dict[str, MockupCorridor] = {}
    for sq in squares:
        adjacent = [c for c in corridors if sq.name in c.squares]
        if adjacent:
            chosen[sq.name] = max(adjacent, key=lambda c: c.free_width_mm)
    out = []
    for sq in squares:
        cor = chosen.get(sq.name)
        if cor is None:
            continue
        sharing = [s.name for s in squares if s.name in chosen and chosen[s.name].name == cor.name]
        i, n = sharing.index(sq.name), len(sharing)
        along = cor.facing[0] + (i + 0.5) / n * (cor.facing[1] - cor.facing[0])
        if cor.runs_along == "y":
            centre = ((cor.band[0] + cor.band[2]) / 2.0, along)
        else:
            centre = (along, (cor.band[1] + cor.band[3]) / 2.0)
        fp = (centre[0] - f / 2.0, centre[1] - f / 2.0, centre[0] + f / 2.0, centre[1] + f / 2.0)
        fits = cor.free_width_mm >= f - _TOL_MM and free.contains(box(*fp).buffer(-_TOL_MM))
        out.append(
            MockupReader(
                square=sq.name,
                row=sq.row,
                part=mk.reader.by_row[sq.row],
                corridor=cor.name,
                faces=_faces(cor, sq.name),
                centre_mm=centre,
                footprint=fp,
                fits=fits,
            )
        )
    return out


def _ground(
    mk: HallRfidMockupCfg, p: float, loops: dict[str, MockupLoop], edge: float
) -> list[GroundSegment]:
    """Corridor centrelines: inter-column ones from the strip to the far
    edge clearance, inter-row ones across each column."""
    cols, rows = mk.columns, mk.rows
    top = len(rows) * p
    xs = []
    out = []
    for ci in range(len(cols) - 1):
        east = max(loops[f"{cols[ci]}{r}"].outline[2] for r in rows)
        west = min(loops[f"{cols[ci + 1]}{r}"].outline[0] for r in rows)
        x = (east + west) / 2.0
        xs.append(x)
        out.append(GroundSegment(f"{cols[ci]}|{cols[ci + 1]}", (x, top), (x, edge)))
    for ci, col in enumerate(cols):
        x0 = edge if ci == 0 else xs[ci - 1]
        x1 = len(cols) * p - edge if ci == len(cols) - 1 else xs[ci]
        for ri in range(len(rows) - 1):
            a, b = loops[f"{col}{rows[ri]}"], loops[f"{col}{rows[ri + 1]}"]
            y = (a.outline[3] + b.outline[1]) / 2.0
            out.append(GroundSegment(f"{a.square}|{b.square}", (x0, y), (x1, y)))
    return out


def layout(
    cfg: BoardConfig, pitch_mm: float | None = None, keepout_mm: float | None = None
) -> MockupLayout:
    """Geometry of the hallrfid board at that pitch and ground keepout
    (default: pitch.mockup_mm and mockup.ground_keepout_mm)."""
    mk = cfg.hall_rfid.mockup
    p = cfg.pitch.mockup_mm if pitch_mm is None else pitch_mm
    k = mk.ground_keepout_mm if keepout_mm is None else keepout_mm
    bd = mk.board
    n_cols, n_rows = len(mk.columns), len(mk.rows)
    width, top = n_cols * p, n_rows * p
    play = (0.0, 0.0, width, top)
    strip = (0.0, top, width, top + bd.strip_mm)
    useful = (0.0, 0.0, width, top + bd.strip_mm)

    squares, loops = [], {}
    for ri, row in enumerate(mk.rows):
        for ci, col in enumerate(mk.columns):
            name = f"{col}{row}"
            cx, cy = (ci + 0.5) * p, (ri + 0.5) * p
            squares.append(
                MockupSquare(name, col, row, (cx, cy), (ci * p, ri * p, (ci + 1) * p, (ri + 1) * p))
            )
            kind = mk.loop_by_column[col]
            spec = mk.loops[kind]
            s = spec.side_ratio * p
            loops[name] = MockupLoop(
                square=name,
                kind=kind,
                side_mm=s,
                turns=spec.turns,
                track_mm=spec.track_mm,
                gap_mm=spec.gap_mm,
                opening_mm=_opening_mm(spec, s),
                outline=(cx - s / 2.0, cy - s / 2.0, cx + s / 2.0, cy + s / 2.0),
                feed_side="",
            )
    order = [sq.name for sq in squares]

    margin = min(
        min(lp.outline[0], lp.outline[1], width - lp.outline[2], top - lp.outline[3])
        for lp in loops.values()
    )
    inset = margin / 2.0
    r_hole = bd.hole_d_mm / 2.0
    hole_xy = [(x, y) for y in (inset, top - inset) for x in (inset, width - inset)]
    useful_edge = box(*useful).exterior
    holes = [
        MockupHole(
            centre_mm=c,
            d_mm=bd.hole_d_mm,
            loop_clearance_mm=min(Point(c).distance(box(*lp.outline)) for lp in loops.values())
            - r_hole,
            edge_clearance_mm=Point(c).distance(useful_edge) - r_hole,
        )
        for c in hole_xy
    ]

    e = bd.edge_clearance_mm
    blocked = [_keepout(lp.outline, k) for lp in loops.values()]
    blocked += [Point(h.centre_mm).buffer(r_hole, quad_segs=_ARC_SEGMENTS) for h in holes]
    free = box(e, e, width - e, top).difference(unary_union(blocked))

    # own margin of each square (note 25, 4.2): what a reader would have
    # without the corridors, inside the square, the edge clearance kept
    obstacles = [(lp.outline, k) for lp in loops.values()]
    obstacles += [((*h.centre_mm, *h.centre_mm), r_hole) for h in holes]
    squares = [
        replace(
            sq,
            free_square_mm=largest_free_square_mm(
                (
                    max(sq.rect[0], e),
                    max(sq.rect[1], e),
                    min(sq.rect[2], width - e),
                    min(sq.rect[3], top),
                ),
                obstacles,
            ),
        )
        for sq in squares
    ]

    corridors = _corridors(mk, p, loops, free, k)
    readers = _readers(mk, squares, corridors, free)
    feeds = {r.square: r.faces for r in readers}
    loop_list = tuple(replace(loops[sq], feed_side=feeds.get(sq, "")) for sq in order)

    sites = []
    channels = mk.mux_channels
    for i, sq in enumerate(squares):
        signal = f"HALL_{sq.name}"
        sites.append(
            HallSite(
                square=sq.name,
                role="centre",
                offset_mm=(0.0, 0.0),
                centre_mm=sq.centre_mm,
                mux_channel=channels.centre[i] if i < len(channels.centre) else None,
                direct_signal=signal if signal in mk.esp32.pins else None,
            )
        )
    host = next((sq for sq in squares if sq.name == mk.hall.cluster_square), None)
    if host is not None:
        for j, (dx, dy) in enumerate(cluster_offsets(cfg, p)):
            sites.append(
                HallSite(
                    square=host.name,
                    role="cluster",
                    offset_mm=(dx, dy),
                    centre_mm=(host.centre_mm[0] + dx, host.centre_mm[1] + dy),
                    mux_channel=channels.cluster[j] if j < len(channels.cluster) else None,
                    direct_signal=None,
                )
            )

    if useful[3] - useful[1] >= useful[2] - useful[0]:
        rails = ((-bd.rail_mm, 0.0, 0.0, useful[3]), (width, 0.0, width + bd.rail_mm, useful[3]))
    else:
        rails = ((0.0, -bd.rail_mm, width, 0.0), (0.0, useful[3], width, useful[3] + bd.rail_mm))
    board = (
        min(r[0] for r in (useful, *rails)),
        min(r[1] for r in (useful, *rails)),
        max(r[2] for r in (useful, *rails)),
        max(r[3] for r in (useful, *rails)),
    )
    fe = bd.fiducial_edge_mm
    corners = (
        (board[0] + fe, board[1] + fe),
        (board[0] + fe, board[3] - fe),
        (board[2] - fe, board[1] + fe),
        (board[2] - fe, board[3] - fe),
    )
    rail_union = unary_union([box(*r) for r in rails])
    fiducials = tuple(
        Fiducial(
            centre_mm=c,
            d_mm=bd.fiducial_d_mm,
            mask_d_mm=bd.fiducial_mask_d_mm,
            on_rail=rail_union.contains(Point(c).buffer(bd.fiducial_mask_d_mm / 2.0)),
        )
        for c in corners[: bd.fiducials]
    )

    return MockupLayout(
        pitch_mm=p,
        keepout_mm=k,
        squares=tuple(squares),
        loops=loop_list,
        corridors=tuple(corridors),
        readers=tuple(readers),
        hall_sites=tuple(sites),
        play_area=play,
        strip=strip,
        useful=useful,
        board=board,
        rails=rails,
        holes=tuple(holes),
        ground=tuple(_ground(mk, p, loops, e)),
        fiducials=fiducials,
        hole_inset_mm=inset,
        free_area_mm2=free.area,
    )


def ground_rings(lay: MockupLayout) -> list[tuple[str, ...]]:
    """Closed faces of the ground copper, the strip pour included (its
    edge on the play side), each with the loops it encloses. A tree
    gives none."""
    x0, y0, x1, _ = lay.strip
    lines = [LineString([s.start, s.end]) for s in lay.ground]
    lines.append(LineString([(x0, y0), (x1, y0)]))
    rings = []
    for face in polygonize(unary_union(lines)):
        enclosed = tuple(
            lp.square
            for lp in lay.loops
            if face.contains(Point((lp.outline[0] + lp.outline[2]) / 2.0,
                                   (lp.outline[1] + lp.outline[3]) / 2.0))
        )
        rings.append(enclosed)
    return rings


@dataclass(frozen=True)
class HallChain:
    pitch_mm: float
    sensor: HallSensorCfg
    corner_khz: float          # RC filter corner
    carrier_db: float          # its attenuation at the NFC carrier, first order
    tau_us: float              # 1 k into the 10 nF plus the mux common node
    share_fraction: float      # mux common node over the filter capacitor plus it
    kick_quiescent_mv: float   # an empty square read right after the ground channel
    kick_quiescent_lsb: float
    kick_worst_mv: float       # the pressed king read right after the ground channel
    kick_worst_lsb: float
    settle_quiescent_us: float  # the empty-square kick back within settle_lsb
    settle_us: float           # worst kick back within settle_lsb (replaces mux.t_settle_us)
    channel_us: float          # settle plus the averaged samples, per mux channel
    row_on_typ_us: float       # ROW_EN to a valid reading: typical power-on, empty square
    row_on_max_us: float       # maximum power-on, pressed king
    king_pressed_v: float      # sensor output, typical sensitivity
    weakest_pawn_lsb: float    # pawn at the maximum gap, in ADC counts
    in_linear_range: bool


def _xy(point: XY) -> str:
    return f"({point[0]:.2f}, {point[1]:.2f})"


def _settle_us(tau_us: float, step_mv: float, criterion_mv: float) -> float:
    return tau_us * math.log(step_mv / criterion_mv) if step_mv > criterion_mv else 0.0


def hall_chain(cfg: BoardConfig, pitch_mm: float | None = None) -> HallChain:
    """Filter, mux settling and row power-on of the mockup Hall chain."""
    if pitch_mm is None:
        pitch_mm = cfg.pitch.mockup_mm
    hr = cfg.hall_rfid
    mh = hr.mockup.hall
    budget = hall_budget(cfg, pitch_mm, sensor_index(cfg, mh.sensor))
    sensor = budget.sensor
    r, c_f, c_on = mh.filter_r_ohm, mh.filter_c_nF * 1e-9, hr.mux.c_on_pF * 1e-12
    corner = 1.0 / (2.0 * math.pi * r * c_f)
    tau_us = r * (c_f + c_on) * 1e6
    share = c_on / (c_on + c_f)
    lsb = adc_lsb_mv(cfg)
    criterion = mh.settle_lsb * lsb
    quiescent_mv = sensor.quiescent_out_v * 1e3
    king_mv = quiescent_mv + budget.strongest_present_mT * sensor.sensitivity_mv_per_mt
    kick_q, kick_w = share * quiescent_mv, share * king_mv
    settle = _settle_us(tau_us, kick_w, criterion)
    esp = hr.esp32
    on_max = sensor.power_on_max_us if sensor.power_on_max_us is not None else sensor.power_on_us
    return HallChain(
        pitch_mm=pitch_mm,
        sensor=sensor,
        corner_khz=corner * 1e-3,
        carrier_db=-10.0 * math.log10(1.0 + (hr.nfc.f_hz / corner) ** 2),
        tau_us=tau_us,
        share_fraction=share,
        kick_quiescent_mv=kick_q,
        kick_quiescent_lsb=kick_q / lsb,
        kick_worst_mv=kick_w,
        kick_worst_lsb=kick_w / lsb,
        settle_quiescent_us=_settle_us(tau_us, kick_q, criterion),
        settle_us=settle,
        channel_us=settle + esp.samples_per_square * esp.adc_sample_us,
        row_on_typ_us=sensor.power_on_us + _settle_us(tau_us, quiescent_mv, criterion),
        row_on_max_us=on_max + _settle_us(tau_us, king_mv, criterion),
        king_pressed_v=king_mv * 1e-3,
        weakest_pawn_lsb=budget.weakest_present_lsb,
        in_linear_range=budget.in_linear_range,
    )


@dataclass(frozen=True)
class MockupPower:
    loads_ma: dict[str, float]   # module, one transmitter, every reader awake, Hall sensors
    total_ma: float
    v_out: float
    dissipation_nominal_w: float  # at the nominal input
    dissipation_w: float          # at the highest input
    t_junction_c: float           # at the highest input, ambient of the yaml
    p_max_w: float                # dissipation that brings the junction to its limit
    current_ok: bool
    thermal_ok: bool

    @property
    def ok(self) -> bool:
        return self.current_ok and self.thermal_ok


def power(cfg: BoardConfig) -> MockupPower:
    """Worst 3.3 V load, radio off: the module, one reader transmitting at
    its TVDD limit, every reader awake at its maximum, every Hall sensor
    at its maximum, all through the linear regulator."""
    mk = cfg.hall_rfid.mockup
    pw = mk.power
    sensor = cfg.hall_rfid.sensor(mk.hall.sensor)
    n_squares = len(mk.squares())
    n_sensors = n_squares + (len(_CLUSTER_SIGNS) if mk.hall.cluster_square in mk.squares() else 0)
    i_sensor = sensor.i_supply_max_ma if sensor.i_supply_max_ma is not None else sensor.i_supply_ma
    loads = {
        "esp32": pw.esp32_ma,
        "reader_tx": mk.reader.i_tvdd_max_ma,
        "readers_awake": n_squares * mk.reader.i_idle_max_ma,
        "hall_sensors": n_sensors * i_sensor,
    }
    total = sum(loads.values())
    v_nom, v_max = pw.v_in
    v_out = pw.regulator.v_out
    p_nom = (v_nom - v_out) * total * 1e-3
    p_max_in = (v_max - v_out) * total * 1e-3
    tj = pw.t_ambient_c + pw.theta_ja_c_per_w * p_max_in
    return MockupPower(
        loads_ma=loads,
        total_ma=total,
        v_out=v_out,
        dissipation_nominal_w=p_nom,
        dissipation_w=p_max_in,
        t_junction_c=tj,
        p_max_w=(pw.t_junction_max_c - pw.t_ambient_c) / pw.theta_ja_c_per_w,
        current_ok=total * 1e-3 <= pw.regulator.i_max_a,
        thermal_ok=tj <= pw.t_junction_max_c,
    )


def _pin_problems(cfg: BoardConfig) -> list[str]:
    mk = cfg.hall_rfid.mockup
    esp = mk.esp32
    pins = esp.pins
    problems = []
    gpios = list(pins.values())
    for g in sorted({g for g in gpios if gpios.count(g) > 1}):
        problems.append(f"GPIO{g} carries two signals")
    for sig in esp.analog_signals:
        if sig not in pins:
            problems.append(f"analog signal {sig} has no pin")
        elif pins[sig] not in esp.adc1_gpios:
            problems.append(f"{sig} on GPIO{pins[sig]}, not an ADC1 input")
    for sig in esp.usb_signals:
        if pins.get(sig) not in esp.usb_gpios:
            problems.append(f"{sig} off the USB pins")
    for sig, g in pins.items():
        if g in esp.strapping_gpios:
            problems.append(f"{sig} drives the strapping pin GPIO{g}")
        if g in esp.usb_gpios and sig not in esp.usb_signals:
            problems.append(f"{sig} takes the USB pin GPIO{g}")
        if g in esp.psram_gpios:
            problems.append(f"{sig} on GPIO{g}, kept free for the octal PSRAM")
    bits = math.ceil(math.log2(cfg.hall_rfid.mux.channels))
    required = [f"MUX_S{i}" for i in range(bits)]
    required += [f"ROW_EN{row}" for row in mk.rows]
    for sq in mk.squares():
        required += [f"HALL_{sq}", f"NSS_{sq}", f"NRSTPD_{sq}"]
        if f"HALL_{sq}" not in esp.analog_signals:
            problems.append(f"HALL_{sq} not declared analog")
    problems += [f"the pin map lacks {sig}" for sig in required if sig not in pins]
    return problems


def _mux_problems(cfg: BoardConfig) -> list[str]:
    mk = cfg.hall_rfid.mockup
    ch = mk.mux_channels
    n = cfg.hall_rfid.mux.channels
    used = ch.all_channels()
    problems = []
    if len(used) != len(set(used)):
        problems.append("a mux channel is used twice")
    if any(not 0 <= c < n for c in used):
        problems.append(f"a mux channel lies beyond the {n} of the {cfg.hall_rfid.mux.part}")
    if len(ch.centre) != len(mk.squares()):
        problems.append("the mux map needs one centre channel per square")
    if len(ch.cluster) != len(_CLUSTER_SIGNS):
        problems.append("the mux map needs one channel per cluster sensor")
    return problems


def check(
    cfg: BoardConfig, pitch_mm: float | None = None, keepout_mm: float | None = None
) -> list[str]:
    """Guards of the hallrfid board at that pitch and ground keepout; an
    empty list means the layout holds."""
    mk = cfg.hall_rfid.mockup
    lay = layout(cfg, pitch_mm, keepout_mm)
    k = lay.keepout_mm
    problems = []

    for rd in lay.readers:
        if not rd.fits:
            problems.append(
                f"reader of {rd.square} does not fit corridor {rd.corridor} "
                f"outside the {k:g} mm ground keepout"
            )
    for a, b in combinations(lay.readers, 2):
        if box(*a.footprint).intersection(box(*b.footprint)).area > _TOL_MM:
            problems.append(f"readers of {a.square} and {b.square} overlap")
    if len(lay.readers) != len(lay.squares):
        problems.append("a square has no corridor for its reader")

    for enclosed in ground_rings(lay):
        around = ", ".join(enclosed) if enclosed else "no loop"
        problems.append(f"ground forms a ring around {around}")
    for seg in lay.ground:
        line = LineString([seg.start, seg.end])
        for lp in lay.loops:
            if line.distance(box(*lp.outline)) < k - _TOL_MM:
                problems.append(f"ground along {seg.corridor} enters the keepout of {lp.square}")
    for rd in lay.readers:
        if not any(LineString([s.start, s.end]).intersects(box(*rd.footprint))
                   for s in lay.ground):
            problems.append(f"reader of {rd.square} is off the ground tree")

    limit = cfg.plateau.quadrant.front_end_max_height_mm
    for name, h in mk.play_area_heights_mm.items():
        if h > limit:
            problems.append(f"{name} stands {h:g} mm, over the {limit:g} mm under the plywood")
    for part in (mk.hall.sensor, mk.hall.alternate):
        h = cfg.hall_rfid.sensor(part).height_mm
        if h > limit:
            problems.append(f"{part} stands {h:g} mm, over the {limit:g} mm under the plywood")

    for hole in lay.holes:
        if hole.loop_clearance_mm <= 0.0:
            problems.append(f"M3 hole at {_xy(hole.centre_mm)} cuts a loop")
        if hole.edge_clearance_mm <= 0.0:
            problems.append(f"M3 hole at {_xy(hole.centre_mm)} breaks the board edge")

    for fid in lay.fiducials:
        if not fid.on_rail:
            problems.append(f"fiducial at {_xy(fid.centre_mm)} leaves the rails")
    if len(lay.fiducials) < mk.board.fiducials:
        problems.append("more fiducials than board corners")

    if mk.hall.cluster_square in mk.squares():
        lp = lay.loop(mk.hall.cluster_square)
        half = lp.opening_mm / 2.0
        land = mk.hall.land_mm
        sites = [s for s in lay.hall_sites if s.square == lp.square]
        for s in sites:
            if max(abs(s.offset_mm[0]), abs(s.offset_mm[1])) + land / 2.0 > half:
                problems.append(
                    f"Hall sensor at {_xy(s.offset_mm)} leaves the opening of {lp.square}"
                )
        for a, b in combinations(sites, 2):
            dx = abs(a.offset_mm[0] - b.offset_mm[0])
            dy = abs(a.offset_mm[1] - b.offset_mm[1])
            if dx < land and dy < land:
                problems.append(f"Hall sensors of {lp.square} overlap")
        cov = cluster_coverage(cfg, lay.pitch_mm)
        if not cov.ok:
            problems.append(
                f"the {lp.square} cluster covers +-{cov.covered_mm:.2f} mm, "
                f"under the admissible +-{cov.admissible_mm:g} mm"
            )
    else:
        problems.append(f"cluster square {mk.hall.cluster_square} is not on the board")

    problems += _pin_problems(cfg)
    problems += _mux_problems(cfg)

    pw = power(cfg)
    if not pw.current_ok:
        problems.append(
            f"3.3 V load of {pw.total_ma:.0f} mA over the {mk.power.regulator.part} rating"
        )
    if not pw.thermal_ok:
        problems.append(f"{mk.power.regulator.part} junction at {pw.t_junction_c:.0f} C")
    rail = mk.power.regulator.v_out
    for part in (mk.hall.sensor, mk.hall.alternate):
        if cfg.hall_rfid.sensor(part).supply_v != rail:
            problems.append(f"{part} is specified at another supply than the {rail:g} V rail")
    if mk.reader.tvdd_v != rail:
        problems.append(f"the readers' TVDD differs from the {rail:g} V rail")
    # the RFID chain: matching, tags in their bases, activation (nfc.py)
    problems += nfc_mockup_check(cfg, lay.pitch_mm)
    return problems
