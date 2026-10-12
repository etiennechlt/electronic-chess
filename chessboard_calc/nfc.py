"""NFC identity layer of the Hall plus RFID alternative (note 24): one
13.56 MHz loop under every square, a passive tag in every piece, and the
question ADR 0001 answered by hand, whether 64 such loops can share one
reader through an analog multiplexer.

Models are first order, like coupling.py: Mohan spiral inductances, the
square loop replaced by the circle of equal area for the mutual
inductance with the tag coil, on-axis field of the loop for the ISO 14443
minimum field. Relative comparisons are the meaningful output.

The mockup of note 25 (section hall_rfid.mockup) adds the models that size
a real board, all at the carrier and all parametric on the pitch:

- the loop: Mohan inductance on its copper envelope (the value the network
  is designed on), checked against the filament model of filament.py;
  AC resistance from the 2D PEEC of its cross-section (skin and proximity),
  plus the feed leads; turn-to-turn capacitance from coplanar strips.
- the matching network of the MFRC522, symmetric, per side: TX, driver
  resistance, EMC filter L0 (with its Q) and C0 to ground, series C1,
  shunt C2, damping Rq, loop. Analysed as a half circuit around the virtual
  ground of the loop's midpoint. Rq sets the loaded Q; C1 and C2 come from
  an exact synthesis (capacitor ESR and inductor loss included) to the
  target differential impedance with the tuning tag at the nominal gap, then
  are normalized to a main value plus a trim, the pair of trims that keeps
  the impedance closest to the target; their detuning is the shift of the
  frequency at which the normalized network comes closest to the target.
  The TX pins are antiphase
  square waves between ground and TVDD; the supply current is the rectified
  mean of the sinusoidal TX current, without the cosine of its phase (an
  upper bound).
- the tag: round two-layer coil in series (top spiral outward, bottom
  inward, both ends at the centre), concentric circular filaments for the
  inductance, voltage-weighted plate overlap between the layers for the
  self capacitance, the chip as a parallel R and C. Its coupling to a loop
  is the flux of the loop's filaments through each turn; the tag loads the
  loop through its reflected impedance.
- activation: the chip voltage of a tag against the one the reference
  sticker (nfc.tag, with a lossless coil, which favours it) gets in a
  uniform field of h_min. This replaces link().h_margin, which is the same
  for every tag size.
- the relay by an idle neighbour loop (two loops, the tag as an open probe)
  and the detuning by a conductive plate under the board (image loop,
  perfect conductor).
- the tag in its piece: the ferrite magnet to first order in its
  susceptibility (integral of B squared over its volume), the LC coil of
  the piece as a closed coil coupled to the tag (coaxial filaments).
- the bench: field per square root of watt, carrier picked up by the Hall
  traces (flux of the loop between them, then the RC filter), TX current
  against capacitor and loop inductance errors, the multiplexer emulation
  of M13c, and the EMF of the field tag in a uniform field.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, replace
from functools import lru_cache

import numpy as np
from scipy.optimize import brentq
from scipy.special import ellipk

from . import filament as fl
from .config import (
    BoardConfig,
    Color,
    NfcAntennaCfg,
    NfcLoopCfg,
    PieceType,
    base_diameter_mm,
    resolve_geometry,
)
from .coupling import mutual_coaxial_loops_nH
from .inductance import mohan_L_uH, piece_coil_design
from .physics import EPS0_F_PER_M, EPS_R_FR4, MU0_H_PER_M, RHO_CU_OHM_M

# IEC 60063 preferred numbers, one decade
_E_SERIES = {
    "E6": (1.0, 1.5, 2.2, 3.3, 4.7, 6.8),
    "E12": (1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2),
    "E24": (1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0,
            3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1),
}
_LOOP_NSUB = 8       # sub-filaments per track for a loop's own inductance
_FIELD_NSUB = 3      # for fields, fluxes and mutuals between loops
_DETUNE_SPAN = 0.10  # frequency span searched for the target impedance, +- of the carrier
_DETUNE_POINTS = 1001
IDLE_STATES = ("held", "floating")


@dataclass(frozen=True)
class LoopGeometry:
    side_mm: float
    d_in_mm: float
    turns: int
    track_mm: float
    gap_mm: float
    L_uH: float             # Mohan current sheet on the copper envelope


def loop_geometry(loop: NfcLoopCfg | NfcAntennaCfg, pitch_mm: float) -> LoopGeometry:
    """Square loop of concentric turns, side as a fraction of the pitch."""
    side = loop.side_ratio * pitch_mm
    # N tracks and N - 1 gaps between the outer and the inner edge (note 25,
    # paragraph 2, point 10: one gap too many underestimated L by 7 %)
    d_in = side - 2.0 * (loop.turns * loop.track_mm + (loop.turns - 1) * loop.gap_mm)
    return LoopGeometry(
        side_mm=side,
        d_in_mm=d_in,
        turns=loop.turns,
        track_mm=loop.track_mm,
        gap_mm=loop.gap_mm,
        L_uH=mohan_L_uH(loop.turns, side, d_in, layout="square"),
    )


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
    geo = loop_geometry(a, pitch_mm)
    omega = 2.0 * math.pi * nfc.f_hz
    x_l = omega * geo.L_uH * 1e-6
    return NfcAntenna(
        side_mm=geo.side_mm,
        d_in_mm=geo.d_in_mm,
        turns=a.turns,
        L_uH=geo.L_uH,
        x_l_ohm=x_l,
        c_res_pF=1.0 / (omega * omega * geo.L_uH * 1e-6) * 1e12,
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


# ------------------------------------------------------------- preferred values
def _preferred(series: str, value: float) -> np.ndarray:
    """Preferred values of the series in the decades around value."""
    d = math.floor(math.log10(value))
    return np.array(
        [float(f"{m * 10.0 ** (d + k):.6g}") for k in (-1, 0, 1) for m in _E_SERIES[series]]
    )


def nearest_preferred(value: float, series: str) -> float:
    """Preferred value nearest to value, on a logarithmic scale."""
    vals = _preferred(series, value)
    return float(vals[np.argmin(np.abs(np.log(vals / value)))])


def main_and_trims(value: float, series: str) -> list[tuple[float, float]]:
    """Largest preferred value at or below value, with the trims in parallel
    that bracket the rest (nothing, the value below, the value above)."""
    vals = _preferred(series, value)
    main = float(np.max(vals[vals <= value * (1.0 + 1e-9)]))
    rest = value - main
    if rest <= value * 1e-9:
        return [(main, 0.0)]
    trims = _preferred(series, rest)
    below = trims[trims <= rest]
    above = trims[trims >= rest]
    out = [(main, 0.0)]
    out += [(main, float(np.max(below)))] if below.size else []
    out += [(main, float(np.min(above)))] if above.size else []
    return out


# ----------------------------------------------------------------- the loops
def _loop_cfg(cfg: BoardConfig, loop: str | NfcLoopCfg | NfcAntennaCfg) -> NfcLoopCfg:
    if isinstance(loop, str):
        return cfg.hall_rfid.mockup.loops[loop]
    return loop


def _loop_key(geo: LoopGeometry) -> tuple[float, int, float, float]:
    return (geo.side_mm, geo.turns, geo.track_mm, geo.gap_mm)


def _loop_filaments(key: tuple, nsub: int, centre=(0.0, 0.0), z_mm: float = 0.0) -> fl.Filaments:
    side, turns, track, gap = key
    return fl.square_loop(side, turns, track, gap, nsub, centre, z_mm)


@lru_cache(maxsize=64)
def _loop_self_h(key: tuple, copper_mm: float) -> float:
    return fl.self_inductance_h(_loop_filaments(key, _LOOP_NSUB), key[2], _LOOP_NSUB, copper_mm)


@lru_cache(maxsize=256)
def _loop_mutual_h(key_a: tuple, key_b: tuple, dx_mm: float, dy_mm: float, dz_mm: float,
                   nsub: int = _FIELD_NSUB) -> float:
    """Mutual of loop a at the origin and loop b displaced, same sense."""
    a = _loop_filaments(key_a, nsub)
    b = _loop_filaments(key_b, nsub, (dx_mm, dy_mm), dz_mm)
    return fl.mutual_h(a, b)


@lru_cache(maxsize=1024)
def _loop_flux_h(key: tuple, centre: tuple[float, float], z_mm: float,
                 radii_mm: tuple[float, ...]) -> float:
    """Flux per ampere of the loop through coaxial circles, summed."""
    f = _loop_filaments(key, _FIELD_NSUB)
    return float(np.sum(fl.flux_through_circles_h(f, centre, z_mm, np.array(radii_mm))))


@lru_cache(maxsize=256)
def _loop_h_axis_per_a(key: tuple, z_mm: float) -> float:
    f = _loop_filaments(key, _FIELD_NSUB)
    return float(fl.bz_t_per_a(f, np.array([[0.0, 0.0, z_mm * 1e-3]]))[0]) / MU0_H_PER_M


@lru_cache(maxsize=64)
def _loop_resistance(key: tuple, copper_mm: float, lead_mm: float,
                     f_hz: float) -> tuple[float, float]:
    """DC and AC resistance of a loop: turns along their centrelines, the
    leads with the outer turn's resistance per length."""
    side, turns, track, gap = key
    sides = [side - track - 2.0 * i * (track + gap) for i in range(turns)]
    rp = fl.strip_resistance_per_m(
        tuple(s / 2.0 for s in sides), (0.0,) * turns, track, copper_mm, f_hz
    )
    lengths_m = [4.0 * s * 1e-3 for s in sides]
    r_ac = sum(r * ln for r, ln in zip(rp, lengths_m, strict=True)) + rp[0] * lead_mm * 1e-3
    r_dc = RHO_CU_OHM_M / (track * copper_mm * 1e-6) * (sum(lengths_m) + lead_mm * 1e-3)
    return r_dc, r_ac


