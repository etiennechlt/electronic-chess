# 25. Maquette Hall + RFID : le plan pour tout commander chez JLCPCB

Rédigée le 11/10/2026, mise à jour le 12/10/2026. Statut : **plan
validé** le 12/10/2026, les quatorze décisions du paragraphe 11 prises
selon leur recommandation ; **lot 2 fait** (le modèle, paragraphe 9).
Rien n'est encore généré ni commandé. Chaque lot de code suivant attend
l'accord sur ses interfaces avant d'être écrit (CLAUDE.md).

Ce plan prolonge la [note 24](24-hall-et-rfid.md), qui jugeait
l'architecture « Hall + RFID » d'un brief extérieur « non pour
l'identité, oui pour la présence » comme alternative au LC, et
« oui, et c'est même la bonne » comme étape intermédiaire. Il en fait
un banc de mesure : une maquette de quatre cases qui vérifie, sur du
cuivre, ce que la note 24 a calculé, et qui se commande chez JLCPCB
(cartes, assemblage, impressions, composants libres de LCSC dans le
même colis). Ce qui s'achète ailleurs est listé au paragraphe 8.3.

**La maquette n'engage pas le plateau.** Elle ne tranche pas pour la
RFID : l'[ADR 0001](../adr/0001-lc-resonators-for-piece-identification.md)
reste en vigueur, et la recommandation « RFID sur le plateau : non en
phase 1 » de la note 24 (section 7, point 4), qu'aucune ADR n'a encore
tranchée, aussi. Elle produit les mesures qui permettront de trancher.

## Provenance des chiffres

Quatre sortes de nombres coexistent ici, et chacun dit d'où il vient :

1. **Calculés par le dépôt** : `chessboard_calc` depuis
   `config/board.yaml` (sections `gap`, `pieces`, `piece_magnet`,
   `resonator`, `plateau`, `measurement`, `hall_rfid`, dont la
   sous-section `mockup` de cette maquette). Ils sont donnés sans
   marque, avec la fonction qui les calcule.
2. **Préliminaires** : calculés hors dépôt le 11/10/2026 pour
   dimensionner ce plan (modèles par filaments, réseau d'adaptation,
   bobine d'étiquette, couverture hors centre, relais par les boucles
   voisines, effet du métal), recalculés par la relecture, puis portés
   dans le yaml et dans `chessboard_calc` au lot 2, qui les épingle par
   des tests. Les valeurs de cette note sont depuis le 12/10/2026 celles
   du dépôt ; là où elles s'écartent du calcul préliminaire au point de
   changer une conclusion, l'écart est dit. La marque *(prél.)* ne
   reste que sur ce qu'un lot suivant fixe.
3. **Prix et stocks** : relevés par recherche web le 11/10/2026, les
   sites de LCSC et de JLCPCB n'étant pas joignables depuis
   l'environnement de travail. Tous sont « estimated » au sens de
   `docs/prix-plateau.csv`, à revalider au lot 3, puis au panier
   (lot 10). Conversion 0,92 EUR par USD, TVA 20 %.
4. **Choix de conception et valeurs de fiche technique** : géométries
   proposées (boucles, amas de capteurs, garde de masse, étiquettes),
   valeurs de composants, caractéristiques lues dans les fiches du
   paragraphe 13, critères de réussite des mesures. Le lot 2 les a
   portés dans le yaml (`hall_rfid.mockup`) et dans
   `measurements/protocol.md`.

## 0. En bref

| | |
|---|---|
| Ce qui part chez JLCPCB | une carte principale de 2 x 2 cases (100 x 145 mm utiles, 110 x 145 avec les rails, 2 couches, assemblée), une planche d'étiquettes NFC assemblée, six pièces de test, une plaque de surface, des cales et des gabarits imprimés (JLC3DP), quelques composants libres de LCSC dans le même colis |
| Ce qui n'y part pas | les aimants ferrite, un NanoVNA et sa sonde, des cartes NTAG213 de référence, la visserie nylon, les consommables de soudure, un adaptateur USB série 3,3 V (paragraphe 8.3) |
| Ce que la maquette mesure | B(z) et B(ρ) des aimants de pièce, la tolérance au décentrage, la diaphonie, le soulèvement, la commutation des capteurs, la liaison NFC avec une étiquette à la taille du pion, la sélectivité entre cases voisines, l'effet du métal et du chariot sous la carte, et les deux objections de l'ADR 0001 à la RFID, le multiplexeur et l'aimant dans la base |
| Coût estimé | 240 à 380 USD chez JLCPCB et LCSC, soit 265 à 420 EUR TTC, plus les frais de dédouanement du transporteur (paragraphe 8.4) ; 50 à 95 EUR d'achats ailleurs, 110 à 185 avec le NanoVNA |
| Délais | 15,5 à 17,5 jours d'effort en tout, dont 11 à 12 sur le chemin critique avant la commande si une autre session mène les lots 7 et 8 (le micrologiciel peut se finir pendant la fabrication) ; le lot 5 peut doubler. Puis la précommande des puces d'étiquette (lancée au lot 3), 2 à 3 semaines de fabrication et de transport, et 6 à 10 jours de mise en route et de mesures (paragraphe 10) |
| Décidé | quatorze points, tous selon leur recommandation, le 12/10/2026 ; deux nouveaux ouverts par le lot 2, D15 et D16 (paragraphe 11) |

## 1. Ce que la maquette doit trancher

| # | Question | Mesure | Critère de réussite |
|---|---|---|---|
| Q1 | Le modèle de champ du disque (`hall.disc_bz_mT`) est-il juste ? | M12a : B(z) au capteur central, pion et roi, sur l'escalier de soulèvement de 0 à 20 mm (z de 6,9 à 26,9 mm entre la face de l'aimant et la plaque de Hall), chaque hauteur relevée au pied à coulisse | un seul facteur d'échelle ajusté par aimant (il porte la sensibilité réelle du capteur et la rémanence réelle de la ferrite) ; écart résiduel au modèle inférieur à 5 % de z = 6,9 à 21,9 mm ; facteur compris entre 0,85 et 1,15 |
| Q2 | Jusqu'où une pièce décentrée reste-t-elle vue ? | M12b : B(ρ) sur le gabarit de décalage, capteur seul puis amas de cinq capteurs | rayon de détection du capteur seul mesuré à 0,5 mm près (modèle : 6,6 mm, `hall.offset_coverage`) ; couverture de l'amas mesurée (modèle : carré de ±9,3 mm) ; décision sur le nombre de capteurs par case contre le décalage admissible d'une pièce posée à la main (décision D14) |
| Q3 | Les pièces voisines et le soulèvement | M12c : un roi seul, successivement sur une case latérale puis sur la case diagonale, champ pris par différence avec et sans lui, au moins 256 lectures par point ; escalier de soulèvement | champ d'un voisin conforme au modèle à 0,05 mT près (-0,22 mT latéral, -0,08 mT diagonal) ; diaphonie des huit voisins recalculée par superposition avec ces valeurs, inférieure à -20 dB (`measurement.crosstalk_max_db`) ; marge de soulèvement au moins 1,5 (`hall_rfid.presence.min_lift_margin`) |
| Q4 | Alimentation par rangées et multiplexeur | M12d : délai entre `ROW_EN` et la lecture ; alternance des voies 8 (masse) et 9 (référence) à délai variable ; voie directe contre voie multiplexée, le mux posé depuis au moins 50 µs ; courant d'une rangée, FET bloqué et ampèremètre entre les pastilles du cavalier de dérivation ; bruit sur la voie 8 | `power_on_us` et `i_supply_ma` mesurés pour le capteur monté ; temps d'établissement après commutation mesuré ; écart entre les deux chemins inférieur à 1 pas de l'ADC ; `esp32.adc_noise_lsb_rms` mesuré. `mux.ron_ohm` reste « to verify » : sans courant continu dans l'entrée de l'ADC, la résistance du mux ne se voit pas |
| Q5 | Une étiquette à la taille du pion se lit-elle ? | M13a : taux de lecture selon l'entrefer, le décentrage, la variante d'étiquette et la conductance d'émission | 100 lectures sur 100 à l'entrefer maximal, sur les décalages de M12b jusqu'au décalage admissible, avec une marge en champ d'au moins 2 : rapport entre le champ de service (7,5 A/m au plus, le maximum ISO) et le plus faible champ qui donne encore 100 lectures sur 100. 100 sur 100 borne l'échec à 3 %, 300 sur 300 à 1 %. Le modèle (`nfc.tag_activation`, à p = 50, entrefer maximal, sur L60x3 et L70x2) donne 1,37 et 1,27 pour P nue, 2,09 et 2,23 pour P + 15 pF, 2,35 et 3,15 pour P + 22 pF, 2,01 et 2,50 pour G nue ; à p = 40, aucune variante n'atteint 2 sur L60x3 |
| Q6 | Lit-on la pièce de la case voisine ? | M13b : étiquette sur la case voisine, lecteurs inactifs dans chacun de leurs états | aucune lecture voisine au champ de service défini en Q5 |
| Q7 | Boucle L60x3 contre L70x2, lecteur NXP contre clone | M13a et M13b sur les quatre cases | choix argumenté pour le plateau, y compris la place qu'il faut au lecteur entre deux boucles (paragraphe 4.2) |
| Q8 | « La commutation de 64 antennes est ingérable (capacité parasite des multiplexeurs à cette fréquence) » (ADR 0001) | M13c : sur une boucle L70x2, celle du modèle, 51 Ω à chacune des deux places de Rq (100 Ω dans la boucle) et 120 pF en parallèle, émetteur à conductance réduite | champ à la vignette et taux de lecture conformes au calcul du lot 2 pour ce réseau (0,87 A/m à pleine conductance, 0,37 A/m courant TVDD tenu sous la limite de M13c, `nfc.mux_emulation`) ; l'objection tient si ce champ reste sous le seuil d'activation mesuré en M13a, le Q de 0,29 du modèle ne prédisant pas à lui seul l'absence de lecture |
| Q9 | Cohabitation : l'ADR 0001 tient « un aimant permanent dans la même base » pour rédhibitoire | M14a : Hall pendant l'émission ; même pièce avec et sans aimant ferrite | aucun décalage des comptes Hall pendant l'émission supérieur au bruit de l'ADC (3 pas efficaces, `esp32.adc_noise_lsb_rms`) ; dérive d'accord de l'étiquette inférieure à 1 % ; taux de lecture inchangé |
| Q10 | Temps de lecture | M13d : chronométrage de la séquence ISO 14443A complète | moins de 10 ms par case (note 24 : 5 à 10 ms), moins de 20 ms par coup |
| Q11 | Le métal et le chariot sous le plateau | M14b : plaque d'aluminium puis d'acier, puis l'aimant N42 du chariot (`carriage.magnet`), à 5, 10, 20 et 30 mm sous la carte | décalage d'accord et taux de lecture de la case au-dessus ; état des capteurs Hall voisins ; distance minimale entre la carte et la mécanique du plateau, versée à la note 24 |

M12 reprend la mesure que la note 24 proposait (M12a à M12c) et y
ajoute la chaîne de lecture (M12d) ; M13 et M14 sont nouvelles. Les
trois entrent au lot 2 dans `measurements/protocol.md`, dans une
section « Maquette Hall + RFID » avec son propre matériel, leurs lignes
au tableau de synthèse et leurs gabarits CSV dans
`measurements/data/templates/` (paragraphe 9).

**Environnement de mesure.** Toute mesure RF se fait carte posée sur
des entretoises nylon de 30 mm, loin de tout métal. Une plaque
conductrice sous la carte (`nfc.metal_detune`, distances comptées depuis
sa face inférieure) : posée sur une table métallique, la carte perd la
moitié de l'inductance de ses boucles et son accord monte de 40 à 43 % ;
à 10 mm, de 3,2 à 3,8 % ; à 20 mm, de 0,8 à 1,1 % ; à 30 mm, de 0,3 à
0,4 %, pour une demi-bande de 2,1 % au Q chargé de 24. Les 30 mm des
entretoises suffisent, 10 mm non.

