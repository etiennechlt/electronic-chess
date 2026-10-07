# 24. Hall + RFID : évaluation comme alternative ou étape intermédiaire

Rédigée le 07/10/2026. Un brief extérieur au dépôt propose, pour un
plateau de 50 x 50 cm à cases de 5,5 à 6 cm, une architecture
« Hall + RFID » : un capteur à effet Hall analogique par case (SS49E ou
DRV5053), soit 64 capteurs lus par quatre multiplexeurs CD74HC4067 sur
l'ADC d'un ESP32, pour voir en temps réel quelles cases changent
(pièce soulevée ou posée), et une couche RFID pour l'identité des
pièces. Budget visé 350 à 550 EUR, avec un objectif pédagogique :
modéliser les champs et les couplages, puis les comparer à des mesures.

Cette note évalue cette architecture contre celle du dépôt
([ADR 0001](../adr/0001-lc-resonators-for-piece-identification.md) :
résonateurs LC passifs, identité par la fréquence), et dit ce qu'elle
vaut comme **alternative** et comme **étape intermédiaire**. Rien
n'est décidé ici ; la section 7 liste ce qu'une ADR trancherait.

Tous les chiffres viennent de la section `hall_rfid` de
`config/board.yaml`, calculés par `chessboard_calc.hall` et
`chessboard_calc.nfc`, imprimés par `python -m chessboard_calc report`
(section « Hall + RFID alternative » de chaque pas) et épinglés par
`tests/test_hall.py` et `tests/test_nfc.py`. Les valeurs de fiche
technique qui n'ont pas pu être relues (courant du DRV5053, résistance
du CD74HC4067 à 3,3 V, délai de mise sous tension) sont marquées « to
verify » dans le yaml.

## 1. Ce qui diffère entre le brief et le projet

| | Brief | Projet |
|---|---|---|
| Pas de case | 55 à 60 mm | 50 mm, figé (ADR 0010) ; tout reste paramétrique |
| Aimant dans la pièce | implicite (il faut bien un aimant pour un capteur Hall) | déjà là : ferrite SrFe, ø base moins 5 mm, 4 mm d'épais (ADR 0002) |
| Entrefer capteur à aimant | non précisé | 6,9 mm : air 2, bois 3, feutre 0,5, bobine de pièce 2, moins 0,6 mm de boîtier ; 7,8 mm au maximum |
| Cerveau | ESP32 | STM32G474, un ESP32-S3 comme pont radio ; le même module sert ici au prototype autonome |
| Identité | RFID | fréquence LC, 12 classes |

Le brief tourne le problème dans le même sens que le projet : un
aimant par pièce, un capteur par case, de la logique au dessus. La
différence est l'identité. Les cases de 55 à 60 mm rendent la partie
Hall plus facile qu'à 50 (aimants plus gros, voisins plus loin,
section 6) ; l'évaluation est faite au pas du projet, le pire des
trois.

## 2. La couche Hall : ce que la physique donne

Le modèle (`hall.disc_bz_mT`) est celui du disque uniformément
aimanté, nappe de courant Br / mu0 sur sa surface latérale, découpée en
boucles dont le champ hors axe est exact (intégrales elliptiques,
même méthode par filaments que `coupling.py`). Sur l'axe, l'empilement
retrouve la forme fermée à 1e-3 près, ce que le test vérifie ; en
champ lointain il retrouve le dipôle. C'est précisément le calcul que
le brief veut confronter à des mesures : un disque de ferrite, un
capteur Hall, une règle, et la courbe B(z) se mesure en une soirée.

Au pas de 50, capteur DRV5053OA (11 mV/mT, le moins sensible de la
famille, pour que le roi reste dans la plage linéaire) :

