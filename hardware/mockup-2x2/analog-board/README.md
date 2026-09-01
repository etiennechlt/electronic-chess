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
contre la géométrie réelle au build), puis applique trois passes
formelles : la passe de garantie retire toute piste ou via qui
passerait sous la garde de fabrication de 0,127 mm (DRC exact shapely)
en réouvrant la liaison concernée ; la passe de finition à géométrie
exacte (`tools/analoggen/finish.py`, sans grille) referme ensuite les
écarts restants par la jonction la plus simple (segment, coudes en L,
coudes en Z balayés, variantes face arrière à un ou deux vias),
chaque jonction restant à 0,132 mm de tout cuivre étranger ; le plan
de masse est enfin calculé sur le cuivre final. La carte générée est
donc toujours DRC zéro, et la liste résiduelle est courte.

## Liste de finition (chevelu affiché dans KiCad)

Le build imprime les jonctions posées et la liste exacte des restes.
À la génération de référence (499 pistes, 259 vias, DRC zéro, 12
jonctions posées par la finition, LED de camp entièrement câblées :
tampon, joint 12 broches, 5V) il reste sept nets à fermer à la main
dans la bande des cellules et le coin buck : M1_A et M2_A (broches 12
et 14 du mux vers les écrêteurs), C2_A, C3_B (ponts courts), BUCK_FB,
BUCK_EN et VREF (raccords de morceaux). Ce sont les couloirs saturés
connus (cuivre routé et verticale arrière M4_B) : des détours
multi-segments qu'un humain trace en un quart d'heure dans pcbnew,
chevelu affiché. Relancer ensuite le DRC KiCad et refaire l'export :
les gerbers du dépôt sont générés depuis la carte telle quelle.

Commande JLCPCB : 2 couches, 1,6 mm, 1 oz, assemblage face top avec
`jlc-bom.csv` et `jlc-cpl.csv` (vérifier les correspondances LCSC dans
leur prévisualisation, et l'orientation des diodes et du régulateur
sur le rendu avant de valider). Ne commander qu'après la finition du
chevelu ci-dessus.