## 2. Ce que la préparation a corrigé dans la note 24

La préparation et la relecture de ce plan ont relevé onze points de la
note 24, de son yaml ou de son code qui ne tiennent pas, ou pas tels
quels. Ils sont la raison de plusieurs choix des paragraphes suivants,
et le lot 2 les a corrigés dans le dépôt et dans la note 24, qui porte
un erratum (décision D11).

1. **L'étiquette de 25 mm ne tient dans aucune base.** Le pion a une
   base de 17,5 mm et le roi de 22,5 mm à p = 50. L'étiquette se
   dérive donc de la base : base moins deux parois et deux jeux, soit
   14,5 mm pour la plus petite (étiquette P) et 19,5 mm pour les bases
   de 22,5 mm (étiquette G) à p = 50 ; 11 et 15 mm à p = 40.
2. **La marge de « 3,2 fois le minimum ISO » ne dépend pas de
   l'étiquette.** `nfc.link().h_margin` est le champ de la boucle sur
   son axe ; il reste le même quelle que soit la taille de l'étiquette.
   À courant égal, l'étiquette P reçoit 38 à 41 % de la tension induite
   dans celle de 25 mm (`NfcActivation.emf_vs_reference`, 41 % sur
   L60x3 et 38 % sur L70x2). Le modèle d'activation (tension
   induite à la puce contre celle de l'étiquette de référence au
   minimum ISO) est `nfc.tag_activation`, écrit au lot 2.
3. **Le courant d'antenne n'est pas 100 mA.** Un réseau d'adaptation à
   50 Ω différentiels pousse 311 mA dans la boucle L70x2 du yaml et
   274 mA dans la boucle L60x3 à pleine conductance (`nfc.matching`),
   soit 15 et 23 A/m à l'étiquette : 10 à 15 fois le minimum ISO de classe 1,
   mais 2 à 3 fois le maximum de 7,5 A/m. Le micrologiciel le ramène
   sous 7,5 A/m par les registres de conductance de l'émetteur. Le
   condensateur unique de 402 pF que le modèle calcule pour la boucle
   L70x2 (`nfc.antenna().c_res_pF`, 433 pF avant la correction du
   point 10) est remplacé par un vrai réseau
   (paragraphe 4.4).
4. **La présence Hall n'est robuste que pour une pièce centrée.** Au
   capteur central, le pion à l'entrefer maximal passe sous le seuil de
   10,3 mT à 6,6 mm du centre de la case, alors qu'il peut s'en écarter
   de 16,25 mm (base de 17,5 mm dans une case de 50). À 10 mm de
   décalage il donne 3,8 mT, autant qu'un roi soulevé de 15 mm : un
   capteur seul ne distingue pas « décentré » de « soulevé ». Chiffres
   de `hall.piece_bz_mT` à p = 50 :

   | ρ (mm) | 0 | 3 | 5 | 6 | 7 | 8 | 10 | 12 | 15 |
   |---|---|---|---|---|---|---|---|---|---|
   | pion, entrefer max (mT) | 20,7 | 18,1 | 14,1 | 11,8 | 9,4 | 7,3 | 3,8 | 1,6 | 0,1 |
   | roi, entrefer max (mT) | 27,6 | 25,7 | 22,3 | 20,0 | 17,4 | 14,6 | 9,1 | 4,8 | 0,9 |

   Un amas de cinq capteurs (centre plus quatre aux points
   (±0,10 p, ±0,10 p), sur les diagonales, soit ±5 mm à p = 50) garde
   le pion au-dessus du seuil sur tout un carré de ±9,3 mm
   (`hall.offset_coverage`), un peu plus de la moitié du décalage
   possible ; posés sur les axes, les mêmes capteurs ne couvriraient
   que ±6,4 mm. À p = 40, l'amas est à ±4 mm, le seuil à 6,8 mT, le
   carré couvert de ±8,0 mm pour 13 mm de décalage possible, et le
   capteur seul voit le pion jusqu'à 5,7 mm. La préparation plaçait
   l'amas à ±0,12 p : le modèle du lot 2 montre que ce point dépasse
   l'optimum (±8,8 mm à p = 50, ±7,9 à p = 40, sous les 8 mm de D14).
   Le décalage qu'une pièce posée à la main doit supporter est
   maintenant dans le yaml (`hall_rfid.layout.admissible_offset_mm`,
   ±8 mm provisoires, décision D14), et c'est contre lui que M12b
   tranche. La
   maquette porte l'amas sur une case pour le mesurer. **La nappe Hall
   4 x 4 de la note 24 attend cette mesure.**
5. **DRV5053OA : deux valeurs de fiche fausses, et la rupture.** Le
   2,3 mA de `i_supply_ma` est le courant de limitation de la sortie ;
   la consommation est de 2,7 mA typique, 3,6 mA au plus. La mise sous
   tension est de 35 µs typique, 50 µs au plus, et non 100. La
   référence C165150 est en rupture chez LCSC.
6. **Le SS39ET est chez LCSC** (C126669), contrairement à ce que dit
   `docs/prix-hall.csv`.
7. **L'ESP32-S3-WROOM-1 ne s'assemble qu'en « Standard » chez
   JLCPCB**, pas en assemblage économique. Ce point décide du type
   d'assemblage (paragraphe 8.2).
8. **Accord de l'étiquette : un compromis, pas une interdiction.**
   Accordée vers 14 MHz, l'étiquette reçoit trois à quatre fois plus de
   tension à courant d'émission égal, mais elle déplace l'impédance du
   lecteur : le réseau accordé avec elle ne vaut que pour cette classe
   d'étiquette (sur L60x3, C1 de 75 pF au lieu de 62 avec P + 22 pF, à
   14,5 MHz ; 121 pF pour une étiquette à 14,0 MHz, l'effet est raide
   près de la porteuse), et à pleine conductance, sur le réseau accordé
   avec P nue, elle tire 133 mA de courant TVDD sur L60x3 et 81 sur
   L70x2 à p = 50, au-delà des 100 mA du MFRC522 sur L60x3
   (`nfc.panel_supply`) ; G nue en tire 116 et G + 10 pF 205 sur L60x3.
   À p = 40, P + 22 pF tombe à 13,8 MHz et aucun réseau accordé avec
   elle n'atteint 50 Ω. Accordée haut, vers 17 MHz, l'étiquette P nue
   laisse l'adaptation presque indépendante de la pièce (courant TVDD de
   40 à 49 mA avec ou sans elle), au prix de ce facteur trois sur la
   tension. Au champ de service, en revanche, toutes les variantes
   restent sous 28 mA : la pleine conductance ne s'emploie qu'avec P
   nue ou sans étiquette (mise en route et M13). La planche porte
   toutes les variantes (paragraphe 5).
9. **Pièce LC et étiquette dans la même base : problème ouvert.**
   L'aimant ferrite, isolant, désaccorde l'étiquette de 0,5 %
   (`nfc.tag_magnet_detune`, susceptibilité supposée de 0,10,
   `mockup.tags.ferrite_chi`). Mais la bobine LC de pièce, couplée à
   0,67 (P) ou 0,65 (G) avec l'étiquette et fermée sur son
   condensateur, lui retirerait 42 à 45 % d'inductance et pousserait sa
   résonance vers 21 à 23 MHz (`nfc.tag_piece_coil`). La maquette mesure des pièces sans bobine
   LC ; la cohabitation des deux technologies dans une pièce n'est pas
   résolue ici.
10. **`nfc.antenna` sous-estime l'inductance des boucles.** Il prend pour
    diamètre intérieur le côté moins 2 N (piste + écart), soit un écart
    de trop : 21 mm au lieu de 22 pour L60x3, 29 au lieu de 30 pour
    L70x2. Mohan donne alors 0,457 et 0,318 µH au lieu de 0,491 et
    0,343 µH, valeurs que confirme le modèle par filaments du dépôt
    (`chessboard_calc/filament.py` : 0,485 et 0,339 µH). Les
    condensateurs du paragraphe 4.4 sont calculés sur la bonne valeur ;
    calculés avec l'ancienne formule, ils auraient poussé le courant
    d'émission au-delà des 100 mA du MFRC522 (115 et 135 mA selon la
    préparation). Le lot 2 a corrigé `nfc.antenna`, et un test épingle
    les inductances des trois boucles à 2 % près contre le modèle par
    filaments. Le Q de 0,27 et le désaccord de -12 % du verdict du
    multiplexeur (`switch_verdict`) deviennent 0,29 et -13 %.
11. **Le CD74HC4067SM96 est en SSOP-24, pas en TSSOP-24.** C'est le
    boîtier DB de TI (5,3 mm de corps), listé « SSOP-24-208mil » chez
    LCSC (C98457). Le commentaire du yaml et `docs/prix-hall.csv` disent
    TSSOP : une empreinte TSSOP ne recevrait pas la pièce.

## 3. L'ensemble commandé

| Élément | Service | Quantité | Ce qu'il porte |
|---|---|---|---|
| Carte principale `hallrfid` | JLCPCB, carte 2 couches et assemblage Standard | 5 cartes, 2 assemblées | 4 cases, 4 boucles NFC, 4 lecteurs, 8 capteurs Hall, le multiplexeur, l'ESP32-S3, l'USB-C |
| Planche d'étiquettes `tag` | JLCPCB, carte 2 couches 0,8 mm et assemblage | 5 planches, 2 assemblées | 17 étiquettes à puce NXP en quatre variantes, 2 emplacements Murata en option, la vignette de champ (non assemblée) |
| Pièces de test | JLC3DP, résine SLA | 6, et 6 de rechange | 2 pions, 2 cavaliers, 2 rois, avec logement d'étiquette et aimant amovible |
| Plaque de surface, cales, gabarits | JLC3DP | 1 jeu | plaque de 3,5 mm sur pieds de 2 mm, cales d'entrefer, escalier de soulèvement, gabarit de décalage |
| Composants libres | LCSC, envoi groupé avec JLCPCB | 1 lot | assortiment de C0G 0603 de retouche, résistances de 51 et 100 Ω (Q8), selfs de 470 et 680 nH (retouche du filtre), les trois composants de la vignette, barrettes 2,54 mm |

## 4. La carte principale `hallrfid`

### 4.1 Format et empilement

- **Deux couches, FR-4 1,6 mm, cuivre 1 oz, HASL sans plomb.**
  L'épaisseur est celle du modèle (`gap.pcb_mm`) : entre le cuivre des
  boucles et le dessous de la pièce, 5,5 mm comme sur le plateau (air
  2,0, contreplaqué 3,0, feutre 0,5).
- **Contour utile : 2p x (2p + bande)**, soit 100 x 145 mm à p = 50 et
  80 x 125 mm à p = 40, avec une bande électronique de 45 mm
  *(prél., le lot 5 la fixe)* ; 110 x 145 mm avec les rails. La carte
  dépasse le palier de 100 x 100 mm : c'est assumé, deux cartes
  coûteraient deux mises en route d'assemblage et un connecteur.
- **Hauteur dans la zone de jeu : 1,8 mm au plus**
  (`plateau.quadrant.front_end_max_height_mm`, sous les 2,0 mm de
  `gap.air_mm`) : boîtiers QFN de 0,85 mm, quartz de 0,8 mm, selfs
  0805, capteurs SOT-23 (1,3 mm dans `hall_rfid.sensors[].height_mm`,
  l'enveloppe du SOT-23, gardée tant que le dessin du boîtier DBZ n'est
  pas relu au lot 3), U.FL non
  montés de 1,25 mm. Le module, l'USB-C, le régulateur et les boutons
  sont dans la bande.
