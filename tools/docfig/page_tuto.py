"""The page that walks through building the bench
(`docs/pages/tuto-banc.html`), the browser twin of note 20: the bills of
materials come from the CSV files the generators write, the figures from
docfig.tuto.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

from chessboard_calc.config import DEFAULT_CONFIG_PATH, BoardConfig, PieceType
from chessboard_calc.coupling import ringdown_signal, ringdown_tau_us
from chessboard_calc.resonance import check_separation, frequency_plan

from .common import fr_num
from .page import check, document, esc
from .q import ADC_FS_FIRMWARE_HZ, listen_window_us
from .tuto import (
    bench_pucks,
    fig_bench_inventory,
    fig_bench_tests,
    fig_puck_making,
    fig_shield_assembly,
)


def pretty_footprint(fp: str) -> str:
    fp = re.sub(r"_\d{4}Metric$", "", fp)
    fp = fp.replace("C_", "").replace("R_", "").replace("Fuse_", "fusible ")
    fp = fp.replace("_", " ")
    return fp


def bom_rows(path: Path) -> str:
    out = []
    with open(path, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            refs = row["References"].replace(" ", ", ")
            code = ", ".join(x for x in (row["MPN"], row["LCSC"]) if x) or "par valeur"
            if row["Footprint"] == "COIL_TIE":
                code = "gravée dans le circuit"
            if row["Footprint"].startswith("TestPoint"):
                code = "pastille nue"
            out.append(
                f"<tr><td>{esc(refs)}</td><td class='n'>{row['Qty']}</td>"
                f"<td>{esc(row['Value'])}</td><td>{esc(pretty_footprint(row['Footprint']))}</td>"
                f"<td>{esc(code)}</td></tr>"
            )
    return "".join(out)


def tuto_page(cfg: BoardConfig, repo: Path | None = None) -> str:
    repo = repo or DEFAULT_CONFIG_PATH.parents[1]
    plan = frequency_plan(cfg)
    pucks = bench_pucks(cfg)
    reduced = cfg.plateau.quadrant.reduced
    p = cfg.pitch.plateau_mm
    board_w = reduced.squares * p + cfg.plateau.quadrant.front_end_strip_mm
    board_h = reduced.squares * p + reduced.strip_overhang_mm
    shield_w, shield_h = cfg.bench.shield.board_mm
    puck_rows = "".join(
        f"<tr><td>{r['glyph']} {r['name']}</td><td class='n'>{fr_num(r['cap_nF'])} nF</td>"
        f"<td class='n'>{r['f0_khz']:.0f} kHz</td><td class='n'>{fr_num(r['d_out'])} / "
        f"{fr_num(r['d_in'])} mm</td><td class='n'>{r['turns']}</td>"
        f"<td class='n'>{fr_num(r['wire'], 3)} mm</td><td class='n'>{fr_num(r['magnet_d'])} mm</td></tr>"
        for r in pucks
    )
    notes = ", ".join(f"{r['f0_khz']:.0f}" for r in pucks)
    pawn = plan.line(PieceType.PAWN, cfg.mockup.test_pieces[0].color)
    band = sorted(line.f0_hz for line in plan.lines)
    rings = [ringdown_signal(cfg, line.piece, line.color, p) for line in plan.lines]
    emf = sorted(r.emf_after_blanking_v for r in rings)
    v = {
        "FIG_INV": fig_bench_inventory(cfg),
        "FIG_SHIELD": fig_shield_assembly(cfg),
        "FIG_PUCK": fig_puck_making(cfg),
        "FIG_TESTS": fig_bench_tests(cfg),
        "BOM_BENCH": bom_rows(repo / "hardware" / "bench" / "bom.csv"),
        "BOM_QUAD": bom_rows(repo / "hardware" / "quadrant-2x2" / "bom.csv"),
        "PUCK_ROWS": puck_rows,
        "NOTES": notes,
        "F_PAWN": f"{pawn.f0_hz / 1e3:.0f}",
        "WINDOW": fr_num(listen_window_us(cfg), 0),
        "Q_MIN": f"{cfg.resonator.q_min_with_magnet:.0f}",
        "L_UH": fr_num(cfg.resonator.L_target_uH, 0),
        "L_TOL": fr_num(cfg.resonator.L_tol_pct, 0),
        "GAP": fr_num(cfg.gap.nominal_total_mm),
        "PCB": fr_num(cfg.gap.pcb_mm),
        "AIR": fr_num(cfg.gap.air_mm),
        "WOOD": fr_num(cfg.gap.surface_mm),
        "FELT": fr_num(cfg.gap.felt_mm),
        "SHIELD": f"{fr_num(shield_w, 0)} x {fr_num(shield_h, 0)}",
        "QUAD": f"{fr_num(board_w, 0)} x {fr_num(board_h, 0)}",
        "F_LOW": f"{band[0] / 1e3:.0f}",
        "F_HIGH": f"{band[-1] / 1e3:.0f}",
        "BW_MIN": fr_num(8 * band[-1] / 1e6),
        "SPS_MIN": fr_num(10 * band[-1] / 1e6),
        "EMF_LO": fr_num(emf[0], 2),
        "EMF_HI": fr_num(emf[-1], 2),
        "VREF": fr_num(cfg.mockup.analog.vref_v, 2),
        "TAU_LO": f"{ringdown_tau_us(band[-1], cfg.resonator.q_min_with_magnet):.0f}",
        "TAU_HI": f"{ringdown_tau_us(band[0], cfg.resonator.q_nominal):.0f}",
        "GAP_KHZ": fr_num(check_separation(cfg).min_worst_case_gap_hz / 1e3, 2),
        "FS": fr_num(ADC_FS_FIRMWARE_HZ / 1e6, 2),
        "FFT": f"{cfg.measurement.fft_points}",
        "AVG": f"{cfg.measurement.coherent_avg}",
        "PULSE": fr_num(cfg.measurement.drive.pulse_us),
        "BLANK": fr_num(cfg.measurement.blanking_us),
        "MAGNET_H": fr_num(cfg.piece_magnet.thickness_mm, 0),
        "TURNS": ", ".join(str(r["turns"]) for r in pucks),
        "WIRES": " et ".join(fr_num(w, 3) for w in sorted({round(r["wire"], 3) for r in pucks})),
    }
    page = document("Monter le banc", BODY)
    for k, val in v.items():
        page = page.replace("{{" + k + "}}", val)
    check(page)
    return page


BODY = r"""<div class="wrap">
<p class="eyebrow">Échiquier à résonateurs LC</p>
<h1>Monter le banc</h1>
<p class="lede">Suite des pages sur le facteur Q et sur le cerveau, pour le même lecteur : quoi faire, quoi commander, quels composants, comment les assembler et comment tester, pour passer du dépôt à un banc qui mesure.</p>

