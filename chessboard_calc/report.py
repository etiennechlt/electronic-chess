"""Resolved parameter tables: the living datasheet of the board.

Everything printed here is derived from config/board.yaml through the
calculation modules; nothing is hardcoded. The unit tests pin the same
outputs against the specification.
"""

from __future__ import annotations

from .config import BoardConfig, Color, PieceType, resolve_geometry
from .corridor import check_corridor
from .coupling import ringdown_signal, signal_vs_pitch
from .hall import amplitude_classes, hall_budget, hall_power, hall_scan
from .inductance import coil_esr_ohm, estimate_q, pcb_sense_coil, piece_coil_design
from .nfc import analog_mux_verdict, antenna, link, tag
from .power import autonomy_h, peak_current_a, peak_power_w, power_budget
from .resonance import check_separation, frequency_plan

_PIECE_LABEL = {
    PieceType.PAWN: "pawn",
    PieceType.KNIGHT: "knight",
    PieceType.BISHOP: "bishop",
    PieceType.ROOK: "rook",
    PieceType.QUEEN: "queen",
    PieceType.KING: "king",
}


def _table(header: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join(lines)


def _class_q_estimates(cfg: BoardConfig, piece: PieceType, pitch_mm: float) -> str:
    design = piece_coil_design(cfg, piece, pitch_mm)
    if design.wire_mm is None:
        return "no wire fits"
    plan = frequency_plan(cfg)
    d_avg = (design.d_out_mm + design.d_in_mm) / 2.0
    qs = []
    for color in (Color.BLACK, Color.WHITE):
        f = plan.line(piece, color).f0_hz
        esr = coil_esr_ohm(
            design.n_turns, d_avg, design.wire_mm, f, cfg.resonator.coil.proximity_factor
        )
        qs.append(estimate_q(design.L_achieved_uH, esr, f))
    return f"{qs[0]:.0f} / {qs[1]:.0f}"


def common_report(cfg: BoardConfig) -> str:
    out = ["# Derived parameters (pitch-independent)", ""]

    plan = frequency_plan(cfg)
    rows = [
        [
            _PIECE_LABEL[line.piece],
            line.color.value,
            f"{line.cap_nF:g}",
            f"{line.f0_hz / 1e3:.1f}",
            f"{line.width_nominal_hz / 1e3:.2f}",
            f"{line.width_min_q_hz / 1e3:.2f}",
            f"{line.tau_nominal_us:.0f}",
        ]
        for line in plan.lines
    ]
    out += [
        f"## Frequency plan (L = {cfg.resonator.L_target_uH:.0f} uH)",
        "",
        _table(
            ["piece", "color", "C (nF)", "f0 (kHz)",
             f"width Q{cfg.resonator.q_nominal:g} (kHz)",
             f"width Q{cfg.resonator.q_min_with_magnet:g} (kHz)", "tau (us)"],
            rows,
        ),
        "",
    ]

    for q in (cfg.resonator.q_nominal, cfg.resonator.q_min_with_magnet):
        rep = check_separation(cfg, q=q)
        worst = min(rep.gaps, key=lambda g: g.gap_widths)
        out.append(
            f"- separation at Q={q:g}: min {rep.min_gap_widths:.2f} widths "
            f"({_PIECE_LABEL[worst.lower.piece]} {worst.lower.color.value} / "
            f"{_PIECE_LABEL[worst.upper.piece]} {worst.upper.color.value}), "
            f"worst tolerance gap {rep.min_worst_case_gap_hz / 1e3:.1f} kHz, "
            f"ok={rep.ok}"
        )
    out.append("")

    for engine_on, label in ((False, "human vs human, Pi off"), (True, "against the engine")):
        budget = power_budget(cfg, engine_on)
        out.append(
            f"- power {label}: {budget.total_w:.2f} W "
            f"(loads {budget.load_sum_w:.2f} + fixed {budget.fixed_overhead_w:.2f} "
            f"+ proportional {budget.proportional_loss_w:.2f}), "
            f"autonomy {autonomy_h(cfg, engine_on):.1f} h"
        )
    out.append(
        f"- peak: {peak_power_w(cfg):.1f} W, {peak_current_a(cfg):.2f} A at nominal bus voltage"
    )
    out.append("")
    return "\n".join(out)


def pitch_report(cfg: BoardConfig, pitch_mm: float) -> str:
    geo = resolve_geometry(cfg, pitch_mm)
    out = [f"# Derived parameters for p = {pitch_mm:g} mm", ""]

    rows = []
    for piece in PieceType:
        cls = geo.classes[piece]
        design = piece_coil_design(cfg, piece, pitch_mm)
        wire = f"{design.wire_mm:g}" if design.wire_mm is not None else "NONE"
        rows.append(
            [
                _PIECE_LABEL[piece],
                f"{cls.base_mm:.1f}",
                f"{cls.coil_d_out_mm:.1f}",
                f"{cls.coil_d_in_mm:.1f}",
                f"{cls.magnet_d_mm:.1f}",
                f"{design.n_turns}",
                f"{design.L_achieved_uH:.1f}",
                wire,
                _class_q_estimates(cfg, piece, pitch_mm),
            ]
        )
    out += [
        "## Piece classes",
        "",
        _table(
            ["piece", "base (mm)", "coil od (mm)", "coil id (mm)", "magnet od (mm)",
             "turns", "L (uH)", "wire (mm)", "Q est. black/white"],
            rows,
        ),
        "",
        "Q estimates use the configured proximity factor "
        f"({cfg.resonator.coil.proximity_factor:g}); measurement 1 calibrates.",
        "",
    ]

    sense = pcb_sense_coil(cfg, pitch_mm)
    out += [
        "## Sense coil",
        "",
        f"- envelope {sense.d_out_mm:.1f} / {sense.d_in_mm:.1f} mm, {sense.layers} layers "
        f"x {sense.turns_per_layer} turns = {sense.turns_total} turns in series",
        f"- track width {sense.track_width_mm:.2f} mm, L = {sense.L_uH:.1f} uH, "
        f"ESR(DC) = {sense.esr_ohm:.2f} ohm",
        f"- SRF with mux off-capacitance: {sense.srf_hz / 1e6:.1f} MHz "
        f"({sense.srf_hz / cfg.measurement.band_hz[1]:.0f}x above band top)",
        "",
    ]

    corridor = check_corridor(cfg, pitch_mm)
    out += [
        "## Corridor",
        "",
        f"- worst pair {_PIECE_LABEL[corridor.worst.a]} + {_PIECE_LABEL[corridor.worst.b]}: "
        f"margin {corridor.worst.margin_mm:.2f} mm against a budget of "
        f"{corridor.budget_mm:g} mm, over {len(corridor.pairs)} pairs, ok={corridor.ok}",
        "",
        "## Gantry and gaps",
        "",
        f"- play area {geo.play_area_mm:.0f} mm, travels X x Y = "
        f"{geo.x_travel_mm:.0f} x {geo.y_travel_mm:.0f} mm",
        f"- air gap {geo.air_gap_mm:g} mm, total gap nominal {geo.gap_nominal_mm:g} mm, "
        f"max {geo.gap_max_mm:g} mm",
        "",
    ]

    est = ringdown_signal(cfg, PieceType.PAWN, Color.BLACK, pitch_mm)
    out += [
        "## Signal estimate (black pawn, worst case)",
        "",
        f"- k = {est.k:.3f}, M = {est.m_uH:.2f} uH, EMF after blanking "
        f"{est.emf_after_blanking_v * 1e3:.2f} mV, preamp out {est.preamp_out_v:.2f} V",
        f"- single-shot SNR {est.snr_db:.0f} dB, with x{cfg.measurement.coherent_avg} "
        f"averaging {est.snr_avg_db:.0f} dB (criterion >= {cfg.measurement.snr_min_db:g} dB)",
        "",
    ]
    out.append(hall_rfid_report(cfg, pitch_mm))
    return "\n".join(out)


def hall_rfid_report(cfg: BoardConfig, pitch_mm: float) -> str:
    """The Hall plus RFID alternative of note 24, numbers only."""
    hr = cfg.hall_rfid
    out = ["## Hall + RFID alternative (note 24)", ""]
    budget = hall_budget(cfg, pitch_mm)
    out += [
        f"Hall sensor {budget.sensor.part} at the square center, magnet face to Hall plate "
        f"{budget.z_nominal_mm:.1f} mm nominal, {budget.z_max_mm:.1f} mm at the maximum gap.",
        "",
    ]
    rows = []
    for piece in PieceType:
        f = budget.fields[piece]
        rows.append(
            [
                _PIECE_LABEL[piece],
                f"{f.magnet_d_mm:.1f} x {f.magnet_t_mm:g}",
                f"{f.b_nominal_mT:.1f}",
                f"{f.b_max_gap_mT:.1f}",
                f"{f.b_lifted_mT:.1f}",
                f"{f.b_neighbor_mT:.2f}",
                f"{f.out_nominal_mv:.0f} / {f.out_nominal_lsb:.0f}",
            ]
        )
    out += [
        _table(
            ["piece", "magnet (mm)", "B nominal (mT)", "B max gap (mT)",
             f"B lifted {hr.layout.lift_detect_mm:g} mm (mT)", "B next square (mT)",
             "out (mV / LSB)"],
            rows,
        ),
        "",
        f"- presence threshold {budget.threshold_mT:.1f} mT, release {budget.release_mT:.1f} mT: "
        f"lift margin {budget.lift_margin:.2f} (criterion >= {hr.presence.min_lift_margin:g}), "
        f"{hr.layout.neighbors_worst_case} surrounding kings {budget.neighbors_sum_mT:.2f} mT "
        f"({budget.crosstalk_db:.1f} dB of the weakest piece, criterion "
        f"<= {cfg.measurement.crosstalk_max_db:g} dB)",
        f"- weakest present swing {budget.weakest_present_lsb:.0f} LSB, "
        f"{budget.noise_margin:.0f}x the ADC noise; linear range ok={budget.in_linear_range}",
    ]
    for coded in (False, True):
        amp = amplitude_classes(cfg, pitch_mm, size_coded=coded)
        label = "size-coded thicknesses" if coded else "uniform magnets"
        spans = ", ".join(
            f"{'/'.join(_PIECE_LABEL[p] for p in c.pieces)} {c.magnet_t_mm:g} mm "
            f"[{c.b_low_mT:.0f}, {c.b_high_mT:.0f}] mT"
            for c in amp.classes
        )
        out.append(
            f"- amplitude classes, {label}: {amp.separable_groups} separable group(s) "
            f"({spans}), linear range ok={amp.in_linear_range}"
        )
    out.append("")
    rows = []
    for i, sensor in enumerate(hr.sensors):
        for gated in (False, True):
            hp = hall_power(cfg, gated, i)
            rows.append(
                [
                    sensor.part,
                    f"{hr.power_gating.groups} groups" if gated else "continuous",
                    f"{hp.current_ma:.0f}",
                    f"{hp.power_w:.2f}",
                    f"{hp.autonomy_h:.0f} (was {hp.autonomy_without_h:.0f})",
                ]
            )
    out += [_table(["sensor", "supply", "mA", "W", "autonomy h vs h (h)"], rows), ""]
    for gated in (False, True):
        sc = hall_scan(cfg, gated)
        out.append(
            f"- scan {'gated' if gated else 'continuous'}: {sc.square_us:.0f} us per square, "
            f"{sc.board_ms:.2f} ms per board, {sc.rate_hz:.0f} Hz"
        )
    ant = antenna(cfg, pitch_mm)
    tg = tag(cfg)
    near = link(cfg, pitch_mm)
    far = link(cfg, pitch_mm, cfg.gap.max_total_mm - cfg.gap.nominal_total_mm)
    mux = analog_mux_verdict(cfg, pitch_mm)
    out += [
        "",
        f"NFC at {hr.nfc.f_hz / 1e6:g} MHz: square loop {ant.side_mm:.0f} mm, {ant.turns} turns, "
        f"L = {ant.L_uH:.2f} uH, tuned by {ant.c_res_pF:.0f} pF, series R for "
        f"Q {hr.nfc.antenna.q_target:g} = {ant.r_series_ohm:.1f} ohm; tag {tg.part} "
        f"L = {tg.L_uH:.2f} uH, self-resonant at {tg.f_self_mhz:.1f} MHz.",
        f"- link at {near.z_mm:.1f} mm: k = {near.k:.2f}, H = {near.h_axis_a_per_m:.1f} A/m "
        f"({near.h_margin:.1f}x the ISO 14443 minimum); at the maximum gap k = {far.k:.2f}, "
        f"{far.h_margin:.1f}x",
        f"- {mux.switch} in the loop: Q {mux.q_with_switch:.2f}, parasitic "
        f"{mux.c_parasitic_pF:.0f} pF detunes by {mux.detune_pct:.0f} %, ok={mux.ok}",
        "",
    ]
    return "\n".join(out)


def full_report(cfg: BoardConfig, pitches_mm: list[float]) -> str:
    parts = [common_report(cfg)]
    parts += [pitch_report(cfg, p) for p in pitches_mm]
    ratio_note = _pitch_ratio_note(cfg)
    if ratio_note:
        parts.append(ratio_note)
    return "\n".join(parts)


def _pitch_ratio_note(cfg: BoardConfig) -> str:
    estimates = signal_vs_pitch(cfg)
    if len(estimates) < 2:
        return ""
    by_pitch = {e.pitch_mm: e for e in estimates}
    pitches = sorted(by_pitch)
    lo, hi = by_pitch[pitches[0]], by_pitch[pitches[-1]]
    ratio = lo.emf_after_blanking_v / hi.emf_after_blanking_v
    return (
        f"Signal ratio p={pitches[0]:g} over p={pitches[-1]:g} (black pawn, nominal gap): "
        f"{ratio:.2f}\n"
    )
