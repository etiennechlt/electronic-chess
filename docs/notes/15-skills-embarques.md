# 15. Skills embarqués : lesquels, pour quel lot, comment les tenir à jour

Les skills sont des modes d'emploi et des scripts que l'assistant de
session charge à la demande. Ils sont copiés dans `.claude/skills/`
pour être disponibles dans tout environnement, y compris distant et
éphémère ; provenance, commits et licences dans
[`.claude/skills/VENDORED.md`](../../.claude/skills/VENDORED.md).
Cette note dit ce que chacun sait faire pour ce projet, à quel lot de
la [note 07](07-etat-et-reste-a-faire.md) il sert, et ce qu'il ne
remplace pas.

## Ce qui vient de kicad-happy (v2.2.1)

| Skill | Sert à | Lot |
|---|---|---|
| `kicad` | analyseurs de schéma et de PCB (`analyze_schematic.py`, `analyze_pcb.py --full`, `cross_analysis.py`) : inventaire, découplage, chaînes LED, régulateurs, connectivité par union-find ; parseur s-expression réutilisé par `tests/test_schematics.py` | 1, à chaque régénération |
| `spice` | bancs ngspice automatiques sur les sous-circuits détectés (filtres, diviseurs, gains) ; complète `chain-spice.cir` et le banc de cellule à écrire | 2 |
| `emc` | analyse de risque CEM sur schéma et PCB (plans, découplage, retours, bords de carte) | après la fermeture des nets, avant commande |
| `datasheets` | extraction structurée des fiches PDF (brochages, seuils) pour nourrir les analyseurs | 1 et 2, dès que les PDF sont accessibles |
| `bom`, `lcsc`, `jlcpcb` | codes LCSC, pièces de base ou étendues, règles de fabrication, export BOM et CPL | 1 (codes LCSC) et 3 |
| `digikey`, `mouser`, `element14`, `pcbway` | approvisionnement de rechange, fiches techniques, fabricant de rechange | 3, si LCSC manque |

Ces analyseurs ne remplacent ni le DRC de KiCad (`tools/drc.py`,
[note 08](08-regenerer.md)) ni la comparaison netlist contre circuit :
la revue du lot 1 ([note 14](14-revue-des-cartes.md)) a trouvé les
erreurs de brochage en lisant les netlists, pas dans leurs constats.

## Ce qui vient de pcba-design-skills (commit d41e999)

Trois skills sur huit, choisis pour le lot 3 ; ce sont des procédés
écrits avec portes de validation (`PASS`, `BLOCKED`, `USER_REVIEW`)
et des artefacts dans `.pcba-workflow/`, presque sans code.

| Skill | Sert à | Lot |
|---|---|---|
| `pcb-layout-review` | liste de contrôle du routage : références de masse, distribution, découplage, éventails de connecteurs, dégagements RF, DRC classé ; à dérouler après la fermeture des nets dans pcbnew | fin du lot 1 |
| `release-pcba-fabrication` | version figée de fabrication : gerbers, perçages, BOM, CPL, rendus, empreintes de hachage et manifeste, pour ne jamais mélanger deux révisions | 3 |
| `operate-jlcpcb-order` | parcours de devis et de commande JLCPCB : téléversement, options, appariement des composants, contrôle de l'aperçu de placement, panier, avec validation humaine avant tout paiement | 3 |

Écartés, et pourquoi : `manage-pcba-program` et
`plan-electronic-product` (gestion de programme et brief produit, la
note 07 tient ce rôle), `qualify-pcba-sourcing` (doublon de `bom`),
`schematic-humanizer` (il réorganise des schémas à étiquettes pour les
rendre lisibles ; les nôtres sont générés, c'est l'émetteur
`analoggen/schematic.py` qu'il faudrait changer, pas les fichiers).

## Ce qui vient de cad-skill

`parametric-3d-printing` : conception CadQuery orientée impression
(tolérances, épaisseurs, clips), pour les pièces de `mechanical/`.
Licence PolyForm Noncommercial, voir `VENDORED.md`.

## Limites à connaître

- Les skills d'approvisionnement et de fiches techniques ont besoin du
  réseau (API DigiKey, Mouser, element14 avec clés ; LCSC sans clé). Un
  environnement fermé les rend muets : la revue du lot 1 a dû marquer
  « à confirmer » les points de fiche non vérifiables.
- Le DRC de KiCad passe par le module `pcbnew` du Python système
  (`/usr/bin/python3 tools/drc.py ...`), pas par un skill.
- Les skills sont exclus de `ruff` (`pyproject.toml`) : conventions
  amont, ne pas les modifier sur place.

## Mettre à jour

1. Cloner l'amont, se placer sur le tag ou le commit voulu.
2. Recopier les répertoires concernés dans `.claude/skills/` (pour
   pcba-design-skills ils sont sous `.agents/skills/` en amont), sans
   `__pycache__`.
3. Vérifier la licence (`LICENSE-kicad-happy`, `LICENSE-pcba-design-skills`,
   `parametric-3d-printing/LICENSE`) et mettre à jour le tableau de
   `VENDORED.md` (version, commit).
4. Lancer un analyseur sur une carte (`analyze_pcb.py --full
   hardware/clock/clock.kicad_pcb`) puis `ruff check .` et `pytest`.
