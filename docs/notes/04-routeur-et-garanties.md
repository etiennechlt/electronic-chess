# 04. Le routeur maison et ses garanties

La carte analogique est routée par un routeur écrit pour le projet
(`tools/analoggen/pcb.py`). Cette note capture ce qu'il fait, les
trous de légalité qu'il a fallu trouver et boucher, et les garanties
formelles qui font qu'une carte générée est toujours livrable.

## Le cœur : A* sur grille avec légalité par distance

- Grille de 0,125 mm, deux couches, coût de via 28, pénalité de
  couche arrière.
- La légalité est distance-based : transformées de distance
  euclidiennes des pads étrangers et du cuivre déjà posé donnent, par
  cellule, la marge exacte qu'un axe de piste doit tenir ; les
  échappées fines (TSSOP 0,65, QFN 0,5) restent routables sans jamais
  chevaucher.
- Rails structurels (VREF, 5VA) et seeds manuels posés avant le
  routage ([note 05](05-seeds-et-couloirs.md)) ; stubs de masse vers
  le plan arrière ; ordre des nets par taille avec promotion des
  échecs sur deux tours ; passe de rattrapage à marge minimale.

## Les trous de légalité, trouvés par autopsie exacte

La méthode qui a tout débloqué : sérialiser le cuivre avant toute
correction et mesurer en géométrie exacte (shapely) chaque paire en
défaut, jusqu'à nommer la cellule fautive. Trois mécanismes réels en
sont sortis, tous corrigés à la racine :

1. **Frange de raster des pads.** Les cellules de départ couvrent la
   boîte du pad arrondie à la grille (une cellule au delà du cuivre) ;
   une polyligne partant d'une cellule de bord balayait son demi-trait
   dans le pad voisin (QFN au pas 0,5). Correctif : les extrémités de
   chemin intérieures à la boîte sont rabattues sur l'axe long du pad
   (`emit_routed`), au départ comme à l'arrivée.
2. **Couloir « own » trop généreux.** Les cellules marquées par ses
   propres pistes (rayon w/2) étaient en passage libre : un chemin
   pouvait longer le bord de ses propres marques puis déborder d'un
   demi-trait chez le voisin, zone jamais validée. Correctif : own se
   limite aux pads ; un pad réellement en contact avec le cuivre de
   son net est marqué raccordé sans routage (contrôle géométrique).
3. **Moignons de masse trop larges.** Le canal entre la colonne ouest
   du QFN et son pad thermique fait 0,195 mm : un stub de masse en
   0,4 mm ne peut pas y être légal. Correctif : largeur fine sur pads
   fins.

Deux impasses instructives ont été essayées puis annulées : autoriser
l'entrée libre dans une cellule cible (raccords par les marques qui ne
touchaent pas le cuivre réel) et sa variante bornée ; le pré-contrôle
de contact réel les a remplacées.

## Les trous de connexité, trouvés au DRC de la carte de banc

Le DRC de KiCad sur la carte de banc (17/09/2026) comptait 31
connexions manquantes là où le bilan du build de `boardgen` n'en
voyait que six. Cinq mécanismes, corrigés dans `boardgen/core.py` :

1. **Couloir de sortie sans cuivre.** Le couloir réclamé derrière un
   via d'éventail était une réservation de cellules, pas du cuivre :
   une route qui commençait ou finissait dedans laissait jusqu'à 2 mm
   de vide entre le via et la piste. Le build dessine désormais le
   cuivre du couloir (0,2 mm, il passe l'autre rangée de vias au pas
   des pastilles) jusqu'au point où la route s'arrête, et le vérifie.
2. **Pastilles rondes et arrondies prises pour des rectangles.** Les
   cellules d'arrivée couvraient la boîte englobante : une route
   pouvait finir sur le coin d'une pastille ronde d'embase ou d'une
   pastille `roundrect` (presque toutes les CMS), coin que KiCad ne
   dessine pas. Les cellules d'arrivée et le contrôle d'isolement
   utilisent la forme réelle (`pad_copper`).
3. **Pastille supposée atteinte.** Quand aucun groupe en attente
   n'était reconnu au bout d'une route (route finie par un via, ou sur
   une pastille traversante vue en deux groupes), le premier groupe
   était déclaré atteint sans preuve. Les vias comptent dans la
   détection, une pastille traversante est un seul groupe sur toutes
   les couches, et une route qui n'atteint rien laisse le net ouvert.