def _coplanar_strips_f_per_m(track_mm: float, gap_mm: float) -> float:
    """Two coplanar strips on the board surface, conformal mapping."""
    k = gap_mm / (gap_mm + 2.0 * track_mm)
    eps_eff = (EPS_R_FR4 + 1.0) / 2.0
    return EPS0_F_PER_M * eps_eff * float(ellipk(1.0 - k * k) / ellipk(k * k))


@dataclass(frozen=True)
class NfcLoop:
    name: str
    pitch_mm: float
    geometry: LoopGeometry
    L_uH: float             # Mohan, the value the network is designed on
    L_filament_uH: float    # filament model, the check
    r_dc_ohm: float
    r_ac_ohm: float         # skin and proximity at the carrier, leads included
    c_self_pF: float        # adjacent turns, voltage weighted
    q0: float               # unloaded, omega L over r_ac


def loop_model(
    cfg: BoardConfig, pitch_mm: float, loop: str | NfcLoopCfg | NfcAntennaCfg
) -> NfcLoop:
    """Electrical model of a reader loop at the carrier."""
    mk = cfg.hall_rfid.mockup
    geo = loop_geometry(_loop_cfg(cfg, loop), pitch_mm)
    key = _loop_key(geo)
    copper = mk.board.copper_um * 1e-3
    f = cfg.hall_rfid.nfc.f_hz
    r_dc, r_ac = _loop_resistance(key, copper, mk.matching.loop_lead_mm, f)
    sides = [geo.side_mm - geo.track_mm - 2.0 * i * (geo.track_mm + geo.gap_mm)
             for i in range(geo.turns)]
    c_pair = _coplanar_strips_f_per_m(geo.track_mm, geo.gap_mm)
    c_self = sum(c_pair * 4.0 * s * 1e-3 for s in sides[1:]) / geo.turns**2
    return NfcLoop(
        name=loop if isinstance(loop, str) else "loop",
        pitch_mm=pitch_mm,
        geometry=geo,
        L_uH=geo.L_uH,
        L_filament_uH=_loop_self_h(key, copper) * 1e6,
        r_dc_ohm=r_dc,
        r_ac_ohm=r_ac,
        c_self_pF=c_self * 1e12,
        q0=2.0 * math.pi * f * geo.L_uH * 1e-6 / r_ac,
    )


def loop_esr_ohm(cfg: BoardConfig, pitch_mm: float, loop: str | NfcLoopCfg) -> float:
    """AC resistance of a loop at the carrier, skin and proximity included."""
    return loop_model(cfg, pitch_mm, loop).r_ac_ohm


# ------------------------------------------------------------------ the tags
@dataclass(frozen=True)
class TagGeometry:
    size: str
    piece: PieceType
    pitch_mm: float
    base_mm: float
    disc_mm: float          # the tag board
    copper_d_mm: float      # outer edge of the outer turn
    d_in_mm: float          # inner edge of the inner turn
    layers: int
    turns_per_layer: int
    track_mm: float         # track and gap
    radii_mm: tuple[float, ...]      # turn centrelines, outer first
    layer_z_mm: tuple[float, ...]    # copper of each layer above the lower one
    L_uH: float             # both layers in series
    L_layer_uH: float       # one layer alone
    k_layers: float         # coupling between the two layers
    c_self_pF: float        # plate overlap between the layers, voltage weighted
    c_chip_pF: float
    f_self_mhz: float       # bare: chip plus self capacitance
    tuned: bool             # f_self inside the window of tags.f_self_mhz
    r_dc_ohm: float
    r_ac_ohm: float
    na_mm2: float           # turn areas summed over both layers


def _tag_radii(copper_d: float, turns: int, track: float) -> tuple[float, ...]:
    """Turn centrelines, outer first; the gap equals the track."""
    return tuple(copper_d / 2.0 - track / 2.0 - i * 2.0 * track for i in range(turns))


def _tag_l_and_c(radii: tuple[float, ...], track: float, board: float,
                 copper: float) -> tuple[float, float, float]:
    """Inductance of both layers in series, of one layer, and the self
    capacitance (F) of the overlap, top spiral outward, bottom inward."""
    l_both = fl.circular_coil_h(radii, (0.0, board), track, copper)
    l_one = fl.circular_coil_h(radii, (0.0,), track, copper)
    lengths = [2.0 * math.pi * r * 1e-3 for r in reversed(radii)]  # inner first
    total = 2.0 * sum(lengths)
    run, c_self = 0.0, 0.0
    for ln in lengths:
        v_top = (run + ln / 2.0) / total
        run += ln
        c_plate = EPS0_F_PER_M * EPS_R_FR4 * ln * track * 1e-3 / (board * 1e-3)
        c_self += c_plate * (1.0 - 2.0 * v_top) ** 2
    return l_both, l_one, c_self


