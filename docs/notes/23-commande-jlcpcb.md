# 23. Commander chez JLCPCB : ce qui part, ce qui ne part pas, et comment

Établi le 19/09/2026 depuis l'état commité du dépôt. Les chiffres
viennent des cartes elles mêmes (`tools/drc.py`, `tools/gerbers.py`,
les BOM et CPL générés) et les capacités du fabricant du skill
`jlcpcb` ([note 15](15-skills-embarques.md)). Les erreurs que cet audit
a trouvées sont expliquées dans la
[note 22](22-erreurs-de-conception.md).

## 1. Ce qui part

Deux cartes, en **cartes nues** (le pourquoi est au paragraphe 5), cinq
exemplaires chacune, qui est le minimum de commande.

| Carte | Contour | Couches | Épaisseur | Finition conseillée | Quantité |
|---|---|---|---|---|---|
| `quadrant-2x2` | 120 x 108 mm | 4 | 1,6 mm | ENIG | 5 |
| `bench` | 80 x 56 mm | 2 | 1,6 mm | HASL sans plomb | 5 |

**Pourquoi ces deux et pas d'autres.** Le quadrant 2 x 2 est le banc de
mise au point du quadrant du plateau : même circuit, même frontal, même
firmware, quatre cases au lieu de seize, et c'est lui qui valide le
frontal et la mesure avant d'engager quatre quadrants 4 x 4
([README](../../hardware/quadrant-2x2/README.md)). La carte de banc
porte la chaîne analogique derrière une Nucleo et sert aux mesures M1 à
M11 ([note 19](19-cerveau-et-banc-nucleo.md),
[note 20](20-tuto-banc.md)). Les deux sont au DRC zéro erreur
bloquante, routage fermé, archives à jour. Les autres cartes ne le sont
pas : paragraphe 4.

**Épaisseur : 1,6 mm, ce n'est pas un détail mécanique.** La spirale de
détection est modélisée comme une bobine multicouche de hauteur égale à
l'épaisseur de la carte (`gap.pcb_mm`), et l'entrefer total en dépend
(1,6 + 2,0 + 3,0 + 0,5 = 7,1 mm). Une carte 1,0 ou 2,0 mm change
l'inductance et l'entrefer.

## 2. Les fichiers, et comment vérifier qu'ils sont les bons

```bash
hardware/quadrant-2x2/quadrant-2x2-gerbers.zip     # 13 fichiers, 4 couches
hardware/bench/bench-gerbers.zip                   # 11 fichiers, 2 couches
```

Chaque archive a son empreinte à côté d'elle, au format `sha256sum`,
qui porte la carte tracée et l'archive :

```bash
cd hardware/quadrant-2x2 && sha256sum -c quadrant-2x2-gerbers.sha256
cd hardware/bench        && sha256sum -c bench-gerbers.sha256
```

Si l'une des deux lignes échoue, ne pas commander : l'archive ne vient
pas de la carte commitée. C'est arrivé
([note 22, point 10](22-erreurs-de-conception.md)).

Pour tout regénérer depuis la source, avec le Python de KiCad pour la
partie fabrication :

```bash
PYTHONPATH=tools .venv/bin/python -m quadgen build --reduced --render docs/images/quadrant-2x2.png
PYTHONPATH=tools .venv/bin/python -m boardgen build bench --render docs/images/bench.png
/usr/bin/python3 tools/drc.py hardware/quadrant-2x2/quadrant-2x2.kicad_pcb hardware/bench/bench.kicad_pcb
/usr/bin/python3 tools/gerbers.py hardware/quadrant-2x2/quadrant-2x2.kicad_pcb hardware/bench/bench.kicad_pcb
```

`tools/gerbers.py` remplit les plans avant de tracer, lit la pile de
couches sur la carte, et refuse toute carte dont le routage n'est pas
fermé.

## 3. Les options du formulaire, écran par écran

Les champs qui ne sont pas listés restent à la valeur par défaut de
JLCPCB.

