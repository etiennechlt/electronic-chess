"""The 100 x 100 mm Hall plus RFID technology demonstrator (`hallrfid-demo`,
note 27): the bench of note 25 cut down to one row of two squares, with
the electronics strip past the row and each reader in the strip under
its own loop. Pure arithmetic on the config, no CAD: the board generator
(`boardgen.hallrfid`) draws what layout() returns and check() refuses a
layout that does not hold.

Frame: origin at the outer corner of square A1, x along the columns (A,
B), y along the single row, away from the player; the strip lies past
the row (larger y), the board is `demo.board.size_mm`. All lengths in mm.

Layout rules, those of the mockup where they still apply (note 25,
paragraphs 4.1 to 4.3) and what the single row changes:

- Each square carries one square loop, centred, of the geometry of its
  column (demo.loop_by_column, loops of the mockup); both ends of a loop
  leave on its south side, toward the strip, where its reader sits.
- The ground copper is one pour over the strip, starting
  ground_keepout_mm past the lowest loop copper; it never enters the play
  area, so no ground ever rings a loop. The matching branches that
  reach a loop's feed and the sensor trios are the only copper inside
  the keepout (D12).
- Each reader, with its quartz, filter and matching network, lives in
  a zone of the strip directly under its loop: the loop's width, from
  just past the feed pads to reader_zone_mm past the pour's edge.
- The sensor trios leave each loop opening on the back layer through a
  corridor west of the feed (trio_exit_mm), down to the strip.
- The M3 holes sit at the play-area corners at half the smallest
  loop-to-edge margin, and at the strip's far corners; the fiducials in
  the strip, three corners of its free area.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import combinations

from shapely.geometry import Point, box

from .config import BoardConfig
from .hallrfid_mockup import (
    _CLUSTER_SIGNS,
    _TOL_MM,
    Fiducial,
    HallSite,
    MockupHole,
    MockupLoop,
    MockupPower,
    MockupSquare,
    _opening_mm,
    _xy,
    cluster_coverage,
    cluster_offsets,
    hall_chain,
)
from .hallrfid_mockup import power as mockup_power
from .nfc import mockup_check as nfc_mockup_check

Rect = tuple[float, float, float, float]
XY = tuple[float, float]

# the feed of a loop (boardgen.nfcloop draws it): both ends leave the
# south side, the top-side start this far west of the centre and the
# back-side bridge this far east of it, so the two series resistors sit
# side by side under the loop
FEED_OFFSET_MM = 1.2
BRIDGE_OFFSET_MM = 1.2
FEED_TRACK_MM = 0.5  # the two feed tracks, start to its resistor and bridge end to its
FIDUCIAL_D_MM = 1.0
FIDUCIAL_MASK_D_MM = 2.0


@dataclass(frozen=True)
class DemoLayout:
    pitch_mm: float
    keepout_mm: float
    squares: tuple[MockupSquare, ...]
    loops: tuple[MockupLoop, ...]
    hall_sites: tuple[HallSite, ...]
    play_area: Rect
    strip: Rect
    board: Rect
    pour: Rect  # the strip ground pour
    reader_zones: dict[str, Rect]  # per square: a reader and its network, under its loop
    trio_corridors: dict[str, Rect]  # per square: back-side exit of the sensor trios
    holes: tuple[MockupHole, ...]
    fiducials: tuple[Fiducial, ...]
    hole_inset_mm: float

    def loop(self, square: str) -> MockupLoop:
        return next(lp for lp in self.loops if lp.square == square)

    def square(self, name: str) -> MockupSquare:
        return next(sq for sq in self.squares if sq.name == name)


def layout(cfg: BoardConfig, pitch_mm: float | None = None) -> DemoLayout:
    """Geometry of the demonstrator board at that pitch (default: the
    mockup pitch, 50 mm)."""
    dm = cfg.hall_rfid.demo
    mk = cfg.hall_rfid.mockup
    p = cfg.pitch.mockup_mm if pitch_mm is None else pitch_mm
    k = dm.ground_keepout_mm
    bd = dm.board
    width, height = bd.size_mm
    n_cols = len(dm.columns)
    top = len(dm.rows) * p
    play = (0.0, 0.0, n_cols * p, top)
    strip = (0.0, top, width, height)
    board = (0.0, 0.0, width, height)

    squares, loops = [], []
    for ci, col in enumerate(dm.columns):
        row = dm.rows[0]
        name = f"{col}{row}"
        cx, cy = (ci + 0.5) * p, 0.5 * p
        squares.append(MockupSquare(name, col, row, (cx, cy), (ci * p, 0.0, (ci + 1) * p, top)))
        spec = mk.loops[dm.loop_by_column[col]]
        s = spec.side_ratio * p
        loops.append(
            MockupLoop(
                square=name,
                kind=dm.loop_by_column[col],
                side_mm=s,
                turns=spec.turns,
                track_mm=spec.track_mm,
                gap_mm=spec.gap_mm,
                opening_mm=_opening_mm(spec, s),
                outline=(cx - s / 2.0, cy - s / 2.0, cx + s / 2.0, cy + s / 2.0),
                feed_side="S",
            )
        )

    margin = min(
        min(lp.outline[0], lp.outline[1], play[2] - lp.outline[2], top - lp.outline[3])
        for lp in loops
    )
    inset = margin / 2.0
    r_hole = bd.hole_d_mm / 2.0
    hole_xy = [
        (inset, inset),
        (width - inset, inset),
        (inset, top - inset),
        (width - inset, top - inset),
        (inset, height - inset),
        (width - inset, height - inset),
    ]
    board_edge = box(*board).exterior
    holes = tuple(
        MockupHole(
            centre_mm=c,
            d_mm=bd.hole_d_mm,
            loop_clearance_mm=min(Point(c).distance(box(*lp.outline)) for lp in loops) - r_hole,
            edge_clearance_mm=Point(c).distance(board_edge) - r_hole,
        )
        for c in hole_xy
    )

    pour_top = max(lp.outline[3] for lp in loops) + k
    pm = bd.pour_margin_mm
    pour = (pm, pour_top, width - pm, height - pm)

    zones: dict[str, Rect] = {}
    corridors: dict[str, Rect] = {}
    for lp in loops:
        x0, _y0, x1, y1 = lp.outline
        cx = (x0 + x1) / 2.0
        zones[lp.square] = (x0, y1 + lp.track_mm / 2.0, x1, pour_top + dm.reader_zone_mm)
        e0, e1 = dm.trio_exit_mm
        cy = (lp.outline[1] + lp.outline[3]) / 2.0
        corridors[lp.square] = (cx + e0, cy + lp.opening_mm / 2.0, cx + e1, pour_top)

    sites: list[HallSite] = []
    channels = dm.mux_channels
    for i, sq in enumerate(squares):
        signal = f"HALL_{sq.name}"
        sites.append(
            HallSite(
                square=sq.name,
                role="centre",
                offset_mm=(0.0, 0.0),
                centre_mm=sq.centre_mm,
                mux_channel=channels.centre[i] if i < len(channels.centre) else None,
                direct_signal=signal if signal in dm.esp32.pins else None,
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

    # three corners of the strip's free area, off the connectors of the
    # south edge and the module's antenna on the east edge
    fe = bd.edge_clearance_mm + 1.0
    fid_xy = (
        (0.30 * width, height - fe),
        (width - fe, 0.52 * height),
        (0.06 * width, max(pour_top, top) + fe),
    )
    fiducials = tuple(
        Fiducial(centre_mm=c, d_mm=FIDUCIAL_D_MM, mask_d_mm=FIDUCIAL_MASK_D_MM, on_rail=True)
        for c in fid_xy[: bd.fiducials]
    )

    return DemoLayout(
        pitch_mm=p,
        keepout_mm=k,
        squares=tuple(squares),
        loops=tuple(loops),
        hall_sites=tuple(sites),
        play_area=play,
        strip=strip,
        board=board,
        pour=pour,
        reader_zones=zones,
        trio_corridors=corridors,
        holes=holes,
        fiducials=fiducials,
        hole_inset_mm=inset,
    )


def power(cfg: BoardConfig) -> MockupPower:
    """The 3.3 V budget of the demonstrator: two readers, six sensors."""
    lay = layout(cfg)
    return mockup_power(cfg, n_readers=len(lay.squares), n_sensors=len(lay.hall_sites))


def _pin_problems(cfg: BoardConfig) -> list[str]:
    dm = cfg.hall_rfid.demo
    esp = cfg.hall_rfid.mockup.esp32  # the module, its GPIO lists and its rules
    pins = dm.esp32.pins
    problems = []
    gpios = list(pins.values())
    for g in sorted({g for g in gpios if gpios.count(g) > 1}):
        problems.append(f"GPIO{g} carries two signals")
    for sig, g in pins.items():
        if g not in esp.module_gpios:
            problems.append(f"{sig} on GPIO{g}, not a pin of the {esp.module}")
    analog = ["MUX_OUT", "PICKUP"] + [f"HALL_{sq}" for sq in dm.squares()]
    for sig in analog:
        if sig not in pins:
            problems.append(f"analog signal {sig} has no pin")
        elif pins[sig] not in esp.adc1_gpios:
            problems.append(f"{sig} on GPIO{pins[sig]}, not an ADC1 input")
    for sig, g in zip(esp.usb_signals, esp.usb_gpios, strict=True):
        if pins.get(sig) != g:
            problems.append(f"{sig} off its USB pin GPIO{g}")
    for sig, g in pins.items():
        if g in esp.strapping_gpios:
            problems.append(f"{sig} drives the strapping pin GPIO{g}")
        if g in esp.usb_gpios and sig not in esp.usb_signals:
            problems.append(f"{sig} takes the USB pin GPIO{g}")
        if g in esp.psram_gpios:
            problems.append(f"{sig} on GPIO{g}, kept free for the octal PSRAM")
    bits = math.ceil(math.log2(cfg.hall_rfid.mux.channels))
    required = [f"MUX_S{i}" for i in range(bits)]
    required += [f"ROW_EN{row}" for row in dm.rows]
    required += ["SPI_MOSI", "SPI_SCK", "SPI_MISO", "RFID_IRQ", "LED", *esp.usb_signals]
    for sq in dm.squares():
        required += [f"NSS_{sq}", f"NRSTPD_{sq}"]
    problems += [f"the pin map lacks {sig}" for sig in required if sig not in pins]
    rails = {"3V3", "GND"}
    for sig in dm.escape_header:
        if sig not in pins and sig not in rails:
            problems.append(f"escape header carries {sig}, which has no pin")
    return problems


def _mux_problems(cfg: BoardConfig) -> list[str]:
    dm = cfg.hall_rfid.demo
    ch = dm.mux_channels
    n = cfg.hall_rfid.mux.channels
    used = ch.all_channels()
    problems = []
    if len(used) != len(set(used)):
        problems.append("a mux channel is used twice")
    if any(not 0 <= c < n for c in used):
        problems.append(f"a mux channel lies beyond the {n} of the {cfg.hall_rfid.mux.part}")
    if len(ch.centre) != len(dm.squares()):
        problems.append("the mux map needs one centre channel per square")
    if len(ch.cluster) != len(_CLUSTER_SIGNS):
        problems.append("the mux map needs one channel per cluster sensor")
    if len(set(used)) != n:
        problems.append(f"every one of the {n} mux inputs must be assigned or grounded")
    return problems


def check(cfg: BoardConfig, pitch_mm: float | None = None) -> list[str]:
    """Guards of the demonstrator board; an empty list means it holds."""
    dm = cfg.hall_rfid.demo
    mk = cfg.hall_rfid.mockup
    lay = layout(cfg, pitch_mm)
    p, k = lay.pitch_mm, lay.keepout_mm
    width, height = dm.board.size_mm
    problems = []

    if abs(len(dm.columns) * p - width) > _TOL_MM:
        problems.append(f"{len(dm.columns)} squares of {p:g} mm do not span the {width:g} mm board")
    if abs(len(dm.rows) * p + dm.board.strip_mm - height) > _TOL_MM:
        problems.append("row plus strip do not make the board height")

    for lp in lay.loops:
        sq = lay.square(lp.square)
        if any(a < b - _TOL_MM for a, b in zip(lp.outline[:2], sq.rect[:2], strict=True)) or any(
            a > b + _TOL_MM for a, b in zip(lp.outline[2:], sq.rect[2:], strict=True)
        ):
            problems.append(f"loop of {lp.square} leaves its square")
        if lp.outline[3] + k > lay.pour[1] + _TOL_MM:
            problems.append(f"ground pour enters the keepout of {lp.square}")

    zones = list(lay.reader_zones.items())
    for name, z in zones:
        if z[1] >= z[3] or z[0] >= z[2]:
            problems.append(f"reader zone of {name} is empty")
        if z[3] > height - dm.board.edge_clearance_mm:
            problems.append(f"reader zone of {name} runs past the strip")
        area = (z[2] - z[0]) * (z[3] - z[1])
        if area < mk.reader.area_mm2[0]:
            problems.append(f"reader zone of {name} offers {area:.0f} mm2 for a reader")
        if z[2] - z[0] < mk.reader.footprint_square_mm:
            problems.append(f"reader zone of {name} is narrower than the reader")
    for (a, za), (b, zb) in combinations(zones, 2):
        if box(*za).intersection(box(*zb)).area > _TOL_MM:
            problems.append(f"reader zones of {a} and {b} overlap")

    for name, c in lay.trio_corridors.items():
        lp = lay.loop(name)
        cx = (lp.outline[0] + lp.outline[2]) / 2.0
        east_limit = (
            cx - FEED_OFFSET_MM - FEED_TRACK_MM / 2.0 - cfg.hall_rfid.mockup.hall.trio_pitch_mm
        )
        if c[0] < lp.outline[0] + lp.track_mm or c[2] > east_limit + _TOL_MM:
            problems.append(f"trio corridor of {name} is not west of the feed inside the loop")
        if c[1] >= c[3]:
            problems.append(f"trio corridor of {name} has no length")

    limit = cfg.plateau.quadrant.front_end_max_height_mm
    for part_name, h in mk.play_area_heights_mm.items():
        if h > limit:
            problems.append(f"{part_name} stands {h:g} mm, over the {limit:g} mm under the plywood")
    for part in (mk.hall.sensor, mk.hall.alternate):
        h = cfg.hall_rfid.sensor(part).height_mm
        if h > limit:
            problems.append(f"{part} stands {h:g} mm, over the {limit:g} mm under the plywood")

    for hole in lay.holes:
        if hole.loop_clearance_mm <= 0.0:
            problems.append(f"M3 hole at {_xy(hole.centre_mm)} cuts a loop")
        if hole.edge_clearance_mm <= 0.0:
            problems.append(f"M3 hole at {_xy(hole.centre_mm)} breaks the board edge")
    strip = box(*lay.strip)
    for fid in lay.fiducials:
        if not strip.contains(Point(fid.centre_mm)):
            problems.append(f"fiducial at {_xy(fid.centre_mm)} leaves the strip")
        if any(Point(fid.centre_mm).distance(Point(h.centre_mm)) < h.d_mm for h in lay.holes):
            problems.append(f"fiducial at {_xy(fid.centre_mm)} sits on a hole")

    land = mk.hall.land_mm
    for s in lay.hall_sites:
        half = lay.loop(s.square).opening_mm / 2.0
        if max(abs(s.offset_mm[0]), abs(s.offset_mm[1])) + land / 2.0 > half:
            problems.append(f"Hall sensor at {_xy(s.offset_mm)} leaves the opening of {s.square}")
    if mk.hall.cluster_square in dm.squares():
        lp = lay.loop(mk.hall.cluster_square)
        sites = [s for s in lay.hall_sites if s.square == lp.square]
        for a, b in combinations(sites, 2):
            dx = abs(a.offset_mm[0] - b.offset_mm[0])
            dy = abs(a.offset_mm[1] - b.offset_mm[1])
            if dx < land and dy < land:
                problems.append(f"Hall sensors of {lp.square} overlap")
        cov = cluster_coverage(cfg, p)
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
    reg = mk.power.regulator
    if not pw.current_ok:
        problems.append(f"3.3 V load of {pw.total_ma:.0f} mA over the {reg.part} rating")
    if not pw.thermal_ok:
        problems.append(f"{reg.part} junction at {pw.t_junction_c:.0f} C")
    if not pw.headroom_ok:
        problems.append(f"{reg.part} input leaves {pw.headroom_v:.2f} V, under its dropout")
    for part in (mk.hall.sensor, mk.hall.alternate):
        if cfg.hall_rfid.sensor(part).supply_v != reg.v_out:
            problems.append(f"{part} is specified at another supply than the {reg.v_out:g} V rail")
    full_scale_v = cfg.hall_rfid.esp32.adc_full_scale_mv * 1e-3
    for part in (mk.hall.sensor, mk.hall.alternate):
        ch = hall_chain(cfg, p, part)
        if not ch.in_linear_range:
            problems.append(f"{part}: the pressed king leaves the sensor's linear range")
        if ch.king_pressed_v > full_scale_v:
            problems.append(f"{part}: the pressed king reads over the ADC full scale")

    problems += nfc_mockup_check(cfg, p)
    return problems