4. **Piste de puissance le long d'une piste d'envol.** Une piste de
   0,6 mm posée sur une piste d'envol de 0,2 mm frôlait le moignon
   voisin à 0,10 mm ; refusée par le contrôle exact, le net restait
   ouvert. Une route large refusée est rejouée fine avant abandon.
5. **Seeds d'un même net vus comme déjà reliés.** Deux seeds disjoints
   d'un net formaient d'emblée l'ensemble « relié » ; le routeur ne
   les rejoignait jamais. Chaque seed est une pièce de cuivre comme
   une pastille : ceux qui se touchent fusionnent sans route, les
   autres sont routés.

Le build lui-même porte maintenant la vérification que le DRC
faisait : un contrôle de connexité exact (shapely) sur le résultat,
chaque net une seule pièce de cuivre, le plan de masse comptant pour
une pièce sur sa couche ; un net en morceaux est listé ouvert quoi
qu'ait cru le routeur. Les chutes de masse choisissent une cellule
avec 0,9 mm de cuivre libre autour, pour que le plan les atteigne, et
chaque empreinte posée reçoit ses propres `tstamp` (les mêmes dans
toutes les instances d'une empreinte de bibliothèque, ce qui faussait
la lecture du rapport DRC). Les cartes de la phase 1 ont été générées
avant ces correctifs : elles portent les mêmes trous cachés jusqu'à
leur régénération ([note 07](07-etat-et-reste-a-faire.md)).

## La comptabilité de connexité, partagée (`tools/quadgen/connect.py`)

Le quadrant (`quadgen`, bande de frontal) et les cartes génériques
(`boardgen`) routent avec le même treillis mais tenaient chacun leur
propre comptabilité de ce qui est relié ; celle du quadrant avait les
trois défauts corrigés sur le banc (tout le cuivre déjà tracé compté
comme une pièce, pastilles prises pour des rectangles, pastille
supposée atteinte), d'où deux nets ouverts annoncés pour 117
connexions manquantes au DRC. Depuis le 18/09/2026 cette comptabilité
n'existe qu'en un exemplaire, importé par les deux générateurs :

- **Pièces de cuivre** (`net_pieces`) : avant de router un net, ses
  pastilles, tronçons d'échappée, bus, seeds et vias sont groupés par
  contact réel (géométrie exacte, union-find) ; chaque composante est
  une pièce, avec les cellules du treillis où une route peut partir ou
  arriver : le cuivre réel de la pastille (jamais un coin arrondi), son
  tronçon d'échappée et sa piste d'envol, le couloir de sortie de son
  via d'éventail, les échantillons d'une piste, un via sur toutes les
  couches. La composante du premier seed, ou du premier bus, mène.
- **Boucle de fermeture** (`close_net`) : le routeur part des pièces
  reliées vers les pièces en attente ; une pièce que le cuivre relié
  touche déjà n'a pas besoin de route ; une pièce ne compte atteinte
  que si une route y finit ou qu'un via y tombe (`reached`) ; une route
  qui n'atteint rien laisse le net ouvert avec sa raison.
- **Cuivre de couloir** (`exit_copper`) : la route qui part ou finit
  dans le couloir d'un via d'éventail reçoit la piste fine qui la relie
  au via.
- **Contrôle final** (`connectivity_check`) : chaque net une seule
  pièce, un plan de masse comptant pour une pièce sur sa couche, les
  îlots de piste comptés comme des pièces ; le compte du build est
  celui que KiCad fera.

Le banc régénéré avec cette version reste fermé (29 nets, DRC KiCad
sans erreur ni élément non connecté) ; le routage de la bande du
quadrant a été réécrit dessus, avec deux treillis (pistes larges pour
les alimentations, fines pour le reste) comme sur les cartes
génériques, et des routes manuelles (`seed`, `seed_via`) pour ce que
le routeur ne trouve pas.

## La géométrie qui empêchait de router (bande du quadrant)

Une fois la comptabilité juste, le compte des connexions manquantes du
quadrant 2 x 2 n'a pas bougé : le routeur ne cherchait pas mal, la
géométrie lui interdisait de réussir. Trois causes, corrigées à la
racine, et une méthode : mesurer avant de router.

