# Scanner Hall (ESP32-S3) : la couche de présence de la note 24

Prototype autonome de l'alternative « Hall + RFID » évaluée dans la
[note 24](../../../docs/notes/24-hall-et-rfid.md) : un capteur à effet
Hall analogique par case lit l'aimant ferrite que chaque pièce porte
déjà (ADR 0002), quatre multiplexeurs CD74HC4067 (un par quadrant,
adresses communes) amènent les 64 sorties sur quatre entrées ADC1 d'un
ESP32-S3, et l'alimentation des capteurs est commutée par rangée de
quadrant pour tenir le courant moyen. Le module est celui de l'horloge
et du pont, même chaîne ESP-IDF.

| Fichier | Rôle |
|---|---|
| `main/hallscan.c`, `hallscan.h` | la logique : lignes de base par case, seuil et hystérésis en comptes ADC, anti-rebond, carte d'occupation, ligne `B` du protocole ; C99 sans dépendance, testée sur PC |
| `main/hallscan_config.h` | **généré** depuis `config/board.yaml` par `scripts/gen_config.py` : seuils (calculés par `chessboard_calc.hall`), broches, cadence, correspondance mux et canal vers case ; commité pour que le build se passe de Python |
| `main/main.c` | l'ESP-IDF : ADC en lecture unitaire, adresses de mux, commutation des rangées, console |
| `test/test_hallscan.c` | test hôte, lancé par la CI |

## Construire et tester

```bash
# test de la logique sur PC (ce que fait la CI)
cc -Wall -Wextra -Werror -Imain test/test_hallscan.c main/hallscan.c -o /tmp/test_hallscan \
  && /tmp/test_hallscan

# regénérer l'en-tête après toute édition de hall_rfid dans le yaml
python3 scripts/gen_config.py ../../../config/board.yaml main/hallscan_config.h

# cible (ESP-IDF 5.x, non compilé par la CI)
. ~/esp/esp-idf/export.sh
idf.py set-target esp32s3 && idf.py build flash monitor
```

Le test `tests/test_hallscan_config.py` du dépôt vérifie que l'en-tête
commité est exactement ce que le générateur écrit depuis le yaml.

## Console (115200 bauds, UART0)

Sortie : la ligne `B,<64 caractères>` de la
[note 12](../../../docs/notes/12-protocole.md) à chaque changement
d'occupation (`.` vide, `?` pièce présente, `w` et `b` si le codage par
polarité est activé dans le yaml), et un compte-rendu périodique sur le
journal.

| Touche | Action |
|---|---|
| `z` | zéro : les lectures courantes de l'échiquier vide deviennent les lignes de base |
| `r` | comptes bruts des 64 cases, une ligne `R,` en CSV |
| `b` | la ligne `B` courante |

## Cycle d'un scan

1. Rangée `g` alimentée (`ROW_EN<g>` bas, P-FET côté haut), attente
   `HALL_POWER_ON_US`.
2. Pour chaque canal de la rangée : adresse sur `MUX_S0..S3`, attente
   `HALL_MUX_SETTLE_US`, puis sur chacun des quatre mux la moyenne de
   `HALL_SAMPLES_PER_SQUARE` lectures ADC.
3. `hallscan_update` : écart à la ligne de base, seuil ou relâchement
   avec hystérésis, anti-rebond sur `HALL_DEBOUNCE_SCANS` scans ; une
   ligne `B` part si une case a changé d'état publié.

Les seuils sont ceux du rapport `python -m chessboard_calc report` :
moitié du champ le plus faible attendu (pion à l'entrefer maximal),
relâchement 15 % plus bas, tous deux convertis en comptes ADC par la
sensibilité du capteur retenu et le pas de l'ADC.

## Ce que ce prototype ne fait pas

- Il n'identifie pas les pièces : la case est vide ou occupée (et, en
  option, blanche ou noire par le sens de l'aimant). L'identité est le
  rôle de la chaîne LC du projet, ou de la couche RFID de la note 24.
- Il n'arbitre pas : la déduction du coup joué depuis deux cartes
  d'occupation appartient au cerveau (lot 6 de la note 07).
- Broches, nombre de groupes et cadence viennent du yaml ; les
  numéros de GPIO sont à confirmer contre le brochage du module avant
  tout câblage (ADC1 sur GPIO1 à GPIO10 sur le S3).
