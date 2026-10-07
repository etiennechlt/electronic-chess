"""The page on the Hall plus RFID alternative (`docs/pages/hall-rfid.html`),
the browser twin of note 24, in three readings: simplified, technical,
implementation. One file, three panels, a switch at the top.
"""

from __future__ import annotations

from chessboard_calc.config import BoardConfig, PieceType
from chessboard_calc.hall import (
    adc_lsb_mv,
    amplitude_classes,
    hall_budget,
    hall_power,
    hall_scan,
    sensor_gap_mm,
)
from chessboard_calc.inductance import pcb_sense_coil
from chessboard_calc.nfc import analog_mux_verdict, antenna, link, tag
from chessboard_calc.power import autonomy_h

from .common import fr_num
from .hall import (
    curve_json,
    fig_hall_classes,
    fig_hall_curve,
    fig_hall_scan,
    fig_hall_stack,
    fig_nfc_switch,
)
from .page import check, document

PIECE_FR = {
    PieceType.PAWN: "pion",
    PieceType.KNIGHT: "cavalier",
    PieceType.BISHOP: "fou",
    PieceType.ROOK: "tour",
    PieceType.QUEEN: "dame",
    PieceType.KING: "roi",
}

OTHER_PITCHES_MM = (40.0, 50.0, 55.0, 60.0)


def _piece_rows(cfg: BoardConfig) -> str:
    b = hall_budget(cfg, cfg.pitch.plateau_mm)
    rows = []
    for piece in PieceType:
        f = b.fields[piece]
        rows.append(
            f"<tr><td>{PIECE_FR[piece]}</td>"
            f'<td class="n">{fr_num(f.magnet_d_mm)} x {fr_num(f.magnet_t_mm, 0)}</td>'
            f'<td class="n">{fr_num(f.b_nominal_mT)}</td>'
            f'<td class="n">{fr_num(f.b_max_gap_mT)}</td>'
            f'<td class="n">{fr_num(f.b_lifted_mT)}</td>'
            f'<td class="n">{fr_num(f.b_neighbor_mT, 2)}</td>'
            f'<td class="n">{fr_num(f.out_nominal_mv, 0)} / {fr_num(f.out_nominal_lsb, 0)}</td></tr>'
        )
    return "\n".join(rows)


def _pitch_rows(cfg: BoardConfig) -> str:
    rows = []
    for p in OTHER_PITCHES_MM:
        b = hall_budget(cfg, p)
        coded = amplitude_classes(cfg, p, size_coded=True)
        ln = link(cfg, p)
        mark = " (le projet)" if p == cfg.pitch.plateau_mm else ""
        rows.append(
            f"<tr><td>{fr_num(p, 0)}{mark}</td>"
            f'<td class="n">{fr_num(b.fields[PieceType.PAWN].b_nominal_mT)}</td>'
            f'<td class="n">{fr_num(b.fields[PieceType.KING].b_lifted_mT)}</td>'
            f'<td class="n">{fr_num(b.lift_margin)}</td>'
            f'<td class="n">{fr_num(b.crosstalk_db)}</td>'
            f'<td class="n">{coded.separable_groups}</td>'
            f'<td class="n">{fr_num(ln.k, 2)}</td>'
            f'<td class="n">{fr_num(ln.h_margin)}</td></tr>'
        )
    return "\n".join(rows)


def _power_rows(cfg: BoardConfig) -> str:
    rows = []
    for i, sensor in enumerate(cfg.hall_rfid.sensors):
        for gated in (False, True):
            hp = hall_power(cfg, gated, i)
            mode = f"{cfg.hall_rfid.power_gating.groups} groupes" if gated else "continue"
            rows.append(
                f"<tr><td>{sensor.part}</td><td>{mode}</td>"
                f'<td class="n">{fr_num(hp.current_ma, 0)}</td>'
                f'<td class="n">{fr_num(hp.power_w, 2)}</td>'
                f'<td class="n">{fr_num(hp.autonomy_h, 0)}</td></tr>'
            )
    return "\n".join(rows)


def _pin_rows(cfg: BoardConfig) -> str:
    roles = {
        "ADC_Q": "sortie du multiplexeur du quadrant, entrée ADC1",
        "MUX_S": "bit d'adresse, commun aux quatre multiplexeurs",
        "ROW_EN": "grille du P-FET d'une rangée, actif bas",
    }
    rows = []
    for name, gpio in cfg.hall_rfid.esp32.pins.items():
        role = next((r for k, r in roles.items() if name.startswith(k)), "")
        rows.append(
            f'<tr><td><code>{name}</code></td><td class="n">GPIO{gpio}</td><td>{role}</td></tr>'
        )
    return "\n".join(rows)


def _spans(cfg: BoardConfig, size_coded: bool) -> str:
    rep = amplitude_classes(cfg, cfg.pitch.plateau_mm, size_coded=size_coded)
    parts = []
    for c in rep.classes:
        names = ", ".join(PIECE_FR[p] for p in c.pieces)
        parts.append(
            f"{names} ({fr_num(c.magnet_t_mm, 0)} mm) de {fr_num(c.b_low_mT, 0)} à "
            f"{fr_num(c.b_high_mT, 0)} mT"
        )
    return " ; ".join(parts)


