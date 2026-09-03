# Carte moteurs : option chariot

Générée par `tools/boardgen` (module `motion`). 90 x 60 mm, 2 couches.
Elle vit dans la base chariot et se branche au cerveau par la nappe
IDC 2 x 10.

- Deux embases pour modules TMC2209 SilentStepStick (brochage Pololu :
  EN, MS1, MS2, PDN_UART x 2, CLK, STEP, DIR ; VM, GND, 2B, 2A, 1A, 1B,
  VIO, GND), adresses UART 0 et 1 par MS1, un seul fil UART à travers
  1 k, réserve 100 µF par pilote.
- Moteurs sur JST XH 4 broches, fins de course X et Y sur JST XH 3
  broches (GND, 3,3 V, signal), servo de l'actionneur d'aimant sur
  JST XH 3 broches (signal, 5 V, GND).
- Points de test, quatre trous M3.

```bash
PYTHONPATH=tools .venv/bin/python -m boardgen build motion --render docs/images/motion.png
```

## Résultat du build

Généré par `python -m boardgen build motion` :

| Composants | Segments | Vias | Nets fermés | Nets ouverts | Défauts d'isolement |
|---|---|---|---|---|---|
| 31 | 151 | 109 | 27 | 1 | 0 |

Nets à finir dans pcbnew (le routeur les a laissés ouverts) :
- MOT_DIAG

Le contrôle d'isolement exact ne signale aucun défaut : ce qui est
tracé respecte les règles, ce qui manque est listé ci-dessus. Les vias
d'éventail des boîtiers fins font 0,45 mm (perçage 0,2 mm), à
confirmer avec le fabricant avant commande.
