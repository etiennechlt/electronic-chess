# 03. Générer du KiCad valide par script

Les deux cartes ne sont pas dessinées dans KiCad : elles sont émises
par des scripts Python (`tools/coilgen`, `tools/analoggen`) depuis
`config/board.yaml`. On ne modifie jamais les fichiers KiCad à la
main, on modifie la source et on régénère
([runbook](08-regenerer.md)).

## Les règles qui rendent ça fiable

1. **Une source, des dérivés.** Toute valeur vient du yaml, les
   grandeurs dérivées de `chessboard_calc`, et les tests épinglent le
   résultat. Un nombre recopié à la main est un bug.
2. **Symboles et empreintes officiels, embarqués verbatim.** Les
   bibliothèques KiCad installées (`/usr/share/kicad/...`) sont la
   source des empreintes et des brochages : `analoggen.fplib` et
   `analoggen.symlib` lisent les fichiers officiels et les copient
   tels quels dans les cartes générées. Raison historique devenue
   discipline : l'environnement de génération n'atteint pas les
   datasheets en ligne, donc chaque brochage utilisé (mux, AD8421,
   ADuM1201, TPS62150, WS2812B, 74AHCT1G125...) a été vérifié sur le
   symbole officiel, jamais supposé. Un composant sans paire
   symbole plus empreinte officielle vérifiable n'entre pas dans le
   design (c'est pour ça que la LED est une WS2812B 5050 et non la
   2020, sans symbole officiel).
3. **kicad-cli est l'oracle.** Chaque carte générée doit passer
   `kicad-cli pcb export svg` et `sch export netlist` (tests
   automatiques). Piège connu : kicad-cli 7 ne re-remplit pas les
   zones, donc le plan de masse est émis pré-rempli en bandes de
   balayage calculées par le générateur.
4. **Sémantique des rotations.** La rotation d'une empreinte s'ajoute
   à l'angle propre de chaque pad, et rot90 étale une rangée le long
   de +x ; `pad_abs_pos` fait foi. Les permutations largeur/hauteur
   des pads tournés ont causé assez d'incidents pour ne plus jamais
   les faire de tête.

## coilgen (carte bobines)

- `geometry.py` : piles de spirales multi-couches avec arcs de liaison
  à 90 degrés entre couches (les jonctions alignées sur le rayon du
  terminal créaient des vias superposés).
- `board.py` : plan des pads du joint (PAD_PLAN), spirales, échappées
  vers le connecteur, sous-système LED
  ([note 05](05-seeds-et-couloirs.md)), gardes géométriques au build.
- `render.py` : rendu matplotlib par couche pour la revue et le
  README.
- Tests : sens de circulation des couches, continuité série, écart
  entre spires, écart cuivre inter-nets échantillonné sur toute la
  carte, comptages du fichier sérialisé, parsing kicad-cli.

## analoggen (carte analogique)

- `circuit.py` : le schéma comme données (138 composants, ~75 nets),
  catalogue de pièces avec MPN et candidats LCSC.
- `filters.py` plus `spice.py` : dimensionnement Sallen-Key en E96 et
  validation ngspice de la chaîne complète (gain ~200 à 400 kHz,
  coupures, réjections), test automatique.
- `schematic.py` : schéma KiCad à étiquettes globales, parsé par
  kicad-cli en test.
- `pcb.py` : placement, routeur maison et ses garanties
  ([note 04](04-routeur-et-garanties.md)).
- `bom.py` : BOM lisible et fichiers JLCPCB (BOM et placements, avec
  le miroir y pour la face).
- Sorties dans `hardware/mockup-2x2/analog-board/`, gerbers zippés
  par `export.sh`.

## Ce que ça achète

Chaque évolution (LED, connecteur 12 broches, changement de pas)
est un diff de source relu et testé, jamais une retouche de fichier
binaire ; et l'alignement inter-cartes (position du joint) est calculé
des deux côtés depuis le même yaml, verrouillé par un test d'égalité
des plans de pads.
