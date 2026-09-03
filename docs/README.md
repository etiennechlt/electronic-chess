# Documentation du damier électronique

Ce dossier est la base de connaissances du projet : tout ce qu'il faut
pour le comprendre, le régénérer, le commander et le reprendre à
froid. Les nombres font autorité dans `config/board.yaml` et dans les
tests qui les épinglent ; les documents expliquent, ils ne dupliquent
pas.

## Entrées par intention

- **Reprendre le projet à froid** : lire dans l'ordre
  [le principe de mesure](notes/01-principe-de-mesure.md),
  [l'architecture](notes/02-architecture-systeme.md),
  [le plateau 8 x 8 et ses choix](notes/10-plateau-8x8-et-horloge.md),
  [l'état et le reste à faire](notes/07-etat-et-reste-a-faire.md),
  puis le [journal](notes/09-journal.md) pour l'historique des choix.
- **Voir le plateau en 3D** : `python mechanical/viewer.py` génère la
  vue interactive (bases fine et chariot, éclaté, couches), les vues
  fixes sont dans `docs/images/plateau-*.png` et `horloge*.png`,
  méthode dans la [note 10](notes/10-plateau-8x8-et-horloge.md).
- **La maquette 2 x 2** (retirée du plan par l'ADR 0010, conservée
  comme référence de la chaîne analogique) : la
  [fiche d'approvisionnement](bom-maquette.md) et le
  [README de la carte analogique](../hardware/mockup-2x2/analog-board/README.md).
- **Comprendre la mesure** :
  [principe](notes/01-principe-de-mesure.md), ADR
  [0001](adr/0001-lc-resonators-for-piece-identification.md) et
  [0007](adr/0007-frequency-extraction-dual-path.md), puis le
  [protocole M1 à M11](../measurements/protocol.md).
- **Savoir quoi faire ensuite** : la [note 07](notes/07-etat-et-reste-a-faire.md),
  feuille de route en deux phases (sans chariot d'abord, chariot ensuite).
- **Ouvrir, vérifier et tester les cartes** : la
  [note 13](notes/13-revue-et-verification.md) (KiCad, DRC, netlists,
  valeurs, simulation, commande, protocole de test) et le bilan de la
  revue des cartes, [note 14](notes/14-revue-des-cartes.md).
- **Imprimer** : `python mechanical/build_all.py` écrit STL et STEP
  dans `mechanical/exports/` (non versionnés).
- **Modifier une carte** :
  [générateurs KiCad](notes/03-generateurs-kicad.md),
  [routeur et garanties](notes/04-routeur-et-garanties.md),
  [seeds et couloirs](notes/05-seeds-et-couloirs.md), puis le
  [runbook de régénération](notes/08-regenerer.md).
- **Toucher au firmware** : [note firmware](notes/06-firmware.md), le
  [README du firmware du cerveau](../firmware/board/README.md) (quatre
  quadrants) et celui de la [maquette](../firmware/mockup/README.md).
- **Lancer les mesures** : [protocole](../measurements/protocol.md),
  gabarits CSV et notebook dans `measurements/`.
- **Filmer le projet** : la série vidéo « Échec et Watt »
  ([bible](serie/README.md), [épisodes et scripts](serie/episodes.md),
  [tournage](serie/tournage.md), [montage](serie/montage.md)).

## Carte du dépôt

| Chemin | Contenu |
|---|---|
| `config/board.yaml` | source unique de toutes les valeurs |
| `chessboard_calc/` | calculs (fréquences, couloir, bobines, couplage, énergie) et CLI de rapport |
| `tools/coilgen/` | générateur complet de la carte bobines (spirales, LED, joint) |
| `tools/analoggen/` | générateur complet de la carte analogique (schéma, PCB routé, BOM, SPICE) |
| `tools/quadgen/` | générateur du quadrant 4 x 4 : spirales, échappées, LED, frontal complet (schéma, placement, routage) |
| `tools/boardgen/` | générateur générique et les quatre cartes du plateau : cerveau, puissance, moteurs, horloge |
| `hardware/quadrant/`, `hardware/brain/`, `hardware/power/`, `hardware/motion/`, `hardware/clock/` | projets KiCad générés, BOM, placements, README de chaque carte |
| `hardware/mockup-2x2/` | artefacts générés : KiCad, gerbers, BOM JLC, guides |
| `firmware/board/` | firmware du cerveau (STM32G474, quatre quadrants, 128 LED) en CMSIS nu |
| `firmware/esp32/` | pont radio du cerveau et horloge (ESP-IDF, NimBLE), logique d'horloge testée sur PC |
| `firmware/mockup/` | firmware de la maquette Nucleo, référence |
| `mechanical/` | CadQuery : plateau 8 x 8 (module, bases, ailes), horloge, pucks, gabarits ; rendus et vue interactive |
| `measurements/` | protocole M1 à M11, gabarits CSV, analyse |
| `docs/adr/` | décisions d'architecture numérotées |
| `docs/notes/` | la présente base de connaissances |
| `docs/serie/` | série vidéo : bible, épisodes, tournage, montage |
| `tests/` | une centaine de tests, dont le couloir bloquant en CI, l'empilement du plateau, le quadrant et la netlist de chaque schéma |

## Notes

| Note | Sujet |
|---|---|
| [01](notes/01-principe-de-mesure.md) | Principe de mesure : LC, ringdown, deux voies, classification |
| [02](notes/02-architecture-systeme.md) | Architecture système et budget de bruit |
| [03](notes/03-generateurs-kicad.md) | Générer du KiCad valide par script |
| [04](notes/04-routeur-et-garanties.md) | Le routeur maison et ses trois garanties |
| [05](notes/05-seeds-et-couloirs.md) | Seeds structurels et couloirs LED : la méthode |
| [06](notes/06-firmware.md) | Firmware : mesure, calibration, LED |
| [07](notes/07-etat-et-reste-a-faire.md) | État de référence et chemin vers le prototype réel |
| [08](notes/08-regenerer.md) | Runbook : tout régénérer |
| [09](notes/09-journal.md) | Journal des décisions et pivots |
| [10](notes/10-plateau-8x8-et-horloge.md) | Plateau 8 x 8, base interchangeable et horloge : les choix et leurs raisons |
| [11](notes/11-cartes-du-plateau.md) | Les cinq cartes du plateau : méthode, choix, revue avant fabrication |
| [12](notes/12-protocole.md) | Protocole plateau, pont radio, horloge (lignes texte, BLE) |
| [13](notes/13-revue-et-verification.md) | Ouvrir, vérifier, simuler, commander et tester les cartes |
| [14](notes/14-revue-des-cartes.md) | Revue des cartes de la phase 1 : constats, corrections, ce qui reste |

Décisions formelles : [index des ADR](adr/README.md). Conventions de
contribution : `CLAUDE.md` à la racine (langue, typographie, source
unique, méthode).