def tag_geometry(cfg: BoardConfig, pitch_mm: float, size: str) -> TagGeometry:
    """Tag coil for the base of its piece class: the widest track (track =
    gap) and the turn count that put the bare self resonance inside the
    window, nearest its centre, the inner opening kept above its share of
    the copper diameter; the closest miss if none does."""
    tg = cfg.hall_rfid.mockup.tags
    if tg.layers != 2:
        raise ValueError("the tag model is a two-layer coil, both ends at the centre")
    piece = tg.sizes[size]
    base = base_diameter_mm(cfg, piece, pitch_mm)
    disc = base - 2.0 * (tg.wall_mm + tg.fit_mm)
    copper_d = disc - 2.0 * tg.edge_mm
    copper = cfg.hall_rfid.mockup.board.copper_um * 1e-3
    c_chip = tg.chip.c_in_pF * 1e-12
    opening_min = max(tg.opening_min_ratio * copper_d, 0.0)
    lo, hi = tg.f_self_mhz
    centre = math.sqrt(lo * hi)
    best = None   # (miss, distance to centre, -track, turns)
    for track in sorted(tg.track_options_mm, reverse=True):
        hits = []
        turns = 1
        while copper_d - 2.0 * (2 * turns - 1) * track > opening_min:
            radii = _tag_radii(copper_d, turns, track)
            l_both, _, c_self = _tag_l_and_c(radii, track, tg.board_mm, copper)
            f = 1.0 / (2.0 * math.pi * math.sqrt(l_both * (c_chip + c_self))) * 1e-6
            miss = max(lo - f, f - hi, 0.0)
            cand = (miss, abs(math.log(f / centre)), -track, turns)
            if miss == 0.0:
                hits.append(cand)
            if best is None or cand < best:
                best = cand
            turns += 1
        if hits:
            best = min(hits)
            break
    if best is None:
        raise ValueError(f"tag {size}: no turn fits a {disc:.1f} mm disc")
    miss, _, neg_track, turns = best
    track = -neg_track
    radii = _tag_radii(copper_d, turns, track)
    l_both, l_one, c_self = _tag_l_and_c(radii, track, tg.board_mm, copper)
    layer_z = (0.0, tg.board_mm)
    rp = fl.strip_resistance_per_m(
        radii * 2, (0.0,) * turns + (tg.board_mm,) * turns, track, copper,
        cfg.hall_rfid.nfc.f_hz,
    )
    lengths_m = [2.0 * math.pi * r * 1e-3 for r in radii * 2]
    r_ac = sum(r * ln for r, ln in zip(rp, lengths_m, strict=True))
    r_dc = RHO_CU_OHM_M / (track * copper * 1e-6) * sum(lengths_m)
    m12 = (l_both - 2.0 * l_one) / 2.0
    return TagGeometry(
        size=size,
        piece=piece,
        pitch_mm=pitch_mm,
        base_mm=base,
        disc_mm=disc,
        copper_d_mm=copper_d,
        d_in_mm=copper_d - 2.0 * (2 * turns - 1) * track,
        layers=tg.layers,
        turns_per_layer=turns,
        track_mm=track,
        radii_mm=radii,
        layer_z_mm=layer_z,
        L_uH=l_both * 1e6,
        L_layer_uH=l_one * 1e6,
        k_layers=m12 / l_one,
        c_self_pF=c_self * 1e12,
        c_chip_pF=tg.chip.c_in_pF,
        f_self_mhz=1.0 / (2.0 * math.pi * math.sqrt(l_both * (c_chip + c_self))) * 1e-6,
        tuned=miss == 0.0,
        r_dc_ohm=r_dc,
        r_ac_ohm=r_ac,
        na_mm2=sum(math.pi * r * r for r in radii) * tg.layers,
    )


@dataclass(frozen=True)
class TagTuning:
    size: str
    geometry: TagGeometry
    trims_pF: tuple[float, ...]
    f_mhz: tuple[float, ...]   # resonance with each trim in parallel with the chip


def tag_tuning(cfg: BoardConfig, pitch_mm: float, size: str) -> TagTuning:
    geo = tag_geometry(cfg, pitch_mm, size)
    trims = cfg.hall_rfid.mockup.tags.trims_pF[size]
    l_h = geo.L_uH * 1e-6
    f = tuple(
        1.0 / (2.0 * math.pi * math.sqrt(l_h * (geo.c_chip_pF + geo.c_self_pF + t) * 1e-12)) * 1e-6
        for t in trims
    )
    return TagTuning(size=size, geometry=geo, trims_pF=tuple(trims), f_mhz=f)


def tag_trim_pF(cfg: BoardConfig, pitch_mm: float, size: str, f_mhz: float) -> float:
    """Capacitance to add to the chip for the tag to resonate at f_mhz."""
    geo = tag_geometry(cfg, pitch_mm, size)
    c_total = 1.0 / ((2.0 * math.pi * f_mhz * 1e6) ** 2 * geo.L_uH * 1e-6) * 1e12
    return c_total - geo.c_chip_pF - geo.c_self_pF


def _tag_impedance(cfg: BoardConfig, geo: TagGeometry, trim_pF: float,
                   omega: np.ndarray | float) -> tuple:
    """Series impedance of the tag circuit and the chip's part of it."""
    c = (geo.c_chip_pF + geo.c_self_pF + trim_pF) * 1e-12
    z_chip = 1.0 / (1.0 / cfg.hall_rfid.mockup.tags.chip_r_ohm + 1j * omega * c)
    return geo.r_ac_ohm + 1j * omega * geo.L_uH * 1e-6 + z_chip, z_chip


def _tag_z_mm(cfg: BoardConfig, extra_gap_mm: float) -> float:
    """Loop copper to the tag's lower copper."""
    return cfg.gap.air_gap_mm + cfg.hall_rfid.nfc.tag.height_in_base_mm + extra_gap_mm


def _loop_tag_mutual_h(key: tuple, geo: TagGeometry, centre: tuple[float, float],
                       z_mm: float) -> float:
    return sum(_loop_flux_h(key, centre, z_mm + lz, geo.radii_mm) for lz in geo.layer_z_mm)


def _reference_radii_mm(cfg: BoardConfig) -> tuple[float, ...]:
    """Turns of the reference sticker (nfc.tag), spread evenly over its annulus."""
    t = cfg.hall_rfid.nfc.tag
    step = (t.d_out_mm - t.d_in_mm) / 2.0 / t.turns
    return tuple(t.d_in_mm / 2.0 + (i + 0.5) * step for i in range(t.turns))


def reference_chip_voltage_v(cfg: BoardConfig) -> float:
    """Chip voltage (rms) of the reference sticker (nfc.tag) in a uniform
    field of h_min: coil lossless, chip with the parallel resistance of
    tags.chip_r_ohm."""
    nfc = cfg.hall_rfid.nfc
    t = nfc.tag
    na = sum(math.pi * (r * 1e-3) ** 2 for r in _reference_radii_mm(cfg))
    omega = 2.0 * math.pi * nfc.f_hz
    emf = omega * MU0_H_PER_M * nfc.h_min_a_per_m * na
    z_chip = 1.0 / (1.0 / cfg.hall_rfid.mockup.tags.chip_r_ohm + 1j * omega * t.c_in_pF * 1e-12)
    return emf * abs(z_chip / (1j * omega * tag(cfg).L_uH * 1e-6 + z_chip))


# ------------------------------------------------------------- the network
@dataclass(frozen=True)
class _Network:
    """Per side values, SI, and the loop it drives."""

    l0: float
    r_l0: float
    c0: float
    c1: float
    c2: float
    esr: float
    rq: float
    r_drv: float
    l_loop: float
    r_loop: float
    c_self: float
    v_src: float            # differential fundamental, rms


@dataclass(frozen=True)
class _Response:
    z_tx: np.ndarray        # differential, TX1 to TX2, driver excluded
    i_tx: np.ndarray        # rms
    v_c0: np.ndarray        # rms, C0 node to ground
    i_loop: np.ndarray      # rms, through the loop inductance


def _zc(c: float, esr: float, omega):
    return esr + 1.0 / (1j * omega * c)


def _respond(net: _Network, omega, z_refl, scale=(1.0, 1.0, 1.0)) -> _Response:
    """Drive the network; scale multiplies C0, C1 and C2 (tolerance corners)."""
    zl = net.r_loop + 1j * omega * net.l_loop + z_refl
    z_ant = 1.0 / (1.0 / zl + 1j * omega * net.c_self)
    zh = z_ant / 2.0 + net.rq
    zb = 1.0 / (1.0 / zh + 1.0 / _zc(net.c2 * scale[2], net.esr, omega))
    zx = _zc(net.c1 * scale[1], net.esr, omega) + zb
    za = 1.0 / (1.0 / zx + 1.0 / _zc(net.c0 * scale[0], net.esr, omega))
    z_tx = 2.0 * (net.r_l0 + 1j * omega * net.l0 + za)
    i_tx = net.v_src / (2.0 * net.r_drv + z_tx)
    v_a = i_tx * za
    i_branch = v_a / zx * zb / zh
    return _Response(z_tx=z_tx, i_tx=i_tx, v_c0=v_a, i_loop=i_branch * z_ant / zl)


