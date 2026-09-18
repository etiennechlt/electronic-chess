"""Figures of the note 20: what to gather for the bench, how the shield
plugs onto the Nucleo, how a test piece is made, how the bench is tested."""

from __future__ import annotations

from chessboard_calc.config import BoardConfig, PieceType, resolve_geometry
from chessboard_calc.inductance import piece_coil_design
from chessboard_calc.resonance import frequency_plan

from .bench import _arrow, _box, _path
from .common import arrow_marker, fr_num, svg_open, text
from .q import FR_PIECE, listen_window_us, piece_name


def _label(x: float, y: float, lines: list[str], anchor: str = "start") -> str:
    out = []
    for i, s in enumerate(lines):
        cls = "lbl strong" if i == 0 else "lbl small muted"
        out.append(text(x, y + i * 14, s, cls, anchor))
    return "\n".join(out)


def _lines(x: float, y: float, lines: list[str], cls: str = "lbl small muted") -> str:
    return "\n".join(text(x, y + i * 14, s, cls) for i, s in enumerate(lines))


def _step(x: float, y: float, n: int, w: float = 26.0) -> str:
    """A numbered disc, the step markers of the assembly figures."""
    return f'<circle class="dot q-high" cx="{x:.1f}" cy="{y:.1f}" r="{w / 2:.1f}"/>' + text(
        x, y + 4.5, str(n), "lbl strong q-high-t", "middle"
    )


def bench_pucks(cfg: BoardConfig) -> list[dict]:
    """The four test pieces of the bench with their numbers from the yaml:
    capacitor, note, coil envelope, turns and wire of the calculator."""
    plan = frequency_plan(cfg)
    p = cfg.pitch.plateau_mm
    geometry = resolve_geometry(cfg, p).classes
    rows = []
    for tp in cfg.mockup.test_pieces:
        line = plan.line(tp.piece, tp.color)
        d = piece_coil_design(cfg, tp.piece, p)
        geo = geometry[tp.piece]
        rows.append(
            {
                "piece": tp.piece,
                "name": piece_name(tp.piece, tp.color),
                "glyph": FR_PIECE[tp.piece.value][3],
                "cap_nF": line.cap_nF,
                "f0_khz": line.f0_hz / 1e3,
                "d_out": d.d_out_mm,
                "d_in": d.d_in_mm,
                "turns": d.n_turns,
                "wire": d.wire_mm,
                "magnet_d": geo.magnet_d_mm,
                "base_d": geo.base_mm,
            }
        )
    return rows


