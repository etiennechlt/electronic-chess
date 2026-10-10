# Films de présentation

Les films qui présentent le projet (financement participatif, promo et
vlog Instagram et TikTok), faits avec [HyperFrames](https://github.com/heygen-com/hyperframes) :
chaque plan est une page HTML animée, rendue image par image en MP4.
Ils suivent la bible de la série ([docs/serie](../../docs/serie/README.md)) :
vertical 1080 x 1920, palette bois, encre, cuivre, ambre et cyan,
sous-titres dans la bande 1 300 à 1 550 px, signature sonore d'une note
par pièce, signature « Échec et Watt ».

## Versions

| Version | Dossier | État |
|---|---|---|
| « L'échiquier qui écoute ses pièces » : une pièce sans puce ni pile, reconnue à sa note, puis l'objet, puis la preuve | [ecoute/](ecoute/) | 9:16, 60 s, construite, plans d'objet en 3D |
| La même en 16:9 pour la page de financement | à créer (nouveau projet, même découpage) | à faire |
| « Une partie, du premier coup au mat » : le coup du berger joué sur le plateau, chaque coup révèle une fonction (détection, partie en ligne, arbitrage, horloge, prise) | [partie/](partie/) | 9:16, 53 s, construite, en 3D |
| « Le plateau se construit » : une seule caméra, le plateau démonté puis remonté couche par couche jusqu'aux pièces, puis posé sur la base chariot | [construction/](construction/) | 9:16, 54,5 s, construite, en 3D |

Le titre affiché suit la version. Voix off : plus tard, doublage ou
voix de synthèse (ElevenLabs), à décider ; les sous-titres de chaque
film (`compositions/captions.html`) sont écrits pour servir de script.

## La 3D

Les plans d'objet sont une scène Three.js unique, à la racine de chaque
film (`index.html`), calculée sur le temps global : une même image se
rend à l'identique à chaque recherche, ce que le rendu image par image
exige. Les compositions posent par-dessus les mots clés, les détails
mesurés et les sous-titres. Le code commun est dans
[`commun/scene3d.js`](commun/scene3d.js) :

- le plateau, la base chariot et l'horloge sont les solides CadQuery du
  dépôt, exportés en STL dans [`commun/meshes/`](commun/meshes/) par
  `mechanical/scenes.py --film-meshes` ;
- les pièces sont des Staunton tournées (le cavalier sculpté), posées
  sur les diamètres de base que calcule `chessboard_calc` ; leur
  hauteur suit `serie.piece_height_ratio` (valeurs de rendu, pas de
  conception) ;
- la pièce ouverte (feutre, bobine et condensateur, aimant, coque) est
  aux cotes de la classe ;
- les points lumineux sont aux positions `led_points` du plateau.

## Ce qui est commité, ce qui se régénère

Sont commités : les compositions (`index.html`, `compositions/`), le
dossier `commun/` (style, aides, police sous licence OFL, scène 3D et
maillages), `BRIEF.md` et `STORYBOARD.md`. Ne sont pas commités :
`assets/` (chiffres, sons, copie de `commun/`, régénérés), `renders/`
(les MP4), `snapshots/` (captures de relecture) et `node_modules/`.

Aucun nombre n'est écrit dans une composition : le texte porte
`data-fact="clé"` et la page le remplit depuis `assets/facts.js`, écrit
par `tools/serie` à partir de `config/board.yaml` ; la scène 3D lit ses
cotes dans `window.FACTS.scene`. `tests/test_serie.py` échoue si un
chiffre calculé apparaît tapé dans un film.

## Régénérer et rendre

Prérequis : Node 22 ou plus, FFmpeg, la CLI (`npm install -g hyperframes`)
et un Chrome sans interface (`hyperframes browser ensure`, ou dans un
environnement distant `PRODUCER_HEADLESS_SHELL_PATH` vers le Chromium
déjà installé). Pour un film donné (`ecoute`, `partie` ou `construction`) :

```bash
python mechanical/scenes.py --film-meshes media/pitch/commun/meshes  # si la géométrie a changé
python -m serie film media/pitch/partie   # chiffres, sons, commun/ dans assets/
cd media/pitch/partie
npm install                               # GSAP et three.js en local : le rendu ne touche pas le réseau
npx hyperframes check                     # lint, exécution, mise en page, contraste
npx hyperframes preview                   # Studio : relire et retoucher dans le navigateur
npx hyperframes render --fps 30 --quality delivery -o renders/partie-9x16.mp4
```

Le rendu 3D passe par le moteur logiciel du navigateur (SwiftShader)
quand il n'y a pas de GPU : compter une vingtaine de minutes par film à
30 i/s. Après une modification du yaml, relancer `python -m serie film` :
le film suit, sans retoucher les compositions.
