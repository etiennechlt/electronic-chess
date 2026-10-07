"""Figures of the note 24: the Hall presence layer and the NFC question.

Every number comes from chessboard_calc.hall and chessboard_calc.nfc,
which read config/board.yaml; the drawings only lay them out.
"""

from __future__ import annotations

import json

from chessboard_calc.config import BoardConfig, PieceType
from chessboard_calc.hall import (
    amplitude_classes,
    hall_budget,
    hall_scan,
    piece_bz_mT,
    sensor_gap_mm,
)
from chessboard_calc.nfc import analog_mux_verdict, antenna

from .bench import _arrow, _box, _path
from .common import arrow_marker, fr_num, svg_open, text

CURVE_Z_MM = (2.0, 30.0)  # distance range of the field curve, magnet face to plate
CURVE_STEP_MM = 0.25


def field_curves(cfg: BoardConfig) -> tuple[list[float], list[float], list[float]]:
    """B(z) of the pawn and of the king, the two ends of the magnet range."""
    p = cfg.pitch.plateau_mm
    zs, pawn, king = [], [], []
    z = CURVE_Z_MM[0]
    while z <= CURVE_Z_MM[1] + 1e-9:
        zs.append(z)
        pawn.append(piece_bz_mT(cfg, PieceType.PAWN, p, z))
        king.append(piece_bz_mT(cfg, PieceType.KING, p, z))
        z += CURVE_STEP_MM
    return zs, pawn, king


