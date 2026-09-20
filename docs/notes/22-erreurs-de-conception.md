# 22. Erreurs de conception des cartes, et ce qui empêche de les refaire

Cette note liste les erreurs réellement commises sur les cartes de ce
projet, pas les erreurs possibles en général. Chacune est écrite de la
même façon : le fait, ce qui l'a révélée, la cause, puis la correction
et le garde-fou. Le garde-fou est la partie qui compte : une erreur
comprise mais laissée sans contrôle automatique revient au build
suivant, et celles qui suivent sont revenues plusieurs fois avant
d'être verrouillées.

Règle du projet, tirée de cette liste : **une erreur trouvée devient
un contrôle qui tourne**, dans le build ou dans les tests. Les
commandes qui font tourner ces contrôles sont rassemblées à la fin.

## 1. Le compte des liaisons manquantes était faux

**Le fait.** Le build annonçait sept liaisons ouvertes sur la carte
analogique, KiCad en comptait vingt-huit. Pendant des jours, les sept
ont servi de repère : on décidait quoi faire, quoi lâcher et quand
s'arrêter sur un chiffre faux.

**Ce qui l'a révélée.** L'ouverture de la carte dans KiCad, avec le
chevelu affiché, après remplissage des zones (touche B).

**La cause.** Trois écarts dans le modèle du générateur, chacun
optimiste : la masse n'était pas vérifiée du tout, deux morceaux de
cuivre sur des couches différentes étaient comptés reliés sans exiger
de via, et une pastille valait la boîte rectangulaire autour d'elle et
non son cuivre réel.

**La correction et le garde-fou.** Le modèle exact du quadrant
(`tools/quadgen/connect.py`) est devenu la comptabilité unique,
importée par les trois générateurs
([note 04](04-routeur-et-garanties.md)) : forme vraie des pastilles,
union par couche, via obligatoire pour changer de couche, plan de masse
calculé îlot par îlot. Le test
`test_the_exact_check_counts_the_pieces_kicad_would` épingle les cas
qui avaient menti (piste qui s'arrête court, changement de couche sans
via, plan coupé en deux). Depuis, le compte du build est celui que
KiCad affiche, et c'est ce qui a permis de passer de 28 à 0.

**La leçon.** Un mauvais arbitre fait prendre les mauvaises décisions
pendant longtemps. La « saturation » qui justifiait de s'arrêter à sept
liaisons n'existait pas : elle était un artefact du compte.

## 2. Le plan de masse pris pour une bande idéale

**Le fait.** Dix-neuf des vingt-huit liaisons manquantes étaient des
masses. Le générateur posait un plan sur une couche et considérait
toute pastille de masse comme reliée à lui.

**Ce qui l'a révélée.** Le compte exact du point 1, une fois le plan
calculé comme le calcule le remplisseur de KiCad.

**La cause.** Un plan traversé par des pistes de la face arrière n'est
plus une bande : c'est une collection d'îlots, et deux pastilles posées
sur deux îlots ne sont pas reliées. Sur les cellules de bobine, quatre
lignes traversent la cellule par la face arrière et découpent son plan
en confettis.

**La correction et le garde-fou.** Le plan est calculé en géométrie
exacte, îlot par îlot, garde 0,3 mm et largeur minimale 0,2 mm, puis
une passe de finition de la masse descend chaque groupe de pastilles
orphelin vers l'îlot qui porte le reste. Là où le découpage est
structurel, une **épine de masse** est tracée avant le routage (une par
cellule, dans le canal de 1,1 mm entre l'écrêteur et la résistance de
grille). Le compte du point 1 vérifie le résultat.

## 3. Une pastille à 1 mm hors du contour, depuis l'origine

**Le fait.** La broche 2 du jack d'alimentation de la carte analogique
était à 1 mm en dehors du contour de carte. Le fabricant aurait fraisé
la carte au milieu de la pastille.

**Ce qui l'a révélée.** `tools/drc.py`, c'est à dire le DRC de KiCad en
ligne de commande, une fois le routage fermé et le contrôle lancé sur
toutes les familles de règles et non sur la seule connexité.

**La cause.** Le générateur vérifiait ce qu'il traçait (gardes entre
cuivres) mais pas ce qu'il plaçait par rapport au bord. Un jack de
panneau dépasse légitimement du contour par son corps, ce qui rendait
le défaut invisible sur le rendu.

