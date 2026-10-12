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
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
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


def hall_power(cfg: BoardConfig, gated: bool, sensor_index: int = 0) -> HallPower:
    hr = cfg.hall_rfid
    sensor = hr.sensors[sensor_index]
    squares = cfg.plateau.grid**2
    current = squares * sensor.i_supply_ma
    if gated:
        current /= hr.power_gating.groups
    power = current * 1e-3 * sensor.supply_v
    usable = cfg.power.battery.energy_wh * cfg.power.battery.usable_fraction
    idle = power_budget(cfg, engine_on=False).total_w
    with_hall = idle + power * (1.0 + cfg.power.regulation_loss_pct / 100.0)
    return HallPower(
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
