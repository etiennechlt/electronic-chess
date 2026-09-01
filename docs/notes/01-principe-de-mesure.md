# 01. Principe de mesure : LC passif, ringdown, deux voies

L'idée pivot du projet : chaque pièce porte un résonateur LC passif
(aucune électronique active, aucun contact), et le plateau identifie
la pièce en mesurant la fréquence de résonance à travers la surface.

## Le résonateur dans la pièce

- Bobine commune à toutes les pièces : L = 45 µH, fil émaillé bobiné
  sur gabarit imprimé (gabarits dans `mechanical/`).
- Condensateur par identité : série E12 en C0G/NP0 1 %, de 1,5 à
  12 nF, soit une bande de fréquences d'environ 217 à 613 kHz
  (`resonance.frequency_plan`).
- La paire la plus serrée du plan (3,3 contre 3,9 nF) est séparée de
  2,50 largeurs de raie à Q = 30, au dessus du plancher exigé de 2,4
  (`resonance.check_separation`, épinglé par `tests/test_resonance.py`,
  écart de tolérance réel 7,06 kHz contre 4,0 exigés).
- Le C0G est obligatoire : sa dérive thermique quasi nulle porte toute
  la stabilité de l'identité.

## La mesure côté plateau

1. Une spirale PCB non résonnante (4 couches en série, ~16 µH,
   `inductance.pcb_sense_coil`) est couplée magnétiquement à la bobine
   de la pièce à travers la surface (bois) et le feutre : entrefer
   nominal 5,1 mm, budget dans `gap` et `coupling.ringdown_signal`.
2. Excitation large bande : un front raide (MOSFET) injecte de
   l'énergie à toutes les fréquences d'un coup ; pas de balayage.
3. On écoute le ringdown : la pièce sonne à sa fréquence propre,
   l'amortisseur actif étouffe la sonnerie de la chaîne pendant les
   2 premières microsecondes (blanking), puis la chaîne amplifie
   (gain ~200, borne yaml 200 à 500) et filtre (passe-bande ordre 4,
   200 à 650 kHz).
4. Deux voies d'extraction en parallèle sur chaque ringdown
   (ADR 0007) : voie A, ADC rapide plus FFT avec interpolation
   parabolique ; voie B, comparateur plus capture de période. La
   maquette mesure les deux à chaque coup pour les départager (M9).

## Identification

- Calibration par pièce en usine (et par la commande `c` du firmware
  pour la maquette) : la fréquence réelle de chaque pièce est stockée,
  ce qui absorbe les tolérances de L, l'entrefer et l'environnement.
- Classification au plus proche voisin contre la table calibrée ;
  aucune précision absolue n'est requise, seule la séparation entre
  identités compte.

## D'où viennent les chiffres

Tous les nombres ci-dessus sont calculés par `chessboard_calc` depuis
`config/board.yaml` et épinglés par les tests (`test_resonance`,
`test_inductance`, `test_coupling`). En cas de doute, la source est le
yaml, jamais un document. Le rapport lisible se génère par
`python -m chessboard_calc.report`.

Voir aussi : ADR [0001](../adr/0001-lc-resonators-for-piece-identification.md)
(choix des LC), [0006](../adr/0006-pitch-parametric-open.md) (pas p
ouvert 40 ou 50 mm, tout paramétrique), et la
[note architecture](02-architecture-systeme.md).