def _synthesize(
    net: _Network, omega: float, z_refl: complex, z_target: float
) -> tuple[float, float]:
    """C1 and C2 per side that make the differential impedance z_target,
    real, at the carrier, every loss included."""
    zl = net.r_loop + 1j * omega * net.l_loop + z_refl
    z_ant = 1.0 / (1.0 / zl + 1j * omega * net.c_self)
    zh = z_ant / 2.0 + net.rq
    za = z_target / 2.0 - (net.r_l0 + 1j * omega * net.l0)
    zx = 1.0 / (1.0 / za - 1.0 / _zc(net.c0, net.esr, omega))
    r_b = zx.real - net.esr
    c2_max = -(1.0 / zh).imag / omega     # C2 that cancels the loop susceptance

    def real_part_miss(c2: float) -> float:
        return (1.0 / (1.0 / zh + 1.0 / _zc(c2, net.esr, omega))).real - r_b

    lo, hi = c2_max * 1e-6, c2_max * (1.0 - 1e-9)
    if r_b <= 0.0 or real_part_miss(lo) * real_part_miss(hi) > 0.0:
        raise ValueError("no C1, C2 network reaches the target impedance")
    c2 = brentq(real_part_miss, lo, hi, xtol=1e-18, rtol=1e-12)
    zb = 1.0 / (1.0 / zh + 1.0 / _zc(c2, net.esr, omega))
    x_c1 = zb.imag - zx.imag
    if x_c1 <= 0.0:
        raise ValueError("the target impedance needs a negative C1")
    return 1.0 / (omega * x_c1), c2


def _base_network(cfg: BoardConfig, lp: NfcLoop, rq: float, c1: float = 1.0,
                  c2: float = 1.0) -> _Network:
    mk = cfg.hall_rfid.mockup
    m, r = mk.matching, mk.reader
    omega = 2.0 * math.pi * cfg.hall_rfid.nfc.f_hz
    return _Network(
        l0=m.l0_nH * 1e-9,
        r_l0=omega * m.l0_nH * 1e-9 / m.l0_q,
        c0=m.c0_pF * 1e-12,
        c1=c1,
        c2=c2,
        esr=m.cap_esr_ohm,
        rq=rq,
        r_drv=r.r_drive_ohm,
        l_loop=lp.L_uH * 1e-6,
        r_loop=lp.r_ac_ohm,
        c_self=lp.c_self_pF * 1e-12,
        v_src=4.0 * r.tvdd_v / (math.pi * math.sqrt(2.0)),
    )


def _i_tvdd(i_tx) -> np.ndarray:
    """Supply current: rectified mean of a sinusoidal TX current (rms)."""
    return 2.0 * math.sqrt(2.0) / math.pi * np.abs(i_tx)


@dataclass(frozen=True)
class NfcMatching:
    loop: str
    pitch_mm: float
    tag: str                # the tag of the tag states, at the nominal gap
    trim_pF: float
    tuned_with_tag: bool    # tuned with that tag, or without any
    L_uH: float
    r_loop_ohm: float
    c_self_pF: float
    q0: float
    rq_exact_ohm: float     # per side, for q_loaded
    rq_ohm: float           # per side, preferred value
    q_loaded: float         # with the preferred Rq
    half_band_pct: float    # half the loaded bandwidth, of the carrier
    l0_nH: float
    c0_pF: float
    f_emc_mhz: float
    c1_exact_pF: float      # per side
    c2_exact_pF: float
    c1_pF: tuple[float, float]   # main and trim, in parallel
    c2_pF: tuple[float, float]
    z_exact_ohm: complex    # exact values, in the tuning state
    z_ohm: complex          # normalized values, tag at the nominal gap
    z_no_tag_ohm: complex
    z_max_gap_ohm: complex
    z_off_centre_ohm: complex    # tag at the admissible offset
    detune_pct: float       # where the normalized network shows the target, tuning state
    i_tx_ma: float          # rms, differential, tag at the nominal gap
    i_tx_no_tag_ma: float
    i_tvdd_ma: float
    i_tvdd_worst_ma: float  # C0, C1, C2 tolerance corners, with and without tag
    i_loop_ma: float        # rms, full conductance
    v_c0_vpp: float
    r1_ohm: float
    r2_ohm: float
    v_rx_vpp: float         # tag at the nominal gap
    v_rx_max_vpp: float     # over the tag states
    h_axis_a_per_m: float   # on axis at the tag, nominal gap, full conductance
    service_fraction: float  # of the full loop current, keeps the field under h_max

    @property
    def c1_built_pF(self) -> float:
        return sum(self.c1_pF)

    @property
    def c2_built_pF(self) -> float:
        return sum(self.c2_pF)


def _network_of(cfg: BoardConfig, mt: NfcMatching) -> _Network:
    lp = loop_model(cfg, mt.pitch_mm, mt.loop)
    return _base_network(cfg, lp, mt.rq_ohm, mt.c1_built_pF * 1e-12, mt.c2_built_pF * 1e-12)


def _target_frequency_hz(net: _Network, f0: float, z_target: float, z_refl_of) -> float:
    """Frequency near the carrier where the network comes closest to the
    target impedance: the carrier itself for the exact values."""
    f = f0 * (1.0 + np.linspace(-_DETUNE_SPAN, _DETUNE_SPAN, _DETUNE_POINTS))
    omega = 2.0 * math.pi * f
    miss = np.abs(_respond(net, omega, z_refl_of(omega)).z_tx - z_target) ** 2
    k = int(np.argmin(miss))
    if 0 < k < f.size - 1:      # parabola through the three points around the minimum
        a, b, c = miss[k - 1 : k + 2]
        den = a - 2.0 * b + c
        if den > 0.0:
            return float(f[k] + 0.5 * (a - c) / den * (f[1] - f[0]))
    return float(f[k])


