# Carte bobines de la maquette 2 x 2

Carte 100 x 100 mm, 4 couches, entièrement générée par
`python -m coilgen build` depuis `config/board.yaml`. Ne pas éditer le
`.kicad_pcb` à la main : modifier le yaml ou le générateur, puis
regénérer.

## Contenu

- 4 spirales de détection (S1 à S4 au pas de 50 mm) : 5 tours par
  couche, 4 couches en série, piste 1,60 mm, espace 0,15 mm, environ
  16 µH par bobine, bornes empilées verticalement et routées en paire
  vers le connecteur.
- Connecteur J1, barrette 1 x 10 au pas 2,54 (ordre des broches :
  GND, C1A, C1B, C3A, C3B, C4A, C4B, C2A, C2B, GND), à souder bord à
  bord avec la carte analogique.
- 4 trous de fixation M3 aux coins (entretoises de 25 mm pour arriver
  au niveau du shield Nucleo).
- 4 trous M3 espacés de 34 mm autour de S3 pour le support d'aimant
  réglable imprimé (répertoire `mechanical/`).

## Ouvrir

`coil-board.kicad_pro`, généré avec la carte, est le fichier à ouvrir
dans KiCad ; il porte la classe de nets et les minima du DRC issus du
yaml : garde 0,13 mm, piste d'interconnexion 0,5 mm, vias 0,6/0,3 mm
pour les bobines et 0,8/0,4 mm pour les LED, cuivre à 0,5 mm du bord.
La carte n'a pas de schéma : elle est purement passive et toute sa
connectivité tient dans le `.kicad_pcb`.

## Fabrication

`sh hardware/mockup-2x2/coil-board/export.sh` regénère la carte et
produit `coil-board-gerbers.zip` (gerbers + perçage Excellon).
Paramètres de commande JLCPCB : 4 couches, 1,6 mm, cuivre 1 oz,
finition au choix, reste par défaut. Aucun assemblage : la carte est
purement passive.
