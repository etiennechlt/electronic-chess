"""Figures of the note 18 (the quality factor Q), computed from the model."""

from __future__ import annotations

import math

from chessboard_calc.config import BoardConfig, Color, PieceType
from chessboard_calc.coupling import coupling, pcb_sense_coil
from chessboard_calc.inductance import coil_esr_ohm, estimate_q, piece_coil_design
from chessboard_calc.resonance import (
    check_separation,
    frequency_plan,
    resonance_width_hz,
    ringdown_tau_us,
)

from .common import arrow_marker, esc, fr_num, lorentz, svg_open, text

# The brain firmware samples at 56.67 MHz / 15 cycles (firmware/board/src/adc.c);
# the yaml keeps a round 4 Msps for the signal estimates.
ADC_FS_FIRMWARE_HZ = 56.67e6 / 15.0

FR_PIECE = {
    "pawn": ("pion", "P", "♙", "♟"),
    "knight": ("cavalier", "C", "♘", "♞"),
    "bishop": ("fou", "F", "♗", "♝"),
    "rook": ("tour", "T", "♖", "♜"),
    "queen": ("dame", "D", "♕", "♛"),
    "king": ("roi", "R", "♔", "♚"),
}


def piece_name(piece: PieceType, color: Color) -> str:
    p = FR_PIECE[piece.value][0]
    if color is Color.WHITE:
        c = "blanche" if p in ("dame", "tour") else "blanc"
    else:
        c = "noire" if p in ("dame", "tour") else "noir"
    return f"{p} {c}"


def listen_window_us(cfg: BoardConfig) -> float:
    return cfg.measurement.fft_points / ADC_FS_FIRMWARE_HZ * 1e6


def fig_q_ringdown(cfg: BoardConfig) -> str:
    """Two damped rings at the black pawn note, Q nominal against Q = 10."""
    q_nom = cfg.resonator.q_nominal
    line = frequency_plan(cfg).line(PieceType.PAWN, Color.BLACK)
    f0 = line.f0_hz
    w, h = 900, 400
    x0, x1 = 70, 870
    t_max = 150.0
    px = (x1 - x0) / t_max
    amp = 68
    window = listen_window_us(cfg)
    panels = [(q_nom, 108, "q-high", "le diapason"), (10.0, 296, "q-low", "la boîte en carton")]
    listen_x = x0 + window * px
    out = [
        svg_open(
            w,
            h,
            f"Deux sonneries amorties a la meme note, Q = {q_nom:.0f} dure longtemps "
            "et Q = 10 s eteint presque aussitot",
        ),
        f"<defs>{arrow_marker('arr1', 7, both=True)}</defs>",
    ]
    for q, cy, cls, title in panels:
        tau = ringdown_tau_us(f0, q)
        out.append(
            f'<rect class="band" x="{x0}" y="{cy - amp - 12}" '
            f'width="{listen_x - x0:.1f}" height="{2 * amp + 24}"/>'
        )
        out.append(f'<line class="axis" x1="{x0}" y1="{cy}" x2="{x1}" y2="{cy}"/>')
        pts, env_hi, env_lo = [], [], []
        t = 0.0
        while t <= t_max:
            e = math.exp(-t / tau)
            y = cy - amp * e * math.sin(2 * math.pi * f0 * t * 1e-6)
            x = x0 + t * px
            pts.append(f"{x:.1f},{y:.1f}")
            env_hi.append(f"{x:.1f},{cy - amp * e:.1f}")
            env_lo.append(f"{x:.1f},{cy + amp * e:.1f}")
            t += 0.12
        out.append(f'<polyline class="env {cls}" points="{" ".join(env_hi[::4])}"/>')
        out.append(f'<polyline class="env {cls}" points="{" ".join(env_lo[::4])}"/>')
        out.append(f'<polyline class="trace {cls}" points="{" ".join(pts)}"/>')
        xt = x0 + tau * px
        out.append(
            f'<line class="mark {cls}" x1="{xt:.1f}" y1="{cy - amp - 8}" '
            f'x2="{xt:.1f}" y2="{cy + amp + 8}"/>'
        )
        n_osc = q / math.pi
        out.append(
            text(
                xt + 8,
                cy - amp - 14,
                f"τ = {fr_num(tau, 0)} µs : il reste 37 %, après ≈ {n_osc:.0f} oscillations",
            )
        )
        out.append(text(x0, cy - amp - 30, f"Q = {q:.0f} : {title}", "title"))
    out.append(
        text(
            listen_x - 6,
            panels[0][1] + amp + 8,
            f"fenêtre d'écoute {fr_num(window, 0)} µs",
            "lbl muted",
            "end",
        )
    )
    ya = h - 22
    out.append(
        f'<line class="axis" x1="{x0}" y1="{ya}" x2="{x1}" y2="{ya}" marker-end="url(#arr1)"/>'
    )
    for tt in range(0, 151, 25):
        xx = x0 + tt * px
        out.append(f'<line class="tick" x1="{xx:.1f}" y1="{ya}" x2="{xx:.1f}" y2="{ya + 5}"/>')
        out.append(text(xx, ya + 18, str(tt), "lbl mono", "middle"))
    out.append(text(x1, ya - 8, "temps en µs après la frappe", "lbl muted", "end"))
    out.append("</svg>")
    return "\n".join(out)