1. **Des bus qu'aucun via ne peut atteindre.** Les quatre bus
   d'alimentation de la bande (5VA, VREF, bus d'excitation, 12 V) sur
   In1 étaient posés au pas de 0,8 mm, avec le rail 3V3 sur In2 au
   milieu et la grille 5 V des LED juste à l'est. Un via traverse
   toutes les couches : il lui faut, autour de son axe, le rayon de sa
   pastille plus l'isolement (0,375 mm) libre de tout bus des autres
   couches. Aucun des quatre ne l'avait. Les bus sont réespacés pour
   que chacun ait son couloir de via, et un test l'exige désormais
   (`test_supply_buses_have_a_via_channel`).
2. **Des prises de cellule impossibles à trouver.** Une cellule de
   bobine est quatre colonnes de composants empilés à 0,1 mm : le
   routeur n'a qu'un couloir de via par cellule et quelques rangées
   libres. Les prises (masse, 5VA, bus d'excitation, 12 V) sont donc
   dessinées dans le générateur (`tools/quadgen/hand.py`), placées
   depuis les pastilles réelles, les mêmes dans les quatre cellules du
   2 x 2 et les seize du 4 x 4.
3. **Une chaîne LED qui traversait le frontal.** Son retour vers le
   connecteur descendait au milieu de la bande sur In1. La chaîne sort
   maintenant par deux voies dessinées au connecteur, une par sens, et
   la bande lui est fermée.

Le plan de masse de la bande, sur la couche arrière, remplace le bus de
masse et ses vias. Il n'est jamais d'un seul tenant : les échappées des
bobines le coupent en deux, les routes de la couche arrière y ouvrent
des criques. Le build calcule les îlots réellement remplis (même règle
que le remplisseur de KiCad : moins le cuivre étranger et son
isolement, puis les cols plus étroits que l'épaisseur minimale
pincés), garde ceux qui portent de la masse, et les fait recoudre par
le routeur comme deux pastilles d'un même net. Le contrôle de
connexité compte un nœud par îlot, donc un plan coupé ne masque plus
rien.

## Ce que le routeur ne peut pas trouver (quadrant 2 x 2)

Le compte du build et celui de KiCad étant devenus le même, la liste des
liaisons restantes était exacte : sept, et chacune a pu être expliquée
avant d'être tracée. Aucune ne vient d'un mauvais réglage du routeur ;
chacune demande un passage que sa grille ne sait pas voir. Elles sont
dans `tools/quadgen/hand.py`, dessinées avant le routage comme les
prises des cellules, donc le routeur route tout le reste autour d'elles.

1. **PULSE_EN, quatre pièces** : broche 14 du connecteur, grille du FET
   d'impulsion, sa résistance de rappel, entrée de l'inverseur du bloc
   central. Le champ d'échappées du connecteur est fait de vias au pas
   de 0,5 mm sur deux rangées, plus le via de la chaîne LED de la
   broche voisine, à pastille de 0,6 mm : il reste 0,475 mm de libre à
   l'est de la broche 14, là où une piste de 0,25 avec ses deux gardes
   de 0,15 en demande 0,55. La route à la main enfile ce chas en
   plongeant au nord d'un via puis en passant au sud de l'autre,
   0,21 mm de marge au pire point. Elle atterrit dans la pastille de
   grille, seul endroit où un via tient, et de ce via partent les deux
   autres branches, une nappe In1 qui descend le bord ouest de la bande
   jusqu'à l'inverseur (43 mm) et une autre vers l'est jusqu'à la
   résistance de rappel, dans la rangée libre sous la rangée de pads.
2. **M2_A et DAMP4_N, un signal par cellule.** Les deux sortent de leur
   cellule par le couloir de via entre la diode double et la colonne
   des FET, puis il leur faut une nappe sur toute la longueur de la
   bande (47 et 42 mm) pour rejoindre le multiplexeur au sud et le
   décodeur au centre. Le routeur paie chaque via et chaque coude : une
   nappe qui traverse la carte n'est jamais le choix local le moins
   cher, et quand vient leur tour, les couloirs pris par leurs voisines
   ne laissent plus de chemin continu. Les nappes sont donc posées :
   In1 à x = 11,45 (entre les vias de grille des cellules et le rail
   3V3), In2 à x = 3,1 (à l'ouest des cellules et des couloirs de
   sortie des blocs centraux).
3. **La colonne d'amplification, quatre pastilles** : l'entrée positive
   de l'amplificateur d'instrumentation, le diviseur de référence et
   les deux bouts de la résistance de gain. Les deux rails analogiques
   montent toute la bande sur les couches internes et traversent cette
   colonne : entre eux ils laissent 0,5 mm là où un via avec son
   isolement en demande 0,75, et aucun via ne tient dans les pastilles
   qu'ils enjambent. Les quatre se prennent donc sur la couche avant,
   par la rangée libre que leurs voisines laissent, exactement comme
   les cellules : l'entrée positive par la rangée entre les deux
   pastilles de son condensateur de liaison, le diviseur par la rangée
   entre les filtres et les amplificateurs, la paire de gain par cette
   même rangée puis par le couloir entre les deux colonnes de broches
   de l'amplificateur, sous son boîtier. La paire se croise une fois,
   en sortant de la colonne : une extrémité descend sur la couche
   avant, l'autre par un via et In2.
4. **La colonne de découplage du bloc central**, deux pastilles d'un
   même condensateur. Sa masse tombait dans une crique du plan que les
   routes autour du condensateur isolaient : le via n'atteignait que du
   cuivre que le remplisseur de KiCad retire, faute d'être relié. Elle
   se raccorde maintenant sur In2 à la pastille de masse du
   condensateur d'en dessous, dans la même colonne, dont la descente
   atteint le plan. La colonne fait 0,95 mm de large et un via perce
   toutes les couches : la nappe de masse longe son bord ouest et le
   5VA du condensateur du milieu garde à l'est la place d'un via, posé
   là lui aussi puisque c'est la place qui compte, le routeur venant le
   chercher ensuite.

Trois de ces liaisons ne sont apparues qu'après le tracé des premières :
chaque nappe posée déplace les choix du routeur. Les ressources rares
de cette bande sont le couloir ouest du bloc central, une bande de
2,7 mm où passent une dizaine de nappes, et la fenêtre de via à l'ouest
des rails, large d'un seul via. Une nappe intérieure qui traverse la
zone d'amplification y coupe quatre liaisons locales pour en fermer une,
d'où la version finale de la paire de gain sur la couche avant. Neuf
routages complets ont été nécessaires, et deux garde-fous les ont rendus
tenables : la vérification de géométrie avant routage
(`test_reduced_strip_geometry_is_legal_before_routing`, cinq secondes)
dit si le tracé est légal, et seul le routage complet (trois à quatre
minutes) dit ce que le tracé a déplacé. Résultat :
**zéro liaison ouverte, zéro élément non connecté au DRC de KiCad**.

Ces routes appartiennent au quadrant réduit, la carte en fabrication :
elles sont placées depuis ses pastilles réelles, mais quelles pièces
restent ouvertes dépend de l'agencement de la bande, et le 4 x 4
l'agence autrement (sa colonne d'amplification et ses multiplexeurs
sont ailleurs, et ses broches de multiplexeur échappent sans via). Il
aura ses propres liaisons quand viendra son tour d'être routé.

