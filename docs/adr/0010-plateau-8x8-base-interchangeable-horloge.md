# ADR 0010. Plateau 8 x 8 direct en quadrants, base interchangeable, horloge à bascule

Date : 2026-09-02. Statut : acceptée.

## Contexte

La maquette 2 x 2 (ADR 0008) devait trancher le pas, la ferrite et la
chaîne de mesure avant le plateau complet. Le porteur du projet a
choisi de ne pas entretenir plusieurs versions : un seul plateau, conçu
directement à l'échelle finale, qui sert aussi de banc de mesure. La
référence d'usage est un plateau capteur du commerce (Chessnut Air,
fin, autonome, sans mécanisme), le déplacement des pièces devenant une
option. Cette ADR consigne l'ensemble des choix pris ce jour et leurs
raisons ; le détail chiffré et la discussion sont dans la
[note 10](../notes/10-plateau-8x8-et-horloge.md).

## Décisions

1. **Pas p = 50 mm, figé.** Le rapport de calcul donne à p = 40 un
   signal à 70 % de celui de p = 50 et un Q estimé de 13 pour le pion
   noir, sous le plancher d'acceptation de 30 ; à p = 50 il est de 33.
   C'est aussi le format tournoi. L'ADR 0006 est tranchée ; les deux
   pas restent calculés et rapportés pour comparaison.
2. **Quadrants 4 x 4 intelligents, quatre cartes identiques.** Chaque
   quadrant (200 x 200 mm, 4 couches) porte ses 16 spirales, 32 LED et
   son frontal analogique sur une bande de bord en face supérieure :
   ADG726 (double 16 vers 1), excitation par FET par bobine derrière un
   décodeur d'adresses, chaîne AD8421 plus Sallen-Key reprise de la
   maquette. Quatre sorties amplifiées vers quatre ADC du STM32G474.
   Ni 16 tuiles 2 x 2 (la carte analogique de maquette ne pilote que
   4 bobines, et les tuiles se gêneraient), ni une carte unique de
   40 cm (paliers tarifaires et signal en microvolts sur 40 cm,
   ADR 0004).
3. **LED de camp identiques sur toutes les cases**, diagonale NO-SE,
   deux par case (128), retrait `leds.corner_inset_mm`. L'exception de
   la case S2 de la maquette venait de son connecteur de bord ; le
   quadrant n'a plus de connecteur dans les coins. Une grille de 81 LED
   partagées aux sommets est écartée : un sommet touche quatre cases.
4. **Un module plateau invariant et deux bases interchangeables.** Le
   module (contreplaqué plus quatre quadrants, 420 x 420 x 6,6 mm) se
   pose dans une base fine (21 mm au total) ou une base chariot
   (54 mm, avec le CoreXY). Le dessous des quadrants est vierge dans
   les deux cas. Cerveau, carte puissance et cellules sont au fond de
   la base, sur une empreinte de fixation commune : changer de base,
   c'est débrancher quatre nappes et déplacer trois cartes.
5. **Le chariot est une option, pas un prérequis.** La base chariot
   porte les ailes de capture (50 mm de chaque côté, affleurantes au
   bois) et la lisière arrière ; le plateau fin n'a ni ailes ni marge.
   Les pièces reçoivent leur aimant ferrite dès le départ pour ne pas
   être refaites. La carte moteurs (TMC2209, fins de course,
   actionneur) vit dans la base chariot ; le cerveau n'embarque que son
   connecteur.
6. **Frontal analogique en face supérieure, sous le bois.** Le portique
   passant à moins d'un millimètre sous les quadrants, le frontal ne
   peut pas être dessous. Un entrefer d'air `gap.air_mm` de 2 mm sous
   le contreplaqué loge les LED (1,6 mm) et des composants plats
   (1,8 mm au plus) ; l'entrefer nominal passe à 7,1 mm, sous le
   maximum de 8. Ce terme d'air était implicite dans la maquette ; il
   est désormais explicite et compté dans le signal.