- **Masse en arbre, jamais en anneau.** Sur les deux faces, la masse de
  la zone de jeu est une croix qui part de la bande par le couloir
  central et suit les couloirs entre boucles ; elle ne longe aucun bord
  extérieur, si bien qu'aucune boucle n'est entourée, même en
  réunissant les deux faces et les vias de couture : un anneau serait
  une spire en court-circuit. La garde de 4 mm autour de chaque boucle
  vaut pour tout cuivre de masse (plan, îlot sous un QFN, pastille d'un
  condensateur), sauf pour les deux branches du réseau d'adaptation qui
  rejoignent l'alimentation de la boucle et pour les trios des capteurs
  Hall (décision D12).
- **Trois mires de placement** (cuivre de 1 mm, ouverture de vernis de
  2 mm, à 3,35 mm au moins du bord) et **deux rails de 5 mm sur les
  grands côtés**, tenus par des attaches à trous et dessinés par le
  générateur : l'assemblage Standard les exige, et les laisser ajouter
  par JLCPCB lui laisserait le choix du côté. Composants à 3 mm au moins
  des bords de la carte utile.
- **Quatre trous M3 non métallisés aux coins de la zone de jeu**,
  centrés à la moitié de la plus petite marge entre boucle et bord
  (3,75 mm à p = 50, 3,0 mm à p = 40), et non à 5 mm comme sur la carte
  bobines (`mockup.coil_board`) : à p = 40, un trou à 5 mm du coin
  entamerait la spire extérieure d'une L70x2, et à p = 50 une tête de
  vis passerait à 0,8 mm de son cuivre. Visserie nylon, vis à tête
  fraisée affleurant la plaque. Deux trous de plus dans la bande.

### 4.2 Les quatre cases

| Case | Boucle | Lecteur | Capteurs Hall |
|---|---|---|---|
| A1 | L60x3 | NXP MFRC52202HN1 | centre, plus 4 aux points (±0,10 p, ±0,10 p) |
| B1 | L70x2 | NXP MFRC52202HN1 | centre |
| A2 | L60x3 | clone JSMSEMI MFRC522 | centre |
| B2 | L70x2 | clone JSMSEMI MFRC522 | centre |

Le plan est croisé : boucles par colonne, lecteurs par rangée. Chaque
boucle existe avec chaque lecteur ; les voisines verticales (A1 et A2,
B1 et B2) portent la même boucle, comme sur un plateau, les voisines
horizontales des boucles différentes.

| Boucle | Côté | Spires | Piste et écart | Ouverture centrale | L (Mohan, filaments) | Pourquoi |
|---|---|---|---|---|---|---|
| L60x3 | 0,60 p = 30 mm | 3 | 1,0 et 0,5 mm | 22 mm | 0,491 et 0,485 µH | recommandée pour le plateau : 1,5 fois plus de champ par racine de watt, moitié moins de couplage aux boucles voisines (`nfc.loop_merit` : 1,49 et 0,57) |
| L70x2 | 0,70 p = 35 mm | 2 | 1,0 et 0,5 mm | 30 mm | 0,343 et 0,339 µH | la boucle du yaml et de la note 24, la référence du modèle |

Les spires sont sur la face avant ; le passage de la spire intérieure
vers l'extérieur se fait par un pont sur la face arrière. Les deux
extrémités de chaque boucle sortent côte à côte au milieu du côté qui
fait face au couloir de son lecteur, et le pont arrière est de ce même
côté. Les trios Hall sortent par un autre côté que celui du pont ; sur
A1, les cinq trios se rejoignent dans l'ouverture et traversent la
boucle en un seul passage, pour qu'aucune masse ne fasse le tour d'une
partie du flux.

**Un lecteur ne tient pas dans la seule marge de sa case.** Son QFN-32
et l'éventail de ses broches demandent un carré libre d'environ 8 mm,
et ses 36 empreintes 300 à 450 mm² ; une fois retirée la garde de 4 mm
autour de la boucle, la marge propre d'une case n'offre au plus qu'un
carré de 7,2 mm (L60x3) ou de 4,7 mm (L70x2) à p = 50
(`hallrfid_mockup.layout`, champ `free_square_mm` de chaque case). Chaque lecteur,
avec son quartz et son filtre, se place donc dans un couloir entre deux
boucles, face à la sienne : le couloir central entre les colonnes A et
B fait 17,5 mm à p = 50, dont 9,5 hors gardes, et la zone de jeu offre
en tout 2 565 mm² hors gardes, hors marge de bord et hors trous, dont
1 839 dans les couloirs (`hallrfid_mockup.layout`). C'est aussi la règle d'un
plateau 8 x 8 sans bande : entre deux boucles L60x3, le couloir hors
gardes fait 12 mm ; entre deux boucles L70x2, 7 mm seulement, trop peu
pour un QFN, ce que Q7 doit peser. À p = 40, avec une garde de 4 mm,
seul le couloir entre deux L60x3 atteint 8 mm, tout juste ; le couloir
central n'en offre que 6 et les lecteurs de B1 et B2 n'y tiennent pas :
la variante p = 40 demande une garde de 2 mm, que M13 devra justifier
(décision D12). `hallrfid_mockup.check` refait ce calcul aux deux pas
et refuse une disposition où un lecteur ne tient pas.

Le modèle (`hallrfid_mockup.layout`) place chaque lecteur dans le
couloir adjacent le plus large : ceux de B1 et B2 dans le couloir
central, ceux de A1 et A2 ensemble dans le couloir A1|A2, qui offre
475 mm² libres pour deux lecteurs, quand un lecteur et ses passifs en
demandent 300 à 450 (`mockup.reader.area_mm2`) : il en manque 125 à
425, ce que le rapport signale. `hallrfid_mockup.check` ne vérifie que
le carré de `mockup.reader.footprint_square_mm` ; le lot 5 tranche
(lecteur de A1 dans la marge extérieure de sa case, passifs en 0402, ou
face arrière) avant le placement.

### 4.3 La chaîne Hall

- **Capteur : TI DRV5055A3QDBZR** (C266128), SOT-23, ratiométrique,
  1,65 V à champ nul sous 3,3 V, 15 mV/mT (14,3 à 15,8), linéaire sur
  ±88 mT, 6 mA typique et 10 mA au plus, mise sous tension de 175 µs
  typique et 330 µs au plus. Le roi appuyé donne 2,17 V et le pion le
  plus faible 410 pas de l'ADC (`hallrfid_mockup.hall_chain`) : tout reste
  dans la plage la plus linéaire de l'ESP32-S3. Pôle sud de l'aimant
  vers le bas : la sortie monte quand un pôle sud fait face au boîtier.
- **Le choix se fait au lot 3, avec un remplaçant désigné** (décision
  D3). Le jour de la commande, un échange ne se fait qu'entre pièces de
  même brochage (1 VCC, 2 OUT, 3 GND), même pente et même ratiométrie :
  DRV5055A3 et SS39ET (C126669, le stock le plus profond), l'en-tête du
  micrologiciel prenant la sensibilité dans le yaml ; il est noté au
  journal et reporté dans `docs/prix-hallrfid.csv` et dans le BOM
  commité. Le DRV5053OA (C165150 en rupture, variante Q1 C2654961, ou
  par le « Global Sourcing » de JLCPCB), de pente négative et non
  ratiométrique, demande de régénérer l'en-tête et ne s'échange pas le
  jour même.
- **Huit capteurs** : un au centre de chaque case, plus quatre autour
  du centre de A1, sur les diagonales, aux points (±0,10 p, ±0,10 p),
  dans l'ouverture de la boucle L60x3 (22 mm à p = 50, 16 mm à
  p = 40). Posés sur les axes, ils ne couvriraient qu'un carré de
  ±6,4 mm au lieu de ±9,3 mm (`hall.offset_coverage`).
- **Par capteur** : 100 nF au plus près, et un filtre RC de 1 kΩ et
  10 nF sur la sortie (-59 dB à 13,56 MHz, `hall_chain`). Le filtre n'agit
  sur la porteuse captée par les pistes que si le 10 nF est en aval de
  la traversée de la boucle : 1 kΩ près du capteur, 10 nF à l'arrivée,
  au plus près de l'entrée du mux ou de la broche de l'ADC ; pour un
  capteur central, au point où la piste se sépare vers les deux, avec
  deux branches courtes et hors des boucles. Les trois pistes sortent
  de la boucle en trio serré, à angle droit, sur la face arrière :
  écartées de 5 mm, elles capteraient 150 à 190 mV efficaces de
  porteuse à pleine conductance, contre 24 à 30 mV en trio serré, ses
  deux pistes extérieures à 0,8 mm (`nfc.hall_trace_pickup`,
  `mockup.hall.trio_pitch_mm`) ; le filtre les ramène à quelques
  dizaines de µV.
- **Chaque capteur central va à la fois sur une entrée ADC1 directe et
  sur une voie du multiplexeur**, pour comparer les deux chemins. Les
  deux chemins partagent le même 10 nF : à chaque commutation, le nœud
  commun du mux (50 pF, `mux.c_on_pF`) y prend ou y rend 0,5 % de
  l'écart avec la voie précédente : après la voie de masse, 8 mV
  (11 pas) pour une case vide et 11 mV (14 pas) pour un roi appuyé,
  résorbés en 31 et 34 µs (`hallrfid_mockup.hall_chain`). Le
  `mux.t_settle_us` de 2 µs du yaml ne vaut donc pas pour la maquette,
  qui attend 34 µs. Avec le filtre, une lecture valable vient 259 µs
  après `ROW_EN`, 417 µs au plus.
