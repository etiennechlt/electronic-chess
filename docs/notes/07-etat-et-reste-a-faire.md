# 07. État de référence et chemin vers le prototype réel

Dernière mise à jour : 02/09/2026. Ce qui est vrai ici est vérifiable
en régénérant ([runbook](08-regenerer.md)) ; les chiffres sont ceux
imprimés par les builds de référence commités.

## Ce qui est fait (phase 0 et phase 1 conception)

| Livrable | État |
|---|---|
| Calculs `chessboard_calc`, yaml, ADR 0001 à 0009 | complets, épinglés par les tests |
| Carte bobines (4 couches, spirales + 8 LED de camp) | générée, gardes vertes, gerbers commités |
| Carte analogique (chaîne complète + tampon LED) | générée : 499 pistes, 259 vias, DRC zéro, 12 raccords de finition posés |
| Firmware Nucleo G474 | compile en CI, deux voies, calibration flash, pilote LED |
| Mécanique CadQuery | pucks, gabarits de bobinage, support aimant, gabarit de perçage bois, STL/STEP exportés |
| Protocole de mesure | M1 à M11, gabarits CSV, notebook d'analyse |
| Approvisionnement | fiche comparée Europe/Asie, prix datés, quatre commandes conseillées |
| Qualité | 66 tests verts, couloir bloquant en CI, ruff propre |

## Pivot du 02/09/2026 (ADR 0010) et état au 03/09/2026

La maquette 2 x 2 n'est plus construite : le plateau 8 x 8 est conçu
directement en quadrants 4 x 4, avec un module plateau invariant et
deux bases interchangeables (fine, ou chariot en option), des cellules
plates, un cerveau à MCU soudé, un emplacement ESP32-S3 et Pi, et une
horloge à bascule séparée en BLE.

Fait : yaml (sections `plateau` et `clock`, `gap.air_mm`, batterie
plate, p = 50 figé), géométrie dérivée et tests, modèles CadQuery du
plateau et de l'horloge avec STL et STEP versionnés dans
`mechanical/exports/`, rendus et vue 3D interactive, ADR 0010 et
[note 10](10-plateau-8x8-et-horloge.md) ; quadrant complet (spirales,
échappées, LED, distribution, FPC, frontal placé et routé) ; cerveau,
puissance, moteurs et horloge générés par `tools/boardgen`
([note 11](11-cartes-du-plateau.md)) ; firmware du cerveau compilé,
pont radio et horloge écrits contre ESP-IDF, protocole fixé
([note 12](12-protocole.md)) ; guide d'ouverture, de vérification et
de test ([note 13](13-revue-et-verification.md)).

## Décision de phasage

