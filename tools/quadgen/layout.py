"""Floor plan of one quadrant: coil grid, terminals, escape lanes, LED
placement and chain order, strip zones. Pure geometry from the config,
KiCad coordinates (origin top-left, y down).

Board frame: the front-end strip occupies x in [0, strip]; the coil
grid starts at x = strip, square (i, j) has its center at
(strip + (i + 0.5) p, (j + 0.5) p). Rows alternate the side of their
coil terminal so that the two rows around each "band" (the corridor
between rows 2b and 2b + 1) escape into that band, west, to the strip.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from chessboard_calc.config import BoardConfig, resolve_geometry
from chessboard_calc.inductance import pcb_sense_coil

LED_BODY = 5.0
LED_PAD_DX, LED_PAD_DY = 2.45, 1.65  # WS2812B PLCC4 pad centers
LED_ROLES = {"1": "VDD", "2": "DOUT", "3": "VSS", "4": "DIN"}


@dataclass(frozen=True)
class Coil:
    idx: int  # 0..15, row-major from the north-west
    col: int
    row: int
    center: tuple[float, float]
    terminal: tuple[float, float]
    start_angle_deg: float  # spiral start: -90 north terminal, +90 south
    band: int
    lane_y: float  # escape lane in the band
    lane_x: float  # vertical lane down the strip
    cell: int  # front-end cell index 0..15
    cell_y: float

    @property
    def net(self) -> str:
        return f"C{self.idx + 1}"


@dataclass(frozen=True)
class Led:
    ref: str
    coil: int
    corner: str  # NW or SE
    x: float
    y: float
    rot: float  # 0 or 180
    order: int  # position in the data chain

    def pad(self, number: str) -> tuple[float, float]:
        dx, dy = {
            "1": (-LED_PAD_DX, -LED_PAD_DY),
            "2": (-LED_PAD_DX, LED_PAD_DY),
            "3": (LED_PAD_DX, LED_PAD_DY),
            "4": (LED_PAD_DX, -LED_PAD_DY),
        }[number]
        if self.rot == 180.0:
            dx, dy = -dx, -dy
        return self.x + dx, self.y + dy

    def via(self, number: str, stub: float) -> tuple[float, float]:
        """Via of a pad: sideways in x, away from the body."""
        px, py = self.pad(number)
        return px + math.copysign(stub, px - self.x), py

    def via_of(self, role: str, stub: float) -> tuple[float, float]:
        number = next(n for n, r in LED_ROLES.items() if r == role)
        return self.via(number, stub)


@dataclass(frozen=True)
class Layout:
    pitch: float
    n: int
    strip_w: float
    board_w: float
    board_h: float
    r_out: float
    r_in: float
    turns_per_layer: int
    spiral_track: float
    coils: tuple[Coil, ...]
    leds: tuple[Led, ...]
    band_lanes: tuple[tuple[float, ...], ...]  # per band, top to bottom
    cell_ys: tuple[float, ...]
    connector_xy: tuple[float, float]
    pin_hole_xy: tuple[float, float]
    mounting_holes: tuple[tuple[float, float], ...]

    def coil(self, col: int, row: int) -> Coil:
        return self.coils[row * self.n + col]

    @property
    def corridor_xs(self) -> tuple[float, ...]:
        """Vertical corridor centerlines between columns (inner ones)."""
        return tuple(self.strip_w + k * self.pitch for k in range(1, self.n))

    @property
    def corridor_ys(self) -> tuple[float, ...]:
        return tuple(k * self.pitch for k in range(1, self.n))


def make_layout(cfg: BoardConfig) -> Layout:
    q = cfg.plateau.quadrant
    p = cfg.pitch.plateau_mm
    n = q.squares
    strip = q.front_end_strip_mm
    geo = resolve_geometry(cfg, p)
    sense = pcb_sense_coil(cfg, p)
    r_out, r_in = geo.sense_d_out_mm / 2.0, geo.sense_d_in_mm / 2.0
    rt = q.routing
    inset = cfg.mockup.coil_board.leds.corner_inset_mm
    board_w, board_h = strip + n * p, n * p

    # Escape bands: one per pair of rows, lanes ordered top to bottom as
    # [row 2b cols 0..n-1, row 2b+1 cols n-1..0]. The free interval is
    # bounded by the LED bodies of both rows.
    n_lanes = 2 * n
    lane_pitch = rt.lane_pitch_mm
    half_span = (n_lanes - 1) * lane_pitch / 2.0
    band_lanes = []
    for b in range(n // 2):
        yb = (2 * b + 1) * p
        free_lo = yb - inset + LED_BODY / 2.0 + rt.track_clearance_mm + rt.route_track_mm / 2.0
        free_hi = yb + inset - LED_BODY / 2.0 - rt.track_clearance_mm - rt.route_track_mm / 2.0
        if yb - half_span < free_lo or yb + half_span > free_hi:
            raise ValueError("escape band too narrow for the lanes between the LED bodies")
        band_lanes.append(tuple(yb - half_span + k * lane_pitch for k in range(n_lanes)))

    # Front-end cells down the strip, one per coil, 8 per band.
    st = q.strip
    per_band = n_lanes
    cell_ys = []
    y0 = st.connector_zone_mm
    for b in range(n // 2):
        top = y0 + b * (per_band * st.cell_pitch_mm + st.middle_zone_mm)
        cell_ys += [top + (m + 0.5) * st.cell_pitch_mm for m in range(per_band)]
    if cell_ys[-1] + st.cell_pitch_mm / 2.0 > board_h:
        raise ValueError("strip floor plan overflows the board")
    guard = rt.route_track_mm + rt.track_clearance_mm
    for lanes in band_lanes:
        for yc in cell_ys:
            if lanes[0] - guard < yc < lanes[-1] + guard:
                raise ValueError(f"cell at y = {yc:.2f} lies inside an escape band")

    coils = []
    for row in range(n):
        for col in range(n):
            idx = row * n + col
            cx, cy = strip + (col + 0.5) * p, (row + 0.5) * p
            up = row % 2 == 1  # odd rows escape north
            terminal = (cx, cy - r_out) if up else (cx, cy + r_out)
            band = row // 2
            lanes = band_lanes[band]
            k = col if row % 2 == 0 else (2 * n - 1 - col)
            lane_y = lanes[k]
            # cells of this band and the up/down split around the lanes
            cells = list(range(band * per_band, (band + 1) * per_band))
            n_up = sum(1 for c in cells if cell_ys[c] < lanes[0])
            if k < n_up:
                cell = cells[n_up - 1 - k]
                xi = n_up - 1 - k
            else:
                cell = cells[per_band - 1 - (k - n_up)]
                xi = k - n_up
            lane_x = st.lane_x0_mm + xi * lane_pitch
            coils.append(
                Coil(
                    idx,
                    col,
                    row,
                    (cx, cy),
                    terminal,
                    -90.0 if up else 90.0,
                    band,
                    lane_y,
                    lane_x,
                    cell,
                    cell_ys[cell],
                )
            )

    # LEDs: NW then SE in every square, rows serpentine. Rotations put
    # DIN toward the previous LED and DOUT toward the next one (see the
    # board builder for the hop geometry).
    d = p / 2.0 - inset
    leds = []
    order = 0
    for row in range(n):
        cols = range(n) if row % 2 == 0 else range(n - 1, -1, -1)
        for col in cols:
            coil = coils[row * n + col]
            cx, cy = coil.center
            east_col = col == n - 1
            if row % 2 == 0:
                rot_nw, rot_se = (180.0, 0.0) if east_col else (0.0, 180.0)
            else:
                rot_nw, rot_se = 180.0, 0.0
            for corner, (x, y), rot in (
                ("NW", (cx - d, cy - d), rot_nw),
                ("SE", (cx + d, cy + d), rot_se),
            ):
                order += 1
                leds.append(Led(f"LD{order}", coil.idx, corner, x, y, rot, order))

    return Layout(
        pitch=p,
        n=n,
        strip_w=strip,
        board_w=board_w,
        board_h=board_h,
        r_out=r_out,
        r_in=r_in,
        turns_per_layer=sense.turns_per_layer,
        spiral_track=sense.track_width_mm,
        coils=tuple(coils),
        leds=tuple(leds),
        band_lanes=tuple(band_lanes),
        cell_ys=tuple(cell_ys),
        connector_xy=(5.5, st.connector_zone_mm / 2.0 + 1.5),
        pin_hole_xy=(3.0, board_h - 3.0),
        # east edge, in the stretches free of LED vias and chain hops
        mounting_holes=((board_w - 2.5, 1.4 * p), (board_w - 2.5, 3.4 * p)),
    )
