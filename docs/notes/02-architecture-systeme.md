# 02. Architecture système et budget de bruit

## Vue d'ensemble

Le système final : un plateau qui identifie les pièces (LC passifs,
[note 01](01-principe-de-mesure.md)), les déplace par un aimant N42
sur un portique CoreXY sous le plateau, et affiche le camp occupant
chaque case par deux points lumineux (ADR 0009). Cerveau temps réel :
STM32G474 ; un Raspberry Pi Zero 2 W optionnel (moteur d'échecs,
réseau) parle au MCU par UART isolée. La maquette 2 x 2 de phase 1
matérialise la chaîne de mesure complète et les LED, sans portique.

## Le plateau 8 x 8 (ADR 0010)

Un module plateau invariant (contreplaqué plus quatre quadrants 4 x 4
identiques, chacun avec ses 16 spirales, 32 LED et son frontal
analogique en bande de bord) posé dans une base fine (21 mm) ou une
base chariot (54 mm, CoreXY et ailes de capture). Au fond de la base :
cerveau (STM32G474 soudé, quatre nappes de quadrant, LED, alimentation
bas niveau, emplacement ESP32-S3 et Pi), carte puissance (BMS 3S,
USB-C PD) et trois cellules plates. Une horloge à bascule séparée,
en BLE, choisit les modes et affiche les temps. Détail et raisons dans
la [note 10](10-plateau-8x8-et-horloge.md).

## Les deux cartes de la maquette (ADR 0008, remplacée)

La maquette n'est plus construite ; sa chaîne analogique reste la
référence du frontal de quadrant.


- **Carte bobines** (100 x 100, 4 couches) : 4 spirales de détection,
  8 LED WS2812B aux coins des cases, entièrement générée par
  `coilgen`. Sous la surface en bois.
- **Carte analogique** (100 x 62, 2 couches, format shield Nucleo) :
  mux différentiel 74HCT4052 (seuils TTL pilotables en 3,3 V, c'est
  le point qui a écarté l'ADG709), polarisation des bobines à
  VREF = 1,65 V, écrêtage 330R + BAV99 devant le mux, excitation par
  FET dédié par case depuis un rail commuté, amortisseur P-FET + 680R,
  AD8421 G = 20, deux Sallen-Key (PH 200 kHz, PB 650 kHz), étage de
  sortie, tampon 74AHCT1G125 pour les LED. Générée par `analoggen`.
- **Joint** : connecteur 12 broches bord à bord
  (GND, A1 B1 A3 B3 A4 B4 A2 B2, GND, LED_DIN, 5V), positions
  calculées du yaml des deux côtés, égalité verrouillée par test.

## Budget de bruit (ADR 0005)

Le signal utile est en microvolts dans 200 à 650 kHz ; tout est
organisé pour que rien de numérique n'émette dedans :

- Buck TPS62150 à 2,2 MHz en forced PWM (fondamentale hors bande) ;
  un cavalier le met en PFM et un second bascule sur un LDO LP2985
  pour la mesure comparative M8. Verdict attendu : si l'écart est
  < 3 dB, le buck seul suffit au plateau final.
- Île analogique 5VA séparée du rail numérique ; la ferrite et les
  découplages tiennent la frontière. Les LED et leur tampon sont sur
  le rail numérique, jamais sur 5VA.
- Mesure différentielle de bout en bout jusqu'à l'AD8421.
- Passe-bande d'ordre 4 : la réjection réelle à 1,5 MHz est ~18 dB
  (validée ngspice), pas les 32 dB supposés au brief initial ; c'est
  documenté et assumé, la moyenne x16 et le fenêtrage font le reste.
- UART du Pi isolée par ADuM1201 (le WiFi du Pi est le pire voisin).
- Trames LED (800 kHz, en pleine bande) uniquement hors fenêtres de
  mesure, garanti par la structure du firmware (ADR 0009, mesure M11).

## Contraintes mécaniques structurantes

- **Couloir** : une pièce en mouvement doit passer entre deux pièces
  posées, d'où r_mobile + r_statique <= p/2. C'est LE garde-fou :
  `tests/test_corridor.py` est bloquant en CI, toute modification du
  yaml qui le viole échoue.
- **Aimants pièces en ferrite** (SrFe, Y30) et non néodyme
  (ADR 0002) : décision pivot, un N42 sous le plateau ne doit pas
  arracher ni retourner les pièces voisines ; la chute de Q induite
  par la ferrite est la mesure décisive M2.
- **Pas p ouvert** (40 ou 50 mm, ADR 0006) : tout le dépôt est
  paramétrique sur p ; la maquette tranche via M4 à M6.

## Alimentation du plateau final

3S2P en 18650 avec BMS ; la maquette, elle, vit sur un bloc 12 V et
l'USB de la Nucleo. Le budget énergie est dans `chessboard_calc.power`
(modèle à surcoût fixe par coup).