<div class="keep">
<p><strong>Le banc, c'est quatre objets.</strong> Une carte de développement Nucleo du commerce, une petite carte de banc qui s'emboîte dessus, un quadrant de quatre cases relié par une nappe, et quatre pucks de test. Plus du bois, du feutre et une alimentation 12 V.</p>
<p><strong>On ne commande rien tant que la première section n'est pas verte.</strong> Au 18 septembre 2026 la carte de banc est prête ; le quadrant 2 x 2 ne l'est pas encore ; les composants passifs n'ont pas de code fournisseur.</p>
<p><strong>On monte le banc par échelons</strong>, un test par échelon, jamais deux nouveautés à la fois. La mesure qui décide de la suite du projet est M2 : le Q avec l'aimant ferrite doit rester au-dessus de {{Q_MIN}}.</p>
</div>

<section>
<p class="eyebrow">Avant de commander</p>
<h2>Ce qui est prêt, ce qui ne l'est pas</h2>
<div class="tbl">
<table>
<thead><tr><th>élément</th><th>état au 18 septembre 2026</th><th>ce qui débloque</th></tr></thead>
<tbody>
<tr><td>Carte de banc</td><td>générée, 29 nets fermés, DRC KiCad : zéro erreur, zéro élément non connecté</td><td>rien : exporter les fichiers de fabrication</td></tr>
<tr><td>Quadrant 2 x 2</td><td>généré ; DRC KiCad : 117 éléments non connectés, deux nets connus du README et des trous de connexité de la même famille que ceux corrigés sur la carte de banc</td><td>fermer les nets dans le générateur du quadrant, DRC à zéro, puis exporter</td></tr>
<tr><td>Codes fournisseur (LCSC)</td><td>présents pour les circuits intégrés, transistors, diodes, connecteurs, LED et inductance ; absents pour résistances, condensateurs, fusibles, barrettes, cavalier et points de test</td><td>une session avec accès au réseau ; en attendant, les passifs se commandent par valeur et boîtier</td></tr>
<tr><td>Devis de fabrication</td><td>à faire</td><td>même session</td></tr>
<tr><td>Deux points de fiche technique</td><td>l'aiguilleur ADG1607 alimenté en 5 V ; les vias de 0,45 mm chez le fabricant</td><td>lecture des fiches, devis</td></tr>
</tbody>
</table>
</div>
<p>Le compte d'éléments non connectés doit être à zéro sur les deux cartes avant toute commande (<code>tools/drc.py</code> dans le dépôt). Le reste de cette page est écrit pour le moment où ce sera le cas ; tout ce qui concerne la carte de banc, la Nucleo, les pucks et le bois peut se préparer dès maintenant.</p>
</section>

