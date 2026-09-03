# Quadrant 4 x 4 : carte de détection du plateau 8 x 8

![Quadrant 4 x 4](../../docs/images/quadrant.png)

Carte générée par `tools/quadgen` depuis `config/board.yaml`
(ADR 0010). Quatre exemplaires identiques dallent l'aire de jeu ; la
paire de droite est montée tournée de 180 degrés, ce qui laisse la
diagonale des LED inchangée et met la bande de frontal au bord extérieur.

## Ce que contient la carte

- 216 x 200 mm, 4 couches : 16 mm de bande de frontal à l'ouest, puis
  quatre colonnes de cases de 50 mm.
- 16 spirales de détection (4 couches en série, 5 tours par couche,
  piste 1,6 mm), bornes empilées au nord des rangées impaires et au
  sud des rangées paires : chaque paire de rangées s'échappe dans le
  couloir qui les sépare (« bande »), huit voies par bande, vers les
  cellules du frontal, borne A sur F.Cu et borne B sur B.Cu.
- 32 WS2812B aux coins NO et SE de chaque case, un 100 nF chacune,
  vias latérales, chaîne de données sur In1 en serpentin (rangée 0 vers
  l'est, rangée 1 vers l'ouest, et ainsi de suite), grille 5 V sur
  In2, masse sur B.Cu (bords nord et sud, couloir médian) reliée au
  bus de la bande sur In1. Chaîne et retours sont routés par un A* sur
  grille de 0,2 mm contre tout le cuivre déjà posé.
- Connecteur FPC 16 broches 0,5 mm (Hirose FH12, 1,4 mm de haut, câble
  sortant à l'ouest), brochage dans `plateau.quadrant.link.pinout`.
- Trou de pion de centrage en bas de la bande, deux trous de fixation
  M3 au bord est, dans les zones libres de vias LED.

Le contrôle d'isolement exact (shapely) tourne à chaque build et le
projet KiCad porte les règles du générateur ; `kicad-cli` 7 n'a pas de
DRC en ligne de commande, lancer celui de KiCad 9 après ouverture. Le
build échoue si une route de la chaîne LED, un retour d'alimentation ou
un net du frontal reste ouvert : la liste imprimée est ce qu'il reste à
fermer dans pcbnew.

## Le frontal de la bande

- 16 cellules de 7,4 mm en face de leur bobine, réparties de part et
  d'autre de chaque bande d'échappée : bleed 10 k vers VREF, 330 ohms
  et BAV99 devant le mux, diode de bus B5819W et AO3400A d'excitation,
  SS34FL de roue libre (SOD-123F, 1 mm de haut), AO3401A et 680 ohms
  d'amortissement, pulldowns 0402. L'entrée A arrive sur F.Cu à
  y - 0,6, l'entrée B sur B.Cu à y + 0,6 avec sa via.
- Zone médiane de 43,8 mm : 74HC4514 (excitation, inhibé par PULSE_EN
  à travers un 74LVC1G04) et 74HC154 (amortissement, validé par
  DAMP_EN_N), deux ADG1607 (bobines 1 à 8, 9 à 16, sorties en
  parallèle, un enable chacun, bus d'adresses A0..A2 partagé), AD8421
  G = 20, OPA2810 en Sallen-Key passe-haut et passe-bas, OPA2810 en
  tampon VREF et étage de sortie, écrêtage vers 3V3 et RC de sortie.
- Zone du milieu (43,8 mm entre les deux groupes de cellules, ancrée
  aux bandes d'échappée) : les deux décodeurs TSSOP l'un sous l'autre
  sur l'axe de la bande, les deux mux LFCSP côte à côte décalés d'un
  demi-pas pour que leurs vias d'éventail s'intercalent, les
  amplificateurs dessous ; les passifs occupent les colonnes que les
  éventails laissent libres de part et d'autre des décodeurs, sous le
  FPC et à côté de l'étage de sortie.
- Zone du connecteur (25,7 mm) : FPC 16 broches, commutateur de rail
  d'impulsion (AO3401A, AO3400A, 10 ohms 2010), réserve 10 µF ; les
  points de test sont dans les colonnes latérales.
- Bus sur In1 côté est : 5VA, VREF, DRIVE_BUS, VIN et GND ; 3V3 et
  5V_LED sur In2. Les lignes de mesure M{k} vers les mux et les lignes
  de grille des décodeurs sont routées par le routeur A* multicouche,
  puis un contrôle d'isolement exact valide toute la carte.
- Les bobines sont des « net ties » (`quadgen:COIL_TIE`) : couches 1
  à 3 et deux vias sur C{k}_A, couche 4 et échappée B sur C{k}_B, la
  jonction In2 vers B.Cu portant les deux nets. Le schéma montre le
  même NT{k}.

Sorties du build : projet KiCad avec schéma, `bom.csv`, `jlc-bom.csv`
(lignes avec code LCSC), `jlc-cpl.csv`, `chain-spice.cir`.

## Régénérer

```bash
PYTHONPATH=tools .venv/bin/python -m quadgen build --render docs/images/quadrant.png
```

## Résultat du build

Généré par `python -m quadgen build` :

| Bobines | LED | Segments | Vias | Routes LED et alimentation ouvertes | Nets du frontal ouverts | Défauts d'isolement |
|---|---|---|---|---|---|---|
| 16 | 32 | 31765 | 560 | 0 | 8 | 0 |

Nets du frontal à finir dans pcbnew : MUXB_OUT, RG_A, INA_INM, RG_B, INA_INP, AMP_OUT, VREF, GND. VREF alimente
les 16 cellules depuis son bus In1 : c'est la liaison du bus à la
référence elle-même qui manque, une seule piste. GND concerne une
broche sans descente vers le plan.

Le contrôle d'isolement exact ne signale aucun défaut. Les vias
d'éventail des boîtiers fins font 0,45 mm (perçage 0,2 mm), à
confirmer avec le fabricant avant commande.