7. **Cellules plates 3S1P** (5 Ah, 55,5 Wh) au lieu du pack 3S2P 18650
   (73,4 Wh) : le plateau reste à 21 mm. Autonomie calculée d'environ
   51 h en humain contre humain et 11 h contre le moteur, au lieu de
   68 et 15 h. Pas de bandeau ni de module batterie déporté : le
   plateau doit fonctionner seul.
8. **Cerveau à MCU soudé** (STM32G474RE LQFP64, SWD, USB), plus de
   Nucleo, pour une seule carte plate ; le G474 sait faire les deux
   voies d'extraction de l'ADR 0007, donc le choix ne dépend pas de
   leur verdict. Découpage fonctionnel en trois cartes : cerveau
   (MCU, quatre nappes de quadrant, chaîne LED, 5 V buck forced PWM,
   3,3 V, îlot analogique LDO), puissance (BMS 3S, charge USB-C PD,
   jauge), moteurs (option, dans la base chariot).
9. **Emplacement communication** sur le cerveau : module ESP32-S3
   (WiFi et BLE) en équipement de base, embase Pi Zero 2 W en option,
   même UART isolée par ADuM1201 et même load switch (ADR 0003 et
   0005). Cible en ligne réaliste : l'API Board de Lichess ; chess.com
   n'offre pas d'API de jeu publique.
10. **Horloge séparée, à bascule, sans fil.** Module autonome
    (120 x 70 mm, module ESP32-S3-WROOM-1 comme le cerveau, une 18650,
    écran 2,4 pouces sur face
    inclinée, barre à bascule de 108 mm sur pivot central avec un
    microrupteur sous chaque extrémité, encodeur pour les menus,
    buzzer, USB-C), relié au plateau en BLE. Elle choisit les modes de
    jeu et affiche les temps ; le plateau reste jouable sans elle. Les
    18650 restent hors du plateau, l'horloge en emporte une.
11. **Outillage.** KiCad 9 est conservé (dépôt natif KiCad, fichiers
    texte, spirales générées par script, plugin JLCPCB, import LCSC
    par easyeda2kicad). Le quadrant reste entièrement généré ; le
    cerveau aura un schéma généré depuis le yaml et un placement à la
    main dans KiCad.
12. **Modélisation 3D depuis le yaml.** `chessboard_calc.plateau`
    dérive les cotes, `mechanical/plateau.py` et `mechanical/clock.py`
    les transforment en solides CadQuery, `mechanical/scenes.py` rend
    les vues de la doc avec un rasteriseur à tampon de profondeur (le
    tri par peintre de matplotlib rendait les grands panneaux faux),
    `mechanical/viewer.py` génère une vue interactive three.js
    (bases, éclaté, couches, noms au survol).

## Conséquences

- La maquette 2 x 2 est retirée du plan. Ses générateurs, cartes et
  docs restent dans le dépôt comme référence de la chaîne analogique
  et du routage, marqués remplacés.
- ADR 0004 amendée (frontal embarqué sur le quadrant, ailes de capture
  dans la base chariot), ADR 0006 tranchée à 50 mm, ADR 0008 remplacée
  pour la partie maquette (le mux différentiel, l'excitation hors mux
  et la chaîne de gain restent valables).
- `config/board.yaml` gagne `pitch.plateau_mm`, `gap.air_mm`, la
  batterie plate, `mcu.mounting`, et les sections `plateau` et
  `clock` ; `tests/test_plateau.py` épingle l'empilement, les emprises,
  les 128 points lumineux à source unique et les gardes de l'horloge.
- Les mesures M1 à M11 se déroulent sur un quadrant plus le cerveau,
  pas sur la maquette. Le test de couloir reste bloquant.
- Points ouverts : force réelle du N42 à travers 7,1 mm (M7), joint
  bois contre aile sans lèvre (0,3 mm max), blindage du frontal en
  1,8 mm de hauteur (plan de masse interne plus ruban de cuivre sous le
  bois), protocole BLE plateau contre horloge, choix chess.com.