def fig_q_width(cfg: BoardConfig) -> str:
    """Resonance curve of the white pawn at Q nominal and Q = 10, with its neighbour."""
    q_nom = cfg.resonator.q_nominal
    plan = frequency_plan(cfg)
    pawn = plan.line(PieceType.PAWN, Color.WHITE)
    knight = plan.line(PieceType.KNIGHT, Color.WHITE)
    f0 = pawn.f0_hz / 1e3
    fn = knight.f0_hz / 1e3
    w, h = 900, 360
    x0, x1 = 70, 860
    fa, fb = 330.0, 470.0
    px = (x1 - x0) / (fb - fa)
    yb, yt = 290, 50
    span = yb - yt
    out = [
        svg_open(
            w,
            h,
            f"Courbe de resonance du pion blanc a {f0:.0f} kHz pour Q = {q_nom:.0f} et Q = 10, "
            f"avec la note voisine du cavalier blanc a {fn:.0f} kHz",
        ),
        f"<defs>{arrow_marker('arr2', 6, both=True)}</defs>",
    ]
    for k, lab in ((0.0, "0"), (0.5, "50 %"), (1.0, "100 %")):
        y = yb - span * k
        out.append(f'<line class="grid" x1="{x0}" y1="{y:.1f}" x2="{x1}" y2="{y:.1f}"/>')
        out.append(text(x0 - 8, y + 4, lab, "lbl mono", "end"))
    for ff in range(340, 461, 20):
        xx = x0 + (ff - fa) * px
        out.append(f'<line class="tick" x1="{xx:.1f}" y1="{yb}" x2="{xx:.1f}" y2="{yb + 5}"/>')
        out.append(text(xx, yb + 20, str(ff), "lbl mono", "middle"))
    out.append(f'<line class="axis" x1="{x0}" y1="{yb}" x2="{x1}" y2="{yb}"/>')
    out.append(text(x1, yb + 38, "fréquence en kHz", "lbl muted", "end"))
    out.append(
        text(
            x0,
            yt - 22,
            "réponse de la pièce à une excitation, en % du maximum",
            "lbl muted",
        )
    )

    def curve(center: float, q: float, cls: str, ghost: bool = False) -> str:
        pts = []
        f = fa
        while f <= fb:
            y = yb - span * lorentz(f, center, q)
            pts.append(f"{x0 + (f - fa) * px:.1f},{y:.1f}")
            f += 0.25
        g = " ghost" if ghost else ""
        return f'<polyline class="trace {cls}{g}" points="{" ".join(pts)}"/>'

    out.append(curve(fn, 10, "q-low", ghost=True))
    out.append(curve(fn, q_nom, "q-high", ghost=True))
    out.append(curve(f0, 10, "q-low"))
    out.append(curve(f0, q_nom, "q-high"))
    yh = yb - span * math.sqrt(0.5)
    out.append(f'<line class="dash" x1="{x0}" y1="{yh:.1f}" x2="{x1}" y2="{yh:.1f}"/>')
    out.append(
        text(x1, yh - 6, "70,7 % : mi-puissance, là où se lit la largeur", "lbl muted", "end")
    )
    w_hi = resonance_width_hz(pawn.f0_hz, q_nom) / 1e3
    w_lo = resonance_width_hz(pawn.f0_hz, 10) / 1e3
    for width, cls, dy, ty, q_s in (
        (w_hi, "q-high", -14, -22, f"{q_nom:.0f}"),
        (w_lo, "q-low", 14, 30, "10"),
    ):
        xa = x0 + (f0 - width / 2 - fa) * px
        xb = x0 + (f0 + width / 2 - fa) * px
        y = yh + dy
        out.append(
            f'<line class="mark {cls}" x1="{xa:.1f}" y1="{y:.1f}" x2="{xb:.1f}" y2="{y:.1f}" '
            'marker-start="url(#arr2)" marker-end="url(#arr2)"/>'
        )
        anchor = "start" if cls == "q-low" else "middle"
        xl = (xa + xb) / 2 if cls == "q-high" else xb + 8
        out.append(
            text(xl, yh + ty, f"largeur {fr_num(width)} kHz à Q = {q_s}", f"lbl {cls}-t", anchor)
        )
    xn = x0 + (fn - fa) * px
    out.append(f'<line class="dash" x1="{xn:.1f}" y1="{yt}" x2="{xn:.1f}" y2="{yb}"/>')
    out.append(text(xn + 6, yt + 2, f"voisin : cavalier blanc, {fn:.0f} kHz"))
    out.append(text(xn + 6, yt + 18, f"à {fn - f0:.0f} kHz de distance", "lbl muted"))
    xp = x0 + (f0 - fa) * px
    out.append(text(xp, yt - 4, f"pion blanc, {f0:.0f} kHz", "lbl", "middle"))
    out.append("</svg>")
    return "\n".join(out)