| Pièce | Aimant (mm) | B nominal (mT) | B entrefer max (mT) | B soulevée de 15 mm (mT) | B sur la case voisine (mT) | Sortie (mV / LSB) |
|---|---|---|---|---|---|---|
| pion | 12,5 x 4 | 25,3 | 20,7 | 2,1 | -0,11 | 278 / 367 |
| cavalier, fou | 15,0 x 4 | 29,4 | 24,6 | 2,9 | -0,16 | 323 / 427 |
| tour, dame, roi | 17,5 x 4 | 32,1 | 27,6 | 3,8 | -0,22 | 353 / 467 |

Ce qui en sort :

- **La présence est robuste.** Seuil à la moitié du champ le plus
  faible (pion à l'entrefer maximal) : 10,3 mT, relâchement à 7,2 mT.
  Un roi soulevé de 15 mm donne 3,8 mT, soit une marge de 1,9 sous le
  relâchement (critère 1,5 dans le yaml). Huit rois sur les cases
  voisines ajoutent 1,2 mT en tout, soit -24,7 dB du pion le plus
  faible (critère -20 dB, le même que la diaphonie de la chaîne LC). Le
  pion le plus faible fait 300 LSB sur l'ADC 12 bits de l'ESP32-S3
  (0,757 mV par LSB à 12 dB d'atténuation), cent fois le bruit estimé.
- **L'identité par l'amplitude n'existe pas avec les aimants du
  projet.** Les trois diamètres (12,5, 15 et 17,5 mm) donnent des
  champs qui se recouvrent dès que l'entrefer bouge de 0,5 mm
  (inclinaison, feutre écrasé) : un seul groupe séparable. C'est la
  version chiffrée du « 2 à 4 classes au mieux » de l'ADR 0001. Avec
  des aimants plus épais sur les pièces lourdes (4, 7 et 12 mm, la
  variante `size_coding` du yaml), on sépare trois groupes au pas de 50
  (pion ; cavalier et fou ; tour, dame et roi), à 62 mT au plus, encore
  dans la plage linéaire ; pas au pas de 40. Le roi porterait alors
  14 g de ferrite. En retournant les aimants d'un camp
  (`color_by_polarity`), le signe de la sortie double le compte : six
  classes. Jamais douze, et le retournement interdit l'aimant permanent
  du chariot (un N42 fixe repousserait un camp) : il impose
  l'électroaimant parmi `carriage.actuator_candidates`.
- **Le courant est le point dur, et il se règle.** 64 capteurs sous
  tension en permanence : 147 mA pour le DRV5053 (0,49 W), 384 mA pour
  la puce du SS49E (1,27 W, plus que tout le plateau au repos).
  L'autonomie humain contre humain passerait de 51 h à 31 h, ou à 19 h.
  En alimentant les capteurs par rangée de quadrant (quatre groupes,
  un P-FET par groupe), la moyenne tombe à 37 mA et l'autonomie
  revient à 44 h ; huit groupes la ramènent à 47 h.

| Capteur | Alimentation | mA | W | Autonomie (h), 51 sans |
|---|---|---|---|---|
| DRV5053OA | continue | 147 | 0,49 | 31 |
| DRV5053OA | 4 groupes | 37 | 0,12 | 44 |
| SS39ET (SS49E en SOT-23) | continue | 384 | 1,27 | 19 |
| SS39ET | 4 groupes | 96 | 0,32 | 36 |

- **La cadence est celle que le brief demande.** 82 µs par case (2 µs
  de commutation, huit lectures de 10 µs), quatre mux lus en parallèle
  sur quatre entrées ADC : 1,7 ms par plateau avec la commutation des
  rangées, soit 580 Hz. La chaîne LC scrute à 5 Hz au repos
  (`measurement.idle_scan_hz`) : la couche Hall voit la pièce quitter
  la case cent fois plus vite, et voit l'état « pièce en main » que le
  LC ne distingue pas d'une case vide.
- **Le boîtier décide du capteur.** Le SS49E du brief est un SIP dont
  les pattes font 4 mm : il ne tient pas dans l'entrefer d'air de 2 mm
  sous le contreplaqué (`gap.air_mm`, garde `hall.check`). Il faut du
  SOT-23 : SS39ET (même puce) ou DRV5053. Le DRV5053 consomme moins de
  la moitié et sort 1 V au repos, ce qui tombe au milieu de la plage de
  l'ADC avec les deux polarités.

### Où mettre le capteur sur le quadrant LC

Le centre de la case est le seul emplacement : à 22 mm du centre, en
bord de spirale, la pièce voisine donne un champ comparable à la pièce
propre et l'attribution est perdue (le même calcul hors axe le
montre). Le centre de la spirale est libre sur 22,5 mm de diamètre
(`sense_coil.inner_ratio`), mais les quatre couches portent chacune
une spirale et aucune piste ne peut sortir du centre sans croiser des
spires. Trois façons de le résoudre, à trancher :

| Option | Ce qu'elle coûte |
|---|---|
| Quadrant en six couches | un palier de prix de carte ; rien ne change à la bobine |
| Spirale sur trois couches, la quatrième aux pistes Hall | pour la même inductance cible, 7 spires par couche au lieu de 5, piste de 1,10 mm au lieu de 1,60 : ESR de 0,59 à 0,90 ohm, Q de la bobine de case en baisse d'un tiers |
| Nappe Hall séparée, carte de 0,6 mm posée sur le quadrant dans l'entrefer d'air | 0,6 + 1,3 mm de capteur sous les 2 mm d'air, juste ; des pistes au dessus des spirales à tenir en diaphonie ; c'est la seule option qui existe avant le quadrant, et sans lui |

Pour l'étape intermédiaire, la troisième option est la bonne : une
carte deux couches de 200 x 200 mm par quadrant, 16 capteurs, un
CD74HC4067, quatre P-FET, un connecteur, aucune chaîne analogique. Elle
se branche sur l'ESP32-S3 du brief aujourd'hui, et sur le bus du
cerveau demain (les lignes `MUX_A0..A2` et les deux enables de la nappe
suffisent à adresser 16 voies, `AMP_OUT` ramène la sortie).

## 3. La couche RFID : ce que la physique donne

Le brief ne détaille pas la lecture RFID. L'évaluation prend le cas
standard : étiquette NFC passive (NTAG213, ISO 14443A, 13,56 MHz) collée
au fond de la base, et une boucle par case gravée sur la carte.

- **Le bilan de liaison n'est pas le problème.** Boucle carrée de
  35 mm à deux spires (0,32 µH, accordée par 433 pF), étiquette de
  25 mm à sept spires (1,96 µH, résonance propre à 16,1 MHz avec les
  50 pF de la puce), 5,5 mm entre le cuivre et l'étiquette : k = 0,22,
  et 100 mA dans la boucle font 4,8 A/m à l'étiquette, 3,2 fois le
  minimum ISO 14443 ; 3,1 fois à l'entrefer maximal. Le couplage se
  calcule avec le même `mutual_coaxial_loops_nH` que le LC.
- **La commutation est le problème, et l'ADR 0001 avait raison.** Une
  boucle de Q 20 à 13,56 MHz veut 1,4 ohm de résistance série en tout.
  Le CD74HC4067 en met 100 (Q = 0,27) et ses quinze voies fermées
  accrochent 125 pF sur une boucle accordée par 433 pF : -12 % de
  fréquence, pour une bande passante de 5 %. Même un commutateur RF de
  1,5 ohm dans la boucle divise le Q par deux. Un commutateur ne peut
  vivre que dans la section adaptée à 50 ohm, derrière un réseau
  d'adaptation par antenne : arbre de neuf SP8T, 64 réseaux, un
  lecteur ; ou bien un lecteur par case.

Les topologies qui tiennent, avec leur ordre de grandeur (estimations
de marché, non relevées) :

| Topologie | Composants | Ordre de grandeur | Remarque |
|---|---|---|---|
| Un lecteur par case | 64 x (MFRC522 en HVQFN32, quartz 27,12 MHz, adaptation), SPI partagé, 64 chip select par registres à décalage | 64 x 3 EUR, 190 EUR environ | un émetteur à la fois, le logiciel l'impose ; pas de RF qui traverse la carte |
| Un lecteur, arbre de commutation 50 ohm | 9 SP8T, 64 adaptations, 1 PN5180 | 80 à 100 EUR environ | 64 lignes RF sur la carte, mise au point de 64 accords |
| Lecteur sur le chariot | 1 lecteur, aucune antenne fixe | 10 EUR | phase 2 seulement, lecture à la demande en déplaçant le chariot |
| Pas de RFID | | 0 | identité par la logique de jeu depuis la position initiale, promotion demandée par l'horloge ou l'application |

Deux remarques pour la cohabitation avec la chaîne LC, si les deux
existaient :

- 13,56 MHz est loin de 200 à 650 kHz, mais 100 mA dans une boucle
  sous la case pendant une mesure LC n'est pas acceptable : la lecture
  NFC se fait hors fenêtre de mesure, comme les trames LED (ADR 0009).
- L'étiquette est une boucle de 2 µH sans ferrite à côté de la bobine
  de 45 µH de la pièce : pas de courant de Foucault, une résonance
  propre à 16 MHz, donc une charge négligeable sur le ringdown ; le
  décalage de fréquence par couplage mutuel est absorbé par la
  calibration par pièce. À vérifier par une mesure M1 avec et sans
  étiquette.

La lecture est lente par case (5 à 10 ms d'anticollision et de lecture
d'UID) mais la couche Hall dit quelles cases ont changé : une
identification par coup, en moins de 20 ms. C'est le sens du couple
Hall plus RFID du brief, et il se tient.

## 4. Verdict

**Comme alternative au LC : non pour l'identité, oui pour la
présence.** La couche Hall ne donne pas l'identité (un groupe avec les
aimants du projet, trois à six avec des aimants codés, jamais douze) ;
la couche RFID la donne mais au prix de 64 lecteurs ou d'un arbre RF,
pour un coût du même ordre que le frontal analogique des quatre
quadrants (les trois références ADG1607, AD8421 et OPA2810 font
114 USD rechange comprise, [fiche du plateau](../bom-plateau.md)), et
seulement sur demande. L'ADR 0001 reste debout.

**Comme étape intermédiaire : oui, et c'est même la bonne.** La couche
Hall ne demande ni chaîne analogique, ni bobinage, ni calibration ; les
pièces ne changent pas (l'aimant y est déjà) ; la carte est en deux
couches ; la lecture est faite en 1,7 ms. Elle permet de développer et
de jouer tout ce qui ne dépend pas de l'identité (lots 6 à 8 de la
[note 07](07-etat-et-reste-a-faire.md) : arbitre depuis la position
initiale, LED, horloge, application, parties humain contre humain)
pendant que la chaîne LC attend ses cartes et la mesure M2. Elle sert
aussi l'objectif du brief : le champ du disque est modélisé ici
exactement, et se mesure avec les mêmes capteurs.

**Et après, la garder ?** Probablement, pour ce que le LC ne sait pas
faire : voir une pièce quitter sa case en quelques millisecondes et
distinguer « en main » de « posée ailleurs », ce qui simplifie
l'arbitre et le dialogue avec l'horloge. Le coût est de 64 SOT-23,
quatre mux et quatre P-FET, de l'ordre de 50 EUR, plus la question de
la carte (section 2). Elle remplace aussi, comme repli si M2 échoue,
les reed switches de l'ADR 0001 : présence par Hall, identité par
RFID à un lecteur par case.

## 5. Ce qui est prototypé dans ce lot

| Livrable | Où | Ce qu'il fait |
|---|---|---|
| Section `hall_rfid` du yaml, modèles typés | `config/board.yaml`, `chessboard_calc/config.py` | capteurs candidats, géométrie, seuils, mux, groupes d'alimentation, ESP32-S3, antenne et étiquette NFC |
| Modèle de champ et budget Hall | `chessboard_calc/hall.py` | champ du disque exact hors axe, champs par pièce, seuils, diaphonie, classes par amplitude, puissance, cadence, gardes |
| Modèle NFC | `chessboard_calc/nfc.py` | boucle, étiquette, couplage, champ ISO, verdict du mux et des commutateurs |
| Rapport | `python -m chessboard_calc report` | section « Hall + RFID alternative » pour chaque pas |
| Tests | `tests/test_hall.py`, `tests/test_nfc.py`, `tests/test_hallscan_config.py` | forme fermée et dipôle, marges, un groupe avec aimants uniformes et trois avec aimants codés, puissance, cadence, verdict du mux, gardes qui tirent, en-tête généré |
| Firmware du scanner | `firmware/esp32/hallscan/` | logique C99 testée sur PC et en CI (seuils, hystérésis, anti-rebond, ligne `B` de la note 12), en-tête généré du yaml, projet ESP-IDF pour l'ESP32-S3 |

Ce qui n'est pas fait : la carte KiCad de la nappe Hall (elle attend
la décision de la section 7 ; `boardgen` sait la produire, c'est un
circuit de 16 capteurs, un mux et quatre FET par quadrant), la
compilation ESP-IDF (pas de chaîne en CI, comme pour le pont et
l'horloge), et la relecture des trois valeurs de fiche marquées à
vérifier.

## 6. Ce que changent les cases de 55 ou 60 mm du brief

Même modèle, même aimant (dont le diamètre suit la base, donc le pas) :

| Pas (mm) | B pion nominal (mT) | B roi soulevé (mT) | Marge au soulèvement | Diaphonie de 8 voisins (dB) | Groupes avec aimants codés | k NFC | Marge ISO |
|---|---|---|---|---|---|---|---|
| 40 | 17,3 | 2,3 | 2,1 | -21,2 | 2 | 0,29 | 3,8 |
| 50 | 25,3 | 3,8 | 1,9 | -24,7 | 3 | 0,22 | 3,2 |
| 55 | 28,3 | 4,6 | 1,8 | -26,0 | 3 | 0,19 | 3,0 |
| 60 | 30,6 | 5,4 | 1,7 | -27,1 | 3 | 0,16 | 2,8 |

La diaphonie s'améliore avec le pas, la marge au soulèvement se
resserre un peu (le roi porte un aimant plus gros qui se voit de plus
loin) et tout reste dans les critères. Le brief n'a aucune raison
physique de préférer 55 à 50 ; le choix du pas reste celui de
l'ergonomie et du couloir de déplacement (ADR 0010).

## 7. Ce qu'une ADR trancherait

1. **Couche Hall de présence : oui ou non, et sur quelle carte** (nappe
   séparée pour l'étape intermédiaire, puis six couches ou spirale à
   trois couches pour l'intégrer au quadrant). La recommandation de
   cette note : la nappe, maintenant.
2. **Capteur et alimentation** : DRV5053OA, par groupes de rangées ;
   SS39ET si le prix ou le stock l'imposent, par groupes
   obligatoirement.
3. **Codage par polarité ou par épaisseur** : non, tant que l'aimant
   permanent du chariot reste candidat ; à rouvrir si l'électroaimant
   est choisi.
4. **RFID sur le plateau** : non en phase 1 ; plan de repli à un
   lecteur par case si M2 échoue ; lecteur sur le chariot à étudier en
   phase 2.
5. **Mesure M12 à ajouter au protocole** : courbe B(z) et B(rho) d'un
   aimant de pièce relevée au capteur de la nappe, comparée à
   `hall.disc_bz_mT` ; puis la courbe de soulèvement, qui fixe les
   seuils réels à la place des fractions du yaml.
