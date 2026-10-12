# Protocole de mesure de la maquette 2 x 2

Objectif : trancher les incertitudes du brief (section 6, mesures 1 à
8) plus les extensions issues de la lecture critique. La mesure 2
valide ou invalide le pivot de l'architecture (aimant ferrite), la 4
oriente le choix du MCU, la 7 dimensionne l'interlock, la 8 arbitre
l'alimentation. La section « Maquette Hall + RFID » ajoute M12 à M14,
pour la carte de la note 25, avec son propre matériel.

## Matériel

- Carte bobines + carte analogique assemblées, Nucleo-G474RE flashée
  (`firmware/mockup`), console série 921600 bauds.
- 4 pucks de test imprimés avec résonateurs bobinés : 12 nF (pion
  noir, 217 kHz), 10 nF (cavalier, 237), 8,2 nF (fou, 262), 6,8 nF
  (tour, 288). Bas de bande volontairement : si ces quatre-là se
  discriminent, le reste de la table est acquis.
- Aimants : ferrite SrFe ø12,5 x 4 (pucks) et N42 ø15 x 5 (support
  réglable), un aimant néodyme supplémentaire pour la mesure 3.
- Oscilloscope conseillé sur TP1 (INA) et TP2 (AMP_OUT) mais le
  firmware suffit pour tous les critères chiffrés.
- Optionnel : LCR-mètre pour L et Q de référence des bobines nues.

Relevés : un fichier CSV par mesure dans `measurements/data/`, gabarits
dans `measurements/data/templates/`, analyse par
`measurements/analysis.ipynb` (fonctions dans `analysis.py`).

## Séquence recommandée

Chaque mesure indique : préparation, acquisition, critère.

### M1. Q du résonateur seul (critère : >= 40 par classe de diamètre)

Par puck, SANS aimant : poser le puck sur sa case, `r` (dump brut),
sauver en `m1_q_<classe>.csv`. L'analyse extrait Q par décrément
logarithmique de l'enveloppe (référence, vérifiée à 2 % sur signaux
synthétiques) ; la largeur spectrale ne fournit qu'une borne
inférieure avec 512 points. La modélisation prévoit le pion
comme cas limite : si Q < 40, essayer le fil de Litz avant de
conclure.

### M2. Q avec aimant ferrite (critère : >= 30 et chute <= 20 %)

Insérer les aimants ferrite dans les pucks, refaire M1 en
`m2_q_ferrite_<classe>.csv`. C'est la mesure pivot : un échec ici
remet l'architecture en cause (repli : reed switches).

### M3. Q avec aimant néodyme, comparaison (chute attendue 40 à 70 %)

Remplacer le ferrite par un N42 équivalent dans un puck,
`m3_q_neodyme.csv`. Quantifie ce que la décision ferrite évite.

### M4. Amplitude et SNR à l'entrefer nominal (critère : SNR >= 20 dB)

Pucks complets, entrefer nominal (PCB + surface 3 mm, bois ou
acrylique selon M10, + feutre).
`s` puis `m` pendant 60 s, `m4_snr.csv`. Critère sur la colonne
snr_db10 (>= 200). Extension M4bis : répéter avec cales à l'entrefer
max 8 mm, critère SNR >= 10 dB.

### M5. Diaphonie case voisine (critère : <= -20 dB)

Un seul puck sur S1, scanner S1 à S4. Rapport d'amplitude
S2/S1 en dB, `m5_diaphonie.csv`.

### M5bis. Détuning mutuel entre résonateurs identiques (< 3 kHz)

Extension de la lecture critique (D) : la position initiale aligne
des pièces identiques. Mesurer f du 12 nF seul sur S1, puis avec un
second 12 nF sur S2 (et S3 si disponible), `m5bis_detuning.csv` :
décalage de fa < 3 kHz.

### M6. Dispersion de f sur 4 bobines main (critère : <= +-3 %)

Bobiner 4 bobines identiques (même gabarit), les mesurer tour à tour
dans le même puck avec le même condensateur, `m6_dispersion.csv`.
Valide l'hypothèse de calibration sans tri.

### M7. Approche du N42 par dessous (dimensionne le parking)

Support réglable sous S3, puck sur S3. Descendre l'aimant par pas de
1 mm (vis M3 : 0,5 mm par tour), relever fa et amp à chaque pas,
`m7_parking.csv`. Chercher la distance où le décalage dépasse 2 kHz :
c'est la distance de parking minimale. Extension M7bis : mesurer
aussi l'effort d'arrachement sur le puck (l'aimant rétracté passera
sous des pièces stockées en bande).

### M8. Plancher de bruit et architecture d'alimentation (<= 6 dB)

Sans puck, dump brut `r` répété dans chaque configuration,
`m8_bruit_<config>.csv` :

1. alimentation analogique par LDO (JP1 côté LDO), Pi absent ;
2. LDO, Pi alimenté sur J5 mais idle ;
3. LDO, Pi en émission WiFi (iperf) ;
4. buck filtré (JP1 côté buck), JP3 en forced PWM, mêmes trois cas ;
5. buck en PFM (JP3 côté PFM) : quantifie le piège des rafales.

Critère du brief : delta <= 6 dB entre Pi éteint et WiFi en émission
avec les mitigations en place. Comparer aussi buck FPWM contre LDO :
si l'écart est < 3 dB, le buck seul suffit au plateau final.

### M9. Comparaison des voies A et B (décision 5.2)

Transversale : chaque CSV contient fa et fb. L'analyse produit
biais, écart-type et taux de rejet de la voie B en fonction du SNR.
Décision : si fb est disponible et stable (écart-type < 200 Hz) sur
M4, la voie B gagne et le choix du MCU s'ouvre.

### M10. Surface bois contre acrylique (ADR 0009)

