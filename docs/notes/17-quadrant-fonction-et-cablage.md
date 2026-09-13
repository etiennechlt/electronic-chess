# 17. Quadrant : la fonction, les composants et leur câblage

Cette note est la description fonctionnelle que le schéma du quadrant
doit suivre, bloc par bloc, avant d'être redessiné puis rerouté. Elle
part du circuit tel que le générateur le décrit
(`tools/quadgen/circuit.py`), des valeurs de `config/board.yaml`
(sections `plateau.quadrant`, `mockup.analog`, `mockup.drive`,
`measurement`) et de la séquence du firmware du cerveau
(`firmware/board/src/measure.c`). Le premier objectif est un quadrant
réduit à 2 x 2 cases, même architecture, pour valider la méthode de
dessin avant le 4 x 4.

## 0. Ce qu'on voit aujourd'hui dans KiCad, et pourquoi

Le schéma généré est un schéma « par étiquettes » : chaque broche de
chaque composant porte un tronçon de 2,54 mm et une étiquette globale
au nom de son net, et aucun fil ne relie deux composants entre eux.
La connectivité est complète (la [note 14](14-revue-des-cartes.md) l'a
vérifiée en exportant la netlist avec `kicad-cli` et en la comparant
au circuit, `tests/test_schematics.py`), mais rien n'est lisible : on
ne voit ni la cellule d'une bobine, ni la chaîne d'amplification, ni
le sens des diodes par rapport au rail. C'est l'écart entre « juste »
et « compréhensible » que cette note et le schéma redessiné doivent
combler.

## 1. La fonction à réaliser

Le quadrant lit une case à la fois, sur ordre du cerveau, et lui rend
un seul signal analogique :

1. adresser une bobine parmi n² (16 en 4 x 4, 4 en 2 x 2) sur un bus
   commun de quatre bits ;
2. l'exciter par une impulsion de courant large bande depuis le rail
   12 V (1 µs, quelques centaines de mA, `measurement.drive`) ;
3. amortir activement la bobine pendant le blanking (2 µs) pour
   étouffer sa propre sonnerie ;
4. écouter le ringdown de la pièce à travers la même bobine, l'amplifier
   d'environ 230 fois et le filtrer dans la bande de 200 à 650 kHz ;
5. livrer ce signal sur `AMP_OUT`, centré sur 1,65 V, à l'ADC du cerveau
   qui fait la FFT et la décision ;
6. allumer les deux LED de camp de chaque case (chaîne WS2812B).

La liaison avec le cerveau est la nappe FPC 16 broches
(`plateau.quadrant.link.pinout`) :

| Broche | Net | Sens | Rôle |
|---|---|---|---|
| 1, 3 | GND | | masse |
| 2 | 5VA | entrée | rail analogique (mux, INA, ampli op) |
| 4 | AMP_OUT | sortie | signal amplifié et filtré vers l'ADC |
| 5 | 3V3 | entrée | logique (décodeurs, inverseur), écrêtage de sortie |
| 6, 8, 9 | MUX_A0, MUX_A1, MUX_A2 | entrée | adresse de bobine, bits 0 à 2 |
| 7 | LED_DIN | entrée | entrée de la chaîne LED |
| 10 | 5V_LED | entrée | alimentation des LED |
| 11 | MUX_EN_L | entrée | enable du mux des bobines 1 à 8 |
| 12 | MUX_EN_H | entrée | enable du mux des bobines 9 à 16, et bit 3 d'adresse des décodeurs |
| 13 | LED_DOUT | sortie | sortie de la chaîne LED vers le quadrant suivant |
| 14 | PULSE_EN | entrée | impulsion d'excitation, actif haut |
| 15 | DAMP_EN_N | entrée | amortissement, actif bas |
| 16 | VIN | entrée | 12 V du rail d'impulsion |

## 2. Le cycle d'une mesure

Séquence de `measure_coil()` dans le firmware du cerveau, pour une
bobine :

