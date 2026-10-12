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
    plateau_mm: float


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
    air_mm: float
    surface_mm: float
    felt_mm: float
    max_total_mm: float

    @property
    def air_gap_mm(self) -> float:
        """Distance from PCB top copper to the underside of the piece coil."""
        return self.air_mm + self.surface_mm + self.felt_mm

    @property
    def nominal_total_mm(self) -> float:
        """The 'entrefer nominal': PCB + air clearance + play surface + felt."""
        return self.pcb_mm + self.air_mm + self.surface_mm + self.felt_mm


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
    mounting: str


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


class LedsCfg(_Model):
    part: str
    fitted: bool  # False: a passive board, no LED placed (the simple pilot)
    per_square: int
    corner_inset_mm: float
    light_hole_d_mm: float
    decoupling_nf: float
    chain_track_mm: float
    ring_track_mm: float
    color_white: tuple[int, int, int]
    color_black: tuple[int, int, int]
    chain_squares: tuple[int, ...]


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
    leds: LedsCfg


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


class BenchConsoleCfg(_Model):
    usart: int
    tx: str
    rx: str


class BenchShieldCfg(_Model):
    board_mm: tuple[float, float]
    layers: int


class BenchCfg(_Model):
    """The Nucleo bench of note 19: NUCLEO=1 build of the brain firmware and
    the bench shield of boardgen."""

    board: str
    console: BenchConsoleCfg
    arduino_pins: dict[str, str]
    signals: dict[str, str]
    shield: BenchShieldCfg

    @model_validator(mode="after")
    def _signals_sit_on_known_connectors(self) -> BenchCfg:
        unknown = [s for s, label in self.signals.items() if label not in self.arduino_pins]
        if unknown:
            raise ValueError(f"bench.signals on unknown Arduino pins: {unknown}")
        return self


class MockupCfg(_Model):
    test_pieces: tuple[TestPieceCfg, ...]
    coil_board: CoilBoardCfg
    analog_board: AnalogBoardCfg
    analog: MockupAnalogCfg
    drive: MockupDriveCfg
    power: MockupPowerCfg
    uart_isolator: IsolatorCfg
    nucleo_pins: dict[str, NucleoPinCfg]


class QuadrantLinkCfg(_Model):
    connector: str
    footprint: str
    pins: int
    pinout: tuple[str, ...]

    @model_validator(mode="after")
    def _pinout_complete(self) -> QuadrantLinkCfg:
        if len(self.pinout) != self.pins:
            raise ValueError("link pinout must name every pin")
        return self


class LedViaCfg(_Model):
    pad_mm: float
    drill_mm: float
    stub_mm: float


class QuadrantRoutingCfg(_Model):
    track_clearance_mm: float
    edge_clearance_mm: float
    route_track_mm: float
    lane_pitch_mm: float
    ring_track_mm: float
    led_via: LedViaCfg
    grid_mm: float

    @model_validator(mode="after")
    def _lane_pitch(self) -> QuadrantRoutingCfg:
        if self.lane_pitch_mm < self.route_track_mm + self.track_clearance_mm - 1e-9:
            raise ValueError("lane pitch must cover track width plus clearance")
        return self


class StripCfg(_Model):
    connector_zone_mm: float
    cell_pitch_mm: float
    middle_zone_mm: float
    lane_x0_mm: float
    cell_entry_x_mm: float


class FrontEndCfg(_Model):
    drive_decoder: str
    damp_decoder: str
    flyback_diode: str
    logic_rail: str


class ReducedQuadrantCfg(_Model):
    squares: int
    strip_overhang_mm: float


class QuadrantCfg(_Model):
    squares: int
    layers: int
    mux: str
    front_end_strip_mm: float
    front_end_max_height_mm: float
    strip_overhang_mm: float
    reduced: ReducedQuadrantCfg
    link: QuadrantLinkCfg
    routing: QuadrantRoutingCfg
    strip: StripCfg
    front_end: FrontEndCfg
    mounting_hole_d_mm: float
    mounting_hole_inset_mm: float