**Phase 1 : tout doit fonctionner sans chariot.** Base fine, module
plateau, cerveau, puissance, horloge, firmware et application. Le
chariot (base chariot, carte moteurs, ailes de capture, actionneur
d'aimant, arbitre de déplacement) est la **phase 2** et ne commence
qu'une fois la phase 1 jouable de bout en bout. Ce qui est déjà conçu
pour le chariot (carte moteurs, base chariot, nappe vers le cerveau,
interlock) est conservé tel quel et n'est ni commandé ni testé avant.

## Phase 1, dans l'ordre

Chaque lot a un critère de sortie ; on ne passe au suivant qu'une
fois le critère tenu. L'ordre n'est pas arbitraire : chaque lot
dépend du précédent et coûte de plus en plus cher à reprendre (une
relecture est gratuite, une carte recommandée coûte trois semaines et
une centaine d'euros, un bobinage refait coûte une soirée).

### 1. Revue des cartes

**Quoi.** Ouvrir les quatre projets de la phase 1 dans KiCad 9
(quadrant, cerveau, puissance, horloge), lancer le DRC, fermer à la
main les nets que le routeur a laissés ouverts (8, 25, 10 et 6),
relire les brochages marqués « à vérifier » contre les fiches
techniques, confirmer les vias d'éventail de 0,45 mm chez le
fabricant ou les remplacer, compléter les codes LCSC.
Méthode : [note 13](13-revue-et-verification.md), sections 1 et 2.

**Pourquoi.** Les cartes sortent d'un générateur qui garantit la
cohérence schéma-PCB, les valeurs dérivées du yaml et l'isolement de
ce qui est tracé, mais pas trois choses : ce qui n'est pas tracé (les
nets ouverts), ce que les bibliothèques KiCad ne savent pas (les
fonctions alternatives du STM32, l'application type des BQ, le sens
des câbles), et ce que le fabricant accepte (vias). Une erreur de
brochage découverte après commande se répare au fil volant au mieux,
par une nouvelle commande au pire. C'est le lot le moins cher et
celui qui évite les reprises les plus chères.

**Sortie.** Zéro erreur DRC, zéro net ouvert, liste des « à vérifier »
cochée, BOM avec un code LCSC ou une source par ligne.

### 2. Simulation

**Quoi.** Lancer `chain-spice.cir` (AD8421 puis Sallen-Key) et écrire
le banc SPICE de la cellule d'excitation et d'amortissement (bobine
de case 16 µH, AO3400A, roue libre SS34FL, écrêteurs BAV99, 330 ohms
devant le mux) : impulsion de 100 ns environ, retour à zéro, tension
vue par le mux. Méthode : note 13, section 3.

**Pourquoi.** La chaîne a été validée sur la maquette mais ses
valeurs ont été reprises dans un nouveau schéma : une relecture par
simulation coûte une heure et attrape une erreur de recopie. La
cellule n'a jamais été simulée avec ses composants définitifs ; c'est
elle qui décide si l'impulsion excite bien le résonateur sans
saturer ni casser le mux (le ADG1607 tolère peu au delà de ses rails),
et le seul moyen de le savoir avant d'avoir la carte est de la
simuler. Une cellule mal dimensionnée touche seize fois par quadrant,
donc soixante-quatre fois.

**Sortie.** Gain plat de 200 à 650 kHz avec les coupures attendues ;
sur la cellule, pic d'excitation dans la plage prévue par la note 01,
amortissement complet avant la fenêtre de mesure, aucune tension hors
rail à l'entrée du mux.

### 3. Commande et fabrication

**Quoi.** Exporter les gerbers depuis KiCad 9, commander quatre
quadrants (4 couches, assemblés), un cerveau (4 couches), une carte
puissance et une horloge (2 couches) ; acheter les trois cellules
plates, les aimants ferrite, le fil, le feutre ; imprimer les pièces
de `mechanical/exports/` (socle fin, contreplaqué gabarit, pucks,
gabarits de bobinage, boîtier d'horloge) ; percer le contreplaqué avec
`surface-template`. Pas de carte moteurs ni de base chariot.
Méthode : note 13, section 4.

**Pourquoi.** C'est le point de non-retour financier, d'où sa place
après la revue et la simulation. Commander les quatre quadrants d'un
coup est délibéré : c'est le même fichier, le prix marginal est
faible, et un quadrant seul suffit aux mesures pendant que les trois
autres attendent. Le contreplaqué et les impressions se lancent en
parallèle parce qu'ils ne dépendent pas des cartes et que leur délai
est le plus long après celui du fabricant.

**Sortie.** Tout le matériel de la phase 1 reçu et inventorié contre
la BOM, pièces imprimées ajustées à blanc dans le socle.

### 4. Bring-up électrique

**Quoi.** Dans l'ordre de la note 13, section 5 : quadrant hors
tension (continuité des bus, absence de court, chaque bobine mesurée),
cerveau seul sous USB-C (rails 5 V, 3,3 V, 5VA, courant au repos,
console série), quadrant sur le cerveau (scan d'un quadrant, CSV), LED
(camps allumés, chaîne des quatre quadrants), carte puissance d'abord
sous alimentation de laboratoire limitée en courant puis sur cellules
avec charge USB-C PD, en lisant l'INA219 et le BQ76920.

**Pourquoi.** Chaque étape n'alimente qu'un sous-ensemble et ne peut
détruire que lui : une bobine en court ou un rail inversé se voient
au multimètre avant de coûter un circuit intégré. Le cerveau seul
avant le quadrant isole les problèmes de rail de ceux de mesure. La
carte puissance passe en dernier et sous limitation de courant parce
que c'est la seule qui peut mettre le feu : un BQ76920 mal câblé sur
des cellules lithium ne pardonne pas. Le firmware du cerveau expose
déjà tout ce qu'il faut pour ce lot (commandes `h`, `1` à `4`, `l`,
`o`), donc il ne demande aucun développement.

**Sortie.** Un quadrant scanne ses 16 cases avec un SNR positif sur
un puck de test, les 128 LED répondent, le pack charge et se protège
(coupure sur sous-tension et surintensité vérifiée à la charge
factice).

### 5. Mesures M1 à M11 et calibration

**Quoi.** Dérouler le [protocole](../../measurements/protocol.md)
écrit pour la maquette, le quadrant remplaçant la carte bobines et le
cerveau la Nucleo : Q à vide et avec ferrite, SNR, séparation des 12
classes, dispersion entre cases et entre pucks, tenue au bois, bruit
des LED, comparaison des deux voies d'extraction. Puis calibrer les
12 classes en flash sur les 64 cases et remplir le tableau de
synthèse.

**Pourquoi.** Le projet repose sur une hypothèse physique (un
résonateur passif sous aimant ferrite reste discriminable à travers
7 mm de bois et d'air) qui n'a été que calculée. M2 est la mesure
décisive : si le Q chute trop avec la ferrite, il faut revoir les
classes ou l'aimant avant tout le reste. M4 à M6 donnent les marges
réelles de calibration, M9 choisit la voie d'extraction que le
firmware gardera, M11 dit si les LED peuvent rester allumées pendant
la mesure. Faire ces mesures sur le matériel définitif, et non plus
sur une maquette, évite de valider une chose pour en construire une
autre.

**Sortie.** Tableau M1 à M11 rempli, chaque pièce identifiée sur
chaque case avec la marge de séparation attendue (au moins 2,4
largeurs de raie), voie d'extraction choisie.

### 6. Firmware du cerveau

**Quoi.** Ajouter à `firmware/board` ce qui manque pour jouer :
l'arbitre (génération des coups légaux, roque, promotion, prise en
passant, détection du coup joué à partir de deux scans), les messages
de partie `B`, `M`, `F`, `S` de la [note 12](12-protocole.md), l'I2C
vers la carte puissance (jauge, tensions de cellule, extinction
propre), le buzzer, les LED d'état, le bouton, l'aide au coup par les
LED de case.

**Pourquoi.** Après le lot 5 le plateau sait lire ; il ne sait pas
encore jouer. L'arbitre vient avant la radio parce que le cerveau
doit rester maître de la partie sans horloge ni réseau (décision de
l'ADR 0010) et parce que le protocole de la note 12 ne transporte que
ce que l'arbitre produit. Le développer sur une mesure calibrée, et
non sur des valeurs simulées, évite d'écrire une détection de coup
pour des données qui n'existent pas.

**Sortie.** Une partie humain contre humain jouée sur le plateau seul,
coups illégaux refusés et signalés par les LED, position finale
correcte à l'export FEN sur la console.

### 7. Pont radio, horloge, application

**Quoi.** Première compilation ESP-IDF du pont et de l'horloge
(`firmware/esp32`), appairage BLE, échange des lignes `N`, `C`, `T`,
`R`, puis WiFi et client Lichess Board sur le pont (`X` pour le coup
adverse, `L` pour l'aide), et l'interface minimale sur l'horloge
(cadences, mode, appairage).

**Pourquoi.** Ce lot ne touche ni au plateau ni au cerveau, qui sont
alors stables et testés : tout ce qui casse ici est côté radio, ce
qui rend le débogage simple. L'horloge d'abord parce qu'elle est
autonome (une seule liaison, un protocole texte lisible au terminal),
Lichess ensuite parce que l'API impose une authentification et une
gestion de session qu'il vaut mieux mettre au point une fois le reste
figé.

**Sortie.** Partie en cadence Fischer avec l'horloge, partie en ligne
jouée jusqu'au bout contre un adversaire distant, reconnexion propre
après coupure BLE.

### 8. Assemblage final

**Quoi.** Base fine complète (cartes et cellules sur leur empreinte,
nappes FPC, interrupteur, USB-C), module plateau (quadrants, entretoises,
contreplaqué, feutre), finition du bois, horloge dans son boîtier, et
le tournage de la série vidéo.

**Pourquoi.** Dernier parce que tout ce qui précède se fait plus
facilement sur table, cartes visibles et sondes accessibles. Fermer
le plateau avant la fin des mesures obligerait à le rouvrir.

**Sortie.** Un plateau fermé, jouable, rechargeable, avec son horloge,
et les rushs de la série.

## Phase 2 : chariot

Commander et tester la carte moteurs, imprimer la base chariot et les
ailes, monter le CoreXY et l'actionneur d'aimant, valider M7 (approche
du N42) et l'interlock scan / aimant, écrire le déplacement (A* dans
les interstices, parking hors zone) et la partie contre le moteur
avec pièces déplacées par le plateau. Tout ce qui précède reste
valable : le module plateau et le cerveau ne changent pas, seule la
base est remplacée et la carte moteurs branchée sur la nappe prévue.

## Ce que chaque mesure décide

| Mesure | Décision alimentée |
|---|---|
| M2 (chute de Q avec ferrite) | viabilité du choix ferrite, la mesure décisive du projet |
| M4 à M6 (SNR, séparation, dispersion) | marges de calibration au pas p = 50 |
| M7 (approche du N42) | distance de parking du chariot (phase 2) |
| M8 (buck contre LDO, radio) | buck seul ou LDO renforcé sur le cerveau |
| M9 (voies A/B) | voie d'extraction retenue |
| M10 (bois contre acrylique) | valide la surface contreplaqué (attendu : neutre) |
| M11 (bruit LED) | valide le fenêtrage structurel |

## La maquette 2 x 2 (référence, non construite)

Ses fichiers restent dans `hardware/mockup-2x2/` et `firmware/mockup/`
comme référence de la chaîne analogique et de la double voie
d'extraction. Ses points ouverts (sept nets à fermer sur la carte
analogique, jack J1 à décaler) ne sont plus à traiter.