- **Multiplexeur CD74HC4067SM96** (C98457, SSOP-24 de 5,3 mm, stock
  à revoir au lot 3), entrée de validation à la masse par une
  résistance de 0 Ω :

  | Voies | Signal |
  |---|---|
  | 0 à 3 | capteurs centraux A1, B1, A2, B2 |
  | 4 à 7 | les quatre capteurs autour du centre de A1 |
  | 8 | masse (zéro du chemin) |
  | 9 | rail commuté de la rangée 1 divisé par deux (référence ratiométrique) |
  | 10 | échelon de la broche de la LED à travers un pont diviseur par deux et un RC connu, pour rester sous la pleine échelle de 3,1 V (chronométrage de l'échantillonnage) |
  | 11 à 15 | barrette d'extension : sondes extérieures, une future nappe |

- **Alimentation par rangées** : deux P-FET AO3401A (C15127), un par
  rangée, grille tirée au 3,3 V par 10 kΩ, un cavalier à souder en
  dérivation pour l'alimentation permanente, un point de test par rail.
- **Zéro ratiométrique** : la sortie suit le rail du capteur, l'ADC a
  sa propre référence. Le micrologiciel prend le zéro de chaque capteur
  à vide au démarrage et lit la voie 9 ; la chute dans le P-FET (moins
  de 5 mV) déplace le zéro de 3 pas au plus, absorbés par ce zéro.

### 4.4 La chaîne RFID, par case

- **Lecteur MFRC522 en QFN-32 5 x 5**, une empreinte, deux puces : le
  NXP MFRC52202HN1,151 (C11322) sur la rangée 1, la référence dont la
  fiche fait autorité ; le clone JSMSEMI MFRC522 (C2760772, 3 266 en
  stock chez JLCPCB au relevé, mais marqué « Discontinued » chez LCSC)
  sur la rangée 2. Le clone suffit à la maquette, pas à fonder seul le
  prix d'un plateau à 64 lecteurs, que le VIBRATION VRC522 (C968718)
  doit aussi chiffrer. La compatibilité broche à broche des deux
  clones n'est qu'annoncée par les vendeurs : leurs fiches (brochage,
  broches de configuration, pastille centrale, valeur de `VersionReg`)
  sont comparées à celle de NXP au lot 3.
- **Mode SPI** par les broches de configuration : `I2C` à la masse,
  `EA` au 3,3 V ; `MFIN` relié à PVSS (la fiche impose de relier un
  MFIN inutilisé à SVDD ou PVSS).
- **Quartz 27,12 MHz** 3225, charge 10 pF (C29975), deux 15 pF C0G.
- **Réseau d'adaptation symétrique**, de chaque côté : TX, L0 en série,
  C0 à la masse, C1 en série, C2 à la masse, Rq, boucle. Visé : 50 Ω
  différentiels et un Q chargé de 24 (`hall_rfid.mockup.matching`, qui
  remplace pour la maquette le `nfc.antenna.q_target` de 20). Accord
  fait au NanoVNA avec l'étiquette P nue posée à l'entrefer nominal,
  puis vérifié en émission par le courant TVDD. À pleine puissance, le
  limiteur de la puce déplace encore l'impédance, ce que M13 mesure.
  Valeurs calculées par `nfc.matching`, par côté (C1 et C2 : valeur
  principale et complément de la série E12, en parallèle) :

  | | L60x3, p = 50 | L70x2, p = 50 | L60x3, p = 40 | L70x2, p = 40 |
  |---|---|---|---|---|
  | Filtre CEM L0 et C0 | 560 nH et 220 pF, coupure à 14,34 MHz | idem | idem | idem |
  | Rq (Q chargé) | 0,68 Ω (24,3) | 0,47 Ω (23,4) | 0,47 Ω (23,5) | 0,33 Ω (23,2) |
  | C1 | 56 + 5,6 pF | 82 + 3,3 pF | 82 + 4,7 pF | 100 + 18 pF |
  | C2 | 470 + 33 pF | 680 + 56 pF | 680 + 56 pF | 1 000 + 33 pF |
  | Impédance, étiquette P posée | 49,0 - 0,7j Ω | 54,7 + 6,4j Ω | 51,9 + 1,4j Ω | 52,0 + 1,8j Ω |
  | Impédance sans étiquette | 48,2 + 26,0j Ω | 57,4 + 21,0j Ω | 57,2 + 27,8j Ω | 61,2 + 12,8j Ω |
  | Courant de boucle à pleine conductance | 274 mA | 311 mA | 315 mA | 371 mA |
  | Champ sur l'axe à l'étiquette, pleine conductance | 23 A/m | 15 A/m | 30 A/m | 21 A/m |
  | Courant TVDD, nominal et au pire des tolérances | 49 et 65 mA | 44 et 59 mA | 46 et 64 mA | 46 et 66 mA |
  | Résistance de sortie au champ de service, par broche | 60,5 Ω | 41,3 Ω | 91,2 Ω | 55,6 Ω |
  | Niveau à `RX`, pleine conductance et service | 1,66 et 0,54 V cc | 1,65 et 0,73 V cc | 1,79 et 0,44 V cc | 1,78 et 0,63 V cc |

  À p = 40, la L60x3 reprend à peu près les valeurs de la L70x2 à
  p = 50. Arrondi à la série E12, le réseau de la L70x2 tombe à 55 Ω au
  lieu de 50 à p = 50, mais son accord ne bouge que de 0,35 % pour une
  demi-bande de 2,1 % : il reste accordé. Le champ de service, 7,5 A/m au plus fort des
  positions admissibles (centre, décalage sur un axe et sur la
  diagonale, `layout.admissible_offset_mm`), s'obtient en relevant la
  résistance de sortie de l'émetteur, comme le fait le registre de
  conductance du MFRC522 : 60,5 Ω par broche sur L60x3 et 41,3 Ω sur
  L70x2 à p = 50, 91 et 56 Ω à p = 40 (`NfcMatching.r_drv_service_ohm`).
  Le courant TVDD y reste sous 28 mA quelle que soit l'étiquette, mais
  le niveau à `RX` tombe à 0,5 à 1,0 V crête à crête, sous la fenêtre
  visée (décision D15, paragraphe 11). Au NanoVNA, dont la source de
  50 Ω dissipe autant que le réseau, le Q lu sur |S21| vaut 12 à 13
  (`nfc.vna_q`), non 24.
- **Tolérances et première émission.** C1 et C2 en C0G à ±2 % ou mieux
  pour les valeurs de 10 pF et plus, à ±0,1 pF en dessous (la tolérance
  s'y exprime en pF). À ±5 %, le courant TVDD atteindrait 94 mA sur
  L60x3 et 90 mA sur L70x2, tout près des 100 mA de la fiche
  (`nfc.tx_supply_spread`, avec et sans étiquette). L'incertitude
  dominante reste l'inductance de la boucle (plan de masse et pont non
  modélisés) : 5 % d'écart (`criteria.loop_l_tol_pct`) le porte vers 94
  et 90 mA avec des condensateurs exacts, 120 mA avec ceux à ±2 %, et
  10 % à 160 mA. Chaque lecteur émet donc d'abord à conductance réduite,
  courant TVDD lu sur sa résistance de mesure, et ne passe à pleine
  conductance qu'après l'accord au NanoVNA et un courant mesuré sous
  70 mA. Une empreinte non montée en parallèle de chaque C1 et C2 sert
  à la retouche.
- **Réception** : R1 et un condensateur de 1 nF en série du nœud C0 vers
  `RX`, R2 de `RX` vers `VMID`, 100 nF sur `VMID` (schéma type de la
  fiche NXP). Le nœud C0 porte 7,1 à 8,1 V crête à crête à pleine
  puissance et `RX` accepte 4 V crête à crête au plus : `nfc.matching`
  prend R2 = 1 kΩ (`mockup.reader.rx_r2_ohm`) et choisit R1, 3,9 kΩ sur
  L60x3 et 3,3 kΩ sur L70x2 à p = 50, pour 1,65 V crête à crête à `RX`,
  dans la fenêtre de 1,5 à 2 V.
- **Les quatre lecteurs sur un seul bus SPI**, une ligne `NSS` chacun
  (tirée au 3,3 V par 10 kΩ), une ligne `NRSTPD` chacun (tirée à la
  masse par 10 kΩ : aucune émission avant le micrologiciel), `IRQ` en
  drain ouvert sur une ligne commune. Le MISO d'un MFRC522 n'est pas
  garanti en haute impédance quand `NSS` est haut : un 74LVC125APW
  (C6059, TSSOP-14), une voie par lecteur validée par son `NSS`, avec
  des 0 Ω non montés pour s'en passer et mesurer s'il est nécessaire.
- **Aménagements de mesure** :
  - une résistance de 1 Ω dans le `TVDD` de chaque lecteur, le 10 µF
    côté broche, avec deux points de test : le courant se lit en
    millivolts au multimètre sans dessouder (50 mV pour 50 mA) ;
  - des points de test sur TX1, TX2 et RX, chacun avec une pastille de
    masse à côté ;
  - pour le NanoVNA, deux 0 Ω entre TX1, TX2 et les selfs L0, qui
    isolent le lecteur pour mesurer le réseau depuis son entrée, et une
    empreinte U.FL non montée à l'entrée de chaque demi-réseau ; la
    méthode (balun 1:1, deux ports, ou un port en trois lectures) est
    écrite au protocole au lot 2 ;
  - sur les boucles L70x2, les deux places de Rq acceptent 51 Ω (100 Ω
    dans la boucle) et une empreinte non montée en parallèle de la
    boucle accepte 120 pF : c'est l'émulation du multiplexeur (Q8). Ce
    montage, comme une boucle coupée, désaccorde tout le réseau :
    l'émetteur ne voit plus que la résonance série de L0 et C0 et
    tirerait 141 mA de courant TVDD à pleine conductance, 143 mA
    boucle coupée (`nfc.mux_emulation`). M13c se fait donc à conductance réduite,
    courant TVDD tenu sous 60 mA
    (`criteria.mux_emulation_i_tvdd_max_ma`) ; le champ tombe alors à
    0,37 A/m.
  - Les trois cartes non assemblées servent à mesurer chaque géométrie
    de boucle seule (inductance, résistance, fréquence propre) par un
    câble SMA dénudé soudé aux pastilles d'alimentation : c'est la
    vérification directe du modèle d'inductance (point 10 du
    paragraphe 2).
- **Règle d'émission** : un seul émetteur à la fois. La fiche NXP ne
  définit pas l'état de TX1 et TX2 émission coupée (« not specified if
  switched off ») ; `DriverSel` à 00 les met en haute impédance, et la
  mise hors tension matérielle les fige sans dire sous quelle
  impédance. Une boucle voisine laissée flottante, accordée, sert de
  relais : entre boucles identiques, la case voisine reçoit 21 % du
  flux de la case active avec L60x3 et 36 % avec L70x2, contre 6 % et
  13 % à sorties tenues, et 2 à 3 % sans boucle voisine ; entre boucles
  différentes, jusqu'à 39 % (`nfc.neighbor_relay`, modèle à deux
  boucles, à p = 50 ; la relecture, sur quatre boucles où les deux
  autres absorbent une part du courant, trouvait 31 %).
  Les voisins restent donc alimentés dans l'état où la fiche
  tire TX1 et TX2 à 0 : émetteurs validés, `Force100ASK` à 1, enveloppe
  nulle par `DriverSel` à 10 avec `MFIN` à PVSS, à vérifier sur les deux
  puces en M13b. Le micrologiciel n'écrit jamais `DriverSel` à 00, lit
  et note `VersionReg`, n'exige pas l'autotest NXP et n'emploie que les
  registres communs aux deux puces.

### 4.5 La bande électronique

- **ESP32-S3-WROOM-1-N8** (C2913198), à 3 mm du petit côté de la bande,
  antenne vers ce bord, aucun cuivre sous l'antenne ni entre elle et le
  bord, sans débord : le Wi-Fi ne sert pas ici, et un débord
  interdirait un rail sur ce bord. USB natif (USB-Serial-JTAG sur GPIO19
  et 20) : ni pont USB série ni quartz 32 kHz. Boutons BOOT (GPIO0) et
  EN, RC sur EN.
- **USB-C 16 broches tout CMS** (candidat C2765186, stock à confirmer au
  lot 3 ; repli USB4085-GF-A C2988369, à pattes traversantes),
  5,1 kΩ sur CC1 et CC2, protection USBLC6-2SC6 (C7519).
- **Deux pastilles 5V et GND** au pas de 2,54 mm, sur le 5 V avant le
  régulateur, pour une première mise sous tension par une alimentation
  de laboratoire limitée en courant, jamais en même temps que l'USB.
- **Régulateur AMS1117-3.3** (C6186), 1 A, avec en sortie le
  condensateur au tantale de 22 µF (résistance série sous 0,5 Ω) que
  sa fiche demande pour la stabilité ; il amortit aussi l'appel de
  courant des rails commutés. Budget sans radio
  (`hallrfid_mockup.power`) : ESP32 vers 100 mA, un lecteur en émission
  jusqu'à 100 mA, quatre lecteurs éveillés jusqu'à 76 mA, huit capteurs
  jusqu'à 80 mA, soit 356 mA ; avec le courant propre du régulateur
  (10 mA au plus), 0,66 W dans le SOT-223 sous 5 V (0,75 W sous 5,25 V,
  jonction vers 107 °C pour 125 admis, avec une résistance thermique
  supposée de 90 °C/W, à relire au lot 3). Sous les 4,75 V d'un hôte
  USB, il lui reste 1,45 V pour 1,3 V de chute au plus.
- Une LED d'état, et une **barrette d'échappement** 2,54 mm non montée
  qui porte tous les signaux, avec un cavalier sur EN : si le module ne
  démarre pas, une ESP32-S3-DevKitC branchée là pilote la carte.

### 4.6 Brochage de l'ESP32-S3

Proposé, validé au lot 2 par des tests : broches uniques, entrées
analogiques sur ADC1, broches de configuration 0, 3, 45 et 46 jamais
pilotées, 19 et 20 réservées à l'USB, 35 à 37 laissées libres pour
qu'un module à PSRAM octale 3,3 V (suffixe R8) reste montable. Les
variantes à 1,8 V (suffixe V) sont exclues : elles mettraient 47 et 48,
donc deux `NRSTPD`, à 1,8 V.

