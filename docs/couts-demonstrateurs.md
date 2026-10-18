# Coûts des démonstrateurs

Généré par `python3 tools/demobom.py` le 18/10/2026 depuis
`docs/prix-demonstrateur.csv` (prix et sources, datés, « vérifié » ou
« estimé ») et les nomenclatures des cartes. Les composants sont
comptés au canal le moins cher ligne à ligne, rechange comprise ; le
détail par repère est dans [`bom-demonstrateur-a.md`](bom-demonstrateur-a.md)
et [`bom-demonstrateur-b.md`](bom-demonstrateur-b.md). Conversion
1 USD = 0.92 EUR, TVA 20% dans la colonne EUR TTC. Une ligne
« optionnelle » n'entre pas dans le minimum : elle est comptée dans le
total complet. L'outillage s'achète une fois pour les deux démonstrateurs.
Deux scénarios : tout acheter, cartes assemblées par JLCPCB et établi à
équiper ; puis souder soi-même avec le gros matériel déjà acheté
(section « soudure maison » en fin de fiche).

## Démonstrateur A, détection LC par oscillations

| Poste | USD | EUR TTC | Statut | Source et remarque |
|---|---|---|---|---|
| **Composants des cartes** (36 lignes, 107 pièces, rechange comprise) | 28 | 31 | relevés web | le moins cher de LCSC ou Mouser ligne à ligne ; tout chez LCSC 11 USD, tout chez Mouser 60 USD |

### Cartes nues (JLCPCB)

| Poste | USD | EUR TTC | Statut | Source et remarque |
|---|---|---|---|---|
| PCB 100x100 4L x5 | 30 | 33 | estimé | JLCPCB 4 couches 100 x 100 mm, 5 pieces, HASL : 25 a 35 USD, plus 10 a 25 pour le cuivre interne 1 oz (note 23, 3.1) |
| PCB inner copper 1oz | 18 | 20 | optionnel, estimé | option cuivre interne 1 oz sur la carte bobines 4 couches, 10 a 25 USD (note 23, 3.1) ; optionnelle |
| PCB 100x62 2L x5 | 4 | 4 | estimé | JLCPCB 2 couches 100 x 62 mm, 5 pieces |
| PCB stencil 100x100 | 8 | 9 | optionnel, estimé | pochoir inox JLCPCB pour une carte 100 x 100, pour qui soude lui-meme a la pate ; 7 a 12 USD |
| *Sous-total cartes nues (jlcpcb)* | *60* | *66* | | |

### Assemblage (JLCPCB)

| Poste | USD | EUR TTC | Statut | Source et remarque |
|---|---|---|---|---|
| PCBA economic setup | 25 | 28 | optionnel, estimé | assemblage economique JLCPCB, frais fixes 2 cartes : preparation 8 USD, pochoir 1.5 USD, 3 USD par reference etendue (note 23, 8.3) |
| JLC3DP pucks and jigs | 15 | 17 | optionnel, estimé | impression 3D JLC3DP des quatre pucks, gabarits de bobinage et gabarit de percage du modele A, resine ou PLA ; 10 a 20 USD, ou filament maison 3 USD |
| *Sous-total assemblage (jlcpcb)* | *40* | *44* | | |

### Cartes de développement

| Poste | USD | EUR TTC | Statut | Source et remarque |
|---|---|---|---|---|
| NUCLEO-G474RE | 20 | 22 | estimé | carte de developpement ST ; releves web du 2026-10-17 : Future 17.33 a 19.52 USD, DigiKey UK 14.96 GBP HT, RS et eStore ST vers 17.5 EUR HT (fiche de la maquette) ; Mouser a verifier au panier |
| *Sous-total cartes de développement* | *20* | *22* | | |

### Composants hors cartes et matériaux

| Poste | USD | EUR TTC | Statut | Source et remarque |
|---|---|---|---|---|
| Magnets ferrite 12 15 18x4 | 12 | 13 | estimé | aimants ferrite Y30 axiaux, 12, 15 et 18 x 4 mm, 18 pieces, boutique d aimants ou place de marche (note 25, 8.3) |
| Enamelled wire 025 0315 | 8 | 9 | estimé | fil emaille 0,25 et 0,315 mm, 50 g de chaque, pour les quatre pucks |
| Puck C0G capacitors | 1 | 1 | estimé | quatre condensateurs C0G 1 pct (12, 10, 8.2, 6.8 nF, 0805 ou 1206) et leur rechange |
| Plywood 3mm felt | 6 | 7 | estimé | contreplaque sec 3 mm 200 x 200 et feutre 0,5 mm (magasin de bricolage ou de loisirs creatifs) |
| Nylon M3 kit | 6 | 7 | estimé | visserie nylon M3 : entretoises 2 mm (A) ou 30 mm (B), vis, ecrous ; un assortiment |
| Supply 12V 2A jack | 12 | 13 | estimé | bloc 12 V 2 A a jack 5,5 x 2,1 mm pour le modele A ; une alimentation de laboratoire le remplace |
| Dupont and USB cables | 2 | 2 | estimé | vingt nappes Dupont femelle-femelle, un cable USB (micro-B pour la Nucleo, USB-C pour le module) ; 3 a 8 USD |
| *Sous-total composants hors cartes et matériaux* | *47* | *52* | | |

