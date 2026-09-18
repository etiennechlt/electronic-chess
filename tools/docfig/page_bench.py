"""The page on the brain board and the Nucleo bench
(`docs/pages/cerveau-banc.html`), the browser twin of note 19.
"""

from __future__ import annotations

from chessboard_calc.config import BoardConfig, Color, PieceType
from chessboard_calc.coupling import coupling, ringdown_signal
from chessboard_calc.resonance import check_separation, frequency_plan

from .bench import fig_bench_nucleo, fig_brain_blocks, fig_scan_cycle
from .common import fr_num
from .page import check, document
from .q import ADC_FS_FIRMWARE_HZ, listen_window_us, q_at


def bench_page(cfg: BoardConfig) -> str:
    plan = frequency_plan(cfg)
    q_min = cfg.resonator.q_min_with_magnet
    meas = cfg.measurement
    window = listen_window_us(cfg)
    sig = ringdown_signal(cfg, PieceType.PAWN, Color.BLACK, cfg.pitch.plateau_mm)
    cpl = coupling(cfg, PieceType.PAWN, cfg.pitch.plateau_mm, cfg.gap.air_gap_mm)
    reduced = cfg.plateau.quadrant.reduced
    p = cfg.pitch.plateau_mm
    board_w = reduced.squares * p + cfg.plateau.quadrant.front_end_strip_mm
    board_h = reduced.squares * p + reduced.strip_overhang_mm
    pucks = []
    for tp in cfg.mockup.test_pieces:
        ln = plan.line(tp.piece, tp.color)
        from docfig.q import piece_name

        pucks.append(
            f"{piece_name(tp.piece, tp.color)} {fr_num(ln.cap_nF)} nF ({ln.f0_hz / 1e3:.0f} kHz)"
        )
    v = {
        "FIG_BLOCS": fig_brain_blocks(cfg),
        "FIG_CYCLE": fig_scan_cycle(cfg),
        "FIG_BANC": fig_bench_nucleo(cfg),
        "MCU": cfg.mcu.part,
        "MHZ": f"{cfg.mcu.sysclk_mhz:.0f}",
        "B_LO": fr_num(meas.band_hz[0] / 1e3, 0),
        "B_HI": fr_num(meas.band_hz[1] / 1e3, 0),
        "PULSE": fr_num(meas.drive.pulse_us),
        "BLANK": fr_num(meas.blanking_us),
        "N": str(meas.fft_points),
        "FS": fr_num(ADC_FS_FIRMWARE_HZ / 1e6, 2),
        "WINDOW": fr_num(window, 0),
        "AVG": str(meas.coherent_avg),
        "SCAN_S": fr_num(2.0 * cfg.plateau.grid**2 / 1e3, 2),
        "IDLE": f"{meas.idle_scan_hz:.0f}",
        "GAP_TOTAL": fr_num(cfg.gap.nominal_total_mm),
        "BOARD": f"{fr_num(board_w, 0)} x {fr_num(board_h, 0)}",
        "STRIP": fr_num(cfg.plateau.quadrant.front_end_strip_mm, 0),
        "OVER": fr_num(reduced.strip_overhang_mm, 0),
        "PUCKS": ", ".join(pucks),
        "Q_MIN": f"{q_min:.0f}",
        "L_UH": fr_num(cfg.resonator.L_target_uH, 0),
        "L_TOL": fr_num(cfg.resonator.L_tol_pct, 0),
        "QB": f"{q_at(cfg, plan.line(PieceType.PAWN, Color.BLACK).f0_hz):.0f}",
        "F_LO": fr_num(plan.lines[0].f0_hz / 1e3, 0),
        "F_HI": fr_num(plan.lines[-1].f0_hz / 1e3, 0),
        "SEP30": fr_num(check_separation(cfg, q_min).min_gap_widths),
        "EMF_MV": fr_num(sig.emf_after_blanking_v * 1e3, 0),
        "SNR": f"{sig.snr_db:.0f}",
        "GAIN_MIN": f"{min(meas.preamp_gain):.0f}",
        "K": fr_num(cpl.k, 2),
        "TAU_RANGE": f"{fr_num(plan.lines[-1].tau_nominal_us, 0)} à {fr_num(plan.lines[0].tau_nominal_us, 0)}",
        "XTALK": fr_num(meas.crosstalk_max_db, 0),
        "SNR_MIN": fr_num(meas.snr_min_db, 0),
        "WOOD": fr_num(cfg.gap.surface_mm),
        "FELT": fr_num(cfg.gap.felt_mm),
    }
    page = document("Le cerveau et le banc", BENCH_BODY)
    for k, val in v.items():
        page = page.replace("{{" + k + "}}", val)
    check(page)
    return page