def hall_page(cfg: BoardConfig) -> str:
    hr = cfg.hall_rfid
    p = cfg.pitch.plateau_mm
    b = hall_budget(cfg, p)
    sensor = b.sensor
    pf, kf = b.fields[PieceType.PAWN], b.fields[PieceType.KING]
    uni = amplitude_classes(cfg, p)
    coded = amplitude_classes(cfg, p, size_coded=True)
    sc = hall_scan(cfg, gated=True)
    sc_cont = hall_scan(cfg, gated=False)
    hp_cont = hall_power(cfg, gated=False)
    hp_gated = hall_power(cfg, gated=True)
    hp_ss = hall_power(cfg, gated=False, sensor_index=1)
    ant = antenna(cfg, p)
    tg = tag(cfg)
    near = link(cfg, p)
    far = link(cfg, p, cfg.gap.max_total_mm - cfg.gap.nominal_total_mm)
    mux = analog_mux_verdict(cfg, p)
    lsb = adc_lsb_mv(cfg)
    s4 = pcb_sense_coil(cfg, p)
    raw3 = cfg.model_dump()
    raw3["sense_coil"]["layers"] = 3
    s3 = pcb_sense_coil(BoardConfig.model_validate(raw3), p)
    z_json, bp_json, bk_json = curve_json(cfg)

    def counts(field_mt: float) -> str:
        return str(int(round(field_mt * sensor.sensitivity_mv_per_mt / lsb)))

    v = {
        "FIG_STACK_S": fig_hall_stack(cfg, uid="-s"),
        "FIG_STACK_T": fig_hall_stack(cfg, uid="-t"),
        "FIG_CURVE": fig_hall_curve(cfg, interactive=True),
        "FIG_CLASSES": fig_hall_classes(cfg),
        "FIG_SCAN_T": fig_hall_scan(cfg, uid="-t"),
        "FIG_SCAN_I": fig_hall_scan(cfg, uid="-i"),
        "FIG_NFC": fig_nfc_switch(cfg),
        "PIECE_ROWS": _piece_rows(cfg),
        "PITCH_ROWS": _pitch_rows(cfg),
        "POWER_ROWS": _power_rows(cfg),
        "PIN_ROWS": _pin_rows(cfg),
        "P": fr_num(p, 0),
        "GRID2": str(cfg.plateau.grid**2),
        "SENSOR": sensor.part,
        "SENSOR2": hr.sensors[1].part,
        "SENS_MV": fr_num(sensor.sensitivity_mv_per_mt, 0),
        "SENSOR_H": fr_num(sensor.height_mm),
        "SENSOR_I": fr_num(sensor.i_supply_ma),
        "SENSOR2_I": fr_num(hr.sensors[1].i_supply_ma),
        "VQ": fr_num(sensor.quiescent_out_v, 2),
        "AIR": fr_num(cfg.gap.air_mm),
        "WOOD": fr_num(cfg.gap.surface_mm),
        "FELT": fr_num(cfg.gap.felt_mm),
        "COIL_H": fr_num(cfg.resonator.coil.height_mm),
        "DIE": fr_num(hr.layout.die_height_mm),
        "Z_NOM": fr_num(b.z_nominal_mm),
        "Z_MAX": fr_num(b.z_max_mm),
        "GAP_NOM": fr_num(cfg.gap.nominal_total_mm),
        "GAP_MAX": fr_num(cfg.gap.max_total_mm),
        "BR": fr_num(cfg.piece_magnet.br_T, 2),
        "MAG_T": fr_num(cfg.piece_magnet.thickness_mm, 0),
        "PAWN_D": fr_num(pf.magnet_d_mm),
        "KING_D": fr_num(kf.magnet_d_mm),
        "B_PAWN": fr_num(pf.b_nominal_mT),
        "B_PAWN_MAX": fr_num(pf.b_max_gap_mT),
        "B_KING": fr_num(kf.b_nominal_mT),
        "B_KING_LIFT": fr_num(kf.b_lifted_mT),
        "B_KING_PRESS": fr_num(kf.b_pressed_mT),
        "B_NB": fr_num(abs(kf.b_neighbor_mT), 2),
        "LIFT_MM": fr_num(hr.layout.lift_detect_mm, 0),
        "TILT": fr_num(hr.layout.tilt_budget_mm),
        "THR": fr_num(b.threshold_mT),
        "REL": fr_num(b.release_mT),
        "THR_FRAC": fr_num(hr.presence.threshold_fraction * 100, 0),
        "HYS_FRAC": fr_num(hr.presence.hysteresis_fraction * 100, 0),
        "LIFT_MARGIN": fr_num(b.lift_margin),
        "LIFT_MIN": fr_num(hr.presence.min_lift_margin),
        "NB_N": str(hr.layout.neighbors_worst_case),
        "NB_SUM": fr_num(b.neighbors_sum_mT, 2),
        "XTALK": fr_num(b.crosstalk_db),
        "XTALK_MAX": fr_num(cfg.measurement.crosstalk_max_db, 0),
        "LSB_WEAK": fr_num(b.weakest_present_lsb, 0),
        "NOISE_MARGIN": fr_num(b.noise_margin, 0),
        "NOISE_LSB": fr_num(hr.esp32.adc_noise_lsb_rms, 0),
        "LSB_MV": fr_num(lsb, 3),
        "ADC_BITS": str(hr.esp32.adc_bits),
        "ADC_FS": fr_num(hr.esp32.adc_full_scale_mv, 0),
        "OUT_PAWN_MV": fr_num(pf.out_nominal_mv, 0),
        "UNI_GROUPS": str(uni.separable_groups),
        "CODED_GROUPS": str(coded.separable_groups),
        "UNI_SPANS": _spans(cfg, False),
        "CODED_SPANS": _spans(cfg, True),
        "CODED_MAX": fr_num(coded.strongest_mT, 0),
        "CODED_T": ", ".join(
            f"{PIECE_FR[k]} +{fr_num(x, 0)} mm"
            for k, x in hr.size_coding.thickness_extra_mm.items()
        ),
        "I_CONT": fr_num(hp_cont.current_ma, 0),
        "P_CONT": fr_num(hp_cont.power_w, 2),
        "AUT_CONT": fr_num(hp_cont.autonomy_h, 0),
        "I_GATED": fr_num(hp_gated.current_ma, 0),
        "P_GATED": fr_num(hp_gated.power_w, 2),
        "AUT_GATED": fr_num(hp_gated.autonomy_h, 0),
        "AUT_BASE": fr_num(autonomy_h(cfg, engine_on=False), 0),
        "I_SS": fr_num(hp_ss.current_ma, 0),
        "P_SS": fr_num(hp_ss.power_w, 2),
        "AUT_SS": fr_num(hp_ss.autonomy_h, 0),
        "GROUPS": str(hr.power_gating.groups),
        "SQ_US": fr_num(sc.square_us, 0),
        "BOARD_MS": fr_num(sc.board_ms, 1),
        "RATE": fr_num(sc.rate_hz, 0),
        "RATE_CONT": fr_num(sc_cont.rate_hz, 0),
        "SAMPLES": str(hr.esp32.samples_per_square),
        "SAMPLE_US": fr_num(hr.esp32.adc_sample_us, 0),
        "SETTLE_US": fr_num(hr.mux.t_settle_us, 0),
        "POWER_ON_US": fr_num(sensor.power_on_us, 0),
        "IDLE_SCAN": fr_num(cfg.measurement.idle_scan_hz, 0),
        "MUX": hr.mux.part,
        "MUX_RON": fr_num(hr.mux.ron_ohm, 0),
        "MUX_CH": str(hr.mux.channels),
        "ESP": hr.esp32.module,
        "TURNS4": str(s4.turns_per_layer),
        "TRACK4": fr_num(s4.track_width_mm, 2),
        "ESR4": fr_num(s4.esr_ohm, 2),
        "TURNS3": str(s3.turns_per_layer),
        "TRACK3": fr_num(s3.track_width_mm, 2),
        "ESR3": fr_num(s3.esr_ohm, 2),
        "SPIRAL_ID": fr_num(cfg.sense_coil.inner_ratio * p, 1),
        "F_NFC": fr_num(hr.nfc.f_hz / 1e6, 2),
        "ANT_SIDE": fr_num(ant.side_mm, 0),
        "ANT_TURNS": str(ant.turns),
        "ANT_L": fr_num(ant.L_uH, 2),
        "ANT_C": fr_num(ant.c_res_pF, 0),
        "ANT_R": fr_num(ant.r_series_ohm),
        "ANT_XL": fr_num(ant.x_l_ohm, 0),
        "Q_TARGET": fr_num(hr.nfc.antenna.q_target, 0),
        "TAG": tg.part,
        "TAG_D": fr_num(hr.nfc.tag.d_out_mm, 0),
        "TAG_TURNS": str(hr.nfc.tag.turns),
        "TAG_L": fr_num(tg.L_uH, 2),
        "TAG_C": fr_num(hr.nfc.tag.c_in_pF, 0),
        "TAG_F": fr_num(tg.f_self_mhz),
        "Z_NFC": fr_num(near.z_mm),
        "K": fr_num(near.k, 2),
        "H": fr_num(near.h_axis_a_per_m),
        "H_MIN": fr_num(hr.nfc.h_min_a_per_m),
        "H_MARGIN": fr_num(near.h_margin),
        "H_MARGIN_FAR": fr_num(far.h_margin),
        "I_ANT": fr_num(hr.nfc.antenna_current_ma_rms, 0),
        "MUX_Q": fr_num(mux.q_with_switch, 2),
        "MUX_CPAR": fr_num(mux.c_parasitic_pF, 0),
        "MUX_DETUNE": fr_num(abs(mux.detune_pct), 0),
        "BW_PCT": fr_num(100.0 / hr.nfc.antenna.q_target, 0),
        "READERS": ", ".join(hr.nfc.reader_candidates),
        "BASELINE_COUNTS": str(int(round(sensor.quiescent_out_v * 1e3 / lsb))),
        "ON_COUNTS": counts(b.threshold_mT),
        "OFF_COUNTS": counts(b.release_mT),
        "DEBOUNCE": str(hr.presence.debounce_scans),
        "Z_LIFT": fr_num(sensor_gap_mm(cfg, hr.layout.lift_detect_mm)),
        "Z_JSON": z_json,
        "BP_JSON": bp_json,
        "BK_JSON": bk_json,
        "N_FETS": str(
            hr.power_gating.groups * (cfg.plateau.grid // cfg.plateau.quadrant.squares) ** 2
        ),
    }
    page = document("Hall + RFID", HALL_BODY, HALL_SCRIPT, HALL_CSS)
    for k, val in v.items():
        page = page.replace("{{" + k + "}}", val)
    check(page)
    return page


HALL_CSS = r"""
.modes{display:flex; flex-wrap:wrap; gap:8px; margin:1.6rem 0 0; position:sticky; top:env(safe-area-inset-top,0px); background:var(--bg); padding-block:.6rem; z-index:3;}
.mode-btn{font:inherit; font-weight:600; font-size:.95rem; padding:.5rem 1rem; border-radius:999px; border:1px solid var(--rule); background:var(--surface); color:var(--ink-2); cursor:pointer;}
.mode-btn:hover{border-color:var(--q-high); color:var(--ink);}
.mode-btn.is-on{background:var(--q-high); border-color:var(--q-high); color:#fff;}
.mode-btn:focus-visible{outline:2px solid var(--q-low); outline-offset:2px;}
.mode-note{font-size:.85rem; color:var(--ink-3); margin:.5rem 0 0; max-width:68ch;}
.mode > section:first-of-type{border-top:0; margin-top:1.6rem; padding-top:0;}
.cards{display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:12px; margin:1.2rem 0; max-width:900px;}
.card{background:var(--surface); border:1px solid var(--rule); border-radius:8px; padding:.9rem 1rem; min-width:0;}
.card .big{font-family:"Bricolage Grotesque","IBM Plex Sans",Helvetica,Arial,sans-serif; font-size:1.8rem; font-weight:700; line-height:1.1; margin:0; font-variant-numeric:tabular-nums;}
.card .big small{font-size:.95rem; font-weight:500; color:var(--ink-2);}
.card .what{font-size:.86rem; color:var(--ink-2); margin:.35rem 0 0;}
.card.warm{border-left:4px solid var(--q-low);}
.card.cool{border-left:4px solid var(--q-high);}
.yesno{display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:12px; margin:1.2rem 0; max-width:900px;}
.yesno div{background:var(--surface); border:1px solid var(--rule); border-radius:8px; padding:.8rem 1rem; min-width:0;}
.yesno h3{margin:0 0 .4rem; font-size:1rem;}
.yesno ul{margin:0; padding-left:1.1rem;}
pre{background:var(--tint); border:1px solid var(--rule); border-radius:6px; padding:.8rem 1rem; overflow-x:auto; font-family:"IBM Plex Mono",Menlo,Consolas,monospace; font-size:.84rem; line-height:1.5; max-width:900px;}
pre code{background:none; padding:0; font-size:inherit;}
.steps{counter-reset:step; list-style:none; padding:0; max-width:72ch;}
.steps li{position:relative; padding-left:2.4rem; margin:.7rem 0;}
.steps li::before{counter-increment:step; content:counter(step); position:absolute; left:0; top:.05rem; width:1.7rem; height:1.7rem; border-radius:50%; background:var(--q-high); color:#fff; font-weight:600; font-size:.85rem; display:grid; place-items:center;}
@media (prefers-reduced-motion: reduce){ html{scroll-behavior:auto;} }
"""


HALL_BODY = r"""<div class="wrap">
<p class="eyebrow">Échiquier à résonateurs LC · note 24</p>
<h1>Hall + RFID</h1>
<p class="lede">Une autre façon de savoir où sont les pièces : un capteur magnétique sous chaque case, qui sent l'aimant que chaque pièce porte déjà, et une étiquette sans contact pour dire laquelle. Évaluée contre la détection LC du projet, comme remplacement et comme étape intermédiaire. Trois lectures de la même page : choisissez la vôtre.</p>

<nav class="modes" aria-label="Niveau de lecture">
<button type="button" class="mode-btn is-on" data-mode="simple" id="btn-simple" aria-pressed="true">Simplifié</button>
<button type="button" class="mode-btn" data-mode="technique" id="btn-technique" aria-pressed="false">Technique</button>
<button type="button" class="mode-btn" data-mode="implementation" id="btn-implementation" aria-pressed="false">Implémentation</button>
</nav>
<p class="mode-note">Même chiffres dans les trois lectures, calculés depuis le yaml du dépôt ; seul le niveau de détail change.</p>

<!-- ======================= SIMPLIFIÉ ======================= -->
<div class="mode" id="simple">
<section>
<p class="eyebrow">En deux minutes</p>
<h2>L'idée</h2>
<p>Chaque pièce de cet échiquier porte dans sa base un petit disque de ferrite, un aimant doux et bon marché, prévu à l'origine pour qu'un chariot caché sous le plateau puisse plus tard déplacer la pièce. Un capteur à effet Hall, un composant de la taille d'un grain de riz, mesure un champ magnétique. En posant un capteur sous chaque case, le plateau sait en permanence si une pièce est posée dessus ou non : l'aimant est là, ou il n'est plus là.</p>
<p>Ce que le capteur ne sait pas, c'est <b>quelle</b> pièce est posée. Un pion et une dame font à peu près le même champ. C'est pour cela que le brief ajoute une étiquette sans contact (RFID, la technologie des cartes de transport) dans chaque pièce, lue par une antenne sous la case. Le projet, lui, identifie les pièces autrement : chaque pièce contient un petit circuit accordé qui « sonne » à sa propre note quand la case le frappe, comme douze diapasons différents.</p>
<div class="keep">
<p><strong>Oui pour savoir où sont les pièces.</strong> Un pion posé donne {{B_PAWN}} mT au capteur, un roi soulevé de {{LIFT_MM}} mm n'en donne plus que {{B_KING_LIFT}} : impossible de les confondre, et les pièces voisines ne gênent pas.</p>
<p><strong>Non pour savoir lesquelles.</strong> Les aimants du projet donnent tous des champs qui se recouvrent : {{UNI_GROUPS}} seul groupe. L'étiquette RFID le saurait, mais lire 64 antennes avec un seul lecteur ne marche pas ; il faudrait un lecteur par case.</p>
<p><strong>Donc : une bonne première étape, pas un remplacement.</strong> Une carte simple, les pièces inchangées, et tout ce qui ne dépend pas de l'identité (jouer, arbitrer, allumer les cases, l'horloge) peut avancer pendant que la détection LC finit ses mesures.</p>
</div>
</section>

<section>
<p class="eyebrow">Comment ça marche</p>
<h2>Un aimant, un capteur, {{Z_NOM}} mm entre les deux</h2>
<figure>
<div class="fig-scroll">{{FIG_STACK_S}}</div>
<figcaption><b>La coupe sous une case.</b> La pièce repose sur le feutre et le contreplaqué ; dessous, une lame d'air de {{AIR}} mm où tiennent les LED et, désormais, le capteur, collé sur le circuit imprimé. L'aimant de la pièce est à {{Z_NOM}} mm de la plaque sensible du capteur. Le champ qui lui parvient vaut {{B_PAWN}} millitesla pour un pion : un aimant de frigo fait quelques dizaines de millitesla à son contact.</figcaption>
</figure>
<p>Le champ d'un aimant décroît vite avec la distance. C'est ce qui rend la chose fiable : posée, la pièce est tout près et le champ est fort ; soulevée de quelques centimètres, le champ s'effondre. Le plateau décide « présente » au-dessus d'un seuil, « absente » en dessous d'un second seuil un peu plus bas, pour ne pas hésiter quand la main tremble.</p>
<figure>
<div class="fig-scroll" id="fig-curve">{{FIG_CURVE}}<div class="tip" id="tip-curve" hidden></div></div>
<figcaption><b>Le champ selon la distance,</b> pour la plus petite pièce (pion) et la plus grosse (roi). La bande bleue est la plage normale quand la pièce est posée. Passez la souris sur la courbe pour lire les valeurs.</figcaption>
</figure>
</section>

<section>
<p class="eyebrow">Ce que ça donne</p>
<h2>Quatre chiffres à retenir</h2>
<div class="cards">
<div class="card cool"><p class="big">{{RATE}} <small>fois par seconde</small></p><p class="what">le plateau relit ses 64 cases ; la détection LC du projet ne balaie que {{IDLE_SCAN}} fois par seconde au repos</p></div>
<div class="card cool"><p class="big">{{LIFT_MARGIN}}<small> x</small></p><p class="what">de marge entre « posée » et « soulevée de {{LIFT_MM}} mm », pour la pièce la plus difficile</p></div>
<div class="card warm"><p class="big">{{UNI_GROUPS}} <small>groupe</small></p><p class="what">c'est tout ce que l'amplitude du champ permet de distinguer avec les aimants du projet : présence, pas identité</p></div>
<div class="card warm"><p class="big">{{AUT_GATED}} h <small>au lieu de {{AUT_BASE}}</small></p><p class="what">d'autonomie sur batterie, en n'alimentant les capteurs que par rangées ; {{AUT_CONT}} h si on les laisse tous allumés</p></div>
</div>
<div class="yesno">
<div><h3>Ce que la couche Hall sait faire</h3><ul>
<li>dire quelles cases sont occupées, et le voir changer en une fraction de seconde ;</li>
<li>voir une pièce quitter sa case avant même qu'elle soit reposée ailleurs ;</li>
<li>distinguer les blancs des noirs si l'on retourne les aimants d'un camp (en option) ;</li>
<li>fonctionner avec les pièces telles qu'elles sont déjà prévues.</li>
</ul></div>
<div><h3>Ce qu'elle ne sait pas faire</h3><ul>
<li>reconnaître une pièce : pion, cavalier ou dame se ressemblent pour elle ;</li>
<li>donc remettre une position arbitraire sur le plateau sans aide ;</li>
<li>savoir en quoi un pion a été promu.</li>
</ul></div>
</div>
<p>Pour jouer une partie normale, le plateau sait qui est où depuis la position de départ, et il suit chaque coup case par case : l'identité ne manque qu'au moment de la promotion, où l'on peut demander au joueur. C'est le compromis des plateaux du commerce les plus simples. La détection LC du projet, elle, reconnaît chaque pièce ; la couche Hall en devient le complément, pas le remplaçant.</p>
</section>

<section>
<p class="eyebrow">Et la RFID ?</p>
<h2>Pourquoi l'étiquette ne suffit pas</h2>
<p>L'étiquette dans la pièce fonctionne : à {{Z_NFC}} mm de l'antenne sous la case, elle reçoit {{H_MARGIN}} fois le champ minimal qu'exige la norme. Le problème est ailleurs. Une antenne RFID est un circuit accordé très fin, comme une corde de guitare tendue juste comme il faut. Pour lire 64 cases avec un seul lecteur, il faudrait brancher et débrancher ces 64 cordes avec un aiguilleur électronique. Or cet aiguilleur ajoute une résistance et une capacité qui désaccordent complètement la corde : elle ne sonne plus. Il reste à mettre un lecteur complet sous chaque case, soit 64 lecteurs, pour un coût du même ordre que l'électronique de la détection LC, qui, elle, reconnaît les pièces à tous les coups.</p>
<div class="keep">
<p><strong>Le verdict.</strong> Hall : oui, tout de suite, comme couche de présence, sur une carte simple. RFID : non sur le plateau, sauf en secours si la détection LC échouait à ses mesures. Détection LC : toujours la voie de l'identité.</p>
</div>
</section>
</div>

<!-- ======================= TECHNIQUE ======================= -->
<div class="mode" id="technique">
<section>
<p class="eyebrow">Le modèle</p>
<h2>Le champ d'un disque de ferrite au capteur</h2>
<p>L'aimant de pièce est un disque de ferrite SrFe (Br = {{BR}} T, ADR 0002), ø{{PAWN_D}} mm pour le pion à ø{{KING_D}} mm pour les pièces lourdes, {{MAG_T}} mm d'épaisseur, posé au-dessus de la bobine LC de {{COIL_H}} mm. Un disque uniformément aimanté équivaut à une nappe de courant K = Br/µ0 sur sa surface latérale : on l'empile en boucles de courant dont le champ hors axe est exact (intégrales elliptiques complètes), la même méthode par filaments que le couplage LC du dépôt. Sur l'axe, l'empilement retrouve la forme fermée à 10<sup>-3</sup> près ; en champ lointain, le dipôle.</p>
<div class="formulas">
<div class="formula"><p class="f">B(z) = Br/2 · [ (z+t)/√(R²+(z+t)²) − z/√(R²+z²) ]</p><p class="d">sur l'axe, z depuis la face de l'aimant, t son épaisseur, R son rayon</p></div>
<div class="formula"><p class="f">B<sub>z</sub>(ρ, z) = Σ boucles µ0 I/(2π) · [K(k) + (R²−ρ²−z²)/((R−ρ)²+z²) · E(k)] / √((R+ρ)²+z²)</p><p class="d">hors axe, pour la case voisine ; k² = 4Rρ/((R+ρ)²+z²)</p></div>
<div class="formula"><p class="f">B ≈ µ0 · 2m / (4π r³), m = Br·V/µ0</p><p class="d">dipôle en champ lointain, la vérification du modèle</p></div>
<div class="formula"><p class="f">z = air + bois + feutre + bobine − plaque = {{Z_NOM}} mm</p><p class="d">{{AIR}} + {{WOOD}} + {{FELT}} + {{COIL_H}} − {{DIE}} mm ; {{Z_MAX}} mm à l'entrefer maximal</p></div>
</div>
<figure>
<div class="fig-scroll">{{FIG_STACK_T}}</div>
<figcaption><b>Coupe à l'échelle.</b> Le capteur est en SOT-23 ({{SENSOR_H}} mm) dans la lame d'air de {{AIR}} mm ; le SS49E du brief, un SIP de 4 mm sur pattes, n'y tient pas, d'où le {{SENSOR}} ({{SENS_MV}} mV/mT, le moins sensible de sa famille, pour que le roi reste dans la plage linéaire) ou le {{SENSOR2}}, même puce que le SS49E en SOT-23.</figcaption>
</figure>
</section>

<section>
<p class="eyebrow">Présence</p>
<h2>Champs, seuils et marges au pas de {{P}} mm</h2>
<div class="tbl">
<table>
<thead><tr><th>pièce</th><th class="n">aimant (mm)</th><th class="n">B nominal (mT)</th><th class="n">B entrefer max (mT)</th><th class="n">B soulevée de {{LIFT_MM}} mm (mT)</th><th class="n">B case voisine (mT)</th><th class="n">sortie (mV / LSB)</th></tr></thead>
<tbody>
{{PIECE_ROWS}}
</tbody>
</table>
</div>
<p>Seuil de présence à {{THR_FRAC}} % du champ le plus faible attendu (pion à l'entrefer maximal, {{B_PAWN_MAX}} mT) : <b>{{THR}} mT</b> ; relâchement {{HYS_FRAC}} % plus bas : <b>{{REL}} mT</b>. Le roi soulevé de {{LIFT_MM}} mm donne {{B_KING_LIFT}} mT, soit une marge de <b>{{LIFT_MARGIN}}</b> sous le relâchement (critère {{LIFT_MIN}}). {{NB_N}} rois sur les cases voisines, latérales et diagonales, ajoutent {{NB_SUM}} mT en tout, soit <b>{{XTALK}} dB</b> du pion le plus faible (critère {{XTALK_MAX}} dB, celui de la chaîne LC). Le roi appuyé (entrefer réduit du budget d'inclinaison de {{TILT}} mm) fait {{B_KING_PRESS}} mT, dans la plage linéaire du capteur.</p>
<figure>
<div class="fig-scroll" id="fig-curve-t">{{FIG_CURVE}}<div class="tip" id="tip-curve-t" hidden></div></div>
<figcaption><b>B(z) du pion et du roi.</b> Bande bleue : entrefer nominal à maximal. Pointillés : seuil et relâchement. Le point du roi soulevé est à z = {{Z_LIFT}} mm.</figcaption>
</figure>
<p>Côté ADC ({{ESP}}, {{ADC_BITS}} bits, {{ADC_FS}} mV pleine échelle, {{LSB_MV}} mV par LSB) : le pion à l'entrefer maximal fait {{LSB_WEAK}} LSB, {{NOISE_MARGIN}} fois le bruit estimé de {{NOISE_LSB}} LSB efficaces après moyennage. Le repos du {{SENSOR}} à {{VQ}} V tombe au milieu de la plage, ce qui laisse la place aux deux polarités.</p>
</section>

<section>
<p class="eyebrow">Identité</p>
<h2>Ce qu'une amplitude peut séparer</h2>
<p>Chaque classe d'aimant occupe un intervalle de champ quand l'entrefer varie de nominal moins {{TILT}} mm à maximal plus {{TILT}} mm. Deux intervalles qui se recouvrent sont un seul groupe.</p>
<figure>
<div class="fig-scroll">{{FIG_CLASSES}}</div>
<figcaption><b>Aimants uniformes : {{UNI_GROUPS}} groupe</b> ({{UNI_SPANS}}). <b>Épaisseurs codées : {{CODED_GROUPS}} groupes</b> ({{CODED_SPANS}}), à {{CODED_MAX}} mT au plus, encore linéaire pour le {{SENSOR}}. Variante du yaml : {{CODED_T}}.</figcaption>
</figure>
<p>C'est la version chiffrée du « 2 à 4 classes au mieux » de l'ADR 0001. Retourner les aimants d'un camp double le compte par le signe de la sortie (six classes), mais interdit un aimant permanent sur le chariot : il repousserait un camp. Jamais douze classes ; l'identité reste à la fréquence LC.</p>
</section>

<section>
<p class="eyebrow">Courant et cadence</p>
<h2>{{GRID2}} capteurs, quatre multiplexeurs, un ADC</h2>
<div class="tbl">
<table>
<thead><tr><th>capteur</th><th>alimentation</th><th class="n">mA</th><th class="n">W</th><th class="n">autonomie humain contre humain (h), {{AUT_BASE}} sans</th></tr></thead>
<tbody>
{{POWER_ROWS}}
</tbody>
</table>
</div>
<p>Le courant de repos est le point dur : {{I_CONT}} mA pour {{GRID2}} {{SENSOR}} en continu, {{I_SS}} mA pour la puce du SS49E, plus que le plateau entier au repos. Un P-FET côté haut par rangée de quadrant ({{GROUPS}} groupes) n'alimente que la rangée lue : la moyenne tombe à {{I_GATED}} mA et l'autonomie remonte à {{AUT_GATED}} h.</p>
<figure>
<div class="fig-scroll">{{FIG_SCAN_T}}</div>
<figcaption><b>Le scanner.</b> Une case coûte {{SETTLE_US}} µs de commutation du {{MUX}} plus {{SAMPLES}} lectures de {{SAMPLE_US}} µs, soit {{SQ_US}} µs ; les quatre multiplexeurs sont lus en parallèle sur quatre entrées ADC1 ; avec {{POWER_ON_US}} µs de mise sous tension par rangée, le plateau est relu en {{BOARD_MS}} ms, {{RATE}} fois par seconde ({{RATE_CONT}} sans commutation).</figcaption>
</figure>
</section>

<section>
<p class="eyebrow">Sur le quadrant LC</p>
<h2>Où mettre le capteur</h2>
<p>Au centre de la case, et nulle part ailleurs : en bord de spirale, la pièce voisine donne un champ comparable à la pièce propre (même calcul hors axe) et l'attribution est perdue. Le centre de la spirale est libre sur {{SPIRAL_ID}} mm, mais les quatre couches portent chacune une spirale : aucune piste ne sort du centre sans croiser des spires.</p>
<div class="tbl">
<table>
<thead><tr><th>option</th><th>ce qu'elle coûte</th></tr></thead>
<tbody>
<tr><td>Quadrant en six couches</td><td>un palier de prix de carte ; rien ne change à la bobine</td></tr>
<tr><td>Spirale sur trois couches, la quatrième aux pistes Hall</td><td>même inductance cible : {{TURNS3}} spires par couche au lieu de {{TURNS4}}, piste de {{TRACK3}} mm au lieu de {{TRACK4}}, ESR de {{ESR4}} à {{ESR3}} Ω, Q de la bobine de case en baisse d'un tiers</td></tr>
<tr><td>Nappe Hall séparée, 0,6 mm, posée sur le quadrant dans la lame d'air</td><td>0,6 + {{SENSOR_H}} mm sous les {{AIR}} mm d'air, juste ; des pistes au-dessus des spirales à tenir en diaphonie ; la seule option qui existe avant le quadrant et sans lui</td></tr>
</tbody>
</table>
</div>
</section>

<section>
<p class="eyebrow">RFID</p>
<h2>Le bilan de liaison tient, la commutation non</h2>
<p>Cas standard : étiquette {{TAG}} (ISO 14443A, {{F_NFC}} MHz) de ø{{TAG_D}} mm à {{TAG_TURNS}} spires au fond de la base ({{TAG_L}} µH, résonance propre à {{TAG_F}} MHz avec les {{TAG_C}} pF de la puce), boucle carrée de {{ANT_SIDE}} mm à {{ANT_TURNS}} spires gravée sous la case ({{ANT_L}} µH, X<sub>L</sub> = {{ANT_XL}} Ω, accord par {{ANT_C}} pF). À {{Z_NFC}} mm : k = {{K}}, et {{I_ANT}} mA dans la boucle font {{H}} A/m à l'étiquette, {{H_MARGIN}} fois le minimum ISO de {{H_MIN}} A/m ({{H_MARGIN_FAR}} fois à l'entrefer maximal). Le couplage se calcule avec la même inductance mutuelle que le LC.</p>
<div class="formulas">
<div class="formula"><p class="f">Q = X<sub>L</sub> / R<sub>série</sub></p><p class="d">Q = {{Q_TARGET}} visé pour la sous-porteuse à 848 kHz, soit {{ANT_R}} Ω de résistance série en tout</p></div>
<div class="formula"><p class="f">C = 1 / (ω² L)</p><p class="d">{{ANT_C}} pF d'accord ; les voies fermées du mux en accrochent {{MUX_CPAR}} de plus</p></div>
<div class="formula"><p class="f">H = N I R² / (2 (R²+z²)<sup>3/2</sup>)</p><p class="d">champ sur l'axe de la boucle, à comparer au minimum ISO 14443</p></div>
</div>
<figure>
<div class="fig-scroll">{{FIG_NFC}}</div>
<figcaption><b>Le {{MUX}} dans la boucle.</b> {{MUX_RON}} Ω de résistance passante pour {{ANT_R}} Ω admis : Q = {{MUX_Q}}. {{MUX_CPAR}} pF parasites sur {{ANT_C}} pF d'accord : {{MUX_DETUNE}} % de fréquence, pour une bande passante de {{BW_PCT}} %. L'ADR 0001 l'avait écrit à la main ; le modèle le chiffre.</figcaption>
</figure>
<div class="tbl">
<table>
<thead><tr><th>topologie</th><th>composants</th><th>remarque</th></tr></thead>
<tbody>
<tr><td>Un lecteur par case</td><td>64 x (MFRC522, quartz 27,12 MHz, adaptation), SPI partagé, 64 chip select par registres à décalage</td><td>un émetteur à la fois ; pas de RF qui traverse la carte ; de l'ordre de 190 EUR, estimation</td></tr>
<tr><td>Un lecteur, arbre de commutation en 50 Ω</td><td>9 SP8T, 64 réseaux d'adaptation, un PN5180</td><td>64 lignes RF sur la carte, 64 accords à mettre au point</td></tr>
<tr><td>Lecteur sur le chariot</td><td>un lecteur, aucune antenne fixe</td><td>phase 2 seulement, lecture à la demande</td></tr>
<tr><td>Pas de RFID</td><td>rien</td><td>identité par la logique de jeu depuis la position initiale, promotion demandée au joueur</td></tr>
</tbody>
</table>
</div>
<p>Lecteurs candidats dans le yaml : {{READERS}}. Cohabitation avec le LC si les deux existaient : lecture NFC hors fenêtre de mesure, comme les trames LED ; l'étiquette sans ferrite, résonante à {{TAG_F}} MHz, charge peu le ringdown et son décalage est absorbé par la calibration par pièce, à vérifier par une M1 avec et sans étiquette.</p>
</section>

<section>
<p class="eyebrow">Autres pas</p>
<h2>Les cases de 55 ou 60 mm du brief</h2>
<div class="tbl">
<table>
<thead><tr><th>pas (mm)</th><th class="n">B pion nominal (mT)</th><th class="n">B roi soulevé (mT)</th><th class="n">marge au soulèvement</th><th class="n">diaphonie de {{NB_N}} voisins (dB)</th><th class="n">groupes, aimants codés</th><th class="n">k NFC</th><th class="n">marge ISO</th></tr></thead>
<tbody>
{{PITCH_ROWS}}
</tbody>
</table>
</div>
<p>L'aimant suit le diamètre de la base, donc le pas. La diaphonie s'améliore avec le pas, la marge au soulèvement se resserre un peu (un roi plus gros se voit de plus loin), tout reste dans les critères : le pas reste une question d'ergonomie et de couloir de déplacement, pas de capteur.</p>
</section>
</div>

<!-- ======================= IMPLÉMENTATION ======================= -->
<div class="mode" id="implementation">
<section>
<p class="eyebrow">Dans le dépôt</p>
<h2>Ce qui existe</h2>
<div class="tbl">
<table>
<thead><tr><th>livrable</th><th>où</th><th>ce qu'il fait</th></tr></thead>
<tbody>
<tr><td>Source des nombres</td><td><code>config/board.yaml</code>, section <code>hall_rfid</code> ; modèles typés dans <code>chessboard_calc/config.py</code></td><td>capteurs candidats, géométrie, seuils, mux, groupes d'alimentation, ESP32-S3, antenne et étiquette NFC ; trois valeurs de fiche marquées « to verify »</td></tr>
<tr><td>Modèle Hall</td><td><code>chessboard_calc/hall.py</code></td><td><code>disc_bz_mT</code> (champ exact hors axe), <code>hall_budget</code> (champs, seuils, diaphonie, marges ADC), <code>amplitude_classes</code>, <code>hall_power</code>, <code>hall_scan</code>, <code>check</code></td></tr>
<tr><td>Modèle NFC</td><td><code>chessboard_calc/nfc.py</code></td><td><code>antenna</code>, <code>tag</code>, <code>link</code>, <code>switch_verdict</code>, <code>analog_mux_verdict</code>, <code>check</code></td></tr>
<tr><td>Rapport</td><td><code>python -m chessboard_calc report</code></td><td>section « Hall + RFID alternative » de chaque pas</td></tr>
<tr><td>Tests</td><td><code>tests/test_hall.py</code>, <code>tests/test_nfc.py</code>, <code>tests/test_hallscan_config.py</code></td><td>forme fermée et dipôle, marges, {{UNI_GROUPS}} groupe avec aimants uniformes et {{CODED_GROUPS}} avec aimants codés, autonomie, cadence, verdict du mux, gardes qui tirent, en-tête généré</td></tr>
<tr><td>Firmware</td><td><code>firmware/esp32/hallscan/</code></td><td>logique C99 testée sur PC et en CI, en-tête généré du yaml, projet ESP-IDF pour l'{{ESP}}</td></tr>
<tr><td>Cette page et la note</td><td><code>docs/pages/hall-rfid.html</code>, <code>docs/notes/24-hall-et-rfid.md</code></td><td>la page est générée par <code>python -m docfig pages</code> des mêmes fonctions ; la note porte le verdict et les décisions à prendre</td></tr>
</tbody>
</table>
</div>
<p>Ce qui n'existe pas encore : la carte KiCad de la nappe Hall (elle attend une décision, <code>boardgen</code> sait la produire), la compilation ESP-IDF (pas de chaîne en CI, comme pour le pont et l'horloge), et la relecture des trois valeurs de fiche.</p>
</section>

<section>
<p class="eyebrow">Le scanner</p>
<h2>Firmware : {{GRID2}} cases en {{BOARD_MS}} ms</h2>
<figure>
<div class="fig-scroll">{{FIG_SCAN_I}}</div>
<figcaption><b>Architecture du prototype autonome du brief.</b> Quatre {{MUX}} ({{MUX_CH}} vers 1), un par quadrant, adresses communes ; quatre entrées ADC1 ; {{N_FETS}} P-FET de rangée ; la ligne <code>B</code> d'occupation de la note 12 sur la console.</figcaption>
</figure>
<pre><code>firmware/esp32/hallscan/
  main/hallscan.h, hallscan.c     logique : lignes de base, seuil et hystérésis, anti-rebond, ligne B
  main/hallscan_config.h          GÉNÉRÉ du yaml : seuils en comptes ADC, broches, cadence, cases par canal
  main/main.c                     ESP-IDF : ADC en lecture unitaire, adresses, rangées, console
  scripts/gen_config.py           le générateur de l'en-tête (chessboard_calc.hall)
  test/test_hallscan.c            test hôte, lancé par la CI</code></pre>
<p>Les seuils de l'en-tête sont ceux du rapport, convertis en comptes ADC par la sensibilité du {{SENSOR}} et le pas de {{LSB_MV}} mV : repos <code>HALL_BASELINE_COUNTS {{BASELINE_COUNTS}}</code>, présence <code>HALL_ON_COUNTS {{ON_COUNTS}}</code>, relâchement <code>HALL_OFF_COUNTS {{OFF_COUNTS}}</code>, anti-rebond sur {{DEBOUNCE}} scans. Un test du dépôt vérifie que l'en-tête commité est exactement ce que le générateur écrit.</p>
<ol class="steps">
<li>Rangée <code>g</code> alimentée (<code>ROW_EN&lt;g&gt;</code> bas), attente de {{POWER_ON_US}} µs.</li>
<li>Pour chaque canal de la rangée : adresse sur <code>MUX_S0..S3</code>, {{SETTLE_US}} µs, puis sur chacun des quatre multiplexeurs la moyenne de {{SAMPLES}} lectures.</li>
<li><code>hallscan_update</code> : écart à la ligne de base, seuil ou relâchement, anti-rebond ; une ligne <code>B,</code> suivie de 64 caractères (<code>.</code> vide, <code>?</code> occupée, <code>w</code> et <code>b</code> si la polarité code le camp) part dès qu'une case change d'état publié.</li>
<li>Console : <code>z</code> prend l'échiquier vide comme lignes de base, <code>r</code> sort les comptes bruts en CSV, <code>b</code> renvoie la ligne courante.</li>
</ol>
<pre><code># test de la logique sur PC (ce que fait la CI)
cc -Wall -Wextra -Werror -Imain test/test_hallscan.c main/hallscan.c -o /tmp/test_hallscan &amp;&amp; /tmp/test_hallscan

# regénérer l'en-tête après toute édition de hall_rfid dans le yaml
python3 scripts/gen_config.py ../../../config/board.yaml main/hallscan_config.h

# cible (ESP-IDF 5.x)
. ~/esp/esp-idf/export.sh &amp;&amp; idf.py set-target esp32s3 &amp;&amp; idf.py build flash monitor</code></pre>
</section>

<section>
<p class="eyebrow">Câblage</p>
<h2>Broches de l'{{ESP}}</h2>
<div class="tbl">
<table>
<thead><tr><th>signal</th><th class="n">broche</th><th>rôle</th></tr></thead>
<tbody>
{{PIN_ROWS}}
</tbody>
</table>
</div>
<p>Les entrées ADC1 du S3 sont les GPIO 1 à 10 ; les numéros sont ceux du yaml et restent à confirmer contre le brochage du module avant tout câblage. Les capteurs sont en 3,3 V, les multiplexeurs aussi ; la sortie du {{SENSOR}} ({{VQ}} V au repos, ±{{OUT_PAWN_MV}} mV pour un pion) entre directement dans l'ADC à 12 dB d'atténuation.</p>
<h2>La nappe Hall d'un quadrant, à dessiner</h2>
<p>Deux couches, 200 x 200 mm, posée sur le quadrant dans la lame d'air, ou seule pour l'étape intermédiaire : 16 capteurs {{SENSOR}} en SOT-23 au centre des cases, un {{MUX}}, {{GROUPS}} P-FET de rangée avec leur résistance de grille, un condensateur de découplage par capteur, un connecteur. Le bus de la nappe du quadrant LC suffit à l'adresser depuis le cerveau (<code>MUX_A0..A2</code> plus un enable comme quatrième bit, <code>AMP_OUT</code> pour la sortie) ; pour l'ESP32-S3 du brief, un connecteur à huit fils (3,3 V, masse, sortie, quatre adresses, une ou quatre lignes de rangée).</p>
</section>

<section>
<p class="eyebrow">Pour continuer</p>
<h2>Les décisions, dans l'ordre</h2>
<ol class="steps">
<li><b>Couche Hall de présence : oui ou non, et sur quelle carte.</b> La nappe séparée pour l'étape intermédiaire ; six couches ou spirale à trois couches pour l'intégrer au quadrant ensuite.</li>
<li><b>Capteur et alimentation.</b> {{SENSOR}} par groupes de rangées ; {{SENSOR2}} si le prix ou le stock l'imposent, par groupes obligatoirement.</li>
<li><b>Codage par polarité ou par épaisseur : non</b> tant que l'aimant permanent du chariot reste candidat ; à rouvrir si l'électroaimant est choisi.</li>
<li><b>RFID sur le plateau : non en phase 1.</b> Repli à un lecteur par case si la mesure M2 échoue ; lecteur sur le chariot à étudier en phase 2.</li>
<li><b>Mesure M12 à ajouter au protocole.</b> B(z) et B(ρ) d'un aimant de pièce relevés au capteur de la nappe, comparés à <code>hall.disc_bz_mT</code> ; puis la courbe de soulèvement, qui fixe les seuils réels à la place des fractions du yaml.</li>
</ol>
<p>Quand une décision tombe, elle s'écrit dans le yaml (section <code>hall_rfid</code>), le rapport, les tests, l'en-tête du firmware et cette page suivent sans recopie.</p>
</section>
</div>

<p class="foot">Chiffres calculés par <code>chessboard_calc</code> depuis <code>config/board.yaml</code> du dépôt electronic-chess, octobre 2026 ; schémas de <code>tools/docfig</code>, note 24 du dépôt.</p>
</div>
"""


HALL_SCRIPT = r"""<script>
(function(){
  var modes = ['simple', 'technique', 'implementation'];
  var btns = document.querySelectorAll('.mode-btn');
  function show(m, push){
    if (modes.indexOf(m) < 0) m = 'simple';
    modes.forEach(function(k){ var el = document.getElementById(k); if (el) el.hidden = (k !== m); });
    Array.prototype.forEach.call(btns, function(b){
      var on = b.getAttribute('data-mode') === m;
      b.classList.toggle('is-on', on); b.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
    try { localStorage.setItem('hall-rfid-mode', m); } catch (e) {}
    if (push) { try { history.replaceState(null, '', '#' + m); } catch (e) {} }
  }
  var start = (location.hash || '').replace('#', '');
  if (modes.indexOf(start) < 0) { try { start = localStorage.getItem('hall-rfid-mode') || 'simple'; } catch (e) { start = 'simple'; } }
  show(start, false);
  Array.prototype.forEach.call(btns, function(b){
    b.addEventListener('click', function(){ show(b.getAttribute('data-mode'), true); });
  });
  window.addEventListener('hashchange', function(){ show((location.hash || '').replace('#', ''), false); });

  var Z = {{Z_JSON}}, BP = {{BP_JSON}}, BK = {{BK_JSON}};
  var X0 = 70, PX = (860 - 70) / 28, YB = 300, PY = (300 - 50) / 40;
  Array.prototype.forEach.call(document.querySelectorAll('svg[data-curve]'), function(svg){
    var xh = svg.querySelector('.hxh');
    if (!xh) return;
    var line = xh.querySelector('line'), dots = xh.querySelectorAll('circle');
    var box = xh.querySelector('rect'), txts = xh.querySelectorAll('text');
    svg.addEventListener('pointermove', function(ev){
      var r = svg.getBoundingClientRect();
      var xv = (ev.clientX - r.left) * 900 / r.width;
      var z = (xv - X0) / PX + Z[0];
      if (z < Z[0] || z > Z[Z.length - 1]) { xh.hidden = true; return; }
      var i = Math.round((z - Z[0]) / 0.25); if (i < 0) i = 0; if (i >= Z.length) i = Z.length - 1;
      var x = X0 + (Z[i] - Z[0]) * PX;
      line.setAttribute('x1', x); line.setAttribute('x2', x);
      dots[0].setAttribute('cx', x); dots[0].setAttribute('cy', YB - Math.min(BP[i], 40) * PY);
      dots[1].setAttribute('cx', x); dots[1].setAttribute('cy', YB - Math.min(BK[i], 40) * PY);
      var bx = x + 12; if (bx + 210 > 860) bx = x - 222;
      var y = YB - Math.min(BK[i], 40) * PY;
      if (y < 60) y = 60;
      box.setAttribute('x', bx); box.setAttribute('y', y - 48);
      txts[0].setAttribute('x', bx + 8); txts[0].setAttribute('y', y - 32);
      txts[0].textContent = Z[i].toFixed(2).replace('.', ',') + ' mm : roi ' + BK[i].toFixed(1).replace('.', ',') + ' mT';
      txts[1].setAttribute('x', bx + 8); txts[1].setAttribute('y', y - 16);
      txts[1].textContent = 'pion ' + BP[i].toFixed(1).replace('.', ',') + ' mT';
      xh.hidden = false;
    });
    svg.addEventListener('pointerleave', function(){ xh.hidden = true; });
  });
})();
</script>
"""