def fig_hall_stack(cfg: BoardConfig, uid: str = "") -> str:
    """Vertical cut: the Hall sensor under the plywood reads the ferrite in
    the base, through the same stack as the LC spiral."""
    scale = 16.0
    w, h = 900, 380
    cx = 450
    gap = cfg.gap
    b = hall_budget(cfg, cfg.pitch.plateau_mm)
    sensor = b.sensor
    lay = cfg.hall_rfid.layout
    y_pcb_bot = 340
    h_pcb, h_air = gap.pcb_mm * scale, gap.air_mm * scale
    h_wood, h_felt = gap.surface_mm * scale, gap.felt_mm * scale
    y_pcb_top = y_pcb_bot - h_pcb
    y_air_top = y_pcb_top - h_air
    y_wood_top = y_air_top - h_wood
    y_felt_top = y_wood_top - h_felt
    pawn = b.fields[PieceType.PAWN]
    base_mm = cfg.pieces.classes[PieceType.PAWN].base_ratio * cfg.pitch.plateau_mm
    base_w = base_mm * scale
    base_h = 9.0 * scale
    y_base_bot = y_felt_top
    y_base_top = y_base_bot - base_h
    out = [
        svg_open(
            w,
            h,
            "Coupe verticale : le capteur Hall en boitier SOT-23 pose sur le circuit imprime "
            "dans la lame d air, sous le contreplaque et le feutre, lit l aimant ferrite de la "
            f"base de la piece a {fr_num(b.z_nominal_mm)} mm",
        ),
        "<defs>"
        + arrow_marker(f"harr{uid}")
        + f'<pattern id="wire{uid}" width="6" height="6" patternUnits="userSpaceOnUse" '
        'patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="6" '
        'stroke="currentColor" stroke-width="1.6"/></pattern></defs>',
    ]
    layers = [
        (y_pcb_top, h_pcb, "lay-pcb", f"circuit imprimé {fr_num(gap.pcb_mm)} mm"),
        (y_air_top, h_air, "lay-air", f"air {fr_num(gap.air_mm)} mm : LED, frontal, et le capteur"),
        (y_wood_top, h_wood, "lay-wood", f"contreplaqué {fr_num(gap.surface_mm)} mm"),
        (y_felt_top, h_felt, "lay-felt", f"feutre {fr_num(gap.felt_mm)} mm"),
    ]
    for y, hh, cls, _label in layers:
        out.append(f'<rect class="{cls}" x="60" y="{y:.1f}" width="780" height="{hh:.1f}"/>')
    # the sensor: SOT-23 body on the top copper, the Hall plate inside
    s_w, s_h = 2.9 * scale, sensor.height_mm * scale
    y_s_top = y_pcb_top - s_h
    out.append(
        f'<rect class="box-mcu" x="{cx - s_w / 2:.1f}" y="{y_s_top:.1f}" width="{s_w:.1f}" '
        f'height="{s_h:.1f}" rx="2"/>'
    )
    y_plate = y_pcb_top - lay.die_height_mm * scale
    out.append(
        f'<line class="wire-a" x1="{cx - s_w / 2 + 6:.1f}" y1="{y_plate:.1f}" '
        f'x2="{cx + s_w / 2 - 6:.1f}" y2="{y_plate:.1f}"/>'
    )
    out.append(
        text(
            cx + s_w / 2 + 10,
            y_s_top + s_h / 2 + 4,
            f"{sensor.part} en {sensor.package}, {fr_num(sensor.height_mm)} mm de haut",
            "lbl",
        )
    )
    # the piece base, coil, magnet
    out.append(
        f'<path class="piece" d="M{cx - base_w / 2:.1f} {y_base_bot:.1f} v-{base_h - 14:.1f} '
        f'q0 -14 14 -14 h{base_w - 28:.1f} q14 0 14 14 v{base_h - 14:.1f} z"/>'
    )
    out.append(f'<path class="piece" d="M{cx - 34} {y_base_top:.1f} q34 -30 68 0 z"/>')
    c_h = cfg.resonator.coil.height_mm * scale
    c_od = (base_mm - cfg.resonator.coil.outer_margin_mm) * scale
    c_id = cfg.resonator.coil.inner_ratio * c_od
    yb_coil = y_base_bot - 4
    bundle_w = (c_od - c_id) / 2
    for xb in (cx - c_od / 2, cx + c_id / 2):
        out.append(
            f'<rect class="bundle" style="fill:url(#wire{uid})" x="{xb:.1f}" '
            f'y="{yb_coil - c_h:.1f}" width="{bundle_w:.1f}" height="{c_h:.1f}"/>'
        )
    m_d = pawn.magnet_d_mm * scale
    m_h = pawn.magnet_t_mm * scale
    y_mag_bot = yb_coil - c_h - 2
    out.append(
        f'<rect class="magnet" x="{cx - m_d / 2:.1f}" y="{y_mag_bot - m_h:.1f}" '
        f'width="{m_d:.1f}" height="{m_h:.1f}" rx="3"/>'
    )
    out.append(
        text(
            cx,
            y_mag_bot - m_h / 2 + 4,
            f"ferrite ø{fr_num(pawn.magnet_d_mm)} x {fr_num(pawn.magnet_t_mm)} mm",
            "lbl",
            "middle",
        )
    )
    out.append(
        text(
            cx - base_w / 2 - 8,
            yb_coil - c_h / 2 + 4,
            "bobine LC (si la pièce en a une)",
            "lbl muted",
            "end",
        )
    )
    # field lines down to the sensor
    for dx in (-40, 0, 40):
        out.append(
            f'<path class="field" d="M{cx + dx} {y_mag_bot + 2:.1f} C{cx + dx * 1.8:.1f} '
            f"{y_wood_top:.1f}, {cx + dx * 1.8:.1f} {y_air_top:.1f}, {cx + dx * 0.6:.1f} "
            f'{y_plate - 3:.1f}" marker-end="url(#harr{uid})"/>'
        )
    out.append(
        text(
            cx + 110,
            y_wood_top + 16,
            f"B = {fr_num(pawn.b_nominal_mT)} mT au capteur",
            "lbl q-high-t",
        )
    )
    out.append(text(cx + 110, y_wood_top + 32, "pour un pion posé, entrefer nominal", "lbl muted"))
    for y, hh, _cls, label in layers:
        out.append(text(66, y + hh / 2 + 4, label))
    xg = 852
    out.append(
        f'<line class="mark" x1="{xg}" y1="{y_mag_bot:.1f}" x2="{xg}" y2="{y_plate:.1f}" '
        f'marker-start="url(#harr{uid})" marker-end="url(#harr{uid})"/>'
    )
    out.append(
        text(
            xg - 6,
            y_mag_bot - m_h - 12,
            f"{fr_num(b.z_nominal_mm)} mm de l'aimant à la plaque de Hall",
            "lbl",
            "end",
        )
    )
    out.append(
        text(
            60,
            18,
            f"base d'un pion, {fr_num(base_mm)} mm de diamètre ; au pas de "
            f"{fr_num(cfg.pitch.plateau_mm, 0)} mm, épaisseurs à l'échelle",
            "lbl muted",
        )
    )
    out.append("</svg>")
    return "\n".join(out)


