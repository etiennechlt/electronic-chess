# 11. Les cartes du plateau : quadrant, cerveau, puissance, moteurs, horloge

Cette note décrit les cinq cartes générées pour le plateau 8 x 8
(ADR 0010), les choix pris en les dessinant et ce qui reste à faire
avant fabrication. Les projets KiCad, BOM et placements sont dans
`hardware/<carte>/`, chacun avec son README ; les générateurs sont
`tools/quadgen` (quadrant) et `tools/boardgen` (les quatre autres).

## Méthode commune

- **Une seule source** : le circuit est décrit en Python contre les
  symboles KiCad officiels (le constructeur refuse toute broche
  inconnue ou oubliée, et depuis cette note un doublon de référence).
  Les gros boîtiers sont câblés par nom de broche
  (`boardgen.core.pins_by_name`), pas par numéro.
- **Placement** : blocs fixés à la main pour les connecteurs et les
  circuits intégrés, passifs empilés par un rangement en étagères à
  partir des cours (courtyards) réels des empreintes ; deux cours qui
  se chevauchent ou une pièce qui sort de la carte font échouer le
  build. Les cartes sont volontairement larges : on a laissé de la
  place plutôt que d'optimiser la surface.
- **Routage** : routeur A* multicouche sur grille de 0,1 mm
  (`quadgen.router.MultiRouter`), coût majoré sur les couches externes
  pour pousser les longs signaux à l'intérieur, alimentations d'abord
  sur une grille gonflée pour la piste large, signaux ensuite, masse
  par descente individuelle vers le plan de masse. Ce que le routeur ne
  ferme pas est listé et se termine dans pcbnew, comme sur la carte
  analogique de la maquette.
