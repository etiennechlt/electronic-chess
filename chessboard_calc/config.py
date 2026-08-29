"""Typed loading and validation of config/board.yaml, the single source of truth.

This module stays free of any physics: it only mirrors the YAML schema,
validates it, and resolves the purely linear geometry (diameters, travels,
gaps) for a given pitch. Everything electromagnetic lives in the sibling
modules, which all take a BoardConfig as input.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "board.yaml"


class PieceType(enum.StrEnum):
    PAWN = "pawn"
    KNIGHT = "knight"
    BISHOP = "bishop"
    ROOK = "rook"
    QUEEN = "queen"
    KING = "king"


class Color(enum.StrEnum):
    WHITE = "white"
    BLACK = "black"


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PieceClassSpec(_Model):
    base_ratio: float
    cap_nF: dict[Color, float]

    @field_validator("base_ratio")
    @classmethod
    def _ratio_in_range(cls, v: float) -> float:
        if not 0.0 < v < 1.0:
            raise ValueError("base_ratio must be within (0, 1)")
        return v

    @model_validator(mode="after")
    def _both_colors(self) -> PieceClassSpec:
        if set(self.cap_nF) != {Color.WHITE, Color.BLACK}:
            raise ValueError("cap_nF must define exactly white and black")
        if any(c <= 0 for c in self.cap_nF.values()):
            raise ValueError("capacitances must be positive")
        return self


class PitchCfg(_Model):
    candidates_mm: tuple[float, ...]
    mockup_mm: float


class PiecesCfg(_Model):
    classes: dict[PieceType, PieceClassSpec]
    spare_queens_per_side: int
    mass_g: tuple[float, float]

    @model_validator(mode="after")
    def _complete_and_unique(self) -> PiecesCfg:
        if set(self.classes) != set(PieceType):
            raise ValueError("classes must define all six piece types")
        caps = [c for spec in self.classes.values() for c in spec.cap_nF.values()]
        if len(set(caps)) != len(caps):
            raise ValueError("the twelve capacitor values must be unique")
        return self


class CorridorCfg(_Model):
    tolerance_budget_mm: float


class ResonatorCoilCfg(_Model):
    outer_margin_mm: float
    inner_ratio: float
    height_mm: float
    wire_candidates_mm: tuple[float, ...]
    insulation_extra_mm: float
    fill_factor: float
    proximity_factor: float


class ResonatorCfg(_Model):
    L_target_uH: float
    L_tol_pct: float
    C_tol_pct: float
    q_nominal: float
    q_min_with_magnet: float
    min_separation_widths: float
    min_tolerance_gap_khz: float
    coil: ResonatorCoilCfg


class PieceMagnetCfg(_Model):
    material: str
    br_T: float
    outer_margin_mm: float
    thickness_mm: float


class GapCfg(_Model):
    pcb_mm: float
    surface_mm: float
    felt_mm: float
    max_total_mm: float

    @property
    def air_gap_mm(self) -> float:
        """Distance from PCB top copper to the underside of the piece coil."""
        return self.surface_mm + self.felt_mm

    @property
    def nominal_total_mm(self) -> float:
        """The brief's 'entrefer nominal': PCB + play surface + felt."""
        return self.pcb_mm + self.surface_mm + self.felt_mm


class SenseCoilCfg(_Model):
    outer_ratio: float
    inner_ratio: float
    layers: int
    L_target_uH: float
    track_gap_mm: float
    via_drill_mm: float
    copper_um: float


class MuxCfg(_Model):
    part: str
    ron_ohm: float
    c_off_pF: float
    idle_coil_policy: str


class DriveCfg(_Model):
    v: float
    pulse_us: float
    current_limit_a: float
    excitation_efficiency: float