## Ce que le routeur ne peut pas trouver (quadrant 4 x 4)

Régénéré le 20/09/2026 avec la comptabilité exacte, les masses
descendues en premier et la passe de finition : 47 nets ouverts après
22 raccords, 27 minutes de routage et autant de passe. Les sondes
(pièces de chaque net, cellules utilisables autour des pastilles)
donnent la cause. C'est celle des quatre liens FPC du cerveau, un
champ d'échappées au pas de 0,5 mm que rien ne peut traverser, à trois
endroits de la bande :

1. **Les deux multiplexeurs se font face.** U3 (bobines 1 à 8) est à
   5,6 mm du bord ouest, U4 (bobines 9 à 16) à 5,6 mm du bord est,
   LFCSP-32 au pas de 0,5 mm. Les huit entrées B de U3 sortent vers
   l'ouest : leurs vias d'éventail sont à 0,95 et 1,65 mm du bord, en
   deux rangées au pas de 1 mm, et leur couloir de sortie sur In2
   pointe vers le bord. Entre deux vias d'une rangée il reste 0,25 mm,
   la largeur d'une piste sans ses gardes : seul le via du bout de
   chaque rangée est atteignable depuis le nord, d'où viennent les
   seize lignes M de la bande 0. Les huit entrées A de U3 sortent vers
   l'est, face aux huit entrées B de U4 : dans les 2,2 mm entre les
   deux champs de moignons, l'échappée n'a pu poser presque aucun via
   (treize des seize broches restent sans) et les moignons finissent en
   impasse sur la face avant, au pas de 0,5 mm, cinq pistes au plus
   pouvant remonter la fente. Bilan : 21 des 32 lignes M ouvertes, plus
   MUXA_OUT, MUX_A0 et MUX_A2, prises dans les mêmes champs.
