# Banc Nucleo : shield d'alimentation et de liaison du quadrant 2 x 2

![Carte de banc](../../docs/images/bench.png)

Carte générée par `tools/boardgen` (module `bench`) depuis la section
`bench` de `config/board.yaml`, pour le banc de la
[note 19](../../docs/notes/19-cerveau-et-banc-nucleo.md) : une
Nucleo-G474RE (le MCU du cerveau, sa sonde et son port série) qui
mesure le quadrant réduit 2 x 2 (`hardware/quadrant-2x2/`) avec le
firmware du cerveau compilé en `make NUCLEO=1`. Le shield apporte au
quadrant ce que le cerveau lui aurait donné, et rien d'autre.
80 x 56 mm, 2 couches : composants et signaux sur F.Cu, plan de masse
sur B.Cu. Elle s'emboîte sur les quatre embases Arduino de la Nucleo
par des barrettes mâles montées côté cuivre, corps sous la carte.

## Blocs

- **Embases Arduino** (J3 alimentation, J4 analogique, J5 numérique 0 à
  7, J6 numérique 8 à 15) : positions prises sur l'empreinte officielle
  `Arduino_UNO_R3`, contour Uno affleurant au bord ouest, bande de
  11,4 mm à l'est pour le jack et la nappe. Le bus du quadrant est sur
  les broches de `bench.signals` : AMP_OUT (après RC) sur A0, PULSE_EN
  sur A2, MUX_A0 à A2 sur D3, D4, D5, MUX_EN_L sur A5, MUX_EN_H sur A4,
  DAMP_EN_N sur D6, LED_DIN sur D13. Le shield prend le 3,3 V et la
  masse de la Nucleo ; son 5 V ne remonte jamais vers elle (la Nucleo
  reste sur l'USB de sa sonde), VIN, 5V, IOREF, NRST et AREF restent
  ouverts.
- **Entrée 12 V** (J1 jack 5,5 x 2,1 mm, prise vers l'est) : SS34 en
  série contre l'inversion, SMBJ15A vers la masse, fusible 1 A, puis
  100 µF, 10 µF et 100 nF : la réserve du rail d'impulsion, comme sur
  le cerveau, dans la colonne centrale entre le jack et le buck.
- **Buck 5 V** (TPS62130, 2,2 µH, DEF haut : PWM forcé) : le rail des
  LED à travers un second fusible 2 A et 100 µF, et l'alimentation du
  tampon LED. Colonne ouest, là où le motif Uno laisse le shield vide.
- **Îlot analogique 5VA** : LP2985-5.0 depuis le 12 V, perle de
  ferrite BLM21PG221, 10 µF et 100 nF, comme sur le cerveau. Le
  cavalier JP1 choisit la source de 5VA_RAW : broches 1 et 2, le LDO
  (défaut) ; 2 et 3, le buck. C'est la comparaison LDO contre buck de la
  mesure M8.
- **Liaison quadrant** : J2, FPC 16 broches Hirose FH12 au brochage du
  quadrant (`plateau.quadrant.link.pinout`), au coin sud-est, nappe
  vers le sud, pastilles vers le nord ; tampon 74AHCT1G125 (3,3 V vers
  5 V) et 470 ohms devant LED_DIN, LED_DOUT sur un point de test ;
  49,9 ohms et 1 nF devant A0, le filtre du cerveau.
- **Points de test** : TP1 LED_END, TP2 5VA, TP3 5V, TP4 3V3, TP5 GND,
  TP6 VIN, TP7 ADC1 (AMP_OUT filtré). Le bus de commande (PULSE_EN,
  DAMP_EN_N, adresses du mux) se sonde sur les broches Morpho de la
  Nucleo, qui doublent chaque broche Arduino.

## Ce qui se soude à la main

Le tampon LED, le buck, l'inductance, le LDO, la perle, les diodes,
le jack et le connecteur FPC reprennent les références du cerveau,
code LCSC compris. Les passifs, les quatre barrettes Arduino (côté
cuivre), JP1 et les points de test n'ont pas de code : `jlc-bom.csv`
ne liste que les lignes qui en ont un, le reste se soude à la main ou
attend la passe de sourcing des autres cartes.

## Régénérer

```bash
PYTHONPATH=tools .venv/bin/python -m boardgen build bench --render docs/images/bench.png
```

`tests/test_bench.py` vérifie que chaque signal du bus est sur la
broche du cerveau (sauf DAMP_EN_N, déplacé de PC2 à D6 parce que PC2
n'atteint qu'un connecteur Morpho), que chaque broche d'embase porte
le net que dit le yaml, que la nappe reprend le brochage du quadrant,
et que chaque broche de barrette tombe sur la pastille de l'empreinte
Uno qu'elle représente.

## Résultat du build

Généré par `python -m boardgen build bench` :

| Composants | Segments | Vias | Nets fermés | Nets ouverts | Défauts d'isolement |
|---|---|---|---|---|---|
| 43 | 193 | 89 | 23 | 6 | 0 |

Nets à finir dans pcbnew (le routeur les a laissés ouverts) :
- LED_DIN1: 1 pad(s) left open (usable start cells 42, goal cells 29)
- MUX_EN_L: 2 pad(s) left open (usable start cells 29, goal cells 264)
- AMP_OUT1: 1 pad(s) left open (usable start cells 38, goal cells 30)
- SW: route rejected, F.Cu: vs BUCK_PG at (23.4,13.7) gap 0.100
- VIN: route rejected, F.Cu: vs BUCK_SS at (27.3,13.7) gap 0.100
- 3V3: 4 pad(s) left open (usable start cells 29, goal cells 378)

Quatre sont des sorties de l'éventail du FPC (LED_DIN1, MUX_EN_L,
AMP_OUT1, 3V3 : la pastille de J2 est murée par les vias de ses
voisines), deux des pistes de puissance refusées à 0,05 mm près contre
les pastilles du QFN du buck (SW, VIN) : le même lot que sur le
cerveau, quelques minutes dans pcbnew, chevelu affiché, puis DRC
KiCad 7 (`tools/drc.py`). Le contrôle d'isolement exact ne signale
aucun défaut sur ce qui est routé.
