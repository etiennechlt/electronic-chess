# ADR 0002. Aimant de pièce en ferrite dure, jamais en néodyme

Statut : acceptée.

## Contexte

L'aimant de déplacement et la bobine d'identification cohabitent dans
la même base de pièce, empilés coaxialement. Un aimant NdFeB est
conducteur (résistivité ~1,4 µΩ·m, profondeur de peau ~0,9 mm à
400 kHz) : les courants de Foucault feraient chuter le Q du résonateur
de 40 à 70 %, ce qui ruinerait la discrimination.

## Décision

Aimant de pièce en ferrite dure (SrFe) : isolant (10^4 à 10^8 Ω·m),
courants de Foucault nuls, transparent au champ alternatif de mesure.
Le Br trois fois plus faible que le néodyme (0,4 T contre 1,3 T) est
compensé par le volume, avec une marge d'un ordre de grandeur sur la
force requise (0,3 à 0,5 N verticaux suffisent).

L'aimant du chariot, hors de la pièce et sous le PCB, reste en NdFeB
N42 (ø 15 x 5 mm).

## Conséquences

- L'empilement bobine en bas, aimant au-dessus sacrifie 2 mm d'entrefer
  sur la force (marge large) et rien sur la mesure (signal faible).
- La perméabilité de recul de la ferrite dure (µr ~1,05 à 1,1) décale
  légèrement L ; le décalage est absorbé par la calibration par pièce.
- La mesure 2 du protocole (chute de Q ≤ 20 % avec ferrite posée) est
  le critère de validation ; la mesure 3 (néodyme, à titre de
  comparaison) quantifie ce que la décision évite.
- La mesure 7 (N42 du chariot approché par dessous) dimensionne la
  distance de parking, la rémanence n'étant un sujet que pour l'option
  électroaimant (décision 5.3 du brief, à arbitrer sur la maquette).
