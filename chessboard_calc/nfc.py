"""NFC identity layer of the Hall plus RFID alternative (note 24): one
13.56 MHz loop under every square, a passive tag in every piece, and the
question ADR 0001 answered by hand, whether 64 such loops can share one
reader through an analog multiplexer.

Models are first order, like coupling.py: Mohan spiral inductances, the
square loop replaced by the circle of equal area for the mutual
inductance with the tag coil, on-axis field of the loop for the ISO 14443
minimum field. Relative comparisons are the meaningful output.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .config import BoardConfig
from .coupling import mutual_coaxial_loops_nH
from .inductance import mohan_L_uH


@dataclass(frozen=True)
class NfcAntenna:
    side_mm: float
    d_in_mm: float
    turns: int
    L_uH: float
    x_l_ohm: float          # reactance at the carrier
    c_res_pF: float         # capacitance that tunes it to the carrier
    r_series_ohm: float     # total series resistance that gives q_target
    bandwidth_khz: float    # carrier over q_target


def antenna(cfg: BoardConfig, pitch_mm: float) -> NfcAntenna:
    nfc = cfg.hall_rfid.nfc
    a = nfc.antenna
    side = a.side_ratio * pitch_mm
    d_in = side - 2.0 * a.turns * (a.track_mm + a.gap_mm)
    l_uh = mohan_L_uH(a.turns, side, d_in, layout="square")
    omega = 2.0 * math.pi * nfc.f_hz
    x_l = omega * l_uh * 1e-6
    return NfcAntenna(
        side_mm=side,
        d_in_mm=d_in,
        turns=a.turns,
        L_uH=l_uh,
        x_l_ohm=x_l,
        c_res_pF=1.0 / (omega * omega * l_uh * 1e-6) * 1e12,
        r_series_ohm=x_l / a.q_target,
        bandwidth_khz=nfc.f_hz / a.q_target * 1e-3,
    )


@dataclass(frozen=True)
class NfcTag:
    part: str
    L_uH: float
    f_self_mhz: float       # with the chip's input capacitance


def tag(cfg: BoardConfig) -> NfcTag:
    t = cfg.hall_rfid.nfc.tag
    l_uh = mohan_L_uH(t.turns, t.d_out_mm, t.d_in_mm, layout="circular")
    f_self = 1.0 / (2.0 * math.pi * math.sqrt(l_uh * 1e-6 * t.c_in_pF * 1e-12))
    return NfcTag(part=t.part, L_uH=l_uh, f_self_mhz=f_self * 1e-6)


@dataclass(frozen=True)
class NfcLink:
    z_mm: float             # antenna copper to tag coil
    k: float
    m_nH: float
    h_axis_a_per_m: float   # field at the tag for antenna_current_ma_rms
    h_margin: float         # over the ISO 14443 minimum


def link(cfg: BoardConfig, pitch_mm: float, extra_gap_mm: float = 0.0) -> NfcLink:
    nfc = cfg.hall_rfid.nfc
    ant = antenna(cfg, pitch_mm)
    tg = tag(cfg)
    z = cfg.gap.air_gap_mm + nfc.tag.height_in_base_mm + extra_gap_mm
    r_ant = (ant.side_mm + ant.d_in_mm) / 2.0 / math.sqrt(math.pi)
    r_tag = (nfc.tag.d_out_mm + nfc.tag.d_in_mm) / 4.0
    m_nh = ant.turns * nfc.tag.turns * mutual_coaxial_loops_nH(r_ant, r_tag, z)
    k = m_nh * 1e-3 / math.sqrt(ant.L_uH * tg.L_uH)
    r_m, z_m = r_ant * 1e-3, z * 1e-3
    i_a = nfc.antenna_current_ma_rms * 1e-3
    h = ant.turns * i_a * r_m * r_m / (2.0 * (r_m * r_m + z_m * z_m) ** 1.5)
    return NfcLink(z_mm=z, k=k, m_nH=m_nh, h_axis_a_per_m=h, h_margin=h / nfc.h_min_a_per_m)


@dataclass(frozen=True)
class SwitchVerdict:
    switch: str
    q_with_switch: float    # antenna Q once the switch resistance is in the loop
    c_parasitic_pF: float   # off channels plus common node hung on the tuned loop
    detune_pct: float       # carrier shift the parasitic capacitance causes
    ok: bool                # Q above half the target and the shift inside half the bandwidth


def switch_verdict(
    cfg: BoardConfig,
    pitch_mm: float,
    switch: str,
    ron_ohm: float,
    c_off_pF: float,
    c_common_pF: float,
    channels: int,
) -> SwitchVerdict:
    nfc = cfg.hall_rfid.nfc
    ant = antenna(cfg, pitch_mm)
    q = ant.x_l_ohm / (ant.r_series_ohm + ron_ohm)
    c_par = c_common_pF + (channels - 1) * c_off_pF
    detune = (math.sqrt(ant.c_res_pF / (ant.c_res_pF + c_par)) - 1.0) * 100.0
    half_bw_pct = 100.0 / (2.0 * nfc.antenna.q_target)
    return SwitchVerdict(
        switch=switch,
        q_with_switch=q,
        c_parasitic_pF=c_par,
        detune_pct=detune,
        ok=q >= nfc.antenna.q_target / 2.0 and abs(detune) <= half_bw_pct,
    )


def analog_mux_verdict(cfg: BoardConfig, pitch_mm: float) -> SwitchVerdict:
    """The CD74HC4067 of the Hall layer, asked to switch the NFC loops."""
    m = cfg.hall_rfid.mux
    return switch_verdict(cfg, pitch_mm, m.part, m.ron_ohm, m.c_off_pF, m.c_on_pF, m.channels)


nfc_link = link


def check(cfg: BoardConfig, pitch_mm: float | None = None) -> list[str]:
    """Guards of the NFC layer as a per-square reader; an empty list holds."""
    if pitch_mm is None:
        pitch_mm = cfg.pitch.plateau_mm
    nfc = cfg.hall_rfid.nfc
    problems = []
    tg = tag(cfg)
    if not nfc.f_hz * 1e-6 <= tg.f_self_mhz <= 1.5 * nfc.f_hz * 1e-6:
        problems.append("tag self-resonance away from the carrier")
    far = link(cfg, pitch_mm, cfg.gap.max_total_mm - cfg.gap.nominal_total_mm)
    if far.h_margin < 1.0:
        problems.append("field at the tag below the ISO 14443 minimum at the maximum gap")
    ant = antenna(cfg, pitch_mm)
    if ant.side_mm > pitch_mm or ant.d_in_mm <= 0.0:
        problems.append("antenna loop does not fit the square")
    return problems