def fig_bench_inventory(cfg: BoardConfig) -> str:
    """What the bench is made of, stacked as it will be used."""
    w, h = 960, 600
    reduced = cfg.plateau.quadrant.reduced
    p = cfg.pitch.plateau_mm
    board_w = reduced.squares * p + cfg.plateau.quadrant.front_end_strip_mm
    board_h = reduced.squares * p + reduced.strip_overhang_mm
    shield_w, shield_h = cfg.bench.shield.board_mm
    pucks = bench_pucks(cfg)
    out = [
        svg_open(
            w,
            h,
            "Ce que reunit le banc : a gauche la Nucleo sous la carte de banc reliee au 12 V "
            "et au PC, a droite le quadrant 2 x 2 sous le contreplaque et le feutre avec "
            "les quatre pucks de test, la nappe entre les deux",
        ),
        f"<defs>{arrow_marker('arr20')}{arrow_marker('arr20b', both=True)}</defs>",
    ]
    # ---- left: the Nucleo and the shield, seen from the side, exploded
    out.append(text(20, 24, "LE CÔTÉ MESURE", "lbl mono muted"))
    nx, ny = 170, 330  # the Nucleo board
    sy = ny - 90  # the shield board
    out.append(f'<rect class="lay-pcb" x="{nx}" y="{ny}" width="300" height="14"/>')
    out.append(
        f'<rect class="box-soft" x="{nx + 10}" y="{ny - 26}" width="46" height="26" rx="3"/>'
    )
    out.append(text(nx + 33, ny - 9, "USB", "lbl small", "middle"))
    for x in (nx + 100, nx + 150, nx + 200, nx + 250):  # the female headers
        out.append(f'<rect class="box" x="{x}" y="{ny - 18}" width="34" height="18" rx="2"/>')
    out.append(
        _label(
            nx,
            ny + 34,
            [
                "Nucleo-G474RE",
                "le même microcontrôleur que le cerveau,",
                "sa sonde de programmation, son port série",
            ],
        )
    )
    out.append(f'<rect class="lay-pcb" x="{nx + 60}" y="{sy}" width="270" height="14"/>')
    for x in (nx + 100, nx + 150, nx + 200, nx + 250):  # the male headers, body under the shield
        out.append(f'<rect class="box" x="{x + 6}" y="{sy + 14}" width="22" height="12" rx="1"/>')
        for k in range(3):
            xx = x + 10 + k * 7
            out.append(f'<line class="wire" x1="{xx}" y1="{sy + 26}" x2="{xx}" y2="{sy + 46}"/>')
    parts = [
        (nx + 66, 48, "jack 12 V"),
        (nx + 130, 26, "buck 5 V"),
        (nx + 186, 26, "LDO 5VA"),
        (nx + 240, 26, "tampon"),
        (nx + 290, 36, "FPC"),
    ]
    for x, pw, name in parts:
        out.append(f'<rect class="box" x="{x}" y="{sy - 18}" width="{pw}" height="18" rx="2"/>')
        out.append(text(x + pw / 2, sy - 6, name, "lbl small", "middle"))
    out.append(_arrow(nx + 190, sy + 50, nx + 190, ny - 24, "arr20"))
    out.append(text(nx + 198, sy + 70, "s'emboîte sur les embases Arduino", "lbl small muted"))
    out.append(
        _label(
            nx + 60,
            sy - 62,
            [
                f"Carte de banc, {fr_num(shield_w, 0)} x {fr_num(shield_h, 0)} mm",
                "le 12 V protégé, le 5 V des LED, le 5 V analogique,",
                "le tampon LED et le connecteur de nappe",
            ],
        )
    )
    # supply and PC, at the far left
    out.append(
        _box(
            20,
            sy - 30,
            130,
            54,
            ["Alimentation 12 V", "de laboratoire,", "limitée en courant"],
            "box-warm",
        )
    )
    out.append(_path(f"M150 {sy - 3} H{nx + 40} V{sy - 9} H{nx + 62}", "arr20", "wire-p"))
    out.append(
        _box(20, ny - 26, 130, 54, ["PC", "console série 115200", "make NUCLEO=1"], "box-soft")
    )
    out.append(_arrow(150, ny - 13, nx + 8, ny - 13, "arr20"))
    # ---- right: the quadrant under wood and felt, with the pucks
    out.append(text(540, 24, "LE CÔTÉ ÉCHIQUIER", "lbl mono muted"))
    qx, qy, qw = 540, 420, 380
    out.append(f'<rect class="lay-pcb" x="{qx}" y="{qy}" width="{qw}" height="14"/>')
    strip = qw * cfg.plateau.quadrant.front_end_strip_mm / board_w
    out.append(
        f'<rect class="box-soft" x="{qx}" y="{qy - 16}" width="{strip:.0f}" height="16" rx="2"/>'
    )
    out.append(text(qx + strip / 2, qy - 5, "frontal", "lbl small", "middle"))
    out.append(f'<rect class="box" x="{qx + 2}" y="{qy - 30}" width="30" height="14" rx="2"/>')
    out.append(text(qx + 17, qy - 20, "FPC", "lbl small", "middle"))
    sq = (qw - strip) / reduced.squares
    for k in range(reduced.squares):  # the two squares with their spirals
        cx = qx + strip + sq * (k + 0.5)
        for r in (0.42, 0.3, 0.18):
            out.append(
                f'<ellipse class="coil" cx="{cx:.1f}" cy="{qy + 7}" rx="{sq * r:.1f}" ry="4"/>'
            )
    out.append(
        _label(
            qx,
            qy + 34,
            [
                f"Quadrant 2 x 2, {fr_num(board_w, 0)} x {fr_num(board_h, 0)} mm, 4 couches",
                "quatre spirales gravées dans le circuit, huit LED,",
                "le frontal analogique complet sur sa bande",
            ],
        )
    )
    # wood and felt, exploded above the quadrant
    wy = qy - 92
    wood_h = cfg.gap.surface_mm * 6
    felt_h = cfg.gap.felt_mm * 6 + 1
    out.append(
        f'<rect class="lay-wood" x="{qx + strip}" y="{wy}" width="{qw - strip:.0f}" '
        f'height="{wood_h:.0f}"/>'
    )
    out.append(
        f'<rect class="lay-felt" x="{qx + strip}" y="{wy - felt_h:.1f}" '
        f'width="{qw - strip:.0f}" height="{felt_h:.1f}"/>'
    )
    out.append(
        _lines(
            qx + strip + 8,
            wy + wood_h + 22,
            [
                f"contreplaqué {fr_num(cfg.gap.surface_mm)} mm et feutre "
                f"{fr_num(cfg.gap.felt_mm)} mm sur des entretoises :",
                f"{fr_num(cfg.gap.air_mm)} mm d'air pour les LED, "
                f"{fr_num(cfg.gap.nominal_total_mm)} mm d'entrefer sous la pièce,",
                "deux trous de 2,5 mm par case au droit des LED",
            ],
        )
    )
    # pucks on the felt
    py = wy - felt_h - 1
    for k, row in enumerate(pucks[: reduced.squares]):
        cx = qx + strip + sq * (k + 0.5)
        pw = sq * 0.45
        out.append(
            f'<path class="puck" d="M{cx - pw / 2:.1f} {py:.1f} v-14 q0 -10 10 -10 '
            f'h{pw - 20:.1f} q10 0 10 10 v14 z"/>'
        )
        out.append(text(cx, py - 8, row["glyph"], "glyph", "middle"))
    out.append(
        _label(
            qx + strip + 30,
            140,
            [
                "Quatre pucks de test imprimés",
                "bobine bobinée sur gabarit, condensateur C0G,",
                "aimant ferrite ; pion, cavalier, fou, tour noirs :",
                ", ".join(f"{r['glyph']} {fr_num(r['cap_nF'])} nF" for r in pucks),
            ],
        )
    )
    # the cable between the two
    out.append(
        _path(
            f"M{nx + 308} {sy - 20} C{nx + 308} {sy - 90} {qx - 40} {qy - 160} {qx + 17} {qy - 32}",
            "arr20b",
            "wire-a",
        )
    )
    out.append(text(500, 92, "nappe FPC 16 conducteurs, pas 0,5 mm :", "lbl small q-high-t"))
    out.append(
        text(500, 106, "le bus de commande, le signal amplifié, les rails", "lbl small muted")
    )
    # foot
    out.append(
        _lines(
            20,
            560,
            [
                "Rien de tout cela n'est le plateau final : le cerveau et la carte puissance "
                "attendent que ce banc ait mesuré",
                "ce qui n'a été que calculé (note 19). Le firmware, le bus de commande et le "
                "quadrant sont ceux du plateau.",
            ],
        )
    )
    out.append("</svg>")
    return "\n".join(out)


