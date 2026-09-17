# 08. Runbook : tout régénérer

Depuis la racine du dépôt. Environnement : Python 3.11 avec le venv du
projet (`python -m venv .venv && .venv/bin/pip install -e .[dev]`),
KiCad 7 ou plus récent avec ses bibliothèques (`kicad-cli` pour les
netlists, `pcbnew` pour le DRC), ngspice, arm-none-eabi-gcc, CadQuery.

## Vérifications de base (avant tout push)

```bash
.venv/bin/ruff check .
.venv/bin/pytest -q          # une centaine de tests, couloir bloquant inclus
```

## DRC KiCad des cartes générées

```bash
/usr/bin/python3 tools/drc.py hardware/quadrant/quadrant.kicad_pcb hardware/brain/brain.kicad_pcb \
    hardware/power/power.kicad_pcb hardware/clock/clock.kicad_pcb hardware/bench/bench.kicad_pcb
```

Avec le Python qui porte le module `pcbnew` de KiCad (celui du système
sur Debian et Ubuntu, KiCad 7 ou plus récent) : charge chaque projet,
remplit les zones, écrit le rapport de KiCad et le résume par type ;
code de sortie non nul tant qu'il reste une erreur ou un élément non
connecté (les nets ouverts). Bilan et lecture des familles de
signalements dans la [note 14](14-revue-des-cartes.md).

## Rapport de calculs

```bash
.venv/bin/python -m chessboard_calc.report
```

## Schémas de la documentation (~2 s)

```bash
PYTHONPATH=tools .venv/bin/python -m docfig build
```

Réécrit les SVG de `docs/images/` que les notes 18 et 19 embarquent
(ringdown, largeur de raie, plan de fréquences, Q selon la fréquence,
coupe, cycle de mesure, chaîne, cerveau, banc) depuis
`config/board.yaml` ; `tests/test_docfig.py` vérifie qu'ils se
construisent et portent les nombres du modèle.

## Carte bobines (~10 s)

```bash
PYTHON=.venv/bin/python sh hardware/mockup-2x2/coil-board/export.sh
```

Régénère `coil-board.kicad_pcb`, son projet `coil-board.kicad_pro`
(le fichier à ouvrir dans KiCad), les gerbers zippés et le rendu
`docs/images/coil-board.png`. Les gardes géométriques (spirales,
terminaux, barillets, bord) lèvent une exception en cas de conflit :
un build silencieusement faux n'existe pas.

## Carte analogique (~5 min, le routage)

```bash
PYTHON=.venv/bin/python sh hardware/mockup-2x2/analog-board/export.sh
```

Lire la sortie du build :

- `finishing pass: N joints` : raccords posés par la passe de
  finition (normal).
- `finish list` : le chevelu restant à fermer dans pcbnew ; la ligne
  `cuivre retire (sous-garde)` signale un tronçon retiré par la passe
  de garantie.
- `drc (0)` : doit toujours être zéro ; un DRC non nul est un bug du
  générateur, pas une carte à corriger à la main.

Sorties : `analog-board.kicad_pro` (le fichier à ouvrir dans KiCad),
`analog-board.kicad_sch`, `.kicad_pcb`, `bom.csv`, `jlc-bom.csv`,
`jlc-cpl.csv`, `chain-spice.cir`, gerbers zippés, rendu
`docs/images/analog-board.png`.

Le projet porte les règles du générateur (classe de nets, minima du
DRC) et, pour la carte analogique, l'uuid de la feuille racine du
schéma : il est réémis à chaque build, donc il ne peut pas dériver de
la carte qu'il accompagne.

## Quadrant 4 x 4 (quelques minutes, routage du frontal compris)

```bash
PYTHONPATH=tools .venv/bin/python -m quadgen build --render docs/images/quadrant.png
```

Régénère `hardware/quadrant/quadrant.kicad_pcb`, le schéma dessiné
(feuille racine `quadrant.kicad_sch` et ses feuilles `rails`,
`cells-1` à `cells-4`, `select`, `chain`, `leds`), son projet
`quadrant.kicad_pro` et le rendu. Le quadrant réduit 2 x 2 de mise au
point ([note 17](17-quadrant-fonction-et-cablage.md)) se régénère par
le même générateur :

```bash
PYTHONPATH=tools .venv/bin/python -m quadgen build --reduced --render docs/images/quadrant-2x2.png
```

