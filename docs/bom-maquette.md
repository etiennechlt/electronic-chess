# Fiche d'approvisionnement de la maquette 2 x 2

Prix relevés le 30/08/2026 par recherche web, chaque ligne porte son
statut : « vérifié » (prix affiché par le distributeur à cette date,
source en bas de page) ou « estimé » (fourchette de marché, à
confirmer au panier). Conversion retenue : 1 USD = 0,92 EUR, arrondie.
Les prix Europe s'entendent TTC pour un particulier en France (TVA
20 %) ; les prix Asie (LCSC, JLCPCB, AliExpress) sont facturés hors
taxe puis la TVA est collectée à la commande (IOSS) ou à l'import,
elle est incluse dans les totaux comparés. La BOM détaillée de la
carte analogique (135 composants) est générée dans
`hardware/mockup-2x2/analog-board/bom.csv` et ses fichiers JLCPCB
(`jlc-bom.csv`, `jlc-cpl.csv`) ; ce document compare les canaux
d'achat, la BOM générée reste la source de vérité des références.

## Comparatif Europe contre Asie, poste par poste

### Circuits intégrés de la carte analogique

| Poste | Référence | Qté | Europe (unitaire) | Asie (unitaire) | Choix conseillé |
|---|---|---|---|---|---|
| Ampli d'instrumentation | AD8421ARZ (R7) | 2 | 8,91 USD Mouser, 9,06 USD DigiKey, 5 361 en stock, vérifié | 3,69 USD LCSC C392903, en stock, vérifié | Asie : moitié prix, à mettre dans la commande JLCPCB |
| Isolateur UART | ADuM1201ARZ-RL7 | 2 | rupture DigiKey (réassort sur commande), vérifié | 1,28 à 1,77 USD LCSC C9669, plus de 11 000 en stock, vérifié | Asie : moins cher et disponible |
| Mux différentiel | 74HCT4052PW,118 | 2 | ~0,60 EUR (estimé) | 0,151 USD LCSC C87681, 33 970 en stock, vérifié | Asie |
| LDO | LP2985A-50DBVR | 2 | ~0,60 EUR (estimé) | 0,165 USD LCSC C109382, 12 375 en stock, vérifié | Asie |
| Buck | TPS62150RGTR | 2 | ~2,50 EUR DigiKey (fourchette Octopart 0,81 à 6,64 USD), estimé | LCSC C527690, 2 003 en stock, prix non affiché (~1,2 USD estimé) | Asie, vérifier le prix au panier |
| Double AOP | OPA2810IDR | 4 | 5,48 USD DigiKey, vérifié | non confirmé chez LCSC | Selon panier : si absent de LCSC, prendre chez Mouser avec la Nucleo |

Lecture : sur les actifs, l'Asie gagne presque partout (souvent de
moitié), et l'assemblage JLCPCB les pose directement, donc le bon
réflexe est de tout mettre dans la commande d'assemblage. L'OPA2810
est le seul candidat à un achat européen d'appoint.

### Cartes (fabrication et assemblage)

| Poste | Europe | Asie | Choix conseillé |
|---|---|---|---|
| Carte bobines 4 couches 100 x 100, 5 pièces | ~60 à 90 EUR (Aisler, Eurocircuits, estimé) | 2 à 5 USD en promotion JLCPCB plus port, vérifié (page tarifs) | Asie, sans hésiter |
| Carte analogique 2 couches, 5 pièces dont 2 assemblées | assemblage prototype européen : plusieurs centaines d'EUR, estimé | fabrication ~2 USD ; assemblage économique : minimum 0,48 USD par carte plus préparation (~8 USD), chargeurs de bande, rayons X pour le QFN du buck ; composants au forfait ; ~35 à 55 USD le tout, vérifié pour les règles, estimé pour le total | Asie : l'assemblage économique JLCPCB est sans équivalent européen à ce budget |
| Port et taxes JLCPCB vers la France | | ~15 à 20 EUR port, TVA 20 % collectée IOSS | inclus dans les totaux |

### MCU et alimentation

