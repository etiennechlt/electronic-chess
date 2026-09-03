# 09. Journal des décisions et pivots

Chronologie condensée, source : l'historique git (`git log --reverse`)
et les ADR. Les entrées gardent le pourquoi, pas le détail (le détail
est dans les notes 03 à 06).

## 29/08/2026, fondations (phase 0)

- Socle : `board.yaml` unique source, `chessboard_calc`, garde-fou
  couloir bloquant en CI, conventions du dépôt (français, pas de
  tirets longs, travail sur `main`).
- Décisions structurantes posées en ADR : résonateurs LC passifs
  (0001), **aimants pièces en ferrite et jamais néodyme** (0002, la
  décision pivot du projet), STM32 maître et Pi optionnel (0003),
  détection PCB quatre quadrants (0004), architecture d'alimentation
  et de bruit (0005), pas p ouvert 40/50 paramétrique (0006), double
  voie d'extraction FFT plus période (0007).

## 29/08/2026, la maquette prend forme

- ADR 0008 : maquette en deux cartes ; le mux pressenti ADG709 est
  écarté au profit du **74HCT4052** (seuils TTL pilotables par un MCU
  3,3 V sur un rail 5 V), excitation hors mux par FET dédié.
- `coilgen` : spirales 4 couches en série ; leçon : les jonctions
  inter-couches alignées sur le rayon du terminal superposaient les
  vias, d'où les arcs de liaison à 90 degrés. Les trous du support
  d'aimant passent de 30 à 34 mm pour ne pas percer la spire externe.
- Firmware compilable (CMSIS nu), mécanique CadQuery, protocole M1 à
  M9, visuels, tests analoggen : la phase 1 est presque complète en
  une journée, sauf le routage.

## 29 au 30/08/2026, la bataille du routage

Progression des liaisons ouvertes de la carte analogique : 57, 51,
46, 40, 21, 16, 12, 9. Les jalons :

- Rasterisation conservative et marquage du cuivre à l'étendue vraie ;
  marge de routage relevée contre l'arrondi de grille.
- Méthode des **seeds répétés hors build** contre la géométrie réelle
  des pads, avec gardes au build (note 05) ; leçons payées : rayon des
  vias contre les rails, moignons de sortie, croisements seed contre
  seed.
- **Passe de garantie** : tout cuivre sous la garde de fabrication est
  retiré et réouvert en chevelu ; la carte part toujours DRC zéro.
- **Autopsies géométriques exactes** du cuivre pré-retrait : trois
  trous de légalité réels identifiés et corrigés à la racine (frange
  de raster des cellules de départ, couloir own par les marques de
  pistes, moignons de masse trop larges) ; deux impasses essayées puis
  annulées (entrée cible libre, puis bornée).
- Constat de **saturation** : chaque seed supplémentaire dans la bande
  des cellules déplaçait plus de nets qu'il n'en fermait ; gel à 18
  restes, puis la **passe de finition à géométrie exacte** (note 04)
  les ramène à 9. L'histoire du canal de 0,52 mm : la garde passe de
  0,137 à 0,132 parce que 0,524 exigés dépassaient de quatre microns.

## 30/08/2026, approvisionnement

Fiche comparée Europe contre Asie, prix relevés et datés.
Enseignements chiffrés : AD8421 à moitié prix chez LCSC (3,69 contre
8,91 USD), ADuM1201 en rupture DigiKey mais plus de 11 000 en stock
LCSC, et le contre-exemple : la Nucleo est moins chère et plus sûre en
Europe (eStore ST) qu'en revendeur asiatique. Panaché conseillé en
quatre commandes.

## 01/09/2026, LED de camp et surface bois (ADR 0009)

- Demande produit : deux points lumineux par case indiquant le camp
  occupant, sur une surface en bois (référence visuelle : plateaux du
  commerce à points aux coins).
- Choix : 2 WS2812B par case aux coins opposés (un coin partagé entre
  deux cases de camps opposés serait ambigu), chaîne unique extensible
  au 8 x 8 ; analyse bois : effet nul sur la fréquence, seuls comptent
  l'épaisseur et l'humidité (mesure M10 ajoutée).
- Intégration : couloirs In1/In2/B de la carte bobines (note 05),
  joint porté à 12 broches, tampon 74AHCT1G125 côté analogique
  (déplacé près du connecteur MCU après un premier placement qui
  faisait échouer LED_DIN), pilote bit-bang DWT (TIM2 occupé par la
  capture), fenêtrage structurel (M11), gabarit de perçage
  `surface-template`.
- Leçon de re-routage : le déplacement du joint et les deux nets
  nouveaux ont d'abord déplacé cinq signaux ; le repositionnement du
  tampon a tout refermé côté LED. Référence : 499 pistes, DRC zéro,
  sept couloirs saturés restants.

## 02/09/2026, plateau 8 x 8 direct, base interchangeable, horloge (ADR 0010)

- Point de départ : ouverture des cartes de la maquette dans KiCad 9
  sous Debian, question « peut-on imprimer huit fois la carte bobines
  pour faire l'échiquier ». Réponse : non (64 cases, carte analogique
  à quatre voies, connecteurs de bord), et le porteur ne veut pas
  traîner plusieurs versions : on conçoit directement le 8 x 8.
