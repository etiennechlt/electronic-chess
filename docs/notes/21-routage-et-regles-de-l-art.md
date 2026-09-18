# 21. Le routage devant les règles de l'art

Les cartes de ce dépôt sont routées par un routeur maison
([note 04](04-routeur-et-garanties.md)). Cette note confronte le
résultat aux règles de placement et de routage de la profession, telles
que les rassemble le skill
[`pcb-routing-best-practices`](https://github.com/IxTechCrypto/kicad-skills/blob/main/skills/pcb-routing-best-practices/SKILL.md)
(placement et zonage, gardes mécaniques, empilage, mixte analogique,
alimentations et di/dt, paires rapides, portes de fabrication,
paradigmes de routeur). Verdict par règle : conforme, écart assumé, ou à
corriger avant la commande.

Les chiffres viennent de `tools/routing_audit.py`, qui lit les cartes
livrées et mesure ce que les règles demandent :

```bash
PYTHONPATH=tools python3 tools/routing_audit.py \
    hardware/quadrant-2x2/quadrant-2x2.kicad_pcb hardware/bench/bench.kicad_pcb
```

Son lecteur de carte a été vérifié contre le modèle du générateur :
mêmes 395 pastilles, mêmes positions et mêmes tailles, transformation de
rotation comprise.

## 1. Ce qui est conforme

| Règle | Mesure sur le quadrant 2 x 2 |
|---|---|
| Orientations orthogonales (0 ou 90 degrés) | 129 boîtiers sur 129 |
| Bancs de passifs en matrices régulières | une cellule de bobine est quatre colonnes de composants au pas de 0,1 mm, dessinées de la même façon dans les quatre cellules du 2 x 2 comme dans les seize du 4 x 4 |
| Zonage fonctionnel | la bande est découpée en zones : connecteur, cellules, bloc central de décodage, colonne d'amplification, bas de bande |
| Largeur de piste contre courant | 0,20 à 1,60 mm ; la plus chargée est le rail LED, 1 A sur 1,0 mm de large, là où la table IPC-2152 de la règle en demande environ 0,4 par interpolation |
| Vias | 0,45 / 0,20 mm (colonne haute densité de la règle) pour les signaux, 0,60 / 0,30 mm (colonne standard) pour les bobines ; courants de quelques milliampères contre plus d'un ampère admissible |
| Isolement de fabrication | 0,15 mm partout, contre 0,127 mm de capacité standard |
| Boucles de commutation | la cellule tient FET, diodes et résistance d'amortissement dans 2 mm, le plan de masse est directement sous elle |
| Descentes de masse | 71 vias pour 68 pastilles de masse, la plus lointaine à 2,55 mm de sa descente |
| Pas de SMT sous un connecteur traversant | aucun traversant sur ces cartes |
| Choix du paradigme de routeur | la règle recommande la recherche sur graphe discret (A\*, coût de via et de coude) pour les bus denses, et le script déterministe pour les boucles sensibles : c'est exactement le partage entre `quadgen/router.py` et `quadgen/hand.py` |

## 2. Les écarts assumés

**Pas de plan de masse continu sur In1.** La règle veut la couche 2
entièrement en masse, sous les signaux de la couche 1. Ici la carte
**est** le capteur : les quatre couches portent les spirales des bobines
en série ([ADR 0001](../adr/0001-lc-resonators-for-piece-identification.md)),
et le plan de masse du frontal est sur la couche arrière. Conséquence
assumée : le retour du cuivre de la bande passe deux diélectriques plus
loin, donc la boucle est plus haute. Ce qui rend l'écart sans effet :
les fréquences de travail vont de 20 à 60 kHz, où la longueur d'onde est
kilométrique ; l'impédance contrôlée et la discipline de retour au
gigahertz que la règle vise ne s'appliquent pas. Ce qui compte, l'aire
de boucle, reste tenu par le plan qui court sous toute la bande.

**La règle 2W n'est pas tenue dans la bande.** L'audit trouve 120
endroits où un net de mesure passe à moins de 0,50 mm (2W) d'un net qui
commute, le pire à 0,225 mm. La bande fait 20 mm de large pour une
centaine de liaisons : desserrer à 2W demanderait une carte plus large,
donc un plateau plus grand. Trois raisons rendent l'écart tenable, et
elles sont vérifiables au banc :

- pendant la fenêtre d'écoute, tous les agresseurs sont statiques :
  l'impulsion dure 1 µs, le blanking 2 µs, et l'écoute commence après ;
  la sélection du multiplexeur, les grilles d'amortissement et le 12 V
  ne bougent plus ;
- chaque prise de bobine est écrêtée par sa paire de diodes vers la
  masse et vers le 5VA, posée pour absorber exactement l'injection des
  fronts par capacité parasite ;
- les deux pires paires sont une prise de multiplexeur contre le 12 V
  (statique) et une borne de bobine contre la grille d'amortissement
  d'une **autre** cellule (statique pendant la mesure de celle-là).

La chaîne LED, elle, commute vite (800 kHz) : c'est pourquoi le firmware
la met hors fenêtre de mesure, et pourquoi le protocole garde une mesure
dédiée (M11, LED éteintes contre blanc plein).

**Les paires ne sont pas appariées en longueur.** L'audit mesure 14 à
15 % d'écart : MUXA_OUT 12,4 mm contre MUXB_OUT 14,6 mm, INA_INP 28,8
contre INA_INM 33,7, RG_A 16,1 contre RG_B 19,0. La règle vise
0,5 à 1,25 mm d'écart pour l'USB et le HDMI. À 40 kHz, 5 mm de piste de
0,25 mm valent 12 mΩ et 0,2 pF : devant la centaine d'ohms de
résistance passante du multiplexeur et l'entrée quasi infinie de
l'amplificateur d'instrumentation, le déséquilibre est de l'ordre de
1e-4, quatre décades sous l'asymétrie du multiplexeur lui-même. Aucun
accord de longueur n'est justifié ici.

## 3. Les deux points à corriger

**La garde des trous de fixation.** La règle exige 3,0 mm de rayon libre
de cuivre autour d'un trou M3 (6 mm de diamètre), pour qu'aucune tête de
vis ni entretoise n'écrase de cuivre. Le quadrant a 2,15 mm : un anneau
libre de 0,55 mm seulement autour du perçage de 3,2 mm, et une tête de
vis M3 fait 5,5 à 6 mm. Elle se posera donc sur du cuivre sous vernis
d'épaisseur 20 µm. Le pion de positionnement de 4,2 mm est à 2,85 mm,
même remarque. Trois sorties, à trancher avant la commande :

1. monter avec des vis nylon ou des rondelles épaulées isolantes (aucun
   changement de carte) ;
2. éloigner les deux trous, dont l'écart vient de
   `plateau.quadrant.mounting_hole_inset_mm` du yaml, ce qui coûte de la
   place dans le champ des spirales ;
3. ajouter une zone d'exclusion autour des trous dans le générateur, ce
   qui revient au même coût de place mais automatiquement.

**Le découplage est trop loin des broches d'alimentation.** La règle veut
le condensateur contre la broche. Mesuré sur le quadrant :

| Broche | Condensateur le plus proche | Distance |
|---|---|---|
| U3.29 (5VA du multiplexeur) | C16 | 8,9 mm |
| U5.8 (5VA de l'AD8421) | C16 | 6,7 mm |
| U8.8 (5VA du second étage) | C21 | 5,5 mm |
| U7.8 (5VA du filtre) | C16 | 4,4 mm |
| U1.24 (3V3 du décodeur) | C6 | 12,3 mm |
| U2.24 (3V3 du décodeur) | C6 | 8,4 mm |

À 3 nH par millimètre de boucle, 9 mm font une trentaine de
nanohenrys : sans effet sur la mesure à 60 kHz, mais pas sur les
transitoires de commutation du multiplexeur et des décodeurs, qui
remontent alors sur le rail analogique. Le correctif est un correctif de
placement, pas de routage : le paquet de passifs par affinité existe
déjà dans `tools/quadgen/strip.py`, il suffit de lui imposer de coller
chaque découplage à son boîtier. À faire avant la commande des quatre
quadrants, pas nécessairement avant celle du 2 x 2 de mise au point.

## 4. Ce que cette revue ne couvre pas

Les chapitres RF du skill (guide d'ondes coplanaire, clôture de vias,
réseau d'adaptation, garde d'antenne) sont hors sujet : aucune de ces
cartes n'a d'étage radio, le pont radio est un module ESP32 sur la carte
cerveau. Les chapitres USB, HDMI et différentiel rapide le sont aussi.
Le chapitre fort courant ne s'applique pas : le rail le plus chargé est
le 5 V des LED, à 1 A, loin des dizaines d'ampères que la règle
dimensionne. L'ergonomie des connecteurs ne concerne que la nappe FPC,
dont la sortie regarde le bord de la carte, comme la règle le demande.

## 5. Carte de banc

Le même audit sur `hardware/bench/bench.kicad_pcb` : 43 boîtiers sur 43
orthogonaux, pistes de 0,20 à 0,60 mm, vias 0,45 / 0,20 et 0,80 / 0,40,
et **aucun** endroit où un net de mesure passe à moins de 2W d'un net
qui commute, la carte étant dix fois moins dense que la bande du
quadrant. Sa mesure de descente de masse n'est pas parlante : ses deux
faces portent un plan, donc une pastille de masse n'a pas besoin de via
pour rejoindre le sien.