**La correction et le garde-fou.** Le jack est reculé à x = 8 mm, ses
pastilles à 0,5 mm du bord, le corps dépassant à l'ouest comme le veut
sa fonction. Le garde-fou est le DRC de KiCad lui même, inscrit dans le
runbook ([note 08](08-regenerer.md)) et lancé sur chaque carte avant
tout export, avec la garde au bord réglée à la valeur de fabrication.

## 4. Quatre couches déclarées pour une carte à deux couches

**Le fait.** Le fichier de la carte analogique déclarait quatre couches
cuivre. L'archive de fabrication portait donc deux couches internes
vides. Un fabricant aurait facturé et gravé une carte quatre couches.

**Ce qui l'a révélée.** La relecture de l'archive produite, fichier par
fichier, au moment de la première commande.

**La cause.** `coilgen.kicad.Board` a quatre couches par défaut, pour
la carte bobines ; le générateur analogique ne redéfinissait pas ce
paramètre.

**La correction et le garde-fou.** `copper_layers=2` dans le
générateur, et surtout `tools/gerbers.py` qui lit la pile de couches
**sur la carte** au lieu de porter une liste par projet, plus le test
`test_the_generated_archives_carry_the_stack_the_board_declares` qui
compare les fichiers de l'archive à la pile que le `.kicad_pcb`
déclare. Une couche oubliée ou une couche en trop est désormais un
test rouge.

## 5. Quarante-neuf chevauchements de courtyard

**Le fait.** Quarante-neuf paires de composants se disputaient la même
place sur la carte analogique, dont quarante-quatre dans le motif de
cellule répété quatre fois. Ce n'est pas un court-circuit et aucune
règle de cuivre n'en parle : c'est une reprise à l'assemblage, des
pièces qui ne tiennent pas côte à côte et des condensateurs que la buse
de refusion pousse hors de leurs pastilles.

**Ce qui l'a révélée.** Le DRC de KiCad, famille `courtyards_overlap`,
que le générateur ne regardait pas.

**La cause.** Le motif de cellule espaçait ses rangées sur la taille
des pastilles (3 mm) alors que les courtyards des boîtiers en demandent
3,3 à 4,2 selon le boîtier.

**La correction et le garde-fou.** Les rangées sont réespacées (la
cellule est 1,7 mm plus haute et tient toujours entre le rail VREF et
le connecteur de bobines), et cinq voisinages serrés sont corrigés un
par un. Le build lit maintenant les courtyards des empreintes, les
pose, et compte les paires qui se recouvrent
(`tools/analoggen/yards.py`) : le nombre sort sur la ligne d'état à
côté des liaisons ouvertes, et le test
`test_no_two_courtyards_of_the_analog_board_overlap` exige zéro.

**La leçon.** Le placement se vérifie comme le routage. Le prix de
cette correction a été de rejouer tout le routage de la carte, donc de
rouvrir des liaisons ailleurs : un défaut de placement se paie en
routage.

## 6. Des liaisons structurelles dessinées à l'oeil

**Le fait.** Les liaisons que le routeur ne trouve pas sont tracées à
la main dans le générateur, avant le routage. Chaque fois qu'une de ces
routes a été posée d'après un rendu au lieu d'une mesure, elle a cassé
quelque chose : une amorce qui croise une autre sur la même couche, un
via qui touche une pastille voisine, une voie qui passe à 0,05 mm d'un
bord de pastille.

**Ce qui l'a révélée.** Au début le DRC, après chaque build de trente
minutes. Beaucoup trop tard.

**La cause.** Une route à la main est une hypothèse sur la géométrie.
Sans contrôle, l'hypothèse est vérifiée trente minutes plus tard, ou
jamais.

**La correction et le garde-fou.** Les fonctions qui posent une amorce
(`T` et `V` dans `_hand_seeds`) revérifient chaque segment et chaque
via, au build, contre la géométrie réelle de toutes les pastilles et
contre les autres amorces, et lèvent une erreur nommée
(`seed C4_B crosses seed C4_A on B.Cu`) avant que le routage ne
commence. Le test
`test_the_hand_seeds_of_the_analog_board_stay_legal` rejoue ce contrôle
en deux secondes. Toutes les coordonnées des amorces sont dérivées des
bords de pastilles mesurés (`edge`, `channel_x`, `P`), jamais écrites
en dur.

## 7. L'ordre de routage : la liaison la plus longue passe en dernier

**Le fait.** Les liaisons qui restaient ouvertes build après build
étaient toujours les mêmes familles : la ligne A de la cellule 4, la
ligne B de la cellule 4, la grille d'amortissement de la cellule 2,
c'est à dire les parcours les plus longs de la carte.

