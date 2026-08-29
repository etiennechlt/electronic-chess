"""SPICE validation of the amplifier chain (ngspice, AC analysis).

Models: the AD8421 as an ideal differential gain block with its
gain-bandwidth behavior at G = 20 (one pole at 1.4 MHz), the OPA2810
halves as single-pole op amps (A0 = 1e5, GBW = 105 MHz), and the exact
E96/E12 component values produced by filters.design_chain. The test
suite checks total gain, both corners and the stopband attenuations,
which pins the printed-circuit values, not just the theory.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .filters import ChainDesign

OPAMP_SUBCKT = """
.subckt opamp inp inn out
E1 n1 0 inp inn 1e5
R1 n1 n2 1k
C1 n2 0 {cpole}
E2 out 0 n2 0 1
.ends
"""


def chain_netlist(chain: ChainDesign) -> str:
    """AC testbench: 1 V differential drive into the INA inputs."""
    gbw = 105e6
    a0 = 1e5
    cpole = 1.0 / (2.0 * 3.141592653589793 * 1e3 * (gbw / a0))
    ina_pole_c = 1.0 / (2.0 * 3.141592653589793 * 1e3 * 1.4e6)
    hp, lp = chain.hp, chain.lp
    lines = [
        "* mockup analog chain",
        OPAMP_SUBCKT.replace("{cpole}", f"{cpole:.4e}"),
        "Vin inp 0 dc 0 ac 1",
        # INA: gain block with a single 1.4 MHz pole (AD8421 at G = 20).
        f"E_ina ina_raw 0 inp 0 {chain.ina_gain}",
        "R_ip ina_raw ina_p 1k",
        f"C_ip ina_p 0 {ina_pole_c:.4e}",
        "E_inab ina_out 0 ina_p 0 1",
        # Sallen-Key high-pass.
        f"C1 ina_out hp_n1 {hp.c_f:.4e}",
        f"C2 hp_n1 hp_in {hp.c_f:.4e}",
        f"R1 hp_n1 hp_out {hp.r_ohm:.4e}",
        f"R2 hp_in 0 {hp.r_ohm:.4e}",
        "X1 hp_in hp_fb hp_out opamp",
        f"Rf1 hp_out hp_fb {hp.rf_ohm:.4e}",
        f"Rg1 hp_fb 0 {hp.rg_ohm:.4e}",
        # Sallen-Key low-pass.
        f"R3 hp_out lp_n1 {lp.r_ohm:.4e}",
        f"R4 lp_n1 lp_in {lp.r_ohm:.4e}",
        f"C3 lp_n1 lp_out {lp.c_f:.4e}",
        f"C4 lp_in 0 {lp.c_f:.4e}",
        "X2 lp_in lp_fb lp_out opamp",
        f"Rf2 lp_out lp_fb {lp.rf_ohm:.4e}",
        f"Rg2 lp_fb 0 {lp.rg_ohm:.4e}",
        # Output gain stage.
        "X3 lp_out out_fb amp_out opamp",
        f"Rf3 amp_out out_fb {chain.out_rf_ohm:.4e}",
        f"Rg3 out_fb 0 {chain.out_rg_ohm:.4e}",
        ".ac dec 60 1k 20meg",
        ".control",
        "run",
        "wrdata OUTFILE mag(v(amp_out))",
        ".endc",
        ".end",
    ]
    return "\n".join(lines)


@dataclass(frozen=True)
class SpiceReport:
    gain_400k: float
    f_low_3db_hz: float
    f_high_3db_hz: float
    att_1m5_db: float
    att_50k_db: float


def run_chain_ac(chain: ChainDesign, workdir: Path) -> SpiceReport:
    if shutil.which("ngspice") is None:
        raise RuntimeError("ngspice not installed")
    workdir.mkdir(parents=True, exist_ok=True)
    data = workdir / "chain_ac.dat"
    net = chain_netlist(chain).replace("OUTFILE", data.as_posix())
    cir = workdir / "chain.cir"
    cir.write_text(net, encoding="utf-8")
    subprocess.run(["ngspice", "-b", cir.as_posix()], check=True,
                   capture_output=True, text=True, timeout=120)
    freqs, mags = [], []
    for line in data.read_text().splitlines():
        parts = re.split(r"\s+", line.strip())
        if len(parts) >= 2:
            freqs.append(float(parts[0]))
            mags.append(float(parts[1]))
    if not freqs:
        raise RuntimeError("no ngspice output")

    def mag_at(f_target):
        best = min(range(len(freqs)), key=lambda i: abs(freqs[i] - f_target))
        return mags[best]

    import math
    peak = max(mags)
    peak_db = 20 * math.log10(peak)
    lo = next(f for f, m in zip(freqs, mags, strict=True)
              if 20 * math.log10(m) >= peak_db - 3.0)
    hi = next(f for f, m in zip(reversed(freqs), reversed(mags), strict=True)
              if 20 * math.log10(m) >= peak_db - 3.0)
    return SpiceReport(
        gain_400k=mag_at(400e3),
        f_low_3db_hz=lo,
        f_high_3db_hz=hi,
        att_1m5_db=peak_db - 20 * math.log10(mag_at(1.5e6)),
        att_50k_db=peak_db - 20 * math.log10(mag_at(50e3)),
    )
