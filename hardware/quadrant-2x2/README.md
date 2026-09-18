# Quadrant réduit 2 x 2 : banc de mise au point du quadrant

![Quadrant 2 x 2](../../docs/images/quadrant-2x2.png)

Carte générée par `tools/quadgen` avec l'option `--reduced`, depuis
`config/board.yaml` (`plateau.quadrant.reduced`) : le même circuit, le
même bus de commande et le même firmware que le quadrant 4 x 4
([README](../quadrant/README.md)), avec quatre cases au lieu de seize.
Elle sert à valider le schéma, le frontal et la mesure sur une carte
courte et bon marché avant de commander les quadrants du plateau. La
fonction, les composants et leur câblage sont décrits bloc par bloc
dans la [note 17](../../docs/notes/17-quadrant-fonction-et-cablage.md).

## Ce que contient la carte

- 120 x 108 mm, 4 couches : 20 mm de bande de frontal à l'ouest
  (`plateau.quadrant.front_end_strip_mm`), deux colonnes de cases de
  50 mm, et un dépassement de 8 mm au sud (`reduced.strip_overhang_mm`)
  parce que la bande de frontal, avec une seule bande d'échappée et ses
  quatre cellules, est plus longue que deux cases.
- 4 spirales de détection identiques à celles du 4 x 4 (4 couches en
  série, 5 tours par couche, piste 1,6 mm), bornes au sud de la rangée
  0 et au nord de la rangée 1, échappées dans la bande qui les sépare
  vers les cellules du frontal, borne A sur F.Cu et borne B sur B.Cu.
