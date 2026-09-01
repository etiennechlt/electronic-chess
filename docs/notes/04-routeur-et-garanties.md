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