| Signal | GPIO | | Signal | GPIO |
|---|---|---|---|---|
| `MUX_OUT` (ADC1) | 1 | | `SPI_MOSI` | 11 |
| `HALL_A1` (ADC1) | 2 | | `SPI_SCK` | 12 |
| `HALL_B1` (ADC1) | 4 | | `SPI_MISO` | 13 |
| `HALL_A2` (ADC1) | 5 | | `NSS_A1`, `NSS_B1`, `NSS_A2`, `NSS_B2` | 14, 38, 39, 40 |
| `HALL_B2` (ADC1) | 6 | | `NRSTPD_A1`, `NRSTPD_B1`, `NRSTPD_A2`, `NRSTPD_B2` | 41, 42, 47, 48 |
| `PICKUP` (ADC1, vignette) | 7 | | `MUX_S0` à `MUX_S3` | 15, 16, 17, 18 |
| `LED` (et échelon de la voie 10) | 8 | | `ROW_EN1` (rangée 1 : A1, B1) | 21 |
| `RFID_IRQ` | 9 | | `ROW_EN2` (rangée 2 : A2, B2) | 10 |
| USB D-, D+ | 19, 20 | | UART0 TX, RX (points de test) | 43, 44 |

Les 19 signaux numériques prennent toutes les broches libres du module
N8 hors 35 à 37, 43 et 44. Ces deux dernières sont la réserve : la
console passe par l'USB-Serial-JTAG, l'UART0 ne sert qu'en secours. Si
une ligne manquait encore, `IRQ` passe en scrutation. Les broches 39 à
42 restent des GPIO tant que le JTAG passe par l'USB (fusibles par
défaut, à ne pas modifier).

### 4.7 Ce que la carte ne porte pas

Pas de spirale LC (une spirale deux couches ne serait pas celle du
projet, et la [carte bobines](../bom-pilote.md) existe), pas de LED de
camp (les WS2812B ne s'assemblent qu'en Standard et n'apprennent rien
ici), pas d'arbre de commutateurs RF, pas de PN5180, pas de batterie,
pas de vignette détachable (elle ferait de la carte un panneau de deux
conceptions, facturé en carte et en assemblage : elle passe sur la
planche d'étiquettes).

## 5. Les étiquettes : la planche `tag`

- **Étiquette P** : disque de 14,5 mm à p = 50 (base du pion moins deux
  parois de 1,2 mm et deux jeux de 0,3 mm, `WALL_MIN` et `FIT_LOOSE` de
  `mechanical/common.py`, portés dans le yaml au lot 2 :
  `mockup.tags.wall_mm` et `fit_mm`), 2 couches,
  FR-4 0,8 mm, bobine de 5 + 5 spires en série à 0,20 et 0,20 mm de
  piste et d'écart (13,5 mm de cuivre, 9,9 mm d'ouverture), les deux
  extrémités au centre, aucun pont. Inductance 1,67 µH, fréquence
  propre de 17,3 MHz avec les 50 pF de la puce (`nfc.tag_geometry`).
  Elle tient dans toutes les bases. À p = 40, le disque fait 11 mm :
  `nfc.tag_geometry`, qui tire spires et piste du pas, y prend 7 + 7
  spires à 0,15 mm (16,5 MHz), la piste la plus large qui s'accorde dans
  la fenêtre de 16 à 18 MHz en gardant une ouverture d'au moins la
  moitié du cuivre (`mockup.tags.opening_min_ratio`).
- **Étiquette G** : disque de 19,5 mm à p = 50 (15 mm à p = 40) pour les
  bases de 22,5 mm, 4 + 4 spires à 0,20 mm, 16,1 MHz (5 + 5 spires et
  16,8 MHz à p = 40), pour mesurer ce que la taille rapporte.
- **Puce** : NXP NTAG I2C plus NT3H2111W0FHKH (C710403), XQFN-8
  1,6 x 1,6 mm, NFC type 2 (ISO 14443-3A), UID de 7 octets lu par le
  MFRC522, 50 pF d'entrée. Broches I2C et alimentation laissées libres
  ou à la masse (à relire dans la fiche, lot 3). Classée « Economic and
  Standard », étendue, mais à zéro dans le stock JLCPCB au relevé
  contre 7 430 chez LCSC : précommande au lot 3. Remplaçante, même
  empreinte : NT3H2211W0FHKH (C2905792, stock faible).
- **Variantes sur la planche**, pour mesurer au lieu de deviner :

  | Variante | Accord (`nfc.tag_tuning`, p = 50) | Rôle |
  |---|---|---|
  | P nue | 17,3 MHz | accordée haut : charge faible du lecteur, adaptation presque indépendante de la pièce, la seule admise à pleine conductance ; mais marge d'activation de 1,27 à 1,37 seulement au champ de service, sous le 2 de Q5 (`nfc.tag_activation`) |
  | P + 15 pF | 15,2 MHz | compromis : marge de 2,09 et 2,23 au champ de service, juste au-dessus de 2 |
  | P + 22 pF | 14,5 MHz | tension à la puce trois fois plus forte que P nue ; la meilleure marge au champ de service (2,35 et 3,15) ; jamais à pleine conductance (paragraphe 2, point 8) |
  | G nue | 16,1 MHz | la grande base : marge de 2,01 et 2,50 au champ de service |
  | G + 10 pF | 14,7 MHz | ajoutée au lot 2 : au pas de 40, la seule G qui tient sur L70x2 (2,02) ; à p = 50, 1,89 sur L60x3 et 3,13 sur L70x2 |
  | Murata LXMS33HCNK-171 (C17590014), en option | antenne intégrée | repli sans bobine à accorder ; 66 pièces chez LCSC au relevé, délai fabricant de 28 semaines |

- **Vignette de champ**, sur la même planche, non assemblée : une
  bobine de 10 mm à 4 spires sur deux couches, une diode de détection à
  seuil bas (type polarisation nulle) et un RC, soudés à la main
  (composants du colis LCSC), reliée par trois fils torsadés à l'entrée
  `PICKUP`. Une spire seule ne donnerait que 17 à 43 mV crête entre 1,5
  et 3,75 A/m, sous le seuil d'une Schottky ordinaire ; la bobine de
  quatre spires sur deux couches en donne 63 à 158 (`nfc.field_pickup`,
  géométrie dans `mockup.pickup`).
  Étalonnée contre le NanoVNA, elle donne une mesure relative du champ
  sans oscilloscope.
- **Planche** : environ 95 x 85 mm, attaches de 5 à 8 trous de 0,6 mm
  (guide JLCPCB), rails de 5 mm, 17 étiquettes à puce NXP et 2
  emplacements Murata par planche, la répartition entre variantes fixée
  au lot 6. Quatre conceptions (P, G, emplacement Murata, vignette),
  déclarées au formulaire. Cinq planches fabriquées, deux assemblées,
  soit 34 étiquettes NXP et 4 Murata. Assemblage économique (0,8 mm est
  dans sa plage), Standard s'il le faut.
- **Dans la pièce** : l'étiquette se loge dans l'alésage de la bobine LC,
  ouvert par-dessous (`mechanical/parts.py`), affleurant la face
  inférieure de la base, puce vers le haut, plaquée par un ruban
  polyimide de 0,06 mm qui la laisse échangeable : sans maintien, son
  jeu vertical de 0,7 mm changerait le couplage. 0,8 mm de carte et
  0,5 mm de puce tiennent sous l'aimant, qui reste à sa hauteur : le
  budget Hall de la note 24 est inchangé (6,9 mm de l'aimant au
  capteur). Le cuivre de la face inférieure de l'étiquette est à 5,5 mm
  de la boucle (`nfc.tag.height_in_base_mm` : 0), celui de sa face
  supérieure à 6,3 mm.

## 6. Les pièces imprimées (JLC3DP)

Résine SLA (9000R ou JLC Black), tolérance annoncée ±0,2 mm, fichiers
STL et STEP générés par `mechanical/` :

- **Six pièces de test** : 2 pions (base 17,5 mm), 2 cavaliers (20 mm),
  2 rois (22,5 mm), hauteur des pucks existants (14 mm, `puck_dims` de
  `mechanical/common.py`), chacune numérotée en gravure. Pions et
  cavaliers portent l'étiquette P ; un roi l'étiquette G, l'autre
  l'étiquette P, pour comparer les tailles dans la même base. L'aimant
  entre à force par-dessous, avant l'étiquette, et un trou d'éjection
  de 2 mm par-dessus permet de le retirer : n'importe quelle pièce,
  aimant retiré, sert de témoin, et M14a compare la même pièce avec et
  sans aimant. Six pièces de rechange au même dessin.
- **Plaque de surface** : 3,5 mm (contreplaqué 3,0 plus feutre 0,5 du
  yaml), aux dimensions de la zone de jeu, avec des pieds de 2,0 mm qui
  évitent les lecteurs, positionnée par les quatre trous M3. Sa
  planéité est relevée en neuf points avant M12.
- **Cales d'entrefer** : 0,9 mm (entrefer maximal moins nominal) taillée
  dans une planche d'étiquettes nue (FR-4 0,8 mm ±0,1), puis 1, 2, 5 et
  10 mm en résine, de 30 x 30 mm au plus pour rester au-dessus de
  l'épaisseur minimale de JLC3DP. Chacune est mesurée au pied à
  coulisse.
- **Escalier de soulèvement** de 0 à 20 mm par pas de 1 mm, et
  **gabarit de décalage** de 0 à 16 mm par pas de 2 mm dans les deux
  axes (M12b).

## 7. Nomenclature et approvisionnement

Par carte principale. Prix vus à l'unité ou à la petite série, relevés
le 11/10/2026 sauf mention ; le lot 3 fige chaque ligne dans
`docs/prix-hallrfid.csv` avec sa source, au format de
`docs/prix-plateau.csv`.

| Fonction | Référence | LCSC | Classe JLCPCB | Qté | Prix vu (USD) | Remarque |
|---|---|---|---|---|---|---|
| Module | ESP32-S3-WROOM-1-N8 | C2913198 | étendue, Standard seulement | 1 | 3,3 | prix du 20/09/2026 |
| Lecteur, rangée 1 | MFRC52202HN1,151 | C11322 | à confirmer | 2 | 1,7 à 2,8 | NXP, non recommandé pour les nouvelles conceptions |
| Lecteur, rangée 2 | JSMSEMI MFRC522 | C2760772 | étendue, en stock | 2 | 1,25 | clone, « Discontinued » chez LCSC |
| Capteur Hall | DRV5055A3QDBZR | C266128 | étendue (à confirmer) | 8 | 0,44 | remplaçant SS39ET C126669 |
| Multiplexeur | CD74HC4067SM96 | C98457 | à confirmer | 1 | 0,27 | SSOP-24 ; stock contradictoire entre relevés |
| Tampon MISO | 74LVC125APW | C6059 | à confirmer | 1 | 0,2 environ | TSSOP-14 |
| Quartz 27,12 MHz | X32252712MMB4SI | C29975 | à confirmer | 4 | 0,064 | |
| Self CEM 560 nH 0805 | FHW0805UCR56JGT | C139264 | à confirmer | 8 | 0,032 | remplaçant C37297 |
| C0G 0603, réseau d'adaptation | à choisir | lot 3 | étendue (pas de ±2 % en basique) | 40 | 0,02 à 0,1 | C0 : 220 pF (8) ; C1 et C2 : 56, 82, 470, 680 et 33 pF à ±2 % ou mieux, 5,6 et 3,3 pF à ±0,1 pF (32) ; 50 V |
| Rq | 0603, 0,68 et 0,47 Ω | lot 3 | à confirmer | 8 | | |
| C0G du quartz et de réception | 15 pF et 1 nF | lot 3 | basique si possible | 8 et 4 | 0,005 | |
| Réception et mesure | R1, R2 (lot 2), 1 Ω de TVDD, 0 Ω | lot 3 ; C21189 pour le 0 Ω | basique | 20 environ | | |
| P-FET | AO3401A | C15127 | basique | 2 | 0,052 | |
| Régulateur | AMS1117-3.3 | C6186 | basique | 1 | 0,055 | |
| Tantale 22 µF | à choisir | lot 3 | à confirmer | 1 | | sortie de l'AMS1117 |
| USB-C | à confirmer | C2765186 | étendue | 1 | 0,3 environ | tout CMS |
| Protection USB | USBLC6-2SC6 | C7519 | étendue | 1 | 0,09 | |
| Passifs génériques | séries basiques 0402 et 0603 | table du lot 3 | basique | 150 environ | 0,002 à 0,01 | 100 nF, 10 nF, 1 µF, 10 µF, 1 kΩ, 5,1 kΩ, 10 kΩ |
| Boutons, LED | séries basiques | lot 3 | basique | 3 | 0,1 | |

