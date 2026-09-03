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

Généré par `python -m boardgen build brain` :

| Composants | Segments | Vias | Nets fermés | Nets ouverts | Défauts d'isolement |
|---|---|---|---|---|---|
| 113 | 1085 | 414 | 76 | 24 | 0 |

Nets à finir dans pcbnew (le routeur les a laissés ouverts) :
- ADC2: 1 pad(s) left open (usable start cells 81, goal cells 36)
- AMP_OUT4: 1 pad(s) left open (usable start cells 38, goal cells 30)
- LED_DIN1: 1 pad(s) left open (usable start cells 30, goal cells 29)
- ENDSTOP_X: 4 pad(s) left open (usable start cells 76, goal cells 473)
- MUX_A2: 1 pad(s) left open (usable start cells 137, goal cells 29)
- MUX_EN_L: 4 pad(s) left open (usable start cells 41, goal cells 116)
- MUX_EN_H: 3 pad(s) left open (usable start cells 79, goal cells 114)
- DAMP_EN_N: 4 pad(s) left open (usable start cells 41, goal cells 116)
- ESP_EN: 9 pad(s) left open (usable start cells 32, goal cells 874)
- 5V_LED: 1 pad(s) left open (usable start cells 473, goal cells 38)
- VBAT: route rejected, F.Cu: vs BUCK_SS at (91.5,21.8) gap 0.121
- VIN: route rejected, F.Cu: vs DAMP_EN_N at (56.5,6.8) gap 0.100
- USB_DP_C: 1 pad(s) left open (usable start cells 107, goal cells 4)
- LED5_K: 1 pad(s) left open (usable start cells 42, goal cells 35)
- CC1: 4 pad(s) left open (usable start cells 10, goal cells 55)
- CC2: 4 pad(s) left open (usable start cells 8, goal cells 59)
- GND: pad at cell (224, 336) has no drop to the pour
- GND: pad at cell (244, 336) has no drop to the pour
- GND: pad at cell (590, 193) has no drop to the pour
- GND: pad at cell (433, 132) has no drop to the pour
- GND: pad at cell (257, 93) has no drop to the pour
- GND: pad at cell (277, 93) has no drop to the pour
- GND: pad at cell (462, 132) has no drop to the pour
- GND: pad at cell (491, 132) has no drop to the pour

DRC KiCad 7 (`tools/drc.py`, zones remplies) : 358 signalements, 141 éléments non connectés (les nets ouverts ci-dessus), erreurs restantes : copper_edge_clearance 4 ; avertissements sans effet sur la fabrication : via_dangling 115, lib_footprint_issues 113, silk_overlap 51, track_dangling 50, silk_over_copper 22, silk_edge_clearance 3. Le contrôle d'isolement exact du générateur ne signale aucun défaut. Les vias d'éventail des boîtiers fins font 0,45 mm (perçage 0,2 mm), dans les capacités standard de JLCPCB, à confirmer sur le devis.
