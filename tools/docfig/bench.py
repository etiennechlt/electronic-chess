"""Figures of the note 19: the brain board, its scan cycle, the Nucleo bench."""

from __future__ import annotations

from chessboard_calc.config import BoardConfig
from chessboard_calc.resonance import frequency_plan

from .common import arrow_marker, fr_num, svg_open, text
from .q import FR_PIECE, listen_window_us


def _box(x: float, y: float, w: float, h: float, lines: list[str], cls: str = "box") -> str:
    """A rounded box with centred text lines, the first one in bold."""
    out = [f'<rect class="{cls}" x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="6"/>']
    n = len(lines)
    step = 15
    y0 = y + h / 2 - (n - 1) * step / 2 + 4
    for i, s in enumerate(lines):
        c = "lbl strong" if i == 0 else "lbl small"
        out.append(text(x + w / 2, y0 + i * step, s, c, "middle"))
    return "\n".join(out)


def _arrow(x1: float, y1: float, x2: float, y2: float, marker: str, cls: str = "wire") -> str:
    return (
        f'<line class="{cls}" x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'marker-end="url(#{marker})"/>'
    )


def _path(d: str, marker: str, cls: str = "wire") -> str:
    return f'<path class="{cls}" d="{d}" marker-end="url(#{marker})"/>'


