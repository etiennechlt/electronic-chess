# Fiche d'approvisionnement du plateau : quatre quadrants et le cerveau

Établie le 20/09/2026. Elle répond à une question précise : que faut il
acheter, et où, pour monter le plateau 8 x 8 de l'ADR 0010, c'est à dire
**quatre quadrants 4 x 4 identiques et un cerveau**. La maquette 2 x 2 a
la sienne ([fiche de la maquette](bom-maquette.md)), même méthode, mêmes
conventions de prix.

Les quantités ne sont pas recopiées : elles sortent des `bom.csv`
générés par `quadgen` et `boardgen`, agrégés par `tools/bomagg.py`. Les
prix, eux, sont des données de marché, ils vieillissent, et chaque ligne
porte son statut (`verified` ou `estimated`) et sa source dans
`docs/prix-plateau.csv`. Conversion retenue, celle de la fiche de la
maquette : 1 USD = 0,92 EUR. Les prix asiatiques sont hors taxe, la TVA
de 20 % est collectée à la commande (IOSS) ou à l'import ; elle est
ajoutée dans les totaux en EUR TTC.

**Ce que cette fiche n'est pas.** Aucune commande n'a été passée. Le
réseau de cet environnement bloque les sites distributeurs et leurs API
(le point était déjà noté sur la maquette) : les relevés viennent de
recherches web du 20/09/2026, les paniers sont préparés au format
d'import de chaque site, et les prix se revalident au panier avant de
payer.

## 1. La liste, en une commande

```bash
python3 tools/bomagg.py --prices docs/prix-plateau.csv \
    --csv docs/bom-plateau.csv --carts docs/
```

```
quadrant       x4   1296 components   80 pads (test points, ties, holes)
brain          x1    103 components   10 pads (test points, ties, holes)
total               1399 components in  71 purchase lines, 1584 units to buy with spares
basket lcsc          138.09 USD over  70 of 71 lines
basket mouser        378.80 USD over  70 of 71 lines
basket mixed         180.05 USD over  71 of 71 lines
one quadrant          32.44 USD of parts,  35 lines, exact count without spares
one brain             18.63 USD of parts,  50 lines, exact count without spares
```

Trois fichiers sortent de là, tous commités :

| Fichier | Contenu |
|---|---|
| [`bom-plateau.csv`](bom-plateau.csv) | les 71 lignes d'achat, quantité par carte, total, quantité à acheter, prix des deux canaux |
| [`panier-lcsc.csv`](panier-lcsc.csv) | 68 lignes au format d'import BOM de LCSC |
| [`panier-mouser.csv`](panier-mouser.csv) | 3 lignes au format d'import BOM de Mouser |

Les 1 399 composants se comptent comme la [note 23](notes/23-commande-jlcpcb.md) :
les points de test, les amarres de spirale et les trous de fixation sont
des pastilles, pas des composants, et ne sont pas dans la liste (90 sur
le plateau). Les 1 584 unités à acheter ajoutent la règle de rechange :
10 % par ligne, jamais moins de un, jamais moins de deux dès dix pièces.
Elle coûte 31,66 USD sur ce panier, soit 21 % : c'est le prix de ne pas
attendre trois semaines pour un AO3400A perdu sous l'établi.

## 2. Ce que la liste coûte

| Panier | USD | EUR HT | EUR TTC | Couverture |
|---|---|---|---|---|
| Tout LCSC | 138,09 | 127,04 | 152,45 | 70 lignes sur 71, l'OPA2810 n'y est pas |
| Tout Mouser | 378,80 | 348,50 | 418,20 | 70 lignes sur 71, la WS2812B n'y est pas |
| **Panaché, le moins cher ligne à ligne** | **180,05** | **165,64** | **198,77** | **71 sur 71** |

Le panier LCSC est le moins cher **et** incomplet : il ne totalise pas
l'OPA2810, que LCSC ne catalogue pas, et l'OPA2810 pèse 49 USD. Un total
partiel qui se lit comme un total complet est exactement l'erreur 11 de
la [note 22](notes/22-erreurs-de-conception.md) ; c'est pourquoi l'outil
affiche la couverture à côté de chaque total, et pourquoi un test exige
qu'aucune ligne ne soit sans prix.

Par carte, composants seuls, au compte exact et sans rechange :

