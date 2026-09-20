# Firmware du cerveau (STM32G474RE, quatre quadrants)

Dérivé du firmware de maquette (`firmware/mockup`), CMSIS nu sans HAL.
Il pilote le bus de commande commun aux quatre quadrants (adresses
A0..A2, enables des deux ADG1607, PULSE_EN, DAMP_EN_N), acquiert le
ringdown sur le convertisseur propre à chaque quadrant (ADC1 à ADC4,
un à la fois, 3,78 Méch/s, 512 points, FFT et interpolation), mesure
la voie B (comparateur plus capture de période) sur le quadrant 1, et
commande les 128 LED de camp en série.

## Construction

```bash
make            # build/board.bin (arm-none-eabi-gcc)
make NUCLEO=1   # build/nucleo/board-nucleo.bin, variante banc (section ci-dessous)
make NUCLEO=1 NUCLEO_FULL=1   # build/nucleo-full/board-nucleo-full.bin, un 4 x 4 sur le banc
make pins       # regénère src/board_pins.h depuis config/board.yaml
                # (PYTHONPATH=tools, la chaîne LED vient de quadgen.layout)
make flash      # rappel de la procédure ST-Link sur le connecteur SWD
```

`board_pins.h` est commité : refaire `make pins` après toute édition de
`plateau.brain.mcu_pins` ou de la géométrie des LED.

## Utilisation

Console sur USART1 (PA9/PA10), donc sur l'UART isolée : sur l'établi,
un adaptateur USB-UART sur l'embase Pi (J8) avec le cavalier JP1 côté
Pi ; plus tard, l'ESP32-S3 relaie le même flux en BLE et en WiFi.
115200 bauds, commande `h` pour l'aide. Sortie CSV :
`q,coil,sq,fa_hz,fb_hz,amp_mv,snr_db10` avec `sq = colonne + 8 x rangée`
(rangée 0 côté joueur, quadrants 1 et 3 à l'ouest, 2 et 4 à l'est
montés tournés).

- `s` : un scan des 64 cases ; `m` / `x` : scan répété marche/arrêt.
- `1`..`4` : scan d'un quadrant.
- `c` : calibration (16 mesures par case, moyennes en flash avec CRC).
- `i` : identification au plus proche voisin ; `l` : identification et
  allumage des LED (démo : classes paires au camp blanc, impaires au
  camp noir) ; `o` : extinction.
- `r` : dump brut des 512 échantillons du quadrant 1, bobine 1.
- `p` / `P` : durée d'impulsion d'excitation par pas de 100 ns.

## Séquence de mesure (par bobine)

1. Adresse sur le bus : mux, décodeur d'excitation et décodeur
   d'amortissement lisent le même index (A0..A2 plus MUX_EN_H comme
   quatrième bit) ; amortissement actif, ADC du quadrant sélectionné.
2. Relâchement de l'amortisseur ; PULSE_EN monte : le rail 12 V et la
   grille du FET de la bobine adressée s'activent ensemble (le 74HC4514
   est inhibé tant que PULSE_EN est bas).
3. Impulsion (1 µs par défaut), flyback dans le SS34FL.
4. Blanking 2 µs par amortissement actif, puis écoute.
5. Acquisition ADC (et captures comparateur sur le quadrant 1).
6. Ré-amortissement, libération des enables, FFT, ligne CSV.

## À vérifier au premier démarrage

- Codes COMP3 INMSEL (DAC3_CH1) et TIM2 TI4SEL (COMP3) dans `comp.c`,
  pris de mémoire du RM0440.
- Numéros de requête DMAMUX des ADC2 à ADC4 dans `adc.c` (36, 37, 38)
  et canaux d'entrée (ADC2_IN3 sur PA6, ADC3_IN12 sur PB0, ADC4_IN4 sur
  PB14), avec la fiche technique.
