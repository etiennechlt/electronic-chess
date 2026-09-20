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

## 07/09/2026, skills embarqués

- kicad-happy passé en v2.2.1 (correctifs des analyseurs et de la
  simulation), et trois skills de pcba-design-skills embarqués pour le
  lot 3 (`release-pcba-fabrication`, `operate-jlcpcb-order`) et la
  relecture de routage (`pcb-layout-review`) ; les cinq autres écartés,
  raisons dans `VENDORED.md`. Usage par lot dans la
  [note 15](15-skills-embarques.md).

## 07/09/2026, doc alignée sur le yaml et coût des cartes

- La doc était en retard sur `config/board.yaml` : le README du
  quadrant annonçait 216 x 200 mm avec une bande de 16 mm, l'ADR 0010
  et la note 10 un module de 420 x 420 mm avec une bordure de 10 mm,
  l'ADG726 et une nappe IDC. Les valeurs vraies (bande et bordure de
  20 mm, quadrant 220 x 200, module 440 x 440, deux ADG1607, nappe FPC
  16 broches) sont maintenant dans ces trois documents et dans le
  README de la racine ; le yaml et `tests/test_plateau.py` n'ont pas
  bougé, la doc a rattrapé.
- Réflexion ouverte sur le coût des cartes, le quadrant en tête
  (220 x 200 mm, 4 couches, cinq pièces au minimum) : devis JLCPCB à
  demander avant toute décision, différentiel vrai contre
  single-ended à trancher avant de chiffrer, piste des tuiles
  100 x 100 examinée et non tranchée, quadrant intelligent à
  instruire en ADR. Le tout dans la [note 16](16-cout-des-cartes.md).

## 13/09/2026, le quadrant relu pour être redessiné

- Constat du porteur : ouvert dans KiCad, le schéma du quadrant (et du
  cerveau) ne montre aucune liaison entre composants. Cause : le schéma
  généré est « par étiquettes », une étiquette globale par broche et
  aucun fil ; la netlist est juste (note 14) mais rien n'est lisible.
- Note 17 : fonction du quadrant, cycle d'une mesure d'après le
  firmware, composants et rôle bloc par bloc, câblage broche à broche,
  variante 2 x 2 (4 cellules, un seul ADG1607, 120 x 100 mm) et deux
  points de conception relevés en relisant (retour de roue libre qui
  dépend de la lenteur de Q1, rappel du P-FET d'amortissement vers VIN
  sans effet derrière un 74HC154). Proposition : redessiner en feuilles
  hiérarchiques à fils depuis le même circuit Python, 2 x 2 d'abord.
- Le commit du 02/09 sur la série vidéo (calendrier, rôles, publication
  en différé), resté sur une branche de session, est repris sur `main`.

## 13/09/2026, schéma dessiné et quadrant 2 x 2

- Nouveau moteur de schéma (`analoggen/sheets.py`) : feuilles
  hiérarchiques, composants placés par gabarit et reliés par des fils,
  étiquettes globales pour les rails et le bus, locales pour les nets
  internes ; le dessin est vérifié contre le circuit avant écriture et
  la netlist relue par kicad-cli est comparée au circuit en test.
  Leçon : KiCad ne relie que des extrémités de segments, un point de
  jonction posé au milieu d'un fil ne connecte rien tant que le fil
  n'est pas coupé là ; et il repositionne les champs justifiés d'un
  symbole tourné, d'où des textes centrés à position calculée.
- Circuit du quadrant : diode de roue libre par cellule et R7 à
  470 ohms (le rail doit être coupé avant la fenêtre d'écoute, pas
  maintenu), rappel du P-FET d'amortissement supprimé, spirale dessinée
  en inductance, écrêteurs BAV99W en SOT-323 pour loger la diode de
  roue libre dans la cellule ; les résistances restent en 0603, un
  essai en 0402 laissait le routeur sans point de départ sur 44
  pastilles de VREF du 4 x 4.
- Quadrant réduit 2 x 2 (`--reduced`, `plateau.quadrant.reduced`) :
  quatre cellules, un mux, huit LED, bande de frontal qui dépasse de
  2 p vers le sud, même firmware.

## 17/09/2026, carte de banc fermée, cœur de boardgen corrigé

