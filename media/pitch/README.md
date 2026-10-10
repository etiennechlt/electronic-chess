# Films de présentation

Les films qui présentent le projet (financement participatif, promo et
vlog Instagram et TikTok), faits avec [HyperFrames](https://github.com/heygen-com/hyperframes) :
chaque plan est une page HTML animée, rendue image par image en MP4.
Ils suivent la bible de la série ([docs/serie](../../docs/serie/README.md)) :
vertical 1080 x 1920, palette bois, encre, cuivre, ambre et cyan,
sous-titres dans la bande 1 300 à 1 550 px, signature sonore d'une note
par pièce.

## Versions

| Version | Dossier | État |
|---|---|---|
| « L'échiquier qui écoute ses pièces » : une pièce sans puce ni pile, reconnue à sa note, puis l'objet, puis la preuve | [ecoute/](ecoute/) | 9:16, 60 s, construite |
| La même en 16:9 pour la page de financement | à créer (nouveau projet, même découpage) | à faire |
| « Une partie, du premier coup au mat » : chaque coup d'une partie courte révèle une fonction (détection, arbitrage, horloge, moteur) | à créer | à faire |
| « Le plateau se construit » : une seule caméra, l'objet s'assemble couche par couche, du fond de la base au feutre des pièces | à créer ; demande des rendus couche par couche depuis `mechanical/` | à faire |

Le titre affiché suit la version. Voix off : plus tard, doublage ou
voix de synthèse (ElevenLabs), à décider ; les sous-titres de chaque
film (`compositions/captions.html`) sont écrits pour servir de script.

## Ce qui est commité, ce qui se régénère

Sont commités : les compositions (`index.html`, `compositions/`), le
style et les aides communs (`film.css`, `film.js`), la police
(`fonts/`, licence OFL), `BRIEF.md` et `STORYBOARD.md`. Ne sont pas
commités : `assets/` (chiffres, sons et rendus, régénérés), `renders/`
(les MP4) et `node_modules/`.

Aucun nombre n'est écrit dans une composition : le texte porte
`data-fact="clé"` et la page le remplit depuis `assets/facts.js`, écrit
par `tools/serie` à partir de `config/board.yaml`.
`tests/test_serie.py` échoue si un chiffre calculé apparaît tapé dans
un film.

## Régénérer et rendre

Prérequis : Node 22 ou plus, FFmpeg, la CLI (`npm install -g hyperframes`)
et un Chrome sans interface (`hyperframes browser ensure`, ou dans un
environnement distant `PRODUCER_HEADLESS_SHELL_PATH` vers le Chromium
déjà installé).

```bash
python -m serie film media/pitch/ecoute   # chiffres, sons et rendus dans assets/
cd media/pitch/ecoute
npm install                               # GSAP en local : le rendu ne touche pas le réseau
npx hyperframes check                     # lint, exécution, mise en page, contraste
npx hyperframes preview                   # Studio : relire et retoucher dans le navigateur
npx hyperframes render --fps 30 --quality delivery -o renders/ecoute-9x16.mp4
```

Après une modification du yaml, relancer la première commande : le film
suit, sans retoucher les compositions.