<section>
<p class="eyebrow">Ce qu'on construit</p>
<h2>Deux côtés et une nappe</h2>
<figure>
<div class="fig-scroll">{{FIG_INV}}</div>
<figcaption><b>Ce que réunit le banc.</b> À gauche le côté mesure, la Nucleo sous la carte de banc reliée au 12 V et au PC ; à droite le côté échiquier, le quadrant sous le contreplaqué et le feutre avec les quatre pucks ; la nappe entre les deux.</figcaption>
</figure>
<p>Le côté mesure est une Nucleo-G474RE, la carte de développement de ST qui porte le même microcontrôleur que le cerveau du plateau, sa sonde de programmation et son port série. La carte de banc ({{SHIELD}} mm) s'emboîte dessus comme un shield Arduino et lui apporte ce que le cerveau aurait donné au quadrant : un 12 V protégé pour frapper les bobines, un 5 V pour les LED, un 5 V analogique propre pour le frontal, un tampon pour la chaîne LED, et le connecteur de nappe.</p>
<p>Le côté échiquier est le quadrant réduit 2 x 2 ({{QUAD}} mm, quatre couches) : quatre spirales gravées dans le circuit imprimé, huit LED de camp et le frontal analogique complet sur sa bande, le même circuit que les quadrants du plateau. Une nappe FPC de seize conducteurs relie les deux côtés. Par dessus le quadrant, le contreplaqué et le feutre reconstituent l'entrefer réel de {{GAP}} mm ; les quatre pucks de test jouent les pièces.</p>
</section>

<section>
<p class="eyebrow">Quoi commander</p>
<h2>Les deux circuits imprimés</h2>
<div class="tbl">
<table>
<thead><tr><th>carte</th><th>format</th><th>couches</th><th>particularités</th></tr></thead>
<tbody>
<tr><td>Carte de banc</td><td>{{SHIELD}} mm, 1,6 mm</td><td class="n">2</td><td>rien de spécial ; finition HASL sans plomb ou ENIG</td></tr>
<tr><td>Quadrant 2 x 2</td><td>{{QUAD}} mm, 1,6 mm</td><td class="n">4</td><td>vias de 0,45 mm à perçage 0,2 mm sous les boîtiers fins : cocher l'option de perçage minimal 0,2 mm, à confirmer sur le devis ; un pochoir rend la pose du frontal beaucoup plus sûre</td></tr>
</tbody>
</table>
</div>
<p>Cinq exemplaires sont le minimum chez JLCPCB et suffisent largement. Les projets KiCad sont dans <code>hardware/bench/</code> et <code>hardware/quadrant-2x2/</code> ; le dépôt ne versionne pas leurs gerbers. Pour les produire : ouvrir le projet dans KiCad 7 ou plus récent, lancer le contrôle des règles, puis Fichier, Tracer (toutes les couches de cuivre, les masques, la sérigraphie et le contour, format Gerber) et Générer les fichiers de perçage. Compresser le dossier et le déposer sur le site du fabricant. Les fichiers <code>jlc-bom.csv</code> et <code>jlc-cpl.csv</code> de chaque carte servent si l'on choisit l'assemblage en usine des composants qui ont un code ; les autres se soudent à la main.</p>

<h2>Les composants de la carte de banc</h2>
<p>La nomenclature <code>hardware/bench/bom.csv</code>, telle que le générateur l'écrit : 43 composants. Les lignes sans code se commandent par valeur et boîtier ; prendre deux exemplaires de chaque petit CMS, un 0603 qui saute de la pince ne se retrouve pas.</p>
<div class="tbl">
<table>
<thead><tr><th>repères</th><th class="n">qté</th><th>valeur</th><th>boîtier</th><th>référence, code LCSC</th></tr></thead>
<tbody>{{BOM_BENCH}}</tbody>
</table>
</div>

