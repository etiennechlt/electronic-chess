# ADR 0003. STM32 maître, Raspberry Pi optionnel

Statut : acceptée.

## Contexte

Le plateau doit être pleinement fonctionnel en mode nomade sur
batterie : partie humain contre humain, arbitrage, détection,
déplacement. Le moteur d'échecs et la connectivité en ligne sont des
fonctions additionnelles. Faire cohabiter une capture à la
microseconde avec une pile WiFi sur le même processeur est une source
de complexité et de bruit.

## Décision

Un STM32G474 (170 MHz, FPU, 5 ADC, CMSIS-DSP, comparateurs et timers
pour la voie B) est le maître du système : scan LC, calibration,
arbitrage, machine à états d'interlock, portique, gestion d'énergie.
Le Pi Zero 2 W n'est alimenté, via un load switch piloté par le STM32,
que pour le moteur d'échecs, l'API Lichess et l'interface riche.
Liaison UART isolée (ADuM1201) avec un protocole simple à base de FEN
et de commandes de coup.

## Conséquences

- Le firmware STM32 porte tout le temps réel et toute la logique de
  jeu ; le Pi est un périphérique remplaçable.
- Trois règles firmware obligatoires : réserve d'énergie avant
  d'engager un coup, extinction propre du Pi (ordre, heartbeat,
  coupure), rootfs du Pi en lecture seule (overlayfs).
- Le mode nomade doit signaler les coups illégaux sans le TFT : la
  lecture critique (point G) ajoute buzzer et LEDs d'état au budget.
- Si la voie B d'extraction l'emporte (ADR 0007), le choix du MCU
  redevient libre ; la séparation STM32 / Pi reste valable.