def fig_shield_assembly(cfg: BoardConfig) -> str:
    """Cross-section of the shield on the Nucleo and the soldering order."""
    w, h = 960, 520
    out = [
        svg_open(
            w,
            h,
            "Coupe de la carte de banc emboitee sur la Nucleo : composants dessus, barrettes males "
            "soudees cote cuivre avec le corps sous la carte, et l'ordre de soudure en six etapes",
        ),
        f"<defs>{arrow_marker('arr21')}</defs>",
    ]
    out.append(text(20, 24, "EN COUPE, UNE FOIS EMBOÎTÉE", "lbl mono muted"))
    x0, sx = 60, 520
    ny = 290  # Nucleo pcb top
    sy = 200  # shield pcb top
    out.append(f'<rect class="lay-pcb" x="{x0}" y="{ny}" width="{sx}" height="16"/>')
    out.append(text(x0 + sx + 8, ny + 12, "Nucleo", "lbl small muted"))
    out.append(f'<rect class="lay-pcb" x="{x0 + 40}" y="{sy}" width="{sx - 40}" height="16"/>')
    out.append(text(x0 + sx + 8, sy + 12, "carte de banc", "lbl small muted"))
    for hx in (x0 + 110, x0 + 280, x0 + 420):  # female headers below, male headers through
        out.append(f'<rect class="box" x="{hx}" y="{ny - 30}" width="60" height="30" rx="2"/>')
        out.append(
            f'<rect class="box-soft" x="{hx + 6}" y="{sy + 16}" width="48" height="10" rx="1"/>'
        )
        for k in range(4):
            xx = hx + 12 + k * 12
            out.append(f'<line class="wire" x1="{xx}" y1="{sy - 6}" x2="{xx}" y2="{ny - 8}"/>')
    tops = [
        (x0 + 50, 44, 18, "jack 12 V"),
        (x0 + 130, 26, 12, "buck"),
        (x0 + 185, 20, 10, "LDO"),
        (x0 + 240, 30, 10, "FPC"),
        (x0 + 350, 14, 10, "tampon"),
        (x0 + 400, 26, 16, "JP1"),
    ]
    for x, pw, ph, name in tops:
        out.append(f'<rect class="box" x="{x}" y="{sy - ph}" width="{pw}" height="{ph}" rx="2"/>')
        out.append(text(x + pw / 2, sy - ph - 5, name, "lbl small", "middle"))
    out.append(_path(f"M{x0 + 270} {sy - 5} H{x0 + 300} V{sy - 46}", "arr21", "wire-a"))
    out.append(text(x0 + 306, sy - 40, "nappe vers le quadrant", "lbl small q-high-t"))
    out.append(f'<line class="dash" x1="{x0 + 20}" y1="{sy + 16}" x2="{x0 + 20}" y2="{ny}"/>')
    out.append(text(x0 + 12, (sy + ny) / 2 + 12, "~11 mm", "lbl small muted", "end"))
    out.append(
        _lines(
            x0,
            ny + 40,
            [
                "Les barrettes mâles : corps sous la carte de banc, broches vers le bas, soudées "
                "côté cuivre (dessous) ;",
                "leurs pointes dépassent à peine sur le dessus. Les embases femelles sont "
                "celles de la Nucleo.",
            ],
            "lbl small",
        )
    )
    out.append(
        _lines(
            x0,
            ny + 92,
            [
                "Pourquoi cet ordre : les petits boîtiers plats se posent sur une carte encore "
                "vide ; les barrettes viennent",
                "en dernier parce qu'une fois soudées la carte ne se pose plus à plat. Les "
                "emboîter dans la Nucleo avant de",
                "les souder garantit qu'elles restent perpendiculaires et au bon pas.",
            ],
        )
    )
    out.append(
        _lines(
            x0,
            ny + 156,
            [
                "Le cavalier JP1 : broches 1 et 2, le 5VA vient du LDO (position de départ) ; "
                "2 et 3, il vient du buck (mesure M8).",
            ],
            "lbl small",
        )
    )
    # ---- right: the order
    ox = 660
    out.append(text(ox, 24, "L'ORDRE DE SOUDURE", "lbl mono muted"))
    steps = [
        ("buck TPS62130, boîtier QFN", "air chaud ou plaque, pâte à braser"),
        ("les autres CMS", "LDO, tampon, diodes, perle, R et C"),
        ("connecteur FPC Hirose", "pattes fines : flux, fer fin, loupe"),
        ("jack, JP1, points de test", "traversants, fer classique"),
        ("les quatre barrettes mâles", "emboîtées dans la Nucleo, puis soudées"),
        ("contrôle à l'ohmmètre", "aucun rail en court-circuit à la masse"),
    ]
    for i, (t1, t2) in enumerate(steps):
        y = 60 + i * 64
        out.append(_step(ox + 14, y + 10, i + 1))
        out.append(text(ox + 36, y + 6, t1, "lbl strong"))
        out.append(text(ox + 36, y + 22, t2, "lbl small muted"))
    out.append("</svg>")
    return "\n".join(out)