class PlateauLedsCfg(_Model):
    corners: tuple[str, str]

    @field_validator("corners")
    @classmethod
    def _opposite_corners(cls, v: tuple[str, str]) -> tuple[str, str]:
        opposite = {"NW": "SE", "SE": "NW", "NE": "SW", "SW": "NE"}
        if v[0] not in opposite or opposite[v[0]] != v[1]:
            raise ValueError("led corners must be two opposite corners")
        return v


class WoodCfg(_Model):
    border_mm: float


class LocatingPinsCfg(_Model):
    d_mm: float
    count: int


class BaseCfg(_Model):
    shell_mm: float
    electronics_cavity_mm: float
    cell_mm: tuple[float, float, float]
    gantry_cavity_mm: float
    locating_pins: LocatingPinsCfg
    wing_seam_max_mm: float


class CommsCfg(_Model):
    module: str
    pi_header: bool
    isolator: str
    load_switch: bool


class BrainCfg(_Model):
    mcu_board: str
    power_board: str
    motion_board: str
    comms: CommsCfg
    peripheral_port: str
    board_mm: tuple[float, float]
    layers: int
    mcu_pins: dict[str, str]

    @model_validator(mode="after")
    def _pins_unique(self) -> BrainCfg:
        pins = list(self.mcu_pins.values())
        if len(pins) != len(set(pins)):
            dup = sorted({p for p in pins if pins.count(p) > 1})
            raise ValueError(f"MCU pins used twice: {dup}")
        return self


class PlateauCfg(_Model):
    grid: int
    quadrant: QuadrantCfg
    leds: PlateauLedsCfg
    wood: WoodCfg
    module_underside_clear: bool
    base: BaseCfg
    brain: BrainCfg

    @model_validator(mode="after")
    def _quadrants_tile_the_grid(self) -> PlateauCfg:
        if self.grid % self.quadrant.squares != 0:
            raise ValueError("quadrant squares must divide the grid")
        return self


class ClockDisplayCfg(_Model):
    diagonal_in: float
    window_mm: tuple[float, float]
    up_slope_mm: float


class RockerCfg(_Model):
    length_mm: float
    width_mm: float
    thickness_mm: float
    recess_mm: float
    tilt_deg: float
    pivot_d_mm: float
    switch_inset_mm: float


class EncoderCfg(_Model):
    knob_d_mm: float
    x_mm: float
    up_slope_mm: float


class BuzzerGrilleCfg(_Model):
    holes: tuple[int, int]
    pitch_mm: float
    hole_d_mm: float
    origin_mm: tuple[float, float]


class ClockCfg(_Model):
    radio: str
    mcu: str
    cell: str
    body_mm: tuple[float, float]
    height_front_mm: float
    height_rear_mm: float
    slope_end_mm: float
    wall_mm: float
    lid_mm: float
    display: ClockDisplayCfg
    rocker: RockerCfg
    encoder: EncoderCfg
    buzzer_grille: BuzzerGrilleCfg
    usb_c_slot_mm: tuple[float, float]


class ThudCfg(_Model):
    hz: float
    decay_s: float
    noise: float


class SerieCfg(_Model):
    """The films: signature sound (each resonator line, transposed into the
    audible), the set-down thud and how the 3D pieces are drawn."""

    transpose_ratio: float
    decay_s: float
    attack_ms: float
    harmonics: tuple[float, ...]
    note_s: float
    scale_step_s: float
    sample_rate_hz: int
    piece_height_ratio: dict[PieceType, float]
    capacitor_mm: tuple[float, float, float]
    thud: ThudCfg


