# 07. État de référence et chemin vers le prototype réel

Dernière mise à jour : 01/09/2026. Ce qui est vrai ici est vérifiable
en régénérant ([runbook](08-regenerer.md)) ; les chiffres sont ceux
imprimés par les builds de référence commités.

## Ce qui est fait (phase 0 et phase 1 conception)

| Livrable | État |
|---|---|
| Calculs `chessboard_calc`, yaml, ADR 0001 à 0009 | complets, épinglés par les tests |
| Carte bobines (4 couches, spirales + 8 LED de camp) | générée, gardes vertes, gerbers commités |
| Carte analogique (chaîne complète + tampon LED) | générée : 499 pistes, 259 vias, DRC zéro, 12 raccords de finition posés |
| Firmware Nucleo G474 | compile en CI, deux voies, calibration flash, pilote LED |
| Mécanique CadQuery | pucks, gabarits de bobinage, support aimant, gabarit de perçage bois, STL/STEP exportés |
| Protocole de mesure | M1 à M11, gabarits CSV, notebook d'analyse |
| Approvisionnement | fiche comparée Europe/Asie, prix datés, quatre commandes conseillées |
| Qualité | 61 tests verts, couloir bloquant en CI, ruff propre |

## Le seul reste côté dépôt

Sept nets de la carte analogique à fermer à la main dans pcbnew
(couloirs saturés : M1_A, M2_A, C2_A, C3_B, BUCK_FB, BUCK_EN, VREF),
un quart d'heure chevelu affiché, puis relancer le DRC KiCad et
`export.sh`. Détail et justification dans le
[README de la carte](../../hardware/mockup-2x2/analog-board/README.md)
et la [note 04](04-routeur-et-garanties.md).

## Le chemin physique, dans l'ordre

1. **Finition pcbnew** ci-dessus, re-export des gerbers.
2. **Commander** (détail chiffré dans la
   [fiche](../bom-maquette.md)) : JLCPCB (deux cartes, assemblage
   économique des deux, tous les actifs posés), eStore ST ou RS
   (Nucleo), Mouser/Farnell seulement si l'OPA2810 manque chez LCSC,
   Europe divers (aimants supermagnete/Magnetpartner, fil E44,
   alim 12 V). Valider les codes LCSC dans la prévisualisation JLC.
3. **Imprimer** les pièces (`mechanical/exports/`), acheter le
   contreplaqué, le percer avec `surface-template` (visserie plus
   deux points lumineux par case).
4. **Bobiner** les résonateurs de test (gabarits, fil 0,25), souder
   les C0G bas de bande, coller les aimants ferrite dans les pucks.
5. **Câbler** la Nucleo (table Dupont du
   [guide de montage](../../hardware/mockup-2x2/README.md)), flasher,
   vérifier les points de bring-up du
   [README firmware](../../firmware/mockup/README.md).
6. **Dérouler M1 à M11** (protocole) et remplir le tableau de
   synthèse.

## Ce que chaque mesure décide

| Mesure | Décision alimentée |
|---|---|
| M2 (chute de Q avec ferrite) | viabilité du choix ferrite, la mesure décisive du projet |
| M4 à M6 (SNR, séparation, dispersion) | pas p = 40 ou 50 mm |
| M7 (approche du N42) | distance de parking du chariot |
| M8 (buck contre LDO, Pi WiFi) | buck seul ou LDO au plateau final |
| M9 (voies A/B) | voie d'extraction retenue, donc choix du MCU final |
| M10 (bois contre acrylique) | valide la surface bois (attendu : neutre) |
| M11 (bruit LED) | valide le fenêtrage structurel |

## Après la maquette (phases suivantes du brief)

Phase 2 : plateau 8 x 8 de détection (mux étendu, 81 ou 128 LED selon
le rendu retenu, calibration complète). Phase 3 : portique CoreXY et
déplacement. Phase 4 : intégration jeu complet avec le Pi. Rien de
tout cela n'est commencé ; les choix de la maquette (paramétrique sur
p, chaîne LED extensible, deux voies mesurées) sont faits pour ne pas
avoir à revenir en arrière.
