"""Analysis functions for the mockup measurement campaign.

The notebook is a thin presentation layer over these functions, which
are unit-tested against synthetic data (tests/test_analysis.py).

M1 to M11 (LC mockup): CSV formats are the firmware's, scan lines
`sq,fa_hz,fb_hz,amp_mv,snr_db10` and raw dumps of 512 ADC samples (one
value per line, with `# fs_hz=` in the header).

M12 to M14 (Hall + RFID mockup, note 25): one CSV per template of
measurements/data/templates/, a header naming the columns of the row
dataclasses below, comment lines starting with `#`; NanoVNA sweeps as
Touchstone files. Every threshold and design number comes from
config/board.yaml through mockup_criteria() and hall_scale(), or is a
function argument; the criteria of note 25 that the yaml does not hold
are arguments, named in measurements/protocol.md.
"""

from __future__ import annotations

import csv
import dataclasses
import functools
import math
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.stats import beta

from chessboard_calc.config import BoardConfig, load_config
from chessboard_calc.hall import adc_lsb_mv, disc_bz_mT, hall_budget, sensor_gap_mm


@dataclass(frozen=True)
class ScanRow:
    sq: int
    fa_hz: float
    fb_hz: float
    amp_mv: float
    snr_db: float


def load_scan_csv(path: Path) -> list[ScanRow]:
    rows = []
    with open(path, encoding="utf-8") as fh:
        for rec in csv.reader(fh):
            if not rec or rec[0].startswith("#"):
                continue
            rows.append(ScanRow(int(rec[0]), float(rec[1]), float(rec[2]),
                                float(rec[3]), float(rec[4]) / 10.0))
    return rows


def load_raw_csv(path: Path) -> tuple[np.ndarray, float]:
    fs = 3_780_000.0
    samples = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line.startswith("#"):
                if "fs_hz=" in line:
                    fs = float(line.split("fs_hz=")[1].split()[0])
                continue
            if line:
                samples.append(float(line))
    return np.asarray(samples), fs