### Outillage et instruments

| Poste | USD | EUR TTC | Statut | Source et remarque |
|---|---|---|---|---|
| Tool soldering iron kit | 25 | 28 | estimé | fer a panne fine reglable, flux, tresse, brucelles, loupe ; 25 a 60 USD selon la gamme |
| Tool multimeter | 15 | 17 | estimé | multimetre avec gamme millivolts (le courant TVDD se lit en mV sur 1 ohm) |
| Tool bench supply | 45 | 50 | estimé | alimentation de laboratoire 0 a 30 V limitee en courant, indispensable aux premieres mises sous tension |
| Tool pocket oscilloscope | 60 | 66 | estimé | oscilloscope de poche 10 MHz ou plus (bande des notes du modele A jusqu a 650 kHz) ; optionnel pour B |
| Tool LCR meter | 30 | 33 | optionnel, estimé | LCR-metre de poche : tranche une bobine de puck douteuse en une minute ; optionnel |
| *Sous-total outillage et instruments* | *175* | *193* | | |

### Port et douane

| Poste | USD | EUR TTC | Statut | Source et remarque |
|---|---|---|---|---|
| Shipping JLCPCB | 25 | 28 | estimé | port DHL ou standard vers la France, 15 a 40 USD selon le poids |
| Shipping Mouser | 20 | 22 | estimé | port Mouser France, offert au-dessus de 50 EUR HT |
| Customs import FR | 0 | 0 | estimé | TVA et frais de dedouanement a l importation : la TVA de 20 pct est comptee dans la colonne EUR TTC ; le transporteur ajoute 10 a 20 EUR de frais de dossier selon l envoi |
| *Sous-total port et douane* | *45* | *50* | | |

| Total | USD | EUR TTC |
|---|---|---|
| **Minimum** (composants, cartes, port, matériaux et outillage indispensables) | **318** | **351** |
| **Complet** (options comprises) | **414** | **457** |

## Démonstrateur B, effet Hall et RFID

| Poste | USD | EUR TTC | Statut | Source et remarque |
|---|---|---|---|---|
| **Composants des cartes** (48 lignes, 157 pièces, rechange comprise) | 32 | 35 | relevés web | le moins cher de LCSC ou Mouser ligne à ligne ; tout chez LCSC 32 USD, tout chez Mouser 85 USD |

### Cartes nues (JLCPCB)

| Poste | USD | EUR TTC | Statut | Source et remarque |
|---|---|---|---|---|
| PCB 100x100 4L x5 | 30 | 33 | estimé | JLCPCB 4 couches 100 x 100 mm, 5 pieces, HASL : 25 a 35 USD, plus 10 a 25 pour le cuivre interne 1 oz (note 23, 3.1) |
| PCB 100x87 2L 0.8 x5 | 8 | 9 | estimé | planche d etiquettes 0.8 mm, 2 couches, panneau client a 4 conceptions : 5 a 15 USD |
| PCB stencil 100x100 | 8 | 9 | optionnel, estimé | pochoir inox JLCPCB pour une carte 100 x 100, pour qui soude lui-meme a la pate ; 7 a 12 USD |
| *Sous-total cartes nues (jlcpcb)* | *46* | *51* | | |

### Assemblage (JLCPCB)

| Poste | USD | EUR TTC | Statut | Source et remarque |
|---|---|---|---|---|
| PCBA standard 2 boards | 60 | 66 | estimé | assemblage Standard JLCPCB face avant, 2 cartes : preparation 25 USD, pochoir, 3 USD par reference etendue (module, lecteurs, mux, tampon, regulateur, USB-C, quartz, selfs), joints : 50 a 70 USD (note 25, 8.2 et 8.4) |
| JLC3DP pieces and plate | 20 | 22 | optionnel, estimé | impression 3D JLC3DP des pieces de test, plaque, cales et gabarits du modele B (note 25, 6) ; 15 a 30 USD, ou filament maison 5 USD |
| *Sous-total assemblage (jlcpcb)* | *80* | *88* | | |

### Cartes de développement

| Poste | USD | EUR TTC | Statut | Source et remarque |
|---|---|---|---|---|
| ESP32-S3-DevKitC-1 | 8 | 9 | optionnel, estimé | carte de developpement de secours du modele B, branchee sur la barrette d echappement si le module ne demarre pas ; optionnelle ; 8 a 15 USD |
| *Sous-total cartes de développement* | *8* | *9* | | |