<h2>Les composants du quadrant 2 x 2</h2>
<p>La nomenclature <code>hardware/quadrant-2x2/bom.csv</code>, 44 lignes ; la fonction de chaque bloc est dans la note 17 du dépôt. Prendre aussi des 1 kΩ et 2 kΩ pour R14, la résistance de gain de l'amplificateur d'instrumentation, au cas où la chaîne écrête.</p>
<div class="tbl">
<table>
<thead><tr><th>repères</th><th class="n">qté</th><th>valeur</th><th>boîtier</th><th>référence, code LCSC</th></tr></thead>
<tbody>{{BOM_QUAD}}</tbody>
</table>
</div>

<h2>La Nucleo, les câbles, l'alimentation</h2>
<ul>
<li><b>NUCLEO-G474RE</b> de ST, avec sa sonde ST-Link intégrée ; un câble USB micro-B vers le PC : il programme la carte et porte la console série.</li>
<li><b>Nappe FFC/FPC</b> de 16 conducteurs au pas de 0,5 mm, 100 à 150 mm, contacts du même côté aux deux bouts (dite « type A ») : les deux connecteurs sont identiques, montés côté composants, contacts vers le bas ; posée à plat entre les deux cartes, la nappe présente ses contacts vers le bas aux deux extrémités. En prendre deux.</li>
<li><b>Alimentation 12 V</b> de laboratoire, limitée en courant (100 mA suffisent au banc à vide, 500 mA avec les LED allumées), linéaire ou batterie : jamais un chargeur à découpage près des bobines. Un cordon à fiche 5,5 x 2,1 mm, positif au centre.</li>
</ul>

<h2>De quoi faire les quatre pucks</h2>
<figure>
<div class="fig-scroll">{{FIG_PUCK}}</div>
<figcaption><b>Fabriquer un puck de test.</b> Bobiner sur le gabarit imprimé, souder le condensateur qui fixe la note, glisser bobine et aimant ferrite dans le puck. Le tableau donne, pour les quatre pucks du banc, le condensateur, la note attendue, les diamètres de la bobine, le nombre de tours et le fil, calculés depuis le yaml du dépôt.</figcaption>
</figure>
<div class="tbl">
<table>
<thead><tr><th>puck</th><th class="n">condensateur</th><th class="n">note</th><th class="n">bobine ext. / int.</th><th class="n">tours</th><th class="n">fil</th><th class="n">aimant</th></tr></thead>
<tbody>{{PUCK_ROWS}}</tbody>
</table>
</div>
<ul>
<li><b>Fil émaillé</b> de {{WIRES}} mm de diamètre de cuivre ; compter 4 m par bobine, une bobine de 10 m de chaque diamètre laisse de quoi recommencer.</li>
<li><b>Condensateurs C0G 1 %</b>, boîtier 0805, 50 V, un de chaque valeur plus rechange. C0G est le diélectrique qui ne bouge ni avec la température ni avec le temps : c'est lui qui tient la note.</li>
<li><b>Aimants ferrite</b> (SrFe), épaisseur {{MAGNET_H}} mm, au diamètre de la table ou au diamètre du commerce le plus proche ; la poche du puck se règle dans <code>mechanical/</code>. Pas de néodyme dans les pucks : la page sur le facteur Q explique pourquoi, et la mesure M3 le vérifie.</li>
<li><b>Impression 3D</b> : les quatre pucks, les trois gabarits de bobinage et leurs rondelles, produits par <code>python mechanical/build_all.py</code>. Vis M3 x 30 avec deux écrous pour l'axe du gabarit, vernis ou colle cyanoacrylate.</li>
</ul>

