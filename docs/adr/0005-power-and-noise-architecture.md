# ADR 0005. Architecture d'alimentation et plan anti-bruit

Statut : acceptée.

## Contexte

La chaîne LC mesure des microvolts sur 64 bobines qui sont autant
d'antennes cadres, dans la bande 200 à 650 kHz. Le Pi (PMIC 1 à 2 MHz,
rafales WiFi), le buck principal et les choppers TMC2209 sont les
agresseurs identifiés. La batterie 3S2P 18650 (73,4 Wh) alimente le
rail moteur en direct et un seul buck descend en 5 V.

## Décision

Sept mesures, toutes obligatoires :

1. Buck 5 V à 2,2 MHz fixe, spread spectrum désactivé, et variante
   forced PWM imposée : en charge légère (0,9 W au repos), un mode
   éco/PFM émettrait des rafales de 1 à 100 kHz en pleine bande
   (lecture critique, B).
2. Îlot analogique : LDO dédié, filtre LC en pi, masse en un point.
3. Isolateur numérique ADuM1201 sur l'UART Pi / STM32.
4. Attaque différentielle des bobines + ampli d'instrumentation
   (topologie exacte tranchée par la maquette, voir ADR 0004).
5. Passe-bande d'ordre 4 sur 200 à 650 kHz.
6. Moyennage cohérent x16 (+12 dB de SNR, 2 ms par case).
7. Éloignement et blindage : Pi au coin opposé du frontal analogique,
   capot fer-blanc par préampli de quadrant.

Côté moteurs : TMC2209 en StealthChop, EN à l'état haut au repos, scan
coupé pendant les mouvements (machine à états d'interlock), chariot
parqué hors de l'aire de jeu pendant les scans, parking en appui sur
les fins de course pour re-zéroter à chaque coup (lecture critique, H).

## Conséquences

- Le modèle de puissance porte un terme fixe de conversion
  (`fixed_overhead_w`) qui réconcilie le total de 0,9 W au repos du
  brief, dont les postes seuls ne sommaient qu'à 0,5 W.
- Autonomie calculée : ~68 h en humain contre humain, ~15 h contre le
  moteur, crête ~1,1 A ; jauge par tension acceptable avec la réserve
  de mouvement de 10 %.
- La mesure 8 du protocole (plancher de bruit Pi éteint / allumé /
  WiFi en émission, delta ≤ 6 dB) valide l'ensemble.