def matching(
    cfg: BoardConfig,
    pitch_mm: float,
    loop: str,
    tag: str | None = None,
    trim_pF: float = 0.0,
    tuned_with_tag: bool = True,
) -> NfcMatching:
    """The MFRC522 network of a mockup loop, tuned with the tag (by default
    matching.tune_tag, bare) centred at the nominal gap, or without any tag;
    the tag states are evaluated with that tag either way."""
    mk = cfg.hall_rfid.mockup
    m, rd = mk.matching, mk.reader
    nfc = cfg.hall_rfid.nfc
    size = m.tune_tag if tag is None else tag
    f0 = nfc.f_hz
    omega = 2.0 * math.pi * f0
    lp = loop_model(cfg, pitch_mm, loop)
    key = _loop_key(lp.geometry)
    tg = tag_geometry(cfg, pitch_mm, size)

    x_l = omega * lp.L_uH * 1e-6
    rq_exact = (x_l / m.q_loaded - lp.r_ac_ohm - 2.0 * m.cap_esr_ohm) / 2.0
    rq = nearest_preferred(rq_exact, m.rq_series) if rq_exact > 0.0 else 0.0
    q_l = x_l / (lp.r_ac_ohm + 2.0 * rq + 2.0 * m.cap_esr_ohm)

    z_tag, _ = _tag_impedance(cfg, tg, trim_pF, omega)
    z0 = _tag_z_mm(cfg, 0.0)
    dz = cfg.gap.max_total_mm - cfg.gap.nominal_total_mm
    offset = cfg.hall_rfid.layout.admissible_offset_mm
    mutual = {
        "nominal": _loop_tag_mutual_h(key, tg, (0.0, 0.0), z0),
        "max_gap": _loop_tag_mutual_h(key, tg, (0.0, 0.0), z0 + dz),
        "off_centre": _loop_tag_mutual_h(key, tg, (offset, 0.0), z0),
    }
    z_refl = {s: (omega * mm) ** 2 / z_tag for s, mm in mutual.items()}
    z_refl["no_tag"] = 0.0

    tuning = "nominal" if tuned_with_tag else "no_tag"
    base = _base_network(cfg, lp, rq)
    c1_x, c2_x = _synthesize(base, omega, z_refl[tuning], m.z_target_ohm)
    exact = _base_network(cfg, lp, rq, c1_x, c2_x)

    def built_of(c1_mt: tuple[float, float], c2_mt: tuple[float, float]) -> _Network:
        return _base_network(cfg, lp, rq, sum(c1_mt) * 1e-12, sum(c2_mt) * 1e-12)

    c1_mt, c2_mt = min(
        itertools.product(main_and_trims(c1_x * 1e12, m.cap_series),
                          main_and_trims(c2_x * 1e12, m.cap_series)),
        key=lambda c: abs(_respond(built_of(*c), omega, z_refl[tuning]).z_tx - m.z_target_ohm),
    )
    built = built_of(c1_mt, c2_mt)
    resp = {s: _respond(built, omega, zr) for s, zr in z_refl.items()}
    nominal = resp["nominal"]

    def z_refl_tuning(w):
        zt, _ = _tag_impedance(cfg, tg, trim_pF, w)
        return (w * mutual["nominal"]) ** 2 / zt if tuned_with_tag else 0.0 * w

    detune = (_target_frequency_hz(built, f0, m.z_target_ohm, z_refl_tuning) / f0 - 1.0) * 100.0

    tol = m.cap_tol_pct / 100.0
    worst = max(
        float(_i_tvdd(_respond(built, omega, z_refl[s], scale).i_tx))
        for s in ("nominal", "no_tag")
        for scale in itertools.product((1.0 - tol, 1.0 + tol), repeat=3)
    )

    # receive divider: R1 and the coupling capacitor from the C0 node to RX,
    # R2 from RX to VMID (AC ground)
    r2 = rd.rx_r2_ohm
    z_cc = 1.0 / (1j * omega * m.rx_coupling_nF * 1e-9)
    v_c0_vpp = {s: 2.0 * math.sqrt(2.0) * abs(r.v_c0) for s, r in resp.items()}
    lo, hi = rd.rx_target_vpp
    target = (lo + hi) / 2.0

    def v_rx(r1: float, state: str = "nominal") -> float:
        return v_c0_vpp[state] * abs(r2 / (r1 + r2 + z_cc))

    r1_ideal = max(r2 * (v_c0_vpp["nominal"] / target - 1.0), r2 * 1e-3)
    r1 = float(min(_preferred(m.rq_series, r1_ideal), key=lambda r: abs(v_rx(r) - target)))

    h_axis = abs(nominal.i_loop) * _loop_h_axis_per_a(key, z0)
    return NfcMatching(
        loop=loop,
        pitch_mm=pitch_mm,
        tag=size,
        trim_pF=trim_pF,
        tuned_with_tag=tuned_with_tag,
        L_uH=lp.L_uH,
        r_loop_ohm=lp.r_ac_ohm,
        c_self_pF=lp.c_self_pF,
        q0=lp.q0,
        rq_exact_ohm=rq_exact,
        rq_ohm=rq,
        q_loaded=q_l,
        half_band_pct=100.0 / (2.0 * q_l),
        l0_nH=m.l0_nH,
        c0_pF=m.c0_pF,
        f_emc_mhz=1.0 / (2.0 * math.pi * math.sqrt(m.l0_nH * 1e-9 * m.c0_pF * 1e-12)) * 1e-6,
        c1_exact_pF=c1_x * 1e12,
        c2_exact_pF=c2_x * 1e12,
        c1_pF=c1_mt,
        c2_pF=c2_mt,
        z_exact_ohm=complex(_respond(exact, omega, z_refl[tuning]).z_tx),
        z_ohm=complex(nominal.z_tx),
        z_no_tag_ohm=complex(resp["no_tag"].z_tx),
        z_max_gap_ohm=complex(resp["max_gap"].z_tx),
        z_off_centre_ohm=complex(resp["off_centre"].z_tx),
        detune_pct=detune,
        i_tx_ma=abs(nominal.i_tx) * 1e3,
        i_tx_no_tag_ma=abs(resp["no_tag"].i_tx) * 1e3,
        i_tvdd_ma=float(_i_tvdd(nominal.i_tx)) * 1e3,
        i_tvdd_worst_ma=worst * 1e3,
        i_loop_ma=abs(nominal.i_loop) * 1e3,
        v_c0_vpp=v_c0_vpp["nominal"],
        r1_ohm=r1,
        r2_ohm=r2,
        v_rx_vpp=v_rx(r1),
        v_rx_max_vpp=max(v_rx(r1, s) for s in resp),
        h_axis_a_per_m=h_axis,
        service_fraction=min(1.0, nfc.h_max_a_per_m / h_axis),
    )


# -------------------------------------------------------------- activation
@dataclass(frozen=True)
class NfcActivation:
    loop: str
    tag: str
    trim_pF: float
    pitch_mm: float
    extra_gap_mm: float
    z_mm: float             # loop copper to the tag's lower copper
    m_nH: float
    k: float
    i_loop_ma: float        # full conductance, the network tuned with matching.tune_tag
    h_axis_a_per_m: float   # on axis at the tag's lower copper, full conductance
    service_fraction: float  # of matching(): keeps the field under h_max at the nominal gap
    v_chip_v: float         # rms, full conductance
    v_ref_v: float          # reference sticker at h_min
    margin: float           # v_chip over v_ref at full conductance
    margin_service: float   # the same at the service conductance
    emf_vs_reference: float  # open EMF over the reference sticker's in its place, same current


def tag_activation(
    cfg: BoardConfig,
    pitch_mm: float,
    loop: str,
    tag: str,
    extra_gap_mm: float = 0.0,
    trim_pF: float = 0.0,
) -> NfcActivation:
    """Voltage the chip of a centred tag gets from the mockup network, and its
    margin over the reference sticker at the ISO minimum field."""
    nfc = cfg.hall_rfid.nfc
    omega = 2.0 * math.pi * nfc.f_hz
    mt = matching(cfg, pitch_mm, loop)
    net = _network_of(cfg, mt)
    lp = loop_model(cfg, pitch_mm, loop)
    key = _loop_key(lp.geometry)
    tg = tag_geometry(cfg, pitch_mm, tag)
    z = _tag_z_mm(cfg, extra_gap_mm)
    m_h = _loop_tag_mutual_h(key, tg, (0.0, 0.0), z)
    z_tag, z_chip = _tag_impedance(cfg, tg, trim_pF, omega)
    resp = _respond(net, omega, (omega * m_h) ** 2 / z_tag)
    i_loop = complex(resp.i_loop)
    v_chip = abs(1j * omega * m_h * i_loop * z_chip / z_tag)
    v_ref = reference_chip_voltage_v(cfg)
    m_ref = _loop_flux_h(key, (0.0, 0.0), z, _reference_radii_mm(cfg))
    return NfcActivation(
        loop=loop,
        tag=tag,
        trim_pF=trim_pF,
        pitch_mm=pitch_mm,
        extra_gap_mm=extra_gap_mm,
        z_mm=z,
        m_nH=m_h * 1e9,
        k=m_h / math.sqrt(lp.L_uH * 1e-6 * tg.L_uH * 1e-6),
        i_loop_ma=abs(i_loop) * 1e3,
        h_axis_a_per_m=abs(i_loop) * _loop_h_axis_per_a(key, z),
        service_fraction=mt.service_fraction,
        v_chip_v=v_chip,
        v_ref_v=v_ref,
        margin=v_chip / v_ref,
        margin_service=v_chip * mt.service_fraction / v_ref,
        emf_vs_reference=m_h / m_ref,
    )


# ------------------------------------------------------------ neighbours
@dataclass(frozen=True)
class NfcRelay:
    loop: str               # the active square
    neighbor_loop: str      # the idle square
    idle_state: str
    pitch_mm: float
    diagonal: bool
    k_loops: float          # coupling between the two loops (negative side by side)
    idle_current_ratio: float    # idle loop current over the active one
    direct_pct: float       # flux through a tag on the idle square, active loop only
    relayed_pct: float      # the same with the idle loop's current added


def _idle_impedance(net: _Network, omega: float, idle_state: str) -> complex:
    """Loop impedance of an idle reader, its TX pins held low through the
    driver or left floating, seen by an EMF in series with the loop."""
    if idle_state == "held":
        z_a = 1.0 / (1.0 / _zc(net.c0, net.esr, omega)
                     + 1.0 / (net.r_l0 + 1j * omega * net.l0 + net.r_drv))
    elif idle_state == "floating":
        z_a = _zc(net.c0, net.esr, omega)
    else:
        raise ValueError(f"idle_state must be one of {IDLE_STATES}")
    z_b = 1.0 / (1.0 / _zc(net.c2, net.esr, omega) + 1.0 / (_zc(net.c1, net.esr, omega) + z_a))
    z_net = 2.0 * (net.rq + z_b)
    z_term = 1.0 / (1.0 / z_net + 1j * omega * net.c_self)
    return net.r_loop + 1j * omega * net.l_loop + z_term