| Carte | Composants | Lignes | Prix des composants | Ce que la note 23 estimait |
|---|---|---|---|---|
| Un quadrant 4 x 4 | 324 | 35 | 32,44 USD, soit 29,84 EUR HT | 41 à 46 EUR |
| Le cerveau | 103 | 50 | 18,63 USD, soit 17,14 EUR HT | 26 EUR |

La [note 23](notes/23-commande-jlcpcb.md), paragraphe 8.2, surestimait
donc d'un tiers, pour une raison simple : elle comptait l'ADG1607 à
8,5 EUR et l'AD8421 jusqu'à 8,2 EUR, prix catalogue occidentaux, alors
que le premier se trouve à 5,12 USD et le second à 3,69 USD chez LCSC.
Le silicium analogique des quatre quadrants fait 99,56 USD au compte
exact et 113,85 USD rechange comprise (105 EUR HT), et non 120 à
140 EUR.

## 3. Les six lignes qui font la facture

| Ligne | Quantité achetée | Coût | Part du panier |
|---|---|---|---|
| OPA2810IDR | 9 | 49,32 USD | 27,4 % |
| ADG1607BCPZ | 9 | 46,08 USD | 25,6 % |
| AD8421ARZ | 5 | 18,45 USD | 10,2 % |
| STM32G474RET6 | 2 | 11,00 USD | 6,1 % |
| FH12-16S-0.5SH(55) | 9 | 10,80 USD | 6,0 % |
| WS2812B | 141 | 8,69 USD | 4,8 % |

**Trois références du frontal analogique font 63,2 % du panier.** C'est
la mesure que la [note 16](notes/16-cout-des-cartes.md), section 2,
attendait pour rouvrir la question du différentiel vrai contre le
single-ended : le poste à discuter n'est ni les 1 399 composants, ni les
128 LED, c'est le mux, l'ampli d'instrumentation et les deux AOP, deux
fois par quadrant pour les deux derniers.

À l'autre bout, les 735 passifs génériques (condensateurs et résistances
0402 à 2010, sans référence fabricant) coûtent 2,85 USD chez LCSC,
rechange comprise, contre 20,42 USD chez Mouser. Sept fois plus cher,
pour 1,6 % du panier : c'est le poste sur lequel il ne faut pas passer
de temps.

## 4. Où acheter quoi

Le partage se fait ligne à ligne, pas par principe. Résultat :

| Canal | Lignes | Pourquoi |
|---|---|---|
| LCSC | 68 | moins cher partout ailleurs, souvent d'un facteur 3 à 10 sur les passifs et les discrets |
| Mouser | 3 | l'OPA2810IDR (absent de LCSC), l'ADG1607BCPZ (5,12 contre 5,60 USD estimé) et le FH12-16S (en rupture chez LCSC) |

Deux cas méritent d'être lus avant de valider :

- **La WS2812B n'existe pas chez Mouser** (Worldsemi n'y est pas
  distribué). Un plateau entier en demande 128 : cette ligne seule
  interdit le panier tout Mouser, et c'est l'argument le plus net en
  faveur de la commande chinoise.
- **L'ADG1607 passe chez Mouser pour 0,48 USD par pièce**, sur un prix
  LCSC estimé et non affiché. Si le panier LCSC l'affiche sous 5,12 USD,
  il repasse chez LCSC et le panier Mouser tombe à deux lignes.

## 5. Neuf codes LCSC à corriger avant tout assemblage

La [note 22](notes/22-erreurs-de-conception.md), point 11, avait trouvé
six codes faux sur douze au quadrant 2 x 2. Le contrôle refait ici sur
les cartes du plateau donne ceci :

| Référence | Code du circuit | Code vérifié le 20/09 | Ce que ça change |
|---|---|---|---|
| ADG1607BCPZ | aucun | C209487 | le mux entre enfin dans un ordre d'assemblage |
| AD8421ARZ | C462186 | C392903 | 3,69 USD, 949 en stock |
| ADuM1201ARZ | C123211 | C9669 | 1,28 USD |
| ESP32-S3-WROOM-1-N8 | C2913204 | C2913198 | C2913204 est la variante N8R2 (2 Mo de PSRAM), pas celle du circuit |
| LP2985AIM5-5.0 | C129541 | C109382 | 0,165 USD |
| STM32G474RET6 | C528140 | C521608 | C528140 ne résout pas |
| TPS62130RGTR | C74016 | C43590 | 0,73 USD, 35 283 en stock |
| FH12-16S-0.5SH(55) | C2837584 | C596731 | en rupture, voir le paragraphe 6 |
| OPA2810IDR | C2059830 | aucun chez LCSC | à acheter chez Mouser ou DigiKey |