def fig_hall_curve(cfg: BoardConfig, interactive: bool = False) -> str:
    """Field at the sensor against the magnet to plate distance, the pawn and
    the king, with the presence threshold, the gap band and the lift."""
    b = hall_budget(cfg, cfg.pitch.plateau_mm)
    zs, pawn, king = field_curves(cfg)
    lay = cfg.hall_rfid.layout
    w, h = 900, 360
    x0, x1 = 70, 860
    za, zb = CURVE_Z_MM
    px = (x1 - x0) / (zb - za)
    yb, yt = 300, 50
    bmax = 40.0
    py = (yb - yt) / bmax
    extra = 'data-curve="1"' if interactive else ""
    out = [
        svg_open(
            w,
            h,
            "Champ au capteur en fonction de la distance entre l aimant et la plaque de Hall, "
            f"pour le pion et le roi : {fr_num(b.fields[PieceType.PAWN].b_nominal_mT)} et "
            f"{fr_num(b.fields[PieceType.KING].b_nominal_mT)} mT a l entrefer nominal, le seuil "
            f"de presence a {fr_num(b.threshold_mT)} mT, le roi souleve de "
            f"{fr_num(lay.lift_detect_mm, 0)} mm sous le relachement",
            extra,
        )
    ]
    bx0 = x0 + (b.z_nominal_mm - za) * px
    bx1 = x0 + (b.z_max_mm - za) * px
    out.append(
        f'<rect class="band" x="{bx0:.1f}" y="{yt - 10}" width="{bx1 - bx0:.1f}" '
        f'height="{yb - yt + 10}"/>'
    )
    out.append(
        text(
            bx1 + 6,
            yt - 2,
            f"entrefer nominal à maximal : {fr_num(b.z_nominal_mm)} à {fr_num(b.z_max_mm)} mm",
            "lbl muted",
        )
    )
    for bb in range(0, 41, 10):
        y = yb - bb * py
        out.append(f'<line class="grid" x1="{x0}" y1="{y:.1f}" x2="{x1}" y2="{y:.1f}"/>')
        out.append(text(x0 - 8, y + 4, str(bb), "lbl mono", "end"))
    for zz in range(5, 31, 5):
        xx = x0 + (zz - za) * px
        out.append(f'<line class="tick" x1="{xx:.1f}" y1="{yb}" x2="{xx:.1f}" y2="{yb + 5}"/>')
        out.append(text(xx, yb + 20, str(zz), "lbl mono", "middle"))
    out.append(f'<line class="axis" x1="{x0}" y1="{yb}" x2="{x1}" y2="{yb}"/>')
    out.append(
        text(x1, yb + 38, "distance de l'aimant à la plaque de Hall, en mm", "lbl muted", "end")
    )
    out.append(text(x0 - 8, yt - 18, "mT", "lbl muted", "end"))
    for level, label in ((b.threshold_mT, "seuil de présence"), (b.release_mT, "relâchement")):
        y = yb - level * py
        out.append(f'<line class="dash" x1="{x0}" y1="{y:.1f}" x2="{x1}" y2="{y:.1f}"/>')
        out.append(text(x1 - 6, y - 5, f"{label} : {fr_num(level)} mT", "lbl muted", "end"))
    for series, cls in ((pawn, "q-low"), (king, "q-high")):
        pts = [
            f"{x0 + (z - za) * px:.1f},{yb - min(v, bmax) * py:.1f}"
            for z, v in zip(zs, series, strict=True)
        ]
        out.append(f'<polyline class="trace {cls}" points="{" ".join(pts)}"/>')
    pf, kf = b.fields[PieceType.PAWN], b.fields[PieceType.KING]
    z_lift = sensor_gap_mm(cfg, lay.lift_detect_mm)
    marks = (
        (
            b.z_max_mm,
            pf.b_max_gap_mT,
            "q-low",
            f"pion, entrefer maximal : {fr_num(pf.b_max_gap_mT)} mT",
            0,
        ),
        (b.z_nominal_mm, kf.b_nominal_mT, "q-high", f"roi posé : {fr_num(kf.b_nominal_mT)} mT", 1),
        (
            z_lift,
            kf.b_lifted_mT,
            "q-high",
            f"roi soulevé de {fr_num(lay.lift_detect_mm, 0)} mm : {fr_num(kf.b_lifted_mT)} mT",
            1,
        ),
    )
    for z, v, cls, label, side in marks:
        xx = x0 + (z - za) * px
        yy = yb - v * py
        out.append(f'<circle class="dot {cls}" cx="{xx:.1f}" cy="{yy:.1f}" r="5"/>')
        if side > 0:
            out.append(text(xx + 10, yy - 10, label))
        else:
            out.append(text(xx + 10, yy + 18, label))
    out.append(
        text(x1 - 6, yt + 44, f"roi, ferrite ø{fr_num(kf.magnet_d_mm)} mm", "lbl q-high-t", "end")
    )
    out.append(
        text(x1 - 6, yt + 60, f"pion, ferrite ø{fr_num(pf.magnet_d_mm)} mm", "lbl q-low-t", "end")
    )
    if interactive:
        out.append(
            '<g class="hxh" hidden="hidden">'
            f'<line class="dash" x1="0" y1="{yt - 10}" x2="0" y2="{yb}"/>'
            '<circle class="dot q-low" r="5"/><circle class="dot q-high" r="5"/>'
            '<rect class="tipbox" width="210" height="38" rx="4"/>'
            '<text class="lbl mono" x="0" y="0"></text>'
            '<text class="lbl mono" x="0" y="0"></text></g>'
        )
    out.append("</svg>")
    return "\n".join(out)


