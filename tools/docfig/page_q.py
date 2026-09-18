"""The page on the quality factor Q (`docs/pages/facteur-q.html`), the
browser twin of note 18: every number from chessboard_calc, every figure
from docfig.q.
"""

from __future__ import annotations

import json

from chessboard_calc.config import BoardConfig, Color, PieceType
from chessboard_calc.coupling import coupling
from chessboard_calc.inductance import piece_coil_design
from chessboard_calc.resonance import (
    check_separation,
    frequency_plan,
    resonance_width_hz,
    ringdown_tau_us,
)

from .common import fr_num
from .page import check, document
from .q import (
    ADC_FS_FIRMWARE_HZ,
    fig_q_chain,
    fig_q_plan,
    fig_q_ringdown,
    fig_q_stack,
    fig_q_timeline,
    fig_q_vs_frequency,
    fig_q_width,
    listen_window_us,
    plan_rows,
    q_at,
    q_curve,
)


def q_page(cfg: BoardConfig) -> str:
    q_nom, q_min = cfg.resonator.q_nominal, cfg.resonator.q_min_with_magnet
    plan = frequency_plan(cfg)
    sep30 = check_separation(cfg, q_min)
    sep50 = check_separation(cfg, q_nom)
    pawn_b = plan.line(PieceType.PAWN, Color.BLACK)
    pawn_w = plan.line(PieceType.PAWN, Color.WHITE)
    knight_w = plan.line(PieceType.KNIGHT, Color.WHITE)
    king_w = plan.line(PieceType.KING, Color.WHITE)
    design = piece_coil_design(cfg, PieceType.PAWN, cfg.pitch.plateau_mm)
    cpl = coupling(cfg, PieceType.PAWN, cfg.pitch.plateau_mm, cfg.gap.air_gap_mm)
    window = listen_window_us(cfg)
    fs, qs = q_curve(cfg)
    caps = sorted({ln.cap_nF for ln in plan.lines})
    rows = "".join(
        f"<tr><td>{r['glyph']} {r['name']}</td><td class='n'>{r['cap']}</td>"
        f"<td class='n'>{r['f0']}</td><td class='n'>{r['w50']}</td>"
        f"<td class='n'>{r['w30']}</td><td class='n'>{r['tau']}</td></tr>"
        for r in plan_rows(cfg)
    )
    v = {
        "Q_NOM": f"{q_nom:.0f}",
        "Q_MIN": f"{q_min:.0f}",
        "F_LO": fr_num(pawn_b.f0_hz / 1e3, 0),
        "F_HI": fr_num(king_w.f0_hz / 1e3, 0),
        "WINDOW": fr_num(window, 0),
        "TAU_LO": fr_num(ringdown_tau_us(pawn_b.f0_hz, q_nom), 0),
        "TAU_HI": fr_num(ringdown_tau_us(king_w.f0_hz, q_nom), 0),
        "TAU_Q10": fr_num(ringdown_tau_us(pawn_b.f0_hz, 10), 0),
        "L_UH": fr_num(cfg.resonator.L_target_uH, 0),
        "C_MIN": fr_num(caps[0]),
        "C_MAX": fr_num(caps[-1]),
        "W50_LO": fr_num(pawn_b.width_nominal_hz / 1e3),
        "W50_HI": fr_num(king_w.width_nominal_hz / 1e3),
        "W30_LO": fr_num(pawn_b.width_min_q_hz / 1e3),
        "W30_HI": fr_num(king_w.width_min_q_hz / 1e3),
        "F_PW": fr_num(pawn_w.f0_hz / 1e3, 0),
        "F_KW": fr_num(knight_w.f0_hz / 1e3, 0),
        "GAP_PK": fr_num((knight_w.f0_hz - pawn_w.f0_hz) / 1e3, 0),
        "W_PW50": fr_num(resonance_width_hz(pawn_w.f0_hz, q_nom) / 1e3),
        "W_PW10": fr_num(resonance_width_hz(pawn_w.f0_hz, 10) / 1e3, 0),
        "SEP50": fr_num(sep50.min_gap_widths),
        "SEP30": fr_num(sep30.min_gap_widths),
        "B_LO": fr_num(cfg.measurement.band_hz[0] / 1e3, 0),
        "B_HI": fr_num(cfg.measurement.band_hz[1] / 1e3, 0),
        "N_TURNS": str(design.n_turns),
        "WIRE": fr_num(design.wire_mm, 2),
        "PROX": fr_num(cfg.resonator.coil.proximity_factor),
        "Q40": f"{q_at(cfg, 40e3):.0f}",
        "QB": f"{q_at(cfg, pawn_b.f0_hz):.0f}",
        "QW": f"{q_at(cfg, pawn_w.f0_hz):.0f}",
        "XTALK": fr_num(cfg.measurement.crosstalk_max_db, 0),
        "GAP_TOTAL": fr_num(cfg.gap.nominal_total_mm),
        "K": fr_num(cpl.k, 2),
        "TOTAL_US": fr_num(2 + 0.3 + 1 + 0.4 + 2 + window, 0),
        "N_SAMPLES": str(cfg.measurement.fft_points),
        "FS": fr_num(ADC_FS_FIRMWARE_HZ / 1e6, 2),
        "GAP_MIN": fr_num(min(g.gap_hz for g in sep30.gaps) / 1e3, 0),
        "FS_JSON": json.dumps([round(f, 1) for f in fs]),
        "QS_JSON": json.dumps([round(q, 1) for q in qs]),
        "TABLE": rows,
        "FIG1": fig_q_ringdown(cfg),
        "FIG2": fig_q_width(cfg),
        "FIG3": fig_q_plan(cfg, interactive=True),
        "FIG4": fig_q_vs_frequency(cfg, interactive=True),
        "FIG5": fig_q_stack(cfg),
        "FIG6": fig_q_timeline(cfg),
        "FIG7": fig_q_chain(cfg),
    }
    page = document("Le facteur Q", Q_BODY, Q_SCRIPT)
    for k, val in v.items():
        page = page.replace("{{" + k + "}}", val)
    check(page)
    return page


