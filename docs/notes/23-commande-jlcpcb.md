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

L'audit de cette note est rejouable en une commande, sans KiCad :

```bash
python3 tools/fabcheck.py                    # toutes les cartes
python3 tools/fabcheck.py hardware/bench     # une seule
```

Il donne par carte le contour, la pile de couches, la piste et le via
les plus petits, l'état de l'empreinte de l'archive, la couverture du
BOM d'assemblage et les lignes sans code LCSC, puis un verdict :
`bare boards ready`, `assembly ready` ou `not ready`. Le code de sortie
est non nul si une archive ne correspond plus à sa carte.

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
| `brain` | 141 éléments non connectés au DRC (23 nets ouverts au build) | fermeture du routage, puis DRC et gerbers |
| `power` | 69 éléments non connectés (12 nets, dont `BAT-` entier, 15 morceaux) | idem |
| `clock` | 51 éléments non connectés (11 nets, dont `VBUS`, 7 morceaux : pastilles USB-C inatteignables par le routeur) | idem |
| `quadrant` (4 x 4) | jamais régénéré depuis la comptabilité exacte | régénérer, fermer, puis gerbers |
| `motion` | 27 éléments non connectés et 24 perçages trop proches | phase 2, ni commandée ni testée (note 07) |

Chiffres mesurés sur les fichiers commités par
`/usr/bin/python3 tools/drc.py`, le 19/09/2026. Un net ouvert compte
plusieurs éléments non connectés, d'où les deux nombres.

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
| `quadrant-2x2` | 118 | 38 | 80 |
| `bench` | 36 | 9 | 27 |

Les points de test, les amarres de spirale et les trous de fixation ne
comptent pas comme composants : ce sont des pastilles, huit sur le
quadrant et sept sur le banc. Téléverser ces BOM tels quels ferait
poser 38 composants sur 118 et laisserait le reste, résistances et
condensateurs compris, à la main.
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

Les avertissements restants se répartissent en trois familles, aucune
bloquante. La sérigraphie d'abord (quadrant : 151 chevauchements de
références, 75 textes coupés par le masque, 4 au bord ; banc : 29 et
6) : rien ne change au cuivre, mais la lisibilité des repères est à
relire sur le rendu si l'on compte sérigraphier utile. Les
bibliothèques d'empreintes ensuite (129 et 43), absentes de la
configuration KiCad locale, ce qui ne dit rien de la carte. Enfin du
cuivre en cul de sac (quadrant : 25 pistes et 11 vias ; banc : 5
vias) : des moignons dont une extrémité ne rejoint rien, laissés par
les passes de finition et par les échappées. Ils n'ouvrent aucune
liaison, ils ne court-circuitent rien, et ils sont fabriqués tels
quels ; sur une carte qui est un capteur, ils sont à nettoyer à la
prochaine reprise du routage plutôt qu'à ignorer indéfiniment.

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

## 8. Le plateau : quadrant 4 x 4 et cerveau, ce que coûterait la commande

Établi le 20/09/2026, une fois les deux cartes régénérées avec la
passe de finition partagée (`quadgen.finish`, [note 04](04-routeur-et-garanties.md)).
Les prix des composants sont des ordres de grandeur : la fiche
d'approvisionnement du 30/08 pour l'AD8421 et l'OPA2810, le devis du
20/09 pour ce que JLCPCB a apparié, des prix catalogue courants pour le
reste. Le panier JLCPCB et LCSC les remplace le jour de la commande ;
avant lui, les codes LCSC de la description de circuit sont à
vérifier ligne par ligne (paragraphe 5 et [note 22](22-erreurs-de-conception.md),
point 11 : six des douze codes du 2 x 2 étaient faux).

### 8.1 Les cartes nues

Même formulaire que le paragraphe 3 ; ce qui change :

| Champ | Quadrant 4 x 4 | Cerveau |
|---|---|---|
| Dimensions | 220 x 200 mm | 120 x 80 mm |
| Couches | 4 | 4 |
| Finition | ENIG (FPC 0,5 mm, deux LFCSP) | ENIG (LQFP 0,5 mm, QFN, quatre FPC) |
| Cuivre interne | 1 oz, même décision qu'au 3.1 : la spirale est la même | 0,5 oz standard suffit, aucune spirale |
| Quantité | 5 (minimum) pour 4 utiles | 5 (minimum) pour 1 utile |