class HallSensorCfg(_Model):
    part: str
    mpn: str
    lcsc: str | None = None
    package: str
    height_mm: float
    supply_v: float
    sensitivity_mv_per_mt: float
    quiescent_out_v: float
    out_range_v: tuple[float, float]
    i_supply_ma: float
    i_supply_max_ma: float | None = None
    power_on_us: float
    power_on_max_us: float | None = None
    note: str

    @model_validator(mode="after")
    def _quiescent_inside_range(self) -> HallSensorCfg:
        lo, hi = self.out_range_v
        if not lo < self.quiescent_out_v < hi:
            raise ValueError("quiescent output must sit inside the output range")
        if self.sensitivity_mv_per_mt <= 0.0:
            raise ValueError("sensitivity is the magnitude, positive")
        if self.i_supply_max_ma is not None and self.i_supply_max_ma < self.i_supply_ma:
            raise ValueError("maximum supply current below the typical one")
        if self.power_on_max_us is not None and self.power_on_max_us < self.power_on_us:
            raise ValueError("maximum power-on time below the typical one")
        return self


class HallLayoutCfg(_Model):
    die_height_mm: float
    magnet_above_coil: bool
    lift_detect_mm: float
    tilt_budget_mm: float
    neighbors_worst_case: int
    admissible_offset_mm: float


class HallPresenceCfg(_Model):
    threshold_fraction: float
    hysteresis_fraction: float
    min_lift_margin: float
    debounce_scans: int

    @model_validator(mode="after")
    def _fractions(self) -> HallPresenceCfg:
        if not 0.0 < self.hysteresis_fraction < self.threshold_fraction < 1.0:
            raise ValueError("need 0 < hysteresis < threshold < 1, as fractions")
        return self


class HallSizeCodingCfg(_Model):
    thickness_extra_mm: dict[PieceType, float]

    @field_validator("thickness_extra_mm")
    @classmethod
    def _non_negative(cls, v: dict[PieceType, float]) -> dict[PieceType, float]:
        if any(extra < 0.0 for extra in v.values()):
            raise ValueError("extra thickness is additive, never negative")
        return v


class HallMuxCfg(_Model):
    part: str
    mpn: str
    lcsc: str | None = None
    channels: int
    ron_ohm: float
    c_off_pF: float
    c_on_pF: float
    t_settle_us: float


class HallGatingCfg(_Model):
    groups: int
    fet: str

    @field_validator("groups")
    @classmethod
    def _positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("at least one supply group")
        return v


class HallEsp32Cfg(_Model):
    module: str
    devkit: str
    adc_bits: int
    adc_full_scale_mv: float
    adc_noise_lsb_rms: float
    adc_sample_us: float
    samples_per_square: int
    pins: dict[str, int]

    @model_validator(mode="after")
    def _pins_unique(self) -> HallEsp32Cfg:
        gpios = list(self.pins.values())
        if len(gpios) != len(set(gpios)):
            raise ValueError("ESP32 GPIO used twice")
        return self


class NfcAntennaCfg(_Model):
    side_ratio: float
    turns: int
    track_mm: float
    gap_mm: float
    q_target: float


class NfcTagCfg(_Model):
    part: str
    order_key: str
    d_out_mm: float
    d_in_mm: float
    turns: int
    c_in_pF: float
    height_in_base_mm: float


class NfcCfg(_Model):
    f_hz: float
    h_min_a_per_m: float
    h_max_a_per_m: float
    antenna_current_ma_rms: float
    antenna: NfcAntennaCfg
    tag: NfcTagCfg
    reader_candidates: tuple[str, ...]


class MockupBoardOutlineCfg(_Model):
    strip_mm: float
    rail_mm: float
    edge_clearance_mm: float
    fiducial_edge_mm: float
    fiducials: int
    fiducial_d_mm: float
    fiducial_mask_d_mm: float
    hole_d_mm: float
    copper_um: float
    eps_r: float
    standoff_mm: float


