# ADR 0007. Extraction de fréquence : FFT et capture de période

Statut : ouverte, les deux voies implémentées et comparées sur maquette.

## Contexte

La classification repose sur la mesure de la fréquence propre du
ringdown (résolution visée ~1 kHz pour des espacements de 20 à
53 kHz). Deux approches crédibles, aux compromis opposés.

## Décision

Le firmware de maquette implémente les deux voies derrière un switch
de compilation :

- Voie A, ADC + FFT : 4 Msps, 512 points, FFT réelle CMSIS-DSP,
  interpolation parabolique du pic. Résolution brute 7,8 kHz, ~1 kHz
  après interpolation. ~500 µs par case, budget vérifié.
- Voie B, comparateur + capture de période : comparateur à hystérésis
  puis input capture. À 170 MHz sur 400 kHz, 425 comptes par période,
  0,05 % moyenné sur 20 périodes, cinq à dix fois mieux que la FFT
  sans ADC rapide. Contraintes : seuil sur amplitude décroissante,
  capture limitée aux premières périodes, rejet des faibles SNR.

## Conséquences

- Si la voie B passe, le choix du MCU devient libre (un ESP32-S3
  pourrait suffire) ; la voie A reste utile en diagnostic car elle
  seule voit un spectre complet (double résonance d'une pièce voisine,
  perturbateur externe).
- La sortie CSV sur UART du firmware de maquette livre les deux
  mesures côte à côte pour le notebook d'analyse.
- Décision au vu des mesures 4 et 6 du protocole.
