# 09. Journal des décisions et pivots

Chronologie condensée, source : l'historique git (`git log --reverse`)
et les ADR. Les entrées gardent le pourquoi, pas le détail (le détail
est dans les notes 03 à 06).

## 29/08/2026, fondations (phase 0)

- Socle : `board.yaml` unique source, `chessboard_calc`, garde-fou
  couloir bloquant en CI, conventions du dépôt (français, pas de
  tirets longs, travail sur `main`).
- Décisions structurantes posées en ADR : résonateurs LC passifs
  (0001), **aimants pièces en ferrite et jamais néodyme** (0002, la
  décision pivot du projet), STM32 maître et Pi optionnel (0003),
  détection PCB quatre quadrants (0004), architecture d'alimentation
  et de bruit (0005), pas p ouvert 40/50 paramétrique (0006), double
  voie d'extraction FFT plus période (0007).

## 29/08/2026, la maquette prend forme

- ADR 0008 : maquette en deux cartes ; le mux pressenti ADG709 est
  écarté au profit du **74HCT4052** (seuils TTL pilotables par un MCU
  3,3 V sur un rail 5 V), excitation hors mux par FET dédié.
- `coilgen` : spirales 4 couches en série ; leçon : les jonctions
  inter-couches alignées sur le rayon du terminal superposaient les
  vias, d'où les arcs de liaison à 90 degrés. Les trous du support
  d'aimant passent de 30 à 34 mm pour ne pas percer la spire externe.
- Firmware compilable (CMSIS nu), mécanique CadQuery, protocole M1 à
  M9, visuels, tests analoggen : la phase 1 est presque complète en
  une journée, sauf le routage.

## 29 au 30/08/2026, la bataille du routage

Progression des liaisons ouvertes de la carte analogique : 57, 51,
46, 40, 21, 16, 12, 9. Les jalons :

- Rasterisation conservative et marquage du cuivre à l'étendue vraie ;
  marge de routage relevée contre l'arrondi de grille.
- Méthode des **seeds répétés hors build** contre la géométrie réelle
  des pads, avec gardes au build (note 05) ; leçons payées : rayon des
  vias contre les rails, moignons de sortie, croisements seed contre
  seed.
- **Passe de garantie** : tout cuivre sous la garde de fabrication est
  retiré et réouvert en chevelu ; la carte part toujours DRC zéro.
- **Autopsies géométriques exactes** du cuivre pré-retrait : trois
  trous de légalité réels identifiés et corrigés à la racine (frange
  de raster des cellules de départ, couloir own par les marques de
  pistes, moignons de masse trop larges) ; deux impasses essayées puis
  annulées (entrée cible libre, puis bornée).
- Constat de **saturation** : chaque seed supplémentaire dans la bande
  des cellules déplaçait plus de nets qu'il n'en fermait ; gel à 18
  restes, puis la **passe de finition à géométrie exacte** (note 04)
  les ramène à 9. L'histoire du canal de 0,52 mm : la garde passe de
  0,137 à 0,132 parce que 0,524 exigés dépassaient de quatre microns.

## 30/08/2026, approvisionnement

Fiche comparée Europe contre Asie, prix relevés et datés.
Enseignements chiffrés : AD8421 à moitié prix chez LCSC (3,69 contre
8,91 USD), ADuM1201 en rupture DigiKey mais plus de 11 000 en stock
LCSC, et le contre-exemple : la Nucleo est moins chère et plus sûre en
Europe (eStore ST) qu'en revendeur asiatique. Panaché conseillé en
quatre commandes.

## 01/09/2026, LED de camp et surface bois (ADR 0009)

- Demande produit : deux points lumineux par case indiquant le camp
  occupant, sur une surface en bois (référence visuelle : plateaux du
  commerce à points aux coins).
- Choix : 2 WS2812B par case aux coins opposés (un coin partagé entre
  deux cases de camps opposés serait ambigu), chaîne unique extensible
  au 8 x 8 ; analyse bois : effet nul sur la fréquence, seuls comptent
  l'épaisseur et l'humidité (mesure M10 ajoutée).
- Intégration : couloirs In1/In2/B de la carte bobines (note 05),
  joint porté à 12 broches, tampon 74AHCT1G125 côté analogique
  (déplacé près du connecteur MCU après un premier placement qui
  faisait échouer LED_DIN), pilote bit-bang DWT (TIM2 occupé par la
  capture), fenêtrage structurel (M11), gabarit de perçage
  `surface-template`.
- Leçon de re-routage : le déplacement du joint et les deux nets
  nouveaux ont d'abord déplacé cinq signaux ; le repositionnement du
  tampon a tout refermé côté LED. Référence : 499 pistes, DRC zéro,
  sept couloirs saturés restants.

## Où en est la ligne de temps

Phase 0 faite, phase 1 conçue et générée de bout en bout ; le reste
est physique (finition pcbnew, commandes, montage, mesures M1 à M11).
Voir [l'état](07-etat-et-reste-a-faire.md).