<h2>Le bois, la quincaillerie, l'outillage</h2>
<ul>
<li>Contreplaqué sec de {{WOOD}} mm et feutre autocollant de {{FELT}} mm, environ 130 x 130 mm pour couvrir les quatre cases. L'entrefer de {{GAP}} mm se décompose en {{PCB}} mm de circuit, {{AIR}} mm d'air, {{WOOD}} mm de bois et {{FELT}} mm de feutre.</li>
<li>Entretoises nylon M3 : {{AIR}} mm entre la carte et le bois (l'air des LED), 10 mm sous la carte ; vis et écrous M3 ; le gabarit de perçage <code>surface-template</code> donne les trous de fixation et les deux points lumineux de 2,5 mm par case.</li>
</ul>
<div class="tbl">
<table>
<thead><tr><th>outil</th><th>pour quoi</th><th>indispensable</th></tr></thead>
<tbody>
<tr><td>fer à souder à pointe fine, flux, tresse à dessouder, loupe</td><td>tout le CMS courant, le connecteur FPC</td><td>oui</td></tr>
<tr><td>station à air chaud ou plaque chauffante, pâte à braser, pochoir</td><td>le buck QFN de la carte de banc, l'aiguilleur LFCSP du quadrant (plage thermique sous le boîtier, impossible au fer)</td><td>oui pour ces deux boîtiers</td></tr>
<tr><td>multimètre</td><td>continuité, tensions des points de test</td><td>oui</td></tr>
<tr><td>alimentation 12 V limitée en courant</td><td>le rail d'impulsion et le 5 V analogique</td><td>oui</td></tr>
<tr><td>oscilloscope, au moins {{BW_MIN}} MHz de bande et {{SPS_MIN}} Méch/s</td><td>voir le signal avant de croire le firmware</td><td>oui pour les mesures, pas pour les premiers échelons</td></tr>
<tr><td>LCR-mètre</td><td>L et Q des bobines nues</td><td>conseillé</td></tr>
<tr><td>perceuse ou petit tour</td><td>bobiner</td><td>oui</td></tr>
<tr><td>imprimante 3D, ou un service d'impression</td><td>pucks et gabarits</td><td>oui</td></tr>
<tr><td>analyseur logique</td><td>le bus de commande, en cas de doute</td><td>non</td></tr>
</tbody>
</table>
</div>
<p>Ce qu'on demande à l'oscilloscope vient de la bande de mesure, {{F_LOW}} à {{F_HIGH}} kHz. La note la plus haute fixe les deux planchers : huit fois cette note en bande passante pour que la sonnerie ne soit pas arrondie, soit {{BW_MIN}} MHz, et dix échantillons par période, soit {{SPS_MIN}} Méch/s. Il faut aussi tenir à l'écran la fenêtre d'écoute, {{WINDOW}} µs sur le banc ({{FFT}} points à {{FS}} Méch/s). Les amplitudes sont généreuses : la force électromotrice sur la spirale va de {{EMF_LO}} à {{EMF_HI}} V crête selon la pièce, une fois les {{BLANK}} µs de silence passés, et AMP_OUT se lit autour de {{VREF}} V. Un petit appareil de poche à une voie, 10 MHz de bande et 48 Méch/s, couvre donc tout ce que les échelons demandent, avec 78 échantillons par période sur la note la plus haute.</p>
<p>Deux limites à connaître avant de s'y fier. Une seule voie interdit de voir l'impulsion et la sonnerie ensemble : on déclenche alors sur la sonnerie elle même (mode normal ou coup unique, front montant, seuil au dessus du bruit) et on vérifie l'impulsion dans un second temps, sonde sur TP3. Et une bande de 10 MHz ne dit rien de l'ondulation du buck à 2,2 MHz : cette comparaison (mesure M8) se lit de toute façon dans les relevés bruts du firmware, pas à l'écran. De même, le générateur intégré de ces appareils plafonne vers 50 kHz, quatre fois sous notre bande : il n'excite rien ici, l'excitation c'est l'impulsion de la carte.</p>
<p>L'oscilloscope ne mesure pas les notes, il montre qu'elles existent. L'identification demande environ 1 kHz de résolution devant un écart pire cas de {{GAP_KHZ}} kHz entre deux pièces voisines : c'est le firmware qui la fournit, {{FFT}} points à {{FS}} Méch/s, FFT et interpolation parabolique, {{AVG}} moyennes cohérentes. Lire une période au curseur sur un écran de 320 pixels donne quelques milliers de hertz d'erreur, bon pour diagnostiquer, insuffisant pour nommer une pièce. Le Q, lui, se lit très bien à l'écran : l'enveloppe décroît en {{TAU_LO}} à {{TAU_HI}} µs selon la note et le Q, soit une dizaine de périodes bien visibles avant l'extinction.</p>
</section>

<section>
<p class="eyebrow">Assembler</p>
<h2>Le quadrant 2 x 2</h2>
<p>Rien à bobiner : les spirales sont dans le circuit imprimé. Tout se joue sur la bande de frontal, 20 mm de large, et dans les coins des cases pour les LED.</p>
<ol>
<li>L'aiguilleur U3 (LFCSP, plage thermique) : pâte à braser au pochoir ou à la seringue, plaque chauffante ou air chaud, repère de la broche 1 sur la sérigraphie. Vérifier à la loupe qu'aucune broche n'est pontée.</li>
<li>Les décodeurs TSSOP U1 et U2, l'AD8421 et les deux OPA2810 en SOIC, l'inverseur : fer fin, une broche d'ancrage puis les autres, tresse en cas de pont.</li>
<li>Les transistors et les diodes : la bague de cathode des diodes en face du trait de la sérigraphie ; les BAV99W (SOT-323) sont les plus petits boîtiers de la carte.</li>
<li>Les résistances et condensateurs, par valeur, en cochant la nomenclature au fur et à mesure.</li>
<li>Les huit WS2812B en dernier, à température modérée (elles supportent mal la chaleur), avec leurs 100 nF ; respecter le coin biseauté du boîtier.</li>
<li>Le connecteur FPC : les pattes de 0,5 mm se soudent avec beaucoup de flux, en glissant la pointe le long de la rangée ; contrôler les ponts à la loupe. Le volet s'ouvre vers le haut, la nappe se glisse contacts vers le bas, le volet se referme.</li>
<li>Nettoyer le flux à l'alcool isopropylique : le frontal traite des microvolts, les résidus font des fuites.</li>
</ol>

<h2>La carte de banc</h2>
<figure>
<div class="fig-scroll">{{FIG_SHIELD}}</div>
<figcaption><b>La carte de banc en coupe, emboîtée sur la Nucleo, et l'ordre de soudure.</b> Les composants dessus ; les barrettes mâles soudées côté cuivre, corps sous la carte, broches vers le bas dans les embases femelles de la Nucleo.</figcaption>
</figure>
<p>L'ordre est celui de la figure : le buck QFN d'abord, à l'air chaud ou sur plaque, pendant que la carte est vide et à plat ; puis les autres CMS au fer ; le connecteur FPC ; les traversants (jack, cavalier JP1) ; et les quatre barrettes mâles en dernier, parce qu'une fois soudées la carte ne se pose plus à plat.</p>
<p>Les barrettes sont la seule chose à ne pas se tromper : le corps sous la carte, les broches vers le bas, la soudure sur le dessous (le côté cuivre). Pour qu'elles restent perpendiculaires et au bon pas, les emboîter d'abord dans les embases femelles de la Nucleo, poser la carte de banc dessus, et souder les broches par le dessus de la carte ; ensuite seulement retirer l'ensemble de la Nucleo. Les quatre embases de la Nucleo ne sont pas symétriques (8, 6, 8 et 10 broches) : la carte ne s'emboîte que dans un sens.</p>
<p>Le cavalier JP1 choisit d'où vient le 5 V analogique : broches 1 et 2, du LDO, la position de départ ; 2 et 3, du buck, pour la comparaison de la mesure M8.</p>

<h2>Les pucks</h2>
<p>Un puck est un résonateur : une bobine et un condensateur qui sonnent à une note, plus un aimant ferrite pour que, plus tard, le chariot du plateau puisse déplacer la pièce.</p>
<ol>
<li>Imprimer le gabarit du bon diamètre (un par classe de bobine) et ses rondelles.</li>
<li>Monter le noyau sur une vis M3 dans le mandrin d'une perceuse, rondelle serrée ; passer le bout du fil dans l'encoche en laissant 10 cm libres.</li>
<li>Bobiner à vitesse lente le nombre de tours de la table ({{TURNS}} selon la pièce), spires serrées et régulières, dans la fenêtre de 2 mm ; laisser 10 cm en sortie.</li>
<li>Imprégner de vernis ou d'une goutte de cyanoacrylate, laisser sécher, retirer la rondelle et sortir la bobine.</li>
<li>Dénuder les deux bouts (l'émail part au grattoir ou dans une grosse goutte d'étain bien chaude), souder le condensateur C0G aux deux fils, court, dans le prolongement de la bobine.</li>
<li>Si un LCR-mètre est là : mesurer L, attendue à {{L_UH}} µH à ± {{L_TOL}} %, et Q à 100 kHz ; noter les valeurs sur le puck, elles servent en M1 et M6.</li>
<li>Glisser la bobine dans les 2 mm du fond du puck, le condensateur dans sa fente, l'aimant dans sa poche par dessus ; un point de colle. Marquer le puck de sa classe.</li>
</ol>
<p>Quatre bobines à la main donnent quatre inductances légèrement différentes : c'est attendu, la note bouge de ± 2,5 % au plus, et la calibration du firmware mesure chaque pièce avant de la reconnaître.</p>

<h2>Le bois</h2>
<p>Scotcher le gabarit <code>surface-template</code> sur le contreplaqué, percer les trous de fixation et les points lumineux de 2,5 mm au droit des LED, coller le feutre, poser sur les entretoises de {{AIR}} mm au-dessus du quadrant. Ne rien mettre de métallique entre la carte et les pucks : une vis en acier au milieu d'une case change sa note.</p>
</section>

<section>
<p class="eyebrow">Tester</p>
<h2>L'échelle des tests</h2>
<figure>
<div class="fig-scroll">{{FIG_TESTS}}</div>
<figcaption><b>Du bas vers le haut, un échelon à la fois.</b> À droite, ce que la console écrit et les touches du firmware. Les tensions attendues se lisent sur les points de test de la carte de banc : TP6 VIN, TP3 5V, TP2 5VA, TP4 3V3, TP5 GND, TP7 ADC1, TP1 LED_END.</figcaption>
</figure>
<ol>
<li><b>Carte de banc seule, ohmmètre.</b> Entre chaque rail (VIN, 5V, 5VA, 3V3) et la masse : jamais zéro ohm. Une valeur qui monte lentement (les condensateurs qui se chargent) est normale.</li>
<li><b>12 V seul, sans Nucleo.</b> Alimentation limitée à 100 mA, jack branché : TP6 à 12 V, TP3 à 5,0 V (le buck), TP2 à 5,0 V (le LDO, cavalier en 1-2), consommation de quelques milliampères. Si le courant part en butée, couper : chercher un pont de soudure sur le buck ou une diode à l'envers.</li>
<li><b>Nucleo et console.</b> Dans <code>firmware/board</code>, <code>make NUCLEO=1</code> produit <code>build/nucleo/board-nucleo.bin</code> ; le copier sur le lecteur NUCLEO ou le flasher par <code>st-flash</code>. Ouvrir le port série de la sonde à 115200 bauds. Emboîter la carte de banc, brancher le 12 V : TP4 à 3,3 V (le 3,3 V vient de la Nucleo), et la console affiche la bannière <code># LC chessboard, nucleo bench</code> avec la cadence d'échantillonnage et l'en-tête du CSV. La touche <code>h</code> liste les commandes.</li>
<li><b>Quadrant et nappe.</b> Nappe engagée aux deux bouts, 12 V rebranché : <code>s</code> écrit quatre lignes CSV (cases 0, 1, 8, 9, soit a1, b1, a2, b2) avec une note quelconque et une amplitude faible : c'est le bruit, il n'y a pas de pièce. Les LED attendent l'échelon 6 : <code>l</code> n'allume que les cases reconnues et répond « no calibration stored » tant que <code>c</code> n'a pas tourné.</li>
<li><b>Un puck, sa note.</b> Le pion noir sur une case : <code>s</code> doit donner sur cette case <code>fa_hz</code> proche de {{F_PAWN}} 000 (± 3 %, la tolérance du fil et du condensateur), <code>fb_hz</code> à quelques centaines de hertz de <code>fa_hz</code>, une amplitude nettement au-dessus des cases vides. La touche <code>r</code> vide les 512 points bruts de la case a1 : tracés, ils doivent montrer une sinusoïde qui décroît doucement sur toute la fenêtre de {{WINDOW}} µs. Si elle est plate en haut, la chaîne écrête : remplacer R14 du quadrant par une valeur plus forte.</li>
<li><b>Quatre pucks, calibration, LED.</b> Un puck par case, <code>c</code> mesure et range les quatre notes en flash, <code>i</code> les reconnaît ensuite ; permuter deux pucks et refaire <code>i</code> : les noms doivent suivre. <code>l</code> allume alors les quatre cases, en blanc chaud ou en bleu selon la classe, et <code>o</code> les éteint : c'est le test de la chaîne LED. Les quatre notes attendues : {{NOTES}} kHz.</li>
<li><b>La campagne M1 à M11.</b> Le protocole du dépôt (<code>measurements/protocol.md</code>) dit, pour chaque mesure, la préparation, la commande, le fichier CSV à remplir et le critère ; la page sur le cerveau et le banc donne la valeur théorique de chaque grandeur et l'ordre : d'abord AMP_OUT à vide à l'oscilloscope, puis un puck sans aimant (M1), puis avec la ferrite (M2, la mesure qui décide), puis les quatre pucks, les voies A et B, les LED et le bois.</li>
</ol>
<p>Avant de croire le firmware, l'oscilloscope : sonde sur TP1 du quadrant (AMP_OUT, centré sur 1,65 V) et sur TP3 (le bus d'impulsion), déclenchement sur TP3. On doit voir l'impulsion de {{PULSE}} µs, {{BLANK}} µs de silence, puis la sonnerie qui remplit la fenêtre sans toucher les rails.</p>
</section>