| Poste | Référence | Europe | Asie | Choix conseillé |
|---|---|---|---|---|
| Carte Nucleo | NUCLEO-G474RE | ~17,50 EUR HT RS (15,02 GBP, réassort 27/08/2026), eStore ST en stock (~17 EUR HT), vérifié | revendeurs eBay et AliExpress ~29 EUR, vérifié | Europe : moins cher ET plus sûr (eStore ST ou RS), contre-exemple utile |
| Bloc 12 V 2 A jack 5,5 x 2,1 | | ~10 EUR Amazon ou magasin local, estimé | ~5 EUR AliExpress, estimé | Europe : la sécurité d'une alim secteur CE vaut les 5 EUR |
| Nappes Dupont F-F 20 cm x 20 | | ~3 EUR Amazon, estimé | ~1,50 EUR AliExpress, estimé | indifférent, grouper avec une autre commande |

### Résonateurs de test et bobinage

| Poste | Référence | Qté | Europe | Asie | Choix conseillé |
|---|---|---|---|---|---|
| C0G 1 % 1206 : 6,8, 8,2, 10, 12 nF | ex. Murata GRM31 ou Samsung | 5 de chaque | 0,30 à 0,60 EUR pièce Mouser, estimé (~9 EUR le lot) | 0,03 à 0,10 USD pièce LCSC, estimé (~1,50 EUR le lot) | Asie, à joindre à la commande LCSC ou JLCPCB |
| Fil émaillé 0,25 mm (et 0,315 mm) | 100 g par diamètre | 2 bobines | dès 4,90 EUR pièce (E44, RadioElec 150 m), vérifié pour l'ordre de prix | ~2 à 4 EUR AliExpress, estimé, 3 à 5 semaines | Europe : E44 ou RadioElec, qualité d'émail connue pour un prix proche |
| Fil de Litz 20 x 0,05 (option si Q insuffisant) | | 10 m | ~8 EUR, estimé | ~4 EUR AliExpress, estimé | Asie si commandé d'avance, sinon Europe |

### Aimants

| Poste | Référence | Qté | Europe | Asie | Choix conseillé |
|---|---|---|---|---|---|
| Ferrite Y30 o15 x 4 (pions) | disque axial | 4 + rechange | 1,95 EUR pièce en 15 x 5 Y35 (Magnetpartner), vérifié ; équivalents chez supermagnete, ct-magnet, univers-magnetique | lots AliExpress ~2 à 5 EUR les 10 à 20, estimé, quantité et nuance moins garanties | Europe : la nuance (Y30 contre Y35) et les cotes sont fiables, c'est le paramètre pivot du projet |
| Ferrite Y30 o12 x 4 (variante) | disque axial | 4 | ~1,50 EUR pièce, estimé | idem ci-dessus | Europe |
| N42 o15 x 5 nickelé (chariot, mesure 7) | supermagnete S-15-05-N, exactement la référence du yaml | 2 | ~1,50 à 2 EUR pièce, page produit confirmée N42, prix au panier | lots AliExpress N42 annoncé, nuance invérifiable | Europe : supermagnete, la nuance N42 est garantie |

Les poches des pucks se régénèrent pour toute taille d'aimant du
commerce : modifier `piece_magnet` dans `config/board.yaml` puis
`python mechanical/build_all.py`.

### Mécanique (achat local, pas de comparatif utile)

| Poste | Quantité | Prix |
|---|---|---|
| Impression 3D (pucks, gabarits, support) ~80 g PETG | | ~3 EUR, estimé |
| Acrylique 3 mm, plaque 120 x 120 | 1 | ~4 EUR, estimé |
| Feutre adhésif 0,5 mm | 1 feuille | ~3 EUR, estimé |
| Visserie M3 (8, 30), écrous, entretoises M3 x 25 | kit | ~6 EUR, estimé |

## Trois totaux comparés (TVA et ports inclus)

| Scénario | Total | Délai typique | Commentaire |
|---|---|---|---|
| Tout Europe | ~200 à 220 EUR | moins d'une semaine | pas d'assemblage abordable : suppose de souder la carte analogique soi-même (135 composants dont un QFN, déconseillé) |
| Tout Asie | ~135 à 150 EUR | 2 à 5 semaines | Nucleo plus chère et douteuse en revendeur, nuances d'aimants invérifiables |
| Panaché conseillé | ~150 à 165 EUR | 1 à 3 semaines | voir la répartition ci-dessous |

Répartition du panaché conseillé, en quatre commandes :