| Champ | Quadrant 2 x 2 | Banc | Pourquoi |
|---|---|---|---|
| Base material | FR-4 | FR-4 | |
| Layers | 4 | 2 | lu sur la carte, vérifié par les tests |
| Dimensions | 120 x 108 mm | 80 x 56 mm | contour `Edge.Cuts` |
| PCB Qty | 5 | 5 | minimum de commande |
| PCB Thickness | 1,6 mm | 1,6 mm | paragraphe 1 |
| Surface finish | ENIG | HASL sans plomb | ENIG pour le FPC 0,5 mm et le QFN du mux, planéité |
| Outer copper weight | 1 oz | 1 oz | `sense_coil.copper_um` = 35 µm |
| **Inner copper weight** | **1 oz (option payante)** | sans objet | paragraphe 3.1 |
| Via covering | Tented | Tented | vias sous les pastilles de masse |
| Remove order number | oui, ou emplacement imposé | idem | la carte est un capteur : pas de cuivre ou d'encre au hasard dans une case |
| Impedance control | non | non | aucune ligne contrôlée |
| Castellated holes | non | non | |
| Gold fingers | non | non | |

### 3.1 Le cuivre interne, décision à prendre avant de valider

La spirale de détection est faite de quatre couches en série. Le
modèle du projet suppose **35 µm sur les quatre**
(`config/board.yaml`, `sense_coil.copper_um: 35`, commentaire « 1 oz
outer and inner copper »). L'empilement standard de JLCPCB en quatre
couches donne 1 oz dehors et **0,5 oz dedans**, donc deux des quatre
couches de la spirale à 17,5 µm.

Conséquence calculée par le modèle (`chessboard_calc.inductance`), sur
la spirale de 20 tours, piste 1,6 mm, L = 15,7 µH :

| Cuivre interne | ESR de la spirale | Q à 217 kHz | Q à 400 kHz | Q à 613 kHz |
|---|---|---|---|---|
| 1 oz (modèle du projet) | 0,589 ohm | 36 | 67 | 103 |
| 0,5 oz (standard JLCPCB) | 0,884 ohm (+50 %) | 24 | 45 | 69 |

Trois choix, à trancher explicitement :

1. **payer l'option 1 oz interne** : la carte mesurée correspond au
   modèle sur lequel repose tout le plan de fréquences, et c'est le
   choix conseillé pour une carte de validation ;
2. accepter 0,5 oz et **corriger le yaml** (`copper_um` par couche),
   donc rejouer les dérivées et les tests qui les épinglent ;
3. accepter 0,5 oz sans rien changer, c'est à dire mesurer une carte
   qui n'est pas celle du modèle. À éviter : c'est exactement le genre
   d'écart silencieux que la [note 22](22-erreurs-de-conception.md)
   passe en revue.

## 4. Ce qui ne part pas, et ce qu'il manque

| Carte | État | Ce qui manque |
|---|---|---|
| `mockup-2x2/coil-board` | 251 violations bloquantes au DRC, 2 éléments non connectés | fermer le routage, dédupliquer les vias superposés ; carte retirée du plan (ADR 0010) |
| `mockup-2x2/analog-board` | routage fermé, DRC zéro, archive à jour | rien techniquement, mais elle ne sert qu'avec la carte bobines ci dessus ; carte retirée du plan |
| `brain` | 23 liaisons ouvertes | fermeture du routage, puis DRC et gerbers |
| `power` | 12 liaisons ouvertes | idem, dont le net `BAT-` entier (15 morceaux) |
| `clock` | 11 liaisons ouvertes | idem, dont `VBUS` (7 morceaux, pastilles USB-C inatteignables par le routeur) |
| `quadrant` (4 x 4) | jamais régénéré depuis la comptabilité exacte | régénérer, fermer, puis gerbers |
| `motion` | aucun code LCSC, aucune archive | phase 2, ni commandée ni testée (note 07) |

Les quatre cartes de la phase 1 (quadrant 4 x 4, cerveau, puissance,
horloge) partagent la même cause : leur routeur pose ce qu'il sait
poser et laisse le reste ouvert, sans la passe de finition ni le
labyrinthe qui ont fermé la carte analogique
([note 04](04-routeur-et-garanties.md)). Le travail est identifié :
brancher ces deux passes sur `tools/boardgen` et `tools/quadgen`, puis
tracer les liaisons structurelles restantes comme sur la carte
analogique. C'est le lot suivant, et il n'est pas fait.

## 5. Cartes nues maintenant, assemblage plus tard

Les fichiers d'assemblage existent (`jlc-bom.csv`, `jlc-cpl.csv`, un
désignateur du CPL correspondant toujours à une ligne du BOM sur toutes
les cartes), mais ils ne portent que les composants qui ont un code
LCSC dans la description de circuit :

| Carte | Composants | Dans le BOM d'assemblage | À souder à la main |
|---|---|---|---|
| `quadrant-2x2` | 126 | 38 | 88 |
| `bench` | 43 | 9 | 34 |