### Composants hors cartes et matériaux

| Poste | USD | EUR TTC | Statut | Source et remarque |
|---|---|---|---|---|
| Magnets ferrite 12 15 18x4 | 12 | 13 | estimé | aimants ferrite Y30 axiaux, 12, 15 et 18 x 4 mm, 18 pieces, boutique d aimants ou place de marche (note 25, 8.3) |
| NTAG213 cards | 3 | 3 | estimé | deux ou trois cartes NTAG213 du commerce, reference de lecture (M13) |
| Polyimide tape | 4 | 4 | estimé | ruban polyimide 10 mm qui tient les disques d etiquette dans les bases |
| Nylon M3 kit | 6 | 7 | estimé | visserie nylon M3 : entretoises 2 mm (A) ou 30 mm (B), vis, ecrous ; un assortiment |
| UFL SMA pigtails | 2 | 2 | estimé | deux pigtails U.FL vers SMA (ou RG178 nu) a souder sur les points de test TX pour l accord au NanoVNA |
| Dupont and USB cables | 2 | 2 | estimé | vingt nappes Dupont femelle-femelle, un cable USB (micro-B pour la Nucleo, USB-C pour le module) ; 3 a 8 USD |
| Aluminium steel plates | 8 | 9 | optionnel, estimé | plaques d aluminium et d acier plus grandes que la zone de jeu pour M14b (chute de magasin de bricolage) |
| *Sous-total composants hors cartes et matériaux* | *37* | *41* | | |

### Outillage et instruments

| Poste | USD | EUR TTC | Statut | Source et remarque |
|---|---|---|---|---|
| Tool soldering iron kit | 25 | 28 | estimé | fer a panne fine reglable, flux, tresse, brucelles, loupe ; 25 a 60 USD selon la gamme |
| Tool multimeter | 15 | 17 | estimé | multimetre avec gamme millivolts (le courant TVDD se lit en mV sur 1 ohm) |
| Tool bench supply | 45 | 50 | estimé | alimentation de laboratoire 0 a 30 V limitee en courant, indispensable aux premieres mises sous tension |
| NanoVNA-H | 70 | 77 | estimé | NanoVNA-H avec sonde et cables U.FL vers SMA, 60 a 90 EUR, place de marche (note 25, D9) |
| Tool NFC phone | 0 | 0 | vérifié | un telephone NFC lit chaque etiquette avant montage : deja possede |
| Tool pocket oscilloscope | 60 | 66 | optionnel, estimé | oscilloscope de poche 10 MHz ou plus (bande des notes du modele A jusqu a 650 kHz) ; optionnel pour B |
| Tool hot air station | 40 | 44 | optionnel, estimé | station a air chaud pour souder soi-meme les QFN du MFRC522 ; inutile si JLCPCB assemble la carte |
| *Sous-total outillage et instruments* | *255* | *282* | | |

### Port et douane

| Poste | USD | EUR TTC | Statut | Source et remarque |
|---|---|---|---|---|
| Shipping JLCPCB | 25 | 28 | estimé | port DHL ou standard vers la France, 15 a 40 USD selon le poids |
| Shipping Mouser | 20 | 22 | estimé | port Mouser France, offert au-dessus de 50 EUR HT |
| Customs import FR | 0 | 0 | estimé | TVA et frais de dedouanement a l importation : la TVA de 20 pct est comptee dans la colonne EUR TTC ; le transporteur ajoute 10 a 20 EUR de frais de dossier selon l envoi |
| *Sous-total port et douane* | *45* | *50* | | |

| Total | USD | EUR TTC |
|---|---|---|
| **Minimum** (composants, cartes, port, matériaux et outillage indispensables) | **359** | **396** |
| **Complet** (options comprises) | **503** | **555** |

## Les deux démonstrateurs ensemble

L'outillage, la visserie, les nappes, les aimants et un port Mouser
ne s'achètent qu'une fois ; une seule commande JLCPCB peut porter les
quatre cartes, ce qui économise encore un port (non compté ici).

| Total | USD | EUR TTC |
|---|---|---|
| Minimum des deux | 552 | 610 |
| Complet des deux | 732 | 809 |

## Scénario : soudure maison, gros matériel déjà acheté

Les cartes se commandent nues et se soudent au fer ; le HVQFN du
MFRC522 et le module ESP32 passent à l'air chaud ou à la plaque, avec
le pochoir. Fer, air chaud, alimentation de laboratoire, multimètre,
oscilloscope et NanoVNA sont déjà sur l'établi, pâte, flux et tresse
aussi. Restent les composants, les cartes nues, les cartes de
développement (la NUCLEO reste comptée : elle porte le démonstrateur A ;
à retirer si elle est déjà dans le tiroir), les matériaux et le port.
Les codes LCSC manquants des condensateurs
d'adaptation n'ont plus d'importance : on les achète par valeur, chez
Mouser ou LCSC, dans la même commande.