def curve_json(cfg: BoardConfig) -> tuple[str, str, str]:
    zs, pawn, king = field_curves(cfg)
    return (
        json.dumps([round(z, 2) for z in zs]),
        json.dumps([round(v, 2) for v in pawn]),
        json.dumps([round(v, 2) for v in king]),
    )


def fig_hall_classes(cfg: BoardConfig) -> str:
    """What an amplitude reading can separate: the field interval of every
    magnet class over the gap scatter, uniform magnets then size coded."""
    p = cfg.pitch.plateau_mm
    uni = amplitude_classes(cfg, p, size_coded=False)
    coded = amplitude_classes(cfg, p, size_coded=True)
    b = hall_budget(cfg, p)
    w, h = 900, 330
    x0, x1 = 230, 860
    bmax = 70.0
    px = (x1 - x0) / bmax
    out = [
        svg_open(
            w,
            h,
            "Intervalles de champ de chaque classe d aimant quand l entrefer varie : avec des "
            f"aimants uniformes les trois se recouvrent, {uni.separable_groups} groupe ; avec des "
            f"epaisseurs codees {coded.separable_groups} groupes separes",
        )
    ]
    names = {
        PieceType.PAWN: "pion",
        PieceType.KNIGHT: "cavalier",
        PieceType.BISHOP: "fou",
        PieceType.ROOK: "tour",
        PieceType.QUEEN: "dame",
        PieceType.KING: "roi",
    }
    for bb in range(0, 71, 10):
        xx = x0 + bb * px
        out.append(f'<line class="grid" x1="{xx:.1f}" y1="40" x2="{xx:.1f}" y2="290"/>')
        out.append(text(xx, 306, str(bb), "lbl mono", "middle"))
    out.append(text(x1, 324, "champ au capteur, en mT", "lbl muted", "end"))
    xt = x0 + b.threshold_mT * px
    out.append(f'<line class="dash" x1="{xt:.1f}" y1="36" x2="{xt:.1f}" y2="290"/>')
    out.append(text(xt + 4, 48, f"seuil {fr_num(b.threshold_mT)} mT", "lbl muted"))
    y = 70
    for title, rep, cls in (
        ("aimants uniformes (le projet)", uni, "seg-listen"),
        ("épaisseurs codées (variante)", coded, "seg-pulse"),
    ):
        out.append(
            text(
                20, y - 14, f"{title} : {rep.separable_groups} groupe(s) séparable(s)", "lbl strong"
            )
        )
        for c in rep.classes:
            xa, xb = x0 + c.b_low_mT * px, x0 + c.b_high_mT * px
            out.append(
                f'<rect class="{cls}" x="{xa:.1f}" y="{y:.1f}" width="{xb - xa:.1f}" '
                'height="18" rx="3"/>'
            )
            label = "/".join(names[pc] for pc in c.pieces)
            out.append(
                text(x0 - 10, y + 13, f"{label}, {fr_num(c.magnet_t_mm, 0)} mm", "lbl", "end")
            )
            out.append(
                text(
                    xb + 6,
                    y + 13,
                    f"{fr_num(c.b_low_mT, 0)} à {fr_num(c.b_high_mT, 0)}",
                    "lbl small muted",
                )
            )
            y += 26
        y += 36
    out.append("</svg>")
    return "\n".join(out)