def neighbor_relay(
    cfg: BoardConfig,
    pitch_mm: float,
    loop: str,
    neighbor_loop: str,
    idle_state: str,
    diagonal: bool = False,
) -> NfcRelay:
    """Flux through a tag (matching.tune_tag, open) centred on the idle
    neighbour square, over the flux through it on the active square: direct,
    and relayed by the current the active loop induces in the idle one."""
    omega = 2.0 * math.pi * cfg.hall_rfid.nfc.f_hz
    tg = tag_geometry(cfg, pitch_mm, cfg.hall_rfid.mockup.matching.tune_tag)
    z = _tag_z_mm(cfg, 0.0)
    act = loop_model(cfg, pitch_mm, loop)
    idle = loop_model(cfg, pitch_mm, neighbor_loop)
    ka, ki = _loop_key(act.geometry), _loop_key(idle.geometry)
    centre = (pitch_mm, pitch_mm if diagonal else 0.0)
    m_loops = _loop_mutual_h(ka, ki, centre[0], centre[1], 0.0)
    net = _network_of(cfg, matching(cfg, pitch_mm, neighbor_loop))
    ratio = -1j * omega * m_loops / _idle_impedance(net, omega, idle_state)
    m_ref = _loop_tag_mutual_h(ka, tg, (0.0, 0.0), z)
    m_direct = _loop_tag_mutual_h(ka, tg, centre, z)
    m_own = _loop_tag_mutual_h(ki, tg, (0.0, 0.0), z)
    return NfcRelay(
        loop=loop,
        neighbor_loop=neighbor_loop,
        idle_state=idle_state,
        pitch_mm=pitch_mm,
        diagonal=diagonal,
        k_loops=m_loops / math.sqrt(act.L_filament_uH * idle.L_filament_uH * 1e-12),
        idle_current_ratio=abs(ratio),
        direct_pct=abs(m_direct / m_ref) * 100.0,
        relayed_pct=abs((m_direct + m_own * ratio) / m_ref) * 100.0,
    )


# ------------------------------------------------------------------- metal
@dataclass(frozen=True)
class MetalDetune:
    loop: str
    pitch_mm: float
    h_mm: float             # plate below the board's lower face
    distance_mm: float      # plate to the loop copper
    k_image: float          # mutual with the image loop over the loop inductance
    l_drop_pct: float
    detune_pct: float       # carrier shift of the loaded loop, upwards
    half_band_pct: float
    ok: bool                # inside half the loaded bandwidth


def metal_detune(cfg: BoardConfig, pitch_mm: float, loop: str, h_mm: float) -> MetalDetune:
    """A conductive plate h_mm under the board (question Q11): the image of
    the loop, mirrored in the plate, carries the opposite current."""
    lp = loop_model(cfg, pitch_mm, loop)
    key = _loop_key(lp.geometry)
    d = h_mm + cfg.gap.pcb_mm
    m_img = _loop_mutual_h(key, key, 0.0, 0.0, -2.0 * d, _LOOP_NSUB)
    k = m_img / (lp.L_filament_uH * 1e-6)
    detune = (1.0 / math.sqrt(1.0 - k) - 1.0) * 100.0
    half_band = matching(cfg, pitch_mm, loop).half_band_pct
    return MetalDetune(
        loop=loop,
        pitch_mm=pitch_mm,
        h_mm=h_mm,
        distance_mm=d,
        k_image=k,
        l_drop_pct=k * 100.0,
        detune_pct=detune,
        half_band_pct=half_band,
        ok=detune <= half_band,
    )


# ------------------------------------------------------- the tag in a piece
def _gauss_panels(edges: np.ndarray, points: int) -> tuple[np.ndarray, np.ndarray]:
    """Gauss-Legendre nodes and weights on consecutive panels."""
    x, w = np.polynomial.legendre.leggauss(points)
    lo, hi = edges[:-1, None], edges[1:, None]
    return ((hi - lo) / 2.0 * x + (hi + lo) / 2.0).ravel(), ((hi - lo) / 2.0 * w).ravel()


def ferrite_dl_h(
    radii_mm: tuple[float, ...],
    layer_z_mm: tuple[float, ...],
    r_mag_mm: float,
    z_bot_mm: float,
    thick_mm: float,
    chi: float,
) -> float:
    """Inductance a coil of coaxial turns gains from a coaxial ferrite disc
    (radius, lower face above the coil's lower layer, thickness), to first
    order in the susceptibility: chi times the integral of B squared over
    the disc, over mu0, for a unit current in the coil."""
    core = min(r_mag_mm, 1.5 * max(radii_mm))
    rho_edges = np.linspace(0.0, core, 25)
    if r_mag_mm > core:
        rho_edges = np.concatenate([rho_edges, np.geomspace(core, r_mag_mm, 9)[1:]])
    z_edges = z_bot_mm + np.concatenate([[0.0], np.geomspace(thick_mm * 1e-3, thick_mm, 16)])
    rho, w_rho = _gauss_panels(rho_edges * 1e-3, 6)
    z, w_z = _gauss_panels(z_edges * 1e-3, 6)
    rr, zz = np.meshgrid(rho, z, indexing="ij")
    br = np.zeros_like(rr)
    bz = np.zeros_like(rr)
    for lz in layer_z_mm:
        for a in radii_mm:
            dbr, dbz = fl.circular_filament_field(a * 1e-3, rr, zz - lz * 1e-3)
            br += dbr
            bz += dbz
    integrand = (br * br + bz * bz) * 2.0 * math.pi * rr
    return chi * float(w_rho @ integrand @ w_z) / MU0_H_PER_M


@dataclass(frozen=True)
class TagMagnetDetune:
    size: str
    pitch_mm: float
    magnet_d_mm: float
    magnet_t_mm: float
    gap_mm: float           # tag's upper copper to the magnet's lower face
    l_rise_pct: float       # the ferrite concentrates the field: L rises
    detune_pct: float       # tag resonance, downwards


def tag_magnet_detune(cfg: BoardConfig, pitch_mm: float, size: str) -> TagMagnetDetune:
    """Detuning of a tag by the ferrite magnet of its piece (note 25,
    paragraph 2, point 9), the magnet where the Hall model puts it."""
    tg = cfg.hall_rfid.mockup.tags
    geo = tag_geometry(cfg, pitch_mm, size)
    magnet_d = resolve_geometry(cfg, pitch_mm).classes[geo.piece].magnet_d_mm
    lift = cfg.resonator.coil.height_mm if cfg.hall_rfid.layout.magnet_above_coil else 0.0
    z_bot = lift - cfg.hall_rfid.nfc.tag.height_in_base_mm
    if z_bot <= max(geo.layer_z_mm):
        raise ValueError("the piece magnet overlaps the tag")
    dl = ferrite_dl_h(geo.radii_mm, geo.layer_z_mm, magnet_d / 2.0, z_bot,
                      cfg.piece_magnet.thickness_mm, tg.ferrite_chi)
    rise = dl / (geo.L_uH * 1e-6)
    return TagMagnetDetune(
        size=size,
        pitch_mm=pitch_mm,
        magnet_d_mm=magnet_d,
        magnet_t_mm=cfg.piece_magnet.thickness_mm,
        gap_mm=z_bot - max(geo.layer_z_mm),
        l_rise_pct=rise * 100.0,
        detune_pct=(1.0 / math.sqrt(1.0 + rise) - 1.0) * 100.0,
    )


_COIL_CELLS = (8, 6)   # radial and axial cells of a piece coil's winding section


@dataclass(frozen=True)
class TagPieceCoil:
    size: str
    pitch_mm: float
    piece: PieceType
    coil_turns: int
    k: float                # tag to the LC coil of the piece, laid on the tag
    l_loss_pct: float       # tag inductance lost to the coil closed on its capacitor
    f_tag_mhz: float        # bare tag resonance with the coil there (was f_self_mhz)


