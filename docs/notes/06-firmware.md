# 06. Firmware : mesure, calibration, LED

`firmware/mockup/` : CMSIS nu, pas de HAL, lieur et startup écrits
main, compile en CI (arm-none-eabi-gcc). Cible : Nucleo-G474RE,
câblée à la carte analogique par le connecteur MCU (table Dupont dans
`hardware/mockup-2x2/README.md`).

## Chaîne de mesure

- Horloge à 170 MHz (`clock.c`), compteur de cycles DWT activé.
- Séquence d'une mesure (`measure.c`) : sélection de la case (mux),
  impulsion d'excitation (durée réglable par CLI), blanking
  d'amortissement, puis acquisition.
- **Voie A** : ADC à 3,78 Méch/s (56,67 MHz, 15 cycles), rafale de
  512 échantillons en DMA, FFT radix-2 maison avec fenêtre de Hann et
  interpolation parabolique du pic (`fft.c`). Le Q spectral à 512
  points ne résout pas au delà de ~15 : c'est documenté, la méthode
  d'enveloppe du protocole reste la référence pour Q.
- **Voie B** : COMP1 avec seuil DAC3, période capturée par TIM2 (TISEL
  TI4). Chaque scan sort fa (FFT), fb (période), amplitude et SNR :
  les deux voies sont départagées par la mesure M9, pas par avance.
- Calibration (`calib.c`) : page flash dédiée (2 Ko), CRC32, moyenne
  de 16 mesures par case ; classification au plus proche voisin.

## LED de camp (ADR 0009)

- TIM2 appartient à la capture de période, donc pas de PWM DMA sur
  PA5 : les trames WS2812 sont générées en bit-bang cycle-exact sur
  DWT->CYCCNT (`led.c`), interruptions masquées ~250 µs par trame,
  latch ligne basse ensuite.
- Le fenêtrage anti-bruit est structurel : la boucle est mono-tâche et
  `measure_square()` est synchrone, une trame ne peut donc jamais
  partir pendant une mesure. La mesure M11 le vérifie.
- L'ordre de chaîne (case par position) et les couleurs des camps sont
  générés depuis le yaml dans `board_pins.h` (`make pins`).

## CLI (VCP ST-Link, 921600 bauds, CSV)

| Touche | Action |
|---|---|
| `h` | aide |
| `s` | un scan des 4 cases (CSV : sq, fa, fb, amp, snr) |
| `m` / `x` | scan répété marche / arrêt |
| `1`..`4` | scan d'une case |
| `c` | calibration (16 mesures par case, flash) |
| `i` | identification au plus proche voisin |
| `r` | dump brut 512 échantillons de la case 1 |
| `p` / `P` | impulsion d'excitation -100 / +100 ns |
| `l` | identifier et allumer les LED (démo : classes 1-2 camp blanc, 3-4 camp noir) |
| `o` | LED éteintes |

## Points d'attention pour la suite

- La correspondance pièce vers camp est une démo (parité de classe) :
  la vraie affectation viendra avec la calibration étendue (couleur
  stockée par pièce).
- `board_pins.h` est généré mais commité (make sans Python possible) :
  après toute édition du yaml, `make pins` puis commit.
- Le lieur définit explicitement `.ARM.exidx` et `_etext` : ne pas
  simplifier ces sections, l'écrasement data/exidx a déjà mordu.