def fig_brain_blocks(cfg: BoardConfig) -> str:
    """What sits on the brain board and what talks to what."""
    w, h = 960, 640
    bat = cfg.power.battery
    out = [
        svg_open(
            w,
            h,
            "Schema bloc de la carte cerveau : alimentation en haut, microcontroleur au "
            "centre, quatre nappes de quadrant a gauche, radio et liaisons a droite, "
            "interface humaine et connecteurs en bas",
        ),
        f"<defs>{arrow_marker('arr8')}{arrow_marker('arr8b', both=True)}</defs>",
    ]
    # power row
    out.append(text(20, 22, "ALIMENTATION", "lbl mono muted"))
    out.append(
        _box(
            20,
            34,
            170,
            62,
            [
                f"VBAT {fr_num(bat.v_range[0])} à {fr_num(bat.v_range[1])} V",
                "depuis la carte puissance (J10)",
                "fusible 2 A",
            ],
        )
    )
    rails = [
        (215, "buck 5 V", "TPS62130, PWM forcé", "logique, LED, buzzer"),
        (400, "LDO 3,3 V", "AP2112K", "MCU et décodeurs"),
        (585, "LDO 5VA analogique", "LP2985 et perle de ferrite", "îlot propre des frontaux"),
        (770, "VIN 12 V impulsions", "fusible 1 A, 100 µF", "rail d'excitation des cases"),
    ]
    for x, t1, t2, t3 in rails:
        out.append(_box(x, 34, 170, 62, [t1, t2, t3], "box-soft"))
    out.append(_arrow(190, 65, 213, 65, "arr8"))
    out.append(_arrow(385, 65, 398, 65, "arr8"))
    out.append(_path("M190 80 H200 V110 H580 V96", "arr8"))
    out.append(_path("M200 110 H765 V96", "arr8"))
    out.append(
        text(
            420,
            124,
            "le 5 V descend vers les LED des quadrants par un second fusible",
            "lbl muted small",
        )
    )

    # MCU
    mx, my, mw, mh = 330, 250, 300, 160
    out.append(
        _box(
            mx,
            my,
            mw,
            mh,
            [
                f"{cfg.mcu.part}, {cfg.mcu.sysclk_mhz:.0f} MHz, sans quartz",
                "quatre convertisseurs, un par quadrant",
                "FFT et capture de période",
                "calibration des 64 cases en flash",
                "arbitre de la partie (à écrire)",
            ],
            "box-mcu",
        )
    )
    # quadrant links
    out.append(text(20, 160, "QUADRANTS", "lbl mono muted"))
    qy = [172, 256, 340, 424]
    for k, y in enumerate(qy, start=1):
        out.append(
            _box(
                20,
                y,
                180,
                62,
                [f"quadrant {k}", "nappe FPC 16 broches", "16 cases, 32 LED, frontal"],
            )
        )
        out.append(_arrow(200, y + 20, mx, my + 20 + (k - 1) * 30, "arr8", "wire-a"))
    out.append(
        text(214, 166, "AMP_OUT 1 à 4 : un signal analogique par quadrant", "lbl small q-high-t")
    )
    # shared control bus
    bx = 262
    y_bus = my + mh - 18
    out.append(f'<line class="wire-p" x1="{mx}" y1="{y_bus}" x2="{bx}" y2="{y_bus}"/>')
    out.append(f'<line class="wire-p" x1="{bx}" y1="{qy[0] + 44}" x2="{bx}" y2="{qy[3] + 44}"/>')
    for y in qy:
        out.append(_arrow(bx, y + 44, 202, y + 44, "arr8", "wire-p"))
    out.append(text(270, 432, "bus de commande commun aux quatre nappes :", "lbl small q-low-t"))
    out.append(
        text(270, 446, "adresse A0 à A2, EN_L, EN_H, PULSE_EN, DAMP_EN_N", "lbl small q-low-t")
    )
    out.append(
        text(270, 460, "plus les rails 5VA, 3V3, 5V_LED et VIN sur chaque nappe", "lbl small muted")
    )
    # LED chain: buffer under the quadrants, into quadrant 1, then 1 to 4
    out.append(_box(20, 508, 196, 40, ["tampon LED", "74AHCT1G125, 3,3 V vers 5 V"], "box-soft"))
    out.append(_path(f"M20 528 H8 V{qy[0] + 31} H18", "arr8"))
    for k in range(3):
        out.append(_arrow(30, qy[k] + 63, 30, qy[k + 1] - 1, "arr8"))
    out.append(text(224, 522, "chaîne LED : 128 LED en série,", "lbl small muted"))
    out.append(text(224, 536, "entre par le quadrant 1, ressort par le 4", "lbl small muted"))
    # comms and links, right column
    out.append(text(700, 160, "LIAISONS", "lbl mono muted"))
    out.append(
        _box(
            740,
            172,
            200,
            62,
            ["module ESP32-S3", "WiFi et BLE : horloge, Lichess", "pont radio, pas d'arbitrage"],
        )
    )
    out.append(_box(740, 262, 200, 48, ["embase Pi Zero (option)", "cavalier JP1 : ESP ou Pi"]))
    out.append(_box(740, 330, 200, 48, ["USB-C", "avec protection ESD"]))
    out.append(_box(740, 398, 200, 48, ["SWD 10 broches", "programmation et débogage"]))
    out.append(_arrow(mx + mw, my + 30, 738, 203, "arr8b"))
    for i, s in enumerate(("UART isolée", "ADuM1201", "115200 bauds", "5 V commuté")):
        out.append(text(640, 176 + 14 * i, s, "lbl small" if i == 0 else "lbl small muted"))
    out.append(_arrow(mx + mw, my + 80, 738, 286, "arr8b"))
    out.append(_arrow(mx + mw, my + 110, 738, 354, "arr8b"))
    out.append(_arrow(mx + mw, my + 140, 738, 422, "arr8b"))
    # bottom row
    out.append(text(20, 560, "INTERFACE ET CONNECTEURS", "lbl mono muted"))
    bottom = [
        (20, 130, ["buzzer", "sur 5 V, FET"]),
        (160, 130, ["4 LED d'état", "et un bouton"]),
        (
            500,
            210,
            ["J10 vers la carte puissance", "I2C : jauge INA219, BMS BQ76920", "CHG_STAT, PWR_KEY"],
        ),
        (
            730,
            210,
            [
                "J9 vers la carte moteurs (phase 2)",
                "STEP, DIR, UART TMC2209",
                "fins de course, servo",
            ],
        ),
    ]
    for x, bw, lines in bottom:
        out.append(_box(x, 568, bw, 58, lines))
    out.append("</svg>")
    return "\n".join(out)