- **Sorties des boîtiers fins** (`quadgen.escape`) : un routeur sur
  grille ne sort pas d'une broche au pas de 0,5 mm (toutes les cellules
  autour sont dans l'isolement des broches voisines), et tout net routé
  devant la rangée la mure. Chaque broche d'un boîtier au pas inférieur
  à 0,8 mm reçoit donc avant routage un éventail classique : un tronçon
  de 0,2 mm dans l'axe de la broche, puis un via de sortie de 0,45 mm
  (perçage 0,2 mm, capacité standard de JLCPCB à confirmer à la
  commande) sur deux rangées alternées à 1,0 et 1,8 mm du bout de la
  broche, pour que deux vias voisins soient à deux pas et qu'une piste
  passe entre. Le routeur part du via, sur la couche interne : les
  cellules du tronçon, du via et d'un couloir de 2 mm au-delà sur la
  couche de sortie appartiennent au net et lui sont rendues après chaque
  net routé (la grille, prudente, les croyait perdues au passage d'une
  piste voisine à 0,5 mm alors que l'écart réel est légal). Un éventail
  qui toucherait du cuivre d'un autre net est raccourci puis supprimé.
  Les nets qui partent d'un boîtier fin sont routés en premier, les
  alimentations ensuite, le reste après. Les passifs sont rangés à
  1,2 mm les uns des autres pour qu'un via et son isolement passent
  entre deux voisins.
- **Recherche** : A* pondéré (heuristique fois 1,3, chemins un peu plus
  longs mais recherche bien plus courte), coût prohibitif sur la couche
  de masse pour que les signaux la traversent sans y circuler.
- **Diagnostic** : pour chaque net laissé ouvert le build indique
  combien de cellules de départ et d'arrivée étaient utilisables, ce
  qui distingue une broche murée d'un chemin introuvable.
- **Contrôle** : isolement exact (shapely) sur tout le cuivre à chaque
  build, `kicad-cli` exporte le schéma en netlist dans les tests et la
  compare au circuit ; le DRC de KiCad se lance par `tools/drc.py`
  (module `pcbnew`) ou à l'ouverture, les règles du projet étant celles
  du build (vias d'éventail comprises).
- **Hygiène de signal** : plan de masse continu sur chaque carte ;
  sur le quadrant, lignes de mesure (après les écrêteurs, avant les
  mux) sur B.Cu et lignes de grille sur In2, bus d'impulsion et
  alimentations sur In1 côté est de la bande ; sur le cerveau, filtre
  RC devant chaque ADC, buck à 2,5 MHz en PWM forcé dans un coin,
  module radio dans le coin opposé aux connecteurs de quadrant.
- **Antenne du module ESP32** : l'origine de l'empreinte n'est pas au
  centre du module, et sa cour KiCad est la zone de dégagement d'antenne
  recommandée par Espressif (48 x 41 mm), bien plus grande que le corps.
  Sur les deux cartes le module est au bord, antenne hors de la carte ;
  le cerveau respecte la cour entière (rien d'autre dans le coin
  sud-est), l'horloge la réduit à la largeur du module, choix assumé
  dans `boardgen/clock.py` (BLE à courte portée, encodeur et
  microrupteur de part et d'autre). Si l'antenne recouvrait la carte,
  `antenna_keepout` y interdirait tout cuivre.

## Quadrant

Détection (spirales, échappées, 32 LED, distribution) plus frontal
complet : 16 cellules d'excitation et d'amortissement reprises de la
maquette, deux ADG1607 (double 8 vers 1) aux sorties en parallèle avec
un enable chacun, décodeurs 74HC4514 et 74HC154 sur 3,3 V, inverseur
74LVC1G04 pour inhiber l'excitation hors impulsion, chaîne AD8421 plus
Sallen-Key validée en SPICE, FPC 16 broches. L'ADG726 du brief n'a pas
de symbole vérifiable dans KiCad 7 et sa fiche n'était pas accessible
depuis l'environnement de génération : les deux ADG1607 le remplacent
avec un brochage vérifié. La bobine est un « net tie » sur le PCB
(couches 1 à 3 sur C{k}_A, couche 4 sur C{k}_B, jonction par deux
pastilles B.Cu dans le creux de la bobine) pour que le routeur ne
puisse jamais court-circuiter ses deux bornes ; ses vias d'empilement
sont décalées radialement hors des bandes de spires, sans quoi elles
court-circuitaient les couches entre elles ([note 14](14-revue-des-cartes.md)). Sur le FPC, les quatre
broches à destination imposée (masse vers le bus In1, 5 V LED vers le
bus In2, entrée et sortie de la chaîne LED) sortent en ligne droite au
delà des rangées de vias d'éventail de leurs voisines : le brochage du
yaml les tient à l'écart les unes des autres, la carte cerveau le
reflète automatiquement.

## Cerveau

STM32G474RE soudé sans quartz, USB-C, SWD, quatre liens quadrant
partageant un bus de commande, chaîne LED sérialisée, buck TPS62130,
LDO logique, îlot analogique 5VA, UART isolée vers un module
ESP32-S3-WROOM-1 ou une embase Pi (cavalier), connecteurs vers les
cartes moteurs et puissance, buzzer, LED, boutons. Le tableau des
broches est dans `plateau.brain.mcu_pins` ; il a été relu contre la
fiche technique (fonctions alternatives des quatre entrées ADC, USART3
sur PC10 et PC11, I2C1 sur PA15 et PB7), voir la
[note 14](14-revue-des-cartes.md).

## Puissance

BQ24610 (chargeur 3S synchrone) alimenté en 20 V par un module
déclencheur USB-C PD du commerce, BQ76920 (AFE de protection, FET en
bas côté), INA219 (jauge), bouton de réveil, fusible, cellules sur JST
XH. Les valeurs de consigne (ISET, ACSET, diviseur VFB, CTN) suivent
l'application type de TI, revues dans la [note 14](14-revue-des-cartes.md)
(mesure de charge 50 mohms, 1 A). Les FET sont des AO3400A, sauf les
deux FET d'entrée en AO3401A que l'ACDRV actif bas du BQ24610 pilote :
la carte ne voit jamais plus de 1,5 A.

## Moteurs

Deux embases pour modules TMC2209 SilentStepStick (brochage Pololu),
adresses UART 0 et 1, moteurs, fins de course et servo sur JST XH,
nappe IDC 2 x 10 vers le cerveau. Vit dans la base chariot, absente
sur le plateau fin.

## Horloge

Module ESP32-S3-WROOM-1 (le même que le cerveau, faute de symbole
ESP32-C3 dans les bibliothèques), MCP73831 sur USB-C, support 18650,
AP2112K, embase pour écran 2,4 pouces ILI9341, microrupteurs sous la
barre à bascule (positions dérivées du yaml, la carte à 5 mm des
parois), encodeur EC11 à l'avant droit, buzzer. La carte fait
110 x 60 mm dans le boîtier de 120 x 70.

## État des builds

Les nombres à jour (composants, nets fermés et ouverts, DRC KiCad) sont
dans la [note 14](14-revue-des-cartes.md), section 3, et dans le README
de chaque carte avec la liste nominative des nets ouverts. Ce qui reste
ouvert se concentre sur trois familles : les broches USB-C (pas de
0,5 mm sur deux rangées, l'éventail n'y tient pas), quelques nets de
puissance vers les gros connecteurs, et des descentes de masse dans
les zones denses. Rien de ce qui est tracé ne viole les règles : le
DRC de KiCad ne signale plus que les nets ouverts et la sérigraphie
depuis la revue.

| Quadrant | Cerveau |
|---|---|
| ![Quadrant](../images/quadrant.png) | ![Cerveau](../images/brain.png) |

| Puissance | Moteurs | Horloge |
|---|---|---|
| ![Puissance](../images/power.png) | ![Moteurs](../images/motion.png) | ![Horloge](../images/clock.png) |

## Avant fabrication

La revue du 03/09/2026 ([note 14](14-revue-des-cartes.md)) a relu les
brochages et corrigé les générateurs ; ce qui reste :

1. Fermer dans pcbnew les nets listés ouverts par le générateur, puis
   relancer `tools/drc.py`.
2. Trancher les points ouverts de la note 14 (LDO 5VA, CTN des cellules,
   plafond de luminosité des LED, type et orientation des nappes FPC,
   position du USB-C du cerveau dans la base).
3. Confirmer sur les fiches les formules ISET du BQ24610 et l'ADG1607 en
   5 V simple.
4. Compléter les codes LCSC manquants dans les générateurs (`jlc-bom.csv`
   n'exporte que les lignes qui en ont un).
5. Confirmer auprès du fabricant les vias d'éventail (0,45 mm, perçage
   0,2 mm) ; sinon passer à 0,6 mm et laisser le routeur finir ces
   sorties dans pcbnew.
6. Vérifier la hauteur des composants du frontal de quadrant (1,8 mm
   maximum sous le bois) sur la BOM finale.
