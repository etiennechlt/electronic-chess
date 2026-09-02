# 10. Plateau 8 x 8, base interchangeable et horloge : les choix et leurs raisons

Cette note déroule la discussion du 02/09/2026 qui a conduit à
l'[ADR 0010](../adr/0010-plateau-8x8-base-interchangeable-horloge.md).
L'ADR liste les décisions ; ici on garde le raisonnement, les chiffres
et les alternatives écartées, pour ne pas les rediscuter dans six mois.
Les cotes citées viennent de `config/board.yaml` (sections `plateau`,
`clock`, `gap`, `power`) et sont épinglées par `tests/test_plateau.py`.

## 1. Pourquoi abandonner la maquette 2 x 2

Le point de départ était d'ouvrir les cartes de la maquette dans KiCad
et de se demander s'il suffisait d'en imprimer plusieurs pour faire un
plateau. Trois faits ont tranché :

- un 8 x 8 fait 64 cases, soit seize tuiles 2 x 2, pas huit ;
- la carte analogique de maquette est câblée pour quatre bobines
  exactement (mux 74HCT4052 double 4 vers 1, quatre lignes DRIVE et
  DAMP, un seul connecteur) et ne peut piloter ni huit ni seize
  tuiles ;
- le connecteur de bord et le support d'aimant sous S1 empêchent de
  poser des tuiles bord à bord.

L'ADR 0004 prévoyait déjà quatre quadrants 4 x 4. Le choix du porteur
a été d'y aller directement plutôt que d'entretenir deux versions : le
quadrant est à la fois le module définitif et le banc de mesure (un
quadrant plus le cerveau suffisent pour M1 à M11). Le coût d'une
erreur de pas est une commande de cinq quadrants 4 couches, de l'ordre
de 40 à 80 USD.

## 2. Le pas p = 50 mm

Le rapport `python -m chessboard_calc report` donne, pour le pion noir
(pire cas, bas de bande, plus petite bobine) :

| | p = 40 | p = 50 |
|---|---|---|
| Signal relatif | 0,70 | 1,00 |
| Q estimé du pion noir | 13 | 33 |
| Plancher `resonator.q_min_with_magnet` | 30 | 30 |
| Marge de couloir, tour contre tour | 2,0 mm | 2,5 mm |
| Quadrant | 160 x 160 mm | 200 x 200 mm |
| Aire de jeu | 320 mm | 400 mm |

À p = 40, le pion passe sous le plancher de Q avant la première
mesure. Le format 50 est aussi celui des plateaux de tournoi (cases de
50 à 57 mm), plus confortable que les 40 mm environ des plateaux
capteurs du commerce. Le yaml garde les deux candidats : le rapport et
les tests de bobinage continuent de les comparer.

## 3. Trois architectures comparées

| Option | Verdict | Raison |
|---|---|---|
| Seize tuiles 2 x 2 | non | électronique 4 voies, mécanique des connecteurs, seize nappes |
| Une carte 8 x 8 de 42 cm | non | hors paliers tarifaires 4 couches, signal en microvolts sur 40 cm, pas de remplacement unitaire |
| Quatre quadrants intelligents plus un cerveau | oui | un seul design de quadrant, préampli au plus près des bobines, quatre ADC en parallèle |
| Quadrants passifs et frontal centralisé | non | 32 lignes de microvolts par quadrant sur 20 cm de nappe avant amplification |

Le quadrant embarque : ADG726 (double 16 vers 1, un boîtier), FET
d'excitation par bobine derrière un décodeur 4 vers 16 (environ 50
SOT-23, l'excitation ne peut pas traverser un mux analogique, voir
ADR 0008), chaîne AD8421 G = 20 plus deux Sallen-Key reprise telle
quelle, protection 330R plus BAV99. La liaison vers le cerveau est une
nappe IDC 2 x 10 par quadrant : 5VA, AGND, 3V3, 5V LED, GND, sortie
analogique, adresses de mux et d'excitation, PULSE_EN, DAMP, LED_DIN,
LED_DOUT. Le brochage exact sera fixé dans le yaml avec le générateur
de quadrant.

## 4. LED identiques partout