Par planche d'étiquettes : 17 NT3H2111W0FHKH (C710403, étendue, 0,66 USD
à l'unité ; précommande de 34 puces plus les pertes de pose, passée au
lot 3, dès le gel des pièces, pour qu'elles soient au magasin JLCPCB au
lot 10), des C0G 0402 de 10, 15 et 22 pF, et deux Murata (1,60 USD) en
option.

Composants libres de LCSC, dans le même colis : un assortiment de C0G
0603 de 2,2 pF à 1 nF pour retoucher l'accord, des résistances 0603 de
51 et 100 Ω (Q8), des selfs 0805 de 470 et 680 nH (retouche du filtre),
la diode et les deux composants de la vignette, des barrettes 2,54 mm.

## 8. La commande chez JLCPCB

### 8.1 Les formulaires

| Champ | Carte principale | Planche d'étiquettes |
|---|---|---|
| Couches | 2 | 2 |
| Dimensions | 110 x 145 mm avec les rails (100 x 145 utiles) | 95 x 85 mm environ |
| Épaisseur | 1,6 mm | 0,8 mm |
| Finition | HASL sans plomb : l'ENIG, que la note 23 conseille au pas de 0,5 mm, est devenu payant, et l'assemblage par JLCPCB juste après fabrication s'accommode du HASL ; l'OSP supporte mal les retouches | HASL : à 0,8 mm, l'assemblage économique n'accepte que le HASL, au plomb seul selon une version du tableau des capacités ; prendre celui que propose le formulaire, ou passer en Standard pour le sans plomb |
| Cuivre | 1 oz | 1 oz |
| Quantité | 5 | 5 |
| Conceptions différentes | 1 | 4 (P, G, emplacement Murata, vignette), déclarées, surcoût au devis |
| Format | carte seule, rails et mires « Added by Customer » | panneau fourni par le client (« Panel by Customer ») |
| Assemblage | Standard, face avant, 2 cartes | économique, 2 planches |
| Confirmation du placement | demandée (QFN, module, USB-C) | demandée (XQFN-8) |
| Numéro de commande | à l'emplacement imposé, dans la bande | à l'emplacement imposé, sur un rail |
| Vias | recouverts de vernis (« Tented », comme à la note 23 ; « Plugged » est une autre option) | idem |

JLC3DP : six pièces et leurs rechanges, la plaque, les cales et les
gabarits, en résine SLA, dans le même panier. Le paiement commun est
documenté, l'envoi commun ne l'est pas : le vérifier au panier, sinon
compter un second port, et ce second colis, sous 150 EUR, paie la TVA au
paiement (IOSS).

LCSC : les composants libres, en envoi groupé avec la commande JLCPCB.
Passer d'abord la commande JLCPCB, puis la commande LCSC en choisissant
l'envoi groupé au paiement (même devise, même compte client ; un colis
groupé ne se sépare plus, le port est recalculé). Vérifier si LCSC
prélève la TVA au paiement : le colis groupé, au-delà de 150 EUR, la
paie à l'import.

### 8.2 Assemblage Standard plutôt qu'économique

Le module ESP32-S3-WROOM-1 n'est assemblé qu'en Standard (point 7 du
paragraphe 2). Trois voies :

| Voie | Frais d'assemblage estimés (USD) | Ce qu'il reste à faire |
|---|---|---|
| **Standard, module posé par JLCPCB** (recommandée) | 90 à 100 : mise en route 25,56, pochoir 8,66, 1,5 par référence chargée (35 à 40 références, basiques comprises), environ 1 400 joints | rien pour la mise en route |
| Économique, module non monté | 40 à 75 (une vingtaine de références étendues, C0G à ±2 % comprises, à 1,5 ou 3 USD selon le tarif du jour) | souder le module à la main (pastilles en bord, plus la pastille de masse dessous) ; module acheté chez LCSC dans le même colis |
| Économique avec un module accepté en économique | à chiffrer | à vérifier le jour du devis (ESP32-S3-MINI-1 annoncé en économique, non confirmé) |

La voie Standard coûte 20 à 50 dollars de plus, selon le tarif des
références étendues en économique, et épargne le module, la seule
soudure difficile. Restent à la main, par choix : Q8, les retouches de
C0G, la vignette et, en secours, la barrette d'échappement. Elle impose
trois mires et deux rails, dessinés sur la carte (paragraphe 4.1).

### 8.3 Ce qui ne part pas de JLCPCB

- **Aimants ferrite** : aucune référence chez LCSC ni chez JLCPCB.
  Diamètres de catalogue les plus proches de 12,5, 15 et 17,5 mm : 12,
  15 et 18 mm sur 4 mm, aimantation axiale, une seule nuance (Y30 ou
  Y35, pas un mélange). Trois de chaque diamètre (deux pour les pièces,
  un nu pour M12a sur cales), autant de rechange, soit 18 disques.
  Achetés au lot 1, mesurés (diamètre et épaisseur au pied à coulisse,
  masse), puis entrés dans le yaml avec la rémanence de la nuance
  achetée (Y30 : 0,37 à 0,40 T ; Y35 : 0,43 à 0,45 T ; le yaml suppose
  0,40 T) avant le lot 8, qui en tire les poches (décision D13).
- **NanoVNA** (60 à 90 EUR), conseillé, avec une sonde de champ proche
  (boucle de 15 à 20 mm sur SMA) et deux câbles U.FL vers SMA. Sans lui,
  la retouche se fait à l'aveugle sur le taux de lecture et la
  vignette, plus lentement. L'oscilloscope de poche de 10 MHz de la
  fiche du pilote ne voit pas 13,56 MHz.
- **Étiquettes de référence** : cinq à dix cartes NTAG213 du commerce,
  lues au téléphone, pour séparer une panne de lecteur d'une panne
  d'étiquette.
- **Visserie nylon** : quatre vis M3 à tête fraisée, entretoises M3 de
  30 mm (quatre sous la zone de jeu, deux sous la bande), écrous.
- **Soudure** : fer fin, flux, tresse, brucelles, ruban polyimide.
- **Câbles** : USB-C de données ; fils Dupont pour la vignette ;
  adaptateur USB série 3,3 V pour l'UART0.
- Hors JLCPCB, compter 50 à 95 EUR sans le NanoVNA, 110 à 185 EUR avec
  *(estimation, prix non relevés)*.

### 8.4 Coût estimé

| Poste | USD |
|---|---|
| 5 cartes principales nues, 110 x 145 mm avec rails, 2 couches, HASL sans plomb | 10 à 25 |
| Assemblage Standard de 2 cartes (frais : mise en route, pochoir, 35 à 40 références à 1,5, joints) | 90 à 100 |
| Lignes possibles du devis : rails, gabarit d'assemblage du module | 0 à 30 |
| Composants de 2 cartes | 35 à 48 |
| Planches d'étiquettes : 5 fabriquées, 2 assemblées, 34 puces et 4 Murata, quatre conceptions | 50 à 80 |
| JLC3DP : pièces, plaque, cales, gabarits | 20 à 40 |
| LCSC : assortiment C0G, résistances, selfs, vignette, barrettes | 10 à 15 |
| Port DHL, 1 kg environ | 25 à 40 |
| **Total** | **240 à 380 USD** |

Soit 220 à 350 EUR hors taxes et **265 à 420 EUR TTC**. Le colis dépasse
150 EUR : il sort du guichet unique de TVA (IOSS), la TVA et les frais
de dédouanement du transporteur se paient à la livraison, ces derniers
de l'ordre de la quinzaine d'euros (non vérifié). Hors JLCPCB, voir le
paragraphe 8.3.

Variante économe : assemblage économique avec le module soudé à la main
et quatre lecteurs clones, environ 25 à 55 USD de moins.

### 8.5 Le jour de la commande

1. Deux à cinq jours ouvrés avant : relever le **stock JLCPCB** (pas
   seulement LCSC) et la colonne « PCBA Type » de chaque ligne ;
   vérifier l'avis d'arrivée des puces précommandées au lot 3 ; Global
   Sourcing pour ce qui manque encore (9 à 15 jours de plus, non
   annulable une fois payé).
2. `sha256sum -c` sur les deux archives, `python3 tools/fabcheck.py` qui
   doit dire **assembly ready** pour les deux cartes. `fabcheck` ne
   contrôle ni les en-têtes ni les rotations : vérifier aussi que
   `jlc-bom.csv` porte `Comment, Designator, Footprint, LCSC Part #` et
   `jlc-cpl.csv` `Designator, Mid X, Mid Y, Layer, Rotation`.
3. Relire `F.Paste` des deux cartes, sur lequel JLCPCB découpe le
   pochoir : fenêtres en damier sur la pastille centrale des quatre
   QFN-32 et du module, ouvertures réduites sur la XQFN-8 de la planche.
4. Téléverser les gerbers, régler les champs du 8.1 (format, nombre de
   conceptions, rails et mires, emplacement du numéro de commande),
   lancer l'analyse DFM de JLCPCB et lire chacun de ses avertissements ;
   expliquer en remarque l'absence voulue de plan de masse autour des
   boucles et les attaches de la planche.
5. Téléverser BOM et CPL. **Première approbation** : l'appariement des
   composants critiques (lecteurs, capteurs, module, multiplexeur, puce
   d'étiquette).
6. **Deuxième approbation** : l'aperçu de placement, contre la table des
   décalages de la note 23 (paragraphe 5) : SOT-23 et SOT-23-6 (+180°),
   SOT-223 du régulateur (+180°), QFN des lecteurs (+90°), SSOP-24 du
   mux, TSSOP-14 du tampon et XQFN-8 de l'étiquette (à vérifier un par
   un), centroïde du module, USB-C.
