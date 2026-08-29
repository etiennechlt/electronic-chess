# Firmware de maquette (NUCLEO-G474RE)

Firmware CMSIS nu, sans HAL, pour la maquette 2 x 2. Les deux voies
d'extraction de fréquence du brief (5.2) tournent en permanence côte à
côte : chaque mesure produit `fa` (voie A, ADC 3,78 Méch/s + FFT 512
points + interpolation parabolique) et `fb` (voie B, comparateur COMP1
à hystérésis contre un seuil DAC3 interne, capture de période TIM2 à
170 MHz, médiane sur les premières périodes). Le notebook d'analyse
compare les deux colonnes sur les mêmes ringdowns.

## Construction

```bash
make            # produit build/mockup.bin (arm-none-eabi-gcc)
make pins       # regénère src/board_pins.h depuis config/board.yaml
make flash      # rappelle la procédure (copie sur le lecteur NUCLEO)
```

Les en-têtes CMSIS de ST et ARM sont embarqués dans `vendor/` avec
leurs licences (Apache 2.0). La FFT est autonome (pas de CMSIS-DSP) :
plus lente que la version optimisée mais sans dépendance, ce qui est
sans enjeu sur la maquette.

## Utilisation

Console sur le port série ST-Link (VCP), 921600 bauds. Commande `h`
pour l'aide. Sortie CSV : `sq,fa_hz,fb_hz,amp_mv,snr_db10`.

- `s` : un scan des 4 cases ; `m` / `x` : scan répété marche/arrêt.
- `c` : passe de calibration (16 mesures par case, moyennes stockées
  dans la dernière page de flash avec CRC).
- `i` : identification au plus proche voisin contre la calibration.
- `r` : dump brut des 512 échantillons ADC de la case 1.
- `p` / `P` : ajuste la durée d'impulsion d'excitation par pas de 100 ns.

## Séquence de mesure (par case)

1. Toutes les bobines amorties (DAMPk_N bas), sélection du mux.
2. Libération de l'amortisseur de la case visée, rail d'impulsion armé.
3. Impulsion de courant large bande (1 µs par défaut) puis flyback
   dans l'écrêteur.
4. Blanking 2 µs par amortissement actif, puis écoute.
5. Acquisition simultanée ADC (512 points) et captures comparateur.
6. Ré-amortissement, FFT et médiane de période, ligne CSV.

## Points à vérifier au premier démarrage

- Le code TISEL de TIM2 (TI4 = COMP1) et le code INMSEL de COMP1
  (DAC3_CH1) suivent le RM0440 ; vérifier au générateur de fonctions
  sur AMP_OUT avant de faire confiance à la voie B.
- La fréquence ADC réelle est 3,78 Méch/s (56,67 MHz / 15 cycles), le
  bandeau de démarrage l'affiche ; le 4 Méch/s du brief est le plafond
  du convertisseur.