def fig_scan_cycle(cfg: BoardConfig) -> str:
    """What the firmware does, from one coil to a detected move."""
    meas = cfg.measurement
    window = listen_window_us(cfg)
    per_square_ms = 2.0  # ADR 0005: x16 coherent averaging, 2 ms per square
    n_sq = cfg.plateau.grid**2
    w, h = 960, 340
    out = [
        svg_open(
            w,
            h,
            "Cycle du firmware : pour chaque quadrant et chaque bobine, adresser, frapper, "
            "blanking, ecouter, FFT ; puis plus proche voisin contre la calibration, etat des "
            "64 cases, comparaison avec le balayage precedent, arbitre, LED et message radio",
        ),
        f"<defs>{arrow_marker('arr9')}</defs>",
    ]
    out.append('<rect class="zone" x="14" y="26" width="932" height="96" rx="8"/>')
    out.append(
        text(
            24,
            44,
            f"POUR CHAQUE QUADRANT (4) ET CHAQUE BOBINE ({cfg.plateau.quadrant.squares**2}) : "
            f"environ {fr_num(per_square_ms, 0)} ms par case "
            f"avec le moyennage x{meas.coherent_avg}",
            "lbl mono muted",
        )
    )
    row1 = [
        ("adresser", "mux et décodeurs"),
        ("frapper", f"{fr_num(meas.drive.pulse_us)} µs, {fr_num(meas.drive.v, 0)} V"),
        ("blanking", f"{fr_num(meas.blanking_us)} µs, case étouffée"),
        ("écouter", f"{meas.fft_points} points, {fr_num(window, 0)} µs"),
        ("FFT", "interpolation du pic"),
        ("f0 de la case", "à 1 kHz près"),
    ]
    bw, gap, x = 138, 16, 24
    for i, (t1, t2) in enumerate(row1):
        cls = "box-warm" if i == 1 else "box"
        out.append(_box(x, 56, bw, 52, [t1, t2], cls))
        if i < len(row1) - 1:
            out.append(_arrow(x + bw + 1, 82, x + bw + gap - 1, 82, "arr9"))
        x += bw + gap
    # row 2
    row2 = [
        ("table de calibration", "la note de chaque pièce,", "mesurée une fois, en flash"),
        ("plus proche voisin", "quelle pièce, quel camp,", "ou case vide"),
        (
            f"état des {n_sq} cases",
            f"balayage complet en {fr_num(per_square_ms * n_sq / 1e3, 2)} s",
            f"{meas.idle_scan_hz:.0f} fois par seconde au repos",
        ),
        ("comparer au balayage", "précédent : une case vidée,", "une case remplie = un coup"),
    ]
    bw2, gap2, x = 210, 22, 24
    y2 = 150
    for i, lines in enumerate(row2):
        out.append(_box(x, y2, bw2, 66, list(lines)))
        if i < len(row2) - 1:
            out.append(_arrow(x + bw2 + 1, y2 + 33, x + bw2 + gap2 - 1, y2 + 33, "arr9"))
        x += bw2 + gap2
    x_f0 = 24 + 5 * (bw + gap) + bw / 2
    x_nn = 24 + (bw2 + gap2) + bw2 / 2
    out.append(_path(f"M{x_f0:.1f} 108 V130 H{x_nn:.1f} V{y2 - 2}", "arr9"))
    # row 3
    y3 = 250
    row3 = [
        (24, 300, ["arbitre", "coup légal ? roque, promotion, prise en passant"]),
        (356, 260, ["LED de camp", "deux points par case, 128 en tout"]),
        (648, 288, ["ligne texte vers le pont radio", "B occupation, M coup, F position, S état"]),
    ]
    for x, bw3, lines in row3:
        out.append(_box(x, y3, bw3, 52, lines))
    x_cmp = 24 + 3 * (bw2 + gap2) + bw2 / 2
    out.append(_path(f"M{x_cmp:.1f} {y2 + 66} V{y2 + 82} H174 V{y3 - 2}", "arr9"))
    out.append(_arrow(324, y3 + 26, 354, y3 + 26, "arr9"))
    out.append(_arrow(616, y3 + 26, 646, y3 + 26, "arr9"))
    out.append(
        text(
            24,
            326,
            "la mesure et la classification existent dans le firmware du cerveau ; l'arbitre et "
            "les messages de partie sont le lot 6 de la note 07",
            "lbl small muted",
        )
    )
    out.append("</svg>")
    return "\n".join(out)