def plan_rows(cfg: BoardConfig) -> list[dict[str, str]]:
    """The twelve classes as display strings, for tables and tooltips."""
    plan = frequency_plan(cfg)
    rows = []
    for line in plan.lines:
        name = FR_PIECE[line.piece.value]
        glyph = name[3] if line.color is Color.BLACK else name[2]
        rows.append(
            {
                "glyph": glyph,
                "letter": name[1],
                "name": piece_name(line.piece, line.color),
                "cap": fr_num(line.cap_nF),
                "f0": fr_num(line.f0_hz / 1e3),
                "w50": fr_num(line.width_nominal_hz / 1e3),
                "w30": fr_num(line.width_min_q_hz / 1e3),
                "tau": fr_num(line.tau_nominal_us, 0),
            }
        )
    return rows


def fig_q_plan(cfg: BoardConfig, interactive: bool = False) -> str:
    """The twelve notes with their line width at the accepted floor Q."""
    q_min = cfg.resonator.q_min_with_magnet
    q_nom = cfg.resonator.q_nominal
    plan = frequency_plan(cfg)
    sep = check_separation(cfg, q_min)
    w, h = 960, 350
    x0, x1 = 50, 930
    fa, fb = 180.0, 660.0
    px = (x1 - x0) / (fb - fa)
    yb, yt = 250, 80
    span = yb - yt
    lo = plan.lines[0].f0_hz / 1e3
    hi = plan.lines[-1].f0_hz / 1e3
    out = [
        svg_open(
            w,
            h,
            f"Les douze notes des pieces entre {lo:.0f} et {hi:.0f} kHz, chacune dessinee "
            f"avec sa largeur de raie a Q = {q_min:.0f}",
        )
    ]
    for ff in range(200, 661, 100):
        xx = x0 + (ff - fa) * px
        out.append(f'<line class="tick" x1="{xx:.1f}" y1="{yb}" x2="{xx:.1f}" y2="{yb + 5}"/>')
        out.append(text(xx, yb + 60, f"{ff} kHz", "lbl mono", "middle"))
    out.append(f'<line class="axis" x1="{x0}" y1="{yb}" x2="{x1}" y2="{yb}"/>')
    for i, line in enumerate(plan.lines):
        f0 = line.f0_hz / 1e3
        w30 = line.width_min_q_hz / 1e3
        name = FR_PIECE[line.piece.value]
        black = line.color is Color.BLACK
        glyph = name[3] if black else name[2]
        pts = [f"{x0 + (f0 - 5 * w30 - fa) * px:.1f},{yb}"]
        f = f0 - 5 * w30
        while f <= f0 + 5 * w30:
            y = yb - span * lorentz(f, f0, q_min)
            pts.append(f"{x0 + (f - fa) * px:.1f},{y:.1f}")
            f += w30 / 12
        pts.append(f"{x0 + (f0 + 5 * w30 - fa) * px:.1f},{yb}")
        cls = "peak-black" if black else "peak-white"
        label = piece_name(line.piece, line.color)
        tip = (
            f"<b>{label}</b><br>condensateur {fr_num(line.cap_nF)} nF, f0 = {fr_num(f0)} kHz"
            f"<br>largeur {fr_num(w30)} kHz à Q = {q_min:.0f}, "
            f"{fr_num(line.width_nominal_hz / 1e3)} kHz à Q = {q_nom:.0f}"
            f"<br>τ = {fr_num(line.tau_nominal_us, 0)} µs à Q = {q_nom:.0f}"
        )
        data = f' data-html="{esc(tip)}"' if interactive else ""
        out.append(f'<g class="peak"{data}>')
        out.append(f'<polygon class="{cls}" points="{" ".join(pts)}"/>')
        xc = x0 + (f0 - fa) * px
        out.append(text(xc, yt - 26, glyph, "lbl glyph", "middle"))
        out.append(text(xc, yt - 8, name[1], "lbl mono", "middle"))
        yf = yb + 20 if i % 2 == 0 else yb + 36
        out.append(text(xc, yf, f"{f0:.0f}", "lbl mono small", "middle"))
        out.append("</g>")
    a = plan.line(PieceType.PAWN, Color.WHITE)
    b = plan.line(PieceType.KNIGHT, Color.WHITE)
    xa = x0 + (a.f0_hz / 1e3 - fa) * px
    xb = x0 + (b.f0_hz / 1e3 - fa) * px
    yk = 26
    out.append(f'<path class="brk" d="M{xa:.1f} {yk + 8}v-8H{xb:.1f}v8"/>')
    gap = (b.f0_hz - a.f0_hz) / 1e3
    out.append(
        text(
            (xa + xb) / 2,
            yk - 6,
            f"paire la plus serrée : {gap:.0f} kHz, soit "
            f"{fr_num(sep.min_gap_widths)} largeurs à Q = {q_min:.0f}",
            "lbl",
            "middle",
        )
    )
    out.append(f'<rect class="peak-black" x="{x0}" y="{h - 30}" width="14" height="12"/>')
    out.append(text(x0 + 20, h - 19, "pièces noires (pleines)"))
    out.append(f'<rect class="peak-white" x="{x0 + 190}" y="{h - 30}" width="14" height="12"/>')
    out.append(
        text(
            x0 + 210,
            h - 19,
            "pièces blanches (creuses), la convention des diagrammes d'échecs",
        )
    )
    out.append("</svg>")
    return "\n".join(out)