1. **JLCPCB** (~65 à 75 EUR TTC port inclus) : les deux cartes,
   l'assemblage économique de 2 cartes analogiques, tous les actifs
   posés (AD8421, ADuM1201, mux, LDO, buck), plus les C0G des
   résonateurs ajoutés au panier LCSC lié.
2. **eStore ST ou RS** (~25 EUR TTC) : la Nucleo-G474RE.
3. **Mouser ou Farnell** (~30 EUR TTC, seulement si nécessaire) :
   OPA2810IDR si absent du panier LCSC, AD8421 de secours ; franco
   Mouser à 50 EUR, sinon grouper avec la Nucleo chez Farnell.
4. **Europe divers** (~40 à 50 EUR) : aimants (supermagnete ou
   Magnetpartner), fil émaillé (E44 ou RadioElec), alim 12 V,
   mécanique locale.

Le brief visait ~70 EUR pour la seule électronique de maquette : le
panaché y répond (cartes assemblées plus actifs ~70 EUR), le reste est
l'outillage réutilisable (Nucleo, alim, fil, aimants, mécanique).

## Vérification finale au panier (à faire à la commande)

Le réseau de cet environnement de travail bloque les API
distributeurs, les codes LCSC de `jlc-bom.csv` sont donc des candidats
issus des références fabricant : la validation ligne à ligne se fait
dans la prévisualisation JLCPCB en téléversant `jlc-bom.csv` et
`jlc-cpl.csv`, l'outil affiche prix, stock et statut (basic, extended)
réels et propose des substituts. Vérifier aussi l'orientation des
diodes et du régulateur sur le rendu avant de valider. Les prix datés
ci-dessus bougent (les fourchettes constatées sur les actifs vont du
simple au double entre canaux), refaire le total au moment de
commander.

## Sources des prix vérifiés (30/08/2026)

- AD8421ARZ : [Mouser](https://www.mouser.com/ProductDetail/Analog-Devices/AD8421ARZ),
  [DigiKey](https://www.digikey.com/en/products/detail/analog-devices-inc/AD8421ARZ/3340511),
  [LCSC C392903](https://www.lcsc.com/product-detail/Instrumentation-Amplifiers_Analog-Devices-AD8421ARZ-R7_C392903.html)
- ADuM1201ARZ-RL7 : [LCSC C9669](https://www.lcsc.com/product-detail/C9669.html),
  [DigiKey](https://www.digikey.com/en/products/detail/analog-devices-inc/ADUM1201ARZ-RL7/995629)
- 74HCT4052PW : [LCSC C87681](https://www.lcsc.com/product-detail/Analog-Switches_Nexperia-74HCT4052PW-118_C87681.html)
- LP2985A-50DBVR : [LCSC C109382](https://lcsc.com/product-detail/Linear-Voltage-Regulators-LDO_Texas-Instruments-LP2985A-50DBVR_C109382.html)
- TPS62150RGTR : [Octopart](https://octopart.com/tps62150rgtr-texas+instruments-21329326),
  [LCSC C527690](https://www.lcsc.com/product-image/C527690.html)
- OPA2810IDR : [DigiKey](https://www.digikey.com/en/products/detail/texas-instruments/OPA2810IDR/10715569)
- NUCLEO-G474RE : [RS](https://uk.rs-online.com/web/p/microcontroller-development-tools/1939786),
  [eStore ST](https://estore.st.com/en/nucleo-g474re-cpn.html)
- Tarifs JLCPCB : [4 couches](https://jlcpcb.com/blog/special-discount-on-quality-4-layers-pcbs),
  [règles assemblage](https://jlcpcb.com/help/article/pcb-assembly-price)
- Aimants : [Magnetpartner ferrite 15 x 5](https://magnetpartner.com/ferrite-magnets-disc-15x5-mm),
  [supermagnete S-15-05-N](https://www.supermagnete.de/eng/disc-magnets-neodymium/disc-magnet-15mm-5mm_S-15-05-N)
- Fil émaillé : [E44](https://www.e44.com/alimentations/alimentations-tous-types/transformateurs/bobinage/fil-cuivre-emaille/),
  [RadioElec](https://www.radioelec.com/en/enameled-copper-wire-025-mm-coil-150-meters-xml-350_357_459-1409.html)