def fig_puck_making(cfg: BoardConfig) -> str:
    """A test piece: the winding jig, the coil, the capacitor, the magnet, the puck."""
    w, h = 960, 560
    pucks = bench_pucks(cfg)
    coil = cfg.resonator.coil
    out = [
        svg_open(
            w,
            h,
            "Fabriquer un puck de test : bobiner le fil sur le gabarit imprime, coller, souder le "
            "condensateur, glisser bobine et aimant ferrite dans le puck ; tableau des quatre "
            "pucks avec condensateur, note attendue, diametres, tours et fil",
        ),
        f"<defs>{arrow_marker('arr22')}</defs>",
    ]
    # step 1: the jig
    out.append(_step(34, 40, 1))
    out.append(text(56, 45, "Bobiner sur le gabarit imprimé", "lbl strong"))
    jx, jy = 60, 120
    out.append(f'<rect class="box-soft" x="{jx}" y="{jy}" width="150" height="8" rx="2"/>')
    out.append(f'<rect class="box-soft" x="{jx}" y="{jy - 40}" width="150" height="8" rx="2"/>')
    out.append(f'<rect class="box" x="{jx + 55}" y="{jy - 40}" width="40" height="48"/>')
    out.append(f'<line class="wire" x1="{jx + 75}" y1="{jy - 70}" x2="{jx + 75}" y2="{jy + 30}"/>')
    out.append(text(jx + 82, jy - 58, "axe M3, dans une perceuse", "lbl small muted"))
    for k in range(6):  # wire turns in the window, in section
        yy = jy - 32 + k * 4.5
        out.append(
            f'<rect class="copper" x="{jx + 12}" y="{yy:.1f}" width="43" height="3" rx="1.5"/>'
        )
        out.append(
            f'<rect class="copper" x="{jx + 95}" y="{yy:.1f}" width="43" height="3" rx="1.5"/>'
        )
    out.append(
        _lines(
            jx,
            jy + 50,
            [
                f"fenêtre de {fr_num(coil.height_mm)} mm entre les flasques,",
                "fil émaillé, spires serrées, vernis, puis retirer la rondelle",
            ],
            "lbl small",
        )
    )
    # step 2: coil + capacitor
    out.append(_step(34, 240, 2))
    out.append(text(56, 245, "Souder le condensateur, une note par pièce", "lbl strong"))
    cx, cy = 110, 320
    for r in (34, 26, 18, 10):
        out.append(f'<circle class="coil" cx="{cx}" cy="{cy}" r="{r}"/>')
    out.append(f'<line class="wire" x1="{cx + 34}" y1="{cy - 2}" x2="{cx + 90}" y2="{cy - 12}"/>')
    out.append(f'<line class="wire" x1="{cx + 10}" y1="{cy}" x2="{cx + 90}" y2="{cy + 12}"/>')
    out.append(f'<rect class="cap" x="{cx + 88}" y="{cy - 16}" width="14" height="32" rx="2"/>')
    out.append(text(cx + 110, cy + 4, "C0G 1 %, boîtier 0805", "lbl small"))
    out.append(text(cx + 110, cy + 18, "aux deux bouts du fil dénudé", "lbl small muted"))
    out.append(
        _lines(
            60,
            380,
            [
                "bobine et condensateur font le résonateur :",
                f"L = {fr_num(cfg.resonator.L_target_uH, 0)} µH pour toutes les pièces, "
                "C change la note",
            ],
            "lbl small",
        )
    )
    # step 3: the puck cutaway
    out.append(_step(34, 440, 3))
    out.append(text(56, 445, "Glisser dans le puck, aimant au-dessus", "lbl strong"))
    px, py = 70, 470
    out.append(
        f'<path class="puck" d="M{px} {py + 70} v-58 q0 -12 12 -12 h116 q12 0 12 12 v58 z"/>'
    )
    out.append(f'<rect class="magnet" x="{px + 30}" y="{py + 22}" width="80" height="18"/>')
    out.append(text(px + 70, py + 35, "aimant ferrite", "lbl small", "middle"))
    for k in range(7):
        out.append(
            f'<rect class="copper" x="{px + 24 + k * 13}" y="{py + 48}" '
            'width="9" height="9" rx="2"/>'
        )
    out.append(
        _lines(
            px + 150,
            py + 29,
            [
                "fente latérale pour le condensateur",
                "poche d'aimant ajustée",
                "bobine dans les 2 mm du bas",
            ],
        )
    )
    # the table of the four pucks
    tx, ty = 470, 60
    out.append(text(tx, ty - 22, "LES QUATRE PUCKS DU BANC", "lbl mono muted"))
    cols = [(0, "pièce"), (130, "C"), (195, "note"), (265, "bobine"), (360, "tours"), (405, "fil")]
    for dx, name in cols:
        out.append(text(tx + dx, ty, name, "lbl small muted"))
    out.append(f'<line class="axis" x1="{tx}" y1="{ty + 6}" x2="{tx + 445}" y2="{ty + 6}"/>')
    for i, r in enumerate(pucks):
        y = ty + 30 + i * 26
        out.append(text(tx, y, f"{r['glyph']} {r['name']}", "lbl"))
        out.append(text(tx + 130, y, f"{fr_num(r['cap_nF'])} nF", "lbl mono"))
        out.append(text(tx + 195, y, f"{r['f0_khz']:.0f} kHz", "lbl mono q-high-t"))
        out.append(text(tx + 265, y, f"ø {fr_num(r['d_out'])} / {fr_num(r['d_in'])}", "lbl mono"))
        out.append(text(tx + 360, y, f"{r['turns']}", "lbl mono"))
        out.append(text(tx + 405, y, f"{fr_num(r['wire'], 3)}", "lbl mono"))
    y = ty + 30 + len(pucks) * 26 + 6
    magnets = sorted({round(r["magnet_d"], 1) for r in pucks})
    out.append(
        _lines(
            tx,
            y,
            [
                "bobine : diamètres extérieur et intérieur, mm ; fil : diamètre du cuivre, mm ;",
                f"tours calculés pour {fr_num(cfg.resonator.L_target_uH, 0)} µH "
                f"(± {fr_num(cfg.resonator.L_tol_pct, 0)} % à la main, soit "
                f"± {fr_num(cfg.resonator.L_tol_pct / 2, 1)} % sur la note) ;",
                f"aimants ferrite SrFe, épaisseur {fr_num(cfg.piece_magnet.thickness_mm, 0)} mm, "
                f"diamètres {', '.join(fr_num(d) for d in magnets)} mm selon la pièce.",
            ],
        )
    )
    out.append(
        _lines(
            tx,
            y + 62,
            [
                "Pourquoi ces quatre-là : le bas de la bande, là où les notes",
                "sont les plus serrées. Si le banc les distingue sans erreur,",
                "les huit autres classes, plus espacées, suivront.",
            ],
            "lbl small",
        )
    )
    out.append(
        _lines(
            tx,
            y + 124,
            [
                f"La pièce sonne à travers {fr_num(cfg.gap.nominal_total_mm)} mm : "
                "le circuit imprimé, l'air,",
                "le bois et le feutre. Le banc mesure ce que cet entrefer laisse passer.",
            ],
        )
    )
    out.append("</svg>")
    return "\n".join(out)


