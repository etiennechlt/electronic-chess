# Nomenclature du démonstrateur B, effet Hall et RFID

Générée par `python3 tools/demobom.py --model b` le 17/10/2026 depuis les
`bom.csv` des cartes et `docs/prix-demonstrateur.csv`. Les quantités
sont celles des cartes ; la colonne « achat » ajoute la rechange de
10 % par ligne (au moins une pièce, deux au-delà de dix). Les prix
sont en USD à l'unité ou à la petite série, datés dans la fiche de
prix, « vérifié » ou « estimé » ; chaque lien ouvre la page ou la
recherche du distributeur, à relire le jour de la commande. Conversion
1 USD = 0.92 EUR, TVA 20 % ajoutée dans les totaux.

## Composants

| Repères | Valeur | Empreinte | MPN | carte | étiquettes | Achat | LCSC (USD) | Mouser (USD) | Moins cher |
|---|---|---|---|---|---|---|---|---|---|
| capacitor | 100n | C_0603_1608Metric |  | 21 | 0 | 24 | [C14663](https://www.lcsc.com/product-detail/C14663.html) 0.010 | [chercher](https://www.mouser.fr/c/?q=100n%200603) 0.12 | 0.24 (lcsc) |
| ic | NT3H2111 G | TSSOP-8_3x3mm_P0.65mm | NT3H2111W0FTTJ | 0 | 15 | 17 | [chercher](https://www.lcsc.com/search?q=NT3H2111W0FTTJ) 0.500 | [771-NT3H2111W0FTTJ](https://www.mouser.fr/ProductDetail/771-NT3H2111W0FTTJ) 1.20 | 8.50 (lcsc) |
| resistor | 10k | R_0603_1608Metric |  | 12 | 0 | 14 | [C25804](https://www.lcsc.com/product-detail/C25804.html) 0.005 | [chercher](https://www.mouser.fr/c/?q=10k%200603) 0.10 | 0.07 (lcsc) |
| resistor | 1k | R_0603_1608Metric |  | 9 | 0 | 10 | [C21190](https://www.lcsc.com/product-detail/C21190.html) 0.005 | [chercher](https://www.mouser.fr/c/?q=1k%200603) 0.10 | 0.05 (lcsc) |
| capacitor | 10n | C_0603_1608Metric |  | 8 | 0 | 9 | [C57112](https://www.lcsc.com/product-detail/C57112.html) 0.010 | [chercher](https://www.mouser.fr/c/?q=10n%200603) 0.12 | 0.09 (lcsc) |
| ic | DRV5055A3 | SOT-23 | DRV5055A3QDBZR | 6 | 0 | 7 | [C266128](https://www.lcsc.com/product-detail/C266128.html) 0.440 | [595-DRV5055A3QDBZR](https://www.mouser.fr/ProductDetail/595-DRV5055A3QDBZR) 0.60 | 3.08 (lcsc) |
| resistor | 0R | R_0603_1608Metric |  | 5 | 0 | 6 | [C21189](https://www.lcsc.com/product-detail/C21189.html) 0.005 | [chercher](https://www.mouser.fr/c/?q=0R%200603) 0.10 | 0.03 (lcsc) |
| capacitor | 10u/25V | C_1206_3216Metric |  | 4 | 0 | 5 | [C13585](https://www.lcsc.com/product-detail/C13585.html) 0.030 | [chercher](https://www.mouser.fr/c/?q=10u%2F25V%201206) 0.25 | 0.15 (lcsc) |
| capacitor | 15p | C_0603_1608Metric |  | 4 | 0 | 5 | [C1644](https://www.lcsc.com/product-detail/C1644.html) 0.010 | [chercher](https://www.mouser.fr/c/?q=15p%200603) 0.12 | 0.05 (lcsc) |
| capacitor | 1u | C_0603_1608Metric |  | 4 | 0 | 5 | [C15849](https://www.lcsc.com/product-detail/C15849.html) 0.010 | [chercher](https://www.mouser.fr/c/?q=1u%200603) 0.12 | 0.05 (lcsc) |
| capacitor | 220p | C_0603_1608Metric |  | 4 | 0 | 5 | [C1653](https://www.lcsc.com/product-detail/C1653.html) 0.010 | [chercher](https://www.mouser.fr/c/?q=220p%200603) 0.12 | 0.05 (lcsc) |
| capacitor | 56p | C_0603_1608Metric |  | 4 | 0 | 5 |  0.010 | [chercher](https://www.mouser.fr/c/?q=56p%200603) 0.12 | 0.05 (lcsc) |
| inductor | 560n | L_0805_2012Metric | FHW0805UCR56JGT | 4 | 0 | 5 | [C139264](https://www.lcsc.com/product-detail/C139264.html) 0.032 | [chercher](https://www.mouser.fr/c/?q=FHW0805UCR56JGT) 0.30 | 0.16 (lcsc) |
| capacitor | 10p | C_0402_1005Metric |  | 0 | 3 | 4 |  0.005 | [chercher](https://www.mouser.fr/c/?q=10p%200402) 0.10 | 0.02 (lcsc) |
| capacitor | 15p | C_0402_1005Metric |  | 0 | 3 | 4 |  0.005 | [chercher](https://www.mouser.fr/c/?q=15p%200402) 0.10 | 0.02 (lcsc) |
| capacitor | 1n | C_0603_1608Metric |  | 2 | 1 | 4 | [C1588](https://www.lcsc.com/product-detail/C1588.html) 0.010 | [chercher](https://www.mouser.fr/c/?q=1n%200603) 0.12 | 0.04 (lcsc) |
| capacitor | 22p | C_0402_1005Metric |  | 0 | 3 | 4 |  0.005 | [chercher](https://www.mouser.fr/c/?q=22p%200402) 0.10 | 0.02 (lcsc) |
| resistor | 0R47 | R_0603_1608Metric |  | 2 | 0 | 3 |  0.005 | [chercher](https://www.mouser.fr/c/?q=0R47%200603) 0.10 | 0.01 (lcsc) |
| resistor | 0R68 | R_0603_1608Metric |  | 2 | 0 | 3 |  0.005 | [chercher](https://www.mouser.fr/c/?q=0R68%200603) 0.10 | 0.01 (lcsc) |
| resistor | 1R | R_0603_1608Metric |  | 2 | 0 | 3 |  0.005 | [chercher](https://www.mouser.fr/c/?q=1R%200603) 0.10 | 0.01 (lcsc) |
| capacitor | 33p | C_0603_1608Metric |  | 2 | 0 | 3 |  0.010 | [chercher](https://www.mouser.fr/c/?q=33p%200603) 0.12 | 0.03 (lcsc) |
| capacitor | 3p3 | C_0603_1608Metric |  | 2 | 0 | 3 |  0.010 | [chercher](https://www.mouser.fr/c/?q=3p3%200603) 0.12 | 0.03 (lcsc) |
| capacitor | 470p | C_0603_1608Metric |  | 2 | 0 | 3 |  0.010 | [chercher](https://www.mouser.fr/c/?q=470p%200603) 0.12 | 0.03 (lcsc) |
| resistor | 5k1 | R_0603_1608Metric |  | 2 | 0 | 3 | [C23186](https://www.lcsc.com/product-detail/C23186.html) 0.005 | [chercher](https://www.mouser.fr/c/?q=5k1%200603) 0.10 | 0.01 (lcsc) |
| capacitor | 5p6 | C_0603_1608Metric |  | 2 | 0 | 3 |  0.010 | [chercher](https://www.mouser.fr/c/?q=5p6%200603) 0.12 | 0.03 (lcsc) |
| capacitor | 680p | C_0603_1608Metric |  | 2 | 0 | 3 |  0.010 | [chercher](https://www.mouser.fr/c/?q=680p%200603) 0.12 | 0.03 (lcsc) |
| capacitor | 82p | C_0603_1608Metric |  | 2 | 0 | 3 |  0.010 | [chercher](https://www.mouser.fr/c/?q=82p%200603) 0.12 | 0.03 (lcsc) |
| ic | MFRC52202HN1,151 | HVQFN-32-1EP_5x5mm_P0.5mm_EP3.1x3.1mm | MFRC52202HN1,151 | 2 | 0 | 3 | [C11322](https://www.lcsc.com/product-detail/C11322.html) 2.570 | [771-MFRC52202HN1151](https://www.mouser.fr/ProductDetail/771-MFRC52202HN1151) 6.84 | 7.71 (lcsc) |
| switch | BOOT | SW_SPST_PTS645 | PTS645SM43SMTR92 | 2 | 0 | 3 | [C221929](https://www.lcsc.com/product-detail/C221929.html) 0.100 | [611-PTS645SM43SMTR92LFS](https://www.mouser.fr/ProductDetail/611-PTS645SM43SMTR92LFS) 0.20 | 0.30 (lcsc) |
| jumper | R1b bypass | SolderJumper-2_P1.3mm_Bridged_Pad1.0x1.5mm |  | 2 | 0 | 3 |  0.000 | [chercher](https://www.mouser.fr/c/?q=R1b%20bypass%20P1.3mm) 0.00 | 0.00 (lcsc) |
| other | 27.12MHz | Crystal_SMD_3225-4Pin_3.2x2.5mm | X32252712MMB4SI | 2 | 0 | 3 | [C29975](https://www.lcsc.com/product-detail/C29975.html) 0.064 | [chercher](https://www.mouser.fr/c/?q=X32252712MMB4SI) 0.50 | 0.19 (lcsc) |
| resistor | 100k | R_0603_1608Metric |  | 0 | 1 | 2 | [C25803](https://www.lcsc.com/product-detail/C25803.html) 0.005 | [chercher](https://www.mouser.fr/c/?q=100k%200603) 0.10 | 0.01 (lcsc) |
| diode | LED | LED_0603_1608Metric | 19-217/GHC-YR1S2/3T | 1 | 0 | 2 | [C72043](https://www.lcsc.com/product-detail/C72043.html) 0.020 | [chercher](https://www.mouser.fr/c/?q=19-217%2FGHC-YR1S2%2F3T) 0.15 | 0.04 (lcsc) |
| resistor | 3k3 | R_0603_1608Metric |  | 1 | 0 | 2 |  0.005 | [chercher](https://www.mouser.fr/c/?q=3k3%200603) 0.10 | 0.01 (lcsc) |
| resistor | 3k9 | R_0603_1608Metric |  | 1 | 0 | 2 |  0.005 | [chercher](https://www.mouser.fr/c/?q=3k9%200603) 0.10 | 0.01 (lcsc) |
| connector | 5V BENCH | PinHeader_1x02_P2.54mm_Vertical |  | 1 | 0 | 2 |  0.100 | [chercher](https://www.mouser.fr/c/?q=5V%20BENCH%201x02) 0.30 | 0.20 (lcsc) |
| ic | 74LVC125 | TSSOP-14_4.4x5mm_P0.65mm | 74LVC125APW,118 | 1 | 0 | 2 | [C6059](https://www.lcsc.com/product-detail/C6059.html) 0.200 | [771-74LVC125APW118](https://www.mouser.fr/ProductDetail/771-74LVC125APW118) 0.45 | 0.40 (lcsc) |
| ic | AMS1117-3.3 | SOT-223-3_TabPin2 | AMS1117-3.3 | 1 | 0 | 2 | [C6186](https://www.lcsc.com/product-detail/C6186.html) 0.055 | [511-LD1117S33TR](https://www.mouser.fr/ProductDetail/511-LD1117S33TR) 0.40 | 0.11 (lcsc) |
| transistor | AO3401A | SOT-23 | AO3401A | 1 | 0 | 2 | [C15127](https://www.lcsc.com/product-detail/C15127.html) 0.052 | [785-AO3401A](https://www.mouser.fr/ProductDetail/785-AO3401A) 0.30 | 0.10 (lcsc) |
| diode | BAT15-03W | D_SOD-323 | BAT15-03W | 0 | 1 | 2 | [chercher](https://www.lcsc.com/search?q=BAT15-03W) 0.300 | [726-BAT15-03W](https://www.mouser.fr/ProductDetail/726-BAT15-03W) 0.45 | 0.60 (lcsc) |
| ic | CD74HC4067 | SSOP-24_5.3x8.2mm_P0.65mm | CD74HC4067SM96 | 1 | 0 | 2 | [C98457](https://www.lcsc.com/product-detail/C98457.html) 0.267 | [595-CD74HC4067SM96](https://www.mouser.fr/ProductDetail/595-CD74HC4067SM96) 1.17 | 0.53 (lcsc) |
| ic | ESP32-S3-WROOM-1-N8 | ESP32-S3-WROOM-1 | ESP32-S3-WROOM-1-N8 | 1 | 0 | 2 | [C2913198](https://www.lcsc.com/product-detail/C2913198.html) 3.300 | [356-ESP32S3WRM1N8](https://www.mouser.fr/ProductDetail/356-ESP32S3WRM1N8) 4.50 | 6.60 (lcsc) |
| jumper | HALL_VCC bypass | SolderJumper-2_P1.3mm_Open_Pad1.0x1.5mm |  | 1 | 0 | 2 |  0.000 | [chercher](https://www.mouser.fr/c/?q=HALL_VCC%20bypass%20P1.3mm) 0.00 | 0.00 (lcsc) |
| connector | MUX EXT | PinHeader_1x06_P2.54mm_Vertical |  | 1 | 0 | 2 |  0.100 | [chercher](https://www.mouser.fr/c/?q=MUX%20EXT%201x06) 0.30 | 0.20 (lcsc) |
| connector | PICKUP | PinHeader_1x03_P2.54mm_Vertical |  | 1 | 0 | 2 |  0.100 | [chercher](https://www.mouser.fr/c/?q=PICKUP%201x03) 0.30 | 0.20 (lcsc) |
| capacitor | 22u/10V tantale | CP_EIA-3528-21_Kemet-B | TAJB226K010RNJ | 1 | 0 | 2 | [chercher](https://www.lcsc.com/search?q=TAJB226K010RNJ) 0.300 | [581-TAJB226K010RNJ](https://www.mouser.fr/ProductDetail/581-TAJB226K010RNJ) 0.40 | 0.60 (lcsc) |
| connector | USB-C | USB_C_Receptacle_GCT_USB4085 | USB4085-GF-A | 1 | 0 | 2 | [C2988369](https://www.lcsc.com/product-detail/C2988369.html) 0.600 | [640-USB4085-GF-A](https://www.mouser.fr/ProductDetail/640-USB4085-GF-A) 0.70 | 1.20 (lcsc) |
| ic | USBLC6-2 | SOT-23-6 | USBLC6-2SC6 | 1 | 0 | 2 | [C7519](https://www.lcsc.com/product-detail/C7519.html) 0.090 | [511-USBLC6-2SC6](https://www.mouser.fr/ProductDetail/511-USBLC6-2SC6) 0.45 | 0.18 (lcsc) |

## Totaux

| Poste | USD | EUR TTC |
|---|---|---|
| Composants, tout chez LCSC (lignes qui y existent) | 32 | 35 |
| Composants, tout chez Mouser (lignes qui y existent) | 85 | 94 |
| Composants, le moins cher ligne à ligne | 32 | 35 |
| PCB_100x100_4L_x5 | 30 | 33 |
| PCB_100x87_2L_0.8_x5 | 8 | 9 |
| PCBA_standard_2_boards | 60 | 66 |
| Shipping_JLCPCB | 25 | 28 |
| Shipping_Mouser | 20 | 22 |
| Magnets_ferrite_12_15_18x4 | 12 | 13 |
| NanoVNA-H | 70 | 77 |
| **Total, le moins cher ligne à ligne, cartes et port compris** | **257** | **284** |

## Non monté sur le démonstrateur

- carte carte : C114, C117, C124, C127, C214, C217, C224, C227, J101, J102, J201, J202, J4, R132, R143, R232, R243
- carte étiquettes : C1, C2, C3, C7, C8, C9
