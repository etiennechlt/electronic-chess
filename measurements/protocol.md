# Protocole de mesure de la maquette 2 x 2

Objectif : trancher les incertitudes du brief (section 6, mesures 1 à
8) plus les extensions issues de la lecture critique. La mesure 2
valide ou invalide le pivot de l'architecture (aimant ferrite), la 4
oriente le choix du MCU, la 7 dimensionne l'interlock, la 8 arbitre
l'alimentation.

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

Pucks complets, entrefer nominal (PCB + 3 mm d'acrylique + feutre).
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