Ordre de grandeur du prix des cartes, extrapolé du devis du 20/09
(frais d'ingénierie 4 couches 21,73 EUR par commande, puis la surface,
30,43 EUR pour 2 592 cm² de 2 x 2 en vingt exemplaires) :

| Poste | EUR hors taxes |
|---|---|
| 5 quadrants 4 x 4, 2 200 cm² | 50 à 80, plus l'option cuivre interne 1 oz |
| 5 cerveaux, 480 cm² | 28 à 35 |
| Port, 2 kg environ | 25 à 40 |

Le devis réel se demande en téléversant `quadrant-gerbers.zip` et
`brain-gerbers.zip` : c'est le chiffre de référence que la
[note 16](16-cout-des-cartes.md) attend depuis le 07/09.

### 8.2 Les composants

Par carte, quantités de `bom.csv`, prix unitaires estimés :

| Quadrant 4 x 4 | Quantité | Unitaire (EUR) | Total (EUR) |
|---|---|---|---|
| ADG1607BCPZ | 2 | 8,5 | 17 |
| AD8421ARZ | 1 | 3,4 à 8,2 | 3,4 à 8,2 |
| OPA2810IDR | 2 | 5 | 10 |
| 74HC4514PW, 74HC154PW, 74LVC1G04 | 3 | 0,4 | 1,2 |
| AO3401A, AO3400A | 34 | 0,06 | 2 |
| B5819W, SS34FL, BAV99W, BAV99 | 81 | 0,04 | 3,2 |
| WS2812B | 32 | 0,07 | 2,2 |
| Passifs, 0402 à 2010 | 135 | 0,01 | 1,4 |
| FH12-16S-0.5SH | 1 | 0,5 | 0,5 |
| **Par quadrant** | 324 | | **41 à 46** |
| **Quatre quadrants** | | | **165 à 185** |

| Cerveau | Quantité | Unitaire (EUR) | Total (EUR) |
|---|---|---|---|
| STM32G474RET6 | 1 | 9 | 9 |
| ESP32-S3-WROOM-1-N8 | 1 | 3 | 3 |
| TPS62130RGTR | 1 | 2,5 | 2,5 |
| ADuM1201ARZ | 1 | 1,5 | 1,5 |
| FH12-16S-0.5SH | 4 | 0,5 | 2 |
| USB-C USB4085, AP2112K, LP2985, AMS1117, 74AHCT1G125, USBLC6-2 | 6 | 0,3 | 1,6 |
| Self, FET, diodes, perle, buzzer, boutons, LED | 15 | 0,2 | 3 |
| Passifs, embases, fusibles | 60 | 0,05 | 3 |
| **Par cerveau** | 103 | | **26** |

Le silicium analogique des quatre quadrants (ADG1607, AD8421, OPA2810)
fait à lui seul 120 à 140 EUR : c'est le poste que la
[note 16](16-cout-des-cartes.md), section 2, propose de rediscuter
(single-ended, mux moins cher) avant d'engager les quatre cartes.

### 8.3 Le total, assemblé ou non

| Scénario | EUR hors taxes | Ce qu'il reste à souder |
|---|---|---|
| Cartes nues (5 + 5), composants achetés à part, port | 300 à 350 | tout : 4 x 324 plus 103 composants, dont deux LFCSP et un LQFP par carte |
| Assemblage économique de 4 quadrants et 1 cerveau, nomenclature complète | 430 à 480 | rien, si tous les codes LCSC sont en bibliothèque (l'ADG1607 reste à trouver) |

Frais fixes de l'assemblage comptés : préparation 7,16 et pochoir 1,35
par carte, 3 USD par référence étendue (une douzaine sur le quadrant,
une vingtaine sur le cerveau), la pose à la pièce. TVA de 20 % en sus
au paiement. Contre 281 EUR pour le devis du 20/09 de vingt cartes
2 x 2 mal appariées : le plateau entier, assemblé, coûte moins de deux
fois ce devis.
