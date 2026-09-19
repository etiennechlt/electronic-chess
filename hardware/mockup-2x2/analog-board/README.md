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

## Ouvrir

`analog-board.kicad_pro` est le fichier à ouvrir dans KiCad : il
associe le schéma et la carte, et il porte les règles du routeur.
Classe de nets : garde 0,15 mm, piste 0,4 mm (0,8 mm pour les rails,
0,25 mm pour les entrées dans les pastilles à pas fin), vias
0,6/0,3 mm. Minima du DRC : garde 0,127 mm, la porte exacte que le
générateur vérifie lui même.

Le DRC de KiCad contrôle aussi ce que le générateur ne regarde pas, en
particulier la distance du cuivre au bord de carte, réglée ici à la
valeur de fabrication 0,2 mm. Sur la génération de référence il
signale la broche 2 du jack J1, placée 1 mm en dehors du contour : le
placement de J1 dans `tools/analoggen/pcb.py` est à corriger avant
commande, ce n'est pas un faux positif.

## Génération et fabrication

```bash
.venv/bin/python -m analoggen build --render docs/images/analog-board.png
sh hardware/mockup-2x2/analog-board/export.sh   # gerbers + percage + zip
```

Le générateur route la carte (routeur A* maison sur grille 0,125 mm,
légalité par transformée de distance, routes structurelles vérifiées
contre la géométrie réelle au build), puis quatre passes finissent le
travail sur le cuivre fini, en géométrie exacte :

1. **garantie** : toute piste ou via passant sous la garde de
   fabrication de 0,127 mm est retirée et sa liaison réouverte ;
2. **finition** (`tools/analoggen/finish.py`) : chaque net encore en
   morceaux reçoit le raccord le plus simple qui tienne (segment,
   coude, Z balayé, variantes face arrière à un ou deux vias), tenu à
   0,15 mm de tout cuivre étranger, la garde que le DRC de KiCad
   exige. Quand aucun ne passe, un **labyrinthe**
   (`tools/analoggen/maze.py`) cherche sur une trame de 0,05 mm, deux
   couches, en payant chaque via et chaque coude ; le chemin trouvé
   est revérifié en géométrie exacte avant d'être posé ;
3. **plan de masse** : calculé comme le calcule le remplisseur de
   KiCad, îlot par îlot (garde 0,3 mm, largeur minimale 0,2 mm), et
   non comme une bande idéale ;
4. **finition de la masse** : chaque groupe de pastilles de masse que
   le plan ne rejoint pas reçoit sa descente vers l'îlot qui porte le
   reste. Le cuivre de masse n'est pas étranger à son propre plan,
   donc ces raccords ne le déplacent pas : le plan se calcule une
   fois, après le routage des signaux.

La connexité est enfin vérifiée couche par couche, plan compris
(`tools/analoggen/connect.py`, qui emprunte la comptabilité du
quadrant) : **le compte du build est celui que KiCad affiche**.

## État mesuré au 19/09/2026

Cette carte est la référence de la chaîne analogique, retirée du plan
par l'[ADR 0010](../../../docs/adr/0010-plateau-8x8-base-interchangeable-horloge.md) :
le banc et le quadrant 2 x 2 la remplacent. Mesures de `tools/drc.py`
(zones remplies) sur le fichier commité :

| Contrôle | Résultat |
|---|---|
| Éléments non connectés | **0** (557 pistes, 296 vias) |
| Chevauchements de courtyard | 49 |
| Cuivre trop près du bord | 1 |
| Gardes sous la valeur de la classe de nets | 0 |

KiCad affiche un chevelu plus long à l'ouverture parce que ses zones
ne sont pas encore remplies : remplir les plans (touche B) donne le
compte ci-dessus.

Les deux défauts qui restent ne sont pas des liaisons :

- **49 chevauchements de courtyard**, hérités du placement
  (connecteurs contre trous de fixation, découplages serrés contre
  leur boîtier). Les corriger demande de déplacer des composants, donc
  de retirer la carte au sort du routage ; la carte est retirée du
  plan, le placement n'a pas été repris.
- **la broche 2 du jack J1**, 1 mm en dehors du contour. C'est un
  défaut de placement réel, pas un faux positif : `PLACEMENTS["J1"]`
  dans `tools/analoggen/pcb.py` est à corriger avant toute commande.

## Ce que le routeur ne trouve pas, et ce qui le remplace

Le build imprime les raccords posés et la liste exacte de ce qui
reste. Les liaisons que la grille ne sait pas voir sont dessinées dans
le générateur (`_hand_seeds`), avant le routage, donc le routeur
travaille autour d'elles ; chacune est revérifiée au build contre la
géométrie réelle des pads et contre les autres routes structurelles.

| Liaison | Pourquoi la grille échoue | Ce qui la remplace |
|---|---|---|
| C2_A, la ligne A de la cellule 2 | la descente vers l'écrêteur et la traversée de la rangée de résistances sont prises quand vient son tour | couloir ouest de la cellule (1,55 mm libre) et traversée sous la rangée, face arrière, comme le routeur le fait de lui même sur la cellule 1 |
| C3_B, la ligne B de la cellule 3 | idem, rangée de la cellule 3 | canal de 0,86 mm entre les deux rangées de la cellule |
| M2_A, la prise A de la cellule 2 | le seul passage fait 1,44 mm entre la résistance de polarisation et la diode du rail 5VA | montée verticale à x = 35,54 |
| M1_A et M4_A, deux broches du mux | leur nappe traverse la bande des cellules sur 25 mm : jamais le choix local le moins cher | échappée de 2,2 mm vers la bande libre au nord des cellules, le reste au routeur (le labyrinthe ferme les 25 mm) |
| VREF, la résistance de fuite de la cellule 1 | sa pastille est murée par la ligne B voisine, 0,2 mm de libre | montée droite vers le rail VREF, posée avant |
| BUCK_FB et BUCK_PG, deux broches du buck | le coin du régulateur n'a que deux sorties et le rail 5V les prend | une voie chacune vers l'ouest, puis traversée de l'échappée d'enable par la face arrière |
| GND de U3, de Q11, de J4 et du connecteur de bobines | le plan de masse n'atteint pas ces pastilles une fois les signaux routés | une descente dédiée par pastille, vers une zone que le plan garde entière |

Commande JLCPCB : 2 couches, 1,6 mm, 1 oz, assemblage face top avec
`jlc-bom.csv` et `jlc-cpl.csv` (vérifier les correspondances LCSC dans
leur prévisualisation, et l'orientation des diodes et du régulateur
sur le rendu avant de valider). Corriger d'abord le placement du jack
J1, dont une broche sort du contour.
