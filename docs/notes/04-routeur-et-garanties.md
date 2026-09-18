# 04. Le routeur maison et ses trois garanties

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

## Les trois garanties formelles

Ordre d'exécution dans `build_pcb` : routage, puis

1. **DRC exact** : shapely, par couche, seuil de fabrication
   0,127 mm ; c'est l'autorité, pas les masques du routeur.
2. **Passe de retrait** (`_strip_subclearance`) : tout cuivre sous la
   garde est retiré et sa liaison réouverte en chevelu explicite ; les
   paires pad contre pad relèvent du placement et sont listées.
3. **Passe de finition** (`tools/analoggen/finish.py`) : sur le cuivre
   fini, en géométrie exacte sans grille, elle referme les écarts par
   le raccord le plus simple (segment, L, Z balayés jusqu'à 6,4 mm,
   variantes face arrière à un ou deux vias, anneaux jusqu'à 4,8 mm),
   chaque raccord tenu à 0,132 mm de tout cuivre étranger. Le réglage
   décisif : les canaux entre rangées de pads des cellules font
   0,52 mm, une garde de 0,137 exigeait 0,524, quatre microns de trop.

Le plan de masse est calculé après, sur le cuivre final. Résultat
invariant : **la carte générée est toujours DRC zéro**, et tout ce qui
n'a pas pu être fermé est imprimé en liste de finition.

## La saturation, et pourquoi on s'arrête là

Les liaisons restantes sont celles dont tout seed structurel déplace
plus de nets qu'il n'en ferme : mesuré sur plusieurs générations
comparées, chaque tentative dans la bande des cellules échangeait un
échec contre deux. Le plancher atteint est une courte liste de
couloirs saturés (bande des cellules, coin buck), des détours
multi-segments qu'un humain trace en un quart d'heure dans pcbnew,
listés par le build et dans le
[README de la carte](../../hardware/mockup-2x2/analog-board/README.md).

## Référence actuelle

499 pistes, 259 vias, DRC zéro, 12 raccords posés par la finition,
nets LED entièrement câblés ; sept nets à fermer à la main (M1_A,
M2_A, C2_A, C3_B, BUCK_FB, BUCK_EN, VREF). La progression historique
des liaisons ouvertes est dans le [journal](09-journal.md).
