# 08. Runbook : tout régénérer

Depuis la racine du dépôt. Environnement : Python 3.11 avec le venv du
projet (`python -m venv .venv && .venv/bin/pip install -e .[dev]`),
kicad-cli 7, ngspice, arm-none-eabi-gcc, CadQuery.

## Vérifications de base (avant tout push)

```bash
.venv/bin/ruff check .
.venv/bin/pytest -q          # 66 tests, couloir bloquant inclus
```

## Rapport de calculs

```bash
.venv/bin/python -m chessboard_calc.report
```

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

## Mécanique

```bash
.venv/bin/python mechanical/build_all.py            # STL + STEP
.venv/bin/python mechanical/render_stl.py           # vues pour le README
.venv/bin/python -c "import sys; sys.path.insert(0,'mechanical'); import scenes"  # scènes composées
```

Le gabarit de perçage du bois est la pièce `surface-template` dans
`mechanical/exports/`.

## Firmware

```bash
cd firmware/mockup
make pins    # régénère src/board_pins.h depuis config/board.yaml
make         # build/mockup.elf
```

`board_pins.h` est commité : refaire `make pins` après toute édition
de `mockup.nucleo_pins` ou `mockup.coil_board.leds` dans le yaml.

## Où vivent les artefacts

| Artefact | Chemin |
|---|---|
| Projets KiCad | `hardware/mockup-2x2/*/[nom].kicad_pro` |
| Gerbers bobines | `hardware/mockup-2x2/coil-board/coil-board-gerbers.zip` |
| Gerbers analogique | `hardware/mockup-2x2/analog-board/analog-board-gerbers.zip` |
| BOM et placements JLC | `hardware/mockup-2x2/analog-board/jlc-*.csv` |
| STL/STEP | `mechanical/exports/` |
| Images du README | `docs/images/` |

Règle d'or : ne jamais éditer un fichier généré ; modifier
`config/board.yaml` ou le générateur, régénérer, committer les deux.
