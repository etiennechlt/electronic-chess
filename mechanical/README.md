# Mécanique de la maquette (CadQuery)

Modèles paramétriques pilotés par `config/board.yaml`. Construction :

```bash
.venv/bin/python mechanical/build_all.py     # STL + STEP dans exports/
```

## Pièces produites

- `puck-<classe>-black` : pucks de test des 4 résonateurs bas de bande
  (pion, cavalier, fou, tour noirs). Alésage étagé par le dessous :
  logement bobine (2 mm), poche aimant ferrite ajustée, fente latérale
  pour le condensateur C0G et son accès de soudure. Impression tête en
  bas, 0,2 mm, sans support.
- `jig-core-d*` et `jig-washer-d*` : gabarits de bobinage, un par
  diamètre de bobine distinct. Le noyau donne le diamètre intérieur,
  les flasques l'épaisseur de 2 mm ; axe M3, encoche de sortie de fil.
  Monter le noyau dans une perceuse ou un petit tour, bobiner, coller
  au vernis, retirer la rondelle.
- `magnet-bracket-base` et `magnet-cup` : support d'aimant réglable
  sous la case S3 de la carte bobines. La platine se visse aux 4 trous
  M3 espacés de 34 mm, l'écrou central capture une vis M3 qui monte ou
  descend la coupelle porte-aimant (mesure 7 : distance de parking).

Quincaillerie : vis M3 x 8 (platine), M3 x 30 + 2 écrous (réglage),
entretoises M3 x 25 pour la carte bobines.

Les exports STL/STEP sont regénérés à la demande et ne sont pas
commités (`.gitignore`).

## Gabarit de perçage de la surface

`surface-template` reprend le contour de la carte bobines avec les
quatre trous de visserie et les deux points lumineux par case au
droit des LED de camp (ADR 0009). L'imprimer à plat (ou exporter le
DXF), le scotcher sur le contreplaqué et percer au travers ; les
points lumineux font `leds.light_hole_d_mm` (2,5 mm), à remplir
d'époxy translucide si l'on veut une surface affleurante.