2. **Les décodeurs à une seule rangée de vias.** U1 (74HC4514) et U2
   (74HC154), TSSOP-24 au pas de 0,65 mm, empilés au centre de la
   zone : une rangée de vias au pas de 0,65 mm (pastille 0,45,
   isolement 0,15, 0,05 de marge) et des couloirs de sortie sur In2
   qui partent vers l'est et l'ouest, perpendiculaires à la bande, alors
   que les sorties DRIVE et DAMP vont aux cellules au nord et au sud.
   Là aussi, seuls les bouts de rangée sont atteignables : neuf DRIVE
   et six DAMP ouverts.
3. **La colonne d'amplification**, comme sur le 2 x 2 : le filtre
   passe-bas et l'étage de sortie (LP_IN, LP_OUT, LP_FB, OUT_FB,
   OUT_STAGE), PULSE_EN, 5VA en quatre pièces, sept îlots du plan de
   masse que les routes de la face arrière isolent.

Ni l'ordre des nets (variante « fine_first », les broches fines en
premier) ni le coût de la face arrière n'y changent rien : la
géométrie interdit, le routeur ne cherche pas mal.

Ce qu'il faut est le motif qui a fermé le cerveau : des éventails
dessinés à la main dans le générateur, chaque broche prolongée sur la
face avant en une voie en escalier qui se termine par un petit via posé
là où il tient, les vias étalés au pas du millimètre, et le routeur qui
continue depuis ces vias sur les couches internes. Sur le 4 x 4 cela
demande de tourner les deux multiplexeurs pour que leurs côtés
d'entrées regardent le nord et le sud (vers les cellules) et non le
bord ou l'autre boîtier, de dessiner quatre éventails de huit broches
et deux éventails de douze pour les décodeurs, puis d'assigner à
chacune des 32 lignes M et des 32 lignes de grille une colonne sur In2
ou B.Cu entre les vias des cellules, la plus lointaine à l'extérieur.
Un lot de un à deux jours, chaque vérification coûtant un routage de
27 minutes ; il n'a pas été engagé le 20/09. Conséquence pour la
commande : aucune archive du 4 x 4 n'existe (`tools/gerbers.py`
refuse une carte au routage ouvert) et son prix
([note 23](23-commande-jlcpcb.md), section 8) reste une extrapolation
du devis du 2 x 2.

## Les quatre passes formelles

Ordre d'exécution dans `build_pcb` : routage, puis

1. **Passe de retrait** (`_strip_subclearance`) : tout cuivre sous la
   garde de la classe de nets, 0,15 mm, est retiré et sa liaison
   réouverte en chevelu explicite ; les paires pad contre pad relèvent
   du placement et sont listées. La garde jugée est bien celle de la
   classe de nets et non le plancher de fabrication de 0,127 mm : une
   piste à 0,136 mm est fabricable et KiCad la compte quand même comme
   une erreur, et le contrôle n'a d'intérêt que s'il dit ce que dit
   KiCad ([note 22](22-erreurs-de-conception.md), point 13).
2. **Passe de finition** (`tools/analoggen/finish.py`) : sur le cuivre
   fini, en géométrie exacte sans grille, elle referme les écarts par
   le raccord le plus simple (segment, L, Z balayés jusqu'à 6,4 mm,
   variantes face arrière à un ou deux vias, anneaux de via jusqu'à
   6 mm dans douze directions). Chaque raccord est tenu à 0,15 mm de
   tout cuivre étranger, c'est à dire la garde de la classe de nets,
   celle que le DRC de KiCad compte comme une erreur. Quand aucun
   raccord simple ne passe, un **labyrinthe**
   (`tools/analoggen/maze.py`) cherche sur une trame de 0,05 mm, deux
   couches, en payant chaque via et chaque coude : il a fermé une
   nappe de 25 mm que la grille du routeur ne voyait pas. Le chemin
   qu'il trouve est revérifié en géométrie exacte avant d'être posé.
   Une liaison qui traverse la carte tomberait à plusieurs millions de
   cellules à ce pas : la fenêtre est alors dégrossie (0,1 puis
   0,2 mm) jusqu'à tenir sous le plafond d'exploration. Comme le
   chemin est de toute façon revérifié, une trame grossière coûte du
   détail, jamais de la légalité.