| Étape | Signaux | Durée | Ce qui se passe sur le quadrant |
|---|---|---|---|
| Adresser | MUX_A0..A2, MUX_EN_L ou MUX_EN_H, puis DAMP_EN_N bas | 2 µs | le mux relie la bobine à l'INA, le décodeur d'amortissement ferme le P-FET de la bobine, la chaîne se stabilise |
| Relâcher | DAMP_EN_N haut | 300 ns | la bobine est libre |
| Exciter | PULSE_EN haut | 1 µs | le rail 12 V est appliqué, le décodeur d'excitation ouvre le N-FET de la bobine adressée, le courant monte dans la spirale |
| Roue libre | PULSE_EN bas | 400 ns | le N-FET s'ouvre, la bobine écrête sur VIN par sa diode, le courant se recircule par le rail |
| Blanking | DAMP_EN_N bas | 2 µs | 680 ohms aux bornes de la bobine, sa sonnerie propre est étouffée |
| Écouter | DAMP_EN_N haut, ADC | 128 µs | 512 échantillons à 4 Méch/s (`measurement`), le ringdown de la pièce traverse le mux, l'INA et les filtres |
| Clore | DAMP_EN_N bas, enables bas | | bobine amortie, bus libéré |

Deux conséquences de câblage découlent de cette séquence : la porte
d'excitation ne doit pouvoir s'ouvrir que pendant PULSE_EN (d'où
l'inhibition du décodeur par PULSE_EN_N), et l'amortissement doit
pouvoir être appliqué à la bobine adressée indépendamment de
l'excitation (d'où le second décodeur, validé par DAMP_EN_N).

## 3. Les blocs, leurs composants et leur rôle

### A. Liaison et rails

| Composant | Rôle |
|---|---|
| J1, FPC 16 broches (Hirose FH12) | seule liaison avec le cerveau, brochage ci-dessus |
| C1 10 µF 25 V sur VIN | réserve locale du rail d'impulsion, absorbe la roue libre |
| C2 10 µF et C4 100 nF sur 5VA | découplage du rail analogique |
| C3 100 nF sur 3V3 | découplage de la logique |

### B. Polarisation VREF (1,65 V)

| Composant | Rôle |
|---|---|
| R5 20,5 k et R6 10 k, C13 1 µF | diviseur de 5VA, 5 x 10 / 30,5 = 1,64 V (`mockup.analog.vref_v`) |
| U8 unité A (OPA2810) | suiveur : VREF basse impédance pour les 2 n² résistances de polarisation, les entrées de l'INA et les retours des filtres |
| C23 1 µF sur VREF | tient la référence pendant les impulsions |

Toute la chaîne est centrée sur VREF pour rester dans la plage
0 à 3,3 V de l'ADC du cerveau et dans la plage d'entrée de l'AD8421
alimenté en 5 V simple.

### C. Rail d'impulsion partagé

| Composant | Rôle |
|---|---|
| Q2 AO3400A, R8 100 k | PULSE_EN (3,3 V) tire la grille de Q1 à la masse ; R8 garde le rail coupé nappe débranchée |
| Q1 AO3401A, R7 10 k | commutateur haut du 12 V vers PULSE_RAIL ; R7 le tient bloqué au repos |
| R9 10 ohms (2010) | limite le courant d'impulsion à environ 1,2 A et dissipe l'énergie de roue libre |
| R10 100 k | ramène DRIVE_BUS à 0 V au repos, les diodes de bus sont alors bloquées |
| U6 74LVC1G04 | PULSE_EN_N pour inhiber le décodeur d'excitation hors impulsion |

### D. Cellule d'une bobine (une par case, n² fois)

Références de la cellule k : R(100 + 10 k + 1) à + 7, D + 1 à + 4,
Q + 1 et + 2, NTk (`cell_refs()`).

| Composant | Rôle |
|---|---|
| NTk, « net tie » | la spirale elle-même : couches 1 à 3 sur Ck_A, couche 4 et échappée sur Ck_B, jointes sur la carte |
| deux 10 k vers VREF | polarisent les deux bornes de la bobine à 1,65 V au repos |
| B5819W (diode de bus) | laisse entrer l'impulsion depuis DRIVE_BUS et isole la bobine du bus au repos |
| AO3400A (N-FET bas) et 100 k | ferme le circuit d'excitation pendant l'impulsion ; le 100 k tient la grille basse |
| SS34FL (roue libre) | écrête l'extrémité B sur VIN quand le N-FET s'ouvre |
| AO3401A (P-FET), 680 ohms, 100 k | amortissement : 680 ohms aux bornes de la bobine, proche de l'amortissement critique de sa résonance parasite avec la capacité du mux (racine de L sur C, 16 µH et 40 pF, donne 630 ohms) |
| deux 330 ohms | limitent le courant vers le mux si un transitoire dépasse les rails |
| deux BAV99 | écrêtent Mk_A et Mk_B entre la masse et 5VA devant le mux |