**Ce qui l'a révélée.** La liste des liaisons ouvertes, en la lisant
comme une donnée plutôt que comme une fatalité : ces nets traversent la
carte, et la bande qu'ils doivent traverser est pleine quand leur tour
vient.

**La cause.** Le routeur trie les nets par portée croissante : les
courts d'abord, les longs ensuite, dans une bande déjà saturée. La
congestion dépend de l'ordre, et rien ne rattrapait un net arrivé trop
tard.

**La correction et le garde-fou.** Trois mesures cumulées : le routeur
joue trois tours et chaque tour promeut en tête ce que le précédent a
manqué (le meilleur tour est gardé) ; les parcours structurellement
impossibles reçoivent leur voie avant le routage (point 6) ; et ce qui
reste passe par la passe de finition puis par le labyrinthe. Le bilan
final est imprimé par le build, liaison par liaison, avec les
pastilles de chaque morceau.

**La leçon.** Une liaison qui échoue n'est presque jamais un hasard à
relancer. C'est un ordre, un mur, ou un couloir trop étroit, et les
trois se mesurent.

## 8. Le labyrinthe qui renonçait sur les longues traversées

**Le fait.** Le labyrinthe (recherche A* en géométrie exacte, dernier
recours quand aucun raccord simple ne passe) rendait « pas de chemin »
sur les liaisons qui traversent la carte, alors qu'un chemin existait.

**Ce qui l'a révélée.** Un appel direct du labyrinthe sur la liaison
restante, hors du build, qui répondait en 0,2 s : trop vite pour une
recherche, donc un abandon et non un échec.

**La cause.** Une trame de 0,05 mm sur une fenêtre de 57 par 61 mm fait
1,4 million de cellules, au delà du plafond d'exploration.

**La correction et le garde-fou.** La fenêtre est dégrossie (0,1 puis
0,2 mm) jusqu'à tenir sous le plafond. Le chemin trouvé est de toute
façon revérifié en géométrie exacte avant d'être posé, donc une trame
grossière coûte du détail et jamais de la légalité. Test :
`test_the_maze_coarsens_its_raster_for_a_haul_across_the_board`.

## 9. Un via ne rentre pas dans 0,85 mm

**Le fait.** La rangée B de la cellule 4 restait isolée. Le labyrinthe
confirmait qu'aucun chemin n'existait, sur les deux couches.

**Ce qui l'a révélée.** La mesure de ce qui l'enfermait, cuivre par
cuivre : la ligne de grille du mux en face avant à x = 76,75, la ligne
d'excitation de la cellule 1 qui traverse toute la carte en face
arrière à x = 75,50, la masse à x = 77,72. Reste 0,85 mm entre deux
murs, et un via de 0,6 mm avec sa garde de 0,15 mm en demande 0,9.

**La cause.** Deux causes en une : la descente n'était pas réclamée
avant le routage, et le raisonnement cherchait un passage en face avant
là où la face avant était pleine.

**La correction et le garde-fou.** La descente est tracée avant le
routage, par la face arrière de la bande : l'écrêteur du rail 5VA et le
FET d'excitation sont tous les deux en CMS, donc **ils ne bloquent que
la face avant**, et la face arrière de cette bande est vide d'une
rangée à l'autre. Deux vias, une descente droite, coordonnées dérivées
des bords de pastilles.

**La leçon, deux fois utile.** Une pastille CMS ne bloque qu'une
couche ; un passage introuvable en face avant est souvent libre en face
arrière. Et avant de dessiner, mesurer les murs : la largeur du couloir
se calcule, elle ne s'estime pas.

## 10. Une archive de fabrication qui ne correspondait plus à sa carte

**Le fait.** `hardware/mockup-2x2/coil-board/coil-board-gerbers.zip`
était commité, plus ancien que le `.kicad_pcb` à côté de lui, et tracé
depuis un état de la carte qui n'existe plus. La carte, dans son état
commité, porte 251 violations bloquantes au DRC (96 gardes, 82 gardes
de perçage, 63 ponts de masque, 8 perçages trop proches) et deux
éléments non connectés. Rien dans un zip ne dit de quelle carte il
vient : cette archive était prête à être commandée.

**Ce qui l'a révélée.** L'audit avant commande : comparer la date de
chaque archive à celle de sa carte, puis passer le DRC sur les cartes
dont une archive est commitée.

**La cause.** Le script d'export de cette carte appelait `kicad-cli`
directement, avec une liste de couches écrite à la main, sans remplir
les zones et **sans le garde de connexité** que
`tools/gerbers.py` applique aux autres cartes. Un chemin parallèle
échappe aux contrôles du chemin principal.

