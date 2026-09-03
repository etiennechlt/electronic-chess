# Note 12 : protocole plateau, pont radio et horloge

Trois maillons parlent entre eux : le STM32 du cerveau (maître de la
partie), l'ESP32-S3 du cerveau (pont radio, BLE et WiFi) et
l'ESP32-S3 de l'horloge. Le même protocole texte circule partout, pour
qu'un terminal série suffise à tout observer et à tout simuler.

## 1. Liaison série STM32 vers ESP32 (et Pi)

USART1 du STM32 (PA9 TX, PA10 RX), 115200 bauds, 8N1, à travers
l'ADuM1201 du cerveau. Le même port sert de console de mise au point :
les commandes à un caractère de `firmware/board/src/cli.c` restent
valables, le pont les transmet telles quelles.

Format : une ligne ASCII par message, terminée par `\n`, champs
séparés par des virgules, premier champ = type. Pas de binaire, pas de
somme de contrôle (liaison courte, isolée, à 115200 bauds) ; une ligne
mal formée est ignorée et comptée.

Messages du plateau (STM32) vers le pont :

| Ligne | Sens | Contenu |
|-------|------|---------|
| `B,<64 caractères>` | plateau | occupation : `.` vide, `w` blanc, `b` noir, `?` inconnu, case a1 en premier, puis b1... h8 |
| `M,<coup>` | plateau | coup détecté au format UCI (`e2e4`, `e7e8q`) |
| `F,<FEN>` | plateau | position complète après un coup validé |
| `S,<état>` | plateau | `idle`, `setup`, `playing`, `ended:<raison>` |
| `E,<texte>` | plateau | erreur ou avertissement (case illisible, pièce manquante) |
| `P,<tension_mV>,<courant_mA>,<pourcent>` | plateau | état batterie relayé de l'INA219 |

Messages du pont (ou de l'horloge, ou d'un PC) vers le plateau :

| Ligne | Contenu |
|-------|---------|
| `N,<mode>,<base_s>,<increment_s>` | nouvelle partie : mode `fischer`, `bronstein`, `simple`, `free` |
| `C,<blanc_ms>,<noir_ms>,<trait>` | temps courants, envoyé par l'horloge chaque seconde et à chaque pression |
| `T,<couleur>` | trait passé à `w` ou `b` (pression sur la barre) |
| `R,<couleur>,<raison>` | fin : abandon (`resign`), drapeau (`flag`), nulle (`draw`) |
| `L,<case>,<r>,<g>,<b>` | allumer une case (0 à 63), pour l'aide au coup adverse (Lichess, moteur) |
| `X,<coup>` | coup de l'adversaire distant à jouer sur le plateau |
| `Q` | demande d'état : le plateau répond `B`, `F`, `S`, `P` |

Le STM32 est la seule autorité sur la légalité des coups : l'horloge
ne fait que compter et signaler les pressions. Un `T` reçu alors que la
pièce n'a pas encore été reposée est mémorisé et appliqué au coup
suivant.

## 2. BLE entre le pont et l'horloge

Service Nordic UART (NUS, UUID `6E400001-B5A3-F393-E0A9-E50E24DCCA9E`)
exposé par le pont en périphérique, l'horloge est centrale : elle
cherche le nom `echecs-<4 hex>` (dérivé de l'adresse MAC), se
connecte, active les notifications sur TX et écrit les lignes sur RX.
Chaque notification porte une ligne entière (MTU demandé 247 octets,
la ligne `B` fait 66 octets, la `F` moins de 100). Les lignes sont
relayées sans transformation : ce que le STM32 émet arrive tel quel à
l'horloge et inversement.

Au raccrochage de la liaison, l'horloge continue de compter seule et
resynchronise par un `C` à la reconnexion ; le plateau continue
d'arbitrer sans horloge (cadence `free`).

## 3. Rôle du pont

- relais série vers BLE (horloge) et vers un client BLE générique
  (téléphone, pour la mise au point) ;
- plus tard WiFi vers l'API Board de Lichess : le pont traduit les
  coups `M` en requêtes `move` et les coups adverses en `X`, les
  temps de la partie en `C` ;
- interface de flashage USB du STM32 par le pont non prévue : le SWD
  reste le chemin de programmation.

## 4. Logique de l'horloge

Modes : `fischer` (incrément ajouté après chaque coup), `bronstein`
(délai restitué au plus la durée du coup), `simple` (pas d'incrément),
`free` (aucun compte, seul le trait est suivi). Pressions sur la barre :
côté blanc enfoncé = les blancs viennent de jouer, le trait passe aux
noirs. Le buzzer sonne trois fois au drapeau, une fois à 10 s. Le menu
sur l'encodeur : cadence (presets 3+2, 5+0, 10+0, 15+10, 30+0,
90+30), mode, luminosité, appairage.

## 5. Ce qui manque

- Génération des coups et validation dans le STM32 (aujourd'hui le
  firmware du cerveau expose la mesure brute et une classification par
  case, pas encore la logique d'échecs).
- Chiffrement BLE (appairage « juste ça marche » pour commencer).
- Client Lichess sur le pont.
