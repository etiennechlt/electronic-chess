# Bibliothèques KiCad du projet

Symboles et empreintes que les bibliothèques officielles de KiCad 7
n'ont pas, au même format qu'elles. Les générateurs les cherchent ici
après `/usr/share/kicad` (`analoggen.symlib`, `analoggen.fplib`) et les
embarquent dans les fichiers générés : rien à installer pour ouvrir
une carte.

| Fichier | Contenu | Source |
|---|---|---|
| `hallrfid.kicad_sym` | `MFRC522` (lecteur NFC, HVQFN32, 33 broches dont la pastille centrale) ; `NT3H2111` (puce d'étiquette NTAG I2C plus, TSSOP8 et XQFN8, même numérotation) | tables des broches des fiches NXP (MFRC522 rév. 3.6, paragraphe 7.1 ; NT3H2111_2211) |
| `hallrfid.pretty/NetTie_NFC_Loop.kicad_mod` | amarre de boucle NFC : deux pastilles qui se touchent, groupe `net_tie_pad_groups` ; la spirale dessinée sur la face avant finit sur la pastille 1, le pont de la face arrière part de la pastille 2 | le principe de l'amarre de spirale de `tools/quadgen` |

Le brochage du MFRC522 embarqué : 1 I2C, 2 PVDD, 3 DVDD, 4 DVSS,
5 PVSS, 6 NRSTPD, 7 MFIN, 8 MFOUT, 9 SVDD, 10 TVSS, 11 TX1, 12 TVDD,
13 TX2, 14 TVSS, 15 AVDD, 16 VMID, 17 RX, 18 AVSS, 19 AUX1, 20 AUX2,
21 OSCIN, 22 OSCOUT, 23 IRQ, 24 SDA (NSS en SPI), 25 à 31 D1 à D7
(D5 SCK, D6 MOSI, D7 MISO), 32 EA, 33 pastille centrale. En SPI :
I2C à la masse, EA au 3,3 V.