def q_curve(cfg: BoardConfig, f_max_khz: float = 700.0) -> tuple[list[float], list[float]]:
    """Estimated Q of the pawn coil against frequency, 5 kHz steps."""
    design = piece_coil_design(cfg, PieceType.PAWN, cfg.pitch.plateau_mm)
    d_avg = (design.d_out_mm + design.d_in_mm) / 2
    pf = cfg.resonator.coil.proximity_factor
    fs, qs = [], []
    f = 10e3
    while f <= f_max_khz * 1e3 + 1:
        esr = coil_esr_ohm(design.n_turns, d_avg, design.wire_mm, f, pf)
        fs.append(f / 1e3)
        qs.append(estimate_q(design.L_achieved_uH, esr, f))
        f += 5e3
    return fs, qs


def q_at(cfg: BoardConfig, f_hz: float) -> float:
    design = piece_coil_design(cfg, PieceType.PAWN, cfg.pitch.plateau_mm)
    d_avg = (design.d_out_mm + design.d_in_mm) / 2
    esr = coil_esr_ohm(
        design.n_turns, d_avg, design.wire_mm, f_hz, cfg.resonator.coil.proximity_factor
    )
    return estimate_q(design.L_achieved_uH, esr, f_hz)


def fig_q_vs_frequency(cfg: BoardConfig, interactive: bool = False) -> str:
    """Q of the pawn coil against frequency, the measurement band highlighted."""
    fs, qs = q_curve(cfg)
    q_min = cfg.resonator.q_min_with_magnet
    band = cfg.measurement.band_hz
    plan = frequency_plan(cfg)
    pb = plan.line(PieceType.PAWN, Color.BLACK).f0_hz
    pw = plan.line(PieceType.PAWN, Color.WHITE).f0_hz
    w, h = 900, 340
    x0, x1 = 70, 860
    fa, fb = 0.0, 700.0
    px = (x1 - x0) / (fb - fa)
    yb, yt = 280, 50
    qmax = 120.0
    py = (yb - yt) / qmax
    extra = 'id="qsvg"' if interactive else ""
    out = [
        svg_open(
            w,
            h,
            "Q estime de la bobine du pion en fonction de la frequence, il monte de "
            f"{q_at(cfg, 40e3):.0f} a 40 kHz jusqu au dela de 80 a 600 kHz, la bande de mesure "
            f"{band[0] / 1e3:.0f} a {band[1] / 1e3:.0f} kHz est en surbrillance",
            extra,
        )
    ]
    bx0 = x0 + (band[0] / 1e3 - fa) * px
    bx1 = x0 + (band[1] / 1e3 - fa) * px
    out.append(
        f'<rect class="band" x="{bx0:.1f}" y="{yt - 10}" width="{bx1 - bx0:.1f}" '
        f'height="{yb - yt + 10}"/>'
    )
    out.append(
        text(
            (bx0 + bx1) / 2,
            yt - 18,
            f"bande de mesure de l'échiquier : {band[0] / 1e3:.0f} à {band[1] / 1e3:.0f} kHz",
            "lbl muted",
            "middle",
        )
    )
    for qq in range(0, 121, 30):
        y = yb - qq * py
        out.append(f'<line class="grid" x1="{x0}" y1="{y:.1f}" x2="{x1}" y2="{y:.1f}"/>')
        out.append(text(x0 - 8, y + 4, str(qq), "lbl mono", "end"))
    for ff in range(0, 701, 100):
        xx = x0 + (ff - fa) * px
        out.append(f'<line class="tick" x1="{xx:.1f}" y1="{yb}" x2="{xx:.1f}" y2="{yb + 5}"/>')
        out.append(text(xx, yb + 20, str(ff), "lbl mono", "middle"))
    out.append(f'<line class="axis" x1="{x0}" y1="{yb}" x2="{x1}" y2="{yb}"/>')
    out.append(text(x1, yb + 38, "fréquence en kHz", "lbl muted", "end"))
    out.append(text(x0 - 8, yt - 18, "Q", "lbl muted", "end"))
    yq = yb - q_min * py
    out.append(f'<line class="dash" x1="{x0}" y1="{yq:.1f}" x2="{x1}" y2="{yq:.1f}"/>')
    out.append(
        text(
            x1 - 6,
            yq - 6,
            f"plancher accepté avec l'aimant posé : Q = {q_min:.0f}",
            "lbl muted",
            "end",
        )
    )
    pts = [
        f"{x0 + (f - fa) * px:.1f},{yb - min(q, qmax) * py:.1f}"
        for f, q in zip(fs, qs, strict=True)
    ]
    out.append(f'<polyline class="trace q-high" points="{" ".join(pts)}"/>')
    marks = (
        (40e3, f"à 40 kHz : Q ≈ {q_at(cfg, 40e3):.0f}"),
        (pb, f"pion noir, {pb / 1e3:.0f} kHz : Q ≈ {q_at(cfg, pb):.0f}"),
        (pw, f"pion blanc, {pw / 1e3:.0f} kHz : Q ≈ {q_at(cfg, pw):.0f}"),
    )
    for f_hz, label in marks:
        xx = x0 + (f_hz / 1e3 - fa) * px
        yy = yb - q_at(cfg, f_hz) * py
        out.append(f'<circle class="dot q-high" cx="{xx:.1f}" cy="{yy:.1f}" r="5"/>')
        out.append(text(xx + 10, yy - 10, label))
    if interactive:
        out.append(
            f'<g id="xh" hidden><line class="dash" x1="0" y1="{yt - 10}" x2="0" y2="{yb}"/>'
            '<circle class="dot q-high" r="5"/>'
            '<rect class="tipbox" width="150" height="22" rx="4"/>'
            '<text class="lbl mono" x="0" y="0"></text></g>'
        )
    out.append("</svg>")
    return "\n".join(out)