class NfcLoopCfg(_Model):
    """A square reader loop, concentric turns, side as a fraction of the pitch."""

    side_ratio: float
    turns: int
    track_mm: float
    gap_mm: float

    @model_validator(mode="after")
    def _sane(self) -> NfcLoopCfg:
        if not 0.0 < self.side_ratio < 1.0:
            raise ValueError("loop side_ratio must be within (0, 1)")
        if self.turns < 1 or min(self.track_mm, self.gap_mm) <= 0.0:
            raise ValueError("need at least one turn and positive track and gap")
        return self


class ReaderPartCfg(_Model):
    maker: str
    mpn: str
    lcsc: str


class MockupReaderCfg(_Model):
    part: str
    package: str
    footprint_square_mm: float
    by_row: dict[int, ReaderPartCfg]
    area_mm2: tuple[float, float]
    r_drive_ohm: float
    i_tvdd_max_ma: float
    i_tvdd_accept_ma: float
    i_idle_ma: float
    i_idle_max_ma: float
    rx_max_vpp: float
    rx_target_vpp: tuple[float, float]
    rx_r2_ohm: float
    r_sense_ohm: float

    @model_validator(mode="after")
    def _limits(self) -> MockupReaderCfg:
        if not self.i_tvdd_accept_ma < self.i_tvdd_max_ma:
            raise ValueError("acceptance current must sit below the datasheet limit")
        if self.i_idle_max_ma < self.i_idle_ma:
            raise ValueError("maximum idle current below the typical one")
        if not 0.0 < self.area_mm2[0] <= self.area_mm2[1]:
            raise ValueError("reader area must be positive, smallest first")
        lo, hi = self.rx_target_vpp
        if not 0.0 < lo < hi < self.rx_max_vpp:
            raise ValueError("RX target must sit inside the RX input limit")
        return self


class MockupMatchingCfg(_Model):
    z_target_ohm: float
    q_loaded: float
    l0_nH: float
    c0_pF: float
    l0_q: float
    cap_esr_ohm: float
    cap_series: str
    cap_tol_pct: float
    rq_series: str
    rx_coupling_nF: float
    loop_lead_mm: float
    tune_tag: str
    gamma_max: float


class MockupHallCfg(_Model):
    sensor: str
    alternate: str
    cluster_square: str
    cluster_offset_ratio: float
    filter_r_ohm: float
    filter_c_nF: float
    decoupling_nF: float
    land_mm: float
    settle_lsb: float
    trio_pitch_mm: float


class MockupMuxChannelsCfg(_Model):
    centre: tuple[int, ...]
    cluster: tuple[int, ...]
    ground: int
    rail_half: int
    led_step: int
    extension: tuple[int, ...]

    def all_channels(self) -> list[int]:
        fixed = [self.ground, self.rail_half, self.led_step]
        return [*self.centre, *self.cluster, *fixed, *self.extension]


class MockupEsp32Cfg(_Model):
    module: str
    lcsc: str
    module_gpios: tuple[int, ...]
    adc1_gpios: tuple[int, ...]
    strapping_gpios: tuple[int, ...]
    usb_gpios: tuple[int, ...]
    psram_gpios: tuple[int, ...]
    analog_signals: tuple[str, ...]
    usb_signals: tuple[str, ...]
    pins: dict[str, int]


class MockupRegulatorCfg(_Model):
    part: str
    lcsc: str
    v_out: float
    i_max_a: float
    dropout_v: float
    i_ground_ma: float


class HallRfidPowerCfg(_Model):
    """The 3.3 V rail of the Hall plus RFID board: its input, the module
    current and the linear regulator with its thermal path."""

    v_in: tuple[float, float]
    v_in_min: float
    esp32_ma: float
    regulator: MockupRegulatorCfg
    theta_ja_c_per_w: float
    t_junction_max_c: float
    t_ambient_c: float

    @model_validator(mode="after")
    def _headroom(self) -> HallRfidPowerCfg:
        lo, hi = self.v_in
        if not self.regulator.v_out < self.v_in_min <= lo <= hi:
            raise ValueError("regulator input must sit above its output: minimum, nominal, maximum")
        if not self.t_ambient_c < self.t_junction_max_c:
            raise ValueError("ambient above the junction limit")
        return self