Q_BODY = r"""<div class="wrap">
<p class="eyebrow">Échiquier à résonateurs LC</p>
<h1>Le facteur Q</h1>
<p class="lede">Chaque pièce de cet échiquier contient un petit circuit qui « sonne » à une note précise quand on l'excite. Q dit combien de temps la note dure et à quel point elle est pure. Cette page explique Q sans électronique préalable, avec les chiffres réels du projet.</p>

<div class="keep">
<p><strong>Q est un nombre sans unité.</strong> Plus il est grand, plus l'oscillation dure et plus la note est fine.</p>
<p><strong>Pour l'échiquier, Q décide si deux pièces voisines restent distinguables.</strong> Le projet vise Q = {{Q_NOM}} et accepte au minimum {{Q_MIN}} une fois l'aimant posé.</p>
<p><strong>Ce qui fait baisser Q :</strong> la résistance du fil de la bobine, le métal à proximité, et tout ce qui absorbe l'énergie de l'oscillation.</p>
</div>

<section>
<p class="eyebrow">L'image à retenir</p>
<h2>Le diapason et la boîte en carton</h2>
<p>Frappez un diapason : il vibre longtemps sur une note nette. Frappez une boîte en carton : un « toc » sourd, fini aussitôt. Le diapason a un Q élevé, la boîte un Q faible. Dans le projet, la pièce est le diapason. La case la « frappe » par une brève impulsion magnétique, puis écoute sa note décroître : c'est ce que le dépôt appelle le <b>ringdown</b>.</p>
<p>Q se lit directement sur cette décroissance. Comptez les oscillations visibles avant que la note ne s'éteigne : vous avez à peu près Q. Plus précisément, après Q/π oscillations il reste 37 % de l'amplitude, et après Q oscillations il en reste 4 %.</p>
<figure>
<div class="fig-scroll">{{FIG1}}</div>
<figcaption><b>Même note, deux Q.</b> Un pion noir sonne à {{F_LO}} kHz. Avec Q = {{Q_NOM}}, la sonnerie remplit la fenêtre d'écoute de {{WINDOW}} µs (τ = {{TAU_LO}} µs). Avec Q = 10 elle est éteinte au bout de {{TAU_Q10}} µs environ : il reste peu de périodes à analyser, et la note est floue.</figcaption>
</figure>
</section>

<section>
<p class="eyebrow">La définition</p>
<h2>Ce que Q mesure exactement</h2>
<p>Une oscillation, c'est de l'énergie qui fait l'aller-retour entre deux réservoirs. Pour une balançoire : la hauteur et la vitesse. Pour notre circuit : le champ magnétique de la bobine (L) et la charge du condensateur (C). À chaque aller-retour, une fraction part en chaleur dans la résistance du fil (R). Q compte, à un facteur 2π près, combien d'allers-retours la réserve d'énergie permet avant d'être épuisée.</p>
<div class="formulas">
<div class="formula"><p class="f">Q = 2π · énergie stockée / énergie perdue par période</p><p class="d">La définition. Sans unité.</p></div>
<div class="formula"><p class="f">f0 = 1 / (2π √(L·C))</p><p class="d">La note. Une seule bobine pour toutes les pièces, douze condensateurs pour douze notes.</p></div>
<div class="formula"><p class="f">Q = 2π·f0·L / R</p><p class="d">Pour notre circuit : la bobine stocke, sa résistance perd. Le numérateur grandit avec la fréquence.</p></div>
<div class="formula"><p class="f">Δf = f0 / Q</p><p class="d">La largeur de la note, lue à mi-puissance. Q élevé, note fine.</p></div>
<div class="formula"><p class="f">τ = Q / (π·f0)</p><p class="d">Le temps au bout duquel il reste 37 % de l'amplitude.</p></div>
</div>
<p>Les chiffres du projet : bobine de {{L_UH}} µH commune à toutes les pièces, condensateurs C0G à 1 % de {{C_MIN}} à {{C_MAX}} nF, douze notes de {{F_LO}} à {{F_HI}} kHz. À Q = {{Q_NOM}}, les notes ont {{W50_LO}} à {{W50_HI}} kHz de large et durent τ = {{TAU_LO}} à {{TAU_HI}} µs. À Q = {{Q_MIN}}, le plancher accepté avec l'aimant, elles s'élargissent à {{W30_LO}} à {{W30_HI}} kHz.</p>
</section>

<section>
<p class="eyebrow">En fréquence</p>
<h2>La même chose vue comme une note</h2>
<p>Un résonateur ne répond fort que tout près de sa note. La largeur de sa réponse vaut f0/Q. Avec un Q élevé la raie est fine et se distingue facilement de la voisine ; avec un Q faible elle s'étale et les deux se confondent. La paire la plus serrée du projet est le pion blanc à {{F_PW}} kHz et le cavalier blanc à {{F_KW}} kHz, à {{GAP_PK}} kHz l'un de l'autre.</p>
<figure>
<div class="fig-scroll">{{FIG2}}</div>
<figcaption><b>Largeur de raie et voisinage.</b> À Q = {{Q_NOM}}, le pion blanc a une raie de {{W_PW50}} kHz : le cavalier est à {{SEP50}} largeurs, sans ambiguïté. À Q = 10, la raie fait {{W_PW10}} kHz, plus que l'écart entre les deux notes : les réponses se recouvrent (courbes pointillées du voisin).</figcaption>
</figure>
<p>Point important pour les discussions sur « les fréquences trop élevées » : la largeur relative 1/Q ne dépend pas de la fréquence. Descendre ou monter la bande ne rapproche ni n'éloigne les notes. Seul Q compte, et Q dépend de la fréquence, comme la section sur la bobine le montre.</p>
</section>

<section>
<p class="eyebrow">L'échiquier</p>
<h2>Douze pièces, douze notes</h2>
<p>Six types de pièces fois deux camps font douze classes. Chacune reçoit un condensateur de la série E12 ; les notes s'échelonnent de {{F_LO}} à {{F_HI}} kHz. Le plateau ne cherche pas une précision absolue : il mesure la note de chaque pièce une fois pour toutes en calibration, puis classe chaque lecture au plus proche voisin. Il suffit donc que les raies ne se recouvrent pas, même à Q = {{Q_MIN}}.</p>
<figure>
<div class="fig-scroll" id="fig3">{{FIG3}}<div class="tip" id="tip3" hidden></div></div>
<figcaption><b>Le plan de fréquences à Q = {{Q_MIN}}.</b> Pièces noires pleines, blanches creuses, comme sur un diagramme d'échecs. Survolez une raie pour lire ses chiffres. La paire la plus serrée reste séparée de {{SEP30}} largeurs de raie ; un test automatique du dépôt casse si une modification passe sous 2,4.</figcaption>
</figure>
<div class="tbl">
<table>
<thead><tr><th>pièce</th><th class="n">C (nF)</th><th class="n">f0 (kHz)</th><th class="n">largeur à Q = {{Q_NOM}} (kHz)</th><th class="n">largeur à Q = {{Q_MIN}} (kHz)</th><th class="n">τ à Q = {{Q_NOM}} (µs)</th></tr></thead>
<tbody>{{TABLE}}</tbody>
</table>
</div>
</section>

<section>
<p class="eyebrow">La bobine</p>
<h2>D'où vient le Q d'une pièce, et pourquoi la bande est là où elle est</h2>
<p>Q = 2π·f0·L / R : le numérateur grandit avec la fréquence, le dénominateur (la résistance du fil) ne grandit que lentement, par l'effet de peau. Pour une bobine plate bobinée main de {{L_UH}} µH, Q monte donc avec la fréquence jusqu'à quelques mégahertz, où la capacité parasite du bobinage et de l'aiguilleur reprend la main. La bande de mesure du projet, {{B_LO}} à {{B_HI}} kHz, est posée sur cette montée.</p>
<figure>
<div class="fig-scroll" id="fig4">{{FIG4}}</div>
<figcaption><b>Q estimé de la bobine du pion</b> ({{N_TURNS}} tours de fil de {{WIRE}} mm), avec le modèle simplifié du dépôt (facteur de proximité {{PROX}}). À 40 kHz, Q ≈ {{Q40}} : trop peu. Dans la bande, {{QB}} à {{QW}} pour les deux pions. Survolez la courbe pour lire une valeur. La mesure M1 du protocole remplace ces estimations par la réalité.</figcaption>
</figure>
<p>Deux autres raisons tiennent la bande où elle est. Dix fois plus bas, il faudrait des condensateurs de 15 à 120 nF, où le C0G à 1 % n'existe plus, or c'est sa stabilité thermique qui porte l'identité des pièces. Et τ = Q/(π·f0) : à fréquence dix fois plus basse, chaque case mettrait dix fois plus longtemps à sonner, et un balayage complet des 64 cases passerait de 0,13 s à 1,3 s.</p>
</section>

<section>
<p class="eyebrow">Les ennemis de Q</p>
<h2>Ce qui abîme Q</h2>
<ul>
<li><b>La résistance du fil.</b> C'est la perte de base, fixée par le diamètre du fil et le nombre de tours. Le dépôt choisit le plus gros fil qui tient dans la base de chaque pièce.</li>
<li><b>Le métal à proximité.</b> Un objet conducteur près de la bobine voit naître des courants de Foucault qui volent de l'énergie à chaque période. Un aimant néodyme (conducteur) dans la pièce aurait ruiné Q ; le projet a choisi une ferrite, isolante. La mesure M2 vérifie que Q reste au-dessus de {{Q_MIN}} avec l'aimant posé : c'est la mesure décisive du projet.</li>
<li><b>Ce qui est branché sur la bobine.</b> Côté plateau, une résistance de 680 ohms est justement mise aux bornes de la spirale de la case pendant 2 µs pour tuer sa propre sonnerie : on veut Q élevé pour la pièce, Q faible pour la case au moment d'écouter.</li>
<li><b>La pièce voisine.</b> Deux résonateurs proches se couplent et se prêtent de l'énergie. Le budget de diaphonie entre cases est de {{XTALK}} dB.</li>
</ul>
</section>

<section>
<p class="eyebrow">La mesure</p>
<h2>Comment le plateau frappe et écoute</h2>
<p>Sous chaque case, une spirale gravée dans le circuit imprimé joue le rôle de la baguette et de l'oreille. Entre elle et la bobine de la pièce : {{GAP_TOTAL}} mm de circuit imprimé, d'air, de contreplaqué et de feutre. Environ un huitième du champ magnétique traverse les deux bobines (k ≈ {{K}}), et cela suffit.</p>
<figure>
<div class="fig-scroll">{{FIG5}}</div>
<figcaption><b>Coupe verticale sous un pion.</b> La bobine plate est au fond de la base, le condensateur C0G dans son trou central, l'aimant ferrite au-dessus. Le champ magnétique commun aux deux bobines porte la note à travers le bois.</figcaption>
</figure>
<figure>
<div class="fig-scroll">{{FIG6}}</div>
<figcaption><b>Une mesure dure environ {{TOTAL_US}} µs.</b> L'impulsion de 12 V est brève et large bande : elle excite toutes les notes possibles à la fois, sans balayage. Le blanking étouffe la sonnerie propre de la spirale de la case ; ensuite seule la pièce sonne, et le convertisseur enregistre {{N_SAMPLES}} points à {{FS}} Méch/s.</figcaption>
</figure>
<figure>
<div class="fig-scroll">{{FIG7}}</div>
<figcaption><b>De la pièce au résultat.</b> Le calcul extrait la fréquence de la sonnerie à 1 kHz près, par transformée de Fourier ou par comptage des périodes ; les notes étant espacées de {{GAP_MIN}} kHz au minimum, la pièce et son camp en découlent.</figcaption>
</figure>
</section>

<section>
<p class="eyebrow">Lexique</p>
<h2>Les mots du projet</h2>
<dl>
<dt>Résonateur LC</dt><dd>Une bobine (L) et un condensateur (C) en boucle : le circuit le plus simple qui sache osciller.</dd>
<dt>Fréquence propre f0</dt><dd>La note à laquelle le résonateur sonne naturellement, fixée par L et C.</dd>
<dt>Ringdown</dt><dd>La sonnerie qui décroît après la frappe. C'est elle que le plateau enregistre.</dd>
<dt>Largeur de raie</dt><dd>La plage de fréquences sur laquelle le résonateur répond fort, égale à f0/Q.</dd>
<dt>τ (tau)</dt><dd>La constante de temps de la décroissance : au bout de τ il reste 37 % de l'amplitude.</dd>
<dt>C0G</dt><dd>Une famille de condensateurs céramiques dont la valeur ne bouge presque pas avec la température ni le temps. C'est ce qui rend la note d'une pièce stable.</dd>
<dt>Courants de Foucault</dt><dd>Courants induits dans un métal par un champ magnétique variable ; ils chauffent le métal et volent l'énergie de l'oscillation.</dd>
<dt>Blanking</dt><dd>Les 2 µs pendant lesquelles on étouffe volontairement la spirale de la case avant d'écouter la pièce.</dd>
<dt>FFT</dt><dd>La transformée de Fourier rapide : le calcul qui transforme un enregistrement dans le temps en liste de notes présentes.</dd>
<dt>Diaphonie</dt><dd>La part du signal d'une case qui fuit vers la case voisine.</dd>
</dl>
</section>

<p class="foot">Chiffres calculés par <code>chessboard_calc</code> depuis <code>config/board.yaml</code> du dépôt electronic-chess, septembre 2026 ; schémas de <code>tools/docfig</code>, note 18 du dépôt. Les Q de bobine sont des estimations de conception ; les mesures M1 et M2 du protocole donnent les valeurs réelles.</p>
</div>
"""

