# Horloge à bascule : carte

![Carte horloge](../../docs/images/clock.png)

Générée par `tools/boardgen` (module `clock`). 110 x 60 mm, 2 couches,
dans le boîtier de `mechanical/clock.py`.

- **Radio et calcul** : module ESP32-S3-WROOM-1 (le même que sur le
  cerveau, BLE vers le plateau), antenne hors du bord est, cour réduite
  à la largeur du module (l'encodeur et un microrupteur sont de part et
  d'autre, choix assumé pour du BLE à courte portée), boutons BOOT et
  EN, embase de programmation 1 x 6, diviseur de tension batterie sur
  IO1, état du chargeur sur IO2 par un diviseur 56 k / 100 k (STAT monte
  à 5 V).
- **Énergie** : USB-C en alimentation seule (5,1 k sur CC, D+, D- et SBU
  non connectés), chargeur 1S MCP73831 à 500 mA avec LED d'état,
  support 18650 Keystone 1042, embase pour l'interrupteur, AP2112K 3,3 V.
- **Interface** : embase 1 x 14 pour un écran 2,4 pouces ILI9341 SPI
  avec tactile, rétroéclairage commuté par un P-FET AO3401A sur 3V3
  (IO7 actif bas, éteint au démarrage), deux microrupteurs 6 x 6 sous
  les extrémités de la
  barre à bascule (positions dérivées de `clock.rocker` du yaml, la
  carte étant à 5 mm des parois du boîtier), encodeur EC11 à poussoir
  à l'avant droit sous son trou de la face inclinée, buzzer 12 mm sur
  transistor, USB-C dans la fente arrière.

```bash
PYTHONPATH=tools .venv/bin/python -m boardgen build clock --render docs/images/clock.png
```

## Résultat du build

Généré par `python -m boardgen build clock` :

| Composants | Segments | Vias | Nets fermés | Nets ouverts | Défauts d'isolement |
|---|---|---|---|---|---|
| 50 | 307 | 149 | 31 | 6 | 0 |

Nets à finir dans pcbnew (le routeur les a laissés ouverts) :
- CHG_SENSE: 1 pad(s) left open (usable start cells 77, goal cells 85)
- CC2: 2 pad(s) left open (usable start cells 8, goal cells 50)
- GND: pad at cell (131, 39) has no drop to the pour
- GND: pad at cell (149, 30) has no drop to the pour
- GND: pad at cell (464, 98) has no drop to the pour
- GND: pad at cell (542, 102) has no drop to the pour

DRC KiCad 7 (`tools/drc.py`, zones remplies) : 178 signalements, 51 éléments non connectés (les nets ouverts ci-dessus), erreurs restantes : aucune ; avertissements sans effet sur la fabrication : via_dangling 53, lib_footprint_issues 50, silk_overlap 38, track_dangling 28, silk_over_copper 8, silk_edge_clearance 1. Le contrôle d'isolement exact du générateur ne signale aucun défaut. Les vias d'éventail des boîtiers fins font 0,45 mm (perçage 0,2 mm), dans les capacités standard de JLCPCB, à confirmer sur le devis.
