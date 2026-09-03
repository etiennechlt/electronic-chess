# 14. Revue des cartes de la phase 1 (lot 1 de la note 07)

Revue du 03/09/2026 des quatre projets de la phase 1 : quadrant,
cerveau, puissance, horloge. Ce que la revue a regardé, ce qu'elle a
trouvé, ce qui a été corrigé dans les générateurs, ce qui reste à
trancher avant de commander. Les nombres de la section « Résultats »
sont ceux des builds et du DRC commités avec cette note.

## 1. Méthode

- **DRC KiCad** : KiCad 7.0.11 (paquet Ubuntu) et son module Python
  `pcbnew`, qui charge le projet, remplit les zones et écrit le même
  rapport que l'éditeur ; `tools/drc.py` l'enchaîne sur chaque carte
  ([runbook](08-regenerer.md)). KiCad 9 sur le poste donne le même
  résultat par `Inspection > Contrôle des règles`.
- **Netlist du schéma contre le circuit** : `kicad-cli sch export
  netlist` sur chaque schéma généré, comparée net par net et broche par
  broche au `Circuit` Python (`tests/test_schematics.py`). C'est ce
  test qui manquait : le schéma du quadrant reliait GND à 5VA.
- **Brochages** : relecture du câblage de chaque circuit intégré à
  partir des noms de broches des symboles officiels (netlist exportée)
  et des fiches techniques telles que connues de mémoire ; les fiches
  PDF de TI et ST n'étaient pas accessibles depuis l'environnement de
  revue, les points marqués « à confirmer » se relisent sur la fiche.
- **Analyseurs du skill KiCad** (`.claude/skills/kicad`) sur les
  quatre schémas et PCB : utiles pour l'inventaire (chaîne LED, budget
  de découplage), peu pour les brochages ; leurs constats recoupent
  ceux ci-dessous.
