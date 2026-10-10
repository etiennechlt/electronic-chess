---
workflow: general-video
flow: automation
storyboard: yes
message: "Chaque coup d'une partie montre une fonction du plateau"
destination: tiktok
aspect: 1080x1920
language: fr
audience: "financement participatif, promo et vlog Instagram et TikTok"
length: 53s
angle: "une partie, du premier coup au mat"
---

## Intent

Film de présentation de l'échiquier à détection LC, version « Une partie,
du premier coup au mat » : le coup du berger joué en entier sur le plateau
en 3D, et chaque coup révèle une fonction (détection par la note de la
pièce, partie en ligne avec les cases qui s'allument, arbitrage du coup
légal, horloge qui bascule seule, suivi d'une prise, fin de partie).
Public : financement participatif, et surtout promo et vlog sur
Instagram et TikTok, donc vertical d'abord. Le titre affiché suit la
version.

## Customizations

- Une seule scène Three.js à la racine, sur le temps global du film :
  pièces Staunton tournées (cavalier sculpté), plateau, base et horloge
  exportés de CadQuery (`mechanical/scenes.py --film-meshes`), LED aux
  positions de `chessboard_calc`. Le code commun est dans
  [`../commun/scene3d.js`](../commun/scene3d.js).
- Les textes (mot clé par coup, notation de la partie, détail mesuré)
  sont des calques 2D par-dessus la scène, dans `compositions/textes.html`.
- Son de synthèse seul : la note de chaque pièce posée, la gamme des
  douze notes sur le carton de fin, générées par `python -m serie`.
- Direction artistique, zones sûres, sous-titres et grammaire de
  montage de la bible de la série ([docs/serie](../../../docs/serie/README.md)),
  signature « Échec et Watt » sur le carton de fin.
- Tous les chiffres passent par `data-fact` et `assets/facts.js`,
  jamais tapés dans une composition (`tests/test_serie.py`).

## Notes

- Voix off plus tard : doublage par Étienne ou voix de synthèse
  (ElevenLabs), à décider. Les sous-titres de `compositions/captions.html`
  sont écrits pour servir de script.
- La partie est une démonstration : le plateau suit et vérifie les coups,
  il ne joue pas à la place du joueur (le moteur sur Pi ou la partie en
  ligne jouent l'adversaire).
- Le rendu 3D passe par le navigateur sans interface et le moteur
  logiciel (SwiftShader) : compter une vingtaine de minutes à 30 i/s.
