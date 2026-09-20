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
- **Commander les cartes chez JLCPCB** : la
  [note 23](notes/23-commande-jlcpcb.md) dit ce qui part et ce qui ne
  part pas, les fichiers et leur empreinte, les options écran par
  écran, la décision du cuivre interne, et ce qu'il manque pour passer
  un ordre d'assemblage plutôt que des cartes nues.
- **Ne pas refaire les erreurs déjà faites** : la
  [note 22](notes/22-erreurs-de-conception.md) reprend chaque erreur
  commise sur les cartes, ce qui l'a révélée, sa cause, sa correction
  et le contrôle automatique qui la rattrape désormais. À lire avant
  de toucher à un générateur ou de commander.
- **Baisser le coût des cartes** : la [note 16](notes/16-cout-des-cartes.md),
  état de la réflexion sur le quadrant et le format 100 x 100, avec
  les décisions à prendre avant tout devis.
- **Ouvrir, vérifier et tester les cartes** : la
  [note 13](notes/13-revue-et-verification.md) (KiCad, DRC, netlists,
  valeurs, simulation, commande, protocole de test) et le bilan de la
  revue des cartes, [note 14](notes/14-revue-des-cartes.md). L'état
  mesuré carte par carte, routage fermé ou non, est dans la
  [note 23](notes/23-commande-jlcpcb.md).
- **Savoir ce que le routage vaut devant les règles du métier** : la
  [note 21](notes/21-routage-et-regles-de-l-art.md) confronte les cartes
  générées aux règles de placement et de routage de la profession, avec
  la mesure de chacune par `tools/routing_audit.py` : ce qui est
  conforme, les écarts assumés (pas de plan continu sur In1 puisque la
  carte est le capteur, règle 2W dans une bande de 20 mm) et les deux
  points à corriger avant la commande.
- **Utiliser les skills embarqués** (analyseurs KiCad, SPICE, CEM,
  approvisionnement, mise en fabrication, commande JLCPCB, CadQuery) :
  la [note 15](notes/15-skills-embarques.md) dit lequel sert à quel
  lot et comment les mettre à jour.
- **Imprimer** : `python mechanical/build_all.py` écrit STL et STEP
  dans `mechanical/exports/` (non versionnés).
- **Comprendre le quadrant avant de le redessiner** : la
  [note 17](notes/17-quadrant-fonction-et-cablage.md), fonction, cycle
  de mesure, composants et câblage bloc par bloc.
- **Expliquer le projet à un non-spécialiste** : la
  [note 18](notes/18-facteur-q.md) (le facteur Q, avec les chiffres du
  projet), la [note 19](notes/19-cerveau-et-banc-nucleo.md) (le
  cerveau, le banc Nucleo, théorie contre réalité) et la
  [note 20](notes/20-tuto-banc.md) (le tuto du banc : quoi commander,
  comment assembler, comment tester) ; leurs schémas sont générés par
  `python -m docfig build`.
- **Envoyer ces explications à quelqu'un** : les mêmes trois textes
  existent en pages autonomes dans [`docs/pages/`](pages/), une par
  note, schémas embarqués et lisibles hors du dépôt :
  [le facteur Q](pages/facteur-q.html),
  [le cerveau et le banc](pages/cerveau-banc.html),
  [monter le banc](pages/tuto-banc.html). Elles sont générées par
  `python -m docfig pages`, des mêmes fonctions et du même yaml que les
  notes, donc jamais désynchronisées d'elles.
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
| `tools/docfig/` | schémas explicatifs de `docs/images/` (notes 18 et 19), dessinés depuis le yaml |
| `hardware/quadrant/`, `hardware/brain/`, `hardware/power/`, `hardware/motion/`, `hardware/clock/` | projets KiCad générés, BOM, placements, README de chaque carte |
| `hardware/quadrant-2x2/` | quadrant réduit 2 x 2 de mise au point, même circuit et même bus, schéma dessiné par feuilles |
| `hardware/bench/` | carte de banc, shield Nucleo-64 qui alimente et relie le quadrant 2 x 2 (note 19) |
| `hardware/mockup-2x2/` | artefacts générés : KiCad, gerbers, BOM JLC, guides |
| `firmware/board/` | firmware du cerveau (STM32G474, quatre quadrants, 128 LED) en CMSIS nu |
| `firmware/esp32/` | pont radio du cerveau et horloge (ESP-IDF, NimBLE), logique d'horloge testée sur PC |
| `firmware/mockup/` | firmware de la maquette Nucleo, référence |
| `mechanical/` | CadQuery : plateau 8 x 8 (module, bases, ailes), horloge, pucks, gabarits ; rendus et vue interactive |
| `measurements/` | protocole M1 à M11, gabarits CSV, analyse |
| `docs/adr/` | décisions d'architecture numérotées |
| `docs/notes/` | la présente base de connaissances |
| `docs/serie/` | série vidéo : bible, épisodes, tournage, montage |
| `.claude/skills/` | skills tiers embarqués (kicad-happy, pcba-design-skills, cad-skill), provenance dans `VENDORED.md` |
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
| [15](notes/15-skills-embarques.md) | Skills embarqués : lesquels, pour quel lot, comment les tenir à jour |
| [16](notes/16-cout-des-cartes.md) | Coût des cartes : quadrant, format 100 x 100, décisions à prendre avant de chiffrer |
| [17](notes/17-quadrant-fonction-et-cablage.md) | Quadrant : la fonction, les composants et leur câblage, base du schéma redessiné |
| [18](notes/18-facteur-q.md) | Le facteur Q, expliqué sans électronique |
| [19](notes/19-cerveau-et-banc-nucleo.md) | Le cerveau et le banc Nucleo, expliqués ; théorie contre réalité |
| [20](notes/20-tuto-banc.md) | Tuto du banc : quoi commander, quels composants, comment assembler et tester |
| [21](notes/21-routage-et-regles-de-l-art.md) | Le routage devant les règles du métier : conforme, écarts assumés, corrections |
| [22](notes/22-erreurs-de-conception.md) | Erreurs de conception des cartes, et le contrôle qui empêche chacune de revenir |
| [23](notes/23-commande-jlcpcb.md) | Commander chez JLCPCB : ce qui part, les options, ce qui manque pour l'assemblage |

Décisions formelles : [index des ADR](adr/README.md). Conventions de
contribution : `CLAUDE.md` à la racine (langue, typographie, source
unique, méthode).