Q_SCRIPT = r"""<script>
(function(){
  var fig = document.getElementById('fig3'), tip = document.getElementById('tip3');
  if (fig && tip) {
    function place(ev){
      var r = fig.getBoundingClientRect();
      var x = ev.clientX - r.left + fig.scrollLeft + 14, y = ev.clientY - r.top + 14;
      if (x + tip.offsetWidth > r.width + fig.scrollLeft - 8) x = ev.clientX - r.left + fig.scrollLeft - tip.offsetWidth - 14;
      tip.style.left = x + 'px'; tip.style.top = y + 'px';
    }
    Array.prototype.forEach.call(fig.querySelectorAll('.peak'), function(g){
      g.addEventListener('pointerenter', function(ev){ tip.innerHTML = g.getAttribute('data-html'); tip.hidden = false; place(ev); });
      g.addEventListener('pointermove', place);
      g.addEventListener('pointerleave', function(){ tip.hidden = true; });
    });
  }
  var svg = document.getElementById('qsvg');
  if (svg) {
    var F = {{FS_JSON}}, Q = {{QS_JSON}};
    var X0 = 70, PX = (860 - 70) / 700, YB = 280, PY = (280 - 50) / 120;
    var xh = document.getElementById('xh');
    var line = xh.querySelector('line'), dot = xh.querySelector('circle'), box = xh.querySelector('rect'), txt = xh.querySelector('text');
    svg.addEventListener('pointermove', function(ev){
      var r = svg.getBoundingClientRect();
      var xv = (ev.clientX - r.left) * 900 / r.width;
      var f = (xv - X0) / PX;
      if (f < F[0] || f > F[F.length - 1]) { xh.hidden = true; return; }
      var i = Math.round((f - F[0]) / 5); if (i < 0) i = 0; if (i >= F.length) i = F.length - 1;
      var x = X0 + F[i] * PX, y = YB - Math.min(Q[i], 120) * PY;
      line.setAttribute('x1', x); line.setAttribute('x2', x);
      dot.setAttribute('cx', x); dot.setAttribute('cy', y);
      var label = F[i].toFixed(0) + ' kHz : Q ≈ ' + Q[i].toFixed(0);
      var bx = x + 12; if (bx + 150 > 860) bx = x - 162;
      box.setAttribute('x', bx); box.setAttribute('y', y - 32);
      txt.setAttribute('x', bx + 8); txt.setAttribute('y', y - 17); txt.textContent = label;
      xh.hidden = false;
    });
    svg.addEventListener('pointerleave', function(){ xh.hidden = true; });
  }
})();
</script>
"""
