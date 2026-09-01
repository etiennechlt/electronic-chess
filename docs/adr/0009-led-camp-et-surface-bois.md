# 0009. LED de camp par case et surface en bois

Date : 2026-09-01. Statut : accepté.

## Contexte

Chaque case doit indiquer visuellement quel camp (blanc ou noir) a
posé la pièce détectée, par deux petits points lumineux aux coins de
la case. Par ailleurs la surface de jeu passe de l'acrylique au bois
(préférence d'aspect), ce qui pose la question de l'effet sur la
mesure de fréquence.

## Décision

### LED

Deux WS2812B (5050, paire symbole plus empreinte officielle KiCad,
brochage vérifié : 1 VDD, 2 DOUT, 3 VSS, 4 DIN) par case, aux deux
coins opposés, en retrait `leds.corner_inset_mm` des bords de case,
hors du cercle des spirales. La case 2 utilise la diagonale NE-SO,
son coin NO tombant sous la rangée du connecteur commun. Une seule
ligne de données chaînée dessert tout le plateau (extensible telle
quelle au 8 x 8, 128 LED), ordre de chaîne dans
`mockup.coil_board.leds.chain_squares` (yaml, partagé par le
générateur de carte et le firmware).

Sur la carte bobines : données sur In1.Cu dans les couloirs entre
spirales, boucle 5V sur In2.Cu (seule équipotentielle de la couche,
esquives locales des empilements de terminaux et de la rangée de
pads), masse en face arrière (boucle, épine centrale, éperons choisis
par un solveur gardé). Chaque LED a son 100 nF avec sa propre paire de
vias. Une garde géométrique au build valide tout le cuivre LED contre
spirales (rayon r_out atteint par les arcs de liaison), terminaux,
barillets du connecteur et bord de carte, à tout pas p.

Sur la carte analogique : le connecteur commun passe à 12 broches
(données et 5V en bout, position calculée du yaml des deux côtés), un
tampon 74AHCT1G125 à seuils TTL monte la donnée 3,3 V du MCU à 5 V
(même astuce de seuils que le mux), alimenté par le rail buck
numérique, jamais par 5VA : l'île analogique reste intouchée. 470R en
série à la source, 100 nF au tampon. Broche MCU : D13 (PA5), une des
trois masses du connecteur MCU réaffectée.

### Bruit

Les rafales de données WS2812 à 800 kHz tombent en pleine bande de
mesure (200 à 650 kHz). Le fenêtrage est structurel : le firmware est
une boucle mono-tâche, `measure_square()` est synchrone, donc une
trame LED ne peut partir qu'entre deux mesures. Au repos la ligne est
statique ; le PWM interne des WS2812 est en kilohertz, hors bande,
rejeté par le passe-bande. TIM2 appartenant à la capture de période,
la trame est générée en bit-bang cycle-exact sur DWT->CYCCNT à
170 MHz, interruptions masquées ~250 µs.

### Surface en bois

Contreplaqué sec, épaisseur paramétrée par `gap.surface_mm`, sans
agrafes ni éléments métalliques. Effet sur la mesure : aucun sur la
fréquence en pratique (matériau amagnétique et isolant, capacités
parasites au niveau du picofarad contre des nanofarads de résonateur,
soit des parties par million, absorbées par la calibration par
pièce) ; les deux effets réels sont l'épaisseur (chute d'amplitude du
ringdown avec l'entrefer, recalculée par `chessboard_calc.coupling`)
et l'humidité (pertes diélectriques, légère baisse de Q, bois sec
recommandé). Une mesure comparative acrylique contre bois est au
protocole. La lumière des LED passe par deux perçages de
`leds.light_hole_d_mm` par case au droit des coins équipés (gabarit
de perçage généré : `mechanical`, pièce `surface-template`),
remplissage époxy translucide en option.

## Conséquences

- Le connecteur commun 10 broches devient 12 : cartes bobines et
  analogique regénérées ensemble, le test d'égalité des plans de pads
  verrouille l'alignement.
- La carte bobines n'est plus purement passive : 8 LED, 8
  condensateurs, 48 vias de distribution.
- Consommation : jusqu'à ~0,5 A si tout est au blanc plein, sur le
  rail buck ; l'usage indicateur réel est de l'ordre de 50 mA.
- Commandes CLI `l` (identifier et allumer, démo : classes 1 et 2 au
  camp blanc, 3 et 4 au camp noir) et `o` (extinction) ; l'affectation
  réelle pièce vers camp viendra avec la calibration étendue.
