---
workflow: general-video
flow: automation
storyboard: yes
message: "Des pièces passives qui chantent, un plateau qui écoute"
destination: tiktok
aspect: 1080x1920
language: fr
audience: "financement participatif, promo et vlog Instagram et TikTok"
length: 60s
angle: "l'échiquier qui écoute ses pièces"
---

## Intent

Film de présentation de l'échiquier à détection LC, version « l'échiquier
qui écoute ses pièces » : une pièce sans puce ni pile, le plateau qui la
reconnaît à sa note, puis l'objet, puis la preuve d'ingénierie. Public :
financement participatif, et surtout promo et vlog sur Instagram et
TikTok, donc vertical d'abord. Le titre affiché suit la version.

## Customizations

- Son de synthèse seul : la signature sonore de la série (une note par
  pièce identifiée, la gamme des douze notes), générée par
  `python -m serie` depuis `chessboard_calc`.
- Direction artistique, zones sûres, sous-titres et grammaire de
  montage de la bible de la série ([docs/serie](../../../docs/serie/README.md)).
- Tous les chiffres passent par `data-fact` et `assets/facts.js`,
  jamais tapés dans une composition (`tests/test_serie.py`).

## Notes

- Voix off plus tard : doublage par Étienne ou voix de synthèse
  (ElevenLabs), à décider. Les sous-titres de `compositions/captions.html`
  sont écrits pour servir de script.
- Les images sont les rendus CAO et les tracés KiCad du dépôt ; aucun
  prototype n'est filmé, la fin dit l'état réel du projet.
