# Carte puissance : pack 3S, charge, protection, jauge

Générée par `tools/boardgen` (module `power`). 100 x 60 mm, 2 couches,
plan de masse en face arrière. Elle gère trois cellules plates 1S 5 Ah.

- **Entrée** : 20 V depuis un module déclencheur USB-C PD du commerce
  (connecteur JST XH 2 broches), TVS SMBJ24A, sens de courant d'entrée
  10 mohms, deux FET dos à dos pilotés par ACDRV.
- **Chargeur** : BQ24610, buck synchrone à deux AO3400A, self 10 µH,
  sens de courant 10 mohms, régulation 12,6 V par diviseur sur VFB,
  courant de charge 1 A (ISET1), précharge et fin de charge (ISET2),
  CTN sur TS, sorties STAT et PG tirées au 3,3 V de l'AFE. Pas de
  chemin d'alimentation : le système tourne sur le pack.
- **Protection** : BQ76920 (AFE 3 à 5S) avec ses filtres 1 k / 100 nF
  par cellule, deux FET AO3400A en bas côté (CHG, DSG) dans le retour
  du pack, sens 5 mohms, CTN, I2C vers le cerveau, sortie ALERT.
- **Jauge** : INA219 sur un shunt 10 mohms côté haut, même bus I2C.
- **Sorties** : fusible 2 A, embase pour un interrupteur, bouton de
  réveil (PWR_KEY), liaison 2 x 4 vers le cerveau, connecteur cellules
  JST XH 4 broches (B-, B1, B2, B+).

Les valeurs d'ISET, d'ACSET et du diviseur de tension suivent
l'application type du BQ24610 ; à vérifier en revue avant fabrication.

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