class TagChipCfg(_Model):
    part: str
    mpn: str
    lcsc: str
    c_in_pF: float


class TagChipAlternateCfg(_Model):
    mpn: str
    lcsc: str


class MockupTagsCfg(_Model):
    sizes: dict[str, PieceType]
    wall_mm: float
    fit_mm: float
    edge_mm: float
    board_mm: float
    layers: int
    track_options_mm: tuple[float, ...]
    opening_min_ratio: float
    f_self_mhz: tuple[float, float]
    chip: TagChipCfg
    chip_alternate: TagChipAlternateCfg
    chip_r_ohm: float
    ferrite_chi: float
    chip_height_mm: float
    tape_mm: float
    trims_pF: dict[str, tuple[float, ...]]
    activation_margin_min: float
    per_panel: int
    murata_per_panel: int

    @model_validator(mode="after")
    def _consistent(self) -> MockupTagsCfg:
        if set(self.trims_pF) != set(self.sizes):
            raise ValueError("every tag size needs its list of trims")
        lo, hi = self.f_self_mhz
        if not 0.0 < lo < hi:
            raise ValueError("tag tuning window must be increasing")
        if not self.track_options_mm or any(w <= 0.0 for w in self.track_options_mm):
            raise ValueError("name at least one positive tag track width")
        if not 0.0 <= self.opening_min_ratio < 1.0:
            raise ValueError("tag opening ratio must be within [0, 1)")
        return self


