# Journal des décisions d'architecture

Chaque décision structurante du projet est consignée ici, avec son
contexte et ses conséquences. Les décisions marquées « ouverte » sont
paramétrées dans `config/board.yaml` et seront tranchées sur mesures.

| ADR | Titre | Statut |
|---|---|---|
| [0001](0001-lc-resonators-for-piece-identification.md) | Identification des pièces par résonateurs LC passifs | acceptée |
| [0002](0002-hard-ferrite-piece-magnets.md) | Aimant de pièce en ferrite dure, jamais en néodyme | acceptée |
| [0003](0003-stm32-master-pi-optional.md) | STM32 maître, Raspberry Pi optionnel | acceptée |
| [0004](0004-four-quadrant-sensing-pcb.md) | PCB de détection découpé en 4 quadrants | acceptée |
| [0005](0005-power-and-noise-architecture.md) | Architecture d'alimentation et plan anti-bruit | acceptée |
| [0006](0006-pitch-parametric-open.md) | Pas de case paramétrique, 40 ou 50 mm | ouverte |
| [0007](0007-frequency-extraction-dual-path.md) | Extraction de fréquence : FFT et capture de période | ouverte |
