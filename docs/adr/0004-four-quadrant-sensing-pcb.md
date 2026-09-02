# ADR 0004. PCB de détection découpé en 4 quadrants

Statut : acceptée, amendée par l'ADR 0010 (frontal analogique embarqué sur le quadrant en face supérieure, ailes de capture portées par la base chariot optionnelle).

## Contexte

Un PCB monobloc de 42 x 42 cm (p = 50) sort des paliers tarifaires
standard (250 à 350 EUR). Un signal de quelques centaines de µV ne
doit pas courir sur 40 cm de carte au milieu des rails numériques.

## Décision

Quatre quadrants identiques de 4 x 4 cases (21 x 21 cm à p = 50,
17 x 17 cm à p = 40), 80 à 120 EUR le jeu. Chaque quadrant embarque
16 bobines de case (spirales gravées sur 4 couches en série, ~15 à
20 µH, non résonantes), son multiplexage, son préampli différentiel et
son passe-bande d'ordre 4. Les 4 sorties attaquent en parallèle 4 ADC
du STM32G474 : scan complet en 8 ms, 128 ms avec moyennage x16.

## Conséquences

- Remplacement unitaire, montage progressif, mesure au plus près de la
  bobine.
- La résonance parasite bobine + capacité de mux (40 pF) reste une
  décade au-dessus de la bande utile (~6 MHz, vérifié par
  `pcb_sense_coil` et son test).
- Point ouvert hérité de la lecture critique (A) : 2 x ADG708 par
  quadrant ne suffisent qu'en single-ended ; le différentiel vrai
  demande 4 x ADG708 ou 2 x ADG726. La maquette (4 bobines sur un
  ADG708, différentiel vrai câblé, cavalier pseudo-différentiel)
  tranche via la mesure 8 avant de figer le schéma quadrant.
- Les bobines non sélectionnées sont court-circuitées à la masse des
  deux extrémités, pas laissées flottantes (`mux.idle_coil_policy`).