- Choix successifs, avec leurs raisons dans la
  [note 10](10-plateau-8x8-et-horloge.md) : p = 50 (signal et Q du
  pion noir), quatre quadrants 4 x 4 intelligents, LED identiques sur
  toutes les cases, chariot optionnel dans une base clipsable avec les
  ailes de capture (inspiration Chessnut Air : plateau fin d'abord),
  électronique et cellules plates au fond de la base sur une empreinte
  commune (le bandeau arrière à 18650 a été refusé), MCU soudé,
  emplacement ESP32-S3 plus Pi, horloge séparée à bascule en BLE
  avec sa propre 18650.
- Outillage : rendu matplotlib jugé illisible, remplacé par un
  rasteriseur à tampon de profondeur et par une vue interactive
  three.js générée depuis les modèles CadQuery.
- Leçon : l'entrefer d'air sous le bois (LED de 1,6 mm) était
  implicite dans la maquette ; il est maintenant un paramètre
  (`gap.air_mm`) compté dans le signal.

## 03/09/2026, générateurs de cartes

- Quadrant : frontal complet (cellules, deux ADG1607, décodeurs,
  chaîne) placé et routé par un routeur A* multicouche écrit pour
  l'occasion ; cellules disposées autour des bandes d'échappée après
  qu'une garde trop laxiste (centre au lieu d'emprise) avait posé des
  composants sur les voies. Bande élargie à 20 mm et bordure bois à
  20 mm pour laisser de la place.
- Cerveau, puissance, moteurs, horloge : générateur générique
  `boardgen` (placement par blocs et étagères depuis les cours réels,
  routage en deux grilles, plan de masse), [note 11](11-cartes-du-plateau.md).
- Leçons : les fiches techniques externes ne sont pas accessibles
  depuis l'environnement de génération, donc chaque composant vient
  des bibliothèques KiCad (brochage vérifié) ou est marqué à vérifier ;
  un routeur qui gonfle les obstacles pour la piste large bloque les
  passages entre broches traversantes, d'où la grille séparée pour les
  signaux.
- Sorties des boîtiers fins : les nets des QFN, LQFP, TSSOP et
  connecteurs FPC restaient tous ouverts, le routeur ne pouvant pas
  quitter une broche au pas de 0,5 mm ; chaque broche reçoit un tronçon
  de sortie avant routage (`quadgen.escape`) et les passifs sont
  espacés de 1,2 mm pour laisser passer un via. Le premier essai
  traçait les tronçons dans la direction radiale, ce qui envoyait ceux
  des connecteurs en rangée sur la broche voisine : ils suivent
  désormais l'axe long de la broche. Les tronçons seuls ne suffisaient
  pas : tout bus routé devant une rangée la murait sur la couche
  supérieure, et un tronçon voisin routé rendait la grille aveugle au
  pas de 0,5 mm. D'où l'éventail complet (tronçon, petit via sur deux
  rangées alternées, couloir de sortie sur la couche interne, cellules
  rendues au net après chaque routage) et l'ordre de routage qui sort
  les boîtiers fins en premier, [note 11](11-cartes-du-plateau.md).
- Horloge sur le même module ESP32-S3-WROOM-1 que le cerveau (une
  référence, une chaîne d'outils) ; protocole texte commun
  ([note 12](12-protocole.md)), firmware du pont et de l'horloge
  écrits (`firmware/esp32`), logique de pendule testée sur PC.

## 03/09/2026, phasage et livrables

- Décision : phase 1 sans chariot jusqu'à une partie jouable de bout en
  bout, chariot en phase 2 ; la carte moteurs et la base chariot
  restent conçues mais ne sont ni commandées ni testées avant.
- STL et STEP de `mechanical/exports/` désormais versionnés, la vue 3D
  interactive reste régénérée à la demande ; schémas d'architecture et
  d'empilement refaits pour le plateau 8 x 8 ; note 13 (ouvrir,
  vérifier, tester) et note 07 réécrite en feuille de route.

## 03/09/2026, revue des cartes (lot 1)

- Le schéma généré du quadrant reliait GND à 5VA (groupes qui se
  chevauchaient) ; l'émetteur espace désormais les groupes d'après leur
  hauteur réelle et un test compare la netlist KiCad de chaque carte au
  circuit. Le DRC de KiCad, lancé par `pcbnew` (`tools/drc.py`), a montré
  que le lecteur de cours d'empreinte ne comprenait pas les bibliothèques
  KiCad 7 : cellule du quadrant recomposée sur les cours réelles, module
  ESP32 au bord du cerveau avec son antenne hors carte, cour réduite et
  assumée sur l'horloge ; règles du projet alignées sur les vias
  d'éventail, vias hors des trous de connecteurs, net tie des bobines
  déplacé hors du trou de via. Plus grave : les vias d'empilement des
  bobines, posées sur le rayon intérieur ou extérieur, recouvraient les
  spires des autres couches et court-circuitaient la bobine (le
  contrôle maison exemptait les paires A/B) ; elles sont désormais
  décalées radialement hors des bandes, la maquette reste à corriger.
- Erreurs de câblage corrigées : FET d'entrée du BQ24610 en canal P
  (ACDRV actif bas), sources des FET DSG et CHG du BQ76920, réseau de
  température et consignes de charge (50 mohms, 1 A), UART de l'ESP32
  croisée sur le cerveau, lecture de charge et rétroéclairage de
  l'horloge. Détail et points restants dans la
  [note 14](14-revue-des-cartes.md).

## Où en est la ligne de temps

Phase 0 faite ; la phase 1 (maquette) est conçue mais ne sera pas
construite : le plateau 8 x 8 est engagé directement (ADR 0010), avec
son module plateau, ses bases et son horloge modélisés. Suivent le
générateur de quadrant, le cerveau, l'horloge, puis les mesures.
Voir [l'état](07-etat-et-reste-a-faire.md).
