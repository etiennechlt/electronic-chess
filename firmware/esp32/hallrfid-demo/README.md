# Micrologiciel du démonstrateur Hall + RFID (ESP32-S3)

Projet ESP-IDF (5.x) pour le module ESP32-S3-WROOM-1 de la carte
`hardware/hallrfid-demo` ([note 27](../../../docs/notes/27-demonstrateur-hall-rfid.md)) :
deux lecteurs MFRC522 sur un bus SPI (une ligne `NSS` et une ligne
`NRSTPD` chacun), six capteurs Hall analogiques à travers un CD74HC4067
sur l'ADC1 (les deux centraux aussi sur une entrée directe), le rail
commuté des capteurs, l'entrée de la vignette de champ et la LED. La
console, sur l'USB natif du module, est l'outil de la mise en route du
[protocole](../../../measurements/protocol.md) : chaque pas du
paragraphe 10.1 de la note 25 y est une commande.

| Fichier | Rôle |
|---|---|
| `main/mfrc522.c`, `mfrc522.h` | pilote du MFRC522 derrière une interface SPI abstraite : registres, réveil et mise hors tension, conductance, états « émission » et « tenu », transceive, CRC par le coprocesseur, séquence ISO 14443A (REQA, anticollision, SELECT, deux niveaux de cascade) ; C99 sans dépendance, testé sur PC |
| `main/hall.c`, `hall.h` | zéros, correction ratiométrique par les voies de référence du mux, seuils avec hystérésis, pôle ; testé sur PC |
| `main/demo_config.h` | **généré** depuis `config/board.yaml` par `scripts/gen_config.py` : broches, voies du mux, seuils en comptes ADC (`chessboard_calc.hall` au pas de la maquette), temps d'établissement (`hallrfid_mockup.hall_chain`), critères de mise en route ; commité pour que le build se passe de Python |
| `main/main.c` | l'ESP-IDF : SPI, GPIO, ADC, console USB-Serial-JTAG |
| `test/test_hallrfid_demo.c` | test hôte : le pilote contre une puce simulée (registres, FIFO, coprocesseur CRC, une étiquette à UID de 7 octets dans le champ), les helpers Hall contre les seuils générés ; lancé par la CI |

## Construire et tester

```bash
# test de la logique sur PC (ce que fait la CI)
cc -Wall -Wextra -Werror -Imain test/test_hallrfid_demo.c main/mfrc522.c main/hall.c \
  -o /tmp/test_hallrfid_demo && /tmp/test_hallrfid_demo

# regénérer l'en-tête après toute édition de hall_rfid dans le yaml
PYTHONPATH=../../.. python3 scripts/gen_config.py ../../../config/board.yaml main/demo_config.h

# cible (ESP-IDF 5.x, non compilé par la CI)
. ~/esp/esp-idf/export.sh
idf.py set-target esp32s3 && idf.py build
idf.py -p /dev/ttyACM0 flash monitor
```

Le test `tests/test_hallrfid_demo_firmware.py` du dépôt vérifie que
l'en-tête commité est exactement ce que le générateur écrit depuis le
yaml.

## Console (USB natif, lignes terminées par entrée)

Au démarrage, les deux lecteurs sont en mise hors tension matérielle et
le rail des capteurs est coupé : rien n'émet avant une commande.

| Commande | Action | Réponse |
|---|---|---|
| `h` | aide et critères du yaml | |
| `e`, `E` | rail des capteurs alimenté, coupé (`ROW_EN1`) | `S,rail on` |
| `s` | un balayage : voies de référence (masse, rail divisé par deux), puis chaque capteur par le mux et, pour A1 et B1, l'entrée directe | `REF,...` puis une ligne `H,<site>,<brut>,<corrigé>,<écart>,<mT>,<pôle S/N/.>,<present/empty>,<direct>` par capteur |
| `z` | les lectures courantes deviennent les zéros | `S,zeroed` |
| `w <n>` | réveil du lecteur n (1 = A1, 2 = B1) : `NRSTPD` haute, réinitialisation logicielle, `VersionReg`, état tenu à la conductance réduite (`CWGsP` 8) | `W,A1,ok,version,0x92,nxp,cwgsp,8` |
| `d <n>` | mise hors tension matérielle du lecteur n | |
| `v` | `VersionReg` des lecteurs | `V,A1,0x92` |
| `t <n> <g>` | le lecteur n émet à la conductance `CWGsP` g (0 à 63, `CWGsN` en proportion) | rappelle où lire le courant TVDD et la limite d'acceptation |
| `o <n>` | retour à l'état tenu : émetteurs validés, `Force100ASK`, `DriverSel` 10, TX1 et TX2 à 0 | |
| `r <n>` | une lecture ISO 14443A | `UID,A1,04A23B1C5D6E80,sak,0x00,atqa,0044` ou `NOTAG,A1,notag` |
| `R <n> <k>` | k lectures (par défaut `criteria.read_trials`) | `READS,A1,<réussies>,<k>,uid,<hex>,cwgsp,<g>` |
| `p` | l'entrée `PICKUP` | `P,<comptes>,<mV>` |
| `l` | bascule la LED | |
| `i` | identifier : balayage, puis lecture de l'étiquette de chaque case occupée (le lecteur passe en émission le temps de la lecture s'il était tenu) | |

Le micrologiciel n'écrit jamais `DriverSel` à 00 (sorties en haute
impédance, état non spécifié par la fiche), n'emploie que les registres
communs à la puce NXP et à ses clones, et n'exige pas l'autotest NXP
(note 25, paragraphe 4.4). La conductance de la première émission
(`FIRST_CW_GS_P`, 8 sur 63) est une valeur de registre du micrologiciel,
pas une grandeur du yaml ; la conductance de service se mesure à la
vignette (note 27, section 6, pas 8).

## Ce que ce micrologiciel ne fait pas

Il ne décide rien : il mesure et affiche. L'arbitrage présence et
identité, la détection d'un coup, la liaison avec le cerveau du plateau
appartiennent au lot 7 de la note 25, après les mesures M12 à M14.