- 8 WS2812B aux coins NO et SE de chaque case, un 100 nF chacune,
  chaîne de données en serpentin sur In1, grille 5 V sur In2, masse
  sur B.Cu le long des bords nord et sud (pas de couloir médian : dans
  un 2 x 2 le seul couloir est la bande d'échappée).
- Connecteur FPC 16 broches 0,5 mm (Hirose FH12), brochage dans
  `plateau.quadrant.link.pinout`, identique au 4 x 4 : le cerveau ne
  voit pas la différence, `COILS_PER_QUADRANT` vaut 4 dans son firmware
  de test.
- Trou de pion de centrage en bas de la bande, deux trous de fixation
  M3 au bord est.

## Le frontal de la bande

Le même que sur le 4 x 4, avec les deux points de la note 17 intégrés :

- 4 cellules de 7,4 mm en face de leur bobine : polarisation 10 k vers
  VREF, 330 ohms et BAV99W (SOT-323) devant le mux, diode de bus B5819W
  et AO3400A d'excitation, SS34FL de roue libre vers VIN, **B5819W de
  roue libre depuis la masse** (le courant de la bobine se referme par
  elle quand le N-FET s'ouvre, quel que soit l'état du commutateur de
  rail), AO3401A et 680 ohms d'amortissement pilotés directement par
  le décodeur (plus de rappel vers VIN). Résistances de polarisation et
  d'écrêtage en 0603, amortissement en 0805, rappel de grille en 0402.
- Décodeurs 74HC4514 (excitation, inhibé par PULSE_EN à travers un
  74LVC1G04) et 74HC154 (amortissement, validé par DAMP_EN_N), sorties
  4 à 15 laissées libres ; un seul ADG1607 (bobines 1 à 4, enable
  MUX_EN_L) ; AD8421 G = 20, deux Sallen-Key OPA2810, tampon VREF et
  étage de sortie, écrêtage vers 3V3 et RC de sortie.
- Commutateur de rail d'impulsion AO3401A commandé par un AO3400A,
  **R7 de 470 ohms** pour que le rail se coupe en moins d'une
  microseconde après PULSE_EN, avant la fenêtre d'écoute ; 10 ohms
  2010 vers le bus des cellules.

## Le schéma

![Cellule de bobine, feuille cells-1](../../docs/images/quadrant-2x2-cellule.png)

![Chaîne d'amplification, feuille chain](../../docs/images/quadrant-2x2-chaine.png)

`quadrant-2x2.kicad_sch` est la feuille racine (connecteur J1 et les
blocs) ; les feuilles `rails`, `cells-1`, `select`, `chain` et `leds`
dessinent chaque bloc avec ses fils, une étiquette globale pour les
rails, le bus d'adresse et les nets partagés entre feuilles, une
étiquette locale pour les nets internes. Le dessin est vérifié contre
le circuit à chaque build et la netlist relue par `kicad-cli` est
comparée au circuit en test (`tests/test_drawn_schematic.py`).

Sorties du build : projet KiCad avec ses six feuilles, `bom.csv`,
`jlc-bom.csv` (lignes avec code LCSC), `jlc-cpl.csv`, `chain-spice.cir`.

## Régénérer

```bash
PYTHONPATH=tools .venv/bin/python -m quadgen build --reduced --render docs/images/quadrant-2x2.png
```

## Résultat du build

Généré par `python -m quadgen build --reduced` :

| Bobines | LED | Segments | Vias | Routes LED et alimentation ouvertes | Nets du frontal ouverts | Défauts d'isolement |
|---|---|---|---|---|---|---|
| 4 | 8 | 8330 | 230 | 0 | 2 | 0 |

Le générateur ne compte que deux nets ouverts, INA_INM (une pastille)
et GND (trois pastilles : D142, R145, C24). Ce compte est faux par
défaut : sa comptabilité de connexité a les trois défauts corrigés
dans le cœur de `boardgen` pour le banc ([note 04](../../docs/notes/04-routeur-et-garanties.md)),
tout le cuivre déjà tracé d'un net compté comme une seule pièce, les
pastilles prises pour des rectangles, et une pastille marquée atteinte
quand la route s'arrête ailleurs.

DRC KiCad 7 (`tools/drc.py`, zones remplies) : 465 signalements, dont
117 éléments non connectés sur 36 nets, en trois familles :

- les tronçons d'échappée des boîtiers fins (U3, les décodeurs) et du
  connecteur FPC, tracés avec leur via puis jamais rejoints : une
  trentaine de lignes 3V3, MUX_A0 à A2, MUX_EN_H et L, DAMP_EN_N,
  AMP_OUT, MUXA_OUT, VIN, 5VA, GND ;
- les pastilles des quatre cellules que le routeur a crues atteintes :
  masse (D1x1, D1x2, R1x5, Q1x1, D1x5), 5VA (D1x1, D1x2), VREF (R1x1,
  R1x2), VIN (D1x4), DRIVE_BUS (D1x3), entrées du mux M1 à M4 (D pad 3
  vers R pad 2, puis vers U3), grilles DRIVE1 à 4 et DAMP1_N à 4_N :
  une soixantaine ;
- une vingtaine de pastilles de la chaîne d'amplification et de ses
  filtres (R8, R10, Q2, C20, C21, R15, R17, R18, R21, R22, D3, R5, R12,
  R13, C14, C16, C4, C6, C2, C22, C23, U5, U7, U8, TP4).

Jusqu'au 18/09/2026 le rapport de KiCad nommait des éléments faux
(pastilles d'autres composants) : les empreintes de bibliothèque
copiées telles quelles partageaient leurs identifiants entre
instances, ce que `place_footprint` corrige depuis le banc ; la carte
a été régénérée avec ce correctif (même cuivre, identifiants uniques)
et le rapport nomme désormais les bons éléments. Erreurs restantes :
aucune ;
avertissements sans effet sur la fabrication : silk_overlap 185,
lib_footprint_issues 129, silk_over_copper 78, via_dangling 41,
track_dangling 27, silk_edge_clearance 5. Le contrôle d'isolement
exact du générateur ne signale aucun défaut. Les vias d'éventail des
boîtiers fins font 0,45 mm (perçage 0,2 mm), dans les capacités
standard de JLCPCB, à confirmer sur le devis. La sérigraphie porte
encore le titre du 4 x 4.

Rien ne se commande avant zéro élément non connecté : la méthode est
celle du banc, porter la comptabilité de connexité du cœur dans
`strip_routing`, rerouter, dessiner à la main ce que le routeur ne
ferme pas (le connecteur FPC d'abord), vérifier au DRC.