Poser successivement la plaque d'acrylique 3 mm puis la planche de
contreplaqué (même épaisseur si possible, sinon noter l'écart) entre
la carte bobines et la pièce de test, sans rien changer d'autre.
Relever pour la case 1 : fa, amplitude et SNR, 16 mesures par surface.
Refaire la série bois après 24 h dans une pièce humide (salle de
bain) pour borner l'effet de l'humidité.

Critère : décalage de fréquence < 500 Hz entre surfaces (attendu :
quelques Hz), chute d'amplitude cohérente avec l'écart d'épaisseur
seul, chute de Q < 10 % même bois humide.

### M11. Bruit des LED de camp (ADR 0009)

Sur la case 1 avec pièce posée : série de 16 mesures LED éteintes
(commande `o`), puis 16 avec les 8 LED au blanc plein (`l` après une
calibration factice, ou en forçant les couleurs), la trame étant par
construction envoyée hors mesure. Comparer plancher de bruit, sigma
de fa et amplitude.

Critère : aucun écart mesurable de sigma fa (< 100 Hz) ni du plancher
(< 1 dB) entre LED éteintes et allumées statiques.

## Maquette Hall + RFID (note 25)

Objectif : répondre aux questions Q1 à Q11 du paragraphe 1 de la [note
25](../docs/notes/25-maquette-hall-rfid.md) avec la carte `hallrfid`
(quatre cases A1, B1, A2, B2 : boucles par colonne, lecteurs par rangée,
un capteur Hall par case et l'amas de la case
`hall_rfid.mockup.hall.cluster_square`). La maquette ne tranche pas pour
la RFID : elle produit les mesures qui permettront de trancher (ADR 0001
et note 24, section 7). M12 mesure la chaîne Hall, M13 la chaîne RFID,
M14 leur cohabitation et l'effet de la mécanique du plateau.

Toutes les valeurs nommées par une clé viennent de `config/board.yaml` :
une clé qui commence par `layout.`, `presence.`, `esp32.` ou `mockup.`
est sous `hall_rfid`, une clé `criteria.` sous `hall_rfid.mockup` (les
nombres du banc et les critères qu'aucune autre clé ne porte), les
autres sont écrites depuis la racine du yaml (`gap.max_total_mm`,
`hall_rfid.nfc.h_max_a_per_m`). `hall.*` et `nfc.*` désignent des
fonctions de `chessboard_calc`, dont les grandeurs de comparaison sont
imprimées par `python -m chessboard_calc report`. `mockup_criteria(cfg)`
de `analysis.py` rassemble ces seuils ; les fonctions d'analyse les
prennent en argument, et par défaut dans le yaml.

### Matériel

- Les cartes `hallrfid` assemblées
  (`mockup.quantities.boards_assembled`), posées sur leurs entretoises
  nylon de `mockup.board.standoff_mm`, loin de tout métal : toute mesure
  RF se fait ainsi (paragraphe 1 de la note 25). Une carte nue pour les
  boucles seules.
- Console du micrologiciel `hallrfid` (lot 7) sur l'USB-Serial-JTAG :
  commandes de mise en route et de mesure, qui écrivent les CSV de M12 à
  M14 ; adaptateur USB série 3,3 V pour l'UART0 en secours.
- Planche d'étiquettes assemblée : étiquettes P et G aux accords de
  `mockup.tags.trims_pF`, Murata en option ; chaque étiquette lue au
  téléphone avant d'entrer dans une pièce, UID noté. Cartes NTAG213 du
  commerce de référence.
- Vignette de champ soudée à la main (planche d'étiquettes), reliée à
  `PICKUP` par trois fils torsadés.
- Pièces imprimées (`mockup.prints`) : pièces de test numérotées, aimant
  amovible et logement d'étiquette ; plaque de surface ; cales
  d'entrefer, dont celle de l'entrefer maximal (`gap.max_total_mm` moins
  l'entrefer nominal, taillée dans une planche d'étiquettes nue) ;
  escalier de soulèvement ; gabarit de décalage.
- Aimants ferrite achetés au lot 1 (`mockup.magnets`), numérotés,
  diamètre et épaisseur relevés au pied à coulisse, nuance notée ; un
  aimant nu par diamètre pour M12a.
- NanoVNA étalonné (kit SMA), sonde de champ proche (boucle sur SMA,
  aire relevée), deux câbles U.FL vers SMA, balun 1:1 si disponible.
- Pied à coulisse avec jauge de profondeur, multimètre, alimentation de
  laboratoire limitée en courant, résistance de tirage de
  `criteria.tx_pullup_ohm` pour M13b.
- M13c : deux résistances de `criteria.mux_emulation_rq_ohm` et un
  condensateur de `criteria.mux_emulation_c_pF` du colis LCSC. M14b :
  plaques d'aluminium et d'acier plus grandes que la zone de jeu,
  l'aimant du chariot (`carriage.magnet`), cales nylon aux distances de
  `criteria.disturber_distances_mm`.

### Relevés et conventions

Un CSV par mesure dans `measurements/data/`, copié des gabarits de
`measurements/data/templates/` (remplacer la ligne d'exemple), lu par
les chargeurs de `analysis.py` :

| Gabarit | Mesures | Chargeur |
|---|---|---|
| `m12_planeite.csv` | planéité de la plaque | `load_flatness_csv` |
| `m12_hall.csv` | M12a, M12b, M12c | `load_hall_csv` |
| `m12d_chaine.csv` | M12d | `load_chain_csv` |
| `m13_vignette.csv` | étalonnage de la vignette | `load_pickup_csv` |
| `m13_rfid.csv` | M13a, M13b (lectures), M13c, M13d | `load_rfid_csv` |
| `m13b_etats_tx.csv` | M13b (broches TX, `VersionReg`) | `load_tx_state_csv` |
| `m14_cohabitation.csv` | M14a, M14b | `load_cohab_csv` |

Les balayages du NanoVNA s'enregistrent en Touchstone (`.s1p`, `.s2p`),
lus par `load_touchstone`, nommés `m13_boucle_<boucle>_<carte>`,
`m13_accord_<case>_<méthode>`, `m14a_etiquette_<pièce>_<aimant>`,
`m14b_<perturbateur>_<distance>`.

- **Repère.** x le long de la rangée (de la colonne A vers B), y le long
  de la colonne (de la rangée 1 vers 2). Les décalages `x_mm`, `y_mm`
  sont ceux de la pièce ou de l'étiquette par rapport au centre de sa
  case (pour M12, la case du capteur ; un voisin sur la case latérale
  est donc à x = p).
- **Capteurs.** `A1`, `B1`, `A2`, `B2` pour les capteurs centraux ;
  l'amas de `mockup.hall.cluster_square` ajoute `A1_ne`, `A1_nw`,
  `A1_sw`, `A1_se` (ne : +x, +y), aux points (±r p, ±r p) de
  `mockup.hall.cluster_offset_ratio` (`cluster_sensor_offsets_mm`).
  `path` vaut `direct` (entrée ADC1 du capteur) ou `mux` (voie
  `mockup.mux_channels.centre` ou `cluster`).
- **z Hall** : de la face inférieure de l'aimant au plan de Hall, somme
  de cotes relevées au pied à coulisse : hauteur de la face supérieure
  de la plaque au centre de la case (planéité, ci-dessous), plus la cale
  ou la marche d'escalier, plus le retrait de la face de l'aimant dans
  la base (jauge de profondeur, aimant enfoncé), moins
  `layout.die_height_mm`. `lift_mm` garde la valeur nominale de la cale
  ou de la marche, z la valeur mesurée.
- **z RFID** : du cuivre de la boucle au cuivre inférieur de
  l'étiquette : hauteur de la plaque, plus la cale, plus le retrait de
  l'étiquette dans la base, ruban compris
  (`hall_rfid.nfc.tag.height_in_base_mm` nul au modèle).
- **Comptes Hall.** `mean_counts` et `std_counts` : moyenne et écart
  type de `n_samples` lectures, chacune moyennée par le micrologiciel
  comme en service ; `zero_counts` : le zéro du capteur, case vide ;
  `rail_half_counts` : la voie de référence (`mux_channels.rail_half`,
  rail commuté de la rangée 1 divisé par deux) lue avec la mesure.
  `counts_to_mT` convertit avec la sensibilité du capteur monté
  (`mockup.hall.sensor`) et le pas de l'ADC (`hall.adc_lsb_mv`) ; la
  voie de référence corrige le zéro et la pente ratiométriques des
  capteurs de la rangée 1 : M12a à M12c se font donc sur des capteurs de
  la rangée 1.
- **Variantes d'étiquette** (`variant`) : la lettre de la taille suivie
  de l'accord ajouté en pF, pour chaque accord de `mockup.tags.trims_pF`
  (`tag_variants` : P0 pour l'étiquette P nue) ; `MURATA` pour
  l'étiquette à antenne intégrée, `REF` pour une carte NTAG213 du
  commerce.
- **Lectures RFID.** Un essai est une séquence ISO 14443A complète
  (REQA, anticollision, SELECT) ; il réussit si l'UID lu est celui de
  l'étiquette posée. Un émetteur à la fois ; sauf en M13b, les lecteurs
  inactifs sont dans l'état `held`. `cwgsp` et `cwgsn` sont les valeurs
  des champs `CWGsP` (registre `CWGsPReg`) et `CWGsN` (registre
  `GsNReg`) ; le courant TVDD se lit en millivolts aux bornes de
  `mockup.reader.r_sense_ohm`.
- **États d'un lecteur inactif** (`neighbor_state`, `state`) : `held`,
  émetteurs validés, `Force100ASK` à 1, `DriverSel` à 10, `MFIN` à PVSS,
  l'état où la fiche tient TX1 et TX2 à 0, celui du service ; `txoff`,
  émetteurs coupés (`Tx1RFEn`, `Tx2RFEn` à 0), état non spécifié par la
  fiche ; `softpd`, mise hors tension logicielle (bit `PowerDown` de
  `CommandReg`) ; `hardpd`, `NRSTPD` à la masse ; `hiz`, `DriverSel` à
  00, seulement par une commande de mesure explicite, le micrologiciel
  ne l'écrivant jamais en service.
- **Séries de lectures et bornes.** Une série compte
  `criteria.read_trials` essais, une série de confirmation
  `criteria.read_trials_confirm` ; une série passe si son taux de
  lecture atteint `criteria.read_target_rate`. Les bornes sont
  unilatérales au niveau `criteria.confidence` (Clopper-Pearson,
  `binomial_upper_bound`) : une série entière borne l'échec d'autant
  plus bas qu'elle compte d'essais, et une série sans lecture voisine
  borne de même la lecture parasite.
- **Champ de service.** La conductance de service d'une case est la plus
  forte qui garde le champ sous `hall_rfid.nfc.h_max_a_per_m` à la
  vignette, étiquette centrée à l'entrefer nominal, où il est le plus
  fort ; le champ de service est celui qu'elle donne au poste de
  l'étiquette.

### Mise en route (note 25, paragraphe 10.1)

Avant toute mesure, carte par carte, en notant au
[journal](../docs/notes/09-journal.md) chaque courant relevé et la
valeur de `VersionReg` de chaque lecteur.

1. Contrôle visuel des quatre QFN et du module à la loupe ; 5 V et 3,3 V
   contre la masse au multimètre. Critère : aucun court-circuit.
2. Première tension par les pastilles 5V, jamais en même temps que
   l'USB : alimentation de laboratoire à 5 V limitée au premier courant
   de `criteria.bringup_supply_limit_ma`, lecteurs en mise hors tension
   matérielle (`NRSTPD` tirées à la masse), rangées Hall coupées.
   Critère : 3,3 V présent, courant de l'ESP32 seul, sans radio, aucun
   échauffement.
3. Flashage par l'USB-C (USB-Serial-JTAG, BOOT tenu à la mise sous
   tension si le module ne s'énumère pas) ; à défaut, UART0 par les
   points de test (`mockup.esp32.pins`, `UART0_TX` et `UART0_RX`). Si le
   module ne démarre pas : barrette d'échappement, cavalier sur EN et
   ESP32-S3-DevKitC.
4. Limite de l'alimentation portée au second courant de
   `criteria.bringup_supply_limit_ma` : l'ESP32 et tous les capteurs à
   leur courant maximal dépassent le premier. Rangées Hall une à une
   (`ROW_EN1`, puis `ROW_EN2`). Critère : le courant croît du nombre de
   capteurs de la rangée (un par case, plus l'amas sur la rangée de
   `mockup.hall.cluster_square`) fois `i_supply_ma` du capteur monté
   (`hall_rfid.sensors`), au plus fois `i_supply_max_ma` ; zéros
   relevés ; un aimant passé à la main sur chaque capteur, pôle sud face
   au boîtier, fait monter sa lecture, sur sa voie de mux et, pour un
   capteur central, sur son entrée directe.
5. Lecteurs réveillés un à un (`NRSTPD` haut), émission coupée.
   Critère : `mockup.reader.i_idle_ma` de plus chacun, au plus
   `i_idle_max_ma` ; `VersionReg` lu (l'une des valeurs
   `criteria.nxp_version_reg` pour la puce NXP, valeur du clone notée
   dans `m13b_etats_tx.csv`).
6. Première émission d'un seul lecteur à conductance minimale, carte sur
   ses entretoises : courant TVDD relevé ; lecture d'une carte NTAG213
   du commerce, puis d'une étiquette P0 déjà lue au téléphone. Critère :
   courant TVDD sous `mockup.reader.i_tvdd_accept_ma` à chaque pas de
   conductance, sinon arrêt et accord d'abord.
7. Accord au NanoVNA (ci-dessous), puis seulement pleine conductance,
   case par case, une fois le courant TVDD mesuré sous
   `i_tvdd_accept_ma`.

### Accord au NanoVNA (préalable de M13)

**Boucles seules.** Sur la carte nue, un câble SMA dénudé soudé aux
pastilles d'alimentation de chaque géométrie de boucle : S11 enregistré
(`m13_boucle_<boucle>_<carte>.s1p`), inductance et résistance à la
porteuse (`hall_rfid.nfc.f_hz`), fréquence propre. C'est la vérification
directe du modèle d'inductance (`nfc.antenna` corrigée et modèle par
filaments, point 10 du paragraphe 2 de la note 25). Critère : inductance
mesurée comparée au modèle, l'écart reporté sur l'accord avant toute
émission ; au-delà de `criteria.loop_l_tol_pct`, réseau recalculé avec
l'inductance mesurée. En deçà non plus, le courant TVDD n'est pas
garanti : avec C1 et C2 à `mockup.matching.cap_tol_pct` et l'inductance
à `criteria.loop_l_tol_pct` du modèle, il peut dépasser
`mockup.reader.i_tvdd_max_ma` (`nfc.tx_supply_spread`). La première
émission à conductance réduite, courant TVDD lu, reste donc obligatoire
dans tous les cas (mise en route, étape 6).

**Réseau d'adaptation.** Lecteur isolé : retirer les deux 0 Ω entre TX1,
TX2 et les selfs L0, monter les deux U.FL à l'entrée de chaque
demi-réseau. Étiquette `mockup.matching.tune_tag` nue, centrée, à
l'entrefer nominal (condition d'accord du paragraphe 4.4 de la note 25).
L'impédance à viser est différentielle, entre les deux entrées ; trois
méthodes la donnent :

1. **Balun 1:1** (référence) : NanoVNA étalonné en bout de câble, le
   balun entre le port 1 et les âmes des deux U.FL, blindages à la masse
   de la carte ; le S11 lu est directement l'impédance différentielle
   (fichier `_balun.s1p`).
2. **Deux ports, sans balun** : étalonnage complet (avec la traversée)
   en bout des câbles SMA, retard des deux câbles U.FL compensé
   (extension de port mesurée U.FL en l'air), port 1 sur l'entrée 1,
   port 2 sur l'entrée 2 ; balayage aller (S11, S21), câbles permutés
   pour S22 et S12 (`_aller.s2p`, `_retour.s2p`).
   `differential_z_from_s` en déduit Z11 + Z22 - Z12 - Z21.
3. **Un seul port, demi-circuit** : entrée 1 avec l'entrée 2 en l'air,
   puis entrée 1 avec l'entrée 2 à la masse (court-circuit soudé à la
   pastille de son U.FL), puis entrée 2 avec l'entrée 1 en l'air
   (`_ouvert1.s1p`, `_masse2.s1p`, `_ouvert2.s1p`).
   `differential_z_from_one_port` en déduit l'impédance différentielle,
   exacte pour un réseau réciproque. **Attention** : la lecture « entrée
   2 à la masse » seule n'est pas la moitié de l'impédance
   différentielle : les condensateurs à la masse du demi-réseau mis à la
   masse sont dans le chemin, et l'écart dépasse le tiers de la valeur
   (test `test_nanovna_methods_recover_the_differential_impedance`).

Critère d'accord : à la porteuse, impédance différentielle proche de
`mockup.matching.z_target_ohm`, meilleure adaptation à la porteuse
(`match_frequency_hz`) ; Q mesuré par `resonance_q` sur |S21| du réseau
vers la sonde de champ proche posée au poste de l'étiquette, comparé au
Q que le modèle donne pour cette source (`nfc.vna_q`), et non à
`mockup.matching.q_loaded` : la source de 50 Ω du NanoVNA, adaptée au
réseau, en double la résistance et en divise le Q par deux environ,
alors que `q_loaded` est le Q sous la résistance d'émission du lecteur.
Retouche par les empreintes non montées en parallèle de C1 et C2 et
l'assortiment de C0G ; valeurs retouchées notées au journal. Puis
remonter les 0 Ω, émettre à conductance réduite et lire le courant TVDD
(mise en route, étapes 6 et 7). La variante P au plus fort accord de
`mockup.tags.trims_pF` se lit aussi sur une case réaccordée avec elle
(point 8 du paragraphe 2 de la note 25), réaccord noté au journal.

**À pleine conductance**, une fois le courant TVDD sous
`mockup.reader.i_tvdd_accept_ma` : courant TVDD relevé émission coupée
puis en émission ; `r_drive_from_tvdd` en déduit la résistance
d'émission par broche à partir de ce courant, de l'impédance
différentielle mesurée à la porteuse et de la tension TVDD
(`mockup.power.regulator.v_out`), par le modèle de source de `nfc` :
c'est la mesure de `mockup.reader.r_drive_ohm`, reportée au yaml.
Diviseur de réception : lecteur de nouveau isolé, S21 de l'entrée du
réseau vers le point de test RX, puis vers le nœud C0, par la même sonde
résistive (résistance série grande devant `mockup.reader.rx_r2_ohm`
devant le port 2, pour ne pas charger le nœud RX) ; `rx_amplitude_vpp`
applique le rapport des deux à la tension du nœud C0 du modèle
(`nfc.matching`), mise à l'échelle par le courant TVDD mesuré. Critère :
amplitude à RX dans `mockup.reader.rx_target_vpp` au régime pour
lequel le diviseur est calculé (décision D15 de la note 25 : pleine
conductance ou champ de service), et sous `mockup.reader.rx_max_vpp` à
pleine conductance ; sinon R1 est retouchée.

**Vignette de champ.** Collée sous la carte, centrée sous la boucle de
la case mesurée, à la distance du cuivre où se tient l'étiquette
au-dessus (z RFID moins `gap.pcb_mm` sous la face inférieure) : le champ
d'une boucle plane loin du métal est symétrique par rapport à son plan,
et la vignette lit ainsi le champ au poste de l'étiquette sans gêner la
pièce. Aux décalages, elle reste sous le centre de la boucle : son champ
est alors celui du centre, proportionnel au courant de boucle, ce qui
suffit aux marges, qui sont des rapports. Sa table d'étalonnage
(`m13_vignette.csv`, tension `PICKUP` contre champ en A/m au poste de
l'étiquette) s'établit une fois : au NanoVNA en petits signaux, la sonde
de champ proche puis la bobine de la vignette (diode non montée, sur un
câble U.FL) au poste de l'étiquette, le réseau attaqué par son entrée :
le rapport des deux transmissions S21 donne la constante de la vignette
en volts par A/m, à comparer à sa géométrie ; puis la loi du détecteur
(tension `PICKUP` contre tension crête induite), diode montée, sur
table, avec une source à la porteuse d'amplitude connue (générateur, ou
NanoVNA en onde continue pour le bas de la courbe). `field_from_pickup`
interpole la table et refuse d'extrapoler ; une série dont la vignette
sort de la table est refusée par l'analyse : étendre la table d'abord.
Sans table, la vignette reste un indicateur relatif : la marge de M13a
se prend alors par la méthode de l'entrefer.

### Planéité de la plaque (avant M12)

Plaque posée sur ses pieds sur une vitre ; hauteur de sa face supérieure
au-dessus de la vitre en neuf points (comparateur, à défaut jauge de
profondeur sous une règle posée en pont) : les quatre centres de case,
les quatre milieux entre cases voisines et le centre de la zone de jeu,
x et y depuis ce centre, `m12_planeite.csv`. Analyse : `flatness` (crête
à crête brut et après retrait du plan moyen). Critère : crête à crête
après retrait du plan inférieur à `layout.tilt_budget_mm` ; sinon la
plaque est réimprimée ou calée. Dans tous les cas, z est relevé à chaque
mesure et jamais supposé.

### M12. Chaîne Hall

#### M12a. B(z) et facteur d'échelle du modèle (Q1)

**Question** : le modèle de champ du disque (`hall.disc_bz_mT`) est-il
juste ?

**Matériel** : un pion et un roi (aimant inséré), un aimant nu de chaque
diamètre, escalier de soulèvement, cales.

**Préparation** : capteur central de `mockup.hall.cluster_square`
(rangée 1), chemin direct ; zéro relevé case vide ; pièce centrée (x = y
= 0) ; aimant nu centré sur les cales.

**Acquisition** : pour chaque pièce, l'escalier de 0 à
`mockup.prints.lift_max_mm` par pas de `lift_step_mm`, chaque z relevé
au pied à coulisse ; pour chaque aimant nu, les cales seules et
combinées sur la même plage ; `criteria.hall_samples` lectures par
point. Lignes `m12a` de `m12_hall.csv`.

**Analyse** : `m12a_fit_rows` (un facteur par aimant, moyenne des
rapports de la mesure convertie en mT au champ de `hall.disc_bz_mT` aux
cotes mesurées de l'aimant et à `piece_magnet.br_T`, sur les marches
jusqu'à `layout.lift_detect_mm` : chaque point pèse le même poids
relatif, comme dans le critère). Le facteur porte la sensibilité réelle
du capteur et la rémanence réelle de la ferrite : des aimants de même
nuance doivent donner des facteurs voisins, un écart signale une erreur
de z ou d'aimantation.

**Critère** : un seul facteur par aimant ; écart résiduel au modèle
inférieur à `criteria.residual_max_pct` sur toute la fenêtre (de z au
repos à ce z plus `layout.lift_detect_mm`) ; facteur dans
`criteria.scale_factor_range`. La rémanence mesurée de la nuance achetée
entre au yaml (`piece_magnet`, décision D13).

#### M12b. Rayon de détection et couverture (Q2, décision D14)

**Question** : jusqu'où une pièce décentrée reste-t-elle vue, par un
capteur seul et par l'amas de cinq capteurs ?

**Matériel** : le pion (le plus petit aimant), la cale de l'entrefer
maximal, le gabarit de décalage.

**Préparation** : pion à l'entrefer maximal, sur le gabarit centré sur
la case `mockup.hall.cluster_square` ; zéros relevés case vide. Seuil :
`presence.threshold_fraction` fois le champ mesuré du pion centré dans
cette position (le seuil que poserait le micrologiciel) ; le seuil du
modèle (`MockupCriteria.model_threshold_mT`) sert de comparaison.

**Acquisition** : capteur seul (centre, chemin direct) : rayons +x, +y
et diagonale du gabarit de 0 à `mockup.prints.offset_max_mm` par pas de
`offset_step_mm`, puis gabarit tourné d'un demi-tour pour -x et -y.
Amas : les cinq capteurs lus à chaque position de la grille d'un
quadrant (x et y de 0 à `offset_max_mm`), puis gabarit tourné d'un quart
de tour pour au moins les axes et la diagonale des trois autres
quadrants. `criteria.hall_samples` lectures par point. Lignes `m12b` de
`m12_hall.csv`.

**Analyse** : `m12b_detection_radius` (rayon par direction, interpolé
entre les deux positions qui encadrent le seuil, `directions` réduites
aux axes et aux diagonales) ; `m12b_cluster_coverage` (demi-côté du plus
grand carré de décalages centré sur la case où au moins un capteur de
l'ensemble lit la pièce au-dessus du seuil), pour le capteur seul puis
pour l'amas. Modèle : `hall.offset_coverage`.

**Critère** : rayon de détection du capteur seul mesuré à
`criteria.radius_resolution_mm` près ; couverture de l'amas mesurée ;
les deux comparées au modèle et au décalage admissible
`layout.admissible_offset_mm`. Décision D14 : un capteur par case si le
capteur seul couvre le décalage admissible ; sinon l'amas, ou une pièce
mieux centrée (décalage admissible révisé) ; la nappe Hall 4 x 4 de la
note 24 attend cette décision.

#### M12c. Pièces voisines et soulèvement (Q3)

**Question** : les pièces voisines et une pièce soulevée trompent-elles
la présence ?

**Matériel** : un roi, l'escalier de soulèvement.

**Préparation** : capteur central de `mockup.hall.cluster_square`,
entrefer nominal, aucune autre pièce sur la carte.

**Acquisition** : le roi seul sur une case latérale (B1, x = p), sur
l'autre case latérale (A2, y = p), puis sur la case diagonale (B2) ;
chaque point alterné avec une lecture sans lui (`piece` à `none`), au
moins `criteria.hall_samples` lectures par point, pour prendre le champ
du voisin par différence sans dérive. Soulèvement : roi sur sa case,
marche `layout.lift_detect_mm` de l'escalier (reprise de M12a). Lignes
`m12c` de `m12_hall.csv`.

**Analyse** : `mean_shift` (champ du voisin et son incertitude, avec et
sans lui) ; `m12c_presence` recalcule seuil, relâchement, marge de
soulèvement et diaphonie des voisins par superposition (les cases
latérales, puis diagonales, jusqu'à `layout.neighbors_worst_case`) à
partir des champs mesurés, le plus faible étant le pion centré de M12b.

**Critère** : champ d'un voisin conforme au modèle (`hall.piece_bz_mT` à
ρ = p et p√2, entrefer nominal) à `criteria.neighbor_field_tol_mT`
près ; diaphonie inférieure à `measurement.crosstalk_max_db` ; marge de
soulèvement au moins `presence.min_lift_margin`. Ces valeurs mesurées
remplacent les fractions du yaml pour fixer les seuils réels (note 24,
section 7, point 5).

#### M12d. Chaîne de lecture (Q4)

**Question** : alimentation par rangées et multiplexeur : quand une
lecture est-elle valable, et le chemin multiplexé vaut-il le direct ?

**Matériel** : multimètre en ampèremètre.

**Préparation** : cases vides, puis un aimant fixe sur un capteur
central pour les essais de chemin.

**Acquisition** :

- `power_on` : délai entre `ROW_EN` et la lecture, de 0 à
  `criteria.power_on_sweep_factor` fois `power_on_max_us` du capteur
  monté, rangée coupée assez longtemps entre deux points pour que le
  filtre se vide ;
- `mux_settle` : alternance de la voie de masse
  (`mockup.mux_channels.ground`) et de la voie de référence
  (`rail_half`), puis de la masse vers un capteur centré sous aimant, à
  délai variable après la commutation ;
- `path` : même capteur par son entrée directe et par sa voie de mux, le
  mux posé depuis au moins `criteria.path_settle_us` ;
- `current` : courant d'une rangée, FET bloqué et ampèremètre entre les
  pastilles du cavalier de dérivation ;
- `noise` : lectures répétées de la voie de masse.

Lignes de `m12d_chaine.csv` (une par délai, chemin ou voie).

**Analyse** : `settling_time_us` (premier délai après lequel la lecture
reste à `mockup.hall.settle_lsb` pas de sa valeur finale) pour la mise
sous tension et pour la commutation ; `mean_shift` entre chemins ;
`pooled_std` pour le bruit.

**Critère** : `power_on_us` et `i_supply_ma` mesurés pour le capteur
monté ; temps d'établissement après commutation mesuré, il remplace
`hall_rfid.mux.t_settle_us` ; écart entre chemin direct et chemin
multiplexé inférieur à `criteria.path_offset_max_lsb` pas de l'ADC ;
bruit de la voie de masse mesuré, il remplace `esp32.adc_noise_lsb_rms`.
`hall_rfid.mux.ron_ohm` reste « to verify » : sans courant continu dans
l'entrée de l'ADC, la résistance du mux ne se voit pas.

### M13. Chaîne RFID

#### M13a. Seuil d'activation et marge (Q5, Q7)

**Question** : une étiquette à la taille du pion se lit-elle, avec
quelle marge, selon la boucle, le lecteur et la variante d'étiquette ?

**Matériel** : étiquettes de chaque variante dans leurs pièces, cale de
l'entrefer maximal, cales et escalier, gabarit de décalage, vignette
étalonnée.

**Préparation** : accord fait ; conductance de service établie par case
(conventions) ; vignette sous la boucle de la case ; voisins `held`.

**Acquisition**, pour chaque case et chaque variante :

1. à la conductance de service, entrefer maximal : une série à chaque
   décalage du gabarit sur +x et +y jusqu'à
   `layout.admissible_offset_mm`, et sur la diagonale jusqu'au coin
   (`layout.admissible_offset_mm`, `layout.admissible_offset_mm`), le
   décalage admissible valant sur chaque axe ;
2. méthode du champ : au centre et au décalage le plus défavorable,
   conductance descendue pas à pas depuis celle de service jusqu'aux
   échecs ; à chaque pas, vignette, courant TVDD et une série ;
3. méthode de l'entrefer : à la conductance de service, au centre,
   étiquette montée par les cales et l'escalier jusqu'aux échecs ;
4. pour la configuration retenue (boucle, lecteur, variante), une série
   de confirmation à l'entrefer maximal et au décalage le plus
   défavorable.

Une ligne `m13a` de `m13_rfid.csv` par série.

**Analyse** : `m13a_thresholds` (`m13a_activation_threshold` par
groupe : niveau le plus faible dont la série passe, et celles de tous
les niveaux plus forts aussi ; champ en A/m par `field_from_pickup`).
Marge en champ : champ de service sur seuil d'activation. Méthode de
l'entrefer : plus grand entrefer z* dont la série passe,
`m13a_activation_threshold` avec `higher_is_easier=False`, puis
`field_margin_from_gap` (rapport des champs de la boucle à l'entrefer
maximal et à z*, à courant égal, par le modèle de boucle de
`chessboard_calc.nfc`) ; les deux méthodes se recoupent. `read_summary`
donne les taux et leurs bornes.

**Critère** (Q5) : séries passées à l'entrefer maximal, sur les
décalages jusqu'à `layout.admissible_offset_mm` ; marge en champ à
l'entrefer maximal (champ de service sur champ d'activation) d'au moins
`mockup.tags.activation_margin_min`, le champ de service restant sous
`hall_rfid.nfc.h_max_a_per_m` ; série de confirmation passée pour la
configuration retenue. (Q7) : boucle L60x3 contre L70x2 et lecteur NXP
contre clone comparés sur la même étiquette (seuil, marge, courant TVDD
au service) ; choix argumenté pour le plateau, avec la place qu'il faut
au lecteur entre deux boucles (paragraphe 4.2 de la note 25).

#### M13b. Sélectivité et états des voisins (Q6, Q7)

**Question** : lit-on la pièce de la case voisine, et dans quel état les
lecteurs inactifs tiennent-ils leurs sorties ?

**Matériel** : multimètre, résistance de tirage de
`criteria.tx_pullup_ohm`, l'étiquette au seuil d'activation le plus bas
en M13a (le pire cas).

**Préparation** : un lecteur actif à sa conductance de service, les
autres dans l'état essayé.

**Acquisition** :

1. broches TX, sur les deux puces (rangées 1 et 2) et pour chaque état
   (`held`, `txoff`, `softpd`, `hardpd`, et `hiz` si la console
   l'expose) : tension continue sur les points de test TX1 et TX2, puis
   la même avec la résistance de tirage vers le rail 3,3 V
   (`mockup.power.regulator.v_out`) : une broche tenue à 0 reste à
   quelques dizaines de millivolts, une broche flottante monte vers le
   rail ; `VersionReg` noté. `m13b_etats_tx.csv` ;
2. lectures voisines : étiquette sur une case latérale de même boucle
   (A1 active, étiquette sur A2), sur une case latérale d'autre boucle
   (sur B1) et sur la case diagonale (B2), centrée et à l'entrefer
   nominal ; une série de confirmation par position et par état des
   voisins ; puis l'étiquette sur la case active, pour vérifier que
   l'état des voisins ne change pas sa lecture. Vignette déplacée sous
   la boucle voisine pour le champ relayé, comparé au calcul de relais
   du lot 2. Lignes `m13b` de `m13_rfid.csv`.

**Analyse** : `read_summary` par position et par état (borne haute de la
lecture parasite, `read_high`).

**Critère** (Q6) : aucune lecture voisine au champ de service, voisins
`held` ; dans cet état, TX1 et TX2 tenus à 0 sur les deux puces. Les
autres états sont informatifs : ils chiffrent ce que la règle d'émission
évite.

#### M13c. Émulation du multiplexeur (Q8)

**Question** : l'objection de l'ADR 0001 à la commutation des antennes
(capacité et résistance d'un multiplexeur dans la boucle) tient-elle ?

**Matériel** : deux résistances de `criteria.mux_emulation_rq_ohm`, un
condensateur de `criteria.mux_emulation_c_pF`.

**Préparation** : sur une case à boucle L70x2 (celle du modèle),
`criteria.mux_emulation_rq_ohm` à chacune des deux places de Rq (le
double dans la boucle) et `criteria.mux_emulation_c_pF` dans l'empreinte
en parallèle de la boucle. Ce montage désaccorde tout le réseau :
l'émetteur tirerait bien plus que `mockup.reader.i_tvdd_max_ma` à pleine
conductance.

**Acquisition** : balayage du réseau modifié au NanoVNA (méthode de
l'accord), puis émission depuis la conductance minimale, montée pas à
pas tant que le courant TVDD reste sous
`criteria.mux_emulation_i_tvdd_max_ma` ; à chaque pas, courant TVDD,
vignette et une série, étiquette P0 centrée à l'entrefer nominal. Lignes
`m13c` de `m13_rfid.csv` (`loop` à `L70x2_mux`). Réseau d'origine remis
et accord revérifié ensuite.

**Analyse** : champ au poste de l'étiquette par `field_from_pickup`,
comparé au seuil d'activation en champ de la même étiquette en M13a et
au calcul du lot 2 pour ce réseau ; `read_summary`.

**Critère** : champ à la vignette et taux de lecture conformes au calcul
du lot 2 pour ce réseau. L'objection tient si ce champ reste sous le
seuil d'activation mesuré en M13a. Mesuré à conductance réduite, ce
champ borne par dessous celui de pleine conductance : s'il dépasse déjà
le seuil, l'objection tombe ; s'il reste dessous, conclure sur la valeur
de pleine conductance du calcul, recalée sur ces points.

#### M13d. Temps de lecture (Q10)

**Question** : combien de temps coûte une identification ?

**Préparation** : configuration retenue en M13a, étiquette centrée à
l'entrefer nominal.

**Acquisition** : le micrologiciel chronomètre la séquence ISO 14443A
complète (REQA, anticollision sur deux niveaux, SELECT, CRC_A) par case,
une série (lignes `m13d`, `t_read_ms_mean` et `t_read_ms_max`) ; puis un
coup entier, du changement vu par la couche Hall (anti-rebond
`presence.debounce_scans` compris) à l'UID disponible, pièce posée à la
main `criteria.read_trials` fois (lignes `m13d_move`).

**Critère** : sur le maximum relevé, moins de
`criteria.read_time_max_ms` par case (l'estimation de la note 24) et
moins de `criteria.move_time_max_ms` par coup.

### M14. Cohabitation et environnement

#### M14a. Hall pendant l'émission, aimant dans la base (Q9)

**Question** : l'ADR 0001 tient « un aimant permanent dans la même
base » pour rédhibitoire : l'émission gêne-t-elle la couche Hall, et
l'aimant gêne-t-il l'étiquette ?

**Matériel** : les pièces de test (aimant amovible par le trou
d'éjection), NanoVNA et sonde de champ proche.

**Acquisition** :

1. Hall pendant l'émission : chacun des capteurs, case vide puis pièce
   posée ; `criteria.hall_samples` lectures émission coupée, puis avec
   le lecteur de sa case à la conductance de service, à pleine
   conductance, puis avec un lecteur voisin ; émission coupée et
   émission alternées pour écarter la dérive. Lignes `m14a_hall` de
   `m14_cohabitation.csv` (`rf_square` à `none` émission coupée) ;
2. même pièce avec et sans son aimant : résonance de l'étiquette, pièce
   posée sur la sonde de champ proche, S11 au NanoVNA (`f_tag_mhz`) ;
   seuil d'activation par la méthode du champ de M13a ; une série de
   confirmation au champ de service, à l'entrefer maximal. Lignes
   `m14a_tag` (`magnet_in` à 1 puis 0).

**Analyse** : `mean_shift` des comptes contre émission coupée ; dérive
relative de `f_tag_mhz` ; `read_summary` et `m13a_activation_threshold`
avec et sans aimant.

**Critère** : aucun décalage des comptes Hall pendant l'émission
supérieur au bruit de l'ADC (`esp32.adc_noise_lsb_rms`, ou la valeur
mesurée en M12d) ; dérive d'accord de l'étiquette inférieure à
`criteria.tag_drift_max_pct` ; taux de lecture inchangé (série de
confirmation passée avec et sans aimant), seuils d'activation égaux à un
pas de conductance près.

#### M14b. Métal et chariot sous la carte (Q11)

**Question** : à quelle distance sous la carte la mécanique du plateau
(plaques, chariot et son aimant) devient-elle sans effet ?

**Matériel** : plaques d'aluminium et d'acier, l'aimant du chariot
(`carriage.magnet`), cales nylon.

**Préparation** : le perturbateur sous la carte, à chacune des distances
`criteria.disturber_distances_mm` de sa face inférieure, centré sous la
case mesurée (l'aimant du chariot dans l'orientation où il attire une
pièce). Le décalage d'accord se mesure sur une case au lecteur isolé
(méthode de l'accord, seconde carte assemblée), les lectures et la
couche Hall sur la première.

**Acquisition**, pour chaque perturbateur et chaque distance, puis sans
perturbateur (`disturber` à `none`) :

- fréquence de meilleure adaptation du réseau (`f_net_mhz`,
  `m14b_<perturbateur>_<distance>.s2p`) ;
- courant TVDD à la conductance de service, vignette (informative : la
  plaque est plus près d'elle que de l'étiquette) et une série,
  étiquette P0 centrée à l'entrefer maximal ;
- capteurs Hall de la case et de ses voisines, case vide puis pion à
  l'entrefer maximal, `criteria.hall_samples` lectures.

Lignes `m14b` de `m14_cohabitation.csv`.

**Analyse** : désaccord relatif contre la mesure sans perturbateur ;
`read_summary` ; champ Hall par `counts_to_mT` comparé au seuil et au
relâchement de M12c ; `min_safe_distance` par perturbateur, une distance
passant si tous les critères y tiennent.

**Critère** : par perturbateur, distance minimale à partir de laquelle
le désaccord reste sous la demi-bande passante
(`MockupCriteria.max_detune_rel`, la moitié de 1 sur
`mockup.matching.q_loaded`), la série de lectures passée, le courant
TVDD sous `mockup.reader.i_tvdd_accept_ma`, et les états Hall inchangés
(cases vides sous le relâchement, pion au-dessus du seuil). La plus
grande de ces distances est la distance minimale entre la carte et la
mécanique du plateau, versée à la note 24.

## Tableau de synthèse à remplir

| Mesure | Critère | Résultat | Verdict |
|---|---|---|---|
| M1 | Q >= 40 | | |
| M2 | Q >= 30, chute <= 20 % | | |
| M3 | informatif | | |
| M4 | SNR >= 20 dB | | |
| M4bis | SNR >= 10 dB a 8 mm | | |
| M5 | <= -20 dB | | |
| M5bis | < 3 kHz | | |
| M6 | <= +-3 % | | |
| M7 | distance pour < 2 kHz | | |
| M8 | delta <= 6 dB | | |
| M9 | sigma fb < 200 Hz | | |
| M10 | df < 500 Hz, dQ < 10 % | | |
| M11 | dsigma < 100 Hz, < 1 dB | | |
| M12a (Q1) | un facteur par aimant dans `criteria.scale_factor_range`, résidu < `criteria.residual_max_pct` jusqu'à `layout.lift_detect_mm` | | |
| M12b (Q2) | rayon du capteur seul à `criteria.radius_resolution_mm` près ; couverture de l'amas contre `layout.admissible_offset_mm` (D14) | | |
| M12c (Q3) | voisin à `criteria.neighbor_field_tol_mT` du modèle ; diaphonie <= `measurement.crosstalk_max_db` ; marge de soulèvement >= `presence.min_lift_margin` | | |
| M12d (Q4) | `power_on_us`, `i_supply_ma`, établissement et bruit mesurés ; direct contre mux < `criteria.path_offset_max_lsb` | | |
| M13a (Q5) | séries passées à l'entrefer max jusqu'au décalage admissible ; marge >= `mockup.tags.activation_margin_min` sous `hall_rfid.nfc.h_max_a_per_m` | | |
| M13b (Q6) | aucune lecture voisine au champ de service ; TX tenus à 0 sur les deux puces | | |
| M13a, M13b (Q7) | choix argumenté de la boucle et du lecteur | | |
| M13c (Q8) | TVDD < `criteria.mux_emulation_i_tvdd_max_ma` ; champ et taux conformes au calcul ; objection tenue si champ < seuil de M13a | | |
| M14a (Q9) | décalage Hall <= `esp32.adc_noise_lsb_rms` ; dérive d'accord < `criteria.tag_drift_max_pct` ; taux inchangé | | |
| M13d (Q10) | < `criteria.read_time_max_ms` par case, < `criteria.move_time_max_ms` par coup | | |
| M14b (Q11) | distance minimale parmi `criteria.disturber_distances_mm` : désaccord < demi-bande, série passée, états Hall inchangés | | |