def fig_bench_tests(cfg: BoardConfig) -> str:
    """The test ladder: each rung a check, what to do, what to expect."""
    w, h = 960, 640
    plan = frequency_plan(cfg)
    pawn = plan.line(PieceType.PAWN, cfg.mockup.test_pieces[0].color)
    window = listen_window_us(cfg)
    q_min = cfg.resonator.q_min_with_magnet
    out = [
        svg_open(
            w,
            h,
            "L'echelle des tests du banc, du bas vers le haut : ohmmetre carte seule, 12 V seul et "
            "points de test, Nucleo et console, quadrant et nappe, un puck et sa note, les quatre "
            "pucks avec la calibration et les LED, puis la campagne de mesures M1 a M11",
        ),
        f"<defs>{arrow_marker('arr23')}</defs>",
    ]
    rungs = [
        (
            "Carte seule, ohmmètre",
            "entre VIN, 5V, 5VA, 3V3 et la masse (points de test)",
            "jamais zéro ohm : pas de court-circuit",
            "box box-soft",
        ),
        (
            "12 V seul, sans Nucleo",
            "alimentation limitée à 100 mA, jack branché",
            "TP6 12 V, TP3 5,0 V, TP2 5,0 V ; moins de 30 mA",
            "box box-soft",
        ),
        (
            "Nucleo et console",
            "USB, 115200 bauds, firmware make NUCLEO=1, touche h",
            "TP4 3,3 V ; bannière « # LC chessboard, nucleo bench »",
            "box box-soft",
        ),
        (
            "Quadrant et nappe",
            "nappe engagée aux deux bouts, touche s",
            "quatre lignes CSV, amplitude faible : le bruit des cases vides",
            "box box-soft",
        ),
        (
            "Un puck, sa note",
            "pion noir sur une case, touche s, puis r pour le brut",
            f"fa ≈ {pawn.f0_hz / 1e3:.0f} kHz à ± 3 % ; "
            f"l'enveloppe dure la fenêtre de {fr_num(window, 0)} µs",
            "box box-piece",
        ),
        (
            "Quatre pucks, calibration, LED",
            "un puck par case, touche c, puis i, puis l",
            "i nomme les quatre pucks sans erreur, l allume leurs cases",
            "box box-piece",
        ),
        (
            "La campagne M1 à M11",
            "protocole measurements/protocol.md, un CSV par mesure",
            f"Q ≥ {q_min:.0f} avec la ferrite (M2) : la mesure qui décide",
            "box box-warm",
        ),
    ]
    out.append(
        text(
            40, 40, "Monter un échelon à la fois : on ne passe au suivant qu'une fois", "lbl small"
        )
    )
    out.append(text(40, 54, "le précédent réussi, et on note ce qu'on a lu.", "lbl small"))
    x, bw = 40, 600
    for i, (t1, t2, t3, cls) in enumerate(rungs):
        y = 560 - i * 76
        out.append(f'<rect class="{cls}" x="{x}" y="{y}" width="{bw}" height="62" rx="6"/>')
        out.append(_step(x + 26, y + 31, i + 1))
        out.append(text(x + 50, y + 22, t1, "lbl strong"))
        out.append(text(x + 50, y + 39, t2, "lbl small"))
        out.append(text(x + 50, y + 54, t3, "lbl small q-high-t"))
        if i:
            out.append(_arrow(x + bw + 14, y + 76 + 60, x + bw + 14, y + 66, "arr23"))
    # the CSV legend
    lx = 690
    out.append(text(lx, 40, "CE QUE LA CONSOLE ÉCRIT", "lbl mono muted"))
    out.append(text(lx, 62, "q,coil,sq,fa_hz,fb_hz,amp_mv,snr_db10", "lbl mono small"))
    legend = [
        ("q, coil, sq", ["quadrant, bobine, case", "(a1 = 0, b1 = 1, a2 = 8, b2 = 9)"]),
        ("fa_hz", ["la note par FFT, à 1 kHz près"]),
        ("fb_hz", ["la même note par comptage de période"]),
        ("amp_mv", ["l'amplitude de la sonnerie"]),
        ("snr_db10", ["signal sur bruit, en dixièmes de dB"]),
    ]
    y = 88
    for k, lines in legend:
        out.append(text(lx, y, k, "lbl mono small strong"))
        out.append(_lines(lx, y + 14, lines))
        y += 18 + 14 * len(lines)
    y += 10
    out.append(text(lx, y, "LES TOUCHES", "lbl mono muted"))
    keys = [
        ("h", "aide"),
        ("s", "un balayage"),
        ("m / x", "balayage répété, stop"),
        ("r", "512 points bruts de la case a1"),
        ("c", "calibrer, en flash"),
        ("i", "identifier"),
        ("l / o", "LED des cases reconnues, extinction"),
        ("p / P", "impulsion plus courte, plus longue"),
    ]
    for i, (k, v) in enumerate(keys):
        yy = y + 24 + i * 20
        out.append(text(lx, yy, k, "lbl mono small strong"))
        out.append(text(lx + 46, yy, v, "lbl small"))
    y = y + 24 + len(keys) * 20 + 12
    out.append(text(lx, y, "À l'oscilloscope, avant de croire", "lbl small strong"))
    out.append(text(lx, y + 14, "le firmware :", "lbl small strong"))
    out.append(
        _lines(
            lx,
            y + 32,
            [
                "TP1 du quadrant (AMP_OUT) et TP3",
                "(bus d'impulsion) ; la sonnerie doit",
                "remplir la fenêtre sans écrêter, sinon",
                "changer la résistance de gain (note 19).",
            ],
        )
    )
    out.append("</svg>")
    return "\n".join(out)
