# Horloge à bascule : carte

![Carte horloge](../../docs/images/clock.png)

Générée par `tools/boardgen` (module `clock`). 110 x 60 mm, 2 couches,
dans le boîtier de `mechanical/clock.py`.

- **Radio et calcul** : module ESP32-S3-WROOM-1 (le même que sur le
  cerveau, BLE vers le plateau), boutons BOOT et EN, embase de
  programmation 1 x 6, diviseur de tension batterie sur IO1.
- **Énergie** : USB-C en alimentation seule (5,1 k sur CC), chargeur 1S
  MCP73831 à 500 mA avec LED d'état, support 18650 Keystone 1042,
  embase pour l'interrupteur, AP2112K 3,3 V.
- **Interface** : embase 1 x 14 pour un écran 2,4 pouces ILI9341 SPI
  avec tactile, deux microrupteurs 6 x 6 sous les extrémités de la
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
| 46 | 285 | 163 | 29 | 6 | 0 |

Nets à finir dans pcbnew (le routeur les a laissés ouverts) :
- VBAT_SENSE
- SBU2
- USB_DP
- USB_DM
- CC1
- CC2

Le contrôle d'isolement exact ne signale aucun défaut : ce qui est
tracé respecte les règles, ce qui manque est listé ci-dessus. Les vias
d'éventail des boîtiers fins font 0,45 mm (perçage 0,2 mm), à
confirmer avec le fabricant avant commande.