### Démonstrateur A, détection LC par oscillations

| Poste | USD | EUR TTC | Statut | Remarque |
|---|---|---|---|---|
| Composants des cartes (107 pièces, rechange comprise) | 28 | 31 | relevés web | le moins cher de LCSC ou Mouser ligne à ligne |
| PCB 100x100 4L x5 | 30 | 33 | estimé | cartes nues (jlcpcb) |
| PCB inner copper 1oz | 18 | 20 | optionnel, estimé | cartes nues (jlcpcb) |
| PCB 100x62 2L x5 | 4 | 4 | estimé | cartes nues (jlcpcb) |
| PCB stencil 100x100 | 8 | 9 | optionnel, estimé | conseillé pour poser la pâte sous les QFN et le module |
| JLC3DP pucks and jigs | 15 | 17 | optionnel, estimé | ou imprimés chez soi |
| NUCLEO-G474RE | 20 | 22 | estimé | cartes de développement |
| Magnets ferrite 12 15 18x4 | 12 | 13 | estimé | composants hors cartes et matériaux |
| Enamelled wire 025 0315 | 8 | 9 | estimé | composants hors cartes et matériaux |
| Puck C0G capacitors | 1 | 1 | estimé | composants hors cartes et matériaux |
| Plywood 3mm felt | 6 | 7 | estimé | composants hors cartes et matériaux |
| Nylon M3 kit | 6 | 7 | estimé | composants hors cartes et matériaux |
| Supply 12V 2A jack | 12 | 13 | estimé | composants hors cartes et matériaux |
| Dupont and USB cables | 2 | 2 | estimé | composants hors cartes et matériaux |
| Shipping JLCPCB | 25 | 28 | estimé | port et douane |
| Shipping Mouser | 20 | 22 | estimé | port et douane |
| Customs import FR | 0 | 0 | estimé | port et douane |
| **Minimum** | **173** | **191** | | |
| **Avec les options** (pochoir, impression 3D, carte de secours) | **214** | **237** | | |

### Démonstrateur B, effet Hall et RFID

| Poste | USD | EUR TTC | Statut | Remarque |
|---|---|---|---|---|
| Composants des cartes (157 pièces, rechange comprise) | 32 | 35 | relevés web | le moins cher de LCSC ou Mouser ligne à ligne |
| PCB 100x100 4L x5 | 30 | 33 | estimé | cartes nues (jlcpcb) |
| PCB 100x87 2L 0.8 x5 | 8 | 9 | estimé | cartes nues (jlcpcb) |
| PCB stencil 100x100 | 8 | 9 | optionnel, estimé | conseillé pour poser la pâte sous les QFN et le module |
| JLC3DP pieces and plate | 20 | 22 | optionnel, estimé | ou imprimés chez soi |
| ESP32-S3-DevKitC-1 | 8 | 9 | optionnel, estimé | cartes de développement |
| Magnets ferrite 12 15 18x4 | 12 | 13 | estimé | composants hors cartes et matériaux |
| NTAG213 cards | 3 | 3 | estimé | composants hors cartes et matériaux |
| Polyimide tape | 4 | 4 | estimé | composants hors cartes et matériaux |
| Nylon M3 kit | 6 | 7 | estimé | composants hors cartes et matériaux |
| UFL SMA pigtails | 2 | 2 | estimé | composants hors cartes et matériaux |
| Dupont and USB cables | 2 | 2 | estimé | composants hors cartes et matériaux |
| Aluminium steel plates | 8 | 9 | optionnel, estimé | composants hors cartes et matériaux |
| Shipping JLCPCB | 25 | 28 | estimé | port et douane |
| Shipping Mouser | 20 | 22 | estimé | port et douane |
| Customs import FR | 0 | 0 | estimé | port et douane |
| **Minimum** | **144** | **159** | | |
| **Avec les options** (pochoir, impression 3D, carte de secours) | **188** | **208** | | |

| Les deux démonstrateurs, soudure maison | USD | EUR TTC |
|---|---|---|
| Minimum (visserie, nappes, aimants et port Mouser comptés une fois) | 277 | 306 |
| Avec les options | 362 | 400 |

## Ce que les prix ne couvrent pas

- Les frais de dossier du transporteur à l'importation (10 à 20 EUR par
  envoi hors UE), variables ; la TVA est comptée.
- Le temps de montage et de mesure, et le contreplaqué ou le filament
  déjà en stock chez qui bricole.
- Les codes LCSC des condensateurs C0G d'adaptation, à relever le jour
  de la commande : sans eux, l'assemblage les saute et ils se soudent au fer.
