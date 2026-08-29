# ADR 0006. Pas de case paramétrique, 40 ou 50 mm

Statut : ouverte, à trancher sur la maquette.

## Contexte

Le pas conditionne l'encombrement, le coût (~120 EUR d'écart),
l'inertie mobile (moitié moindre à 40 mm) et le confort de jeu. La
contrainte L = 45 µH impose plus de tours quand le diamètre de bobine
baisse, ce qui compense presque la perte géométrique de couplage.

## Décision

Aucun pas n'est figé. Tout le dépôt est paramétrique sur `p` :
`config/board.yaml` porte les deux candidats (40 et 50 mm) et des
ratios plutôt que des millimètres ; générateurs PCB, modèles 3D et
firmware lisent ce fichier. La maquette est à p = 50, imposé par le
palier tarifaire 100 x 100 mm.

## Conséquences

- La CI vérifie la contrainte de couloir et les fenêtres de bobinage
  pour les deux pas à chaque commit.
- Éléments chiffrés au jour de la décision (rapport
  `python -m chessboard_calc report`) : le modèle de premier ordre
  donne un signal à p = 40 autour de 70 % de celui à p = 50 (le brief
  annonçait moins 5 % ; à vérifier en mesure 4), et surtout des Q de
  bobine estimés à 13 / 23 pour le pion p = 40 en fil plein contre
  33 / 57 à p = 50 : le bas de bande à p = 40 exigerait probablement
  du fil de Litz (lecture critique, C).
- En dessous de 30 mm le sujet devient le Q et le confort de bobinage,
  hors périmètre.