Sur la maquette, la case S2 utilisait la diagonale NE-SO parce que son
coin NO tombait sous la rangée de plots du connecteur. Le quadrant n'a
plus de connecteur dans un coin ; toutes les cases prennent NO-SE, en
retrait de 4,5 mm des bords. Les 128 positions sont calculées une
seule fois (`chessboard_calc.plateau.led_points`) pour le générateur de
carte, le gabarit de perçage et les modèles 3D, ce qui supprime la
table de coins dupliquée entre `coilgen` et `mechanical/parts.py` de la
maquette. La variante à 81 LED partagées aux sommets est écartée : un
sommet touche quatre cases, l'indication de camp devient ambiguë.

## 5. Module plateau et bases interchangeables

Le module plateau est l'invariant : contreplaqué de 3 mm avec ses 128
points lumineux et les quatre quadrants en dessous, 420 x 420 mm avec
une bordure de 10 mm, 6,6 mm d'épaisseur. Il se pose dans l'une des
deux bases sur quatre pions de centrage de 4 mm, et s'y relie par les
quatre nappes.

| | Base fine | Base chariot |
|---|---|---|
| Emprise | 420 x 420 mm | 520 x 440 mm |
| Hauteur totale | 21 mm | 54 mm |
| Coque | 2 mm | 2 mm |
| Cavité électronique | 12 mm | 12 mm, au fond |
| Cavité CoreXY | aucune | 33 mm |
| Ailes de capture | aucune | 2 x 50 mm, affleurantes |
| Lisière arrière | aucune | 20 mm (marge y du portique) |

Règles qui rendent l'échange possible :

- **le dessous des quadrants reste vierge**, le chariot y passe à
  moins d'un millimètre ;
- **l'électronique vit au fond de la base**, sur une empreinte de
  fixation identique dans les deux bases ; changer de base, c'est
  débrancher quatre nappes et déplacer trois cartes ;
- **les ailes appartiennent à la base chariot**, pas au module : le
  plateau fin reste un carré de 42 cm ; dans la base chariot, la pièce
  glisse du bois sur l'aile à travers un joint sans lèvre (0,3 mm au
  plus), et l'aimant la porte à travers l'aile comme à travers le bois ;
- **les pions de centrage fixent le repère du chariot** : les fins de
  course se calent sur la base, la base se cale sur le module.

Le bandeau arrière de 30 mm envisagé pour loger un pack 18650 a été
refusé pour l'esthétique ; d'où les cellules plates (section 7).

## 6. Critique du chariot, et pourquoi il est optionnel

- **Coût matériel** : deux NEMA17, rails MGN9 de 400 et 500 mm,
  courroies GT2 et renvois, profilés 2020, deux TMC2209, fins de
  course, actionneur d'aimant : 150 à 220 EUR, soit le prix de toute
  la détection.
- **Épaisseur** : 33 mm de cavité en plus, le plateau passe de 21 à
  54 mm. C'est le coût esthétique majeur, et il est irréversible dans
  un meuble monobloc ; d'où la base clipsable.
- **Passage sous les bobines** : aimant à 6 mm de l'aimant de pièce,
  donc à moins d'un millimètre du PCB ; rien ne peut être sous les
  quadrants, et le frontal passe en face supérieure (section 8).
