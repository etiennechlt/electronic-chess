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
| 113 | 1062 | 655 | 76 | 25 | 0 |

Nets à finir dans pcbnew (le routeur les a laissés ouverts) :
- ADC2
- LED_DIN1
- AMP_OUT4
- MUX_A2
- MUX_EN_L
- MUX_EN_H
- DAMP_EN_N
- PULSE_EN
- 5V_LED
- 5VA
- VBAT (route refusée par le contrôle d'isolement)
- VIN (route refusée par le contrôle d'isolement)
- 3V3
- USB_DP_C
- LED3_K
- BUZ_DRV
- USB_DP
- CC1
- GND (descente vers le plan pour une broche)
- GND (descente vers le plan pour une broche)
- GND (descente vers le plan pour une broche)
- GND (descente vers le plan pour une broche)
- GND (descente vers le plan pour une broche)
- GND (descente vers le plan pour une broche)
- GND (descente vers le plan pour une broche)

Le contrôle d'isolement exact ne signale aucun défaut : ce qui est
tracé respecte les règles, ce qui manque est listé ci-dessus. Les vias
d'éventail des boîtiers fins font 0,45 mm (perçage 0,2 mm), à
confirmer avec le fabricant avant commande.