- Carte de banc (shield Nucleo du quadrant 2 x 2) fermée jusqu'au
  bout : 29 nets, zéro ouvert, DRC KiCad zéro défaut. Le DRC comptait
  31 connexions manquantes là où le build en annonçait six : couloirs
  de sortie des vias d'éventail sans cuivre, routes finissant sur le
  coin arrondi d'une pastille, pastille déclarée atteinte sans preuve,
  piste de puissance refusée le long d'une piste d'envol, seeds d'un
  net jamais rejoints. Tous corrigés dans le cœur, qui vérifie
  maintenant la connexité exacte de chaque net après routage
  ([note 04](04-routeur-et-garanties.md)).
- Les liaisons que le routeur ne trouve pas sont dessinées comme dans
  pcbnew mais dans le générateur : éventail du FH12 à seize broches sur
  les deux faces, sorties du buck, longues liaisons 3V3, 5V_LED et
  AMP_OUT1 en face avant ([note 05](05-seeds-et-couloirs.md), README
  de la carte). KiCad 7.0.11 installé dans l'environnement pour le
  DRC ; les empreintes posées reçoivent des `tstamp` uniques, sans
  quoi le rapport DRC nomme les mauvais éléments.

## 19/09/2026, la carte analogique de maquette fermée

- Point de départ : KiCad comptait vingt-huit éléments non connectés
  sur la carte commitée, le build en annonçait sept. L'écart venait du
  modèle : la masse n'était pas vérifiée, les couches étaient
  fusionnées sans exiger de via, et une pastille valait la boîte
  autour d'elle. Le modèle exact du quadrant a été branché sur la
  carte analogique (`tools/analoggen/connect.py`), avec la forme vraie
  des pastilles et le plan de masse calculé comme le calcule le
  remplisseur de KiCad, îlot par îlot.
- Résultat immédiat : dix-neuf des vingt-huit liaisons manquantes
  étaient des masses, des groupes de pastilles reliés entre eux en
  face avant mais jamais descendus vers un îlot que le plan gardait
  entier. Une passe de finition de la masse, jouée contre les îlots
  réels, les a fermées.
- Deux outils ajoutés : un **labyrinthe** à géométrie exacte
  (`tools/analoggen/maze.py`, trame 0,05 mm, deux couches, via et
  coude payants) pour les liaisons qu'aucun raccord simple ne ferme,
  et des **routes structurelles** tracées avant le routage dans des
  canaux mesurés libres de pastilles.
- Deux défauts que la fermeture a mis à nu, corrigés dans la foulée :
  la broche 2 du jack, 1 mm hors du contour depuis l'origine (le jack
  recule à x = 8, son corps dépasse à l'ouest comme il se doit), et le
  fichier de carte qui déclarait quatre couches cuivre pour une carte
  deux couches, ce qu'un fabricant aurait facturé et gravé tel quel.
  Les gerbers de la carte sont désormais produits par
  `tools/gerbers.py`, pours remplis, et commités.
- Puis les 49 chevauchements de courtyard, la dernière famille que le
  DRC signalait encore. Quarante-quatre venaient du motif de cellule,
  dont les rangées étaient espacées sur les pastilles et non sur les
  courtyards ; les cinq autres, de voisinages serrés autour du jack et
  du réservoir. Le placement est repris, et le build vérifie désormais
  cette famille lui même (`tools/analoggen/yards.py`).
- Le prix du déplacement : tout le routage se rejoue. Trois tours de
  build ont été nécessaires, et chacun rouvrait deux à cinq liaisons
  ailleurs. La réponse n'a pas été de les fermer une à une mais de
  poser ce qui manquait structurellement : une **épine de masse** par
  cellule sur la face arrière, avec la descente de ses deux pastilles
  les plus fragiles, et une nappe pour la ligne la plus longue de la
  carte, celle que le routeur essaie en dernier quand la bande sud est
  pleine.
- Le placement corrigé a rouvert le routage une dernière fois, et la
  réponse a de nouveau été structurelle plutôt que liaison par
  liaison : la traversée de sa rangée par la ligne B de chaque
  cellule, face avant, dans le canal de 0,86 mm entre les deux
  rangées ; le contournement du coin sud-est, qui ne porte aucune
  pastille, pour la ligne B de la cellule 4 ; la descente de sa rangée
  B par la face arrière de la bande, où l'écrêteur et le FET, tous
  deux en CMS, ne bloquent rien ; une épine de masse pour le tampon
  LED, coincé sous le connecteur Nucleo entre vingt échappées ; un
  tour de routage de plus, puisque chaque tour promeut ce que le
  précédent a manqué ; et un labyrinthe qui dégrossit sa trame (0,1
  puis 0,2 mm) quand la liaison traverse la carte, au lieu
  d'abandonner sur son plafond d'exploration. Résultat : **568 pistes,
  288 vias, zéro liaison ouverte, zéro DRC, zéro chevauchement**.