def fig_q_stack(cfg: BoardConfig) -> str:
    """Vertical cut under a pawn: piece coil, felt, plywood, air, board spiral."""
    scale = 16.0
    w, h = 900, 340
    cx = 450
    gap = cfg.gap
    y_pcb_bot = 300
    h_pcb, h_air = gap.pcb_mm * scale, gap.air_mm * scale
    h_wood, h_felt = gap.surface_mm * scale, gap.felt_mm * scale
    y_pcb_top = y_pcb_bot - h_pcb
    y_air_top = y_pcb_top - h_air
    y_wood_top = y_air_top - h_wood
    y_felt_top = y_wood_top - h_felt
    design = piece_coil_design(cfg, PieceType.PAWN, cfg.pitch.plateau_mm)
    sense = pcb_sense_coil(cfg, cfg.pitch.plateau_mm)
    cpl = coupling(cfg, PieceType.PAWN, cfg.pitch.plateau_mm, gap.air_gap_mm)
    base_mm = design.d_out_mm + cfg.resonator.coil.outer_margin_mm
    base_w = base_mm * scale
    base_h = 8.0 * scale
    y_base_bot = y_felt_top
    y_base_top = y_base_bot - base_h
    out = [
        svg_open(
            w,
            h,
            "Coupe verticale : la bobine plate dans la base de la piece, le feutre, le "
            "contreplaque, la lame d air, puis la spirale de la case dans le circuit imprime, "
            f"{gap.nominal_total_mm:.1f} mm en tout",
        ),
        "<defs>"
        + arrow_marker("arr5")
        + '<pattern id="wire" width="6" height="6" patternUnits="userSpaceOnUse" '
        'patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="6" '
        'stroke="currentColor" stroke-width="1.6"/></pattern></defs>',
    ]
    layers = [
        (
            y_pcb_top,
            h_pcb,
            "lay-pcb",
            f"circuit imprimé {fr_num(gap.pcb_mm)} mm, spirale de la case sur "
            f"{sense.layers} couches",
        ),
        (y_air_top, h_air, "lay-air", f"air {fr_num(gap.air_mm)} mm (LED et bande de frontal)"),
        (y_wood_top, h_wood, "lay-wood", f"contreplaqué {fr_num(gap.surface_mm)} mm"),
        (y_felt_top, h_felt, "lay-felt", f"feutre {fr_num(gap.felt_mm)} mm"),
    ]
    for y, hh, cls, _label in layers:
        out.append(f'<rect class="{cls}" x="60" y="{y:.1f}" width="780" height="{hh:.1f}"/>')
    turns = sense.turns_per_layer
    r_in = sense.d_in_mm / 2 * scale
    r_out = sense.d_out_mm / 2 * scale
    pitch_t = (r_out - r_in) / turns
    tw = sense.track_width_mm * scale
    for li in range(sense.layers):
        y = y_pcb_top + 3 + li * (h_pcb - 6) / (sense.layers - 1) - 1.5
        for i in range(turns):
            xr = cx + r_in + i * pitch_t
            xl = cx - r_in - i * pitch_t - tw
            out.append(
                f'<rect class="copper" x="{xl:.1f}" y="{y:.1f}" width="{tw:.1f}" height="3"/>'
            )
            out.append(
                f'<rect class="copper" x="{xr:.1f}" y="{y:.1f}" width="{tw:.1f}" height="3"/>'
            )
    out.append(
        f'<path class="piece" d="M{cx - base_w / 2:.1f} {y_base_bot:.1f} v-{base_h - 14:.1f} '
        f'q0 -14 14 -14 h{base_w - 28:.1f} q14 0 14 14 v{base_h - 14:.1f} z"/>'
    )
    out.append(f'<path class="piece" d="M{cx - 34} {y_base_top:.1f} q34 -30 68 0 z"/>')
    c_od = design.d_out_mm * scale
    c_id = design.d_in_mm * scale
    c_h = cfg.resonator.coil.height_mm * scale
    yb_coil = y_base_bot - 4
    bundle_w = (c_od - c_id) / 2
    for xb in (cx - c_od / 2, cx + c_id / 2):
        out.append(
            f'<rect class="bundle" x="{xb:.1f}" y="{yb_coil - c_h:.1f}" '
            f'width="{bundle_w:.1f}" height="{c_h:.1f}"/>'
        )
    out.append(
        f'<rect class="cap" x="{cx - 12}" y="{yb_coil - c_h + 8:.1f}" '
        'width="24" height="12" rx="2"/>'
    )
    m_d = (base_mm - cfg.piece_magnet.outer_margin_mm) * scale
    m_h = cfg.piece_magnet.thickness_mm * scale
    y_mag_bot = yb_coil - c_h - 6
    out.append(
        f'<rect class="magnet" x="{cx - m_d / 2:.1f}" y="{y_mag_bot - m_h:.1f}" '
        f'width="{m_d:.1f}" height="{m_h:.1f}" rx="3"/>'
    )
    out.append(text(cx, y_mag_bot - m_h / 2 + 4, "aimant ferrite (isolant)", "lbl", "middle"))
    for dx in (-52, 0, 52):
        out.append(
            f'<path class="field" d="M{cx + dx} {y_pcb_top + 2:.1f} C{cx + dx * 2.2:.1f} '
            f"{y_air_top:.1f}, {cx + dx * 2.2:.1f} {y_wood_top:.1f}, {cx + dx} "
            f'{yb_coil - c_h - 2:.1f}" marker-end="url(#arr5)"/>'
        )
    for y, hh, _cls, label in layers:
        out.append(text(66, y + hh / 2 + 4, label))
    y_coil = yb_coil - c_h / 2 + 4
    out.append(
        text(
            cx - base_w / 2 - 8,
            y_coil,
            f"bobine {fr_num(cfg.resonator.L_target_uH, 0)} µH, {design.n_turns} tours",
            "lbl",
            "end",
        )
    )
    out.append(text(cx + base_w / 2 + 8, y_coil, "condensateur C0G au centre"))
    out.append(text(cx + 100, y_air_top - 4, "champ magnétique partagé", "lbl q-high-t"))
    out.append(
        text(cx + 100, y_air_top + 12, f"k ≈ {fr_num(cpl.k, 2)} : un huitième du flux", "lbl muted")
    )
    xg = 852
    out.append(
        f'<line class="mark" x1="{xg}" y1="{y_felt_top:.1f}" x2="{xg}" y2="{y_pcb_bot}" '
        'marker-start="url(#arr5)" marker-end="url(#arr5)"/>'
    )
    ym = (y_felt_top + y_pcb_bot) / 2
    out.append(text(xg - 6, ym - 4, f"{fr_num(gap.nominal_total_mm)} mm", "lbl", "end"))
    out.append(text(xg - 6, ym + 12, "en tout", "lbl muted", "end"))
    out.append(
        text(
            60,
            y_base_top - 6,
            f"base d'un pion, {fr_num(base_mm)} mm de diamètre ; épaisseurs de cuivre exagérées",
            "lbl muted",
        )
    )
    out.append("</svg>")
    return "\n".join(out)


