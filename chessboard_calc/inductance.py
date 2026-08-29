"""Coil inductance models and inverse design helpers.

Conventions: dimensions in mm, inductance in uH, frequency in Hz.

Wheeler's 1928 formulas are used with their original inch-based
coefficients; accuracy is a few percent for well-proportioned coils.
That is enough at design time because every resonator is calibrated
per piece afterwards (brief 3.3), and the sense coil is deliberately
non-resonant.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .config import BoardConfig, PieceType, resolve_geometry
from .physics import MM_PER_INCH, MU0_H_PER_M, RHO_CU_OHM_M

# Mohan et al., "Simple accurate expressions for planar spiral
# inductances", JSSC 1999. Coefficients (c1, c2, c3, c4) per layout.
_MOHAN_COEFFS = {
    "circular": (1.00, 2.46, 0.00, 0.20),
    "hexagonal": (1.09, 2.23, 0.00, 0.17),
    "octagonal": (1.07, 2.29, 0.00, 0.19),
    "square": (1.27, 2.07, 0.18, 0.13),
}


def _check_envelope(d_out_mm: float, d_in_mm: float) -> None:
    if not d_out_mm > d_in_mm > 0.0:
        raise ValueError(f"need d_out > d_in > 0, got d_out={d_out_mm}, d_in={d_in_mm}")


def wheeler_pancake_L_uH(n_turns: float, d_out_mm: float, d_in_mm: float) -> float:
    """Flat spiral (negligible axial height), Wheeler 1928."""
    _check_envelope(d_out_mm, d_in_mm)
    a = (d_out_mm + d_in_mm) / 4.0 / MM_PER_INCH  # average radius, inches
    c = (d_out_mm - d_in_mm) / 2.0 / MM_PER_INCH  # radial depth, inches
    return a * a * n_turns * n_turns / (8.0 * a + 11.0 * c)


def wheeler_multilayer_L_uH(
    n_turns: float, d_out_mm: float, d_in_mm: float, height_mm: float
) -> float:
    """Round coil of rectangular winding cross-section, Wheeler 1928."""
    _check_envelope(d_out_mm, d_in_mm)
    if height_mm <= 0.0:
        raise ValueError("height_mm must be positive; use wheeler_pancake_L_uH otherwise")
    a = (d_out_mm + d_in_mm) / 4.0 / MM_PER_INCH
    b = height_mm / MM_PER_INCH
    c = (d_out_mm - d_in_mm) / 2.0 / MM_PER_INCH
    return 0.8 * a * a * n_turns * n_turns / (6.0 * a + 9.0 * b + 10.0 * c)


def mohan_L_uH(
    n_turns: float, d_out_mm: float, d_in_mm: float, layout: str = "circular"
) -> float:
    """Planar spiral, Mohan current-sheet expression."""
    _check_envelope(d_out_mm, d_in_mm)
    c1, c2, c3, c4 = _MOHAN_COEFFS[layout]
    d_avg_m = (d_out_mm + d_in_mm) / 2.0 * 1e-3
    rho = (d_out_mm - d_in_mm) / (d_out_mm + d_in_mm)  # fill ratio, > 0 by envelope check
    l_h = (
        MU0_H_PER_M
        * n_turns
        * n_turns
        * d_avg_m
        * c1
        / 2.0
        * (math.log(c2 / rho) + c3 * rho + c4 * rho * rho)
    )
    return l_h * 1e6


@dataclass(frozen=True)
class TurnsSolution:
    n_turns: int
    L_achieved_uH: float
    relative_error: float


def solve_turns(
    L_target_uH: float,
    d_out_mm: float,
    d_in_mm: float,
    height_mm: float = 0.0,
    method: str = "wheeler",
) -> TurnsSolution:
    """Invert L(N) for the integer turn count closest to the target.

    All models here scale exactly with N^2 for a fixed envelope, so the
    inversion is analytic followed by integer rounding.
    """
    if method == "wheeler":
        if height_mm > 0.0:
            def model(n: float) -> float:
                return wheeler_multilayer_L_uH(n, d_out_mm, d_in_mm, height_mm)
        else:
            def model(n: float) -> float:
                return wheeler_pancake_L_uH(n, d_out_mm, d_in_mm)
    elif method == "mohan":
        def model(n: float) -> float:
            return mohan_L_uH(n, d_out_mm, d_in_mm)
    else:
        raise ValueError(f"unknown method {method!r}")

    l1 = model(1.0)
    n_real = math.sqrt(L_target_uH / l1)
    candidates = {max(1, math.floor(n_real)), max(1, math.ceil(n_real))}
    best = min(candidates, key=lambda n: abs(model(float(n)) - L_target_uH))
    achieved = model(float(best))
    return TurnsSolution(
        n_turns=best,
        L_achieved_uH=achieved,
        relative_error=(achieved - L_target_uH) / L_target_uH,
    )


@dataclass(frozen=True)
class WindowReport:
    fits: bool
    area_needed_mm2: float
    area_available_mm2: float
    wire_od_mm: float


def wire_window_check(
    n_turns: int,
    d_out_mm: float,
    d_in_mm: float,
    height_mm: float,
    wire_mm: float,
    fill_factor: float,
    insulation_extra_mm: float = 0.0,
) -> WindowReport:
    """Check that N turns of round wire fit the rectangular winding window."""
    _check_envelope(d_out_mm, d_in_mm)
    depth_mm = (d_out_mm - d_in_mm) / 2.0
    od = wire_mm + insulation_extra_mm
    area_available = depth_mm * height_mm
    area_needed = n_turns * math.pi * (od / 2.0) ** 2 / fill_factor
    fits = area_needed <= area_available and od <= min(depth_mm, height_mm)
    return WindowReport(
        fits=fits,
        area_needed_mm2=area_needed,
        area_available_mm2=area_available,
        wire_od_mm=od,
    )


def skin_depth_mm(f_hz: float) -> float:
    return math.sqrt(RHO_CU_OHM_M / (math.pi * f_hz * MU0_H_PER_M)) * 1e3


def coil_esr_ohm(
    n_turns: int,
    d_avg_mm: float,
    wire_mm: float,
    f_hz: float,
    proximity_factor: float = 1.0,
) -> float:
    """First-order AC resistance of a round-wire winding.

    Skin effect uses the thick-wire asymptote r/(2 delta) + 1/4, clamped
    at the DC value; proximity effect is a flat multiplier supplied by
    the caller (config resonator.coil.proximity_factor). This is a
    design-time estimate only; measurement 1 gives the truth.
    """
    length_m = n_turns * math.pi * d_avg_mm * 1e-3
    area_m2 = math.pi * (wire_mm / 2.0 * 1e-3) ** 2
    r_dc = RHO_CU_OHM_M * length_m / area_m2
    delta = skin_depth_mm(f_hz)
    f_skin = max(1.0, wire_mm / 2.0 / (2.0 * delta) + 0.25)
    return r_dc * f_skin * proximity_factor


def estimate_q(L_uH: float, esr_ohm: float, f_hz: float) -> float:
    return 2.0 * math.pi * f_hz * L_uH * 1e-6 / esr_ohm


@dataclass(frozen=True)
class PieceCoilDesign:
    piece: PieceType
    pitch_mm: float
    d_out_mm: float
    d_in_mm: float
    height_mm: float
    n_turns: int
    L_achieved_uH: float
    wire_mm: float | None  # largest candidate that fits, None if none fits
    window: WindowReport


def piece_coil_design(cfg: BoardConfig, piece: PieceType, pitch_mm: float) -> PieceCoilDesign:
    """Solve the piece resonator coil for L_target on this class diameter."""
    geo = resolve_geometry(cfg, pitch_mm).classes[piece]
    coil_cfg = cfg.resonator.coil
    sol = solve_turns(
        cfg.resonator.L_target_uH,
        geo.coil_d_out_mm,
        geo.coil_d_in_mm,
        height_mm=coil_cfg.height_mm,
    )
    chosen: float | None = None
    window: WindowReport | None = None
    for wire in sorted(coil_cfg.wire_candidates_mm, reverse=True):
        report = wire_window_check(
            sol.n_turns,
            geo.coil_d_out_mm,
            geo.coil_d_in_mm,
            coil_cfg.height_mm,
            wire,
            coil_cfg.fill_factor,
            coil_cfg.insulation_extra_mm,
        )
        if window is None:
            window = report  # keep the largest-wire report as fallback diagnostics
        if report.fits:
            chosen, window = wire, report
            break
    assert window is not None
    return PieceCoilDesign(
        piece=piece,
        pitch_mm=pitch_mm,
        d_out_mm=geo.coil_d_out_mm,
        d_in_mm=geo.coil_d_in_mm,
        height_mm=coil_cfg.height_mm,
        n_turns=sol.n_turns,
        L_achieved_uH=sol.L_achieved_uH,
        wire_mm=chosen,
        window=window,
    )


@dataclass(frozen=True)
class SenseCoilDesign:
    pitch_mm: float
    d_out_mm: float
    d_in_mm: float
    layers: int
    turns_per_layer: int
    turns_total: int
    track_width_mm: float
    L_uH: float
    esr_ohm: float
    srf_hz: float  # self-resonance against the mux off-capacitance


def pcb_sense_coil(cfg: BoardConfig, pitch_mm: float) -> SenseCoilDesign:
    """Design the 4-layer series square-cell sense spiral for its L target.

    The stacked layers are tightly coupled (board thickness is small
    against the diameter), so the whole stack is modeled as one Wheeler
    multilayer coil of height equal to the PCB thickness. Turns are
    rounded to a multiple of the layer count and spread evenly over the
    annulus, which fixes the track width.
    """
    sc = cfg.sense_coil
    geo = resolve_geometry(cfg, pitch_mm)
    d_out, d_in = geo.sense_d_out_mm, geo.sense_d_in_mm
    sol = solve_turns(sc.L_target_uH, d_out, d_in, height_mm=cfg.gap.pcb_mm)

    def stack_l(total: int) -> float:
        return wheeler_multilayer_L_uH(total, d_out, d_in, cfg.gap.pcb_mm)

    lower = max(sc.layers, (sol.n_turns // sc.layers) * sc.layers)
    upper = lower + sc.layers
    total = min((lower, upper), key=lambda n: abs(stack_l(n) - sc.L_target_uH))
    per_layer = total // sc.layers

    depth_mm = (d_out - d_in) / 2.0
    turn_pitch = depth_mm / per_layer
    track_width = turn_pitch - sc.track_gap_mm
    if track_width <= 0.0:
        raise ValueError("annulus too narrow for the solved turn count and track gap")

    d_avg = (d_out + d_in) / 2.0
    length_m = total * math.pi * d_avg * 1e-3
    esr = RHO_CU_OHM_M * length_m / (track_width * 1e-3 * sc.copper_um * 1e-6)
    l_uh = stack_l(total)
    srf = 1.0 / (2.0 * math.pi * math.sqrt(l_uh * 1e-6 * cfg.mux.c_off_pF * 1e-12))
    return SenseCoilDesign(
        pitch_mm=pitch_mm,
        d_out_mm=d_out,
        d_in_mm=d_in,
        layers=sc.layers,
        turns_per_layer=per_layer,
        turns_total=total,
        track_width_mm=track_width,
        L_uH=l_uh,
        esr_ohm=esr,
        srf_hz=srf,
    )