Le fichier de prix porte le code vérifié, l'outil signale l'écart à
chaque exécution (`lcsc clash`), et c'est ce code qui part dans le
panier. Corriger les générateurs est un autre chantier : regénérer une
carte refait son routage, et celui du quadrant 4 x 4 n'est pas fermé
(note 23, paragraphe 4). Ces codes se corrigent dans
`tools/quadgen/circuit.py` et `tools/boardgen/` à la prochaine reprise du
routage, pas avant.

## 6. Trois risques d'approvisionnement

1. **Le FH12-16S-0.5SH(55) est obsolète.** DigiKey l'annonce comme non
   fabriqué, LCSC est en rupture sur C596731. Le plateau en demande huit
   (quatre côté quadrants, quatre côté cerveau). Un FPC 16 voies au pas
   de 0,5 mm du commerce courant coûte 0,10 à 0,30 USD contre 1,54 :
   changer d'embase économise une dizaine d'USD et supprime le risque,
   au prix d'une vérification d'empreinte sur les deux cartes.
2. **L'OPA2810 n'est pas chez LCSC.** Une commande d'assemblage JLCPCB
   ne pourra pas le poser : soit il est fourni en pièces consignées
   (3 USD de frais par référence étendue, plus la logistique), soit
   l'étage est revu (paragraphe 7).
3. **La variante d'ESP32 diverge.** Le circuit demande un N8, son code
   pointe un N8R2. Les deux existent, le second a 2 Mo de PSRAM en plus ;
   il faut choisir, le firmware ESP-IDF n'en dépend pas aujourd'hui.

## 7. Quatre leviers, chiffrés

| Levier | Ce qu'il rapporte | Ce qu'il coûte en décision |
|---|---|---|
| Frontal single-ended plutôt que différentiel vrai | le poste mux passe de 46 à 12 ou 22 USD selon le composant, soit 24 à 34 USD | la mesure qui tranche reste à définir ([note 16](notes/16-cout-des-cartes.md), section 2) |
| Un double AOP moins cher que l'OPA2810 | de 49 à 18 ou 22 USD, soit environ 28 USD | revue du gabarit (bruit, bande, entrée FET) ; la bande de mesure est de 217 à 613 kHz pour un composant à 70 MHz |
| Embase FPC courante à la place du FH12 | environ 9 USD | vérifier l'empreinte sur le quadrant et sur le cerveau |
| Acheter au compte exact, sans rechange | 31,66 USD | trois semaines d'attente si une pièce meurt au montage ; déconseillé |

Les trois premiers leviers pris ensemble font tomber le panier de 180 à
environ 110 USD, soit un tiers. Aucun ne se décide dans cette fiche :
les deux premiers sont des choix de conception, le troisième une
vérification d'empreinte.

Le levier qui n'est pas dans ce tableau est l'assemblage : la
[note 23](notes/23-commande-jlcpcb.md), paragraphe 8.3, chiffre
l'assemblage économique de quatre quadrants et d'un cerveau à 430 à
480 EUR contre 300 à 350 EUR en cartes nues. Les 130 EUR d'écart
achètent 1 399 poses, dont huit LFCSP au pas de 0,5 mm et un LQFP-64 :
c'est le meilleur rapport de cette fiche, à condition d'avoir corrigé
les codes du paragraphe 5.

## 8. Le plateau complet, cartes comprises

| Poste | EUR TTC | Source |
|---|---|---|
| Composants, panier panaché avec rechange | 199 | cette fiche, paragraphe 2 |
| 5 quadrants 4 x 4 nus, 4 couches, ENIG, cuivre interne 1 oz | 60 à 96 | note 23, paragraphe 8.1 |
| 5 cerveaux nus, 4 couches, ENIG | 34 à 42 | note 23, paragraphe 8.1 |
| Port et TVA sur les cartes | 30 à 48 | note 23, paragraphe 8.1 |
| Port LCSC et Mouser | 25 à 40 | estimé, deux expéditions |
| **Total, tout à souder soi même** | **348 à 425** | |

La commande d'assemblage remplace le port des composants et une partie
du temps de fer par 130 EUR environ, ce qui amène le plateau assemblé
aux alentours de 450 à 500 EUR TTC, cohérent avec la note 23.

## 9. La commande, dans l'ordre

