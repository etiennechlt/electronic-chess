# Carte analogique de la maquette 2 x 2

Carte 100 x 62 mm, 2 couches, générée intégralement par
`python -m analoggen build` depuis `config/board.yaml` et la
description de circuit `tools/analoggen/circuit.py`. Ne pas éditer les
fichiers KiCad à la main : modifier la source et regénérer.

## Contenu (ADR 0008)

- Entrée 12 V (jack, antiretour SS34, TVS), buck TPS62150 2,5 MHz avec
  cavalier JP3 (PFM ou forced PWM) et LDO LP2985 ; JP1 choisit la
  source du rail analogique 5VA (mesure 8).
- 4 cellules bobine : polarisation 1,65 V, protections 330R + BAV99
  devant le mux, excitation par FET dédié depuis un rail commuté
  (diode de bus B5819W, écrêteur SS34), amortisseur P-FET + 680R
  (0R possible pour l'expérience court-circuit franc).
- Mux différentiel 74HCT4052 (seuils TTL pour le MCU 3,3 V), AD8421
  G = 20, deux étages Sallen-Key Butterworth (200 kHz PH, 650 kHz PB),
  étage de sortie x4,57, RC et écrêtage vers l'ADC. Gain total ~200 à
  400 kHz, validé ngspice (`chain-spice.cir`).
- UART Pi isolée (ADuM1201, R66/R67 en pont si non peuplé), connecteur
  d'alimentation Pi J5 sur le 5 V du buck.
- J2 : connecteur femelle coudé vers la carte bobines (broche 1 à
  x = 38,57 mm, aligné avec elle) ; J4 : 2 x 10 vers la Nucleo ;
  6 points de test.

## Génération et fabrication

```bash
.venv/bin/python -m analoggen build --render docs/images/analog-board.png
sh hardware/mockup-2x2/analog-board/export.sh   # gerbers + percage + zip
```

Le générateur route la carte (routeur A* maison sur grille 0,125 mm,
légalité par transformée de distance, seeds structurels vérifiés
contre la géométrie réelle au build), calcule le plan de masse en
bandes (kicad-cli 7 ne re-remplit pas les zones), puis applique deux
garanties formelles : un DRC géométrique exact (shapely) au seuil de
fabrication 0,127 mm, et une passe finale qui retire toute piste ou
via qui passerait sous cette garde en réouvrant la liaison concernée.
La carte générée est donc toujours DRC zéro ; en contrepartie une
courte liste de liaisons reste à fermer à la main.

## Liste de finition (chevelu affiché dans KiCad)

Le build imprime la liste exacte (« finish list »). À la génération de
référence (464 pistes, 242 vias, DRC zéro) : quatre liaisons jamais
routées (BUCK_PG vers R2.1, M1_A vers U3.12, C3_B vers R44.1, C2_A
vers R31.1) et des équipotentielles en plusieurs morceaux à
raccorder (VIN, SW, BUCK_PG, BUCK_FB, 5VA, VREF, M1_A, C2_A, C3_B,
PI_3V3), dont quatre proviennent de la passe de garantie qui a retiré
un tronçon sous-garde (5VA, SW, VREF, VIN). Toutes sont des sauts
locaux de quelques millimètres : ouvrir le `.kicad_pcb` dans pcbnew,
activer l'affichage du chevelu et les fermer à la main (environ 30
minutes), puis relancer le DRC KiCad avant export. Les gerbers du
dépôt sont générés depuis la carte telle quelle : refaire l'export
après la finition.

Note de méthode : les liaisons restantes sont celles dont tout seed
structurel déplace plus de nets qu'il n'en ferme (saturation locale du
routage) ; les seeds conservés (BUCK_SS, BUCK_DEF, PI_3V3, contrôles
mux, rails) ont chacun été répétés hors build contre la géométrie
réelle avec une marge d'au moins 0,225 mm, et la garde du build les
revalide à chaque génération.

Commande JLCPCB : 2 couches, 1,6 mm, 1 oz, assemblage face top avec
`jlc-bom.csv` et `jlc-cpl.csv` (vérifier les correspondances LCSC dans
leur prévisualisation, et l'orientation des diodes et du régulateur
sur le rendu avant de valider). Ne commander qu'après la finition du
chevelu ci-dessus.
