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
