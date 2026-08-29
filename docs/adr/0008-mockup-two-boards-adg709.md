# ADR 0008. Maquette en deux cartes, mux différentiel, excitation hors mux

Statut : acceptée.

## Contexte

Le brief demandait une maquette monocarte 100 x 100 mm avec « 1 x
ADG708, voies inactives à la masse ». Trois problèmes concrets sont
apparus à la conception détaillée :

1. Un ADG708 est un multiplexeur 8 vers 1 simple : il ne route qu'un
   signal à la fois et ne peut donc pas faire de la mesure
   différentielle de 4 bobines (2 bornes simultanées par bobine).
2. L'excitation ne peut pas traverser le multiplexeur : le front de
   0,5 a 1 A dépasse d'un ordre de grandeur le courant admissible d'un
   mux analogique (~30 mA), et le front de 12 V violerait ses tensions
   absolues.
3. Loger 4 spirales de ø 40 mm, le buck, le frontal analogique et les
   connecteurs sur 100 x 100 mm placerait le convertisseur à découpage
   au milieu de la zone de mesure, ce que la maquette est censée
   caractériser, pas subir.

## Décision

- **Deux cartes.** Une carte bobines 100 x 100 mm, 4 couches,
  intégralement générée par script (spirales, connecteur, trous de
  fixation, support d'aimant sous la case 1), et une carte analogique
  2 couches au format shield Nucleo-64, jointes bord à bord par une
  barrette rigide 1 x 10 (GND, A1..B4, GND). La carte analogique se
  branche sur une Nucleo-G474RE : MCU, alimentation 3,3 V, VCP USB
  pour la sortie CSV, sans MCU à souder.
- **Mux différentiel double 4 vers 1** : retenu 74HCT4052 (seuils
  d'entrée TTL, indispensables avec un MCU 3,3 V sur un mux alimenté
  en 5 V ; Ron ~70 ohms négligeable devant l'entrée haute impédance de
  l'INA, bruit thermique 1,5 nV/racine(Hz)). L'ADG709 (4 ohms) reste
  l'alternative directe au même brochage fonctionnel. Pour le quadrant
  4 x 4 de la phase 2, l'équivalent est un ADG726 (double 16 vers 1),
  un seul boîtier par quadrant : ceci remplace le « 2 x ADG708 » de la
  BOM du brief et résout la contradiction relevée en lecture critique
  (point A).
- **Excitation par FET dédié par bobine**, hors mux : un commutateur
  haut partagé (AO3401) applique le rail 12 V via 10 ohms, un AO3400
  bas par bobine ferme le circuit pendant l'impulsion, une diode de
  bus B5819W isole les bobines au repos et une Schottky SS34 par
  bobine écrête le flyback vers le rail.
- **Amortissement par P-FET AO3401 et 680 ohms par bobine** (grille
  tirée à VIN, commande 3,3 V active à l'état bas) : amortissement
  proche du critique du ringing parasite pendant le blanking, et
  charge des bobines non sélectionnées ; la variante 0 ohm redonne le
  court-circuit franc du brief (politique `shorted`), a comparer en
  mesure 5.
- **Protection du chemin de mesure** : 330 ohms série et BAV99 vers
  les rails devant chaque entrée mux, ce qui borne la contribution en
  bruit à ~3,3 nV/racine(Hz) contre 3 nV pour l'AD8421.
- **Chaîne de gain** : AD8421 G = 20 (BW ~1,4 MHz), deux étages
  Sallen-Key Butterworth à composants égaux (passe-haut 200 kHz,
  passe-bas 650 kHz, K = 1,59), étage de sortie x4,57 compensant
  l'affaissement mi-bande : ~200 à 400 kHz, validé ngspice. La
  polarisation générale est à 1,65 V pour rester dans la fenêtre du
  MCU 3,3 V. Réjection réelle à 1,5 MHz : ~18 dB (le 32 dB du brief
  supposait la pente d'un passe-bas d'ordre 4, voir la doc de la
  carte).

## Conséquences

- La carte bobines est un livrable paramétrique : la variante p = 40
  se régénère par script pour quelques euros.
- La carte analogique est réutilisable telle quelle pour toutes les
  variantes de carte bobines et préfigure le préampli de quadrant.
- Le brief est amendé sur la référence du mux ; l'ADR 0004 reste
  valable sur le fond (attaque différentielle), la référence exacte
  devient ADG709 (maquette) et ADG726 (quadrant).
- Toutes les valeurs sont dans `config/board.yaml`, section `mockup`.