def fig_q_timeline(cfg: BoardConfig) -> str:
    """One measurement: address, release, pulse, flyback, blanking, listen."""
    window = listen_window_us(cfg)
    n = cfg.measurement.fft_points
    fs_m = fr_num(ADC_FS_FIRMWARE_HZ / 1e6, 2)
    w, h = 960, 300
    segs = [
        ("adresser", "2 µs", 90, "seg"),
        ("relâcher", "0,3 µs", 70, "seg"),
        ("frapper", f"{fr_num(cfg.measurement.drive.pulse_us)} µs", 90, "seg-pulse"),
        ("roue libre", "0,4 µs", 80, "seg"),
        ("blanking", f"{fr_num(cfg.measurement.blanking_us)} µs", 100, "seg"),
        ("écouter", f"{fr_num(window, 0)} µs", 450, "seg-listen"),
    ]
    out = [
        svg_open(
            w,
            h,
            "Sequence d une mesure : adresser, relacher, frapper, roue libre, blanking, "
            f"ecouter {window:.0f} microsecondes, avec l allure de la tension sur la spirale",
        )
    ]
    x = 40
    y0, hb = 34, 34
    bounds = []
    for name, dur, sw, cls in segs:
        out.append(f'<rect class="{cls}" x="{x}" y="{y0}" width="{sw - 3}" height="{hb}" rx="3"/>')
        out.append(text(x + (sw - 3) / 2, y0 + 15, name, "lbl", "middle"))
        out.append(text(x + (sw - 3) / 2, y0 + 28, dur, "lbl mono small", "middle"))
        bounds.append((x, x + sw - 3))
        x += sw
    out.append(text(40, y0 - 12, "durées réelles, largeurs non proportionnelles", "lbl muted"))
    ym = 190
    out.append(f'<line class="axis" x1="40" y1="{ym}" x2="{x - 3}" y2="{ym}"/>')
    pts = [f"{bounds[0][0]},{ym}", f"{bounds[1][1]},{ym}"]
    xa, xb = bounds[2]
    pts += [f"{xa + 4},{ym - 78}", f"{xb - 4},{ym - 78}"]
    xa, xb = bounds[3]
    pts += [f"{xa + 2},{ym + 70}", f"{xa + 20},{ym + 30}", f"{xb - 4},{ym + 4}"]
    xa, xb = bounds[4]
    for i in range(61):
        t = i / 60
        y = ym - 40 * math.exp(-4.5 * t) * math.sin(2 * math.pi * 7 * t)
        pts.append(f"{xa + t * (xb - xa):.1f},{y:.1f}")
    xa, xb = bounds[5]
    for i in range(901):
        t = i / 900
        y = ym - 52 * math.exp(-2.2 * t) * math.sin(2 * math.pi * 26 * t)
        pts.append(f"{xa + t * (xb - xa):.1f},{y:.1f}")
    out.append(f'<polyline class="trace q-high" points="{" ".join(pts)}"/>')
    out.append(
        text(
            40,
            ym + 92,
            "tension aux bornes de la spirale de la case, allure seulement",
            "lbl muted",
        )
    )
    xa, xb = bounds[2]
    drive = cfg.measurement.drive
    out.append(
        text(
            (xa + xb) / 2, ym - 88, f"{fr_num(drive.v, 0)} V, environ 1 A", "lbl q-low-t", "middle"
        )
    )
    xa, xb = bounds[4]
    out.append(text((xa + xb) / 2, ym + 60, "la case sonne,", "lbl", "middle"))
    out.append(text((xa + xb) / 2, ym + 74, "on l'étouffe", "lbl", "middle"))
    xa, xb = bounds[5]
    out.append(
        text(
            (xa + xb) / 2,
            ym - 68,
            f"la pièce sonne : c'est ce qu'on mesure, {n} échantillons à {fs_m} Méch/s",
            "lbl q-high-t",
            "middle",
        )
    )
    out.append("</svg>")
    return "\n".join(out)