- Fonctions non couvertes par cette version : I2C vers la carte
  puissance, buzzer, LED d'état, bouton, chariot, et les messages de
  partie du protocole (`B`, `M`, `F`, `S`, [note 12](../../docs/notes/12-protocole.md)) :
  la console n'émet encore que les CSV de mesure, que le pont ESP32
  relaie tels quels.

## Variante banc : `make NUCLEO=1`

Le même firmware, compilé pour le banc de la
[note 19](../../docs/notes/19-cerveau-et-banc-nucleo.md) : une
Nucleo-G474RE (même MCU que le cerveau) reliée au quadrant réduit 2 x 2
par la carte de banc. Le bus, le cycle de mesure, la FFT, le
comparateur, la calibration et la CLI sont identiques ; ce qui change
vient de `board.h` et des constantes générées dans `board_pins.h` :

| | cerveau (`make`) | banc (`make NUCLEO=1`) |
|---|---|---|
| Quadrants | 4, de 16 bobines | 1, de 4 bobines (`plateau.quadrant.reduced`) |
| Console | USART1, PA9 et PA10, à travers l'ADuM1201 | USART2, PA2 et PA3, port série virtuel de la sonde ST-Link (`bench.console` du yaml) |
| Convertisseurs | ADC1 à ADC4 | ADC1 seul (PA0, comparateur COMP3 inchangé) |
| Chaîne LED | 128, quatre quadrants en série | 8, ordre du 2 x 2 (`NUCLEO_LED_CHAIN_SQ`) |
| Cases dans le CSV | a1 à h8 | a1, b1, a2, b2, soit 0, 1, 8, 9 |
| Commandes `2` à `4` | balayent un quadrant | refusées avec un commentaire |
| Sortie | `build/board.bin` | `build/nucleo/board-nucleo.bin` |

Un quadrant 4 x 4 complet se branche sur le même shield (même nappe,
même brochage, MUX_EN_H compris) : `make NUCLEO=1 NUCLEO_FULL=1` garde
tout ce qui précède et prend seize bobines par quadrant et la chaîne de
32 LED d'un quadrant posé à l'origine (`NUCLEO_FULL_LED_CHAIN_SQ`,
généré du même yaml), sortie `build/nucleo-full/board-nucleo-full.bin`.
Budget du banc et précaution sur les LED dans la
[note 19](../../docs/notes/19-cerveau-et-banc-nucleo.md), section 5.

Câblage du quadrant sur la Nucleo-64 : le bus du cerveau
(`plateau.brain.mcu_pins`) tombe sur l'embase Arduino, à une exception
près, DAMP_EN_N, dont le PC2 du cerveau n'atteint qu'un connecteur
Morpho : la variante le prend sur D6 (section `bench.signals` du yaml,
appliquée par `board.h`), ce qui permet une carte de banc sans
connecteur Morpho (`hardware/bench/`).

| Signal de la nappe | Broche | Sur la Nucleo |
|---|---|---|
| AMP_OUT | PA0 | A0 |
| PULSE_EN | PA4 | A2 |
| MUX_A0, MUX_A1, MUX_A2 | PB3, PB5, PB4 | D3, D4, D5 |
| MUX_EN_L | PC0 | A5 |
| MUX_EN_H | PC1 | A4 |
| DAMP_EN_N | PB10 (PC2 sur le cerveau) | D6 |
| LED_DIN | PA5 | D13 |
| 3V3, GND | | 3V3 et GND de la Nucleo |
| 5VA, 5V_LED, VIN | | la carte de banc (LDO 5 V, rail LED, jack 12 V) |

Flasher : copier `board-nucleo.bin` sur le lecteur NUCLEO, ou
`st-flash write build/nucleo/board-nucleo.bin 0x8000000`. Console : le
port série de la sonde, 115200 bauds, commande `h`. Deux broches ont
une seconde vie sur la Nucleo : PC13 (LED_STAT1 du cerveau) est le
bouton B1, PA5 (LED_DIN) la LED verte LD2 ; les LED d'état ne sont pas
pilotées par cette version et LD2 clignote au rythme des trames LED,
sans conséquence.