def fig_hall_scan(cfg: BoardConfig, uid: str = "") -> str:
    """The standalone scanner: four quadrants of sensors, four muxes, the
    ESP32-S3, the row supplies and the occupancy line out."""
    hr = cfg.hall_rfid
    sc = hall_scan(cfg, gated=True)
    q = cfg.plateau.quadrant.squares
    w, h = 960, 430
    out = [
        svg_open(
            w,
            h,
            "Schema bloc du scanner : quatre quadrants de seize capteurs Hall, un multiplexeur "
            "par quadrant, quatre entrees ADC de l ESP32-S3, quatre bits d adresse partages, "
            "quatre commutateurs d alimentation par rangee, la ligne B vers la console",
        ),
        f"<defs>{arrow_marker('sarr' + uid)}</defs>",
    ]
    out.append(text(20, 22, "QUADRANTS", "lbl mono muted"))
    out.append(text(330, 22, "MULTIPLEXEURS", "lbl mono muted"))
    out.append(text(600, 22, hr.esp32.module.upper(), "lbl mono muted"))
    for i in range(4):
        y = 40 + i * 82
        out.append(
            _box(
                20,
                y,
                230,
                62,
                [
                    f"quadrant {i + 1} : {q * q} capteurs {hr.sensors[0].part}",
                    f"{hr.power_gating.groups} rangées de "
                    f"{q * q // hr.power_gating.groups}, un P-FET chacune",
                    "sortie analogique, 3,3 V, masse",
                ],
            )
        )
        out.append(_box(330, y + 8, 180, 46, [f"{hr.mux.part}", f"{hr.mux.channels} vers 1"]))
        out.append(_arrow(250, y + 31, 330, y + 31, "sarr" + uid, "wire-a"))
        out.append(_arrow(510, y + 31, 600, y + 31, "sarr" + uid, "wire-a"))
        out.append(text(515, y + 24, f"ADC_Q{i + 1}", "lbl small mono"))
    out.append(
        _box(
            600,
            60,
            180,
            230,
            [
                "ESP32-S3-WROOM-1",
                f"ADC1, {hr.esp32.adc_bits} bits",
                f"{hr.esp32.samples_per_square} lectures par case",
                "",
                "hallscan.c :",
                "ligne de base par case,",
                "seuil et hystérésis,",
                "anti-rebond",
            ],
            "box-mcu",
        )
    )
    # shared address bus and row enables
    out.append(_path("M600 310 H420 V 265", "sarr" + uid, "wire-p"))
    out.append(text(430, 330, f"MUX_S0..S3 : adresse commune aux {4} multiplexeurs", "lbl small"))
    out.append(_path("M600 350 H135 V 368", "sarr" + uid, "wire"))
    out.append(
        text(
            145,
            388,
            f"ROW_EN0..{hr.power_gating.groups - 1} : une rangée alimentée à la fois "
            f"(courant moyen divisé par {hr.power_gating.groups})",
            "lbl small",
        )
    )
    out.append(_arrow(780, 175, 850, 175, "sarr" + uid, "wire"))
    out.append(_box(850, 150, 100, 50, ["console", "115200 bauds"]))
    out.append(text(850, 222, "B,........", "lbl mono"))
    out.append(text(850, 238, "à chaque changement", "lbl small muted"))
    out.append(text(600, 318, "", "lbl"))
    out.append(
        text(
            20,
            412,
            f"un scan : {fr_num(sc.square_us, 0)} µs par case, "
            f"{fr_num(sc.board_ms, 1)} ms par plateau, {fr_num(sc.rate_hz, 0)} fois par seconde",
            "lbl strong",
        )
    )
    out.append("</svg>")
    return "\n".join(out)


