"""Sense-coil to piece-coil coupling and received signal estimates.

Geometry convention: air_gap_mm is the distance from the PCB top copper
to the underside of the piece coil, i.e. play surface + felt (+ any
extra lift). It excludes the PCB thickness; the per-layer depth of the
four sense spirals is added internally. The brief's 'entrefer nominal'
of 5.1 mm therefore corresponds to air_gap_mm = 3.5 with a 1.6 mm PCB.

The excitation model is deliberately first-order (fast current step,
flux transfer derated by an efficiency factor from config). Absolute
amplitudes carry the model uncertainty; relative comparisons (pitch,
gap, class) are the meaningful output until measurement 4 calibrates.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from scipy.special import ellipe, ellipk

from .config import BoardConfig, Color, PieceType
from .inductance import pcb_sense_coil, piece_coil_design
from .physics import K_BOLTZMANN, MU0_H_PER_M, T_AMBIENT_K
from .resonance import frequency_plan, ringdown_tau_us

_PIECE_FILAMENTS = 12  # radial discretization of the piece winding


def _mutual_h(r1_m: np.ndarray, r2_m: np.ndarray, d_m: float) -> np.ndarray:
    """Maxwell mutual inductance of coaxial circular filaments, in henries."""
    m = 4.0 * r1_m * r2_m / ((r1_m + r2_m) ** 2 + d_m * d_m)
    k = np.sqrt(m)
    return MU0_H_PER_M * np.sqrt(r1_m * r2_m) * ((2.0 / k - k) * ellipk(m) - 2.0 / k * ellipe(m))


def mutual_coaxial_loops_nH(r1_mm: float, r2_mm: float, axial_gap_mm: float) -> float:
    if min(r1_mm, r2_mm) <= 0.0 or axial_gap_mm <= 0.0:
        raise ValueError("radii and axial gap must be positive")
    value = _mutual_h(np.asarray(r1_mm * 1e-3), np.asarray(r2_mm * 1e-3), axial_gap_mm * 1e-3)
    return float(value) * 1e9


@dataclass(frozen=True)
class CouplingResult:
    k: float
    m_uH: float
    L_sense_uH: float
    L_piece_uH: float


def coupling(
    cfg: BoardConfig, piece: PieceType, pitch_mm: float, air_gap_mm: float | None = None
) -> CouplingResult:
    """Mutual inductance and coupling factor by filament decomposition."""
    if air_gap_mm is None:
        air_gap_mm = cfg.gap.air_gap_mm
    if air_gap_mm <= 0.0:
        raise ValueError("air_gap_mm must be positive")
    sense = pcb_sense_coil(cfg, pitch_mm)
    pcoil = piece_coil_design(cfg, piece, pitch_mm)

    turn_pitch = (sense.d_out_mm - sense.d_in_mm) / 2.0 / sense.turns_per_layer
    sense_radii_m = (
        np.linspace(
            sense.d_in_mm / 2.0 + turn_pitch / 2.0,
            sense.d_out_mm / 2.0 - turn_pitch / 2.0,
            sense.turns_per_layer,
        )
        * 1e-3
    )
    layer_depths_mm = np.linspace(0.0, cfg.gap.pcb_mm, sense.layers)

    edges = np.linspace(pcoil.d_in_mm / 2.0, pcoil.d_out_mm / 2.0, _PIECE_FILAMENTS + 1)
    piece_radii_m = (edges[:-1] + edges[1:]) / 2.0 * 1e-3
    turns_per_filament = pcoil.n_turns / _PIECE_FILAMENTS

    m_total_h = 0.0
    piece_z_mm = air_gap_mm + pcoil.height_mm / 2.0
    for depth in layer_depths_mm:
        d_m = (piece_z_mm + depth) * 1e-3
        grid = _mutual_h(piece_radii_m[:, None], sense_radii_m[None, :], d_m)
        m_total_h += turns_per_filament * float(np.sum(grid))

    m_uh = m_total_h * 1e6
    k = m_uh / math.sqrt(sense.L_uH * pcoil.L_achieved_uH)
    return CouplingResult(
        k=k, m_uH=m_uh, L_sense_uH=sense.L_uH, L_piece_uH=pcoil.L_achieved_uH
    )


def coupling_k(
    cfg: BoardConfig, piece: PieceType, pitch_mm: float, air_gap_mm: float | None = None
) -> float:
    return coupling(cfg, piece, pitch_mm, air_gap_mm).k


@dataclass(frozen=True)
class SignalEstimate:
    piece: PieceType
    color: Color
    pitch_mm: float
    air_gap_mm: float
    f0_hz: float
    k: float
    m_uH: float
    drive_delta_i_a: float
    piece_current_a: float
    emf_v: float
    emf_after_blanking_v: float
    preamp_out_v: float
    noise_in_vrms: float
    snr_db: float
    snr_avg_db: float


def ringdown_signal(
    cfg: BoardConfig,
    piece: PieceType,
    color: Color,
    pitch_mm: float,
    air_gap_mm: float | None = None,
) -> SignalEstimate:
    """First-order received-signal chain for one piece on its square.

    Steps: drive current ramp into the sense coil, flux-transfer estimate
    of the resonator's initial current (derated by excitation_efficiency),
    back-EMF at the resonant frequency, exponential decay through the
    blanking window, minimum preamp gain, and input-referred noise over
    the analog band. Coherent averaging adds 10 log10(N) to the SNR.
    """
    if air_gap_mm is None:
        air_gap_mm = cfg.gap.air_gap_mm
    meas = cfg.measurement
    cpl = coupling(cfg, piece, pitch_mm, air_gap_mm)
    line = frequency_plan(cfg).line(piece, color)

    delta_i = min(
        meas.drive.v * meas.drive.pulse_us * 1e-6 / (cpl.L_sense_uH * 1e-6),
        meas.drive.current_limit_a,
    )
    i_piece = meas.drive.excitation_efficiency * cpl.m_uH / cpl.L_piece_uH * delta_i
    omega = 2.0 * math.pi * line.f0_hz
    emf = omega * cpl.m_uH * 1e-6 * i_piece
    tau_us = ringdown_tau_us(line.f0_hz, cfg.resonator.q_min_with_magnet)
    emf_blanked = emf * math.exp(-meas.blanking_us / tau_us)

    sense = pcb_sense_coil(cfg, pitch_mm)
    r_source = sense.esr_ohm + 2.0 * cfg.mux.ron_ohm
    bw_hz = meas.band_hz[1] - meas.band_hz[0]
    e_n2 = (meas.preamp_noise_nv_rthz * 1e-9) ** 2
    thermal2 = 4.0 * K_BOLTZMANN * T_AMBIENT_K * r_source
    noise_vrms = math.sqrt((e_n2 + thermal2) * bw_hz)

    snr_db = 20.0 * math.log10(emf_blanked / math.sqrt(2.0) / noise_vrms)
    return SignalEstimate(
        piece=piece,
        color=color,
        pitch_mm=pitch_mm,
        air_gap_mm=air_gap_mm,
        f0_hz=line.f0_hz,
        k=cpl.k,
        m_uH=cpl.m_uH,
        drive_delta_i_a=delta_i,
        piece_current_a=i_piece,
        emf_v=emf,
        emf_after_blanking_v=emf_blanked,
        preamp_out_v=emf_blanked * min(meas.preamp_gain),
        noise_in_vrms=noise_vrms,
        snr_db=snr_db,
        snr_avg_db=snr_db + 10.0 * math.log10(meas.coherent_avg),
    )


def signal_vs_pitch(
    cfg: BoardConfig, gaps_mm: Sequence[float] | None = None
) -> tuple[SignalEstimate, ...]:
    """Worst-case (black pawn) signal across candidate pitches and gaps.

    Backs the brief's claim that the signal only drops a few percent
    between p = 50 and p = 40 thanks to the constant-L turn count.
    """
    if gaps_mm is None:
        gaps_mm = [cfg.gap.air_gap_mm]
    estimates = []
    for pitch in cfg.pitch.candidates_mm:
        for gap in gaps_mm:
            estimates.append(
                ringdown_signal(cfg, PieceType.PAWN, Color.BLACK, pitch, air_gap_mm=gap)
            )
    return tuple(estimates)
