# Firmware ESP32 : pont radio et horloge

Deux projets ESP-IDF (5.x) pour le module ESP32-S3-WROOM-1, plus un
composant commun.

| Dossier | Rôle |
|---------|------|
| `common/` | analyseur de lignes du protocole (`proto.c`) et service Nordic UART sur NimBLE (`nus.c`), périphérique pour le pont, central pour l'horloge |
| `bridge/` | pont du cerveau : relais UART (STM32, 115200 bauds à travers l'ADuM1201) vers BLE, et retour ; WiFi et client Lichess plus tard |
| `clock/` | horloge à bascule : minuterie Fischer, Bronstein, simple ou libre, barre (deux microrupteurs), encodeur pour les presets, buzzer, écran ILI9341 2,4 pouces, liaison BLE au pont |

Le protocole est décrit dans `docs/notes/12-protocole.md`.

## État

- La logique de l'horloge (`clock/main/chessclock.c`) est testée sur
  PC : `cc -Iclock/main clock/test/test_chessclock.c clock/main/chessclock.c && ./a.out`.
  L'analyseur de lignes compile en C standard.
- Les parties ESP-IDF (NimBLE, UART, LEDC, esp_lcd) sont écrites contre
  l'API d'ESP-IDF 5.2 mais **ne sont pas compilées par la CI** du dépôt
  (pas de chaîne ESP-IDF). Première compilation à faire sur poste :

```bash
. ~/esp/esp-idf/export.sh
cd firmware/esp32/bridge && idf.py set-target esp32s3 && idf.py build flash monitor
cd firmware/esp32/clock  && idf.py set-target esp32s3 && idf.py build flash monitor
```

## Broches

Pont (module du cerveau) : UART1 sur IO17 (TX) et IO18 (RX) vers
l'ADuM1201, la console USB du module reste libre pour le débogage.

Horloge : voir `ESP_PINS` dans `tools/boardgen/clock.py` (écran SPI2
sur IO15/16/17 avec CS IO4, DC IO5, RST IO6, rétroéclairage IO7 ;
barre IO12 blancs et IO13 noirs ; encodeur IO9/IO10, poussoir IO11 ;
buzzer IO14).