1. **Ne pas commander les cartes du plateau aujourd'hui.** Le quadrant
   4 x 4 n'a pas d'archive de fabrication (47 nets ouverts, note 23,
   paragraphe 4) ; le cerveau en a une, vérifiée. La validation du
   frontal passe d'abord par le quadrant 2 x 2 et la carte de banc, qui
   se commandent tels quels.
2. Rejouer la liste et les paniers (paragraphe 1), pour partir des
   fichiers à jour.
3. Ouvrir le panier LCSC, importer `docs/panier-lcsc.csv`, **relever les
   prix et les stocks réels ligne à ligne** : 63 des 71 lignes sont
   estimées et 8 seulement relevées, notamment tous les passifs. Compléter les codes des passifs
   génériques dans le panier, ou les laisser à la bibliothèque de
   l'assembleur si l'assemblage est retenu.
4. Ouvrir le panier Mouser, importer `docs/panier-mouser.csv`, vérifier
   que l'OPA2810 et l'ADG1607 sont en stock, et arbitrer l'ADG1607 selon
   le prix LCSC affiché (paragraphe 4).
5. Reporter les prix relevés dans `docs/prix-plateau.csv` avec leur
   statut et leur source, rejouer l'outil : le total devient un devis.
6. Pour les cartes, suivre la [note 23](notes/23-commande-jlcpcb.md),
   paragraphes 3 et 7 (empreintes, options, cuivre interne, quatre
   approbations séparées du skill `operate-jlcpcb-order`).
7. Noter dans le [journal](notes/09-journal.md) la date, les prix
   obtenus et les écarts avec cette fiche.

## 10. Sources des relevés du 20/09/2026

- ADG1607BCPZ : [LCSC C209487](https://lcsc.com/product-detail/Analog-Switches_Analog-Devices_ADG1607BCPZ-REEL7_Analog-Devices-ADI-ADG1607BCPZ-REEL7_C209487.html),
  [Octopart](https://octopart.com/adg1607bcpz-reel7-analog+devices-13130399),
  [Mouser](https://www.mouser.com/ProductDetail/Analog-Devices/ADG1607BCPZ-REEL7?qs=BpaRKvA4VqEg%2FkzeF3lydg%3D%3D)
- AD8421ARZ : [LCSC C392903](https://www.lcsc.com/product-detail/Instrumentation-Amplifiers_Analog-Devices-AD8421ARZ-R7_C392903.html),
  [Mouser](https://www.mouser.com/ProductDetail/Analog-Devices/AD8421ARZ?qs=/tpEQrCGXCyoA2YFZOY76g%3D%3D)
- OPA2810IDR : [DigiKey](https://www.digikey.com/en/products/detail/texas-instruments/OPA2810IDR/10715569),
  absent des résultats LCSC
- STM32G474RET6 : [LCSC C521608](https://www.lcsc.com/product-detail/C521608.html),
  [Mouser](https://www.mouser.com/ProductDetail/STMicroelectronics/STM32G474RET6?qs=PzGy0jfpSMvUBs7PMTDqlg%3D%3D)
- ESP32-S3-WROOM-1 : [N8 C2913198](https://lcsc.com/product-detail/WiFi-Modules_Espressif-Systems-ESP32-S3-WROOM-1-N8_C2913198.html),
  [N8R2 C2913204](https://www.lcsc.com/product-detail/C2913204.html)
- TPS62130RGTR : [LCSC C43590](https://www.lcsc.com/product-detail/DC-DC-Converters_Texas-Instruments_TPS62130RGTR_Texas-Instruments-Texas-Instruments-TPS62130RGTR_C43590.html)
- WS2812B : [LCSC C2761795](https://www.lcsc.com/product-detail/Light-Emitting-Diodes-LED_Worldsemi-WS2812B-B-T_C2761795.html)
- AO3400A : [LCSC C20917](https://www.lcsc.com/product-detail/MOSFET_AOS_AO3400A_AO3400A_C20917.html)
- FH12-16S-0.5SH(55) : [LCSC C596731](https://lcsc.com/product-detail/FFC-FPC-Connectors_HRS-Hirose-FH12-16S-0-5SH-55_C596731.html),
  [DigiKey, obsolète](https://www.digikey.com/en/products/detail/hirose-electric-co-ltd/FH12-16S-0-5SH-55/1110319)
- ADuM1201ARZ et LP2985A : relevés du 30/08/2026, [fiche de la maquette](bom-maquette.md)