<section>
<p class="eyebrow">Si ça ne marche pas</p>
<h2>Où regarder</h2>
<div class="tbl">
<table>
<thead><tr><th>symptôme</th><th>où regarder</th></tr></thead>
<tbody>
<tr><td>Pas de console</td><td>le port série est celui de la sonde ST-Link (ttyACM sous Linux, COM sous Windows), 115200 bauds ; le firmware est bien celui de <code>build/nucleo/</code></td></tr>
<tr><td>TP3 sans 5 V</td><td>polarité du jack (positif au centre), fusible F1, pont de soudure sur le buck, D1 à l'envers</td></tr>
<tr><td>TP2 sans 5 V</td><td>cavalier JP1 absent ou sur 2-3 sans buck ; LDO U2</td></tr>
<tr><td>Console vivante, <code>s</code> sans amplitude même avec un puck</td><td>nappe mal engagée ou contacts du mauvais côté ; 5VA absent sur le quadrant (TP2) ; MUX_EN_L ou PULSE_EN : regarder TP3 du quadrant à l'oscilloscope pendant <code>s</code>, l'impulsion doit y être</td></tr>
<tr><td>Note très différente de celle attendue</td><td>mauvais condensateur ou nombre de tours ; un LCR-mètre tranche en une minute ; du métal près de la case</td></tr>
<tr><td>Q faible, sonnerie courte</td><td>métal à proximité, bobine mal vernie, ou un aimant néodyme à la place de la ferrite ; comparer avec et sans aimant (M1 contre M2)</td></tr>
<tr><td>Sonnerie écrêtée</td><td>gain trop fort pour l'entrefer réel : R14 du quadrant vers 1 kΩ ou 2 kΩ</td></tr>
<tr><td>LED muettes</td><td><code>l</code> demande une calibration au préalable ; sinon TP1 LED_END de la carte de banc, tampon U3, 5V_LED et fusible F2</td></tr>
</tbody>
</table>
</div>
</section>