class MeasurementCfg(_Model):
    band_hz: tuple[float, float]
    blanking_us: float
    window_us: float
    adc_sps: float
    fft_points: int
    coherent_avg: int
    idle_scan_hz: float
    preamp_gain: tuple[float, float]
    bandpass_order: int
    crosstalk_max_db: float
    snr_min_db: float
    preamp_noise_nv_rthz: float
    drive: DriveCfg


class GantryDriverCfg(_Model):
    part: str
    mode: str
    disable_at_idle: bool


class GantryPerPitchCfg(_Model):
    motor: str
    guide: str


class GantryCfg(_Model):
    kinematics: str
    capture_band_ratio: float
    y_margin_mm: float
    speed_mm_s: tuple[float, float]
    accel_mm_s2: tuple[float, float]
    settle_ms: float
    driver: GantryDriverCfg
    per_pitch: dict[int, GantryPerPitchCfg]
    homing: str


class CarriageMagnetCfg(_Model):
    material: str
    d_mm: float
    h_mm: float


class CarriageCfg(_Model):
    magnet: CarriageMagnetCfg
    engage_gap_mm: float
    retract_gap_mm: float
    actuator_candidates: tuple[str, ...]


class FrictionCfg(_Model):
    mu_felt_acrylic: float
    lateral_fraction: tuple[float, float]


class BatteryCfg(_Model):
    layout: str
    cell: str
    energy_wh: float
    usable_fraction: float
    v_range: tuple[float, float]
    ntc_on_pack: bool


class Buck5vCfg(_Model):
    f_sw_mhz: float
    forced_pwm: bool
    spread_spectrum: bool
    candidates: tuple[str, ...]


class LoadsCfg(_Model):
    stm32_analog: float
    pi: float
    tft: float
    motors_avg: float
    motors_peak: float
    ui_idle: float


class PiLinkCfg(_Model):
    isolator: str
    load_switch: bool


class PowerCfg(_Model):
    battery: BatteryCfg
    buck_5v: Buck5vCfg
    loads_w: LoadsCfg
    fixed_overhead_w: float
    regulation_loss_pct: float
    move_reserve_pct: float
    pi_link: PiLinkCfg


class McuCfg(_Model):
    part: str
    sysclk_mhz: float


class TestPieceCfg(_Model):
    piece: PieceType
    color: Color


class MagnetMountCfg(_Model):
    square: tuple[int, int]
    hole_spacing_mm: float
    hole_d_mm: float


class JointCfg(_Model):
    pins: int
    pitch_mm: float
    pad_d_mm: float
    drill_mm: float


class CoilBoardCfg(_Model):
    size_mm: tuple[float, float]
    layers: int
    coil_grid: int
    track_clearance_mm: float
    edge_clearance_mm: float
    mounting_hole_d_mm: float
    mounting_hole_inset_mm: float
    magnet_mount: MagnetMountCfg
    joint: JointCfg
    route_track_mm: float


class AnalogBoardCfg(_Model):
    size_mm: tuple[float, float]
    layers: int
    format: str


class AnalogMuxCfg(_Model):
    part: str
    ron_ohm: float
    note: str


class InaCfg(_Model):
    part: str
    gain: float
    rg_ohm: float


class FilterCfg(_Model):
    hp_hz: float
    lp_hz: float
    q: float
    output_gain: float
    opamp: str


class AdcRcCfg(_Model):
    r_ohm: float
    c_nF: float


class MockupAnalogCfg(_Model):
    vref_v: float
    mux: AnalogMuxCfg
    clamp_r_ohm: float
    bleed_r_ohm: float
    ina: InaCfg
    input_ac_nF: float
    input_bias_r_ohm: float
    filter: FilterCfg
    adc_rc: AdcRcCfg


class MockupDriveCfg(_Model):
    rail_fet: str
    rail_r_ohm: float
    bus_diode: str
    coil_fet: str
    clamp_diode: str
    damp_fet: str
    damp_r_ohm: float


class MockupInputCfg(_Model):
    v_nom: float
    jack: str
    tvs: str
    reverse_diode: str


