# Nomenclature du démonstrateur A, détection LC par oscillations

Générée par `python3 tools/demobom.py --model a` le 17/10/2026 depuis les
`bom.csv` des cartes et `docs/prix-demonstrateur.csv`. Les quantités
sont celles des cartes ; la colonne « achat » ajoute la rechange de
10 % par ligne (au moins une pièce, deux au-delà de dix). Les prix
sont en USD à l'unité ou à la petite série, datés dans la fiche de
prix, « vérifié » ou « estimé » ; chaque lien ouvre la page ou la
recherche du distributeur, à relire le jour de la commande. Conversion
1 USD = 0.92 EUR, TVA 20 % ajoutée dans les totaux.

## Composants

| Repères | Valeur | Empreinte | MPN | bobines | analogique | Achat | LCSC (USD) | Mouser (USD) | Moins cher |
|---|---|---|---|---|---|---|---|---|---|
| resistor | 100k | R_0603_1608Metric |  | 0 | 13 | 15 |  0.005 | [chercher](https://www.mouser.fr/c/?q=100k%200603) 0.10 | 0.07 (lcsc) |
| resistor | 10k | R_0603_1608Metric |  | 0 | 10 | 12 |  0.005 | [chercher](https://www.mouser.fr/c/?q=10k%200603) 0.10 | 0.06 (lcsc) |
| diode | BAV99 | SOT-23 | BAV99 | 0 | 9 | 10 | [C2500](https://www.lcsc.com/product-detail/C2500.html) 0.020 | [771-BAV99-T/R](https://www.mouser.fr/ProductDetail/771-BAV99-T%2FR) 0.15 | 0.20 (lcsc) |
| resistor | 330R | R_0603_1608Metric |  | 0 | 8 | 9 |  0.005 | [chercher](https://www.mouser.fr/c/?q=330R%200603) 0.10 | 0.04 (lcsc) |
| capacitor | 100n | C_0603_1608Metric |  | 0 | 7 | 8 |  0.010 | [chercher](https://www.mouser.fr/c/?q=100n%200603) 0.12 | 0.08 (lcsc) |
| transistor | AO3400A | SOT-23 | AO3400A | 0 | 5 | 6 | [C20917](https://www.lcsc.com/product-detail/C20917.html) 0.040 | [785-AO3400A](https://www.mouser.fr/ProductDetail/785-AO3400A) 0.30 | 0.24 (lcsc) |
| transistor | AO3401A | SOT-23 | AO3401A | 0 | 5 | 6 | [C15127](https://www.lcsc.com/product-detail/C15127.html) 0.052 | [785-AO3401A](https://www.mouser.fr/ProductDetail/785-AO3401A) 0.30 | 0.31 (lcsc) |
| diode | SS34 | D_SMA | SS34 | 0 | 5 | 6 | [C8678](https://www.lcsc.com/product-detail/C8678.html) 0.040 | [833-SS34](https://www.mouser.fr/ProductDetail/833-SS34) 0.30 | 0.24 (lcsc) |
| resistor | 680R | R_0805_2012Metric |  | 0 | 4 | 5 |  0.010 | [chercher](https://www.mouser.fr/c/?q=680R%200805) 0.10 | 0.05 (lcsc) |
| diode | B5819W | D_SOD-123 | B5819W | 0 | 4 | 5 | [C8598](https://www.lcsc.com/product-detail/C8598.html) 0.030 | [chercher](https://www.mouser.fr/c/?q=B5819W) 0.25 | 0.15 (lcsc) |
| resistor | 1k | R_0603_1608Metric |  | 0 | 3 | 4 |  0.005 | [chercher](https://www.mouser.fr/c/?q=1k%200603) 0.10 | 0.02 (lcsc) |
| capacitor | 1n | C_0603_1608Metric |  | 0 | 3 | 4 |  0.010 | [chercher](https://www.mouser.fr/c/?q=1n%200603) 0.12 | 0.04 (lcsc) |
| capacitor | 1u | C_0603_1608Metric |  | 0 | 3 | 4 |  0.010 | [chercher](https://www.mouser.fr/c/?q=1u%200603) 0.12 | 0.04 (lcsc) |
| capacitor | 330p | C_0603_1608Metric |  | 0 | 2 | 3 |  0.010 | [chercher](https://www.mouser.fr/c/?q=330p%200603) 0.12 | 0.03 (lcsc) |
| resistor | 590R | R_0603_1608Metric |  | 0 | 2 | 3 |  0.005 | [chercher](https://www.mouser.fr/c/?q=590R%200603) 0.10 | 0.01 (lcsc) |
| resistor | 750R | R_0603_1608Metric |  | 0 | 2 | 3 |  0.005 | [chercher](https://www.mouser.fr/c/?q=750R%200603) 0.10 | 0.01 (lcsc) |
| resistor | 787R | R_0603_1608Metric |  | 0 | 2 | 3 |  0.005 | [chercher](https://www.mouser.fr/c/?q=787R%200603) 0.10 | 0.01 (lcsc) |
| ic | OPA2810 | SOIC-8_3.9x4.9mm_P1.27mm | OPA2810IDR | 0 | 2 | 3 | [C2059830](https://www.lcsc.com/product-detail/C2059830.html) | [595-OPA2810IDR](https://www.mouser.fr/ProductDetail/595-OPA2810IDR) 5.48 | 16.44 (mouser) |
| resistor | 10R | R_2512_6332Metric |  | 0 | 1 | 2 |  0.050 | [chercher](https://www.mouser.fr/c/?q=10R%202512) 0.30 | 0.10 (lcsc) |
| capacitor | 10n | C_0603_1608Metric |  | 0 | 1 | 2 |  0.010 | [chercher](https://www.mouser.fr/c/?q=10n%200603) 0.12 | 0.02 (lcsc) |
| capacitor | 10u/10V | C_1206_3216Metric |  | 0 | 1 | 2 |  0.030 | [chercher](https://www.mouser.fr/c/?q=10u%2F10V%201206) 0.25 | 0.06 (lcsc) |
| capacitor | 10u/25V | C_1206_3216Metric |  | 0 | 1 | 2 |  0.030 | [chercher](https://www.mouser.fr/c/?q=10u%2F25V%201206) 0.25 | 0.06 (lcsc) |
| resistor | 20k5 | R_0603_1608Metric |  | 0 | 1 | 2 |  0.005 | [chercher](https://www.mouser.fr/c/?q=20k5%200603) 0.10 | 0.01 (lcsc) |
| capacitor | 2u2 | C_0603_1608Metric |  | 0 | 1 | 2 |  0.010 | [chercher](https://www.mouser.fr/c/?q=2u2%200603) 0.12 | 0.02 (lcsc) |
| resistor | 3.57k | R_0603_1608Metric |  | 0 | 1 | 2 |  0.005 | [chercher](https://www.mouser.fr/c/?q=3.57k%200603) 0.10 | 0.01 (lcsc) |
| capacitor | 47u/25V | CP_Elec_6.3x7.7 |  | 0 | 1 | 2 |  0.100 | [chercher](https://www.mouser.fr/c/?q=47u%2F25V%20Elec) 0.40 | 0.20 (lcsc) |
| resistor | 49R9 | R_0603_1608Metric |  | 0 | 1 | 2 |  0.005 | [chercher](https://www.mouser.fr/c/?q=49R9%200603) 0.10 | 0.01 (lcsc) |
| resistor | 523R | R_0603_1608Metric |  | 0 | 1 | 2 |  0.005 | [chercher](https://www.mouser.fr/c/?q=523R%200603) 0.10 | 0.01 (lcsc) |
| jumper | 5VA: 1 buck / 3 LDO | PinHeader_1x03_P2.54mm_Vertical |  | 0 | 1 | 2 |  0.100 | [chercher](https://www.mouser.fr/c/?q=5VA%3A%201%20buck%20%2F%203%20LDO%201x03) 0.30 | 0.20 (lcsc) |
| ic | 74HC4052 | TSSOP-16_4.4x5mm_P0.65mm | 74HCT4052PW | 0 | 1 | 2 | [C57078](https://www.lcsc.com/product-detail/C57078.html) 0.151 | [771-74HCT4052PW118](https://www.mouser.fr/ProductDetail/771-74HCT4052PW118) 0.60 | 0.30 (lcsc) |
| ic | AD8421 | SOIC-8_3.9x4.9mm_P1.27mm | AD8421ARZ | 0 | 1 | 2 | [C392903](https://www.lcsc.com/product-detail/C392903.html) 3.691 | [584-AD8421ARZ](https://www.mouser.fr/ProductDetail/584-AD8421ARZ) 8.91 | 7.38 (lcsc) |
| connector | COIL JOINT | PinHeader_1x12_P2.54mm_Vertical |  | 0 | 1 | 2 |  0.100 | [chercher](https://www.mouser.fr/c/?q=COIL%20JOINT%201x12) 0.30 | 0.20 (lcsc) |
| connector | 12V | BarrelJack_Horizontal | DC-005-5.5x2.1 | 0 | 1 | 2 | [C381118](https://www.lcsc.com/product-detail/C381118.html) 0.200 | [chercher](https://www.mouser.fr/c/?q=DC-005-5.5x2.1) 0.80 | 0.40 (lcsc) |
| ic | LP2985-5.0 | SOT-23-5 | LP2985AIM5-5.0 | 0 | 1 | 2 | [C129541](https://www.lcsc.com/product-detail/C129541.html) 0.165 | [926-LP2985AIM5-5.0NOPB](https://www.mouser.fr/ProductDetail/926-LP2985AIM5-5.0NOPB) 0.60 | 0.33 (lcsc) |
| connector | MCU | PinHeader_2x10_P2.54mm_Vertical |  | 0 | 1 | 2 |  0.100 | [chercher](https://www.mouser.fr/c/?q=MCU%202x10) 0.30 | 0.20 (lcsc) |
| diode | SMBJ15A | D_SMB | SMBJ15A | 0 | 1 | 2 | [C113962](https://www.lcsc.com/product-detail/C113962.html) 0.100 | [576-SMBJ15A](https://www.mouser.fr/ProductDetail/576-SMBJ15A) 0.40 | 0.20 (lcsc) |

## Totaux

| Poste | USD | EUR TTC |
|---|---|---|
| Composants, tout chez LCSC (lignes qui y existent) | 11 | 13 |
| Composants, tout chez Mouser (lignes qui y existent) | 60 | 67 |
| Composants, le moins cher ligne à ligne | 28 | 31 |
| NUCLEO-G474RE | 20 | 22 |
| PCB_100x100_4L_x5 | 30 | 33 |
| PCB_100x62_2L_x5 | 4 | 4 |
| Shipping_JLCPCB | 25 | 28 |
| Shipping_Mouser | 20 | 22 |
| **Total, le moins cher ligne à ligne, cartes et port compris** | **126** | **139** |

## Non monté sur le démonstrateur

- carte analogique : C26, C27, C4, C5, C6, C7, C8, FB1, J5, JP3, L1, R1, R2, R3, R4, R66, R67, R68, U1, U7, U8