BENCH_BODY = r"""<div class="wrap">
<p class="eyebrow">Échiquier à résonateurs LC</p>
<h1>Le cerveau et le banc</h1>
<p class="lede">Suite de la page sur le facteur Q, pour le même lecteur : ce que fait la carte cerveau du plateau, et comment un banc réduit autour d'une carte de développement Nucleo, sans cerveau ni carte puissance, va confronter les grandeurs physiques calculées à la réalité.</p>

<div class="keep">
<p><strong>Le cerveau est un chef d'orchestre, pas un instrument de mesure.</strong> L'amplification et le filtrage sont sur les quadrants ; le cerveau choisit la case, frappe, écoute, calcule et raconte la partie.</p>
<p><strong>Le banc remplace le cerveau par une Nucleo</strong> qui porte le même microcontrôleur, et le plateau par un quadrant de quatre cases qui porte le même circuit. Trois composants en plus, pas trois cartes.</p>
<p><strong>Chaque grandeur calculée a sa mesure et son critère.</strong> Le tableau de la fin dit ce qu'on attend, comment on le vérifie, et ce qui fait échouer.</p>
</div>

<section>
<p class="eyebrow">Le cerveau</p>
<h2>À quoi il sert</h2>
<p>Le plateau est fait de quatre quadrants identiques (chacun seize cases, trente-deux LED et son frontal analogique) posés sous le contreplaqué, et d'une carte cerveau au fond de la base. Le cerveau décide quelle case on mesure, frappe, écoute, calcule la note, en déduit la pièce, compare deux balayages pour trouver le coup joué, allume les LED de camp et raconte la partie au pont radio. Il ne reçoit des quadrants que quatre signaux déjà amplifiés.</p>
<figure>
<div class="fig-scroll">{{FIG_BLOCS}}</div>
<figcaption><b>Ce qu'il y a sur la carte et qui parle à qui.</b> En haut l'alimentation, au centre le {{MCU}} à {{MHZ}} MHz, à gauche les quatre nappes de quadrant, à droite la radio et les liaisons, en bas l'interface et les connecteurs vers les autres cartes.</figcaption>
</figure>
<div class="tbl">
<table>
<thead><tr><th>bloc</th><th>composants</th><th>rôle</th></tr></thead>
<tbody>
<tr><td>Microcontrôleur</td><td>{{MCU}}, {{MHZ}} MHz, sans quartz, SWD, USB-C</td><td>mesure, calcul, calibration en flash, arbitre (à écrire), protocole</td></tr>
<tr><td>Alimentation</td><td>fusible 2 A, buck 5 V TPS62130 en PWM forcé, LDO 3,3 V AP2112K</td><td>le 5 V nourrit la logique, les LED et le buzzer ; le 3,3 V le MCU et les décodeurs des quadrants</td></tr>
<tr><td>Îlot analogique</td><td>LDO 5 V LP2985, perle de ferrite, découplages</td><td>un 5 V propre, séparé du 5 V numérique, pour les aiguilleurs, l'amplificateur et les filtres des quadrants</td></tr>
<tr><td>Rail d'impulsion</td><td>fusible 1 A, 100 µF</td><td>le 12 V de la batterie envoyé tel quel aux quadrants pour frapper les bobines</td></tr>
<tr><td>Rail LED</td><td>fusible 2 A, 100 µF</td><td>le 5 V des 128 LED, séparé pour que leurs appels de courant ne remontent pas</td></tr>
<tr><td>Liens quadrant</td><td>quatre connecteurs FPC 16 broches</td><td>un bus de commande commun (adresse, enables, PULSE_EN, DAMP_EN_N), un signal AMP_OUT par quadrant vers un convertisseur dédié, les rails</td></tr>
<tr><td>Chaîne LED</td><td>tampon 74AHCT1G125</td><td>passe le signal de 3,3 V à 5 V, entre dans le quadrant 1, ressort, entre dans le 2, et ainsi de suite</td></tr>
<tr><td>Communication</td><td>ADuM1201, interrupteur de charge, ESP32-S3, embase Pi Zero, cavalier</td><td>une UART isolée à 115200 bauds vers le pont radio (WiFi et BLE), ou vers un Pi en option ; le pont ne fait que relayer</td></tr>
<tr><td>Interface</td><td>buzzer sur FET, quatre LED d'état, bouton</td><td>signaux au joueur</td></tr>
<tr><td>Connecteurs</td><td>J10 vers la carte puissance, J9 vers la carte moteurs (phase 2)</td><td>le cerveau n'embarque ni batterie ni moteurs</td></tr>
</tbody>
</table>
</div>
<p>Trois idées à garder. <b>Un seul bus pour quatre quadrants</b> : les quatre nappes reçoivent les mêmes fils de commande, seul l'enable du bon quadrant est actif, le cerveau ne mesure jamais deux cases à la fois. <b>L'analogique reste court</b> : le seul signal fragile qui traverse une nappe est AMP_OUT, déjà amplifié 230 fois. <b>Rien de numérique n'émet pendant qu'on écoute</b> : le buck découpe au-dessus de 2 MHz, hors de la bande {{B_LO}} à {{B_HI}} kHz ; les trames LED ne partent qu'entre deux mesures ; la radio est coupée pendant les balayages.</p>
</section>

<section>
<p class="eyebrow">Le cerveau</p>
<h2>Ce qu'il fait, dans le temps</h2>
<figure>
<div class="fig-scroll">{{FIG_CYCLE}}</div>
<figcaption><b>Le cycle du firmware.</b> La première ligne existe et tourne ; l'arbitre et les messages de partie de la dernière ligne sont encore à écrire.</figcaption>
</figure>
<p>Pour chaque quadrant et chaque bobine, le firmware adresse la case, frappe pendant {{PULSE}} µs depuis le 12 V, étouffe la spirale pendant {{BLANK}} µs, écoute {{N}} points à {{FS}} Méch/s ({{WINDOW}} µs), calcule la FFT et interpole le pic : une fréquence à 1 kHz près. Avec le moyennage x{{AVG}}, une case coûte environ 2 ms et un balayage complet des 64 cases {{SCAN_S}} s ; au repos le plateau balaie {{IDLE}} fois par seconde.</p>
<p>La classification est au plus proche voisin contre une table de calibration : la note de chaque pièce, mesurée une fois et stockée en flash. Deux balayages successifs qui diffèrent (une case vidée, une case remplie) font un coup. L'arbitre (coup légal, roque, promotion, prise en passant) vient ensuite, puis une ligne de texte vers le pont radio : occupation des cases, coup, position, état.</p>
</section>

<section>
<p class="eyebrow">Le banc</p>
<h2>Pourquoi une Nucleo avant le cerveau</h2>
<p>Le projet repose sur une hypothèse physique qui n'a été que calculée : un résonateur passif sous aimant ferrite reste discriminable à travers {{GAP_TOTAL}} mm de bois et d'air. Tant qu'elle n'est pas mesurée, fabriquer le cerveau, la carte puissance et l'horloge revient à construire autour d'une inconnue. Or rien de tout cela n'est nécessaire pour mesurer.</p>
<ul>
<li>La <b>Nucleo-G474RE</b> porte le même microcontrôleur que le cerveau, avec sa sonde de programmation et son port série intégrés ; le brochage du bus de commande retenu pour le cerveau tombe sur son connecteur Arduino.</li>
<li>Le <b>quadrant réduit 2 x 2</b> porte le même circuit, le même bus et le même firmware que le 4 x 4, avec quatre cases au lieu de seize ; ce qu'il valide se reporte sans redessin.</li>
<li>Il manque au banc un 12 V, un 5 V analogique propre et un tampon LED : trois composants, pas trois cartes.</li>
</ul>
<p>Multiplier ce 2 x 2 en seize tuiles pour couvrir 64 cases n'est en revanche pas possible avec cette carte : sa bande de frontal de {{STRIP}} mm et son dépassement de {{OVER}} mm laisseraient des vides entre les cases. Le chemin retenu est 2 x 2 comme banc, quadrants 4 x 4 pour le plateau.</p>
<figure>
<div class="fig-scroll">{{FIG_BANC}}</div>
<figcaption><b>Le banc, à l'échelle pour le quadrant.</b> La carte de banc s'emboîte sur la Nucleo, une nappe de seize fils va au quadrant {{BOARD}} mm, les pucks de test sont posés sur le contreplaqué et le feutre, les instruments regardent par-dessus l'épaule du firmware.</figcaption>
</figure>
<div class="tbl">
<table>
<thead><tr><th>élément</th><th>rôle</th><th>état</th></tr></thead>
<tbody>
<tr><td>Nucleo-G474RE</td><td>le MCU, la programmation, la console série</td><td>du commerce ; firmware <code>make NUCLEO=1</code></td></tr>
<tr><td>Quadrant 2 x 2 assemblé</td><td>quatre cases, frontal complet, huit LED</td><td>généré ; deux nets à fermer, codes LCSC et devis à faire</td></tr>
<tr><td>Carte de banc au format shield Nucleo-64</td><td>jack 12 V avec protection, LDO 5VA, rail 5V_LED, tampon pour LED_DIN, connecteur FPC 16, pont AMP_OUT vers A0, points de test</td><td>générée par le dépôt (<code>hardware/bench</code>) ; repli sans carte : breakout FPC vers 2,54 mm, fils, module LDO 5 V</td></tr>
<tr><td>Alimentation de laboratoire 12 V limitée en courant</td><td>le rail d'impulsion et le 5VA ; linéaire ou batterie, jamais un chargeur à découpage près des bobines</td><td>outillage</td></tr>
<tr><td>Quatre pucks de test</td><td>bobine de {{L_UH}} µH bobinée sur gabarit, condensateur C0G, aimant ferrite : {{PUCKS}}, le bas de bande, l'espacement le plus serré</td><td>gabarits et pucks imprimés</td></tr>
<tr><td>Contreplaqué {{WOOD}} mm et feutre {{FELT}} mm</td><td>l'entrefer nominal de {{GAP_TOTAL}} mm</td><td>à découper</td></tr>
<tr><td>Oscilloscope 2 voies, 100 Méch/s</td><td>voir AMP_OUT et le bus d'impulsion avant de croire le firmware</td><td>outillage</td></tr>
<tr><td>LCR-mètre</td><td>L et Q des bobines nues, la référence de M1</td><td>outillage</td></tr>
<tr><td>Analyseur logique</td><td>vérifier le bus de commande et les temps du cycle</td><td>outillage</td></tr>
</tbody>
</table>
</div>
<p>Le câblage entre le quadrant et la Nucleo suit les broches retenues pour le cerveau : AMP_OUT sur A0, PULSE_EN sur A2, les trois bits d'adresse sur D3, D4 et D5, les deux enables sur A5 et A4, LED_DIN sur D13 ; seul DAMP_EN_N change de broche (D6 au lieu du PC2 du cerveau, qui n'atteint qu'un connecteur Morpho), et la carte de banc tient sur les seules embases Arduino. Le firmware du cerveau se compile pour le banc en une commande (<code>make NUCLEO=1</code>) : la console passe sur le port série de la sonde, un seul quadrant de quatre bobines est balayé, la chaîne LED est celle du 2 x 2 ; tout le reste est identique au cerveau.</p>
</section>

<section>
<p class="eyebrow">Théorie contre réalité</p>
<h2>Ce que le banc mesure</h2>
<p>Chaque ligne oppose une grandeur calculée par le modèle du dépôt à la mesure qui la vérifie, avec le critère du protocole M1 à M11. M2 est la mesure décisive : si le Q chute trop avec l'aimant, on revoit l'aimant ou les classes avant tout le reste.</p>
<div class="tbl">
<table>
<thead><tr><th>grandeur</th><th>théorie</th><th>comment on la mesure</th><th>critère</th><th>mesure</th></tr></thead>
<tbody>
<tr><td>Inductance de la bobine de pièce</td><td>{{L_UH}} µH visés, ±{{L_TOL}} % de dispersion main</td><td>LCR-mètre sur la bobine nue</td><td>dans la tolérance</td><td>M1, M6</td></tr>
<tr><td>Q de la pièce sans aimant</td><td>{{QB}} (pion noir) à 107 (roi blanc) estimés</td><td>décrément logarithmique de l'enveloppe du dump brut</td><td>≥ 40</td><td>M1</td></tr>
<tr><td>Q avec l'aimant ferrite</td><td>chute faible attendue (ferrite isolante)</td><td>même méthode, aimant inséré</td><td>≥ {{Q_MIN}} et chute ≤ 20 % ; la mesure décisive</td><td>M2</td></tr>
<tr><td>Q avec un aimant néodyme</td><td>chute de 40 à 70 % attendue</td><td>même méthode</td><td>informatif : quantifie ce que la ferrite évite</td><td>M3</td></tr>
<tr><td>Note f0 de chaque classe</td><td>{{F_LO}} à {{F_HI}} kHz, séparation {{SEP30}} largeurs à Q = {{Q_MIN}}</td><td>colonnes fa (FFT) et fb (période) du CSV</td><td>quatre pucks du bas de bande distinguables sans erreur</td><td>M4, M9</td></tr>
<tr><td>Amplitude et rapport signal sur bruit</td><td>FEM après blanking {{EMF_MV}} mV, SNR {{SNR}} dB (estimation optimiste : avec le gain {{GAIN_MIN}} la chaîne écrête sûrement, à voir à l'oscilloscope en premier)</td><td>colonnes amp_mv et snr_db10, à l'entrefer nominal puis à 8 mm</td><td>≥ {{SNR_MIN}} dB, ≥ 10 dB à 8 mm</td><td>M4, M4bis</td></tr>
<tr><td>Couplage k</td><td>{{K}} à l'entrefer nominal</td><td>déduit de l'amplitude en fonction de l'entrefer (cales)</td><td>cohérent avec le modèle</td><td>M4bis</td></tr>
<tr><td>Constante de temps τ</td><td>{{TAU_RANGE}} µs à Q = 50</td><td>pente de l'enveloppe</td><td>cohérente avec le Q mesuré</td><td>M1</td></tr>
<tr><td>Diaphonie entre cases</td><td>budget {{XTALK}} dB</td><td>un puck sur une case, lecture des trois autres</td><td>≤ {{XTALK}} dB</td><td>M5</td></tr>
<tr><td>Détuning entre pièces identiques</td><td>quelques kHz au plus</td><td>deux pucks 12 nF côte à côte</td><td>&lt; 3 kHz</td><td>M5bis</td></tr>
<tr><td>Dispersion de quatre bobines main</td><td>±{{L_TOL}} % de L, soit ±2,5 % de f</td><td>quatre bobines dans le même puck</td><td>≤ ±3 %</td><td>M6</td></tr>
<tr><td>Plancher de bruit et alimentation</td><td>buck hors bande, LDO de référence</td><td>dump brut à vide, LDO contre buck, radio allumée ou éteinte</td><td>delta ≤ 6 dB</td><td>M8, partiel sur le banc</td></tr>
<tr><td>Voie A contre voie B</td><td>~1 kHz (FFT), ~0,05 % (période)</td><td>colonnes fa et fb côte à côte</td><td>sigma fb &lt; 200 Hz</td><td>M9</td></tr>
<tr><td>Bois contre acrylique</td><td>effet nul attendu</td><td>même case, deux surfaces, puis bois humide</td><td>df &lt; 500 Hz, dQ &lt; 10 %</td><td>M10</td></tr>
<tr><td>Bruit des LED</td><td>nul par construction (trames hors mesure)</td><td>LED éteintes puis au blanc plein</td><td>dsigma &lt; 100 Hz, &lt; 1 dB</td><td>M11</td></tr>
</tbody>
</table>
</div>
<p>Ce que le banc ne mesure pas : l'approche de l'aimant néodyme du chariot (M7, phase 2), les effets propres à quatre quadrants (128 LED en série, quatre nappes, quatre convertisseurs) et le buck du cerveau, qui attendent le plateau.</p>
</section>

<section>
<p class="eyebrow">Dans quel ordre</p>
<h2>Les premières heures sur le banc</h2>
<ol>
<li>AMP_OUT à vide à l'oscilloscope : plancher de bruit, raies parasites (chargeurs, radio grandes ondes).</li>
<li>Un puck : amplitude, écrêtage éventuel (la résistance de gain de l'amplificateur est prête à changer), τ et Q.</li>
<li>M2 avec la ferrite : si Q passe sous {{Q_MIN}}, on s'arrête et on revoit l'aimant ou les classes avant tout le reste.</li>
<li>Les quatre pucks du bas de bande : séparation, calibration, identification.</li>
<li>Voie A contre voie B, puis différentiel contre single-ended, ce qui demande une option de cavalier sur le 2 x 2 avant sa commande.</li>
<li>Les LED (M11), puis le bois (M10).</li>
</ol>
<p>Chaque mesure remplit une ligne du tableau de synthèse du protocole ; c'est ce tableau qui autorise, ou non, la commande des quatre quadrants et du cerveau.</p>
</section>

<p class="foot">Chiffres calculés par <code>chessboard_calc</code> depuis <code>config/board.yaml</code> du dépôt electronic-chess, septembre 2026 ; schémas de <code>tools/docfig</code>, note 19 du dépôt.</p>
</div>
"""