def tag_piece_coil(
    cfg: BoardConfig, pitch_mm: float, size: str, color: Color = Color.WHITE
) -> TagPieceCoil:
    """The LC coil of the piece (resonator), laid on the tag's upper copper
    and closed on its capacitor, seen from the tag at the carrier (note 25,
    paragraph 2, point 9). The coil's own capacitance and resistance are
    left out: far below its self resonance it acts as a closed turn."""
    geo = tag_geometry(cfg, pitch_mm, size)
    cls = resolve_geometry(cfg, pitch_mm).classes[geo.piece]
    coil = piece_coil_design(cfg, geo.piece, pitch_mm)
    nr, nz = _COIL_CELLS
    dr = (cls.coil_d_out_mm - cls.coil_d_in_mm) / 2.0 / nr
    dz = cfg.resonator.coil.height_mm / nz
    r_edges = np.linspace(cls.coil_d_in_mm / 2.0, cls.coil_d_out_mm / 2.0, nr + 1)
    z_edges = max(geo.layer_z_mm) + np.linspace(0.0, cfg.resonator.coil.height_mm, nz + 1)
    rc, zc = np.meshgrid(0.5 * (r_edges[:-1] + r_edges[1:]), 0.5 * (z_edges[:-1] + z_edges[1:]))
    rc, zc = rc.ravel() * 1e-3, zc.ravel() * 1e-3
    wc = np.full(rc.size, 1.0 / rc.size)
    l_c = fl.coaxial_set_self_h(rc, zc, wc, np.full(rc.size, fl.GMD_RECT * (dr + dz) * 1e-3))
    rt = np.array([r for _ in geo.layer_z_mm for r in geo.radii_mm]) * 1e-3
    zt = np.array([z for z in geo.layer_z_mm for _ in geo.radii_mm]) * 1e-3
    m = fl.coaxial_set_mutual_h(rc, zc, wc, rt, zt, np.ones(rt.size))
    l_t = geo.L_uH * 1e-6
    k = m / math.sqrt(l_c * l_t)
    omega = 2.0 * math.pi * cfg.hall_rfid.nfc.f_hz
    n = coil.n_turns
    cap = cfg.pieces.classes[geo.piece].cap_nF[color] * 1e-9
    z_coil = 1j * omega * n * n * l_c + 1.0 / (1j * omega * cap)
    l_eff = l_t + ((omega * n * m) ** 2 / z_coil).imag / omega
    return TagPieceCoil(
        size=size,
        pitch_mm=pitch_mm,
        piece=geo.piece,
        coil_turns=n,
        k=k,
        l_loss_pct=(1.0 - l_eff / l_t) * 100.0,
        f_tag_mhz=geo.f_self_mhz * math.sqrt(l_t / l_eff),
    )


# ---------------------------------------------------------- loop merit
@dataclass(frozen=True)
class LoopMerit:
    loop: str
    pitch_mm: float
    h_per_a: float          # on axis at the tag, nominal gap, A/m per A
    h_per_sqrt_w_loop: float     # per square root of the power in the loop's own resistance
    h_per_sqrt_w_loaded: float   # the same with the damping, at the network's loaded Q
    k_side: float           # to the loop of the side neighbour square
    k_diagonal: float


def loop_merit(cfg: BoardConfig, pitch_mm: float, loop: str) -> LoopMerit:
    """Field per square root of watt and coupling to the neighbours (note 25,
    paragraph 4.2), for comparing loops."""
    lp = loop_model(cfg, pitch_mm, loop)
    key = _loop_key(lp.geometry)
    h = _loop_h_axis_per_a(key, _tag_z_mm(cfg, 0.0))
    x_l = 2.0 * math.pi * cfg.hall_rfid.nfc.f_hz * lp.L_uH * 1e-6
    q_l = matching(cfg, pitch_mm, loop).q_loaded
    l_fil = lp.L_filament_uH * 1e-6
    return LoopMerit(
        loop=loop,
        pitch_mm=pitch_mm,
        h_per_a=h,
        h_per_sqrt_w_loop=h / math.sqrt(lp.r_ac_ohm),
        h_per_sqrt_w_loaded=h / math.sqrt(x_l / q_l),
        k_side=_loop_mutual_h(key, key, pitch_mm, 0.0, 0.0) / l_fil,
        k_diagonal=_loop_mutual_h(key, key, pitch_mm, pitch_mm, 0.0) / l_fil,
    )


# ----------------------------------------------------------- Hall traces
@dataclass(frozen=True)
class HallTracePickup:
    loop: str
    pitch_mm: float
    spacing_mm: float       # between the outermost traces
    length_mm: float        # square centre to past the loop's ground keepout
    flux_nwb_per_a: float   # through the strip, per ampere in the loop
    emf_mv: float           # rms, full conductance loop current
    filtered_mv: float      # after the sensor's output RC filter
    filter_db: float


def hall_trace_pickup(
    cfg: BoardConfig, pitch_mm: float, loop: str, spacing_mm: float | None = None
) -> HallTracePickup:
    """Carrier picked up by the Hall trio leaving a loop on the back copper,
    straight from the sensor at the square centre to past the ground
    keepout (note 25, paragraph 4.3). By default the outermost traces of a
    tight trio, two trio pitches apart."""
    mk = cfg.hall_rfid.mockup
    s = 2.0 * mk.hall.trio_pitch_mm if spacing_mm is None else spacing_mm
    lp = loop_model(cfg, pitch_mm, loop)
    key = _loop_key(lp.geometry)
    length = lp.geometry.side_mm / 2.0 + mk.ground_keepout_mm
    x, wx = _gauss_panels(np.linspace(0.0, length, int(math.ceil(length / 0.25)) + 1) * 1e-3, 4)
    y, wy = _gauss_panels(np.array([-s / 2.0, s / 2.0]) * 1e-3, 4)
    xx, yy = np.meshgrid(x, y, indexing="ij")
    pts = np.stack([xx.ravel(), yy.ravel(), np.full(xx.size, -cfg.gap.pcb_mm * 1e-3)], axis=1)
    bz = fl.bz_t_per_a(_loop_filaments(key, _FIELD_NSUB), pts).reshape(xx.shape)
    flux = float(wx @ bz @ wy)
    omega = 2.0 * math.pi * cfg.hall_rfid.nfc.f_hz
    emf = omega * abs(flux) * matching(cfg, pitch_mm, loop).i_loop_ma * 1e-3
    gain = 1.0 / abs(1.0 + 1j * omega * mk.hall.filter_r_ohm * mk.hall.filter_c_nF * 1e-9)
    return HallTracePickup(
        loop=loop,
        pitch_mm=pitch_mm,
        spacing_mm=s,
        length_mm=length,
        flux_nwb_per_a=flux * 1e9,
        emf_mv=emf * 1e3,
        filtered_mv=emf * gain * 1e3,
        filter_db=20.0 * math.log10(gain),
    )


# -------------------------------------------------------- spread of the TX
@dataclass(frozen=True)
class TxSpread:
    loop: str
    pitch_mm: float
    cap_tol_pct: float      # on C1 and C2, both sides alike
    l_error_pct: float      # on the loop inductance
    i_tx_max_ma: float      # rms, worst corner, with and without the tag
    i_tvdd_max_ma: float
    i_tvdd_min_ma: float


