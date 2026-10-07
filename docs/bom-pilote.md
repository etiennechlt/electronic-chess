# Fiche du pilote simple : une carte bobines 100 x 100 et un shield à la main

Établie le 07/10/2026. Elle répond à une commande précise : **un pilote
avec le minimum de composants, qui tienne dans le palier 100 x 100 mm
avec une seule carte à concevoir, le traitement sur un shield posé à
côté de la Nucleo et soudé à la main.** Les quantités sortent des
nomenclatures générées, les prix des relevés du 20/09/2026
(`docs/prix-plateau.csv`, [fiche de la maquette](bom-maquette.md)),
conversion 1 USD = 0,92 EUR, TVA 20 % ajoutée. Aucune commande n'a été
passée.

## 1. Ce qu'est le pilote

| Élément | Choix | Pourquoi |
|---|---|---|
| Carte à concevoir | une seule : la [carte bobines](../hardware/mockup-2x2/coil-board/README.md), 100 x 100 mm, 4 couches, passive (quatre spirales, un connecteur 1 x 12, huit trous) | à p = 50 mm, quatre cases font exactement 100 x 100 : il n'y a de place ni pour un frontal ni pour une LED de plus sans sortir du palier ([note 16](notes/16-cout-des-cartes.md), section 3) |
| Pas | p = 50 mm, celui du plateau (ADR 0010) | un pilote à p = 40 ne validerait pas le plateau |
| LED de camp | aucune (`mockup.coil_board.leds.fitted: false`) | seize composants et toute la chaîne de données en moins ; c'est aussi ce qui a fermé le DRC de la carte |
| Frontal | sur un shield soudé à la main, trois options au paragraphe 3 | le signal brut de spirale traverse 10 à 15 cm de nappe, acceptable sur un pilote de paillasse, refusé sur le plateau (ADR 0004) |
| Contrôleur | NUCLEO-G474RE, le MCU du cerveau, firmware `make NUCLEO=1` | rien à souder de fin, sonde et port série compris |
| Pions | quatre pucks de test (pion, cavalier, fou, tour noirs) | le bas de la bande, les notes les plus serrées ([note 20](notes/20-tuto-banc.md)) |

Ce pilote est la maquette de l'ADR 0008 allégée : même carte bobines,
sans LED, et son frontal au choix. Il mesure le couplage spirale-pièce
à travers 7,1 mm d'entrefer, le facteur Q des pucks et la séparation
des notes, avec le firmware du cerveau ; il ne mesure ni les LED, ni la
nappe FPC, ni le frontal embarqué du quadrant.

## 2. La carte, ce qu'elle coûte

| Poste | EUR TTC | Détail |
|---|---|---|
| 5 cartes bobines nues, 4 couches, 100 x 100 | 8 à 15 | 1,6 mm, 1 oz externe, HASL sans plomb |
| Option cuivre interne 1 oz | 10 à 25 | la spirale du modèle ; en 0,5 oz standard l'ESR monte de 50 % et le Q perd un tiers ([note 23](notes/23-commande-jlcpcb.md), 3.1) : payer, ou corriger le yaml avant de mesurer |
| Barrette 1 x 12 au pas 2,54 | 0,1 | la seule pièce de la carte, soudée à la main |

Les gerbers et leur empreinte sont commités
(`coil-board-gerbers.zip`, `coil-board-gerbers.sha256`), DRC KiCad à
zéro erreur et zéro élément non connecté.

## 3. Le shield : trois options

Le shield fait trois choses : frapper chaque bobine (rail 12 V commuté,
un FET par bobine), écouter la sonnerie (mux différentiel, gain,
filtrage) et donner à la Nucleo ses signaux (A0 pour l'ADC, D3 à D15
pour les commandes). Les trois options partagent le même circuit, celui
de l'ADR 0008 ; elles diffèrent par le support.

### Option A, conseillée : la carte analogique existante, soudée à la main

