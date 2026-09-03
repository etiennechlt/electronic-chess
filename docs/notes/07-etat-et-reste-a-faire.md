# 07. État de référence et chemin vers le prototype réel

Dernière mise à jour : 02/09/2026. Ce qui est vrai ici est vérifiable
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
| Qualité | 66 tests verts, couloir bloquant en CI, ruff propre |

## Pivot du 02/09/2026 (ADR 0010) et état au 03/09/2026

La maquette 2 x 2 n'est plus construite : le plateau 8 x 8 est conçu
directement en quadrants 4 x 4, avec un module plateau invariant et
deux bases interchangeables (fine, ou chariot en option), des cellules
plates, un cerveau à MCU soudé, un emplacement ESP32-S3 et Pi, et une
horloge à bascule séparée en BLE.

Fait : yaml (sections `plateau` et `clock`, `gap.air_mm`, batterie
plate, p = 50 figé), géométrie dérivée et tests, modèles CadQuery du
plateau et de l'horloge avec STL et STEP versionnés dans
`mechanical/exports/`, rendus et vue 3D interactive, ADR 0010 et
[note 10](10-plateau-8x8-et-horloge.md) ; quadrant complet (spirales,
échappées, LED, distribution, FPC, frontal placé et routé) ; cerveau,
puissance, moteurs et horloge générés par `tools/boardgen`
([note 11](11-cartes-du-plateau.md)) ; firmware du cerveau compilé,
pont radio et horloge écrits contre ESP-IDF, protocole fixé
([note 12](12-protocole.md)) ; guide d'ouverture, de vérification et
de test ([note 13](13-revue-et-verification.md)).

## Décision de phasage

**Phase 1 : tout doit fonctionner sans chariot.** Base fine, module
plateau, cerveau, puissance, horloge, firmware et application. Le
chariot (base chariot, carte moteurs, ailes de capture, actionneur
d'aimant, arbitre de déplacement) est la **phase 2** et ne commence
qu'une fois la phase 1 jouable de bout en bout. Ce qui est déjà conçu
pour le chariot (carte moteurs, base chariot, nappe vers le cerveau,
interlock) est conservé tel quel et n'est ni commandé ni testé avant.

## Phase 1, dans l'ordre

Chaque lot a un critère de sortie ; on ne passe au suivant qu'une
fois le critère tenu.

1. **Revue des cartes** ([note 13](13-revue-et-verification.md)).
   DRC de KiCad 9 sur quadrant, cerveau, puissance, horloge ; nets
   ouverts fermés dans pcbnew (8, 25, 10, 6) ; brochages « à vérifier »
   validés sur les fiches (STM32G474, BQ24610, BQ76920, FPC, USB-C) ;
   vias 0,45 mm confirmés chez le fabricant ou remplacés. Sortie :
   quatre projets à zéro erreur DRC, zéro net ouvert.
2. **Simulation.** Chaîne d'amplification (`chain-spice.cir`) et un
   banc SPICE de la cellule d'excitation et d'amortissement à écrire
   (bobine 16 µH, écrêteurs, AO3400A, roue libre). Sortie : gain plat
   200 à 650 kHz, impulsion et amortissement conformes à la note 01.
3. **Commande.** Codes LCSC complétés, gerbers exportés, quatre
   quadrants, un cerveau, une carte puissance, une horloge ; pièces
   imprimées depuis `mechanical/exports/` ; contreplaqué percé avec
   `surface-template` ; cellules plates, aimants, fil. Pas de carte
   moteurs. Sortie : matériel reçu et inventorié.
4. **Bring-up électrique** (note 13, section 5) : quadrant hors
   tension, cerveau seul, quadrant sur cerveau avec la console, LED,
   puissance sous alimentation limitée puis sur cellules. Sortie :
   un quadrant scanne ses 16 cases, les 128 LED s'allument, le pack
   charge et protège.
5. **Mesures M1 à M11** ([protocole](../../measurements/protocol.md))
   sur un quadrant plus le cerveau, calibration des 12 classes en
   flash, tableau de synthèse rempli. Sortie : chaque pièce identifiée
   sur chaque case avec la marge de séparation attendue.
6. **Firmware du cerveau** : arbitre (coups légaux, roque, promotion,
   prise en passant), messages de partie `B`, `M`, `F`, `S` de la note
   12, I2C vers la carte puissance (INA219, BQ76920), buzzer, LED
   d'état, bouton, extinction propre. Sortie : une partie humain contre
   humain jouée sur le plateau seul, coups validés et illégaux signalés.
7. **Pont radio et horloge** : première compilation ESP-IDF, appairage
   BLE, cadence et pressions synchronisées, puis WiFi et client
   Lichess Board sur le pont. Sortie : partie en cadence avec l'horloge,
   partie en ligne contre un adversaire distant.
8. **Assemblage final** de la base fine et du module plateau, feutre,
   finition du bois, et la série vidéo qui va avec.

## Phase 2 : chariot

Commander et tester la carte moteurs, imprimer la base chariot et les
ailes, monter le CoreXY et l'actionneur d'aimant, valider M7 (approche
du N42) et l'interlock scan / aimant, écrire le déplacement (A* dans
les interstices, parking hors zone) et la partie contre le moteur
avec pièces déplacées par le plateau. Tout ce qui précède reste
valable : le module plateau et le cerveau ne changent pas, seule la
base est remplacée et la carte moteurs branchée sur la nappe prévue.

## Ce que chaque mesure décide

| Mesure | Décision alimentée |
|---|---|
| M2 (chute de Q avec ferrite) | viabilité du choix ferrite, la mesure décisive du projet |
| M4 à M6 (SNR, séparation, dispersion) | marges de calibration au pas p = 50 |
| M7 (approche du N42) | distance de parking du chariot (phase 2) |
| M8 (buck contre LDO, radio) | buck seul ou LDO renforcé sur le cerveau |
| M9 (voies A/B) | voie d'extraction retenue |
| M10 (bois contre acrylique) | valide la surface contreplaqué (attendu : neutre) |
| M11 (bruit LED) | valide le fenêtrage structurel |

## La maquette 2 x 2 (référence, non construite)

Ses fichiers restent dans `hardware/mockup-2x2/` et `firmware/mockup/`
comme référence de la chaîne analogique et de la double voie
d'extraction. Ses points ouverts (sept nets à fermer sur la carte
analogique, jack J1 à décaler) ne sont plus à traiter.
