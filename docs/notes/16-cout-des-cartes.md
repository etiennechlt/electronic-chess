# 16. Coût des cartes : quadrant, format 100 x 100 et décisions à prendre avant de chiffrer

État d'une réflexion ouverte au 07/09/2026. Rien ici n'est décidé :
la note garde les faits établis, les pistes examinées et l'ordre dans
lequel les décisions doivent tomber, pour que la discussion reprenne
là où elle s'est arrêtée. Les cotes viennent de `config/board.yaml`
(sections `plateau`, `measurement`, `gap`).

## 1. Le poste qui motive la réflexion

Le quadrant : 220 x 200 mm en 4 couches (4 p plus la bande de frontal
de 20 mm, sur 4 p), quatre exemplaires par plateau, et un minimum de
commande de cinq pièces chez JLCPCB. L'[ADR 0004](../adr/0004-four-quadrant-sensing-pcb.md)
chiffrait le jeu de quadrants entre 80 et 120 EUR, la
[note 10](10-plateau-8x8-et-horloge.md) une commande de cinq
quadrants entre 40 et 80 USD : deux ordres de grandeur d'avant le
frontal embarqué et la bande de 20 mm, à remplacer par un devis. Le
devis JLCPCB exact n'a pas encore été demandé : c'est le préalable à
toute décision, et il se fait sur le quadrant tel quel (contour et
empilement actuels, nets ouverts ou non, le prix n'en dépend pas),
avec le skill `operate-jlcpcb-order` de la
[note 15](15-skills-embarques.md).

## 2. Décision amont : différentiel vrai ou single-ended

Le frontal actuel est câblé en différentiel vrai : deux ADG1607
(double 8 vers 1) amènent les deux bornes de la bobine sur l'AD8421.
En single-ended il faut moitié moins de voies de mux (ADR 0004) et un
étage d'entrée plus simple : le frontal maigrit, la bande de frontal
avec lui, et toute l'arithmétique du découpage change. Ce point est
ouvert depuis l'ADR 0004, qui le renvoyait à la mesure 8 sur la
maquette (cavalier pseudo-différentiel). Trois choses ont bougé
depuis :

- la maquette n'est plus construite (ADR 0010) ;
- la M8 du [protocole](../../measurements/protocol.md) telle
  qu'écrite compare LDO, buck et radio, pas les deux câblages
  d'entrée ;
- le frontal du quadrant n'a pas de cavalier single-ended
  (`tools/quadgen/circuit.py`, entrées de l'AD8421 prises sur les
  deux sorties de mux).

La mesure qui tranche reste donc à définir, sur le quadrant ou sur un
banc réduit ; tant qu'elle n'est pas faite, chiffrer un découpage
revient à chiffrer un frontal qui peut changer.

## 3. La piste des tuiles 100 x 100 mm

Seize tuiles de 2 x 2 cases, dans le palier tarifaire le plus bas
(celui de la carte bobines de la maquette, ADR 0006 et 0008). Points
établis lors de l'analyse du 07/09 :

- À p = 50, une tuile 2 x 2 fait exactement 100,00 mm : aucune place
  pour la bande de frontal de 20 mm, et le dessous doit rester vierge
  (ADR 0010, décisions 4 et 6). Une tuile 100 x 100 ne peut donc pas
  porter son frontal analogique.
- Conséquence : le signal brut de bobine (quelques centaines de µV,
  sur la même paire que l'impulsion de 12 V limitée à 2 A,
  `measurement.drive`) traverserait un connecteur avant
  amplification. C'est ce que l'ADR 0004 et la décision 2 de
  l'ADR 0010 ont refusé, et ce que la note 10 écarte sous le nom de
  « quadrants passifs et frontal centralisé ».
- La surface de cuivre est presque la même dans les deux découpages :
  16 x 100 cm² contre 4 x 440 cm². L'économie porte sur le supplément
  grand format, à mettre en regard de seize connecteurs, seize nappes
  et l'alignement de seize cartes sur 400 mm.
- Les nappes de tuile devraient traverser l'aire des bobines dans
  l'entrefer de 2 mm (`gap.air_mm`), donc passer au-dessus de
  spirales voisines, avec `measurement.crosstalk_max_db` à -20 dB à
  tenir.

Variantes évoquées et non tranchées :

| Variante | Format | Ce qu'elle change |
|---|---|---|
| Demi-quadrant 4 x 2 | 220 x 100 mm | huit cartes qui gardent leur bande de frontal ; à chiffrer |
| Quadrant sans bande | 200 x 200 mm | frontal déporté dans la cavité de la base ; le signal brut traverse alors une nappe, à confronter à la même objection qu'aux tuiles |
| Rigide-flexible | | écartée sur le coût |

## 4. Piste connexe : le quadrant intelligent

Un STM32G431 par quadrant, qui excite, mesure et convertit sur place ;
la nappe vers le cerveau devient entièrement numérique et n'emporte
plus de signal analogique. Quatre MCU au lieu des seize qu'exigeraient
des tuiles intelligentes. Jugée plus rentable que le passage aux
tuiles ; à instruire dans une ADR séparée, avec le partage des rôles
entre le G431 du quadrant et le G474 du cerveau et le protocole sur
la nappe.

## 5. Point de vigilance sur la nappe actuelle

Sur la nappe du quadrant (`plateau.quadrant.link.pinout`), `AMP_OUT`
est en broche 4 et `LED_DIN` en broche 7. Les trames WS2812 (800 kbit/s,
donc un spectre qui recouvre la bande de mesure de 200 à 650 kHz,
`measurement.band_hz`) ne doivent jamais partir pendant une mesure.
L'exclusion est structurelle côté firmware (boucle mono-tâche,
`measure_square()` synchrone, [note 06](06-firmware.md)) et vérifiée
par la mesure M11 : c'est une garantie logicielle posée sur un
couplage physique, à garder en tête dans tout nouveau brochage, et un
point que la nappe entièrement numérique du quadrant intelligent
(section 4) ferait disparaître.

## 6. Ordre des décisions

1. Devis JLCPCB du quadrant tel quel (cinq pièces, 4 couches, avec et
   sans assemblage) : le chiffre de référence.
2. Différentiel vrai ou single-ended, et la mesure qui le tranche.
3. Sur cette base, chiffrer les découpages restés en lice contre le
   quadrant actuel, connecteurs et nappes compris.
4. ADR du quadrant intelligent si la piste tient.
