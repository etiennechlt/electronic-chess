# Note 13 : ouvrir, vérifier et tester les cartes

Où regarder et quoi lancer pour passer des fichiers générés à des
cartes commandées puis mesurées. Tout part de `config/board.yaml` ;
un chiffre qui n'en découle pas est suspect.

## 1. Ouvrir un projet dans KiCad 9

Les cinq projets sont dans `hardware/<carte>/<carte>.kicad_pro`
(`quadrant`, `brain`, `power`, `motion`, `clock`) ; la maquette 2 x 2
de référence dans `hardware/mockup-2x2/`.

- Fichiers au format KiCad 7 : KiCad 8 ou 9 les ouvre et propose la
  conversion au premier enregistrement. Symboles et empreintes sont
  embarqués, rien à installer. Le `.kicad_prl` créé à l'ouverture est
  ignoré par git ; une régénération remet le projet dans son état
  canonique (voir la [note 08](08-regenerer.md)), donc modifier le
  générateur plutôt que le fichier quand la modification doit durer.
- Modèles 3D : pointer `KICAD6_3DMODEL_DIR` (ou la variable de votre
  version) vers les modèles de la distribution si la vue 3D reste vide.
- Le schéma est généré en feuille unique, groupé par bloc fonctionnel
  (cellules, mux, chaîne, alimentation...). Il porte les mêmes nets
  que le PCB : `tests/test_quadgen.py::test_schematic_exports_a_netlist`
  et `tests/test_boardgen.py::test_schematic_netlists` exportent la
  netlist avec `kicad-cli` et la comparent au circuit Python.

## 2. Vérifier que tout correspond

| Question | Où c'est garanti | Ce qu'il reste à faire à la main |
|---|---|---|
| Le PCB suit le schéma | même objet `Circuit` pour les deux, netlist exportée et comparée par les tests | rien, sauf après une retouche manuelle dans pcbnew : relancer « Mettre à jour le PCB depuis le schéma » ne s'applique pas (schéma généré), comparer plutôt avec `Outils > Comparer les netlists` |
| Les broches des circuits intégrés | symboles des bibliothèques officielles KiCad, câblage par nom de broche (`pins_by_name`), refus de toute broche inconnue ou oubliée | valider contre la fiche technique les brochages marqués « à vérifier » : STM32G474 (fonctions alternatives des ADC, USART3 sur PC10 et PC11, I2C1 sur PA15 et PB7), BQ24610 et BQ76920 (application type), orientation des câbles FPC et USB-C ; liste dans la [note 11](11-cartes-du-plateau.md) |
| Les valeurs des composants | dérivées du yaml par `chessboard_calc` et épinglées par `pytest` ; `python -m chessboard_calc.report` imprime tout (fréquences des 12 classes, Q, séparation, bobines, entrefer, budget de puissance, autonomie) | les consignes de charge (ISET, ACSET, diviseur VFB, CTN) suivent l'application type de TI : revue en lisant la fiche BQ24610 ; les diviseurs de mesure et les RC de sortie se relisent sur le schéma |
| Les pistes | contrôle d'isolement exact (shapely) à chaque build et sur chaque route candidate, largeur et isolement dans le `.kicad_pro` | lancer le DRC de KiCad 9 (`Inspection > Contrôle des règles`) ; fermer les nets ouverts listés dans le README de chaque carte ; confirmer les vias 0,45 mm chez le fabricant |
| L'intégrité de signal | plan de masse continu, RC devant chaque ADC, buck 2,5 MHz en PWM forcé loin de l'analogique, lignes de mesure sur B.Cu et grille sur In2 du quadrant ([note 11](11-cartes-du-plateau.md)) | revue visuelle des retours de masse sous les lignes de mesure après fermeture manuelle des nets |
| La mécanique | `tests/test_plateau.py` (empilement, empreintes des cartes dans la base, LED dans leur case), vues éclatées | rien avant impression |

## 3. Simuler

- Chaîne d'amplification du quadrant : `hardware/quadrant/chain-spice.cir`
  (AD8421 en gain 20 puis Sallen-Key passe-haut et passe-bas), à
  lancer avec `ngspice -b hardware/quadrant/chain-spice.cir`. Le
  critère : gain plat de 200 à 650 kHz, coupures à leur place.
- Cellule d'excitation et amortissement : pas encore de banc SPICE ;
  à écrire sur le modèle du `chain-spice.cir` avant la commande
  (bobine 16 µH, écrêteurs, AO3400A, roue libre).
- Résonateurs et couplage : ce sont des calculs fermés
  (`chessboard_calc`), pas des simulations ; le rapport donne les
  largeurs de raie et la marge de séparation.

## 4. Commander

- Quadrant : 4 couches, 1,6 mm, 1 oz, assemblage face top ; commander
  quatre exemplaires du même fichier. `jlc-bom.csv` et `jlc-cpl.csv`
  sont dans `hardware/quadrant/`, gerbers à exporter depuis KiCad 9
  (`Fichier > Tracer`) une fois les nets fermés.
- Cerveau : 4 couches. Puissance, moteurs, horloge : 2 couches.
- Les codes LCSC du BOM sont des candidats saisis hors ligne : vérifier
  chaque ligne dans la prévisualisation JLCPCB (mêmes réserves que pour
  la [maquette](../../hardware/mockup-2x2/README.md)).
- La carte moteurs n'est utile qu'avec la base chariot : commander plus
  tard.

## 5. Tester

Dans l'ordre, un quadrant seul puis le cerveau :

1. **Quadrant hors tension** : continuité des bus (5VA, VREF,
   DRIVE_BUS, VIN, GND sur les points de test TP1 à TP4), absence de
   court entre rails, chaque bobine mesurée entre ses deux bornes
   (environ 16 µH, quelques ohms).
2. **Cerveau seul** : alimenter par USB-C, vérifier 5 V, 3,3 V, 5VA
   dans l'ordre, courant au repos, console série (`firmware/board`,
   115200 bauds, commande `h`).
3. **Quadrant sur le cerveau** : nappe FPC, `1` scanne les 16 bobines,
   CSV `q,coil,sq,fa_hz,fb_hz,amp_mv,snr_db10`. Un puck de test posé
   sur une case doit donner sa fréquence de classe et un SNR positif.
4. **Mesures M1 à M11** du [protocole](../../measurements/protocol.md) :
   écrit pour la maquette, il s'applique tel quel avec le quadrant à
   la place de la carte bobines et le cerveau à la place de la Nucleo ;
   les CSV vont dans `measurements/data/`, l'analyse dans le notebook.
5. **LED** : `l` allume les camps, `o` éteint ; vérifier la chaîne des
   quatre quadrants par la sortie DOUT.
6. **Puissance** : d'abord sans cellules avec une alimentation de
   laboratoire limitée en courant sur PACK+, puis avec les cellules et
   la charge par USB-C PD, en surveillant les tensions de cellule par
   l'INA219 et le BQ76920 sur I2C.
7. **Horloge** : compilation ESP-IDF sur poste (`firmware/esp32`),
   barre, encodeur, buzzer, écran, puis appairage BLE avec le pont du
   cerveau et échange des lignes `C`, `T`, `N` de la [note 12](12-protocole.md).

## 6. Fichiers d'impression

`python mechanical/build_all.py` écrit les STL et STEP dans
`mechanical/exports/` (ignoré par git, une minute de calcul) : socle
fin, socle chariot, module plateau, boîtier, fond et barre de
l'horloge, pucks de test, gabarits de bobinage, support d'aimant.
Les STEP s'importent dans KiCad 9 pour vérifier les cartes dans leur
base.