### E. Décodeurs d'adresse

| Composant | Rôle |
|---|---|
| U1 74HC4514 (4 vers 16, sorties actives hautes) | une sortie par grille de N-FET ; inhibé par PULSE_EN_N : aucune grille n'est haute hors impulsion |
| U2 74HC154 (4 vers 16, sorties actives basses) | une sortie par grille de P-FET ; validé par DAMP_EN_N |
| C5, C6 100 nF | découplage sur 3V3 |

Le bit 3 d'adresse est MUX_EN_H : bobines 1 à 8 quand il est bas,
9 à 16 quand il est haut ; le firmware pose MUX_EN_L au complément.

### F. Multiplexeurs

| Composant | Rôle |
|---|---|
| U3 ADG1607 (bobines 1 à 8), U4 ADG1607 (9 à 16) | double 8 vers 1 : les deux bornes de la bobine adressée vers les deux entrées de l'INA, sorties des deux boîtiers en parallèle, un enable chacun |
| C7, C8 100 nF | découplage sur 5VA |

### G. Chaîne d'amplification (valeurs de `design_chain`)

| Composant | Rôle |
|---|---|
| C14, C15 100 nF, R12, R13 100 k | couplage AC des deux sorties de mux, repolarisées à VREF |
| U5 AD8421, R14 523 ohms | amplificateur d'instrumentation, gain 1 + 9,9 k / 523 = 20, référence VREF |
| U7 unité A, C17, C18 1 nF, R15, R16 787 ohms, R17 590 ohms, R18 1 k | Sallen-Key passe-haut, 202 kHz, K = 1,59 |
| U7 unité B, R19, R20 750 ohms, C19, C20 330 pF, R21 590 ohms, R22 1 k | Sallen-Key passe-bas, 643 kHz, K = 1,59 |
| U8 unité B, R23 3,57 k, R24 1 k | étage de sortie x 4,57, compense l'affaissement en milieu de bande |
| R25 49,9 ohms, C24 1 nF | RC vers l'ADC |
| D3 BAV99 | écrête AMP_OUT entre la masse et 3V3 |
| C16, C21, C22 100 nF | découplage des trois boîtiers |

Gain total calculé : 231 à mi-bande, dans la fourchette
`measurement.preamp_gain`.

### H. LED de camp

| Composant | Rôle |
|---|---|
| LD1 à LD2n² WS2812B | deux par case (coins NO et SE), chaînées de LED_DIN à LED_DOUT dans l'ordre du serpentin des rangées |
| CL1 à CL2n² 100 nF | un découplage par LED sur 5V_LED |

### I. Points de test

TP1 AMP_OUT, TP2 VREF, TP3 DRIVE_BUS, TP4 GND.

## 4. Le câblage, bloc par bloc

Les numéros sont ceux des symboles KiCad officiels, vérifiés par le
constructeur de circuit (une broche oubliée ou inconnue fait échouer
le build).

### A. Liaison et rails

- J1 : broches 1 à 16 sur les nets du tableau de la section 1.
- C1 entre VIN et GND ; C2 et C4 entre 5VA et GND ; C3 entre 3V3 et
  GND.

### B. Polarisation

- R5 de 5VA à VREF_DIV, R6 de VREF_DIV à GND, C13 de VREF_DIV à GND.
- U8A : entrée + (broche 3) sur VREF_DIV, sortie (1) sur VREF,
  entrée - (2) sur VREF. U8 alimenté broche 8 sur 5VA, broche 4 sur
  GND, C22 entre 5VA et GND, C23 entre VREF et GND.

### C. Rail d'impulsion

- Q2 : grille (1) PULSE_EN, source (2) GND, drain (3) Q1_G ; R8 de
  PULSE_EN à GND.
