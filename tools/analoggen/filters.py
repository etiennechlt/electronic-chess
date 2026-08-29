"""Analog chain computations: Sallen-Key stages and chain gain.

Equal-component Sallen-Key stages: fc = 1 / (2 pi R C) and
Q = 1 / (3 - K), so the Butterworth Q of 0.7071 asks for K = 1.586.
Values are rounded to E96 (resistors) and E12 (capacitors); the SPICE
run in the test suite checks the resulting corners and gain.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

E96 = [
    1.00, 1.02, 1.05, 1.07, 1.10, 1.13, 1.15, 1.18, 1.21, 1.24, 1.27, 1.30,
    1.33, 1.37, 1.40, 1.43, 1.47, 1.50, 1.54, 1.58, 1.62, 1.65, 1.69, 1.74,
    1.78, 1.82, 1.87, 1.91, 1.96, 2.00, 2.05, 2.10, 2.15, 2.21, 2.26, 2.32,
    2.37, 2.43, 2.49, 2.55, 2.61, 2.67, 2.74, 2.80, 2.87, 2.94, 3.01, 3.09,
    3.16, 3.24, 3.32, 3.40, 3.48, 3.57, 3.65, 3.74, 3.83, 3.92, 4.02, 4.12,
    4.22, 4.32, 4.42, 4.53, 4.64, 4.75, 4.87, 4.99, 5.11, 5.23, 5.36, 5.49,
    5.62, 5.76, 5.90, 6.04, 6.19, 6.34, 6.49, 6.65, 6.81, 6.98, 7.15, 7.32,
    7.50, 7.68, 7.87, 8.06, 8.25, 8.45, 8.66, 8.87, 9.09, 9.31, 9.53, 9.76,
]


def round_e96(value: float) -> float:
    if value <= 0:
        raise ValueError("value must be positive")
    exp = math.floor(math.log10(value))
    mant = value / 10**exp
    best = min(E96 + [10.0], key=lambda m: abs(m - mant))
    return best * 10**exp


@dataclass(frozen=True)
class SkStage:
    kind: str            # "hp" or "lp"
    fc_hz: float         # achieved corner with rounded values
    r_ohm: float
    c_f: float
    k: float             # stage gain 1 + rf/rg
    rf_ohm: float
    rg_ohm: float

    @property
    def q(self) -> float:
        return 1.0 / (3.0 - self.k)


def design_sk(kind: str, fc_target_hz: float, q_target: float, c_f: float) -> SkStage:
    r_ideal = 1.0 / (2.0 * math.pi * fc_target_hz * c_f)
    r = round_e96(r_ideal)
    k_ideal = 3.0 - 1.0 / q_target
    rg = 1000.0
    rf = round_e96((k_ideal - 1.0) * rg)
    k = 1.0 + rf / rg
    return SkStage(
        kind=kind,
        fc_hz=1.0 / (2.0 * math.pi * r * c_f),
        r_ohm=r, c_f=c_f, k=k, rf_ohm=rf, rg_ohm=rg,
    )


@dataclass(frozen=True)
class ChainDesign:
    ina_gain: float
    hp: SkStage
    lp: SkStage
    out_gain: float
    out_rf_ohm: float
    out_rg_ohm: float

    @property
    def total_gain(self) -> float:
        return self.ina_gain * self.hp.k * self.lp.k * self.out_gain


def design_chain(cfg) -> ChainDesign:
    """Full chain from the mockup.analog section of the config."""
    filt = cfg.mockup.analog.filter
    hp = design_sk("hp", filt.hp_hz, filt.q, 1.0e-9)
    lp = design_sk("lp", filt.lp_hz, filt.q, 330.0e-12)
    rg = 1000.0
    rf = round_e96((filt.output_gain - 1.0) * rg)
    return ChainDesign(
        ina_gain=cfg.mockup.analog.ina.gain,
        hp=hp, lp=lp,
        out_gain=1.0 + rf / rg,
        out_rf_ohm=rf, out_rg_ohm=rg,
    )
