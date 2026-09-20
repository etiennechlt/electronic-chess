# Cerveau : carte principale du plateau

![Carte cerveau](../../docs/images/brain.png)

Carte générée par `tools/boardgen` (module `brain`) depuis
`config/board.yaml` (ADR 0010). 120 x 80 mm, 4 couches : F.Cu
composants et signaux, In1 plan de masse, In2 alimentations et
signaux longs, B.Cu signaux. Elle vit au fond de la base, sur
l'empreinte commune aux deux bases.

## Blocs

- **MCU** : STM32G474RE soudé (LQFP-64), sans quartz (HSI plus CRS sur
  l'USB), boutons RESET et BOOT, connecteur SWD 2 x 5 au pas 1,27 mm
  (SWO et TDI laissés libres), USB-C en périphérique (USBLC6-2 en
  protection, 5,1 k sur CC, VBUS non utilisé : la carte se nourrit du
  pack). Le tableau des broches est `plateau.brain.mcu_pins` dans le
  yaml, relu contre la fiche technique dans la
  [note 14](../../docs/notes/14-revue-des-cartes.md) (quatre entrées ADC
  sur quatre convertisseurs distincts, PB8 sert de BOOT0, PG10 de NRST).
- **Liens quadrants** : quatre connecteurs FPC 16 broches (même
  brochage que le quadrant), bus d'adresses et d'enables partagé,
  quatre sorties analogiques vers quatre ADC à travers 49,9 ohms et
  1 nF, chaîne LED sérialisée d'un quadrant au suivant, tampon
  74AHCT1G125 à la source.
- **Alimentation** : fusible d'entrée, buck TPS62130 3 A à 2,5 MHz en
  PWM forcé (DEF haut) pour le 5 V, AP2112K pour le 3,3 V logique,
  LP2985 plus perle de ferrite pour l'îlot 5VA des quadrants, rail
  12 V d'impulsion (VIN) fusé avec sa réserve de 100 µF, rail LED fusé.
- **Communication** : UART tamponnée par un ADuM1201 (GND2 sur la masse
  commune : pas d'isolation galvanique tant que le module est sur la
  carte), TXD0 du module vers l'entrée VIA, sortie VOB vers RXD0, load
  switch P-FET sur le 5 V du module, régulateur AMS1117 pour
  l'ESP32-S3-WROOM-1, cavalier JP1 pour alimenter le côté module depuis
  l'ESP32 ou le Pi, embase Pi 2 x 4, embase de programmation ESP 1 x 6,
  boutons BOOT et EN. Le module est au bord est, son antenne dépasse de
  6 mm de la carte et sa zone de dégagement (la cour KiCad, 48 x 41 mm)
  occupe le coin sud-est : le quatrième trou de fixation est remonté à
  mi-hauteur du bord est.
- **Liens** : IDC 2 x 10 vers la carte moteurs (VBAT, STEP, DIR, EN,
  UART TMC, fins de course, servo, 5 V, 3,3 V), 2 x 4 vers la carte
  puissance (VBAT, I2C, état de charge, touche de réveil).
- **Interface** : buzzer 12 mm sur transistor, quatre LED d'état,
  bouton utilisateur, points de test.

## Hygiène de signal

Le plan de masse In1 est continu ; les sorties analogiques arrivent au
bord nord avec leur filtre RC juste devant le MCU ; le module radio est
au coin sud-est, le plus loin des connecteurs de quadrant ; le buck est
au coin nord-est avec sa boucle de commutation courte. Le routeur pousse
les longs signaux sur les couches internes (coût majoré sur F.Cu et
B.Cu) et ne perce jamais de via dans le trou d'une pastille traversante.
Point ouvert de la revue : le LP2985 de l'îlot 5VA (SOT-23-5) dissipe
0,5 W depuis VBAT pour les quatre frontaux, un boîtier à pad thermique
est proposé.

## Régénérer

```bash
PYTHONPATH=tools .venv/bin/python -m boardgen build brain --render docs/images/brain.png
```

Le contrôle d'isolement exact tourne à chaque build ; les nets que le
routeur n'a pas fermés sont listés et restent à finir dans pcbnew.

## Résultat du build

Généré par `python -m boardgen build brain` le 20/09/2026 :

| Composants | Segments | Vias | Raccords de la passe | Nets fermés | Nets ouverts | Défauts d'isolement |
|---|---|---|---|---|---|---|
| 113 | 1528 | 476 | 6 | 92 | 0 | 0 |

Ce qui a fermé la carte, dans l'ordre où il a fallu le trouver
([note 04](../../docs/notes/04-routeur-et-garanties.md)) :

- les éventails des quatre liens FPC dessinés à la main (voies de
  0,3 mm en escalier sur la face avant, un petit via au bout de chacune,
  les masses descendues au plan à leur moignon), la bande médiane
  descendue sous eux ;
- le bus des quadrants, les alimentations, VBAT, les quatre sorties
  analogiques et les deux lignes UART de l'isolateur routés en premier,
  quand la carte est vide ;
- le haul VBAT dessiné à la main sur la face arrière, du lien moteurs
  au fusible F1 par le bord sud puis une colonne à l'ouest du lien
  puissance ;
- chaque LED d'état placée à côté de sa résistance ;
- les masses descendues au plan avant les signaux, une garde de 0,1 mm
  autour des pastilles CMS ;
- le rip-up et reroutage des nets murés, puis la passe de finition
  partagée (six raccords).

DRC KiCad 7 (`tools/drc.py`, zones remplies) : 220 signalements, aucun élément non connecté, aucune erreur ; avertissements sans effet sur la fabrication : lib_footprint_issues 113, silk_overlap 52, via_dangling 27, silk_over_copper 23, silk_edge_clearance 3, track_dangling 2. Le contrôle d'isolement exact du générateur ne signale aucun défaut. Les vias d'éventail des boîtiers fins font 0,45 mm (perçage 0,2 mm), dans les capacités standard de JLCPCB.

## Fabrication

`brain-gerbers.zip` (quatre couches de cuivre, masques, sérigraphies,
pâte, contour, perçages PTH et NPTH, fiche de travail) et son
empreinte `brain-gerbers.sha256`, produits par
`/usr/bin/python3 tools/gerbers.py hardware/brain/brain.kicad_pcb` ;
`sha256sum -c brain-gerbers.sha256` dans ce dossier vérifie que
l'archive est celle de la carte commitée. Commande et options du
formulaire dans la [note 23](../../docs/notes/23-commande-jlcpcb.md) :
120 x 80 mm, 4 couches, ENIG (LQFP au pas de 0,5 mm, QFN, quatre FPC),
cuivre interne standard. La nomenclature d'assemblage (`jlc-bom.csv`,
`jlc-cpl.csv`) est complète en références, mais ses codes LCSC restent
à vérifier ligne par ligne avant tout ordre d'assemblage
([note 22](../../docs/notes/22-erreurs-de-conception.md), point 11).
