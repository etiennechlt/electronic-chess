"""Hall-sensor presence layer: the piece's own ferrite read by one analog
sensor per square (note 24, alternative or intermediate step to the LC
identification of ADR 0001).

The piece magnet (piece_magnet, ADR 0002) is a uniformly magnetized disc.
Its field is that of a cylindrical current sheet of density Br / mu0 on
the lateral surface, computed as a stack of circular current loops with
the exact off-axis loop field (complete elliptic integrals), the same
filament method as coupling.py. On axis the stack converges to the
closed form, which the tests check.

Geometry convention: z_mm is the distance from the near face of the
magnet to the Hall plate. The nominal value derives from the stack
(gap.air_gap_mm: air clearance, plywood and felt), the piece coil under
the magnet when layout.magnet_above_coil is set, and the plate height
inside the SOT-23 package.

Off-centre pieces (note 25, paragraph 2, point 4): a sensor sees a piece
while the off-axis field of its magnet stays above the presence
threshold, so a sensor covers a disc of offsets around it, of the
detection radius of the weakest piece at the maximum gap. A set of
sensors covers the union of those discs; offset_coverage gives the
half-side of the largest square of offsets, centred on the square,
inside that union, computed exactly from the nearest-sensor distance
(its maximum over a square sits at a corner, where a bisector of two
sensors crosses an edge, or at a circumcentre of three).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.optimize import brentq
from scipy.special import ellipe, ellipk

from .config import BoardConfig, HallSensorCfg, PieceType, resolve_geometry
from .physics import MU0_H_PER_M
from .power import power_budget

_SLICES = 32  # axial discretization of the magnet thickness


def _loop_bz_t(i_a: float, r_m: float, rho_m: np.ndarray, z_m: np.ndarray) -> np.ndarray:
    """Axial field of a circular current loop at radius rho and height z."""
    sum_sq = (r_m + rho_m) ** 2 + z_m * z_m
    diff_sq = (r_m - rho_m) ** 2 + z_m * z_m
    m = 4.0 * r_m * rho_m / sum_sq
    return (
        MU0_H_PER_M
        * i_a
        / (2.0 * math.pi)
        / np.sqrt(sum_sq)
        * (ellipk(m) + (r_m * r_m - rho_m * rho_m - z_m * z_m) / diff_sq * ellipe(m))
    )


def disc_bz_mT(
    br_T: float, r_mm: float, t_mm: float, z_mm: float, rho_mm: float = 0.0
) -> float:
    """Axial field of a disc magnet, z_mm from its near face, rho_mm off axis."""
    if min(br_T, r_mm, t_mm) <= 0.0 or z_mm <= 0.0 or rho_mm < 0.0:
        raise ValueError("need positive Br, radius, thickness and z, non-negative rho")
    k_a_per_m = br_T / MU0_H_PER_M
    slice_m = t_mm * 1e-3 / _SLICES
    depths_m = (np.arange(_SLICES) + 0.5) * slice_m
    z_m = z_mm * 1e-3 + depths_m
    bz = _loop_bz_t(k_a_per_m * slice_m, r_mm * 1e-3, np.full_like(z_m, rho_mm * 1e-3), z_m)
    return float(np.sum(bz)) * 1e3


def disc_bz_axis_mT(br_T: float, r_mm: float, t_mm: float, z_mm: float) -> float:
    """Closed form on the axis, the reference for the stacked loops."""
    if min(br_T, r_mm, t_mm) <= 0.0 or z_mm <= 0.0:
        raise ValueError("need positive Br, radius, thickness and z")
    r2 = r_mm * r_mm
    far = (z_mm + t_mm) / math.sqrt(r2 + (z_mm + t_mm) ** 2)
    near = z_mm / math.sqrt(r2 + z_mm * z_mm)
    return br_T / 2.0 * (far - near) * 1e3


def sensor_gap_mm(cfg: BoardConfig, extra_mm: float = 0.0) -> float:
    """Magnet face to Hall plate at the nominal stack, plus any extra lift."""
    lay = cfg.hall_rfid.layout
    z = cfg.gap.air_gap_mm - lay.die_height_mm + extra_mm
    if lay.magnet_above_coil:
        z += cfg.resonator.coil.height_mm
    return z


def magnet_thickness_mm(cfg: BoardConfig, piece: PieceType, size_coded: bool) -> float:
    t = cfg.piece_magnet.thickness_mm
    if size_coded:
        t += cfg.hall_rfid.size_coding.thickness_extra_mm.get(piece, 0.0)
    return t


def piece_bz_mT(
    cfg: BoardConfig,
    piece: PieceType,
    pitch_mm: float,
    z_mm: float,
    rho_mm: float = 0.0,
    size_coded: bool = False,
) -> float:
    geo = resolve_geometry(cfg, pitch_mm)
    r = geo.classes[piece].magnet_d_mm / 2.0
    t = magnet_thickness_mm(cfg, piece, size_coded)
    return disc_bz_mT(cfg.piece_magnet.br_T, r, t, z_mm, rho_mm)


def adc_lsb_mv(cfg: BoardConfig) -> float:
    esp = cfg.hall_rfid.esp32
    return esp.adc_full_scale_mv / float(2**esp.adc_bits)


def sensor_index(cfg: BoardConfig, sensor: int | str) -> int:
    """Index in hall_rfid.sensors of a sensor given by index or part name."""
    sensors = cfg.hall_rfid.sensors
    if isinstance(sensor, int):
        if not 0 <= sensor < len(sensors):
            raise IndexError(sensor)
        return sensor
    parts = [s.part for s in sensors]
    if sensor not in parts:
        raise KeyError(sensor)
    return parts.index(sensor)


@dataclass(frozen=True)
class PieceField:
    piece: PieceType
    magnet_d_mm: float
    magnet_t_mm: float
    b_nominal_mT: float      # nominal stack
    b_max_gap_mT: float      # maximum stack (gap.max_total_mm)
    b_pressed_mT: float      # nominal minus the tilt budget: the strongest present reading
    b_lifted_mT: float       # raised by lift_detect_mm from the nominal stack
    b_neighbor_mT: float     # the same piece on the adjacent square, read by this sensor
    out_nominal_mv: float    # sensor output swing at the nominal stack
    out_nominal_lsb: float   # the same in ADC counts


@dataclass(frozen=True)
class HallBudget:
    pitch_mm: float
    sensor: HallSensorCfg
    z_nominal_mm: float
    z_max_mm: float
    fields: dict[PieceType, PieceField]
    weakest_present_mT: float    # pawn at the maximum stack
    strongest_present_mT: float  # king pressed down
    strongest_lifted_mT: float
    neighbors_sum_mT: float      # worst additive interference of the surrounding pieces
    threshold_mT: float
    release_mT: float
    lift_margin: float           # release level over the strongest lifted field
    crosstalk_db: float          # neighbors sum over the weakest present field
    weakest_present_lsb: float
    noise_margin: float          # weakest present swing over the ADC noise
    in_linear_range: bool

    @property
    def ok(self) -> bool:
        return self.lift_margin >= 1.0 and self.in_linear_range


def _neighbor_sum_mT(cfg: BoardConfig, pitch_mm: float, z_mm: float) -> float:
    """Worst additive field of the surrounding pieces: kings on every side
    and diagonal square. Negative in reality (return flux); its magnitude
    is what eats into the threshold margin."""
    n = cfg.hall_rfid.layout.neighbors_worst_case
    side = abs(piece_bz_mT(cfg, PieceType.KING, pitch_mm, z_mm, rho_mm=pitch_mm))
    diag = abs(piece_bz_mT(cfg, PieceType.KING, pitch_mm, z_mm, rho_mm=pitch_mm * math.sqrt(2)))
    sides = min(n, 4)
    diags = max(0, min(n - 4, 4))
    return sides * side + diags * diag


def hall_budget(cfg: BoardConfig, pitch_mm: float, sensor_index: int = 0) -> HallBudget:
    hr = cfg.hall_rfid
    sensor = hr.sensors[sensor_index]
    geo = resolve_geometry(cfg, pitch_mm)
    z_nom = sensor_gap_mm(cfg)
    z_max = sensor_gap_mm(cfg, cfg.gap.max_total_mm - cfg.gap.nominal_total_mm)
    z_pressed = z_nom - hr.layout.tilt_budget_mm
    z_lift = sensor_gap_mm(cfg, hr.layout.lift_detect_mm)
    lsb = adc_lsb_mv(cfg)
    fields: dict[PieceType, PieceField] = {}
    for piece in PieceType:
        b_nom = piece_bz_mT(cfg, piece, pitch_mm, z_nom)
        fields[piece] = PieceField(
            piece=piece,
            magnet_d_mm=geo.classes[piece].magnet_d_mm,
            magnet_t_mm=magnet_thickness_mm(cfg, piece, size_coded=False),
            b_nominal_mT=b_nom,
            b_max_gap_mT=piece_bz_mT(cfg, piece, pitch_mm, z_max),
            b_pressed_mT=piece_bz_mT(cfg, piece, pitch_mm, z_pressed),
            b_lifted_mT=piece_bz_mT(cfg, piece, pitch_mm, z_lift),
            b_neighbor_mT=piece_bz_mT(cfg, piece, pitch_mm, z_nom, rho_mm=pitch_mm),
            out_nominal_mv=b_nom * sensor.sensitivity_mv_per_mt,
            out_nominal_lsb=b_nom * sensor.sensitivity_mv_per_mt / lsb,
        )
    weakest = min(f.b_max_gap_mT for f in fields.values())
    strongest = max(f.b_pressed_mT for f in fields.values())
    lifted = max(f.b_lifted_mT for f in fields.values())
    neighbors = _neighbor_sum_mT(cfg, pitch_mm, z_nom)
    threshold = hr.presence.threshold_fraction * weakest
    release = threshold - hr.presence.hysteresis_fraction * weakest
    lo, hi = sensor.out_range_v
    swing_v = strongest * sensor.sensitivity_mv_per_mt * 1e-3
    in_range = (sensor.quiescent_out_v + swing_v <= hi) and (sensor.quiescent_out_v - swing_v >= lo)
    weakest_lsb = weakest * sensor.sensitivity_mv_per_mt / lsb
    return HallBudget(
        pitch_mm=pitch_mm,
        sensor=sensor,
        z_nominal_mm=z_nom,
        z_max_mm=z_max,
        fields=fields,
        weakest_present_mT=weakest,
        strongest_present_mT=strongest,
        strongest_lifted_mT=lifted,
        neighbors_sum_mT=neighbors,
        threshold_mT=threshold,
        release_mT=release,
        lift_margin=release / lifted,
        crosstalk_db=20.0 * math.log10(neighbors / weakest),
        weakest_present_lsb=weakest_lsb,
        noise_margin=weakest_lsb / hr.esp32.adc_noise_lsb_rms,
        in_linear_range=in_range,
    )


@dataclass(frozen=True)
class AmplitudeClass:
    pieces: tuple[PieceType, ...]
    magnet_d_mm: float
    magnet_t_mm: float
    b_low_mT: float   # maximum stack plus the tilt budget
    b_high_mT: float  # nominal stack minus the tilt budget


@dataclass(frozen=True)
class AmplitudeReport:
    size_coded: bool
    classes: tuple[AmplitudeClass, ...]   # ascending field
    separable_groups: int                 # classes whose field intervals do not overlap
    strongest_mT: float
    in_linear_range: bool


def amplitude_classes(
    cfg: BoardConfig, pitch_mm: float, size_coded: bool = False, sensor_index: int = 0
) -> AmplitudeReport:
    """How many piece classes an amplitude reading could tell apart once
    the gap scatters: each class is a field interval over the gap range
    (nominal minus tilt to maximum plus tilt); adjacent intervals that
    overlap merge into one group. With the uniform magnets of ADR 0002
    the answer is one group, presence only; size_coded applies the
    thickness extras of the yaml to see what a thicker magnet buys."""
    hr = cfg.hall_rfid
    sensor = hr.sensors[sensor_index]
    geo = resolve_geometry(cfg, pitch_mm)
    tilt = hr.layout.tilt_budget_mm
    z_high = sensor_gap_mm(cfg) - tilt
    z_low = sensor_gap_mm(cfg, cfg.gap.max_total_mm - cfg.gap.nominal_total_mm) + tilt
    by_magnet: dict[tuple[float, float], list[PieceType]] = {}
    for piece in PieceType:
        key = (geo.classes[piece].magnet_d_mm, magnet_thickness_mm(cfg, piece, size_coded))
        by_magnet.setdefault(key, []).append(piece)
    classes = []
    for (d, t), pieces in by_magnet.items():
        r = d / 2.0
        classes.append(
            AmplitudeClass(
                pieces=tuple(pieces),
                magnet_d_mm=d,
                magnet_t_mm=t,
                b_low_mT=disc_bz_mT(cfg.piece_magnet.br_T, r, t, z_low),
                b_high_mT=disc_bz_mT(cfg.piece_magnet.br_T, r, t, z_high),
            )
        )
    classes.sort(key=lambda c: c.b_low_mT)
    groups = 1
    for lower, upper in zip(classes, classes[1:], strict=False):
        if upper.b_low_mT > lower.b_high_mT:
            groups += 1
    strongest = max(c.b_high_mT for c in classes)
    lo, hi = sensor.out_range_v
    swing_v = strongest * sensor.sensitivity_mv_per_mt * 1e-3
    in_range = sensor.quiescent_out_v + swing_v <= hi and sensor.quiescent_out_v - swing_v >= lo
    return AmplitudeReport(
        size_coded=size_coded,
        classes=tuple(classes),
        separable_groups=groups,
        strongest_mT=strongest,
        in_linear_range=in_range,
    )


@dataclass(frozen=True)
class HallPower:
    sensor: HallSensorCfg
    gated: bool
    squares: int
    current_ma: float        # average over a scan
    power_w: float           # at the sensor rail, before regulation loss
    autonomy_h: float        # human vs human, the Hall layer added to the idle budget
    autonomy_without_h: float
    sensors_per_square: int = 1
    sensors: int = 0         # on the whole board
    muxes: int = 0           # hall_rfid.mux parts that read them


def hall_power(
    cfg: BoardConfig, gated: bool, sensor_index: int = 0, sensors_per_square: int = 1
) -> HallPower:
    """Sensor supply over the plateau; sensors_per_square above one is the
    mockup cluster generalized (decision D6 of note 25)."""
    if sensors_per_square < 1:
        raise ValueError("at least one sensor per square")
    hr = cfg.hall_rfid
    sensor = hr.sensors[sensor_index]
    squares = cfg.plateau.grid**2
    sensors = squares * sensors_per_square
    current = sensors * sensor.i_supply_ma
    if gated:
        current /= hr.power_gating.groups
    power = current * 1e-3 * sensor.supply_v
    usable = cfg.power.battery.energy_wh * cfg.power.battery.usable_fraction
    idle = power_budget(cfg, engine_on=False).total_w
    with_hall = idle + power * (1.0 + cfg.power.regulation_loss_pct / 100.0)
    return HallPower(
        sensors_per_square=sensors_per_square,
        sensors=sensors,
        muxes=math.ceil(sensors / hr.mux.channels),
        sensor=sensor,
        gated=gated,
        squares=squares,
        current_ma=current,
        power_w=power,
        autonomy_h=usable / with_hall,
        autonomy_without_h=usable / idle,
    )


@dataclass(frozen=True)
class HallScan:
    gated: bool
    square_us: float         # one square: mux settling plus the averaged samples
    board_ms: float          # the 64 squares, four muxes read in parallel
    rate_hz: float


def hall_scan(cfg: BoardConfig, gated: bool, sensor_index: int = 0) -> HallScan:
    hr = cfg.hall_rfid
    esp = hr.esp32
    square_us = hr.mux.t_settle_us + esp.samples_per_square * esp.adc_sample_us
    per_mux = hr.mux.channels
    if gated:
        groups = hr.power_gating.groups
        board_us = groups * (hr.sensors[sensor_index].power_on_us + per_mux / groups * square_us)
    else:
        board_us = per_mux * square_us
    return HallScan(gated=gated, square_us=square_us, board_ms=board_us * 1e-3,
                    rate_hz=1e6 / board_us)


Point = tuple[float, float]


def detection_radius_mm(
    cfg: BoardConfig, piece: PieceType, pitch_mm: float, z_mm: float, threshold_mT: float
) -> float:
    """Largest offset at which one sensor still reads the piece above the
    threshold; zero when even the centred piece stays below it."""

    def excess(rho_mm: float) -> float:
        return piece_bz_mT(cfg, piece, pitch_mm, z_mm, rho_mm) - threshold_mT

    if excess(0.0) <= 0.0:
        return 0.0
    if excess(pitch_mm) >= 0.0:
        raise ValueError("the threshold is not crossed within one pitch")
    return float(brentq(excess, 0.0, pitch_mm, xtol=1e-9))


def _bisector_crossings(a: Point, b: Point, h: float) -> list[Point]:
    """Where the perpendicular bisector of a and b crosses the four edges
    of the square [-h, h]^2 (the line n . q = c, n = 2 (b - a))."""
    nx, ny = 2.0 * (b[0] - a[0]), 2.0 * (b[1] - a[1])
    c = b[0] ** 2 + b[1] ** 2 - a[0] ** 2 - a[1] ** 2
    out = []
    for edge in (-h, h):
        if ny != 0.0:
            out.append((edge, (c - nx * edge) / ny))
        if nx != 0.0:
            out.append(((c - ny * edge) / nx, edge))
    return out


def _circumcentre(a: Point, b: Point, c: Point) -> Point | None:
    det = 2.0 * ((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1]))
    if det == 0.0:
        return None
    sa, sb, sc = (p[0] ** 2 + p[1] ** 2 for p in (a, b, c))
    ux = ((sb - sa) * (c[1] - a[1]) - (sc - sa) * (b[1] - a[1])) / det
    uy = ((sc - sa) * (b[0] - a[0]) - (sb - sa) * (c[0] - a[0])) / det
    return ux, uy


def farthest_offset_gap_mm(positions: tuple[Point, ...], half_side_mm: float) -> float:
    """Largest distance from a point of the square [-h, h]^2 to its nearest
    sensor. Inside each nearest-sensor cell the distance is convex, so
    the maximum sits at a vertex of a cell clipped by the square: a
    corner, a bisector crossing an edge, or a circumcentre of three
    sensors. Evaluating the true nearest distance at a superset of those
    points inside the square gives the maximum exactly."""
    h = half_side_mm
    pts = tuple(dict.fromkeys(positions))
    if not pts:
        raise ValueError("need at least one sensor position")
    candidates: list[Point] = [(sx * h, sy * h) for sx in (-1.0, 1.0) for sy in (-1.0, 1.0)]
    for i, a in enumerate(pts):
        for j in range(i + 1, len(pts)):
            candidates.extend(_bisector_crossings(a, pts[j], h))
            for k in range(j + 1, len(pts)):
                centre = _circumcentre(a, pts[j], pts[k])
                if centre is not None:
                    candidates.append(centre)
    tol = 1e-9 * max(1.0, h)
    inside = [q for q in candidates if abs(q[0]) <= h + tol and abs(q[1]) <= h + tol]
    return max(min(math.dist(q, s) for s in pts) for q in inside)


def covered_half_side_mm(positions: tuple[Point, ...], radius_mm: float) -> float:
    """Half-side of the largest square of offsets, centred on the square,
    whose every point lies within radius_mm of at least one sensor."""
    if radius_mm <= 0.0 or farthest_offset_gap_mm(positions, 0.0) > radius_mm:
        return 0.0
    lo, hi = 0.0, max(max(abs(x), abs(y)) for x, y in positions) + radius_mm
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if farthest_offset_gap_mm(positions, mid) <= radius_mm:
            lo = mid
        else:
            hi = mid
    return lo


def possible_offset_mm(cfg: BoardConfig, pitch_mm: float) -> float:
    """Largest offset, on either axis, of the smallest base kept on its square."""
    geo = resolve_geometry(cfg, pitch_mm)
    smallest = min(c.base_mm for c in geo.classes.values())
    return (pitch_mm - smallest) / 2.0


@dataclass(frozen=True)
class OffsetCoverage:
    pitch_mm: float
    sensor: HallSensorCfg
    z_mm: float                          # maximum stack, where presence is weakest
    threshold_mT: float
    radius_mm: dict[PieceType, float]    # detection radius of one sensor, per piece
    weakest: PieceType                   # the piece seen over the smallest radius
    detection_radius_mm: float           # that radius, the one the coverage uses
    positions_mm: tuple[Point, ...]      # sensors, from the square centre
    covered_mm: float                    # half-side of the square of offsets covered
    possible_mm: float                   # largest offset of the smallest base on its square
    admissible_mm: float                 # layout.admissible_offset_mm (D14)

    @property
    def ok(self) -> bool:
        return self.covered_mm >= self.admissible_mm


def offset_coverage(
    cfg: BoardConfig,
    pitch_mm: float,
    sensor: int | str = 0,
    positions: tuple[Point, ...] | None = None,
) -> OffsetCoverage:
    """Detection radius of one sensor and the square of piece offsets a set
    of sensors covers (default: one sensor at the centre), compared with
    the admissible offset of a piece set down by hand."""
    idx = sensor_index(cfg, sensor)
    budget = hall_budget(cfg, pitch_mm, idx)
    pos = ((0.0, 0.0),) if positions is None else tuple(positions)
    radii = {
        piece: detection_radius_mm(cfg, piece, pitch_mm, budget.z_max_mm, budget.threshold_mT)
        for piece in PieceType
    }
    weakest = min(radii, key=radii.__getitem__)
    return OffsetCoverage(
        pitch_mm=pitch_mm,
        sensor=budget.sensor,
        z_mm=budget.z_max_mm,
        threshold_mT=budget.threshold_mT,
        radius_mm=radii,
        weakest=weakest,
        detection_radius_mm=radii[weakest],
        positions_mm=pos,
        covered_mm=covered_half_side_mm(pos, radii[weakest]),
        possible_mm=possible_offset_mm(cfg, pitch_mm),
        admissible_mm=cfg.hall_rfid.layout.admissible_offset_mm,
    )


def check(cfg: BoardConfig, pitch_mm: float | None = None) -> list[str]:
    """Design guards of the Hall layer; an empty list means it holds."""
    if pitch_mm is None:
        pitch_mm = cfg.pitch.plateau_mm
    hr = cfg.hall_rfid
    problems = []
    for sensor in hr.sensors:
        if sensor.height_mm >= cfg.gap.air_mm:
            problems.append(f"{sensor.part} taller than the air clearance")
    budget = hall_budget(cfg, pitch_mm)
    if budget.lift_margin < hr.presence.min_lift_margin:
        problems.append("a lifted king still reads as present")
    if budget.crosstalk_db > cfg.measurement.crosstalk_max_db:
        problems.append("surrounding pieces eat the presence threshold")
    if not budget.in_linear_range:
        problems.append("a pressed king saturates the sensor")
    quadrants = (cfg.plateau.grid // cfg.plateau.quadrant.squares) ** 2
    if hr.mux.channels * quadrants < cfg.plateau.grid**2:
        problems.append("one mux per quadrant does not cover the squares")
    if hr.mux.channels % hr.power_gating.groups != 0:
        problems.append("supply groups must divide the squares of a quadrant")
    return problems
