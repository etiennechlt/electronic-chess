# Quadrant 4 x 4 : carte de détection du plateau 8 x 8

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
DRC en ligne de commande, lancer celui de KiCad 9 après ouverture.

## Ce qui reste (bloc suivant)

Les cellules du frontal (16 cellules de 8,5 mm : FET d'excitation et
d'amortissement, diodes, résistances), l'ADG726, les décodeurs 74HC4514
et 74HC154, la chaîne AD8421 plus Sallen-Key, avec leur schéma, leur
placement et leur routage. Les sorties A et B de chaque bobine
arrivent déjà à l'entrée de leur cellule (`strip.cell_entry_x_mm`).

## Régénérer

```bash
PYTHONPATH=tools .venv/bin/python -m quadgen build --render docs/images/quadrant.png
```