vers `hardware/quadrant-2x2/`. Le build échoue (code 1) si une route
de la chaîne LED ou un retour d'alimentation est ouvert, ou si le
contrôle d'isolement exact trouve un défaut ; `tests/test_quadgen.py`
reconstruit la carte et vérifie la source unique des LED, les
échappées vers les cellules et l'export `kicad-cli`.

## Cartes du plateau : cerveau, puissance, moteurs, horloge (~2 à 15 min chacune)

```bash
for b in brain power motion clock; do
  PYTHONPATH=tools .venv/bin/python -m boardgen build $b --render docs/images/$b.png
done
```

Chaque build écrit `hardware/<carte>/<carte>.kicad_pro`, le schéma, le
PCB, `bom.csv`, `jlc-bom.csv` et `jlc-cpl.csv`, puis route tous les
nets avec le routeur A* multicouche et passe le contrôle d'isolement
exact. Les nets restés ouverts sont listés dans la sortie (et dans le
README de chaque carte) : ils se ferment dans pcbnew avant commande.
Le générateur échoue si deux cours d'empreinte se chevauchent ou si une
pièce sort de la carte.

## Plateau 8 x 8 et horloge (ADR 0010)

```bash
.venv/bin/python mechanical/scenes.py        # docs/images/plateau-*.png, horloge*.png (~4 min)
.venv/bin/python mechanical/viewer.py        # mechanical/exports/plateau-3d.html, vue interactive
.venv/bin/python mechanical/build_all.py     # STEP des assemblages, STL et STEP de l'horloge
```

Les cotes viennent de `plateau`, `clock`, `gap` et `power` dans le
yaml, dérivées par `chessboard_calc.plateau` et épinglées par
`tests/test_plateau.py` (sans CadQuery) et `tests/test_mechanical.py`
(avec). La vue interactive charge three.js depuis cdnjs ; elle s'ouvre
dans n'importe quel navigateur.

## Mécanique de la maquette

```bash
.venv/bin/python mechanical/build_all.py            # STL + STEP
.venv/bin/python mechanical/render_stl.py           # vues pour le README
.venv/bin/python -c "import sys; sys.path.insert(0,'mechanical'); import scenes"  # scènes composées
```

Le gabarit de perçage du bois est la pièce `surface-template` dans
`mechanical/exports/`.

## Carte de banc Nucleo (~1 min)

```bash
PYTHONPATH=tools .venv/bin/python -m boardgen build bench --render docs/images/bench.png
```

Régénère `hardware/bench/` (projet KiCad, BOM, placements) depuis la
section `bench` du yaml : embases Arduino sur l'empreinte officielle
`Arduino_UNO_R3`, bus du quadrant sur les broches de `bench.signals`,
routes manuelles de l'éventail FPC et du buck redessinées et vérifiées
à chaque build ; le build échoue si un net reste ouvert ou si une
route manuelle ne passe plus.

## Firmware

```bash
cd firmware/board
make pins       # regénère src/board_pins.h (PYTHONPATH=tools, chaîne LED depuis quadgen)
make            # build/board.elf
make NUCLEO=1   # build/nucleo/board-nucleo.elf, banc Nucleo de la note 19
```

Maquette, pour référence :

```bash
cd firmware/mockup
make pins    # régénère src/board_pins.h depuis config/board.yaml
make         # build/mockup.elf
```

`board_pins.h` est commité : refaire `make pins` après toute édition
de `plateau.brain.mcu_pins`, `plateau.quadrant`, `bench` ou
`mockup.coil_board.leds` dans le yaml ; `tests/test_firmware_pins.py`
échoue tant que l'en-tête commité du cerveau ne correspond pas au yaml
(la maquette n'a pas ce garde-fou).

## Où vivent les artefacts

| Artefact | Chemin |
|---|---|
| Projets KiCad | `hardware/quadrant/quadrant.kicad_pro`, `hardware/mockup-2x2/*/[nom].kicad_pro` |
| Gerbers bobines | `hardware/mockup-2x2/coil-board/coil-board-gerbers.zip` |
| Gerbers analogique | `hardware/mockup-2x2/analog-board/analog-board-gerbers.zip` |
| BOM et placements JLC | `hardware/mockup-2x2/analog-board/jlc-*.csv` |
| STL/STEP, vue 3D interactive | `mechanical/exports/` |
| Images du README | `docs/images/` |

Règle d'or : ne jamais éditer un fichier généré ; modifier
`config/board.yaml` ou le générateur, régénérer, committer les deux.