def tx_supply_spread(
    cfg: BoardConfig, pitch_mm: float, loop: str, cap_tol_pct: float, l_error_pct: float = 0.0
) -> TxSpread:
    """TX current of the built network when C1 and C2 drift by cap_tol_pct
    and the real loop inductance misses the model by l_error_pct (note 25,
    paragraph 4.4), over the corners and the centre of both ranges."""
    mt = matching(cfg, pitch_mm, loop)
    net = _network_of(cfg, mt)
    omega = 2.0 * math.pi * cfg.hall_rfid.nfc.f_hz
    tg = tag_geometry(cfg, pitch_mm, mt.tag)
    lp = loop_model(cfg, pitch_mm, loop)
    m_h = _loop_tag_mutual_h(_loop_key(lp.geometry), tg, (0.0, 0.0), _tag_z_mm(cfg, 0.0))
    z_tag, _ = _tag_impedance(cfg, tg, mt.trim_pF, omega)
    t, e = cap_tol_pct / 100.0, l_error_pct / 100.0
    currents = []
    for z_refl in ((omega * m_h) ** 2 / z_tag, 0.0):
        for s1, s2, sl in itertools.product((-1, 0, 1), repeat=3):
            n = replace(net, l_loop=net.l_loop * (1.0 + sl * e))
            resp = _respond(n, omega, z_refl, (1.0, 1.0 + s1 * t, 1.0 + s2 * t))
            currents.append(abs(complex(resp.i_tx)))
    tvdd = _i_tvdd(np.array(currents))
    return TxSpread(
        loop=loop,
        pitch_mm=pitch_mm,
        cap_tol_pct=cap_tol_pct,
        l_error_pct=l_error_pct,
        i_tx_max_ma=max(currents) * 1e3,
        i_tvdd_max_ma=float(np.max(tvdd)) * 1e3,
        i_tvdd_min_ma=float(np.min(tvdd)) * 1e3,
    )


# ------------------------------------------------- M13c, the mux emulation
@dataclass(frozen=True)
class MuxEmulation:
    loop: str
    pitch_mm: float
    rq_ohm: float           # at each Rq place
    c_parallel_pF: float    # across the loop
    q_loop: float           # omega L over the loop and both resistors
    i_loop_ma: float        # full conductance, network left as tuned
    h_axis_a_per_m: float   # at the tag, nominal gap
    i_tx_ma: float
    i_tvdd_ma: float
    h_at_tvdd_limit_a_per_m: float   # conductance lowered to the M13c TVDD limit
    i_tx_cut_loop_ma: float          # the same network with the loop cut
    i_tvdd_cut_loop_ma: float


def mux_emulation(cfg: BoardConfig, pitch_mm: float, loop: str) -> MuxEmulation:
    """M13c (note 25, question Q8): the resistance and capacitance a
    multiplexer would hang on the loop, fitted on the built network
    (criteria.mux_emulation_*), the tuning tag centred at the nominal gap.
    A lower conductance is taken as a lower source voltage."""
    crit = cfg.hall_rfid.mockup.criteria
    mt = matching(cfg, pitch_mm, loop)
    net = _network_of(cfg, mt)
    omega = 2.0 * math.pi * cfg.hall_rfid.nfc.f_hz
    lp = loop_model(cfg, pitch_mm, loop)
    key = _loop_key(lp.geometry)
    tg = tag_geometry(cfg, pitch_mm, mt.tag)
    z0 = _tag_z_mm(cfg, 0.0)
    m_h = _loop_tag_mutual_h(key, tg, (0.0, 0.0), z0)
    z_tag, _ = _tag_impedance(cfg, tg, mt.trim_pF, omega)
    z_refl = (omega * m_h) ** 2 / z_tag
    emulated = replace(net, rq=crit.mux_emulation_rq_ohm,
                       c_self=net.c_self + crit.mux_emulation_c_pF * 1e-12)
    resp = _respond(emulated, omega, z_refl)
    cut = _respond(replace(emulated, rq=1e12), omega, 0.0)
    i_tvdd = float(_i_tvdd(resp.i_tx))
    h = abs(complex(resp.i_loop)) * _loop_h_axis_per_a(key, z0)
    return MuxEmulation(
        loop=loop,
        pitch_mm=pitch_mm,
        rq_ohm=crit.mux_emulation_rq_ohm,
        c_parallel_pF=crit.mux_emulation_c_pF,
        q_loop=omega * net.l_loop / (net.r_loop + 2.0 * crit.mux_emulation_rq_ohm),
        i_loop_ma=abs(complex(resp.i_loop)) * 1e3,
        h_axis_a_per_m=h,
        i_tx_ma=abs(complex(resp.i_tx)) * 1e3,
        i_tvdd_ma=i_tvdd * 1e3,
        h_at_tvdd_limit_a_per_m=h * min(1.0, crit.mux_emulation_i_tvdd_max_ma * 1e-3 / i_tvdd),
        i_tx_cut_loop_ma=abs(complex(cut.i_tx)) * 1e3,
        i_tvdd_cut_loop_ma=float(_i_tvdd(cut.i_tx)) * 1e3,
    )


# ------------------------------------------------------------ field tag
@dataclass(frozen=True)
class FieldPickup:
    h_a_per_m: float
    turns: int
    na_mm2: float           # turn areas summed over the layers
    emf_mv_peak: float      # open circuit, uniform field
    single_turn_mv_peak: float   # one turn on the outer centreline


def field_pickup(cfg: BoardConfig, h_a_per_m: float) -> FieldPickup:
    """EMF of the field tag of the tag panel (mockup.pickup, note 25,
    paragraph 5) in a uniform field, against a single turn."""
    pk = cfg.hall_rfid.mockup.pickup
    per_layer = pk.turns // pk.layers
    radii = [pk.d_mm / 2.0 - pk.track_mm / 2.0 - i * 2.0 * pk.track_mm for i in range(per_layer)]
    na = pk.layers * sum(math.pi * r * r for r in radii)
    volts_per_mm2 = (math.sqrt(2.0) * 2.0 * math.pi * cfg.hall_rfid.nfc.f_hz
                     * MU0_H_PER_M * h_a_per_m * 1e-6)
    return FieldPickup(
        h_a_per_m=h_a_per_m,
        turns=pk.turns,
        na_mm2=na,
        emf_mv_peak=volts_per_mm2 * na * 1e3,
        single_turn_mv_peak=volts_per_mm2 * math.pi * radii[0] ** 2 * 1e3,
    )


# ------------------------------------------------------------------ guards
def mockup_check(cfg: BoardConfig, pitch_mm: float | None = None) -> list[str]:
    """Guards of the mockup's NFC chain at one pitch, or at every candidate
    pitch by default; an empty list holds."""
    mk = cfg.hall_rfid.mockup
    pitches = cfg.pitch.candidates_mm if pitch_mm is None else (pitch_mm,)
    rd, tg = mk.reader, mk.tags
    dz = cfg.gap.max_total_mm - cfg.gap.nominal_total_mm
    problems = []
    for p in pitches:
        built = []
        for size in tg.sizes:
            try:
                geo = tag_geometry(cfg, p, size)
            except ValueError:
                problems.append(f"tag {size} at p = {p:g}: does not fit its base")
                continue
            built.append(size)
            if not geo.tuned:
                problems.append(f"tag {size} at p = {p:g}: self-resonance outside its window")
        for loop in sorted(set(mk.loop_by_column.values())):
            where = f"loop {loop} at p = {p:g}"
            try:
                mt = matching(cfg, p, loop)
            except ValueError as err:
                problems.append(f"{where}: {err}")
                continue
            if mt.rq_exact_ohm <= 0.0:
                problems.append(f"{where}: the loop alone is below the loaded Q target")
            if abs(mt.z_exact_ohm - mk.matching.z_target_ohm) > 0.01 * mk.matching.z_target_ohm:
                problems.append(f"{where}: exact network misses the target impedance")
            if abs(mt.detune_pct) > mt.half_band_pct:
                problems.append(f"{where}: normalized network detunes past half the bandwidth")
            if mt.i_tvdd_worst_ma > rd.i_tvdd_max_ma:
                problems.append(f"{where}: TX supply over the reader limit at the C tolerance")
            lo, hi = rd.rx_target_vpp
            if not lo <= mt.v_rx_vpp <= hi:
                problems.append(f"{where}: RX amplitude outside its target")
            if mt.v_rx_max_vpp > rd.rx_max_vpp:
                problems.append(f"{where}: RX over its input limit")
            for size in built:
                # Q5 of note 25: the margin counts at the service field, and the
                # panel carries several trims of each size, one of which must hold
                best = max(
                    tag_activation(cfg, p, loop, size, dz, trim).margin_service
                    for trim in tg.trims_pF[size]
                )
                if best < tg.activation_margin_min:
                    problems.append(
                        f"{where}: tag {size} activation margin below the minimum at the "
                        "service field, whatever its trim"
                    )
    return problems