3. **Plan de masse** : calculé comme le calcule le remplisseur de
   KiCad, îlot par îlot (garde 0,3 mm, largeur minimale 0,2 mm), et
   non comme une bande idéale. C'est là que se cachait l'essentiel des
   liaisons manquantes : un plan de masse coupé en morceaux par les
   pistes de la face arrière ne relie rien d'un morceau à l'autre.
4. **Finition de la masse** : chaque groupe de pastilles de masse que
   le plan ne rejoint pas reçoit sa descente vers l'îlot qui porte le
   reste. Le cuivre de masse n'est pas étranger à son propre plan,
   donc ces raccords ne le déplacent pas : le plan se calcule une
   fois, après le routage des signaux, et la masse se finit contre
   lui.

La connexité est enfin vérifiée couche par couche, plan compris
(`tools/analoggen/connect.py`), avec la forme vraie des pastilles et
non la boîte autour : **le compte du build est celui de KiCad**.

Le placement est vérifié de la même façon, et pour la même raison
(`tools/analoggen/yards.py`) : deux courtyards qui se recouvrent ne
sont pas un court-circuit, aucune règle de cuivre n'en parle, et
c'est pourtant une reprise à l'assemblage. Le build lit les courtyards
des empreintes, les pose, compte les paires qui se recouvrent, et sort
le nombre sur sa ligne d'état. Quarante-neuf sur cette carte à
l'ouverture du contrôle : le motif de cellule espaçait ses rangées de
3 mm quand les boîtiers en demandent 3,3 à 4,2. Les rangées ont été
réespacées et cinq voisinages serrés corrigés un par un ; le compte
est à zéro, et le routage a été refait sur le placement corrigé.

## La passe de finition partagée (`tools/quadgen/finish.py`)

Le 20/09/2026, la passe de finition et le labyrinthe de la carte
analogique ont été portés sur le modèle de cuivre partagé, pour servir
les trois générateurs : n'importe quelle pile de couches, une couche de
plan sur laquelle aucun raccord ne court (In1 du cerveau), le contour et
les règles de la carte servie (garde, largeur, via, distance de perçage
à perçage), et des zones interdites en forme quelconque (les spirales
du quadrant : aucun raccord ne traverse une bobine). Chaque générateur
présente son cuivre sous la forme de tuples simples (pastilles avec leur
forme vraie, pistes, vias, trous, zones interdites, plan) et redessine
le plan de raccords que la passe lui rend.

Ce qui ne change pas : les familles de raccords (segment, L, Z balayé ;
un via puis une course sur une autre couche ; deux vias et une course
sur une troisième couche ; le labyrinthe en dernier recours, sur toutes
les couches routables à la fois), la garde de la classe de nets tenue
contre tout cuivre étranger, la revérification exacte de tout chemin
du labyrinthe, et la masse finie en second, contre les îlots réels de
son plan ou, sur une couche de plan, par une descente pour chaque
groupe sans cuivre sur elle.

Ce qui a été appris en le portant : la famille à deux vias explorait
toutes les paires de spots de via (156 par côté) avant de renoncer, ce
qui coûtait neuf minutes sur un cas de vingt millimètres ; elle est
bornée à six spots par côté et n'essaie plus la course sur la couche
d'un des deux moignons, ce que les familles précédentes couvrent déjà.
Le labyrinthe part toujours de la plus petite pièce : semé des milliers
de cellules d'un plan ou d'un bus, il épuisait son plafond sur le
semis. Un via plus fin (celui des éventails, 0,45 mm) est essayé après
le via standard de la carte, et chaque net dispose d'un budget de
temps au delà duquel il reste ouvert et listé. Les tests de
`tests/test_finish.py` fixent ces cas sur du cuivre synthétique, en
deux et en quatre couches.

Dans `boardgen`, la passe court après le routeur et avant le compte de
connexité, sur toutes les cartes ; dans `quadgen`, après le routage de
la bande et avant le calcul du plan de masse de la bande. Un net que la
passe ferme sort de la liste des nets ouverts, quoi que le routeur en
ait dit ; un net qu'elle ne ferme pas y reste avec la raison du
routeur.

## Rip-up et reroutage (`tools/boardgen/core.py`)