def fig_q_chain(cfg: BoardConfig) -> str:
    """From the piece to the result, eight boxes."""
    sense = pcb_sense_coil(cfg, cfg.pitch.plateau_mm)
    band = cfg.measurement.band_hz
    w, h = 980, 140
    boxes = [
        ("pièce", f"bobine {fr_num(cfg.resonator.L_target_uH, 0)} µH", "et son C0G"),
        ("spirale de la case", f"{fr_num(sense.L_uH, 0)} µH", f"{sense.turns_total} tours"),
        ("aiguilleur", "une case", "à la fois"),
        ("amplificateur", "gain ≈ 230", ""),
        ("filtre", f"{band[0] / 1e3:.0f} à {band[1] / 1e3:.0f} kHz", ""),
        (
            "convertisseur",
            f"{cfg.measurement.fft_points} points",
            f"{fr_num(ADC_FS_FIRMWARE_HZ / 1e6, 2)} Méch/s",
        ),
        ("calcul", "FFT ou comptage", "des périodes"),
        ("résultat", "f0 à 1 kHz près,", "donc la pièce"),
    ]
    out = [
        svg_open(w, h, "Chaine de mesure de la piece au resultat en huit etapes"),
        f"<defs>{arrow_marker('arr7')}</defs>",
    ]
    bw, gap, x = 110, 12, 8
    yb, hb = 30, 72
    for i, (t1, t2, t3) in enumerate(boxes):
        cls = "box box-piece" if i == 0 else "box"
        out.append(f'<rect class="{cls}" x="{x}" y="{yb}" width="{bw}" height="{hb}" rx="6"/>')
        out.append(text(x + bw / 2, yb + 24, t1, "lbl strong", "middle"))
        out.append(text(x + bw / 2, yb + 44, t2, "lbl small", "middle"))
        out.append(text(x + bw / 2, yb + 60, t3, "lbl small", "middle"))
        if i == 0:
            for dx in (1, 7):
                out.append(
                    f'<path class="field" d="M{x + bw + dx} {yb + 28} q7 8 0 16 q-7 8 0 16"/>'
                )
        elif i < len(boxes) - 1:
            out.append(
                f'<line class="axis" x1="{x + bw + 1}" y1="{yb + hb / 2}" '
                f'x2="{x + bw + gap - 1}" y2="{yb + hb / 2}" marker-end="url(#arr7)"/>'
            )
        x += bw + gap
    out.append(
        text(
            8,
            yb + hb + 24,
            "entre la pièce et la spirale : pas de fil, seulement le champ magnétique "
            "à travers le bois",
            "lbl muted",
        )
    )
    out.append("</svg>")
    return "\n".join(out)