La [carte analogique de la maquette](../hardware/mockup-2x2/analog-board/README.md)
est ce shield, déjà conçu, routé et au DRC zéro, 100 x 62 mm en deux
couches (palier 100 x 100), avec ses gerbers commités. Rien à
concevoir : c'est une seconde carte à commander, pas un second design.
Tout se soude au fer sauf le buck TPS62150 (QFN), que le pilote ne
monte pas.

| Bloc | Monter | Laisser vide |
|---|---|---|
| Entrée 12 V | jack J1, SS34 D1, TVS D2, réservoir C1 et C2 | |
| Rail 5VA | LDO U2 LP2985 et ses C9, C10, C11, C12 ; cavalier JP1 en position LDO | buck U1, L1, JP3, R1 à R4, C4 à C8, C27, perle FB1 |
| Cellules bobine (x 4) | 10 k x 2, 330 R x 2, BAV99 x 2, B5819W, AO3400A, SS34, AO3401A, 680 R, 100 k x 2 | |
| Commutateur de rail | Q1 AO3401A, Q2 AO3400A, R7, R8, R10, R9 10 R en 2512 | |
| Mux et chaîne | U3 74HCT4052, U4 AD8421 (R14 fixe le gain 20), U5 et U6 OPA2810, leurs résistances et condensateurs, R5, R6, C13 du VREF | |
| UART Pi isolée | | U7 ADuM1201, C26, J5 ; R66 et R67 restent non montées |
| LED | | U8 74AHCT1G125, R68 |

| Poste | EUR TTC | Détail |
|---|---|---|
| 5 cartes analogiques nues, 2 couches, 100 x 62 | 2 à 5 | HASL sans plomb suffit |
| Composants montés, compte exact | 18 | 16,3 USD : OPA2810 x 2 à 5,48 (Mouser), AD8421 3,69, 74HCT4052 0,15, LP2985 0,17, FET et diodes 1,2, passifs 0,6, jack et barrettes 0,4 |
| Les mêmes avec la rechange de 10 % par ligne | 30 | la rechange double les circuits à l'unité |
| Port des composants | 15 à 25 | LCSC, plus Mouser ou DigiKey pour l'OPA2810 |

### Option B : perfboard ou shield de prototypage Nucleo, câblé à la main

Les mêmes composants que l'option A, sans la carte : les boîtiers CMS
passent sur des adaptateurs (SOIC-8 vers DIP x 3, TSSOP-16 x 1 ou un
74HCT4052N en DIP-16, SOT-23 x 10 ou des FET TO-92 : BS170 pour
l'AO3400A, BS250 pour l'AO3401A) sur une plaque de prototypage
Nucleo-64 ou une perfboard, 8 à 12 EUR d'adaptateurs et de plaque.

C'est l'option qui respecte à la lettre « un seul design de PCB », et
c'est celle que cette fiche déconseille : deux OPA2810 à 105 MHz en
Sallen-Key et un AD8421 à gain 20 sur une plaque à trous, c'est une
journée de câblage et un risque sérieux d'oscillation et de bruit, sur
la mesure même que le pilote doit établir. Elle reste valable pour un
premier essai sans chaîne de gain (paragraphe 6).

### Option C : un shield minimal à concevoir

Une chaîne single-ended sur l'amplificateur interne du STM32G474 (PGA
jusqu'à x 64, 13 MHz de produit gain-bande) et son comparateur
(ADR 0007), un seul 74HC4051, les quatre FET d'excitation, sans
AD8421, sans OPA2810, sans amortisseurs : une trentaine de composants.
Elle n'existe pas : c'est une conception (deux à trois jours, une ADR,
le firmware de la voie comparateur) qui change l'architecture de
mesure que les quadrants reprennent. À ouvrir seulement si la première
mesure du paragraphe 6 montre que la chaîne de l'ADR 0008 est
surdimensionnée.

## 4. Le reste