- **Détection** : scan coupé pendant les mouvements (interlock de
  l'ADR 0005) ; parking hors aire de jeu pour ne pas perturber
  l'aimant ferrite d'une pièce (mesure M7).
- **Précision** : courroies et re-zérotage à chaque coup contre les
  fins de course, budget de tolérance 0,8 mm ; le cadre doit être
  rigide sur 500 mm.
- **Force** : 0,3 à 0,5 N nécessaires, marge d'un ordre de grandeur
  avec le N42 sur ferrite (ADR 0002), à confirmer à travers 7,1 mm.

Un plateau capteur fin fonctionne sans rien de tout cela. On joue
d'abord sur la version fine ; la base chariot vient si l'envie tient.
Les pièces reçoivent leur aimant ferrite dès le départ parce qu'il ne
coûte rien et évite de refaire les pièces.

## 7. Batterie plate

| | 3S2P 18650 | 3S1P cellules plates |
|---|---|---|
| Énergie | 73,4 Wh | 55,5 Wh |
| Épaisseur | 18,5 mm, impose un bandeau | 8 mm, tient dans la cavité de 12 mm |
| Autonomie humain contre humain | 68 h | 51 h |
| Autonomie contre le moteur | 15 h | 11 h |

Une cinquantaine d'heures reste des semaines de parties. Charge par
USB-C PD sur la carte puissance, BMS 3S, jauge. Les 18650 ne
disparaissent pas du projet : l'horloge en emporte une.

## 8. Frontal sous le bois et entrefer d'air

Les WS2812B font 1,6 mm de haut sur le dessus des quadrants ; la
maquette ne comptait pas cet air dans l'entrefer. Il est désormais
explicite : `gap.air_mm` = 2 mm, dans lequel tiennent les LED et des
composants de 1,8 mm au plus (TSSOP, SOIC, 0603, LFCSP de l'ADG726).
L'entrefer nominal passe de 5,1 à 7,1 mm pour un maximum de 8, et le
modèle de signal en tient compte (`chessboard_calc.coupling`). Le
blindage du frontal se fait par plan de masse interne et ruban de
cuivre collé sous le contreplaqué, faute de hauteur pour un capot.

## 9. Cerveau, puissance, moteurs

Trois cartes, une feuille de schéma par bloc :

- **Cerveau** : STM32G474RE soudé (LQFP64, SWD, USB), quatre
  connecteurs de quadrant, chaîne LED, 5 V buck 2,2 MHz forced PWM,
  3,3 V, îlot analogique LDO plus filtre en pi, emplacement
  communication, prise USB-C périphérique, connecteur chariot.
- **Puissance** : BMS 3S, charge USB-C PD, jauge. Ce qui chauffe et
  peut brûler a sa carte.
- **Moteurs**, optionnelle, dans la base chariot : deux TMC2209, fins
  de course, actionneur d'aimant, nappe vers le cerveau.

Pourquoi souder le MCU plutôt que garder une Nucleo : la Nucleo apporte
gratuitement le quartz, l'USB, le régulateur et la sonde ST-Link, mais
c'est une carte fille de 7 cm dressée dans un plateau de 21 mm. Souder
le G474 demande d'ajouter tout cela et une sonde à part (ST-Link V3
mini, 10 à 30 EUR) ; en échange une seule carte plate, et pas de
seconde version. Le G474 sait faire la voie A (ADC plus FFT) et la
voie B (comparateur plus capture), donc le choix du MCU ne dépend pas
du verdict de l'ADR 0007.

## 10. Communication : ESP32-S3, Pi, Lichess

L'ADR 0003 prévoyait un Pi Zero 2 W derrière une UART isolée et un
load switch. On généralise en un emplacement communication sur le
cerveau : une empreinte de module ESP32-S3 (WiFi et BLE, environ
3 EUR, suffisant pour l'API Board de Lichess et pour parler à
l'horloge) et une embase Pi pour un moteur d'échecs local, sur la même
interface (UART isolée ADuM1201, 5 V commuté, même protocole FEN).
L'ESP32-S3 passe d'option à équipement de base parce que l'horloge en
dépend. Côté services : Lichess a une API Board publique faite pour
les plateaux physiques ; chess.com n'a qu'une API de lecture, les
plateaux du commerce y accèdent via leur application partenaire. Pour
un plateau maison, chess.com est au mieux une passerelle non
officielle, à considérer comme non garantie.

Le module radio se place au fond de la base, loin des bandes de
frontal des quadrants, et son rail est coupé pendant les scans : c'est
le plan anti-bruit de l'ADR 0005 appliqué tel quel. Le WiFi à 2,4 GHz
est très loin de la bande 200 à 650 kHz ; ce sont les rafales de
courant du module qui sont surveillées, pas la porteuse.

## 11. Horloge à bascule

Le plateau doit fonctionner sans elle ; elle est donc un module
autonome, posé à côté comme une pendule de compétition :

- boîtier imprimé 120 x 70 mm, parois 2 mm, fond vissé ; face avant
  inclinée de 26 à 36 mm de haut sur 42 mm, arrière plat ;
- barre à bascule de 108 x 18 mm sur pivot central de 4 mm, dans un
  évidement de 5 mm, course de 5 degrés, un microrupteur sous chaque
  extrémité à 12 mm du bout ; appuyer d'un côté lance le temps de
  l'autre ; la barre reste en position comme sur une pendule mécanique ;
- écran 2,4 pouces IPS (fenêtre 50 x 38 mm) face aux joueurs, gros
  chiffres ; encodeur rotatif à poussoir à l'avant droit pour les
  menus (mode de jeu, cadence, niveau du moteur, connexion Lichess) ;
  grille de buzzer à l'avant gauche ; fente USB-C à l'arrière ;
- ESP32-C3 (BLE, faible consommation), une 18650 1S de 3 Ah couchée en
  travers, chargeur USB-C. Des semaines d'autonomie en usage pendule.

La logique d'horloge et des menus vit dans l'ESP32-C3 ; le STM32 du
plateau reste maître de la partie et de l'arbitrage, l'ESP32-S3 n'est
qu'un pont radio. Les boutons séparés (première version) ont été
remplacés par la barre à la demande du porteur.

## 12. Outillage retenu

Priorités, avec des ordres de prix relevés de mémoire de marché, à
confirmer au panier :

| Outil | Pourquoi | Ordre de prix |
|---|---|---|
| Oscilloscope 2 voies, 25 MHz et 100 Méch/s minimum, mémoire 1 M points | ringdown à 200 à 650 kHz, blanking de 2 µs, fronts d'excitation | Hantek 6022BE USB 55 à 70 EUR (OpenHantek6022 sous Debian) ; Hantek DSO2C10 150 à 170 EUR ; Rigol DS1054Z d'occasion 250 EUR |
| Station fer plus air chaud | 0603, SOT-23, reprise du QFN du buck | 60 à 100 EUR |
| Multimètre | continuité, rails, courants | 40 à 90 EUR (UNI-T UT61E, Brymen BM235) |
| LCR-mètre | trier les bobines de 45 µH et les C0G | testeur LCR-T7 ou TC1 15 à 20 EUR (Amazon, AliExpress) ; DER EE DE-5000 100 à 120 EUR ; UNI-T UT612 80 EUR ; Peak LCR45 110 EUR (Farnell, Conrad) |
| Alimentation de labo 12 V à limitation de courant | premier allumage | 50 à 80 EUR |
| Sonde ST-Link V3 mini | flasher et déboguer le MCU soudé | 10 à 30 EUR |
| Analyseur logique USB | timing WS2812, UART, adresses de mux | 10 EUR |

Les scopes de poche à quelques mégaéchantillons par seconde (DSO150,
DSO-TC3) sont inutilisables ici. Un générateur de fonctions est utile
pour la voie B, le DAC du G474 le remplace au début.

KiCad 9 est conservé face à EasyEDA : dépôt natif KiCad (les
générateurs émettent son format et `kicad-cli` valide les cartes en
test), fichiers texte dans git, export BOM et CPL JLCPCB par le plugin
Fabrication Toolkit, import des empreintes LCSC par easyeda2kicad, et
surtout personne ne dessine seize spirales 4 couches à la main.

## 13. Méthode 3D

- `chessboard_calc/plateau.py` dérive toutes les cotes (empilements,
  emprises, points lumineux, gardes) sans dépendre de CadQuery, pour
  que les tests tournent en CI légère.
- `mechanical/plateau.py` et `mechanical/clock.py` construisent les
  solides ; chaque pièce est un `Part` (nom, forme, couleur, couche,
  facteur d'éclaté) partagé par les rendus et la vue interactive.
- `mechanical/render_stl.py` est passé d'un tri par peintre
  (matplotlib, faux sur les grands panneaux) à un rasteriseur à tampon
  de profondeur en numpy : occlusions exactes, ombrage plat, sur
  échantillonnage 2x. Une vue du plateau prend une trentaine de
  secondes.
- `mechanical/scenes.py` produit `docs/images/plateau-*.png` et
  `horloge*.png` ; `mechanical/viewer.py` génère
  `mechanical/exports/plateau-3d.html`, la vue interactive three.js
  (bases fine et chariot, éclaté, couches masquables, noms au survol,
  tables d'empilement et d'emprise), non commitée, régénérée à la
  demande ; `mechanical/build_all.py` exporte les STEP des assemblages
  et les STL de l'horloge. Sous Debian, `apt install freecad` ouvre
  les STEP ; KiCad 9 importe les STEP pour les cartes.

## 14. Ce qui reste

1. Générateur de quadrant : fait pour la couche de détection
   (`tools/quadgen`, [README](../../hardware/quadrant/README.md)) ;
   reste le frontal de la bande (cellules, mux, décodeurs, chaîne).
2. Schéma du cerveau généré depuis le yaml, placement à la main dans
   KiCad ; cartes puissance et moteurs.
3. Carte de l'horloge et son firmware ESP32-C3 ; protocole BLE
   plateau contre horloge.
4. Retrait progressif de la maquette 2 x 2 des docs de commande ; ses
   générateurs restent la référence de la chaîne analogique.
5. Mesures M1 à M11 sur un quadrant plus le cerveau.
