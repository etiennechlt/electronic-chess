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
