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
  [l'état et le reste à faire](notes/07-etat-et-reste-a-faire.md),
  puis le [journal](notes/09-journal.md) pour l'historique des choix.
- **Commander la maquette** : la
  [fiche d'approvisionnement](bom-maquette.md) (prix comparés Europe
  contre Asie, quatre commandes conseillées), après la finition
  décrite dans l'[état](notes/07-etat-et-reste-a-faire.md) et le
  [README de la carte analogique](../hardware/mockup-2x2/analog-board/README.md).
- **Comprendre la mesure** :
  [principe](notes/01-principe-de-mesure.md), ADR
  [0001](adr/0001-lc-resonators-for-piece-identification.md) et
  [0007](adr/0007-frequency-extraction-dual-path.md), puis le
  [protocole M1 à M11](../measurements/protocol.md).
- **Modifier une carte** :
  [générateurs KiCad](notes/03-generateurs-kicad.md),
  [routeur et garanties](notes/04-routeur-et-garanties.md),
  [seeds et couloirs](notes/05-seeds-et-couloirs.md), puis le
  [runbook de régénération](notes/08-regenerer.md).
- **Toucher au firmware** : [note firmware](notes/06-firmware.md) et
  le [README du firmware](../firmware/mockup/README.md).
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
| `hardware/mockup-2x2/` | artefacts générés : KiCad, gerbers, BOM JLC, guides |
| `firmware/mockup/` | firmware Nucleo G474 en CMSIS nu |
| `mechanical/` | pièces CadQuery : pucks, gabarits, support aimant, gabarit de perçage |
| `measurements/` | protocole M1 à M11, gabarits CSV, analyse |
| `docs/adr/` | décisions d'architecture numérotées |
| `docs/notes/` | la présente base de connaissances |
| `docs/serie/` | série vidéo : bible, épisodes, tournage, montage |
| `tests/` | 66 tests, dont le couloir bloquant en CI |

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

Décisions formelles : [index des ADR](adr/README.md). Conventions de
contribution : `CLAUDE.md` à la racine (langue, typographie, source
unique, méthode).