- Deux tentatives ont coûté un build chacune et valent d'être notées,
  parce qu'elles disent la même chose : une amorce posée dans un
  couloir occupe ce couloir. Une descente de masse tracée au milieu de
  la colonne d'échappée du connecteur a rouvert trois lignes
  d'excitation ; remise en épine, parallèle aux échappées au lieu de
  les croiser, elle ne gêne plus personne. Avant de poser une route
  structurelle, regarder par où passent celles qui existent déjà.
- Leçon retenue et écrite dans la [note 04](04-routeur-et-garanties.md) :
  la « saturation » qui justifiait d'arrêter à sept liaisons était un
  artefact du compte. Un mauvais arbitre fait prendre les mauvaises
  décisions pendant des jours ; le compte exact a renversé la
  conclusion en une journée.

## 20/09/2026, devis, passe de finition partagée, cerveau et 4 x 4

- Le devis JLCPCB de vingt cartes 2 x 2 (281 EUR) est démonté ligne par
  ligne ([note 23](23-commande-jlcpcb.md), le document « Cartes du
  damier ») : six codes LCSC sur douze étaient des candidats jamais
  vérifiés et JLCPCB les a pris au mot, dont un codec audio à 7,47 EUR
  pièce à la place de l'AD8421 (149 EUR sur 281). Le format au dessus
  de 100 x 100 ne coûte que le frais d'ingénierie, 21,73 EUR par
  commande ; un 2 x 2 en 100 x 100 serait un nouveau plan de frontal
  en croix entre les bobines, 3 à 5 jours, et l'offre spéciale impose
  0,5 oz interne. Décision en attente : tuile du plateau ou carte de
  mise au point.
- KiCad 7.0.11 et ses bibliothèques s'installent dans l'environnement
  distant depuis l'archive Ubuntu (les PPA sont bloqués) : DRC, gerbers
  et tests des générateurs y tournent.
- Le firmware du banc pilote un quadrant 4 x 4 complet sur le même
  shield : `make NUCLEO=1 NUCLEO_FULL=1`, seize bobines derrière
  MUX_EN_H, chaîne de 32 LED générée du yaml ; budget du banc et
  précaution sur le courant des LED dans la note 19.
- La passe de finition et le labyrinthe de la carte analogique sont
  portés sur le modèle de cuivre partagé (`tools/quadgen/finish.py`,
  [note 04](04-routeur-et-garanties.md)) et branchés sur les trois
  générateurs ; un instantané du routage (`QUADGEN_DUMP`,
  `BOARDGEN_DUMP`, `--resume`) permet de rejouer la passe et les
  contrôles en secondes. Leçons : borner la famille à deux vias (neuf
  minutes sur un cas de vingt millimètres avant), faire partir le
  labyrinthe de la plus petite pièce, essayer le via fin après le via
  standard, donner un budget de temps à chaque net.
- Cerveau, régénéré : 23 nets ouverts, presque tous aux quatre
  connecteurs FPC dont les broches sont murées par leurs propres
  éventails ; le bus routé en premier plus la passe de finition en
  laissent 18. Réponse structurelle, comme sur le banc : les éventails
  des quatre liens sont dessinés à la main sur la face avant (voies de
  0,3 mm en escalier, un petit via au bout de chacune, les masses
  descendues au plan à leur moignon), la bande médiane descend de
  2,2 mm sous eux.
- Quadrant 4 x 4, régénéré pour la première fois depuis la comptabilité
  exacte : 36 nets ouverts, les entrées des deux mux, les sorties des
  décodeurs, la colonne des amplificateurs, 5VA, VREF et sept îlots du
  plan de masse ; le routage seul prend 27 minutes.
- Estimation du prix du plateau, cartes nues et assemblées, poste par
  poste (note 23, section 8) : 300 à 350 EUR hors taxes en cartes nues,
  430 à 480 EUR assemblé, dont 120 à 140 EUR de silicium analogique
  pour les quatre frontaux.

## Où en est la ligne de temps

Phase 0 faite ; la phase 1 (maquette) est conçue mais ne sera pas
construite : le plateau 8 x 8 est engagé directement (ADR 0010), avec
son module plateau, ses bases et son horloge modélisés. Suivent le
générateur de quadrant, le cerveau, l'horloge, puis les mesures.
Voir [l'état](07-etat-et-reste-a-faire.md).
