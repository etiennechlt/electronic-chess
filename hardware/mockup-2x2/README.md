# Maquette 2 x 2 : commande, montage, mise en route

Deux cartes (ADR 0008) : la carte bobines (100 x 100, 4 couches,
passive) et la carte analogique (100 x 62, 2 couches, assemblée). Le
MCU est une Nucleo-G474RE du commerce reliée en nappes Dupont.

## 1. Commander

### Carte bobines (~15 EUR les 5)

`sh hardware/mockup-2x2/coil-board/export.sh` produit
`coil-board-gerbers.zip` (aussi commité). JLCPCB : 4 couches, 1,6 mm,
1 oz, pas d'assemblage.

### Carte analogique (~60 EUR les 5 dont 2 assemblées)

`analog-board/` contient le projet KiCad, `jlc-bom.csv` et
`jlc-cpl.csv`. JLCPCB : 2 couches, 1,6 mm, assemblage face top.
Important : les codes LCSC du BOM sont des candidats plausibles saisis
hors ligne ; l'outil de commande JLC rapproche aussi par référence
fabricant (MPN) et signale tout écart : vérifier chaque ligne dans
leur prévisualisation avant de payer, en particulier TPS62150RGTR,
AD8421ARZ, OPA2810IDR, 74HCT4052PW, ADuM1201ARZ. Les composants
introuvables en assemblage (souvent l'AD8421) se commandent chez
Mouser ou DigiKey et se soudent à la main (SOIC, facile).

### Le reste (~70 EUR)

Voir `docs/bom-maquette.md` : Nucleo-G474RE, condensateurs C0G des
résonateurs, fil émaillé, aimants ferrite et N42, contreplaqué sec 3 à 6 mm,
feutre, visserie, impression des pièces de `mechanical/`.

## 2. Assembler

1. Carte analogique : souder les traversants (jack, barrettes J2 J4
   J5, JP1 JP3) ; laisser R66 et R67 non montées (elles court-circuitent
   l'isolateur UART).
2. Carte bobines : souder la barrette coudée 1 x 10 mâle pointant vers
   le nord ; entretoises M3 x 25 aux quatre coins.
3. Emboîter la barrette dans le connecteur femelle coudé J2 de la
   carte analogique : les deux cartes sont coplanaires, broche 1 sur
   broche 1 (x = 38,57 mm sur les deux).
4. Support d'aimant : visser la platine sous S3, monter la coupelle
   sur sa vis M3.
5. Bobiner les 4 résonateurs (gabarits imprimés, fil 0,25 mm, tours
   par classe donnés par `python -m chessboard_calc report`), souder
   chaque condensateur C0G, coller bobine et aimant dans les pucks,
   feutre dessous.
6. Percer la planche de contreplaqué avec le gabarit `surface-template`
   (trous de visserie et points lumineux des LED), puis la poser sur les
   entretoises au dessus de
   la carte bobines.

## 3. Câbler la Nucleo

Nappes Dupont femelle-femelle de J4 vers la Nucleo (UM2505), table
générée depuis `config/board.yaml` (section `nucleo_pins`) :

| J4 | Signal | Nucleo |
|---|---|---|
| 1 | 3V3 | 3V3 |
| 2, 4, 19 | GND | GND |
| 3 | AMP_OUT | A0 (PA0), en pont vers A1 (PA1) pour la voie B |
| 5 | MUX_A0 | D3 (PB3) |
| 6 | MUX_A1 | D4 (PB5) |
| 7 | MUX_INH | D5 (PB4) |
| 8 | PULSE_EN | A2 (PA4) |
| 9 a 12 | DRIVE1..4 | D11 (PA7), D12 (PA6), D14 (PB9), D15 (PB8) |
| 13 a 16 | DAMP1..4_N | D6 (PB10), D7 (PA8), D9 (PC7), D10 (PB6) |
| 17 | MCU_TX | D8 (PA9) |
| 18 | MCU_RX | D2 (PA10) |
| 20 | INA_OUT | libre (oscilloscope) |

## 4. Mise en route

1. Flasher `firmware/mockup` (`make`, copier le .bin sur le lecteur
   NUCLEO). Console VCP 921600 bauds.
2. Alimenter le 12 V (JP1 côté LDO pour commencer, JP3 côté FPWM).
3. `h` puis `s` : quatre lignes CSV. Sans puck, amp_mv doit rester
   faible ; poser un puck doit faire apparaître sa fréquence.
4. Vérifier la voie B au générateur de fonctions sur AMP_OUT (voir
   `firmware/mockup/README.md`, points à vérifier).
5. Dérouler `measurements/protocol.md`.
