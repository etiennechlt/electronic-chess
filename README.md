# Échiquier électronique automatique à détection LC

Échiquier physique qui identifie chaque pièce (type et couleur) par un
résonateur LC passif logé dans sa base, arbitre les coups (roque,
prise en passant, promotion incluse), joue contre un moteur d'échecs
ou en ligne, et fonctionne sur batterie. Plateau fin de 42 cm et
21 mm d'épaisseur ; le déplacement des pièces par aimant sur portique
CoreXY est une base optionnelle qui se substitue au fond plat. Le
STM32G474 est maître, un ESP32-S3 sert de pont radio (WiFi, BLE vers
l'horloge à bascule séparée), le Raspberry Pi Zero 2 W est optionnel.

![Architecture du système](docs/images/architecture.svg)

## Principe de détection

Chaque pièce porte une bobine plate de 45 µH et un condensateur C0G
1 % de la série E12 qui fixe sa classe (12 valeurs, 217 à 613 kHz).
Chaque case excite en large bande par un front raide, écoute le
ringdown à travers l'entrefer, et classifie au plus proche voisin sur
des fréquences calibrées par pièce. L'aimant de pièce est en ferrite
dure, transparent au champ de mesure ; celui du chariot en néodyme.

![Empilement vertical coté](docs/images/stackup-blueprint.svg)

![Plan de fréquences des 12 classes](docs/images/frequency-plan.svg)

## Source de vérité unique

Toute valeur numérique du projet vient de
[`config/board.yaml`](config/board.yaml). Les grandeurs dérivées (les
12 fréquences, diamètres, courses, entrefer, autonomie) sont calculées
par la bibliothèque `chessboard_calc` et épinglées par les tests
contre la spécification. Le pas de case `p` est figé à 50 mm
(ADR 0010) ; tout reste paramétrique et le rapport compare toujours
40 et 50.

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pytest                                        # les garde-fous
.venv/bin/python -m chessboard_calc report --pitch all  # tables dérivées
```

Le test de couloir (`tests/test_corridor.py`) verrouille la contrainte
`r_mobile + r_statique <= p/2` pour les 21 paires de classes : si une
édition du yaml la viole, la CI casse, car la partie se bloquerait dès
e2-e4.

## Plateau 8 x 8 (ADR 0010)

Un module plateau invariant (contreplaqué plus quatre quadrants 4 x 4
identiques, frontal analogique embarqué) posé dans une base fine ou,
plus tard, dans une base chariot avec le CoreXY et les ailes de
capture. Cerveau, carte puissance et cellules plates au fond de la
base, sur la même empreinte dans les deux bases. Horloge à bascule
séparée, en BLE. Choix et raisons dans la
[note 10](docs/notes/10-plateau-8x8-et-horloge.md).

| Plateau fin | Vue éclatée |
|---|---|
| ![Plateau fin](docs/images/plateau-fin.png) | ![Vue éclatée](docs/images/plateau-eclate.png) |

| Base chariot ouverte | Base chariot avec le module plateau |
|---|---|
| ![Base chariot ouverte](docs/images/plateau-chariot-ouvert.png) | ![Base chariot](docs/images/plateau-chariot.png) |

| Horloge à bascule | Horloge éclatée |
|---|---|
| ![Horloge](docs/images/horloge.png) | ![Horloge éclatée](docs/images/horloge-eclatee.png) |

Vue 3D interactive (bases, éclaté, couches, noms au survol) :
`python mechanical/viewer.py` puis ouvrir `mechanical/exports/plateau-3d.html`.

## Maquette 2 x 2 (phase 1, conçue, non construite)

La maquette a été conçue de bout en bout puis remplacée par le plateau
direct (ADR 0010) ; elle reste la référence de la chaîne analogique et
du routage ([guide](hardware/mockup-2x2/README.md),
[fiche d'approvisionnement](docs/bom-maquette.md)).

| Vue d'ensemble | Pièce de test éclatée |
|---|---|
| ![Vue 3D de la maquette](docs/images/mockup-3d.png) | ![Vue éclatée du puck](docs/images/piece-exploded.png) |

- **Carte bobines** (100 x 100, 4 couches, générée par
  [`coilgen`](tools/coilgen/)) : 4 spirales série de 5 tours par
  couche, 8 LED de camp WS2812B chaînées aux coins des cases (deux
  points lumineux par case à travers la surface en bois, ADR 0009),
  gerbers commités, [détails](hardware/mockup-2x2/coil-board/README.md).
- **Carte analogique** (100 x 62, 2 couches, générée par
  [`analoggen`](tools/analoggen/)) : mux différentiel, AD8421,
  filtres Sallen-Key validés ngspice, buck forced-PWM contre LDO en
  cavalier, UART Pi isolée ; routée DRC zéro par le routeur maison,
  une courte liste de liaisons à fermer dans pcbnew avant commande,
  [détails](hardware/mockup-2x2/analog-board/README.md).
- **Firmware** ([`firmware/mockup`](firmware/mockup/)) : les deux
  voies d'extraction du brief mesurées simultanément sur chaque
  ringdown, calibration en flash, CSV sur le port série ; compile en CI.
- **Mécanique** ([`mechanical/`](mechanical/README.md)) : plateau
  8 x 8 (module, bases, ailes), horloge, pucks de test, gabarits de
  bobinage, STL et STEP paramétriques, rendus et vue interactive.

| Carte bobines | Carte analogique |
|---|---|
| ![Carte bobines](docs/images/coil-board.png) | ![Carte analogique](docs/images/analog-board.png) |

## Documentation

La base de connaissances du projet vit dans
[`docs/`](docs/README.md) : entrées par intention, notes de concepts
(mesure, architecture, générateurs, routeur, firmware), état de
référence, runbook de régénération et journal des décisions. Les
décisions formelles sont dans [`docs/adr/`](docs/adr/README.md).

## Arborescence

| Répertoire | Contenu | Phase |
|---|---|---|
| `config/` | `board.yaml`, source de vérité unique | 0 |
| `chessboard_calc/` | calculs paramétriques et garde-fous | 0 |
| `tools/coilgen`, `tools/analoggen` | générateurs KiCad des deux cartes | 1 |
| `hardware/mockup-2x2/` | projets KiCad (`.kicad_pro` à ouvrir), gerbers, BOM, guides | 1 |
| `firmware/mockup/` | firmware Nucleo-G474RE | 1 |
| `measurements/` | protocole, gabarits CSV, analyse | 1 |
| `mechanical/` | modèles CadQuery (plateau, horloge, pucks), rendus, vue 3D | 1 à 3 |
| `hardware/quadrant-4x4/`, `mainboard/`, `firmware/board/`, `app/` | plateau complet | 2 à 4 |

## État et décisions

Phase 0 (socle, calculs, CI) livrée, phase 1 (maquette) conçue puis
remplacée par le plateau 8 x 8 direct (ADR 0010) : yaml, géométrie,
modèles 3D du plateau et de l'horloge faits ; générateur de quadrant,
cerveau et horloge à suivre. Les
décisions d'architecture et leurs justifications sont dans
[`docs/adr/`](docs/adr/README.md) ; conventions dans
[`CLAUDE.md`](CLAUDE.md) : code et commentaires en anglais,
documentation en français, aucune valeur dupliquée hors de
`board.yaml`.
