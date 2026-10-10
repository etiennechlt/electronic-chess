---
workflow: general-video
flow: automation
storyboard: yes
message: "Couche par couche, ce qu'il y a sous le bois"
destination: tiktok
aspect: 1080x1920
language: fr
audience: "financement participatif, promo et vlog Instagram et TikTok"
length: 54.5s
angle: "le plateau se construit"
---

## Intent

Film de présentation de l'échiquier à détection LC, version « Le plateau
se construit » : le plateau fini, démonté en accéléré, puis remonté du
fond de la base jusqu'aux pièces, une pièce ouverte au passage, et pour
finir le même module plateau posé sur la base chariot de la phase 2.
Ton documentaire, très calme. Public : financement participatif, et
surtout promo et vlog sur Instagram et TikTok, donc vertical d'abord.
Le titre affiché suit la version.

## Customizations

- Une seule scène Three.js à la racine, sur le temps global du film.
  Chaque couche est le vrai solide CadQuery (`mechanical/scenes.py
  --film-meshes`) : base fine, trois cellules, cerveau et carte
  puissance, quatre quadrants, contreplaqué, puis la base chariot. Les
  pièces Staunton et la pièce ouverte (feutre, bobine et condensateur,
  aimant, coque) sont dessinées sur les cotes de `chessboard_calc`, dans
  [`../commun/scene3d.js`](../commun/scene3d.js).
- Une seule caméra documentaire qui tourne lentement autour du plateau ;
  deux exceptions coupées franc : le gros plan sur la pièce ouverte, le
  plan bas du changement de base.
- Son de synthèse seul : un bruit sourd à chaque couche posée
  (`pose.wav`), la note du pion quand la pièce se referme, puis les douze
  familles de pièces qui tombent sur les douze notes de la gamme, un pas
  de gamme (`serie.scale_step_s`) entre deux familles.
- Direction artistique, zones sûres, sous-titres et grammaire de
  montage de la bible de la série ([docs/serie](../../../docs/serie/README.md)),
  signature « Échec et Watt » sur le carton de fin.
- Tous les chiffres passent par `data-fact` et `assets/facts.js`,
  jamais tapés dans une composition (`tests/test_serie.py`) ; le
  compteur de spirales est calculé depuis `spirals_per_quadrant`.

## Notes

- Voix off plus tard : doublage par Étienne ou voix de synthèse
  (ElevenLabs), à décider. Les sous-titres de `compositions/captions.html`
  sont écrits pour servir de script.
- La base chariot est la phase 2 du projet : le film le dit à l'écran.
- Le rendu 3D passe par le navigateur sans interface et le moteur
  logiciel (SwiftShader) : compter une vingtaine de minutes à 30 i/s.