| Poste | EUR TTC | Détail |
|---|---|---|
| NUCLEO-G474RE | 21 | eStore ST ou RS, 17,50 EUR HT |
| Nappes Dupont femelle-femelle x 20 | 3 | J4 du shield vers les embases Arduino de la Nucleo ([README de la maquette](../hardware/mockup-2x2/README.md), paragraphe 3) |
| Alimentation 12 V | 0 ou 10 | de laboratoire limitée en courant, sinon un bloc 12 V 2 A à jack 5,5 x 2,1 ; jamais un chargeur à découpage près des bobines |
| Quatre pucks | 24 à 30 | aimants ferrite Y30, fil émaillé 0,25 et 0,315 mm, C0G 1 % 0805, impression PETG, vis M3 x 30 ([note 20](notes/20-tuto-banc.md), 3.5) |
| Surface de jeu | 13 | contreplaqué sec 3 mm, feutre 0,5 mm, entretoises et visserie M3 nylon |
| Outillage | 0, ou 200 à 400 | fer fin, multimètre, alimentation, oscilloscope de poche 10 MHz, LCR-mètre, perceuse pour bobiner ; l'air chaud n'est plus nécessaire, le QFN n'est pas monté |

## 5. Totaux

| Scénario | EUR TTC |
|---|---|
| Carte bobines seule, 5 pièces, port compris | 26 à 43, plus 10 à 25 pour le cuivre interne |
| Pilote complet, option A, rechange comprise, outillage déjà là | **130 à 195** |
| Pilote complet, option B | 140 à 205 |
| Le même pilote sur le quadrant 2 x 2 avec son frontal embarqué (fiche du 07/10) | 220 à 283 |

Détail du scénario A : cartes 10 à 20, cuivre interne 10 à 25, port et
TVA des cartes 18 à 28, composants 30, port des composants 15 à 25,
Nucleo et nappes 24, pucks 24 à 30, surface 13. Ce qui pèse : les deux
OPA2810 et l'AD8421 (14,65 USD sur 16,3), le port, et l'option cuivre
interne, qui coûte plus que la carte qu'elle améliore.

## 6. Ce que le modèle dit du signal, et la première mesure

`chessboard_calc.coupling.ringdown_signal` donne, pour une pièce sur sa
case à travers 7,1 mm d'entrefer, la force électromotrice attendue sur
la spirale après les 2 µs de silence :

| Pièce | Note | EMF sur la spirale |
|---|---|---|
| pion noir | 217 kHz | 0,12 V crête |
| cavalier noir | 237 kHz | 0,21 V |
| fou noir | 262 kHz | 0,23 V |
| tour noire | 288 kHz | 0,37 V |
| roi blanc | 613 kHz | 0,74 V |

Avec le gain de 200 à 400 de la chaîne de l'ADR 0008, ces amplitudes
donnent 24 à 150 V en sortie : la chaîne sature à 3,3 V dès le premier
pion. Soit le modèle surestime d'un facteur dix à cinquante, soit le
gain est trop fort d'autant. C'est la première chose que le pilote
mesure, et elle ne demande aucun shield : un FET d'excitation sur une
plaque d'essai, la Nucleo qui le commande, et l'oscilloscope directement
sur une borne de spirale, un puck posé sur la case. L'amplitude lue
décide entre l'option A telle quelle, l'option A avec le gain de
l'AD8421 ramené à 1 (R14 retirée), et l'option C.

## 7. Dans l'ordre

1. Commander les cartes bobines (paragraphe 2), et la carte analogique
   avec elles si l'option A est retenue : même panier, même port.
2. Pendant la fabrication : bobiner les quatre pucks, imprimer les
   gabarits, percer le contreplaqué au gabarit `surface-template`.
3. À réception : la mesure du paragraphe 6, à l'oscilloscope, sans
   shield.
4. Souder le shield de l'option retenue, brancher la Nucleo, dérouler
   les échelons de la [note 20](notes/20-tuto-banc.md) avec le firmware
   en `make NUCLEO=1`.
5. Noter dans le [journal](notes/09-journal.md) les prix obtenus et
   l'amplitude mesurée : c'est elle qui décide de la suite, quadrant
   avec frontal embarqué ou tuile 100 x 100 avec frontal centralisé.