Le cerveau, une fois les éventails des liens dessinés et VBAT posé à
la main, restait chaotique : chaque correction fermait deux nets et en
ouvrait trois autres (VBAT et LED5_K fermés, AMP_OUT4, I2C_SCL et
ESP_3V3 ouverts au build suivant). Les sondes disent pourquoi : un net
laissé en morceaux l'est presque toujours parce que les routes de ses
voisins, posées avant lui, possèdent la grille autour d'une de ses
pastilles (le couloir d'une broche fine, une résistance entre deux
vias), et aucun budget de recherche ne trouve un chemin qui n'existe
pas. Le remède classique est le rip-up : `GenericBoard.reroute_walled`,
exécuté à la fin de `route_all`, avant la passe de finition.

Un net à la fois, parmi ceux que la connexité exacte trouve en
morceaux : les routes de ses voisins qui possèdent la grille à moins de
0,6 mm de ses pièces sont soulevées avec les siennes (les seeds, les
moignons d'échappée, les descentes de masse, les nets d'alimentation et
les nets routés en premier restent), la grille est repeinte, et tout
est rerouté sur la carte telle qu'elle est, le net ouvert en premier,
avec un budget doublé (deux millions de nœuds). La levée est gardée si
moins de nets sont en morceaux après elle, défaite sinon ; jusqu'à
trois passages sur les nets restants, arrêtés par un passage qui ne
ferme rien. Le build imprime ce que chaque levée a fait (« rip-up 1,
ESP_3V3: 6 neighbour(s) lifted, nets in pieces 9 -> 8 ») ;
`BOARDGEN_RIP_UP=0` le désactive, pour comparer.

Pour lever une route, il faut savoir ce qui est route : chaque
tentative du routeur enregistre les pistes et les vias qu'elle a
dessinés, et chaque piste et via se souvient des lignes qu'elle a
écrites dans le fichier de carte, pour les en retirer aussi.

Sur le cerveau du 20/09 : neuf nets en morceaux après le routage, six
après le rip-up (dix minutes), un après la passe de finition ; le même
build sans rip-up en laissait deux ou trois. Ce qu'il ne fait pas :
lever un mur fait d'alimentations ou des nets routés en premier, et
c'est là que finissent les derniers ouverts (AMP_OUT4 muré par 3V3 et
5VA sous les éventails des liens, COMM_RXD par les rails du bloc de
communication autour de l'isolateur), d'où les quatre sorties
analogiques et les deux lignes UART de l'isolateur ajoutées à la liste
des nets routés en premier, quand la carte est vide.

## La saturation, et ce qu'elle cachait

Cette note affirmait que les liaisons restantes étaient celles dont
tout seed structurel déplace plus de nets qu'il n'en ferme, mesuré sur
plusieurs générations comparées. C'était vrai des essais faits, et
faux comme conclusion : le compte servant d'arbitre était celui d'un
modèle de connexité optimiste, qui ignorait la masse, fusionnait les
couches sans exiger de via et prenait la boîte d'une pastille pour son
cuivre. Il annonçait sept liaisons ouvertes là où KiCad en comptait
vingt-huit, et il jugeait donc mal chaque tentative.

Le modèle exact a renversé la conclusion : les seeds structurels
ferment ce qu'on leur demande, à condition de les tracer dans des
canaux mesurés libres de pastilles, et le plancher n'était pas la
saturation mais la mesure. Treize liaisons sont désormais dessinées
dans `_hand_seeds` : la ligne A de la cellule 2 (deux), la ligne B de
la cellule 3, la prise A de la cellule 2, deux broches du
multiplexeur, la résistance de fuite de la cellule 1, les deux sorties
du régulateur à découpage, et quatre masses que le plan n'atteint pas.
Tout le reste est fermé par les passes.

## Référence actuelle

568 pistes, 288 vias, **zéro élément non connecté** au DRC de KiCad
comme au compte du build, zéro garde sous la valeur de la classe de
nets, zéro cuivre hors contour, **zéro chevauchement de courtyard**, et
les gerbers commités avec l'empreinte de la carte dont ils sortent. La
carte n'a plus de défaut connu, toutes familles confondues.

La progression historique des liaisons ouvertes est dans le
[journal](09-journal.md) : 57, 51, 46, 40, 21, 16, 12, 9, puis 28 une
fois le compte devenu exact, puis 0 ; puis 4, 1 et 6 à mesure que la
correction des courtyards rejouait le routage, et 0 de nouveau.
