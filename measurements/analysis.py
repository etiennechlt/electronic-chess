"""Analysis functions for the mockup measurement campaign.

The notebook is a thin presentation layer over these functions, which
are unit-tested against synthetic ringdowns (tests/test_analysis.py).
CSV formats are the firmware's: scan lines `sq,fa_hz,fb_hz,amp_mv,
snr_db10` and raw dumps of 512 ADC samples (one value per line, with
`# fs_hz=` in the header).
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np


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
