# Planche d'étiquettes NFC du démonstrateur Hall + RFID

Carte générée par `python -m taggen build` depuis `config/board.yaml`
(`hall_rfid.mockup.tags`, `hall_rfid.demo.tags`, `hall_rfid.mockup.pickup`)
et le modèle d'étiquette de `chessboard_calc.nfc` (`tag_geometry`,
`tag_tuning`). Ne pas éditer le `.kicad_pcb` à la main : modifier le
yaml ou le générateur, puis regénérer. La fonction, le montage et les
mesures sont dans la [note 27](../../docs/notes/27-demonstrateur-hall-rfid.md).

## Ce que porte la planche

- **100 x 86,5 mm, 2 couches, FR-4 0,8 mm**, rails de 5 mm sur les
  deux grands côtés et barres de 3 mm en haut et en bas, trois mires
  sur les rails.
- **15 étiquettes rondes**, trois de chaque variante, tenues par des
  attaches de 2,5 mm à trous de souris (0,5 mm au pas de 0,75) : la
  rupture se fait au bord du disque, sans ergot.

  | Variante | Disque | Bobine | Accord (modèle) | Pour quelle base |
  |---|---|---|---|---|
  | P | 14,5 mm | 5 + 5 spires, piste et écart 0,20 mm | 17,3 MHz | pion, cavalier, fou (bases de 17,5 à 20 mm à p = 50) |
  | P + 15 pF | 14,5 mm | idem | 15,2 MHz | compromis de la note 25 |
  | P + 22 pF | 14,5 mm | idem | 14,5 MHz | la meilleure marge d'activation, jamais à pleine conductance |
  | G | 19,5 mm | 4 + 4 spires | 16,1 MHz | tour, dame, roi (bases de 22,5 mm) |
  | G + 10 pF | 19,5 mm | idem | 14,7 MHz | la seule G qui tient au pas de 40 |

  Chaque disque : la spirale de la face avant part du centre vers le
  bord, un via au bord, la spirale de la face arrière revient vers le
  centre ; les deux extrémités arrivent sur les broches LA (1) et LB
  (8) de la puce **NT3H2111W0FTTJ** (NXP NTAG I2C plus, TSSOP8,
  soudable au fer), posée au centre ; un condensateur 0402 C0G d'accord
  entre LA et LB, monté sur les variantes qui en portent un. Les broches
  I2C, FD, VCC, VSS et VOUT restent en l'air : la puce vit du champ du
  lecteur. Le disque entre dans l'alésage de la base d'une pièce, puce
  vers le haut, tenu par un ruban polyimide (note 25, paragraphe 5).
- **La vignette de champ** (17 x 14,5 mm, en bas à droite) : une bobine
  de 10 mm à 2 + 2 spires, une diode Schottky à faible seuil
  (BAT15-03W, SOD-323), 1 nF et 100 kΩ en charge, deux pastilles pour
  les fils torsadés vers l'entrée `PICKUP` de la carte principale. Les
  trois composants se soudent à la main. Étalonnée contre le NanoVNA,
  elle donne une mesure relative du champ sans oscilloscope.

## Nomenclatures

`bom.csv` liste les 15 puces, les 9 condensateurs d'accord montés (3 x
10 pF, 3 x 15 pF, 3 x 22 pF), les 6 emplacements non montés et les trois
composants de la vignette. `jlc-bom.csv` et `jlc-cpl.csv` ne portent que
les lignes à code LCSC : le code de la puce en TSSOP8 et ceux des 0402
C0G sont à relever au panier (la puce en XQFN8, C710403, est l'autre
option si JLCPCB doit poser les puces : même brochage, empreinte à
changer dans le générateur). Sans assemblage, la planche se commande
nue et les puces se soudent au fer : 0,65 mm de pas, flux, une broche
d'ancrage puis les autres.

## Régénérer et vérifier

```bash
PYTHONPATH=tools .venv/bin/python -m taggen build --render docs/images/tag-demo.png
/usr/bin/python3 tools/drc.py hardware/tag-demo/tag-demo.kicad_pcb
/usr/bin/python3 tools/gerbers.py hardware/tag-demo/tag-demo.kicad_pcb
cd hardware/tag-demo && sha256sum -c tag-demo-gerbers.sha256
```

DRC KiCad 7.0.11 sur le fichier commité : zéro erreur, zéro élément
non connecté (les avertissements restants sont les chemins de
bibliothèque des empreintes et quelques repères de sérigraphie sur la
vignette). `tag-demo-gerbers.zip` se dépose tel quel chez JLCPCB :
2 couches, 0,8 mm, HASL, « Panel by Customer », quatre conceptions
déclarées (P, G, vignette et le cadre), 5 pièces. Options écran par
écran dans la note 27.