def q_from_ringdown(samples: np.ndarray, fs_hz: float) -> tuple[float, float]:
    """(f0, Q) by FFT peak plus log-decrement of the analytic envelope."""
    x = samples - samples.mean()
    n = len(x)
    win = np.hanning(n)
    spec = np.abs(np.fft.rfft(x * win))
    k = int(np.argmax(spec[2:]) + 2)
    f0 = k * fs_hz / n

    # Analytic envelope through the Hilbert transform (via FFT).
    full = np.fft.fft(x)
    h = np.zeros(n)
    h[0] = 1.0
    if n % 2 == 0:
        h[n // 2] = 1.0
        h[1:n // 2] = 2.0
    else:
        h[1:(n + 1) // 2] = 2.0
    env = np.abs(np.fft.ifft(full * h))

    # Fit ln(env) over the usable stretch (10 % to 70 % of the record,
    # clear of edge effects and of the noise floor).
    t = np.arange(n) / fs_hz
    lo, hi = int(0.1 * n), int(0.7 * n)
    seg = env[lo:hi]
    good = seg > (env.max() * 0.05)
    if good.sum() < 16:
        return f0, float("nan")
    slope = np.polyfit(t[lo:hi][good], np.log(seg[good]), 1)[0]
    if slope >= 0:
        return f0, float("inf")
    tau = -1.0 / slope
    return f0, math.pi * f0 * tau


def q_from_spectrum(samples: np.ndarray, fs_hz: float) -> tuple[float, float]:
    """(f0, Q lower bound) from the -3 dB width of the resonance line.

    With 512 samples the bin width (about 7.4 kHz) exceeds the true
    linewidth of any Q above ~15, so this only lower-bounds Q; the
    envelope log-decrement (q_from_ringdown) is the reference.
    """
    x = (samples - samples.mean()) * np.hanning(len(samples))
    spec = np.abs(np.fft.rfft(x))
    freqs = np.fft.rfftfreq(len(x), 1.0 / fs_hz)
    k = int(np.argmax(spec[2:]) + 2)
    peak = spec[k]
    half = peak / math.sqrt(2.0)
    left = k
    while left > 0 and spec[left] > half:
        left -= 1
    right = k
    while right < len(spec) - 1 and spec[right] > half:
        right += 1
    width = freqs[right] - freqs[left]
    if width <= 0:
        return freqs[k], float("inf")
    return float(freqs[k]), float(freqs[k] / width)


def crosstalk_db(amp_active_mv: float, amp_neighbor_mv: float) -> float:
    return 20.0 * math.log10(max(amp_neighbor_mv, 1e-9) / max(amp_active_mv, 1e-9))


def dispersion_pct(freqs_hz: list[float]) -> float:
    arr = np.asarray(freqs_hz, dtype=float)
    return float((arr.max() - arr.min()) / arr.mean() * 100.0 / 2.0)


@dataclass(frozen=True)
class AbReport:
    n: int
    n_b_valid: int
    bias_hz: float
    sigma_hz: float


def ab_compare(rows: list[ScanRow]) -> AbReport:
    """Path B against path A on the same ringdowns."""
    pairs = [(r.fa_hz, r.fb_hz) for r in rows if r.fb_hz > 0.0]
    if not pairs:
        return AbReport(n=len(rows), n_b_valid=0, bias_hz=float("nan"),
                        sigma_hz=float("nan"))
    diff = np.asarray([b - a for a, b in pairs])
    return AbReport(n=len(rows), n_b_valid=len(pairs),
                    bias_hz=float(diff.mean()), sigma_hz=float(diff.std()))


def noise_floor_dbfs(samples: np.ndarray) -> float:
    """RMS in-band noise relative to ADC full scale, in dB."""
    x = samples - samples.mean()
    return 20.0 * math.log10(max(x.std(), 1e-9) / 4096.0)


def synth_ringdown(f0_hz: float, q: float, fs_hz: float, n: int = 512,
                   amp: float = 800.0, noise: float = 2.0,
                   seed: int = 0) -> np.ndarray:
    """Synthetic firmware-like capture, for tests and the notebook demo."""
    rng = np.random.default_rng(seed)
    t = np.arange(n) / fs_hz
    tau = q / (math.pi * f0_hz)
    sig = amp * np.exp(-t / tau) * np.sin(2.0 * math.pi * f0_hz * t)
    return 2048.0 + sig + rng.normal(0.0, noise, n)


# ---------------------------------------------------------------------------
# Hall + RFID mockup (note 25): M12 to M14
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MockupCriteria:
    """What the M12 to M14 criteria read from the yaml, at one pitch."""

    pitch_mm: float
    z_nominal_mm: float          # magnet face to Hall plate, nominal stack
    z_max_mm: float              # the same at gap.max_total_mm
    max_gap_shim_mm: float       # shim that turns the nominal stack into the maximum one
    tag_z_nominal_mm: float      # loop copper to tag copper, nominal stack
    lift_detect_mm: float        # M12a residual window and M12c lifted king
    threshold_fraction: float    # of the weakest present field
    hysteresis_fraction: float
    min_lift_margin: float
    neighbors: int
    crosstalk_max_db: float
    adc_noise_lsb_rms: float     # Q4 measures it, Q9 compares the RF shift with it
    admissible_offset_mm: float  # D14, against the M12b coverage
    model_threshold_mT: float    # hall_budget threshold, for comparison with the measured one
    activation_margin_min: float
    h_max_a_per_m: float         # ISO maximum: the service field stays below
    i_tvdd_accept_ma: float      # full conductance only below this
    max_detune_rel: float        # half the loaded bandwidth, 1 / (2 q_loaded)
    # hall_rfid.mockup.criteria, under the same names
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


def mockup_criteria(cfg: BoardConfig, pitch_mm: float | None = None) -> MockupCriteria:
    p = cfg.pitch.mockup_mm if pitch_mm is None else pitch_mm
    hr = cfg.hall_rfid
    mk = hr.mockup
    shim = cfg.gap.max_total_mm - cfg.gap.nominal_total_mm
    return MockupCriteria(
        pitch_mm=p,
        z_nominal_mm=sensor_gap_mm(cfg),
        z_max_mm=sensor_gap_mm(cfg, shim),
        max_gap_shim_mm=shim,
        tag_z_nominal_mm=cfg.gap.air_gap_mm + hr.nfc.tag.height_in_base_mm,
        lift_detect_mm=hr.layout.lift_detect_mm,
        threshold_fraction=hr.presence.threshold_fraction,
        hysteresis_fraction=hr.presence.hysteresis_fraction,
        min_lift_margin=hr.presence.min_lift_margin,
        neighbors=hr.layout.neighbors_worst_case,
        crosstalk_max_db=cfg.measurement.crosstalk_max_db,
        adc_noise_lsb_rms=hr.esp32.adc_noise_lsb_rms,
        admissible_offset_mm=hr.layout.admissible_offset_mm,
        model_threshold_mT=hall_budget(cfg, p).threshold_mT,
        activation_margin_min=mk.tags.activation_margin_min,
        h_max_a_per_m=hr.nfc.h_max_a_per_m,
        i_tvdd_accept_ma=mk.reader.i_tvdd_accept_ma,
        max_detune_rel=0.5 / mk.matching.q_loaded,
        **mk.criteria.model_dump(),
    )


@functools.cache
def _yaml_criteria() -> MockupCriteria:
    """The criteria of config/board.yaml, for the defaults of the functions
    below: an argument left to None takes its value from here."""
    return mockup_criteria(load_config())


def _confidence(confidence: float | None) -> float:
    return _yaml_criteria().confidence if confidence is None else confidence


def _target(target_rate: float | None) -> float:
    return _yaml_criteria().read_target_rate if target_rate is None else target_rate


def cluster_sensor_offsets_mm(
    cfg: BoardConfig, pitch_mm: float | None = None
) -> dict[str, tuple[float, float]]:
    """Sensor names of the cluster square and their position from its centre:
    x along the row (towards column B), y along the column (towards row 2),
    the four extra sensors named by compass quadrant (ne is +x, +y)."""
    p = cfg.pitch.mockup_mm if pitch_mm is None else pitch_mm
    hall = cfg.hall_rfid.mockup.hall
    a = hall.cluster_offset_ratio * p
    sq = hall.cluster_square
    return {
        sq: (0.0, 0.0),
        f"{sq}_ne": (a, a),
        f"{sq}_nw": (-a, a),
        f"{sq}_sw": (-a, -a),
        f"{sq}_se": (a, -a),
    }


# --- Template rows and loaders ----------------------------------------------


@dataclass(frozen=True)
class HallRow:
    """A line of m12_hall.csv: one Hall reading averaged by the firmware."""

    test: str               # m12a, m12b or m12c
    square: str             # square of the sensor
    sensor: str             # A1, B1, A2, B2, or the cluster names (cluster_sensor_offsets_mm)
    path: str               # direct (ADC1 input) or mux
    piece: str              # engraved piece id, "magnet" for a bare magnet, "none"
    magnet_id: str
    magnet_d_mm: float      # caliper
    magnet_t_mm: float
    grade: str              # ferrite grade of the batch
    lift_mm: float          # nominal staircase step or shim stack under the piece
    z_mm: float             # magnet near face to Hall plate, from caliper readings
    x_mm: float             # piece centre from the centre of the sensor's square
    y_mm: float
    n_samples: int
    mean_counts: float
    std_counts: float
    zero_counts: float      # the sensor's zero, square empty
    rail_half_counts: float  # mux channel rail_half (switched row-1 rail, divided) meanwhile


@dataclass(frozen=True)
class ChainRow:
    """A line of m12d_chaine.csv: the Hall read chain."""

    test: str               # power_on, mux_settle, path, current or noise
    square: str
    sensor: str             # sensor read, or ground / rail_half for those mux channels
    path: str               # direct or mux
    channel: int            # mux channel read, -1 on the direct path
    prev_channel: int       # channel selected before the switch, -1 if none
    delay_us: float         # ROW_EN to sample (power_on), switch to sample (mux_settle)
    n_samples: int
    mean_counts: float
    std_counts: float
    i_row_ma: float         # row current, FET off, ammeter across the bypass jumper


@dataclass(frozen=True)
class FlatnessRow:
    """A line of m12_planeite.csv: surface plate height at one point."""

    x_mm: float             # from the centre of the play area
    y_mm: float
    h_mm: float


@dataclass(frozen=True)
class RfidRow:
    """A line of m13_rfid.csv: a series of reads under fixed conditions."""

    test: str               # m13a, m13b, m13c, m13d or m13d_move
    square: str             # square whose reader transmits
    loop: str               # loop name of the yaml, L70x2_mux for the M13c emulation
    reader: str             # maker of the reader chip (by_row of the yaml)
    tag_id: str
    variant: str            # P, P15, P22, G, MURATA or REF (commercial NTAG213)
    tag_square: str         # square the tag sits on
    z_mm: float             # loop copper to the tag's lower copper, caliper
    x_mm: float             # tag centre from the centre of tag_square
    y_mm: float
    neighbor_state: str     # held, txoff, softpd, hardpd or hiz
    cwgsp: int              # CWGsP register value (carrier, p driver)
    cwgsn: int              # CWGsN field of GsNReg (carrier, n driver)
    trials: int
    successes: int          # complete ISO 14443A reads returning the expected UID
    i_tvdd_ma: float        # millivolts across reader.r_sense_ohm over its value
    pickup_mv: float        # field tag reading
    t_read_ms_mean: float
    t_read_ms_max: float


@dataclass(frozen=True)
class TxStateRow:
    """A line of m13b_etats_tx.csv: TX pins of an idle reader."""

    square: str
    reader: str
    version_reg: str        # VersionReg as read, hexadecimal
    state: str              # held, txoff, softpd, hardpd or hiz
    tx1_mv: float           # DC on the TX1 test point
    tx2_mv: float
    tx1_pullup_mv: float    # the same with the test pull-up to the 3.3 V rail
    tx2_pullup_mv: float
    i_tvdd_ma: float


@dataclass(frozen=True)
class PickupRow:
    """A line of m13_vignette.csv: one point of the field tag calibration."""

    pickup_mv: float
    h_a_per_m: float        # field at the tag position
    method: str


@dataclass(frozen=True)
class CohabRow:
    """A line of m14_cohabitation.csv."""

    test: str               # m14a_hall, m14a_tag or m14b
    square: str
    sensor: str             # Hall sensor read (m14a_hall, m14b)
    rf_square: str          # square whose reader transmits meanwhile, "none" if off
    piece: str
    tag_id: str
    variant: str
    magnet_in: int          # 1 magnet in the base, 0 ejected (m14a_tag)
    disturber: str          # none, aluminium, steel or n42 (m14b)
    distance_mm: float      # board bottom face to the disturber
    cwgsp: int
    cwgsn: int
    f_tag_mhz: float        # tag resonance at the NanoVNA probe (m14a_tag)
    f_net_mhz: float        # best-match frequency of the network (m14b)
    i_tvdd_ma: float
    pickup_mv: float
    trials: int
    successes: int
    n_samples: int
    mean_counts: float
    std_counts: float


def _to_float(text: str) -> float:
    text = text.strip()
    return float(text) if text else math.nan


def _to_int(text: str) -> int:
    """Integer cell, decimal or 0x hexadecimal (register values); -1 when empty."""
    text = text.strip()
    if not text:
        return -1
    if text.lower().startswith("0x"):
        return int(text, 16)
    return int(float(text))


_PARSERS: dict[str, Callable[[str], object]] = {
    "float": _to_float,
    "int": _to_int,
    "str": str.strip,
}


def _load_rows(path: Path | str, cls: type) -> list:
    """Rows of a template-shaped CSV. The header must name every field of
    cls (extra columns are ignored); lines starting with # are comments."""
    with open(path, encoding="utf-8", newline="") as fh:
        lines = [ln for ln in fh if ln.strip() and not ln.lstrip().startswith("#")]
    reader = csv.DictReader(lines)
    fields = dataclasses.fields(cls)
    header = reader.fieldnames or []
    missing = [f.name for f in fields if f.name not in header]
    if missing:
        raise ValueError(f"{path}: missing columns {missing}")
    return [
        cls(**{f.name: _PARSERS[f.type](rec.get(f.name) or "") for f in fields})
        for rec in reader
    ]


def load_hall_csv(path: Path | str) -> list[HallRow]:
    return _load_rows(path, HallRow)


def load_chain_csv(path: Path | str) -> list[ChainRow]:
    return _load_rows(path, ChainRow)


def load_flatness_csv(path: Path | str) -> list[FlatnessRow]:
    return _load_rows(path, FlatnessRow)


def load_rfid_csv(path: Path | str) -> list[RfidRow]:
    return _load_rows(path, RfidRow)


def load_tx_state_csv(path: Path | str) -> list[TxStateRow]:
    return _load_rows(path, TxStateRow)


def load_pickup_csv(path: Path | str) -> list[PickupRow]:
    return _load_rows(path, PickupRow)


def load_cohab_csv(path: Path | str) -> list[CohabRow]:
    return _load_rows(path, CohabRow)


def load_touchstone(path: Path | str) -> tuple[np.ndarray, np.ndarray, float]:
    """(freq_hz, s, z0_ohm) of a .s1p or .s2p file as NanoVNA tools save
    it: s has shape (n,) for one port, (n, 2, 2) for two ports. Formats RI,
    MA and DB and units Hz to GHz are read; the defaults are the Touchstone
    ones (GHz, MA, R 50)."""
    units = {"HZ": 1.0, "KHZ": 1e3, "MHZ": 1e6, "GHZ": 1e9}
    unit, fmt, z0 = 1e9, "MA", 50.0
    data = []
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.split("!", 1)[0].strip()
            if not line:
                continue
            if line.startswith("#"):
                tokens = line[1:].upper().split()
                for i, tok in enumerate(tokens):
                    if tok in units:
                        unit = units[tok]
                    elif tok in ("RI", "MA", "DB"):
                        fmt = tok
                    elif tok == "R" and i + 1 < len(tokens):
                        z0 = float(tokens[i + 1])
                continue
            data.append([float(v) for v in line.split()])
    arr = np.asarray(data, dtype=float)
    freq = arr[:, 0] * unit
    pairs = arr[:, 1:].reshape(len(arr), -1, 2)
    a, b = pairs[..., 0], pairs[..., 1]
    if fmt == "RI":
        s = a + 1j * b
    elif fmt == "MA":
        s = a * np.exp(1j * np.deg2rad(b))
    else:
        s = 10.0 ** (a / 20.0) * np.exp(1j * np.deg2rad(b))
    if s.shape[1] == 1:
        return freq, s[:, 0], z0
    if s.shape[1] == 4:
        # Touchstone two-port order is S11 S21 S12 S22
        return freq, s[:, [0, 2, 1, 3]].reshape(-1, 2, 2), z0
    raise ValueError(f"{path}: one or two ports only")


# --- Shared statistics --------------------------------------------------------


def mean_shift(
    mean_a: float, std_a: float, n_a: int, mean_b: float, std_b: float, n_b: int
) -> tuple[float, float]:
    """(b - a, its standard error) between two averaged series."""
    return mean_b - mean_a, math.sqrt(std_a**2 / n_a + std_b**2 / n_b)


def pooled_std(stds: Sequence[float], counts: Sequence[int]) -> float:
    """Standard deviation pooled over series of n samples each."""
    s = np.asarray(stds, dtype=float)
    dof = np.asarray(counts, dtype=float) - 1.0
    return float(math.sqrt(np.sum(dof * s * s) / np.sum(dof)))


def _sorted_unique_mean(x: Sequence[float], y: Sequence[float]) -> tuple[np.ndarray, np.ndarray]:
    """x sorted without repeats, y averaged over the repeats."""
    xs, inv = np.unique(np.round(np.asarray(x, dtype=float), 9), return_inverse=True)
    ys = np.bincount(inv, weights=np.asarray(y, dtype=float)) / np.bincount(inv)
    return xs, ys


# --- M12: the Hall chain ------------------------------------------------------


@dataclass(frozen=True)
class HallScale:
    """Counts to millitesla for one sensor part on the mockup ADC."""

    lsb_mv: float
    sensitivity_mv_per_mt: float
    polarity: float = 1.0   # +1: output rises with a south pole facing the package


def hall_scale(cfg: BoardConfig, part: str | None = None, polarity: float = 1.0) -> HallScale:
    """The mockup sensor (hall_rfid.mockup.hall.sensor) unless a part is named."""
    hr = cfg.hall_rfid
    sensor = hr.sensor(part or hr.mockup.hall.sensor)
    return HallScale(adc_lsb_mv(cfg), sensor.sensitivity_mv_per_mt, polarity)


def counts_to_mT(
    counts: float | np.ndarray,
    zero_counts: float | np.ndarray,
    scale: HallScale,
    rail_counts: float | np.ndarray | None = None,
    rail_ref_counts: float | None = None,
) -> float | np.ndarray:
    """Field from averaged counts. The sensor is ratiometric: when the rail
    reference channel is given, now and when the zero was taken, both the
    zero and the sensitivity follow the rail; the absolute sensitivity at
    the reference rail is what the M12a scale factor absorbs."""
    ratio: float | np.ndarray = 1.0
    if rail_counts is not None and rail_ref_counts is not None:
        r = np.asarray(rail_counts, dtype=float) / rail_ref_counts
        ratio = np.where(np.isfinite(r), r, 1.0)
    out = (
        scale.polarity
        * (np.asarray(counts, dtype=float) - np.asarray(zero_counts, dtype=float) * ratio)
        * scale.lsb_mv
        / (scale.sensitivity_mv_per_mt * ratio)
    )
    return float(out) if np.ndim(out) == 0 else out


def hall_field_mT(row: HallRow, scale: HallScale, rail_ref_counts: float | None = None) -> float:
    return float(counts_to_mT(row.mean_counts, row.zero_counts, scale,
                              row.rail_half_counts, rail_ref_counts))


def model_bz_mT(
    row: HallRow, br_T: float, sensor_xy_mm: tuple[float, float] = (0.0, 0.0)
) -> float:
    """hall.disc_bz_mT for the magnet of the row, as measured, at its z and
    its offset from the sensor."""
    rho = math.hypot(row.x_mm - sensor_xy_mm[0], row.y_mm - sensor_xy_mm[1])
    return disc_bz_mT(br_T, row.magnet_d_mm / 2.0, row.magnet_t_mm, row.z_mm, rho)


@dataclass(frozen=True)
class ScaleFit:
    factor: float           # measured over model, least squares through the origin
    factor_sigma: float     # its standard error
    max_residual: float     # largest |measured / (factor x model) - 1|
    rms_residual: float
    n: int


def m12a_scale_factor(measured_mT: Sequence[float], model_mT: Sequence[float]) -> ScaleFit:
    """One scale factor between measured and modelled fields (it carries
    the real sensitivity and the real remanence), with its spread."""
    m = np.asarray(measured_mT, dtype=float)
    b = np.asarray(model_mT, dtype=float)
    ok = np.isfinite(m) & np.isfinite(b)
    m, b = m[ok], b[ok]
    n = len(m)
    if n == 0:
        raise ValueError("no finite point to fit")
    sbb = float(np.sum(b * b))
    k = float(np.sum(m * b)) / sbb
    resid = m - k * b
    sigma = math.sqrt(float(np.sum(resid * resid)) / (n - 1) / sbb) if n > 1 else math.nan
    rel = m / (k * b) - 1.0
    return ScaleFit(
        factor=k,
        factor_sigma=sigma,
        max_residual=float(np.max(np.abs(rel))),
        rms_residual=float(np.sqrt(np.mean(rel * rel))),
        n=n,
    )


def m12a_fit_rows(
    rows: Iterable[HallRow],
    scale: HallScale,
    br_T: float,
    max_lift_mm: float | None = None,
    rail_ref_counts: float | None = None,
) -> dict[str, ScaleFit]:
    """Scale factor per magnet over the m12a rows (centre sensor, centred
    piece), up to max_lift_mm on the staircase when it is given."""
    groups: dict[str, list[HallRow]] = {}
    for r in rows:
        if r.test != "m12a" or r.piece == "none":
            continue
        if max_lift_mm is not None and r.lift_mm > max_lift_mm + 1e-9:
            continue
        groups.setdefault(r.magnet_id, []).append(r)
    return {
        mid: m12a_scale_factor(
            [hall_field_mT(r, scale, rail_ref_counts) for r in grp],
            [model_bz_mT(r, br_T) for r in grp],
        )
        for mid, grp in groups.items()
    }


def crossing_radius_mm(
    rho_mm: Sequence[float], field_mT: Sequence[float], threshold_mT: float
) -> float:
    """Offset at which the field first falls below the threshold going
    outward, linearly interpolated between the two points around the
    crossing; 0 when the innermost point is already below, inf when no
    point is."""
    rho, f = _sorted_unique_mean(rho_mm, field_mT)
    if f[0] < threshold_mT:
        return 0.0
    below = np.nonzero(f < threshold_mT)[0]
    if below.size == 0:
        return math.inf
    i = int(below[0])
    r0, r1, f0, f1 = rho[i - 1], rho[i], f[i - 1], f[i]
    return float(r0 + (r1 - r0) * (f0 - threshold_mT) / (f0 - f1))


def radii_by_direction(
    x_mm: Sequence[float],
    y_mm: Sequence[float],
    field_mT: Sequence[float],
    threshold_mT: float,
    directions: Iterable[int] | None = None,
) -> dict[int, float]:
    """crossing_radius_mm along each ray from the centre, keyed by its
    direction in whole degrees (0 is +x, 90 is +y, 45 the diagonal); the
    centre point belongs to every ray. On a full grid of offsets most rays
    hold few points: name the directions to keep (the axes and diagonals
    the protocol reads), every direction present otherwise."""
    x = np.asarray(x_mm, dtype=float)
    y = np.asarray(y_mm, dtype=float)
    f = np.asarray(field_mT, dtype=float)
    rho = np.hypot(x, y)
    centre = rho < 1e-9
    ang = np.round(np.degrees(np.arctan2(y, x))).astype(int) % 360
    present = set(ang[~centre].tolist())
    wanted = present if directions is None else {int(d) % 360 for d in directions} & present
    out = {}
    for a in sorted(wanted):
        sel = centre | (ang == a)
        out[int(a)] = crossing_radius_mm(rho[sel], f[sel], threshold_mT)
    return out


def _cheb(p: tuple[float, float]) -> float:
    return max(abs(p[0]), abs(p[1]))


def _inward_neighbour(
    p: tuple[float, float], pts: Iterable[tuple[float, float]]
) -> tuple[float, float] | None:
    """The nearest measured point towards the centre: along x on a column
    of constant y when |x| > |y|, along y when |y| > |x|, along the
    diagonal on a diagonal."""
    x, y = p
    ax, ay = abs(x), abs(y)
    eps = 1e-9
    if ax < eps and ay < eps:
        return None
    if abs(ax - ay) < eps:
        cands = [q for q in pts if abs(abs(q[0]) - abs(q[1])) < eps and abs(q[0]) < ax - eps
                 and q[0] * x >= 0.0 and q[1] * y >= 0.0]
    elif ax > ay:
        cands = [q for q in pts if abs(q[1] - y) < eps and abs(q[0]) < ax - eps and q[0] * x >= 0.0]
    else:
        cands = [q for q in pts if abs(q[0] - x) < eps and abs(q[1]) < ay - eps and q[1] * y >= 0.0]
    return max(cands, key=_cheb) if cands else None


def grid_covered_half_side_mm(
    x_mm: Sequence[float], y_mm: Sequence[float], margin: Sequence[float]
) -> float:
    """Half-side of the largest square of offsets, centred on the square,
    in which every point is detected, from a grid of offsets (any subset of
    quadrants) and the detection margin at each point (best sensor's field
    minus the threshold). Each undetected point bounds it at the crossing,
    interpolated from its inward neighbour; inf when every point is
    detected, 0 when the centre is not."""
    pts = {
        (round(float(a), 6), round(float(b), 6)): float(m)
        for a, b, m in zip(x_mm, y_mm, margin, strict=True)
    }
    bound = math.inf
    for p, m in pts.items():
        if m >= 0.0:
            continue
        n = _inward_neighbour(p, pts)
        if n is None:
            bound = min(bound, _cheb(p))
            continue
        mn = pts[n]
        if mn < 0.0:
            continue  # the neighbour bounds tighter
        t = mn / (mn - m)
        bound = min(bound, _cheb((n[0] + t * (p[0] - n[0]), n[1] + t * (p[1] - n[1]))))
    return bound


def _fields_by_position(
    rows: Iterable[HallRow], scale: HallScale, rail_ref_counts: float | None
) -> dict[str, dict[tuple[float, float], float]]:
    """sensor -> (x, y) -> field, repeats averaged."""
    acc: dict[str, dict[tuple[float, float], list[float]]] = {}
    for r in rows:
        key = (round(r.x_mm, 6), round(r.y_mm, 6))
        acc.setdefault(r.sensor, {}).setdefault(key, []).append(
            hall_field_mT(r, scale, rail_ref_counts))
    return {s: {k: float(np.mean(v)) for k, v in d.items()} for s, d in acc.items()}


def m12b_detection_radius(
    rows: Iterable[HallRow],
    scale: HallScale,
    threshold_mT: float,
    sensor: str,
    rail_ref_counts: float | None = None,
    directions: Iterable[int] | None = None,
) -> dict[int, float]:
    """Detection radius of one sensor per direction (radii_by_direction)
    from the m12b rows of the offset jig, offsets taken from that sensor's
    square centre."""
    fields = _fields_by_position(
        (r for r in rows if r.test == "m12b" and r.sensor == sensor), scale, rail_ref_counts
    ).get(sensor, {})
    if not fields:
        raise ValueError(f"no m12b reading for sensor {sensor}")
    pos = list(fields)
    return radii_by_direction([p[0] for p in pos], [p[1] for p in pos],
                              [fields[p] for p in pos], threshold_mT, directions)


def m12b_cluster_coverage(
    rows: Iterable[HallRow],
    scale: HallScale,
    threshold_mT: float,
    sensors: Iterable[str],
    rail_ref_counts: float | None = None,
) -> float:
    """Covered half-side (grid_covered_half_side_mm) of a set of sensors:
    a piece is seen where at least one of them reads it above the
    threshold. Only offsets where every listed sensor was read count."""
    names = list(sensors)
    fields = _fields_by_position(
        (r for r in rows if r.test == "m12b" and r.sensor in names), scale, rail_ref_counts
    )
    common = set.intersection(*(set(fields.get(s, {})) for s in names))
    if not common:
        raise ValueError("no offset read by every listed sensor")
    pos = sorted(common)
    margin = [max(fields[s][p] for s in names) - threshold_mT for p in pos]
    return grid_covered_half_side_mm([p[0] for p in pos], [p[1] for p in pos], margin)


@dataclass(frozen=True)
class PresenceReport:
    """hall_budget's presence figures, recomputed from measured fields."""

    threshold_mT: float
    release_mT: float
    lift_margin: float      # release over the lifted field
    neighbors_mT: float     # superposed neighbours, magnitudes
    crosstalk_db: float     # neighbours over the weakest present field


def m12c_presence(
    weakest_mT: float,
    lifted_mT: float,
    side_mT: float,
    diag_mT: float,
    threshold_fraction: float,
    hysteresis_fraction: float,
    neighbors: int,
) -> PresenceReport:
    """weakest: pawn at the maximum stack, centred (M12b); lifted: king
    raised by layout.lift_detect_mm (M12a); side and diag: one king on a
    side and on a diagonal square, by difference (M12c). The neighbours
    fill the four sides first, then the four diagonals."""
    threshold = threshold_fraction * weakest_mT
    release = threshold - hysteresis_fraction * weakest_mT
    sides = min(neighbors, 4)
    diags = max(0, min(neighbors - 4, 4))
    total = sides * abs(side_mT) + diags * abs(diag_mT)
    return PresenceReport(
        threshold_mT=threshold,
        release_mT=release,
        lift_margin=release / lifted_mT,
        neighbors_mT=total,
        crosstalk_db=20.0 * math.log10(total / weakest_mT),
    )


def settling_time_us(
    delay_us: Sequence[float],
    counts: Sequence[float],
    tolerance_counts: float,
    final_counts: float | None = None,
) -> float:
    """First delay after which the reading stays within tolerance of its
    final value (the reading at the longest delay unless given),
    interpolated; inf when the last point is still out of tolerance."""
    d, v = _sorted_unique_mean(delay_us, counts)
    final = v[-1] if final_counts is None else final_counts
    err = np.abs(v - final)
    bad = np.nonzero(err > tolerance_counts)[0]
    if bad.size == 0:
        return float(d[0])
    i = int(bad[-1])
    if i == len(d) - 1:
        return math.inf
    t = (err[i] - tolerance_counts) / (err[i] - err[i + 1])
    return float(d[i] + t * (d[i + 1] - d[i]))


@dataclass(frozen=True)
class Flatness:
    pv_mm: float            # peak to valley of the heights
    residual_pv_mm: float   # once the least-squares plane is removed
    slope: float            # of that plane, mm per mm


def flatness(rows: Iterable[FlatnessRow]) -> Flatness:
    pts = list(rows)
    x = np.array([r.x_mm for r in pts])
    y = np.array([r.y_mm for r in pts])
    h = np.array([r.h_mm for r in pts])
    a = np.column_stack([x, y, np.ones_like(x)])
    coef = np.linalg.lstsq(a, h, rcond=None)[0]
    res = h - a @ coef
    return Flatness(pv_mm=float(np.ptp(h)), residual_pv_mm=float(np.ptp(res)),
                    slope=float(math.hypot(coef[0], coef[1])))


# --- M13: the RFID chain ------------------------------------------------------


def binomial_upper_bound(
    events: int, trials: int, confidence: float | None = None
) -> float:
    """One-sided Clopper-Pearson upper bound on the probability of an event
    seen `events` times in `trials` (0 in 100 gives 3 %, 0 in 300 gives 1 %
    at 95 %); confidence defaults to criteria.confidence of the yaml."""
    if trials <= 0:
        return math.nan
    if events >= trials:
        return 1.0
    return float(beta.ppf(_confidence(confidence), events + 1, trials - events))


@dataclass(frozen=True)
class ReadStats:
    trials: int
    successes: int
    rate: float
    fail_high: float        # upper bound on the failure rate
    read_high: float        # upper bound on the read rate (stray reads of M13b)


def read_stats(trials: int, successes: int, confidence: float | None = None) -> ReadStats:
    return ReadStats(
        trials=trials,
        successes=successes,
        rate=successes / trials if trials > 0 else math.nan,
        fail_high=binomial_upper_bound(trials - successes, trials, confidence),
        read_high=binomial_upper_bound(successes, trials, confidence),
    )


def read_summary(
    rows: Iterable[RfidRow | CohabRow], keys: Sequence[str], confidence: float | None = None
) -> dict[tuple, ReadStats]:
    """Trials and successes summed over the rows sharing the given columns."""
    acc: dict[tuple, list[int]] = {}
    for r in rows:
        if r.trials <= 0:
            continue
        tot = acc.setdefault(tuple(getattr(r, k) for k in keys), [0, 0])
        tot[0] += r.trials
        tot[1] += r.successes
    return {k: read_stats(n, s, confidence) for k, (n, s) in acc.items()}


@dataclass(frozen=True)
class ActivationThreshold:
    level: float            # hardest level that meets the target, with every easier one
    failing_level: float    # the next harder level measured, which misses it (nan if none)
    trials: int             # at `level`
    successes: int
    fail_high: float        # failure-rate bound at `level`


def m13a_activation_threshold(
    level: Sequence[float],
    trials: Sequence[int],
    successes: Sequence[int],
    target_rate: float | None = None,
    confidence: float | None = None,
    higher_is_easier: bool = True,
) -> ActivationThreshold:
    """Activation threshold from series of reads at several levels: field
    or field proxy (higher is easier), or gap or offset (higher is harder).
    Walking from the easiest level, the threshold is the last one whose
    read rate meets the target; a lucky series beyond the first miss does
    not count. Levels measured twice are pooled. target_rate and
    confidence default to criteria.read_target_rate and
    criteria.confidence of the yaml."""
    target_rate = _target(target_rate)
    lv = np.round(np.asarray(level, dtype=float), 9)
    n = np.asarray(trials, dtype=int)
    k = np.asarray(successes, dtype=int)
    uniq = sorted(set(lv.tolist()), reverse=higher_is_easier)
    found = math.nan
    found_n = found_k = 0
    failing = math.nan
    for u in uniq:
        sel = lv == u
        nn, kk = int(n[sel].sum()), int(k[sel].sum())
        if nn > 0 and kk >= target_rate * nn - 1e-9:
            found, found_n, found_k = u, nn, kk
        else:
            failing = u
            if math.isnan(found):
                found_n, found_k = nn, kk
            break
    return ActivationThreshold(
        level=found,
        failing_level=failing,
        trials=found_n,
        successes=found_k,
        fail_high=binomial_upper_bound(found_n - found_k, found_n, confidence),
    )


def field_from_pickup(
    pickup_mv: float | np.ndarray, calib: Iterable[PickupRow]
) -> float | np.ndarray:
    """Field tag reading to A/m through its calibration table, linear
    between points; nan outside the calibrated range (no extrapolation)."""
    pts = sorted((c.pickup_mv, c.h_a_per_m) for c in calib)
    if len(pts) < 2:
        raise ValueError("the calibration needs at least two points")
    xs = np.array([p[0] for p in pts])
    ys = np.array([p[1] for p in pts])
    out = np.interp(np.asarray(pickup_mv, dtype=float), xs, ys, left=math.nan, right=math.nan)
    return float(out) if np.ndim(out) == 0 else out


def field_margin_from_gap(
    z_reached_mm: float, z_required_mm: float, field_at: Callable[[float], float]
) -> float:
    """Field margin from the gap method: the largest gap that still reads
    (z_reached) against the gap that must read (z_required), converted by
    the loop's field against height at constant current (field_at)."""
    return field_at(z_required_mm) / field_at(z_reached_mm)


def m13a_thresholds(
    rows: Iterable[RfidRow],
    target_rate: float | None = None,
    calib: Iterable[PickupRow] | None = None,
    confidence: float | None = None,
    keys: Sequence[str] = ("square", "tag_id", "z_mm", "x_mm", "y_mm"),
) -> dict[tuple, ActivationThreshold]:
    """Activation threshold per group of m13a rows, the level being the
    field at the tag from the field tag (A/m when calib is given, raw
    millivolts otherwise)."""
    cal = list(calib) if calib is not None else None
    groups: dict[tuple, list[RfidRow]] = {}
    for r in rows:
        if r.test == "m13a":
            groups.setdefault(tuple(getattr(r, k) for k in keys), []).append(r)
    out = {}
    for key, grp in groups.items():
        lv = [r.pickup_mv for r in grp]
        if cal is not None:
            lv = [float(field_from_pickup(v, cal)) for v in lv]
        out[key] = m13a_activation_threshold(
            lv, [r.trials for r in grp], [r.successes for r in grp], target_rate, confidence)
    return out


def resonance_q(freq_hz: Sequence[float], magnitude: Sequence[float]) -> tuple[float, float]:
    """(f0, Q) of a resonance peak of a linear magnitude (|S21| to the probe
    loop, |Z|): f0 at the peak, refined by a parabola, Q over the width
    between the two half-power crossings, each interpolated."""
    f = np.asarray(freq_hz, dtype=float)
    m = np.asarray(magnitude, dtype=float)
    k = int(np.argmax(m))
    if k == 0 or k == len(m) - 1:
        raise ValueError("the peak sits at an end of the sweep")
    y0, y1, y2 = m[k - 1], m[k], m[k + 1]
    denom = y0 - 2.0 * y1 + y2
    shift = 0.5 * (y0 - y2) / denom if denom != 0.0 else 0.0
    f0 = float(f[k] + shift * (f[k + 1] - f[k - 1]) / 2.0)
    half = y1 / math.sqrt(2.0)
    i = k
    while i > 0 and m[i] > half:
        i -= 1
    j = k
    while j < len(m) - 1 and m[j] > half:
        j += 1
    if m[i] > half or m[j] > half:
        raise ValueError("the sweep does not reach the half-power points")
    f_lo = f[i] + (half - m[i]) * (f[i + 1] - f[i]) / (m[i + 1] - m[i])
    f_hi = f[j - 1] + (half - m[j - 1]) * (f[j] - f[j - 1]) / (m[j] - m[j - 1])
    return f0, float(f0 / (f_hi - f_lo))


def differential_z_from_s(
    s11: complex | np.ndarray,
    s21: complex | np.ndarray,
    s22: complex | np.ndarray,
    s12: complex | np.ndarray | None = None,
    z0_ohm: float = 50.0,
) -> complex | np.ndarray:
    """Differential impedance between the two network inputs from the
    single-ended S-parameters of the two half-network inputs (NanoVNA:
    forward sweep for S11 and S21, cables swapped for S22; S12 = S21 by
    reciprocity unless given): Z = z0 (I + S) (I - S)^-1, then
    Zdiff = Z11 + Z22 - Z12 - Z21, the impedance a floating source (an
    ideal 1:1 balun) sees. On a symmetric network it equals the mixed-mode
    value from Sdd11 = (S11 - S12 - S21 + S22) / 2. z0_ohm is the
    reference of the sweep, as load_touchstone returns it."""
    s21 = np.asarray(s21, dtype=complex)
    s12 = s21 if s12 is None else np.asarray(s12, dtype=complex)
    s11 = np.asarray(s11, dtype=complex)
    s22 = np.asarray(s22, dtype=complex)
    s = np.stack([np.stack([s11, s12], axis=-1), np.stack([s21, s22], axis=-1)], axis=-2)
    eye = np.eye(2)
    zm = z0_ohm * (eye + s) @ np.linalg.inv(eye - s)
    z = zm[..., 0, 0] + zm[..., 1, 1] - zm[..., 0, 1] - zm[..., 1, 0]
    return complex(z) if np.ndim(z) == 0 else z


def differential_z_from_one_port(
    z_open: complex | np.ndarray,
    z_grounded: complex | np.ndarray,
    z_open_other: complex | np.ndarray | None = None,
) -> complex | np.ndarray:
    """Differential impedance from one-port readings at the half-network
    inputs: input 1 with input 2 open (Z11), input 1 with input 2 grounded
    (Z11 - Z12^2 / Z22), and input 2 with input 1 open (Z22, taken equal
    to Z11 for a symmetric network when omitted). Exact for a reciprocal
    network: Zdiff = Z11 + Z22 - 2 Z12. The sign of Z12 is the one that
    gives the larger real part: the other root is the common-mode path,
    which leaves the loop out and is nearly reactive at the carrier."""
    z11 = np.asarray(z_open, dtype=complex)
    z22 = z11 if z_open_other is None else np.asarray(z_open_other, dtype=complex)
    z12 = np.sqrt(z22 * (z11 - np.asarray(z_grounded, dtype=complex)))
    a = z11 + z22 - 2.0 * z12
    b = z11 + z22 + 2.0 * z12
    z = np.where(a.real >= b.real, a, b)
    return complex(z) if np.ndim(z) == 0 else z


def match_frequency_hz(
    freq_hz: Sequence[float], z_ohm: Sequence[complex], z_target_ohm: float
) -> float:
    """Frequency of the best match to z_target_ohm (smallest reflection),
    refined by a parabola through the three points around the minimum."""
    f = np.asarray(freq_hz, dtype=float)
    z = np.asarray(z_ohm, dtype=complex)
    g = np.abs((z - z_target_ohm) / (z + z_target_ohm))
    k = int(np.argmin(g))
    if k == 0 or k == len(g) - 1:
        return float(f[k])
    y0, y1, y2 = g[k - 1], g[k], g[k + 1]
    denom = y0 - 2.0 * y1 + y2
    shift = 0.5 * (y0 - y2) / denom if denom != 0.0 else 0.0
    return float(f[k] + shift * (f[k + 1] - f[k - 1]) / 2.0)


# --- M14: cohabitation and environment ---------------------------------------


def min_safe_distance(distance_mm: Sequence[float], ok: Sequence[bool]) -> float:
    """Smallest distance from which every farther distance measured passes;
    nan when even the farthest fails. Distances measured twice must pass
    every time."""
    d = np.round(np.asarray(distance_mm, dtype=float), 9)
    passed = np.asarray(ok, dtype=bool)
    uniq = np.unique(d)
    good = np.array([passed[d == u].all() for u in uniq])
    if not good[-1]:
        return math.nan
    bad = np.nonzero(~good)[0]
    return float(uniq[bad[-1] + 1] if bad.size else uniq[0])
