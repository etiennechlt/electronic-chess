# Carte puissance : pack 3S, charge, protection, jauge

![Carte puissance](../../docs/images/power.png)

Générée par `tools/boardgen` (module `power`). 100 x 60 mm, 2 couches,
plan de masse en face arrière. Elle gère trois cellules plates 1S 5 Ah.

- **Entrée** : 20 V depuis un module déclencheur USB-C PD du commerce
  (connecteur JST XH 2 broches), TVS SMBJ24A, sens de courant d'entrée
  10 mohms, deux P-FET AO3401A dos à dos (drain commun) que la sortie
  ACDRV, active bas, pilote.
- **Chargeur** : BQ24610, buck synchrone à deux AO3400A, self 10 µH,
  sens de courant 50 mohms (1 A = 50 mV), régulation 12,6 V par
  diviseur sur VFB, courant de charge 1 A (ISET1 à 0,995 V), précharge
  et fin de charge 0,2 A (ISET2 à 0,101 V), limite d'entrée 2,5 A
  (ACSET à 0,499 V), fenêtre de température 0 à 45 °C par le réseau
  5,23 k / 30,1 k de la fiche sur une CTN 10 k, sorties STAT et PG
  tirées au 3,3 V de l'AFE. Pas de chemin d'alimentation : le système
  tourne sur le pack, BATDRV reste libre.
- **Protection** : BQ76920 (AFE 3 à 5S) avec ses filtres 1 k / 100 nF
  par cellule, deux FET AO3400A en bas côté dans le retour du pack (DSG
  source côté cellules après la résistance de mesure, CHG source sur
  PACK-), sens 5 mohms, CTN, I2C vers le cerveau, sortie ALERT.
- **Jauge** : INA219 sur un shunt 10 mohms côté haut, même bus I2C.
- **Sorties** : fusible 2 A, embase pour un interrupteur, bouton de
  réveil (PWR_KEY), liaison 2 x 4 vers le cerveau, connecteur cellules
  JST XH 4 broches (B-, B1, B2, B+).

Les valeurs d'ISET, d'ACSET et du diviseur de tension suivent
l'application type du BQ24610, revues dans la
[note 14](../../docs/notes/14-revue-des-cartes.md) ; les formules
(ICHG = V(ISET1) / 20 RSR, IPRE = ITERM = V(ISET2) / 10 RSR) et la
plage admise de V(ISET2) restent à confirmer sur la fiche. Points
ouverts : la CTN de charge est sur la carte alors que le yaml la veut
sur le pack (deux broches de plus au connecteur cellules), et le cerveau
ne doit jamais ouvrir DSG par I2C (rien ne le refermerait).

```bash
PYTHONPATH=tools .venv/bin/python -m boardgen build power --render docs/images/power.png
```

## Résultat du build

Généré par `python -m boardgen build power` :

| Composants | Segments | Vias | Nets fermés | Nets ouverts | Défauts d'isolement |
|---|---|---|---|---|---|
| 82 | 417 | 156 | 43 | 10 | 0 |

Nets à finir dans pcbnew (le routeur les a laissés ouverts) :
- VREF
- 3V3_BMS
- CELL1
- CELL2
- SRP
- PH
- CELL3
- VAD
- PACK+
- BAT-

Le contrôle d'isolement exact ne signale aucun défaut : ce qui est
tracé respecte les règles, ce qui manque est listé ci-dessus. Les vias
d'éventail des boîtiers fins font 0,45 mm (perçage 0,2 mm), à
confirmer avec le fabricant avant commande.