class MockupBuckCfg(_Model):
    part: str
    f_sw_mhz: float
    l_uH: float
    vout: float
    forced_pwm: bool


class MockupLdoCfg(_Model):
    part: str
    vout: float


class PiHeaderCfg(_Model):
    pins: int
    rail: str


class MockupPowerCfg(_Model):
    input: MockupInputCfg
    buck: MockupBuckCfg
    ldo: MockupLdoCfg
    analog_source_jumper: tuple[str, str]
    pi_header: PiHeaderCfg


class IsolatorCfg(_Model):
    part: str
    bypass_jumpers: bool


class NucleoPinCfg(_Model):
    arduino: str
    mcu: str


class MockupCfg(_Model):
    test_pieces: tuple[TestPieceCfg, ...]
    coil_board: CoilBoardCfg
    analog_board: AnalogBoardCfg
    analog: MockupAnalogCfg
    drive: MockupDriveCfg
    power: MockupPowerCfg
    uart_isolator: IsolatorCfg
    nucleo_pins: dict[str, NucleoPinCfg]


class BoardConfig(_Model):
    schema_version: int
    pitch: PitchCfg
    pieces: PiecesCfg
    corridor: CorridorCfg
    resonator: ResonatorCfg
    piece_magnet: PieceMagnetCfg
    gap: GapCfg
    sense_coil: SenseCoilCfg
    mux: MuxCfg
    measurement: MeasurementCfg
    gantry: GantryCfg
    carriage: CarriageCfg
    friction: FrictionCfg
    power: PowerCfg
    mcu: McuCfg
    mockup: MockupCfg


@dataclass(frozen=True)
class ClassGeometry:
    piece: PieceType
    base_mm: float
    coil_d_out_mm: float
    coil_d_in_mm: float
    magnet_d_mm: float


@dataclass(frozen=True)
class ResolvedGeometry:
    pitch_mm: float
    classes: dict[PieceType, ClassGeometry]
    sense_d_out_mm: float
    sense_d_in_mm: float
    play_area_mm: float
    x_travel_mm: float
    y_travel_mm: float
    air_gap_mm: float
    gap_nominal_mm: float
    gap_max_mm: float


def load_config(path: Path | str = DEFAULT_CONFIG_PATH) -> BoardConfig:
    with open(path, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    return BoardConfig.model_validate(raw)


def base_diameter_mm(cfg: BoardConfig, piece: PieceType, pitch_mm: float) -> float:
    return cfg.pieces.classes[piece].base_ratio * pitch_mm


def resolve_geometry(cfg: BoardConfig, pitch_mm: float) -> ResolvedGeometry:
    classes: dict[PieceType, ClassGeometry] = {}
    for piece, spec in cfg.pieces.classes.items():
        base = spec.base_ratio * pitch_mm
        d_out = base - cfg.resonator.coil.outer_margin_mm
        classes[piece] = ClassGeometry(
            piece=piece,
            base_mm=base,
            coil_d_out_mm=d_out,
            coil_d_in_mm=cfg.resonator.coil.inner_ratio * d_out,
            magnet_d_mm=base - cfg.piece_magnet.outer_margin_mm,
        )
    play = 8.0 * pitch_mm
    return ResolvedGeometry(
        pitch_mm=pitch_mm,
        classes=classes,
        sense_d_out_mm=cfg.sense_coil.outer_ratio * pitch_mm,
        sense_d_in_mm=cfg.sense_coil.inner_ratio * pitch_mm,
        play_area_mm=play,
        x_travel_mm=play + 2.0 * cfg.gantry.capture_band_ratio * pitch_mm,
        y_travel_mm=play + cfg.gantry.y_margin_mm,
        air_gap_mm=cfg.gap.air_gap_mm,
        gap_nominal_mm=cfg.gap.nominal_total_mm,
        gap_max_mm=cfg.gap.max_total_mm,
    )