def fig_bench_nucleo(cfg: BoardConfig) -> str:
    """The bench: Nucleo, bench shield, reduced quadrant, pucks, instruments."""
    plan = frequency_plan(cfg)
    reduced = cfg.plateau.quadrant.reduced
    n = reduced.squares
    p = cfg.pitch.plateau_mm
    strip = cfg.plateau.quadrant.front_end_strip_mm
    board_w = n * p + strip
    board_h = n * p + reduced.strip_overhang_mm
    w, h = 960, 500
    out = [
        svg_open(
            w,
            h,
            "Le banc : une Nucleo-G474RE sous une carte de banc, une nappe vers le quadrant "
            "2 x 2, les pucks de test sur le contreplaque, l alimentation de laboratoire, "
            "l oscilloscope, le LCR-metre et l analyseur logique",
        ),
        f"<defs>{arrow_marker('arr10')}{arrow_marker('arr10b', both=True)}</defs>",
    ]
    # supply and PC
    out.append(
        _box(
            20,
            30,
            200,
            56,
            ["alimentation de labo 12 V", "limitée en courant,", "linéaire ou batterie"],
        )
    )
    out.append(_arrow(120, 86, 120, 118, "arr10", "wire-p"))
    out.append(text(128, 106, "12 V", "lbl small q-low-t"))
    # shield and nucleo
    out.append(
        _box(
            20,
            120,
            220,
            78,
            [
                "carte de banc (shield)",
                "jack 12 V, LDO 5VA, rail 5V_LED,",
                "tampon LED, connecteur FPC 16",
            ],
            "box-soft",
        )
    )
    out.append(
        _box(
            20,
            212,
            220,
            96,
            [
                "Nucleo-G474RE",
                "le même MCU que le cerveau",
                "ST-Link et port série intégrés",
                "brochage Arduino = bus du cerveau",
            ],
            "box-mcu",
        )
    )
    out.append(
        text(
            24,
            320,
            "emboîtées : la carte de banc se pose sur les connecteurs Arduino",
            "lbl small muted",
        )
    )
    out.append(
        _box(
            20,
            380,
            220,
            62,
            ["PC", "console série 115200 bauds, CSV,", "notebook d'analyse M1 à M11"],
        )
    )
    out.append(_arrow(120, 308, 120, 378, "arr10b"))
    out.append(text(128, 348, "USB", "lbl small"))
    # quadrant, drawn to scale 2.2 px per mm
    s = 2.2
    qx, qy = 396, 120
    qw, qh = board_w * s, board_h * s
    # FPC cable to the quadrant
    out.append(f'<path class="wire-a" d="M240 160 C330 160, 330 250, {qx} 250"/>')
    for i, s_ in enumerate(("nappe FPC, 16 fils :", "bus, AMP_OUT, LED,", "et les rails")):
        out.append(text(250, 126 + 14 * i, s_, "lbl small q-high-t"))
    out.append(f'<rect class="box" x="{qx}" y="{qy}" width="{qw:.1f}" height="{qh:.1f}" rx="4"/>')
    sx = strip * s
    out.append(
        f'<rect class="box-soft" x="{qx}" y="{qy}" width="{sx:.1f}" height="{qh:.1f}" rx="4"/>'
    )
    out.append(
        f'<text class="lbl small" transform="translate({qx + sx / 2 + 4:.1f} '
        f'{qy + qh / 2:.1f}) rotate(-90)" text-anchor="middle">'
        "bande de frontal : cellules, mux, ampli, filtre</text>"
    )
    test_pieces = cfg.mockup.test_pieces
    legend: list[str] = []
    r_out = cfg.sense_coil.outer_ratio * p / 2 * s
    r_in = cfg.sense_coil.inner_ratio * p / 2 * s
    for row in range(n):
        for col in range(n):
            cx = qx + sx + (col + 0.5) * p * s
            cy = qy + (row + 0.5) * p * s
            for rr in (r_out, (r_out + r_in) / 2, r_in):
                out.append(f'<circle class="coil" cx="{cx:.1f}" cy="{cy:.1f}" r="{rr:.1f}"/>')
            k = row * n + col
            if k < len(test_pieces):
                tp = test_pieces[k]
                line = plan.line(tp.piece, tp.color)
                name = FR_PIECE[tp.piece.value]
                out.append(f'<circle class="puck" cx="{cx:.1f}" cy="{cy:.1f}" r="{r_in - 2:.1f}"/>')
                out.append(text(cx, cy - 2, name[0], "lbl small", "middle"))
                out.append(
                    text(cx, cy + 10, f"{fr_num(line.cap_nF)} nF", "lbl small mono", "middle")
                )
                legend.append(f"{name[0]} {line.f0_hz / 1e3:.0f}")
    out.append(
        text(
            qx,
            qy + qh + 18,
            f"quadrant 2 x 2, {fr_num(board_w, 0)} x {fr_num(board_h, 0)} mm, 4 couches, "
            f"même circuit et même bus que le 4 x 4",
            "lbl small muted",
        )
    )
    out.append(
        text(
            qx,
            qy + qh + 34,
            "pucks de test posés sur le contreplaqué de "
            f"{fr_num(cfg.gap.surface_mm)} mm et le feutre : entrefer nominal "
            f"{fr_num(cfg.gap.nominal_total_mm)} mm",
            "lbl small muted",
        )
    )
    out.append(
        text(
            qx,
            qy + qh + 50,
            "pucks du bas de bande, l'espacement le plus serré : " + ", ".join(legend) + " kHz",
            "lbl small muted",
        )
    )
    # instruments
    ix = 720
    out.append(
        _box(
            ix,
            120,
            220,
            62,
            ["oscilloscope 2 voies", "sondes sur TP1 (AMP_OUT)", "et TP3 (bus d'impulsion)"],
        )
    )
    out.append(_box(ix, 210, 220, 48, ["LCR-mètre", "L et Q des bobines nues (M1)"]))
    out.append(_box(ix, 286, 220, 48, ["analyseur logique", "adresses, PULSE_EN, DAMP_EN_N"]))
    out.append(_arrow(qx + qw, qy + 8, ix - 2, 150, "arr10b"))
    out.append(_arrow(qx + qw, qy + qh - 30, ix - 2, 234, "arr10b"))
    out.append(_arrow(240, 250, 300, 250, "arr10b"))
    out.append(_path(f"M300 250 V412 H{ix + 110} V336", "arr10"))
    out.append(text(306, 428, "bus de commande observé en parallèle", "lbl small muted"))
    out.append(
        text(
            20,
            470,
            "ce qui manque par rapport au plateau : le cerveau, la carte puissance, "
            "les cellules, la radio, l'horloge ; rien de tout cela n'est nécessaire pour mesurer",
            "lbl small muted",
        )
    )
    out.append("</svg>")
    return "\n".join(out)