<section>
<p class="eyebrow">Lexique</p>
<h2>Les mots de cette page</h2>
<dl>
<dt>Shield</dt><dd>carte fille qui s'emboîte sur les connecteurs d'une carte de développement, au format des Arduino ici.</dd>
<dt>CMS</dt><dd>composant monté en surface, sans pattes traversantes ; les tailles 0603, 0805, 1206 sont ses dimensions en centièmes de pouce.</dd>
<dt>QFN, LFCSP</dt><dd>boîtiers plats sans broches apparentes, avec une plage de soudure sous le composant : air chaud ou plaque chauffante.</dd>
<dt>Nappe FPC</dt><dd>câble plat souple à contacts imprimés, pas de 0,5 mm entre conducteurs.</dd>
<dt>Gerber</dt><dd>les fichiers de fabrication d'un circuit imprimé, une couche par fichier.</dd>
<dt>C0G</dt><dd>diélectrique de condensateur céramique stable en température et dans le temps.</dd>
<dt>Puck</dt><dd>le palet de test qui tient lieu de pièce d'échecs.</dd>
<dt>Point de test</dt><dd>une pastille nue sur la carte, faite pour y poser une sonde.</dd>
<dt>CSV</dt><dd>le texte que la console écrit, une mesure par ligne, des virgules entre les colonnes ; les tableurs et les notebooks du dépôt le lisent tel quel.</dd>
</dl>
</section>

<p class="foot">Chiffres calculés par <code>chessboard_calc</code> depuis <code>config/board.yaml</code> du dépôt electronic-chess, nomenclatures des générateurs, septembre 2026 ; schémas de <code>tools/docfig</code>, note 20 du dépôt.</p>
</div>
"""