- **Non fait** : ouverture dans KiCad 9 (pas d'écran), consultation
  LCSC et JLCPCB en ligne (réseau fermé), simulation (lot 2).

## 2. Constats et corrections

### 2.1 Bloquants, corrigés dans les générateurs

| Carte | Constat | Correction |
|---|---|---|
| Quadrant | Les trois vias d'empilement de chaque bobine (jonctions F.Cu/In1, In1/In2, In2/B.Cu) étaient posées sur le rayon intérieur ou extérieur, là où les spires des deux autres couches passent un quart de tour plus loin, 0,4 mm plus loin en rayon : chaque via traversante recouvrait ces spires de 0,2 à 0,7 mm et court-circuitait la bobine entre couches. Le contrôle maison exemptait toute paire C{k}_A contre C{k}_B, le DRC de KiCad le voyait (98 isolements à zéro). La carte bobines de la maquette, générée par la même géométrie, a le même défaut. | Vias décalées radialement hors des bandes de spires (1,3 mm vers l'intérieur ou l'extérieur, 3,5 mm pour la dernière jonction qui porte le net tie), reliées aux spirales par un tronçon radial de la même piste ; l'exemption A/B des contrôles réduite aux deux pastilles du net tie. Le plan de bobinage de `coilgen` reste à corriger de même avant toute commande de la maquette. |
| Quadrant | Le schéma généré court-circuitait GND et 5VA : les groupes DECODERS et MUXES, espacés de 60 mm à la main, se chevauchaient (symboles plus hauts que l'espacement) et une étiquette de l'un tombait sur un tronçon de l'autre. Le PCB, généré du même objet `Circuit`, était juste. | L'émetteur de schéma (`analoggen/schematic.py`) empile désormais les groupes d'après leur hauteur réelle (broches, tronçons, longueur des étiquettes), le y demandé n'est plus qu'un minimum ; `tests/test_schematics.py` compare la netlist KiCad de chaque carte au circuit. |
| Puissance | Les deux FET d'entrée (ACFET, RBFET) étaient des AO3400A, canal N, alors que la sortie ACDRV du BQ24610 est active bas et pilote des canaux P : l'adaptateur n'atteignait jamais le chargeur. | AO3401A, drain commun, sources sur ACN et sur l'entrée du chargeur. |
| Puissance | Sources des FET de protection inversées : le FET DSG avait sa source sur PACK- et le FET CHG sur le côté cellules. Le pilote DSG du BQ76920 est référencé à VSS (côté cellules), le courant de décharge traverse la diode du FET CHG et n'est bloqué que par DSG. | DSG : source côté cellules (après la résistance de mesure), CHG : source sur PACK-, résistances grille-source suivant. |
| Puissance | Réseau TS du BQ24610 : 10 k vers REGN (6 V) et CTN 10 k vers la masse, soit 91 % de VREF à 25 °C, au-dessus du seuil « froid » (73,5 %) : charge suspendue à température ambiante. | Réseau de la fiche pour une CTN 103AT : 5,24 k depuis VREF, 30,31 k vers la masse (E96 : 5,23 k et 30,1 k), fenêtre 0 à 45 °C. |
| Puissance | Consignes de courant : avec 10 mohms, ISET1 à 1,1 V donnait 5,5 A de charge au lieu de 1 A, ISET2 à 0,3 V donnait 3 A de précharge et de fin de charge, ACSET à 1,1 V une limite d'entrée de 5,5 A sur une source PD de 3 A. | Résistance de mesure 50 mohms (1 A = 50 mV, la plage prévue pour ISET), ISET1 0,995 V (1,0 A), ISET2 0,101 V (0,2 A de précharge et de fin), ACSET 0,499 V (2,5 A). Formules ICHG = V(ISET1) / (20 RSR), IPRE = ITERM = V(ISET2) / (10 RSR), IIN = V(ACSET) / (20 RAC), à confirmer sur la fiche avec la plage admise de V(ISET2). |
| Cerveau | UART du module ESP32 croisée : les deux 0 ohm reliaient la sortie de l'isolateur (broche 6, VOB) à la sortie TXD0 du module et son entrée (broche 7, VIA) à l'entrée RXD0. Deux sorties en conflit, une entrée en l'air : aucun octet ne passait. | TXD0 vers COMM_TXD (entrée VIA), COMM_RXD (sortie VOB) vers RXD0 ; l'embase Pi était déjà dans le bon sens. |
| Cerveau | SWD : broches 6 (SWO) et 8 (TDI des sondes JTAG) reliées à NRST ; une sonde pilotant TDI aurait tenu le MCU en reset. | 6 et 8 non connectées. |
| Horloge | IO2 du module allait sur un net `LED_CHG` à une seule broche ; la LED de charge était sur STAT. STAT monte à VBUS (5 V), inadmissible sur une entrée du module. | Diviseur 56 k / 100 k de STAT vers IO2 (3,2 V au niveau haut, bas sans USB). |
| Horloge | Rétroéclairage de l'écran (broche LED du module 2,4 pouces, quelques dizaines de mA) piloté directement par IO7 : au-delà de ce qu'une broche fournit. | P-FET AO3401A côté haut sur 3V3, grille tirée haute (éteint au démarrage), IO7 actif bas. |
| Horloge, cerveau, puissance | Nets à une seule broche (`3V3_NC`, `NC`, `AFE_NC`, `SBU1`, `SBU2`, `BATDRV_NC`, `USB_DP`, `USB_DM`) que KiCad n'exporte pas et qui comptaient comme nets ouverts. | Broches déclarées non connectées ; sur l'horloge D+, D-, SBU du USB-C (alimentation seule) aussi. |

### 2.2 DRC : ce que KiCad refusait, corrigé dans les générateurs

Le contrôle d'isolement maison des générateurs disait zéro défaut ; le
DRC de KiCad en trouvait de 400 à 1500 par carte. Les familles :

| Famille | Cause | Correction |
|---|---|---|
| `via_diameter`, `drill_out_of_range`, `track_width` | Les règles écrites dans le `.kicad_pro` (via 0,6 ou 0,8 mm, perçage 0,3 ou 0,4, piste 0,25) ne connaissaient pas les vias d'éventail 0,45 / 0,2 mm, les tronçons de 0,2 mm ni les trous de 0,2 mm du module ESP32. | `design_rules` déclare ce que le build a réellement dessiné : minimum via et trou d'après les vias émises, minimum piste d'après les tronçons. |
| `courtyards_overlap` (121 sur le quadrant, 4 sur le cerveau) | Le lecteur de cours d'empreinte ne comprenait que l'ordre d'attributs de KiCad 6 ; avec les bibliothèques 7 il retombait sur « pastilles plus 0,25 mm », un SOT-23 faisait 3,0 mm de haut au lieu de 3,4, le module ESP32 24 x 19 mm au lieu de sa zone de dégagement d'antenne de 48 x 41. | Lecture par le parseur s-expression de toute primitive sur F.CrtYd. La cellule du quadrant est recomposée à partir des cours réelles (colonnes empilées, contrôlées contre le pas de 7,4 mm) ; sur le cerveau le module ESP32 est posé au bord est, antenne hors de la carte (recommandation Espressif), quatrième trou de fixation, embase Pi, connecteur puissance et boutons déplacés hors de la zone de dégagement ; sur l'horloge la cour du module est volontairement réduite à sa largeur (encodeur et microrupteur de part et d'autre), en le disant dans le code : BLE à courte portée. |
| `hole_near_hole` (via sur le trou d'une pastille traversante, 194 sur le cerveau) | Le routeur voyait la pastille traversante comme du cuivre de son net et y posait des vias. | Cellules de via interdites autour de chaque trou de pastille (trou à trou 0,25 mm). |
| `holes_co_located`, `hole_near_hole` via contre via | Via du routeur posée sur ou à 0,1 mm de la via d'éventail dont il repart. | Une via n'est plus émise si une via du même net couvre déjà le point. |
| `clearance` à 0,13 mm | Les contrôles maison toléraient 0,02 mm sous l'isolement déclaré. | Contrôle exact (tolérance numérique 0,001 mm). |
| `clearance`, `hole_clearance` sur le net tie des bobines (226 sur le quadrant) | La jonction In2 vers B.Cu était une pastille traversante du net A sous une pastille B.Cu du net B : KiCad n'exempte pas du dégagement de trou le cuivre d'un autre net posé sur un trou, même dans un net tie. | La jonction redevient une via ordinaire du net A ; le net tie est deux pastilles B.Cu carrées qui se touchent, 2,5 mm plus loin sur l'arc d'entrée de la dernière couche, la piste large s'arrêtant avant la pastille du net B. |
| `items_not_allowed` | Broches du connecteur puissance dans la zone d'exclusion d'antenne. | Résolu par le nouveau placement. |

Restent des avertissements sans effet sur la fabrication : recouvrements
de sérigraphie (références sur des lignes), bibliothèques d'empreintes
non configurées dans le contexte du DRC en ligne de commande, vias et
pistes pendantes des nets encore ouverts.

### 2.3 À trancher avant commande (non corrigé ici)

- **LDO 5VA du cerveau** : le LP2985 en SOT-23-5 alimente les frontaux
  des quatre quadrants (deux OPA2810 et un AD8421 par quadrant, environ
  17 mA chacun, 70 mA en tout) depuis VBAT : 0,5 W à 12,6 V, soit plus
  de 100 °C d'échauffement dans ce boîtier. Proposition : le
  TPS7A4901DGNR (MSOP PowerPAD) déjà retenu pour la maquette dans le
  yaml, ou un pré-régulateur.
- **CTN sur les cellules** : le yaml dit `ntc_on_pack: true`, les deux
  CTN sont des 0603 sur la carte puissance. Pour surveiller les
  cellules plates il faut une CTN collée sur le pack et deux broches de
  plus sur le connecteur cellules (JST XH 6 broches).
- **Courant des LED par nappe** : 32 WS2812B par quadrant sur une seule
  broche 5V_LED du FPC (0,5 A par contact chez Hirose). Aux couleurs de
  camp du yaml (blanc chaud 255/170/60, environ 38 mA par LED) un
  quadrant tire 1,2 A. Le firmware doit plafonner la luminosité à un
  quart environ (0,5 A par quadrant, cohérent avec le fusible LED de
  2 A du cerveau), ou la nappe doit doubler ses broches 5V_LED et GND.
- **Extinction et réveil** : le cerveau n'est alimenté qu'à travers le
  FET DSG ; s'il l'ouvre par I2C pour s'éteindre, rien ne le referme
  (le BQ76920 redémarre FET ouverts et attend un hôte). L'extinction
  propre du lot 6 doit garder DSG fermé et laisser l'interrupteur
  mécanique couper, ou la carte puissance doit recevoir un load switch à
  verrouillage.
- **Câbles FPC** : les deux extrémités portent le même FH12 (contacts
  du même côté du câble). Règle : un pli à 180° ou un pli diagonal
  retourne la face du câble ; avec un nombre impair de plis il faut un
  câble à contacts opposés (type B), pair un câble à contacts du même
  côté (type A) ; l'ordre des broches est direct tant que les deux
  connecteurs ont la sortie de câble du même côté. Les connecteurs du
  cerveau sortent tous au nord alors que les quadrants sortent à
  l'ouest et à l'est : le chemin des nappes dans la base (note 10) fixe
  le type de câble et l'orientation des connecteurs du cerveau ; à
  décider dans le modèle mécanique avant de commander les nappes.
- **USB-C du cerveau** : au bord ouest de la carte, à 40 mm de la paroi
  de la base dans le modèle mécanique. Fente dans la base au droit du
  connecteur, ou rallonge en façade.
- **Antenne du cerveau** : le module dépasse maintenant de 6 mm du bord
  est de la carte ; l'empreinte de 120 x 80 mm dans la base devient
  126 x 80, à reporter dans `mechanical/plateau.py`.
- **ADG1607 en 5 V simple** : le brochage vient du symbole officiel ;
  la tenue en alimentation simple 5 V et la résistance passante dans ce
  cas sont à lire sur la fiche (la fiche spécifie ±5 V et 12 V simple).
- **Isolateur sans isolation** : GND2 de l'ADuM1201 est la masse
  commune, le module ESP32 est sur la même carte : l'ADuM1201 n'est
  qu'un tampon. Acceptable pour le module ; si un Pi est branché sur
  l'embase avec sa propre alimentation, il faut une masse séparée et
  un convertisseur isolé, sinon retirer l'isolateur.
- **Détails à relire sur les fiches** : CE du BQ24610 tiré à REGN (6 V,
  seuil absolu à vérifier, VREF est le choix sûr) ; SMBJ24A qui écrête
  vers 39 V au-dessus du maximum absolu de VCC et ACP ; 22 ohms en série
  sur USB inutiles sur STM32G4 (sans effet) ; LED d'état sur PC13 à
  PC15 en puits de courant, à garder en puits et sous 2 MHz ; 470 ohms
  en série sur la ligne de données LED, 100 à 330 ohms est plus usuel.
- **Note 13, étape 2 du test** : « alimenter par USB-C » ne peut pas
  marcher, VBUS n'est relié qu'à la protection ESD ; le cerveau se
  teste avec une alimentation de laboratoire sur VBAT_IN (J10).

### 2.4 Vérifié sans remarque

STM32G474RE : les quatre entrées ADC sur quatre convertisseurs (PA0
ADC1_IN1, PA6 ADC2_IN3, PB0 ADC3_IN12, PB14 ADC4_IN4), TIM2_CH1 sur
PA5, TIM3 sur PC6 et PC8, USART3 sur PC10 et PC11, I2C1 sur PA15 et
PB7, TIM4_CH1 sur PB6, TIM2_CH3 sur PB10, USART1 sur PA9 et PA10, USB
sur PA11 et PA12, BOOT0 sur PB8, NRST sur PG10 : conformes. TPS62130 :
FSW bas (2,5 MHz), DEF haut (PWM forcé), diviseur 523 k / 100 k (4,98 V).
BQ24610 : côté buck (HIDRV, LODRV, BTST, PH, SRP, SRN), VCC par 10 ohms,
VFB 100 k / 20 k (12,6 V), STAT et PG tirés au 3,3 V de l'AFE. BQ76920 :
filtres de cellules, VC5 et VC4 sur VC3 pour 3S, REGSRC, CAP1, REGOUT,
TS1, mesure SRP côté VSS. INA219 : shunt entre CELL3 et PACK+, adresse
0x40. ADG1607 : adresses, enables, sorties en parallèle. 74HC4514 et
74HC154 : adresses (le quatrième bit est MUX_EN_H), inhibitions.
MCP73831 : 2 k sur PROG (500 mA). USB-C : 5,1 k sur CC1 et CC2, ESD
USBLC6-2. Diodes de roue libre des buzzers dans le bon sens.
Brochage FPC identique aux deux bouts.

## 3. Résultats des builds et du DRC

À jour au commit de cette note ; régénérer avec le runbook et relancer
`tools/drc.py` pour vérifier.

RESULTS_TABLE

Les nets ouverts restent ceux que le routeur ne ferme pas ; ils se
terminent dans pcbnew comme prévu par la note 13, et le DRC les compte
comme éléments non connectés jusque-là.

## 4. Ce qui reste pour clore le lot 1

1. Fermer les nets ouverts dans pcbnew (ou améliorer le routeur), puis
   `tools/drc.py` à zéro élément non connecté.
2. Trancher les points de la section 2.3, au moins le LDO 5VA, la CTN
   des cellules et le plafond de luminosité.
3. Confirmer sur les fiches les valeurs marquées « à confirmer » du
   BQ24610 (formules et plages ISET), de l'ADG1607 (5 V simple) et les
   maxima absolus cités.
4. Compléter les codes LCSC : `jlc-bom.csv` n'exporte que les lignes
   qui en ont un ; il manque tous les passifs (résistances, condensateurs,
   fusibles, embases, CTN, points de test), l'ADG1607, le buzzer, le
   support 18650, l'encodeur et les microrupteurs. Les codes se
   saisissent dans les définitions de pièces des générateurs (champ
   `lcsc` de `Part`), pas dans les CSV.
5. Vias 0,45 / 0,2 mm : dans les capacités standard de JLCPCB (via
   0,45 mm, perçage 0,2 mm, anneau 0,125 mm) d'après la table de règles
   du skill `jlcpcb` ; à confirmer dans le devis.