def fig_nfc_switch(cfg: BoardConfig) -> str:
    """Why an analog multiplexer cannot switch a 13.56 MHz loop: what the
    loop needs against what the CD74HC4067 gives."""
    p = cfg.pitch.plateau_mm
    ant = antenna(cfg, p)
    v = analog_mux_verdict(cfg, p)
    nfc = cfg.hall_rfid.nfc
    w, h = 900, 280
    x0, x1 = 300, 820
    out = [
        svg_open(
            w,
            h,
            "Trois grandeurs de la boucle NFC, ce qu il faut contre ce que donne le "
            f"multiplexeur analogique : resistance serie {fr_num(ant.r_series_ohm)} contre "
            f"{fr_num(cfg.hall_rfid.mux.ron_ohm, 0)} ohm, Q {fr_num(nfc.antenna.q_target, 0)} "
            f"contre {fr_num(v.q_with_switch, 2)}, desaccord de {fr_num(abs(v.detune_pct), 0)} "
            "pour cent",
        )
    ]
    rows = (
        (
            "résistance série dans la boucle",
            f"{fr_num(ant.r_series_ohm)} Ω pour Q = {fr_num(nfc.antenna.q_target, 0)}",
            f"{fr_num(cfg.hall_rfid.mux.ron_ohm, 0)} Ω de résistance passante",
            ant.r_series_ohm,
            cfg.hall_rfid.mux.ron_ohm,
        ),
        (
            "facteur Q de la boucle",
            f"{fr_num(nfc.antenna.q_target, 0)} visé",
            f"{fr_num(v.q_with_switch, 2)} avec le multiplexeur",
            nfc.antenna.q_target,
            v.q_with_switch,
        ),
        (
            "capacité sur la boucle accordée",
            f"{fr_num(ant.c_res_pF, 0)} pF d'accord",
            f"{fr_num(v.c_parasitic_pF, 0)} pF parasites : "
            f"{fr_num(v.detune_pct, 0)} % de fréquence",
            ant.c_res_pF,
            v.c_parasitic_pF,
        ),
    )
    out.append(text(x0, 30, "ce qu'il faut", "lbl q-high-t"))
    out.append(text(x0 + 200, 30, "ce que donne le CD74HC4067", "lbl q-low-t"))
    y = 56
    for title, need_label, mux_label, need, mux in rows:
        scale = (x1 - x0) / max(need, mux)
        out.append(text(20, y + 14, title, "lbl strong"))
        out.append(
            f'<rect class="seg-listen" x="{x0}" y="{y}" '
            f'width="{max(need * scale, 2):.1f}" height="16" rx="3"/>'
        )
        out.append(text(x0 + max(need * scale, 2) + 8, y + 13, need_label, "lbl small"))
        out.append(
            f'<rect class="seg-pulse" x="{x0}" y="{y + 22}" '
            f'width="{max(mux * scale, 2):.1f}" height="16" rx="3"/>'
        )
        out.append(text(x0 + max(mux * scale, 2) + 8, y + 35, mux_label, "lbl small"))
        y += 70
    out.append(
        text(
            20,
            262,
            "verdict du modèle : ok="
            + ("oui" if v.ok else "non")
            + " ; un commutateur ne peut vivre que dans la section adaptée à 50 Ω, "
            "jamais dans la boucle",
            "lbl muted",
        )
    )
    out.append("</svg>")
    return "\n".join(out)
