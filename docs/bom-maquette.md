# BOM complète de la maquette 2 x 2

Prix indicatifs TTC port compris, arrondis. La BOM détaillée de la
carte analogique (135 composants, références et codes LCSC candidats)
est générée dans `hardware/mockup-2x2/analog-board/bom.csv` ; vérifier
les codes LCSC dans l'outil JLCPCB au moment de la commande.

## Cartes

| Poste | Référence | Quantité | Prix |
|---|---|---|---|
| Carte bobines 4 couches 100 x 100 | gerbers du dépôt | 5 (min) | ~15 EUR |
| Carte analogique 2 couches + assemblage top | gerbers + jlc-bom + jlc-cpl | 5 dont 2 assemblées | ~60 EUR |
| Composants hors assemblage (AD8421ARZ si indisponible LCSC) | Mouser/DigiKey | 2 | ~18 EUR |

## MCU et câblage

| Poste | Référence | Quantité | Prix |
|---|---|---|---|
| Nucleo-G474RE | ST | 1 | ~15 EUR |
| Nappes Dupont F-F 20 cm | | 20 | ~3 EUR |
| Bloc 12 V 2 A jack 5,5 x 2,1 | | 1 | ~10 EUR |

## Résonateurs de test (bas de bande)

| Poste | Référence | Quantité | Prix |
|---|---|---|---|
| C0G 1 % 1206 : 6,8 nF, 8,2 nF, 10 nF, 12 nF | ex. Murata GRM31 C0G | 5 de chaque | ~6 EUR |
| Fil émaillé 0,25 mm (et 0,315 mm) | 100 g | 1 bobine de chaque | ~12 EUR |
| Fil de Litz 20 x 0,05 (option, si Q du pion < 40) | | 10 m | ~8 EUR |
| Aimant ferrite Y30 ø12 x 4 et ø15 x 4 | disques axiaux | 4 + 4 | ~6 EUR |
| Aimant N42 ø15 x 5 (chariot, mesure 7) | | 2 | ~4 EUR |

Les poches des pucks se régénèrent pour toute taille d'aimant du
commerce : modifier `piece_magnet` dans `config/board.yaml` puis
`python mechanical/build_all.py`.

## Mécanique

| Poste | Quantité | Prix |
|---|---|---|
| Impression 3D (pucks, gabarits, support) ~80 g PETG | | ~3 EUR |
| Acrylique 3 mm, plaque 120 x 120 | 1 | ~4 EUR |
| Feutre adhésif 0,5 mm | 1 feuille | ~3 EUR |
| Visserie M3 (8, 30), écrous, entretoises M3 x 25 | kit | ~6 EUR |

## Total

Environ 170 EUR tout compris avec les minimums de commande (dont ~60
de PCB assemblés pour 5 exemplaires) ; le brief visait ~70 EUR pour la
seule électronique de maquette, atteint si l'on retire la Nucleo, les
quantités excédentaires et l'alimentation déjà possédées.