Téléverser ces BOM tels quels ferait poser 38 composants sur 126 et
laisserait le reste, résistances et condensateurs compris, à la main.
Ce qui manque sur le quadrant 2 x 2 : les passifs génériques (18 x
100 nF, 8 x 330 R, 9 x 10 k, et les autres valeurs unitaires), les huit
BAV99W, et **le multiplexeur ADG1607** (ADG1607BCPZ). Sur le banc : les
passifs, deux fusibles, les barrettes et les électrolytiques. Les
points de test et les amarres de spirale n'ont pas à y être, ce sont
des pastilles.

Donc : **commander les cartes nues**, plus un pochoir encadré si
l'assemblage se fait à la pâte (les deux cartes ne portent des pastilles
CMS que sur la face avant, l'archive ne contient que `F_Paste`), et
s'approvisionner à part ([fiche d'approvisionnement](../bom-maquette.md)).
C'est le chemin de prototypage normal.

Avant de passer un ordre d'assemblage, plus tard :

1. compléter les codes LCSC de la description de circuit, ligne par
   ligne, en vérifiant le stock (skill `lcsc`), puis regénérer les BOM
   et CPL et recompter les composants assemblés contre ceux de la
   carte ;
2. vérifier les rotations dans l'aperçu de placement. Les décalages
   connus entre KiCad et JLCPCB : SOT-23 et SOT-23-5 +180 degrés,
   SOT-223 +180, SOIC +90 ou +270, QFN +90, diodes SMA, SMB et SMC
   +180. Le quadrant en porte quatre familles concernées (le mux en
   LFCSP, les BAV99W en SC-70, les FET en SOT-23, les diodes SOD-123) ;
3. garder les quatre approbations séparées du skill
   `operate-jlcpcb-order` : appariement des composants critiques,
   aperçu de placement, prix final, paiement. Aucune n'implique la
   suivante ;
4. chiffrer à part les composants fournis par soi : le devis JLCPCB ne
   les itémise pas, et 3 USD s'ajoutent par référence étendue.

## 6. Vérification de fabricabilité, faite

Les règles des projets KiCad sont au niveau ou au dessus des capacités
annoncées par JLCPCB, et le DRC passe avec ces règles, ce qui vaut
contrôle de fabricabilité sur les familles mesurables.

| Règle | Quadrant 2 x 2 | Banc | Capacité JLCPCB |
|---|---|---|---|
| Piste la plus fine (cuivre) | 0,20 mm | 0,20 mm | 0,09 mm en 4 couches, 0,127 mm en 2 |
| Garde minimale | 0,15 mm | 0,15 mm | 0,09 / 0,127 mm |
| Via le plus petit | 0,45 / 0,20 mm | 0,45 / 0,20 mm | 0,25 / 0,15 mm en 4 couches, 0,45 / 0,20 mm en 2 |
| Perçage à perçage | 0,25 mm | 0,25 mm | 0,25 mm usuel |
| Cuivre au bord de carte | 0,50 mm | 0,50 mm | 0,30 mm, 0,50 conseillé |
| Éléments non connectés | 0 | 0 | |
| Violations bloquantes au DRC | 0 (sur 395 avertissements) | 0 (sur 83) | |

Le point resté ouvert dans la [note 07](07-etat-et-reste-a-faire.md),
« confirmer les vias d'éventail de 0,45 mm chez le fabricant », est
tranché : 0,45 mm de diamètre pour 0,20 mm de perçage passe en quatre
couches (minimum 0,25 / 0,15) comme en deux couches (minimum
0,45 / 0,20, donc juste au minimum sur le banc). Aucun via à changer.

Les avertissements restants sont de la sérigraphie (chevauchements de
références, texte coupé par le masque) et des bibliothèques
d'empreintes absentes de la configuration KiCad locale. Ils ne changent
pas le cuivre et ne bloquent pas la fabrication ; la sérigraphie est à
relire une fois sur le rendu si la lisibilité compte.

## 7. Ordre des opérations, le jour de la commande

1. `sha256sum -c` sur les deux archives ;
2. téléverser `quadrant-2x2-gerbers.zip`, régler les options du
   paragraphe 3, **trancher le cuivre interne** (3.1) ;
3. téléverser `bench-gerbers.zip`, régler ses options ;
4. ajouter un pochoir encadré face avant pour chaque carte si
   l'assemblage se fait à la pâte ;
5. relire le prix et l'adresse, puis payer (deux approbations
   distinctes) ;
6. noter dans le [journal](09-journal.md) la date, les options
   retenues, le prix et le délai annoncé, et l'empilement que JLCPCB
   affecte à la carte quatre couches.