- Q1 : grille (1) Q1_G, source (2) VIN, drain (3) PULSE_RAIL ; R7 de
  Q1_G à VIN.
- R9 de PULSE_RAIL à DRIVE_BUS ; R10 de DRIVE_BUS à GND.
- U6 : entrée (2) PULSE_EN, sortie (4) PULSE_EN_N, VCC (5) 3V3,
  GND (3).

Fonctionnement : PULSE_EN haut sature Q2, la grille de Q1 tombe à la
masse, Q1 conduit, DRIVE_BUS monte à 12 V à travers les 10 ohms.

### D. Cellule de la bobine k

- NTk : broche 1 sur Ck_A, broche 2 sur Ck_B.
- Polarisation : 10 k de Ck_A à VREF, 10 k de Ck_B à VREF.
- Mesure : 330 ohms de Ck_A à Mk_A, 330 ohms de Ck_B à Mk_B ; BAV99 :
  broche 1 sur GND, broche 3 sur Mk_A (ou Mk_B), broche 2 sur 5VA. Le
  symbole conduit de la broche 1 vers la 3 puis vers la 2 : la masse
  vers le signal, le signal vers 5VA, c'est l'écrêteur classique.
  Mk_A et Mk_B vont aux entrées SkA et SkB du mux.
- Excitation : B5819W anode (2) sur DRIVE_BUS, cathode (1) sur Ck_A ;
  N-FET grille (1) sur DRIVEk, source (2) sur GND, drain (3) sur
  Ck_B ; 100 k de DRIVEk à GND ; SS34FL anode (2) sur Ck_B, cathode (1)
  sur VIN.
- Amortissement : P-FET grille (1) sur DAMPk_N, source (2) sur Ck_A,
  drain (3) sur DMPk ; 680 ohms de DMPk à Ck_B ; 100 k de DAMPk_N à
  VIN.

Fonctionnement : au repos les deux bornes sont à 1,65 V et la diode de
bus est bloquée (DRIVE_BUS à 0 V). Pendant l'impulsion, DRIVE_BUS à
12 V passe par la diode de bus jusqu'à Ck_A, le N-FET tire Ck_B à la
masse : 12 V sur 16 µH, le courant monte d'environ 0,75 A par
microseconde. À l'ouverture du N-FET, Ck_B monte jusqu'à VIN plus une
chute de diode et le courant se referme par SS34FL, VIN, Q1, R9 et la
diode de bus, où il s'éteint en une à deux microsecondes. DAMPk_N bas
rend le P-FET passant et met les 680 ohms entre Ck_A et Ck_B. Pendant
l'écoute, la bobine ne voit plus que ses 10 k, les 330 ohms et l'entrée
du mux.

### E. Décodeurs

- U1 74HC4514 : EL (1) sur 3V3, ~EN (23) sur PULSE_EN_N, A0 (2)
  MUX_A0, A1 (3) MUX_A1, A2 (21) MUX_A2, A3 (22) MUX_EN_H, Vdd (24)
  3V3, Vss (12) GND ; Q0 à Q15 sur DRIVE1 à DRIVE16 (broches 11, 9, 10,
  8, 7, 6, 5, 4, 18, 17, 20, 19, 14, 13, 16, 15).
- U2 74HC154 : E0 (18) sur GND, E1 (19) sur DAMP_EN_N, A0 (23) MUX_A0,
  A1 (22) MUX_A1, A2 (21) MUX_A2, A3 (20) MUX_EN_H, VCC (24) 3V3,
  GND (12) ; S0 à S15 sur DAMP1_N à DAMP16_N (broches 1 à 11, puis 13
  à 17).
- C5 et C6 entre 3V3 et GND.

### F. Multiplexeurs

- U3 : S1A à S8A (17 à 24) sur M1_A à M8_A, S1B à S8B (8 à 1) sur M1_B
  à M8_B, DA (27) sur MUXA_OUT, DB (31) sur MUXB_OUT, A0 (15) MUX_A0,
  A1 (14) MUX_A1, A2 (10) MUX_A2, EN (16) MUX_EN_L, VDD (29) 5VA,
  VSS (25, 33) et GND (9) sur GND, broches 11, 12, 13, 26, 28, 30, 32
  non connectées.
