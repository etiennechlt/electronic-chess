# Échiquier électronique automatique à détection LC

Échiquier physique qui identifie chaque pièce (type et couleur) par
résonateur LC passif embarqué dans la base, déplace les pièces par un
aimant sur portique CoreXY sous le plateau, arbitre les coups (roque,
prise en passant, promotion incluse), joue contre un moteur d'échecs ou
en ligne, et fonctionne sur batterie. Le STM32G474 est maître, le
Raspberry Pi Zero 2 W est optionnel et coupé au repos.

Principe de détection : chaque pièce porte une bobine plate de 45 µH et
un condensateur C0G 1 % de la série E12 qui fixe sa classe (12 valeurs,
217 à 612 kHz). Chaque case excite en large bande par un front raide,
écoute le ringdown, et classifie au plus proche voisin sur des
fréquences calibrées par pièce. L'aimant de pièce est en ferrite dure,
transparent au champ de mesure ; celui du chariot en néodyme N42.

## Source de vérité unique

Toute valeur numérique du projet vient de [`config/board.yaml`](config/board.yaml).
Les grandeurs dérivées (12 fréquences, diamètres, courses, entrefer,
autonomie) sont calculées par la bibliothèque `chessboard_calc` et
épinglées par les tests contre la spécification. Le pas de case `p`
(40 ou 50 mm) reste ouvert : tout est paramétrique.

## Démarrage rapide

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pytest                                # tous les garde-fous
.venv/bin/python -m chessboard_calc report --pitch all   # tables dérivées
```

Le test `tests/test_corridor.py` verrouille la contrainte de couloir
`r_mobile + r_statique <= p/2` pour les 21 paires de classes : si une
édition de `board.yaml` la viole, la CI casse, car la partie se
bloquerait dès e2-e4.

## Arborescence

| Répertoire | Contenu | Phase |
|---|---|---|
| `config/` | `board.yaml`, source de vérité unique | 0 |
| `chessboard_calc/` | calculs paramétriques (inductance, résonance, couloir, couplage, puissance) | 0 |
| `tests/` | garde-fous CI | 0 |
| `docs/adr/` | journal des décisions d'architecture | 0 |
| `tools/coilgen/` | générateur de spirales KiCad | 1 |
| `hardware/mockup-2x2/` | maquette KiCad 100 x 100 mm | 1 |
| `firmware/mockup/` | voies A et B, calibration, CSV sur UART | 1 |
| `measurements/` | protocole des 8 mesures, relevés, notebook | 1 |
| `hardware/quadrant-4x4/`, `hardware/mainboard/` | plateau complet | 2 |
| `firmware/board/` | firmware complet | 2 |
| `mechanical/` | modèles CadQuery pilotés par `board.yaml` | 3 |
| `app/` | service Pi : Stockfish, Lichess, PGN, UART | 4 |

## État

Phase 0 livrée : socle du dépôt, configuration unique, bibliothèque de
calculs et garde-fous CI. Prochaine étape : la maquette 2 x 2 (phase 1),
qui tranche l'essentiel de l'incertitude technique pour environ 70 EUR ;
la mesure décisive est la chute de Q avec l'aimant ferrite posé.

Les décisions déjà prises et leurs justifications sont dans
[`docs/adr/`](docs/adr/README.md). Conventions du projet : code,
identifiants et commentaires en anglais ; documentation en français.