class MockupPickupCfg(_Model):
    """The field tag of the tag panel: a small untuned coil and a detector."""

    d_mm: float
    turns: int
    layers: int
    track_mm: float

    @model_validator(mode="after")
    def _sane(self) -> MockupPickupCfg:
        if self.layers < 1 or self.turns < self.layers or self.turns % self.layers:
            raise ValueError("pickup turns must spread evenly over its layers")
        if not 0.0 < 2.0 * (2 * self.turns // self.layers - 1) * self.track_mm < self.d_mm:
            raise ValueError("pickup turns do not fit its diameter")
        return self


class MockupMagnetsCfg(_Model):
    material: str
    diameters_mm: tuple[float, ...]
    thickness_mm: float


class MockupPrintsCfg(_Model):
    pieces: dict[PieceType, int]
    spare_pieces: int
    shims_mm: tuple[float, ...]
    shim_side_mm: float
    lift_max_mm: float
    lift_step_mm: float
    offset_max_mm: float
    offset_step_mm: float
    eject_hole_mm: float


class MockupQuantitiesCfg(_Model):
    boards: int
    boards_assembled: int
    tag_panels: int
    tag_panels_assembled: int


class MockupCriteriaCfg(_Model):
    """Bench numbers and acceptance of M12 to M14 that no other key holds
    (measurements/protocol.md); measurements/analysis.py reads them."""

    bringup_supply_limit_ma: tuple[float, float]
    nxp_version_reg: tuple[int, ...]
    confidence: float
    hall_samples: int
    scale_factor_range: tuple[float, float]
    residual_max_pct: float
    radius_resolution_mm: float
    neighbor_field_tol_mT: float
    power_on_sweep_factor: float
    path_settle_us: float
    path_offset_max_lsb: float
    loop_l_tol_pct: float
    read_trials: int
    read_trials_confirm: int
    read_target_rate: float
    tx_pullup_ohm: float
    mux_emulation_rq_ohm: float
    mux_emulation_c_pF: float
    mux_emulation_i_tvdd_max_ma: float
    read_time_max_ms: float
    move_time_max_ms: float
    tag_drift_max_pct: float
    disturber_distances_mm: tuple[float, ...]

    @model_validator(mode="after")
    def _sane(self) -> MockupCriteriaCfg:
        lo, hi = self.scale_factor_range
        if not 0.0 < lo < 1.0 < hi:
            raise ValueError("the scale factor window must bracket 1")
        if not 0.0 < self.confidence < 1.0 or not 0.0 < self.read_target_rate <= 1.0:
            raise ValueError("confidence and read target are fractions")
        if not 0 < self.read_trials <= self.read_trials_confirm:
            raise ValueError("a confirmation series is at least a plain one")
        d = self.disturber_distances_mm
        if not d or d[0] <= 0.0 or any(b <= a for a, b in zip(d, d[1:], strict=False)):
            raise ValueError("disturber distances must be positive and increasing")
        if self.read_time_max_ms > self.move_time_max_ms:
            raise ValueError("a move includes at least one square read")
        return self


class HallRfidMockupCfg(_Model):
    """The Hall plus RFID test board of note 25: 2 x 2 squares, loops by
    column, readers by row."""

    columns: tuple[str, ...]
    rows: tuple[int, ...]
    board: MockupBoardOutlineCfg
    ground_keepout_mm: float
    ground_keepout_min_mm: float
    loops: dict[str, NfcLoopCfg]
    loop_by_column: dict[str, str]
    reader: MockupReaderCfg
    matching: MockupMatchingCfg
    hall: MockupHallCfg
    mux_channels: MockupMuxChannelsCfg
    esp32: MockupEsp32Cfg
    power: HallRfidPowerCfg
    play_area_heights_mm: dict[str, float]
    tags: MockupTagsCfg
    pickup: MockupPickupCfg
    magnets: MockupMagnetsCfg
    prints: MockupPrintsCfg
    quantities: MockupQuantitiesCfg
    criteria: MockupCriteriaCfg

    @model_validator(mode="after")
    def _references(self) -> HallRfidMockupCfg:
        if set(self.loop_by_column) != set(self.columns):
            raise ValueError("every column needs a loop")
        if not set(self.loop_by_column.values()) <= set(self.loops):
            raise ValueError("loop_by_column names a loop that is not defined")
        if set(self.reader.by_row) != set(self.rows):
            raise ValueError("every row needs a reader part")
        if not 0.0 < self.ground_keepout_min_mm <= self.ground_keepout_mm:
            raise ValueError("the reduced ground keepout must not exceed the nominal one")
        q = self.quantities
        if q.boards_assembled > q.boards or q.tag_panels_assembled > q.tag_panels:
            raise ValueError("more assembled than fabricated")
        return self

    def squares(self) -> list[str]:
        """Square names, row by row from row 1: A1, B1, A2, B2."""
        return [f"{c}{r}" for r in self.rows for c in self.columns]

    def loop_of(self, square: str) -> NfcLoopCfg:
        return self.loops[self.loop_by_column[square[0]]]


class HallRfidCfg(_Model):
    """The Hall plus RFID alternative of note 24: numbers only, no verdict."""

    sensors: tuple[HallSensorCfg, ...]
    layout: HallLayoutCfg
    presence: HallPresenceCfg
    color_by_polarity: bool
    size_coding: HallSizeCodingCfg
    mux: HallMuxCfg
    power_gating: HallGatingCfg
    esp32: HallEsp32Cfg
    nfc: NfcCfg
    mockup: HallRfidMockupCfg

    @model_validator(mode="after")
    def _at_least_one_sensor(self) -> HallRfidCfg:
        if not self.sensors:
            raise ValueError("name at least one Hall sensor candidate")
        parts = {s.part for s in self.sensors}
        if not {self.mockup.hall.sensor, self.mockup.hall.alternate} <= parts:
            raise ValueError("the mockup sensor and its alternate must be listed in sensors")
        return self

    def sensor(self, part: str) -> HallSensorCfg:
        """The sensor of that part name."""
        for s in self.sensors:
            if s.part == part:
                return s
        raise KeyError(part)


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
    bench: BenchCfg
    mockup: MockupCfg
    plateau: PlateauCfg
    clock: ClockCfg
    serie: SerieCfg
    hall_rfid: HallRfidCfg


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