- U4 : idem avec M9 à M16 et EN sur MUX_EN_H.
- C7 et C8 entre 5VA et GND.

### G. Chaîne

- C14 de MUXA_OUT à INA_INP, C15 de MUXB_OUT à INA_INM ; R12 de
  INA_INP à VREF, R13 de INA_INM à VREF.
- U5 : -IN (1) INA_INM, +IN (4) INA_INP, RG (2 et 3) reliées par R14,
  Vs- (5) GND, Vs+ (8) 5VA, REF (6) VREF, OUT (7) INA_OUT ; C16 entre
  5VA et GND.
- Passe-haut, U7A (+ broche 3, - broche 2, sortie 1) : C17 de INA_OUT à
  HP_N1, C18 de HP_N1 à HP_IN (entrée +), R15 de HP_N1 à HP_OUT
  (sortie), R16 de HP_IN à VREF, R17 de HP_OUT à HP_FB (entrée -),
  R18 de HP_FB à VREF.
- Passe-bas, U7B (+ broche 5, - broche 6, sortie 7) : R19 de HP_OUT à
  LP_N1, R20 de LP_N1 à LP_IN (entrée +), C19 de LP_N1 à LP_OUT
  (sortie), C20 de LP_IN à VREF, R21 de LP_OUT à LP_FB (entrée -), R22
  de LP_FB à VREF. U7 alimenté broche 8 sur 5VA, broche 4 sur GND, C21
  entre 5VA et GND.
- Sortie, U8B (+ broche 5, - broche 6, sortie 7) : entrée + sur LP_OUT,
  R23 de OUT_STAGE (sortie) à OUT_FB (entrée -), R24 de OUT_FB à VREF ;
  R25 de OUT_STAGE à AMP_OUT, C24 de AMP_OUT à GND, D3 broche 1 sur
  GND, broche 3 sur AMP_OUT, broche 2 sur 3V3.

### H. LED

- LDi : VDD (1) sur 5V_LED, VSS (3) sur GND, DIN (4) sur le maillon
  précédent, DOUT (2) sur le suivant ; maillons LED_DIN, LED_L1 à
  LED_L(2n² - 1), LED_DOUT. CLi entre 5V_LED et GND près de chaque LED.

## 5. Le quadrant 2 x 2

Même architecture, même bus, même firmware, avec n = 2 :

- 4 cellules (bobines 1 à 4), 8 LED, carte de 2 p plus la bande sur
  2 p, soit 120 x 100 mm à p = 50 ;
- un seul ADG1607 (U3, enable MUX_EN_L) ; U4 disparaît, MUX_EN_H ne
  sert plus qu'aux décodeurs, où il reste bas ;
- les décodeurs restent des 4 vers 16 dont les sorties 4 à 15 sont
  libres, pour garder le bus et le firmware identiques ; un 2 vers 4
  serait possible mais changerait le brochage à la nappe ;
- côté générateur, le circuit est déjà paramétré par
  `plateau.quadrant.squares`, mais le plan de la bande (`strip.py`)
  suppose huit cellules par bande et les trous de fixation sont posés à
  1,4 p et 3,4 p : à généraliser avant de régénérer le PCB.

## 6. Points relevés en relisant le circuit, et ce qui a été fait

Les deux premiers points ont été tranchés le 13/09/2026 et sont dans
le circuit (`tools/quadgen/circuit.py`) ; la décision suit chaque
constat.