**La correction et le garde-fou.** Le script d'export de la carte
bobines appelle maintenant `tools/gerbers.py` comme les autres, donc le
garde refuse d'exporter tant que le routage n'est pas fermé, et
l'archive obsolète est retirée du dépôt (elle sera regénérée quand la
carte passera le DRC). En plus, `tools/gerbers.py` écrit à côté de
chaque archive un fichier au format `sha256sum` qui porte l'empreinte
de la carte tracée et celle de l'archive :

```bash
cd hardware/bench && sha256sum -c bench-gerbers.sha256
```

Le test `test_every_archive_records_the_board_it_was_plotted_from`
compare ces empreintes à ce qui est commité : une archive qui cesse de
correspondre à sa source est un test rouge, et non un fichier que
personne ne regarde deux fois.

## 11. Un BOM d'assemblage silencieusement partiel

**Le fait.** Les fichiers `jlc-bom.csv` ne portent que les lignes qui
ont un code LCSC. Sur le quadrant 2 x 2, cela fait 38 composants sur
126 : les résistances et condensateurs génériques, les BAV99W, et
surtout le multiplexeur ADG1607 n'y sont pas. Téléversé tel quel, un
ordre d'assemblage aurait posé 38 composants et laissé les 88 autres à
souder à la main, dont des 0603.

**Ce qui l'a révélée.** La comparaison du BOM complet (`bom.csv`) avec
le BOM d'assemblage (`jlc-bom.csv`), référence par référence. La parité
entre BOM et CPL, elle, était parfaite sur toutes les cartes, et c'est
justement ce qui cachait le trou : les deux fichiers viennent de la
même source, donc ils sont d'accord sur un sous ensemble incomplet.

**La cause.** Le code LCSC est facultatif dans la description de
circuit, et les lignes sans code sont filtrées à l'export sans être
signalées.

**La correction et le garde-fou.** Tant que les codes ne sont pas
complétés, la commande se fait en **cartes nues**, ce qui est le
chemin normal en prototypage ; le détail par carte et la liste exacte
des lignes à compléter sont dans la
[note 23](23-commande-jlcpcb.md). La règle : ne jamais lire la parité
BOM contre CPL comme une preuve de complétude, et compter les
composants du BOM d'assemblage contre ceux de la carte.

## 12. Deux perçages au même endroit, encore ouvert

**Le fait.** La carte bobines porte huit violations `hole_near_hole`
avec une distance mesurée de 0,000 mm : des vias superposés, ou un via
posé sur un perçage traversant. Un foret qui repasse dans un trou déjà
percé casse le trou, la métallisation, ou le foret.

**Ce qui l'a révélée.** Le DRC de KiCad sur la carte commitée.

**La cause.** Le générateur de la carte bobines pose ses vias sans
vérifier qu'un via du même net ne recouvre pas déjà la place. Le
générateur des autres cartes le fait (`GenericBoard.via` refuse un via
qui recouvre un via du même net, parce que deux pastilles qui se
recouvrent sont un seul cuivre et deux forets qui se rapprochent sont
un défaut de fabrication).

**L'état.** Ouvert, et assumé : la carte bobines de la maquette est
retirée du plan par l'[ADR 0010](../adr/0010-plateau-8x8-base-interchangeable-horloge.md).
Elle n'a plus d'archive commitée (point 10) et le garde de
`tools/gerbers.py` refuse d'en produire une. Le jour où cette carte
repasse en fabrication, la déduplication de vias du générateur
générique est à porter dans `coilgen`.

## Les contrôles, et la commande qui les fait tourner

| Erreur | Contrôle | Commande |
|---|---|---|
| 1, 2 | comptabilité exacte, plan îlot par îlot | ligne d'état du build, `pytest` |
| 3, 4, 5, 12 | DRC de KiCad, toutes familles | `/usr/bin/python3 tools/drc.py <carte>` |
| 4 | pile de couches de l'archive contre la carte | `pytest tests/test_gerbers.py` |
| 5 | courtyards du placement | ligne d'état du build, `pytest` |
| 6 | amorces revérifiées contre les pastilles | build, `pytest` |
| 7, 8 | bilan des liaisons ouvertes | ligne d'état du build |
| 10 | empreinte de l'archive et de sa carte | `sha256sum -c`, `pytest` |
| 11 | BOM d'assemblage contre BOM complet | [note 23](23-commande-jlcpcb.md) |

Avant tout push : `ruff check .` puis `pytest`. Avant tout export de
fabrication : `tools/drc.py`, puis `tools/gerbers.py`, qui refuse une
carte au routage ouvert.