7. **Troisième approbation** : le prix final et l'adresse, chaque ligne
   du devis relue contre le paragraphe 8.4 (conceptions multiples,
   rails, gabarit d'assemblage, grande taille) ; un écart de plus de
   20 USD repasse par le paragraphe 11.
8. JLC3DP : téléverser les STL, choisir matière et couleur, dans le même
   panier.
9. **Quatrième approbation** : le paiement. Ces quatre approbations de
   la note 23 restent séparées (skill `operate-jlcpcb-order`) : aucune
   n'implique la suivante.
10. Ensuite seulement, la commande LCSC en envoi groupé (paragraphe 8.1).
11. Répondre dans la journée aux questions d'ingénierie de JLCPCB : la
    production les attend.
12. Noter dans le [journal](09-journal.md) la date, les options, les
    prix et les délais annoncés.

## 9. Ce qu'il faut écrire dans le dépôt

Les interfaces ci-dessous ont été écrites au lot 2 (12/10/2026), avec
les noms qu'elles portent dans le dépôt quand ils diffèrent de la
proposition ; ce qui relève des lots 4 à 9 (générateurs, micrologiciel,
mécanique) reste à écrire.

**yaml.** Une sous-section `hall_rfid.mockup` : grille de cases (2 x 2),
bande, marges, trous et rails ; les deux boucles (rapport au pas,
spires, piste, écart) et leur affectation aux colonnes ; garde de masse ;
lecteurs (pièce, MPN, LCSC par rangée), quartz, filtre CEM, impédance
visée et Q chargé ; capteurs (index dans `sensors`, décalage de l'amas
en fraction du pas) ; étiquettes (paroi, jeu, couches, piste, épaisseur,
puce et sa capacité, accords des variantes), avec les jeux
d'impression aujourd'hui en constantes de `mechanical/common.py` ;
brochage ; pièces imprimées ; quantités. Ailleurs : le décalage
admissible d'une pièce posée à la main (décision D14) ; la liste
`sensors` gagne le DRV5055A3 (le SS39ET y est déjà), et les deux valeurs
fausses du DRV5053OA sont corrigées ; le commentaire du multiplexeur
dit SSOP-24 ; `piece_magnet` reçoit les aimants achetés.

**chessboard_calc.**

| Fonction | Rôle |
|---|---|
| `nfc.antenna` corrigée | diamètre intérieur sans l'écart de trop (paragraphe 2, point 10), test contre le modèle par filaments à 2 % près |
| `nfc.loop_esr_ohm(cfg, p, loop)` | résistance de la boucle avec l'effet de peau |
| `nfc.matching(cfg, p, loop, tag) -> NfcMatching` | C0, C1, C2, Rq exacts et normalisés, R1 et R2 de réception, impédance obtenue avec et sans étiquette, courants, tension à `RX` |
| `nfc.tag_geometry(cfg, p, size)`, `nfc.tag_tuning(...)` | étiquette dérivée de la base et du pas, inductance deux couches, fréquence propre, variantes |
| `nfc.tag_activation(cfg, p, loop, tag, extra_gap)` | tension induite à la puce et marge, en remplacement de `h_margin` pour juger une étiquette |
| `nfc.neighbor_relay(cfg, p, loop, neighbor_loop, idle_state)` | flux sur la case voisine, direct et par la boucle voisine inactive |
| `nfc.metal_detune(cfg, p, loop, h_mm)` | désaccord par une plaque conductrice sous la carte (Q11) |
| `hall.offset_coverage(cfg, p, sensors)` | rayon de détection et couverture d'un amas de capteurs contre le décalage admissible |
| `chessboard_calc/hallrfid_mockup.py` | `layout(cfg)` (centres, boucles, couloirs, lecteurs, bande, arbre de masse), `check(cfg)` (ce qui tient aux deux pas, place des lecteurs, aucun anneau autour d'une boucle, hauteurs sous la plaque, trous hors des boucles), `power(cfg)` |

Le rapport (`python -m chessboard_calc report`) gagne une section
« maquette Hall + RFID ».

**Générateurs.** Dans `tools/boardgen` : épaisseur de carte dans `Spec`
(la planche fait 0,8 mm), zones interdites à la masse sans interdire les
pistes, pièces dessinées hors bibliothèque (les boucles), rails et mires
dessinés ; `nfcloop.py` (boucle carrée à pont arrière, pastilles
d'alimentation, liaison de net comme les amarres de spirale) ;
`blocks.py` (USB-C 16 broches tout CMS, circuit repris du cerveau sur
l'empreinte du candidat C2765186 ; le bloc du cerveau, USB4085-GF-A à
pattes traversantes, reste le repli) ; `hallrfid.py` (la carte) ;
`tag.py` (la planche, spirale à deux extrémités centrales, contours
circulaires et attaches, vignette). Sorties dans `hardware/hallrfid/` et
`hardware/tag/`, une carte par répertoire comme le lit `fabcheck`. Dans
`tools/analoggen` : une table des passifs par valeur et empreinte avec
leur code LCSC, qui refuse une valeur sans code (sinon `fabcheck` ne
peut pas conclure « assembly ready », note 22 point 11), et les
rotations et centroïdes du CPL.

**Micrologiciel.** `firmware/esp32/hallrfid/` : la logique de
`hallscan` déplacée dans `firmware/esp32/common/`, un pilote MFRC522 sur
un transport SPI abstrait, la séquence ISO 14443A (REQA, anticollision
sur deux niveaux, SELECT, CRC_A), la table UID vers pièce en NVS, la
console sur USB-Serial-JTAG et ses commandes de mise en route et de
mesure, qui écrivent les CSV de M12 à M14. La logique est testée sur PC
en CI (vecteurs CRC_A de la norme, lecteur simulé, ordonnanceur : un
seul émetteur, Hall lu émission coupée). Un job de CI compile le projet
ESP-IDF pour l'ESP32-S3 : ce serait le premier micrologiciel ESP32 du
dépôt à l'être.

**Mesures.** `measurements/protocol.md` gagne M12 à M14, chacune avec
son matériel, sa préparation, son acquisition et son critère, comme M1
à M11, et le tableau de synthèse gagne Q1 à Q11. Chaque mesure a son
gabarit dans `measurements/data/templates/` : pour M12, pièce,
diamètre, épaisseur et nuance réels de l'aimant, z mesuré au pied à
coulisse, décalage x et y, capteur, chemin direct ou mux, nombre
d'échantillons, moyenne et écart type en comptes, zéro, voie 9 ; pour
M13, case, boucle, lecteur, étiquette et variante, z, décalage, état des
voisins, conductance d'émission, essais, lectures réussies, courant
TVDD, lecture de la vignette. Les fonctions d'analyse vont dans
`measurements/analysis.py`, testées sur données synthétiques comme
celles de M1 à M11 : facteur d'échelle de M12a, rayon de détection de
M12b, seuil d'activation de M13a.

**Mécanique.** `mechanical/` : pièce à logement d'étiquette et aimant
amovible, plaque de surface, cales, escalier, gabarit de décalage ; les
jeux d'impression passent du code au yaml (ceux d'aujourd'hui sont
réglés pour le FDM).

**Tests.** Sans KiCad : géométrie, place des lecteurs aux deux pas,
réseau d'adaptation (impédance à 1 % près, désaccord des valeurs
normalisées inférieur à la demi-bande), étiquette dans la base et
accord, marge d'activation, couverture Hall, brochage, gardes qui
tirent. Avec KiCad : carte fermée, deux ou trois spires et leur pont
par boucle, aucun anneau de masse autour d'une boucle sur le cuivre
généré (deux faces et vias réunis, test topologique et non simple
recherche de masse à l'intérieur), garde respectée par les îlots des
lecteurs, un seul passage de trios Hall par boucle, archives cohérentes.

## 10. Lots, dans l'ordre

| Lot | Contenu | Critère de sortie | Effort |
|---|---|---|---|
| 0. Fusion et CI (fait le 11/10/2026) | fusionner la branche de la note 24 dans `main` (deux conflits additifs : `config/board.yaml`, sections `serie` et `hall_rfid` en fin de fichier, et `chessboard_calc/config.py`, classes `SerieCfg` et `Hall*`, `Nfc*` avant `BoardConfig` et leurs deux champs), supprimer la branche ; placer derrière un `skipif` les 8 tests qui lisent les bibliothèques KiCad (ils échouent déjà sur `main`) ou ajouter un job KiCad à la CI ; commiter cette note avec la fusion ou après elle, jamais avant | `ruff check .` et `pytest` verts en CI | 0,5 j |
| 1. Ce plan et les achats | valider cette note et les décisions du paragraphe 11 ; commander aimants et NanoVNA (paragraphe 8.3) | plan accepté, achats lancés | |
| 2. Modèle (fait le 12/10/2026) | yaml, `chessboard_calc` (dont la correction de `nfc.antenna`), rapport, tests ; protocole M12 à M14, gabarits et analyse | tests verts, valeurs marquées *(prél.)* des paragraphes 1, 2, 4 et 5 recalculées par le dépôt | 2 j |
| 3. Gel des pièces | chaque ligne : MPN, code LCSC, classe JLCPCB, stock du jour, dans `docs/prix-hallrfid.csv` ; relecture des fiches (broches de configuration et réception du MFRC522 NXP, fiches JSMSEMI et VRC522 comparées broche à broche, brochage de la NT3H2111, capteur) ; symboles et empreintes KiCad officiels disponibles ; précommande des puces d'étiquette | aucune ligne sans code, aucune en rupture, précommande passée | 1 j |
| 4. Outillage | KiCad 7.0.11 et CadQuery dans l'environnement (paquets Ubuntu joignables) | tests KiCad exécutés au lieu d'être sautés | 0,5 j |
| 5. Carte principale | extensions de `boardgen`, boucles, arbre de masse, carte, routage à la main de l'USB-C et des éventails QFN | build à zéro liaison ouverte, `tools/drc.py` à zéro erreur, rendu relu | 4 à 5 j, 8 à 10 s'il faut des passes à la main |
| 6. Planche d'étiquettes | `tag.py`, contours, attaches, vignette | idem, planche dans les limites JLCPCB | 1,5 j |
| 7. Micrologiciel | `hallrfid`, tests sur PC en CI, compilation ESP-IDF en CI | tests verts, compilation verte | 3 à 4 j |
| 8. Mécanique | pièces, plaque, cales, gabarits, sur les aimants mesurés | STL et STEP exportés, cotes épinglées | 1,5 j |
| 9. Dossier de fabrication | gerbers, empreintes `sha256`, `fabcheck` « assembly ready », manifeste (skill `release-pcba-fabrication`), revues (skills `kicad`, `emc`, `pcb-layout-review`) | archives et empreintes commitées | 1 j |
| 10. Commande | paragraphe 8.5 | commande passée, journal à jour | 0,5 j |
| 11. Mise en route et mesures | paragraphe 10.1, puis M12 à M14 | tableau de synthèse rempli, décisions de la note 24 tranchées | 1 à 2 j de mise en route, 1 à 2 d'accord, 4 à 6 de mesures |

Le lot 3 passe avant le lot 5 : les empreintes dépendent des pièces
retenues. Les lots 7 et 8 ne sont parallèles aux lots 5 et 6 que s'ils
sont menés par une autre session ; le lot 7 peut aussi se finir pendant
la fabrication. Le lot 5 est le plus incertain : la note 23
(paragraphe 4) montre l'horloge et la carte puissance encore ouvertes
et le quadrant 4 x 4 à 24 nets ouverts.

### 10.1 Mise en route

Préparée au lot 7 (commandes de la console) et écrite dans
`measurements/protocol.md` au lot 2 :

1. Contrôle visuel des quatre QFN et du module à la loupe ; 5 V et
   3,3 V contre la masse au multimètre, aucun court-circuit.
2. Première tension par les pastilles 5V, alimentation de laboratoire à
   5 V limitée à 150 mA : lecteurs en mise hors tension matérielle
   (`NRSTPD` tirées à la masse), rangées Hall coupées.
3. Flashage par l'USB-C (USB-Serial-JTAG, BOOT tenu à la mise sous
   tension si le module ne s'énumère pas) ; à défaut, UART0 par les
   points de test 43 et 44 et un adaptateur USB série 3,3 V.
4. Rangées Hall une à une, limite portée à 400 mA : 48 mA de plus
   pour huit DRV5055A3 (80 au plus) ; zéros relevés, un aimant passé à
   la main sur chaque capteur.
5. Lecteurs réveillés un à un, émission coupée : 13,5 mA de plus chacun
   (19 au plus), lecture de `VersionReg` (0x91 ou 0x92 chez NXP, valeur
   du clone notée).
6. Première émission d'un seul lecteur à conductance minimale, carte
   sur ses entretoises de 30 mm loin de tout métal, courant TVDD relevé ;
   lecture d'une carte NTAG213 du commerce, puis d'une étiquette P déjà
   lue au téléphone.
7. Accord au NanoVNA, puis seulement pleine conductance.

## 11. Décisions

Prises le 12/10/2026 : les quatorze, selon la recommandation. Le lot 2
en ouvre deux, D15 et D16, à la suite du tableau.

| # | Décision | Recommandation | Alternative |
|---|---|---|---|
| D1 | Ordre de la fusion de la note 24 (lot 0) | **avant la validation de ce plan** : CLAUDE.md impose de pousser sur `main` et de supprimer la branche ; cette note n'est commitée qu'avec la fusion ou après elle, puisqu'elle renvoie à la note 24 | aucune : garder la note 24 hors de `main` contredirait CLAUDE.md |
| D2 | Type d'assemblage de la carte principale | **Standard, module posé** | économique, module soudé à la main (20 à 50 USD de moins) |
| D3 | Capteur Hall | **DRV5055A3**, le mieux approvisionné des deux TI au relevé du 11/10/2026, choisi au lot 3 avec le SS39ET pour remplaçant ; la maquette mesure alors ses valeurs (6 mA, 175 µs), pas celles du DRV5053OA | DRV5053OA par Global Sourcing, pour garder le capteur que modélise la note 24, sa consommation (2,7 mA) et son démarrage (35 µs) |
| D4 | Lecteurs | **2 NXP et 2 clones** | 4 clones (environ 6 USD de moins) ; 4 NXP si la fiche du clone diffère |
| D5 | Boucles | **deux géométries, L60x3 et L70x2, par colonne** | une seule, L60x3 |
| D6 | Amas Hall de cinq capteurs sur A1 | **oui** : c'est la question qui conditionne la nappe 4 x 4. L'amas est un instrument de mesure : généralisé au plateau, il ferait 320 capteurs et 20 multiplexeurs, et, au modèle de la note 24 (balayage continu, quatre groupes), 216 mA et 26 h d'autonomie avec le DRV5053OA, 480 mA et 16,5 h avec le DRV5055A3, contre 51 h sans couche Hall (`hall.hall_power` à cinq capteurs par case) | un capteur par case |
| D7 | Étiquettes | **planche JLCPCB, P et G, trois accords de P, Murata en option** | étiquettes NTAG213 du commerce de 15 mm (hors JLCPCB, accord inconnu) |
| D8 | Quantités | **5 cartes dont 2 assemblées ; 5 planches dont 2 assemblées ; 6 pièces et 6 de rechange** | |
| D9 | NanoVNA | **l'acheter au lot 1**, avec sa sonde | accord à l'aveugle par le taux de lecture |
| D10 | Relevé des stocks LCSC et JLCPCB au lot 3 | **outillé** : accès réseau à `lcsc.com`, `jlcpcb.com` et `jlcsearch.tscircuit.com` depuis le poste qui exécute le lot 3, relevés datés dans `docs/prix-hallrfid.csv` | relevé à la main le jour de la commande |
| D11 | Erreurs de la note 24 | **les corriger au lot 2** (paragraphe 2), et noter dans la note 24 que la nappe 4 x 4 attend M12b | |
| D12 | Place des lecteurs et garde de masse | **dans les couloirs entre boucles, un lecteur face à sa boucle, garde de 4 mm** | garde de 2 mm (seule possible à p = 40) |
| D13 | Aimants | **ferrite d'une seule nuance, aimantation axiale, 12, 15 et 18 mm sur 4 mm, achetés et mesurés au lot 1** | diamètres du modèle sur commande spéciale |
| D14 | Décalage admissible d'une pièce posée à la main | **le fixer au lot 2**, provisoirement à ±8 mm (le carré que couvre l'amas au pas de 40, ±9,3 mm au pas de 50), et le revoir après M12b | le laisser ouvert : M12b donne alors une courbe sans décision |

**Ouvertes par le lot 2.**

| # | Décision | Recommandation | Alternative |
|---|---|---|---|
| D15 | Diviseur de réception R1 et R2 : à quel niveau d'émission le calculer | **au champ de service**, `RX` dans la fenêtre de `mockup.reader.rx_target_vpp` en service, avec une seconde empreinte de R1 en série, court-circuitée par un pont à souder qu'on ouvre pour les essais à pleine conductance (mise en route, accord, M13) : le nœud C0 varie d'un facteur 3 à 4 entre les deux régimes, et aucun diviseur fixe ne tient à la fois la fenêtre en service et les 4 V crête à crête à pleine conductance (paragraphe 4.4) | garder R1 calculé à pleine conductance, `RX` à 0,5 à 1 V crête à crête en service, et vérifier en M13 que le MFRC522 lit à ce niveau en relevant son gain de réception |
| D16 | Variante p = 40 : la boucle L60x3 n'atteint la marge de Q5 avec aucun trim d'étiquette au champ de service (P plafonne vers 1,96, G vers 1,46) | **boucles L70x2 dans les deux colonnes** de la variante p = 40, la seule boucle qui tient à ce pas (G + 10 pF compris) ; à trancher avec la variante, après M13 | garder L60x3 et rapprocher l'étiquette de la boucle (base plus mince), ou admettre une marge plus faible que M13a mesurera |

**Ce que chaque décision bloque.** D15 : lot 5. D16 : la variante p = 40. D1 : lot 0. D5, D6, D11, D12 et
D14 : lot 2. D3, D4 et D10 : lot 3. D2 : lots 5 et 9 (mires, rails,
module posé ou non). D7 : lots 6 et 8. D13 : lot 8. D8 : lot 10. D9 et
les achats hors JLCPCB se font au lot 1, pour que les aimants soient
mesurés avant le lot 8 et l'appareil là avant la livraison.

## 12. Risques et parades

| Risque | Parade |
|---|---|
| Une pièce manque au stock JLCPCB le jour de la commande (capteur, puce d'étiquette, multiplexeur, NXP non recommandé, clone arrêté) | remplaçants à la même empreinte (SS39ET, NT3H2211, VRC522) ; précommande au lot 3 ; Global Sourcing |
| L'accord des boucles est faux (inductance à 5 ou 10 % près ; plan de masse à 4 mm et pont non modélisés) | première émission à conductance réduite, courant TVDD lu sur sa résistance ; boucles mesurées seules sur les cartes nues ; C0G à ±2 %, empreintes de retouche, assortiment de C0G, NanoVNA |
| La garde de masse et le lecteur, à 4 mm de la boucle, en abaissent le Q ou la désaccordent | impédance de la boucle seule sur une carte nue, puis entourée de son lecteur sur une carte assemblée (NanoVNA, M13) |
| Le clone diffère du NXP (brochage, `VersionReg`, registres de test) | fiches comparées au lot 3 ; le micrologiciel n'emploie que les registres communs ; brochage différent : quatre NXP (D4) |
| Une pièce voisine répond par le relais de sa boucle inactive | un seul émetteur, voisins dans l'état où la fiche tient TX1 et TX2 à 0, champ de service sous 7,5 A/m, anticollision complète et recoupement avec la couche Hall |
| La carte est mesurée sur une table métallique | entretoises de 30 mm, consigne du paragraphe 1 ; Q11 mesure l'effet |
| Le module ne démarre pas | barrette d'échappement et cavalier sur EN, DevKitC ; UART0 par les points de test |
| Le routage automatique échoue sur l'USB-C (déjà vu sur l'horloge, note 23) | éventails et USB-C dessinés à la main, comme `hand.py` du quadrant ; lot 5 compté jusqu'à 10 jours |
| L'étiquette P est trop faible | variantes d'accord, étiquette G, Murata en option ; la marge est mesurée et non supposée |
| Soudure de la XQFN-8 ratée sur une partie des étiquettes | 34 étiquettes pour 6 pièces ; chaque étiquette lue au téléphone, UID noté, avant d'entrer dans une pièce |
| Planche de 0,8 mm qui plie ou casse au montage | attaches au guide JLCPCB, rails de 5 mm, trois planches nues de rechange |
| Décharges électrostatiques sur les étiquettes nues | manipulation par la tranche, rangement en sachet antistatique |
| Plaque SLA voilée | planéité relevée en neuf points avant M12 ; z de chaque mesure relevé, non supposé |
| JLCPCB met la commande en attente sur une question d'ingénierie | répondre dans la journée ; remarques jointes à la commande (paragraphe 8.5, étape 4) |
| Rotations du CPL | table des décalages de la note 23, deuxième approbation |
| Le champ dépasse le maximum ISO | champ de service ramené sous 7,5 A/m par le micrologiciel, vérifié à la vignette |
| Émetteur à 13,56 MHz | la maquette est un banc de laboratoire, non mis sur le marché ; un plateau à 64 émetteurs relèverait de la directive RED (EN 300 330 et EN 301 489-3), à chiffrer dans la décision RFID |
| KiCad absent de l'environnement de travail | lot 4 |

## 13. Sources

Relevés par recherche web le 11/10/2026, non vérifiés au panier :

- Capteurs : [fiche TI DRV5055](https://www.ti.com/lit/gpn/drv5055),
  [sensibilités du DRV5055 à 3,3 V](https://www.ti.com/document-viewer/lit/html/SLIA086A/GUID-D7997616-429F-4C5B-9786-7D0EA94BBBD4),
  [DRV5055A3 C266128](https://www.lcsc.com/product-image/C266128.html),
  [SS39ET C126669](https://jlcpcb.com/partdetail/SS39ET/C126669),
  [fiche TI DRV5053](https://ti.com/document-viewer/DRV5053/datasheet/GUID-9040AE2C-EF9D-4EFA-8EE3-9D97046A4D65),
  [CD74HC4067SM96](https://ti.com/product/CD74HC4067/part-details/CD74HC4067SM96).
- Lecteurs : [fiche NXP MFRC522](https://nxp.com/docs/en/data-sheet/MFRC522.pdf),
  [JSMSEMI MFRC522 C2760772](https://jlcpcb.com/partdetail/JSMSEMI-MFRC522/C2760772),
  [NXP MFRC522 C11322](https://www.lcsc.com/product-detail/C11322.html),
  [VRC522 C968718](https://jlcpcb.com/partdetail/VIBRATION-VRC522/C968718),
  [MISO de plusieurs MFRC522](https://community.nxp.com/t5/NFC/MFRC522-Multiple-SPI/m-p/799661).
- Étiquettes : [fiche NXP NT3H2111](https://www.nxp.com/docs/en/data-sheet/NT3H2111_2211.pdf),
  [NT3H2111W0FHKH C710403](https://jlcpcb.com/partdetail/NxpSemicon-NT3H2111W0FHKH/C710403),
  [Murata LXMS33HCNK-171 C17590014](https://www.lcsc.com/product-detail/C17590014.html).
- Module et alimentation : [ESP32-S3-WROOM-1-N8, Standard seulement](https://jlcpcb.com/partdetail/3198296-ESP32_S3_WROOM_1N8/C2913198),
  [fiche ESP32-S3-WROOM-1](https://documentation.espressif.com/esp32-s3-wroom-1_wroom-1u_datasheet_en.html),
  [fiche AMS1117](https://files.waveshare.com/upload/b/b8/AMS1117-datasheet.pdf).
- JLCPCB : [prix de l'assemblage](https://jlcpcb.com/help/article/pcb-assembly-price),
  [capacités d'assemblage](https://jlcpcb.com/capabilities/pcb-assembly-capabilities),
  [surcoûts, dont les conceptions multiples](https://jlcpcb.com/help/article/In-what-cases-will-there-be-charged-extra),
  [Global Sourcing](https://jlcpcb.com/help/article/60-how-to-use-jlcpcb-global-sourcing-parts-service),
  [précommande](https://jlcpcb.com/help/article/what-is-jlcpcb-parts-pre-order-service),
  [OSP gratuit, ENIG payant](https://jlcpcb.com/news/jlcpcb-pcb-osp-finish),
  [attaches à trous](https://jlcpcb.com/blog/mouse-bite-panelization-guide),
  [TVA européenne](https://jlcpcb.com/help/article/EU-VAT-E-commerce-Rules-%26-Adjustments).
- LCSC : [envoi groupé avec JLCPCB](https://www.lcsc.com/faqs/ordering-quotation/combine-lcsc-jlcpcb-orders).
- JLC3DP : [capacités](https://jlc3dp.com/capabilities/3d-printing-service),
  [règles de conception](https://jlc3dp.com/help/article/3d-printing-design-guideline).

Les calculs préliminaires (boucles, adaptation, étiquette, relais par
la boucle voisine, couverture hors centre, effet du métal, place des
lecteurs) ont été refaits par le dépôt au lot 2 (`chessboard_calc` :
`nfc`, `filament`, `hall`, `hallrfid_mockup`) ; les scripts de
préparation et de relecture ne sont pas versionnés.