1. **Le retour de roue libre passe par Q1.** Quand le N-FET s'ouvre,
   le courant de la bobine se referme par SS34FL, VIN, puis Q1, R9 et
   la diode de bus. Or DRIVEk et PULSE_EN retombent au même instant
   (le décodeur est inhibé par PULSE_EN_N), et Q1 ne reste passant
   que grâce à la lenteur de sa grille (R7 10 k contre sa capacité de
   grille, quelques microsecondes). Si Q1 se bloquait avant la fin de
   la roue libre, le courant n'aurait plus que le 680 ohms par la diode
   de substrat du P-FET et l'écrêteur de Mk_A par ses 330 ohms : des
   centaines de volts.
   Décision : une Schottky de roue libre par cellule, de la masse vers
   Ck_A (B5819W, la même que la diode de bus), et R7 abaissée de 10 k à
   470 ohms. Le condensateur de grille envisagé d'abord aurait tenu Q1
   passant trop longtemps : le rail doit au contraire être coupé avant
   la fenêtre d'écoute, sinon la diode de bus tire la bobine adressée
   à 12 V pendant la mesure et les écrêteurs injectent des dizaines de
   milliampères dans 5VA. Avec 10 k, Q1 restait passant une quinzaine
   de microsecondes après PULSE_EN, soit le début de la fenêtre ; avec
   470 ohms il se bloque en moins d'une microseconde, le bus se
   décharge par les polarisations des cellules, et la roue libre ne
   dépend plus de lui : le courant se referme par la SS34FL, VIN, le
   condensateur C1 et la diode de roue libre. Le banc SPICE de la
   cellule (lot 2) doit compter les capacités de ces trois diodes,
   qui abaissent la résonance parasite de la spirale.
2. **Le 100 k de DAMPk_N vers VIN ne sert à rien** avec une sortie
   push-pull à 3,3 V du 74HC154 : la grille reste à 3,3 V, jamais à
   VIN. Conséquence : pendant l'impulsion de la bobine adressée, sa
   source (Ck_A) est à 12 V et le P-FET conduit (18 mA dans 680 ohms,
   sans effet), mais il n'est pas « bloqué dur » comme le yaml le
   suppose. Décision : résistance supprimée, la grille est tenue par la
   sortie du décodeur.
3. **Les noms de broches du symbole KiCad BAV99** (K, A, K) sont
   trompeurs ; c'est le dessin qui fait foi, et le câblage masse,
   signal, 5VA est le bon.
4. Restent de la [note 14](14-revue-des-cartes.md) : l'ADG1607 en 5 V
   simple à confirmer sur la fiche, le courant LED par nappe, les
   codes LCSC.

## 7. Le schéma redessiné (fait le 13/09/2026)

![Cellule de bobine du quadrant 2 x 2](../images/quadrant-2x2-cellule.png)

- `analoggen/sheets.py` est le moteur : une feuille place des unités
  de symboles à des positions de gabarit et dessine les fils entre
  leurs broches ; les rails, le bus d'adresse et les nets partagés
  entre feuilles portent des étiquettes globales, les nets internes à
  une feuille une étiquette locale. Avant d'écrire quoi que ce soit, le
  moteur vérifie le dessin contre le circuit : chaque broche est posée,
  chaque net est un seul composant connexe, deux nets ne se touchent
  jamais, chaque net porte son nom. Les positions des broches passent
  par la matrice d'orientation de KiCad, donc un symbole tourné ou
  miroir tombe où KiCad le dessine. Chaque segment est coupé aux
  points qui le touchent : KiCad ne relie que des extrémités, un point
  de jonction seul ne suffit pas.
- `quadgen/schematic.py` porte les gabarits : feuille racine avec J1
  et les blocs, rails et polarisation, cellules (quatre par feuille,
  même gabarit pour chacune), sélection, chaîne, LED. Le même code
  dessine le 2 x 2 et le 4 x 4.
- La netlist relue par `kicad-cli` est comparée au circuit pour les deux
  variantes (`tests/test_drawn_schematic.py`), en plus du contrôle du
  moteur. L'ancien émetteur par étiquettes reste disponible pour les
  autres cartes.

## 8. Le quadrant 2 x 2 tel que généré

- `python -m quadgen build --reduced` lit `plateau.quadrant.reduced`
  (`squares: 2`, `strip_overhang_mm`) et écrit `hardware/quadrant-2x2/`
  : quatre cellules, un ADG1607, huit LED, décodeurs conservés avec
  leurs sorties 4 à 15 laissées libres.
- La carte fait 2 p plus la bande sur 2 p plus le dépassement : avec
  une seule bande d'échappée, la bande de frontal (zone du connecteur,
  quatre cellules, zone médiane) est plus longue que 2 p, et la carte
  s'allonge d'autant vers le sud. Le 4 x 4 n'a pas de dépassement.
- Dans la cellule, les quatre résistances de polarisation et
  d'écrêtage passent en 0402 et l'amortissement en 0603 pour loger la
  diode de roue libre dans le pas de 7,4 mm.
