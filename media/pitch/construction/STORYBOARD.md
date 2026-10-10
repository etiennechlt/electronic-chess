---
format: 1080x1920
duration: 54.5s
message: "Couche par couche, ce qu'il y a sous le bois"
arc: "démontage → titre → base, énergie, cerveau, quadrants, bois → une pièce → les pièces → fini → base chariot → fin"
audience: "financement participatif, Instagram et TikTok"
mode: collaborative
---

Fil conducteur : une seule caméra qui tourne lentement autour du
plateau, et chaque couche, vrai solide CadQuery, qui tombe d'en haut et
se pose avec un bruit sourd. Plan tenu : le plateau fini (10). Les
chiffres entre accolades sont des clés de `assets/facts.js`. Toute la
scène 3D vit dans `index.html` ; les plans ci-dessous sont des fenêtres
de temps de cette scène et de `compositions/textes.html`.

## Frame 1 : Accroche

- status: animated
- src: index.html (0 à 3 s) et compositions/textes.html
- duration: 3s
- transition_in: cut
- scene: le plateau fini une seconde, puis les couches s'envolent dans l'ordre inverse, « On le démonte »
- voiceover: Un échiquier qui reconnaît ses pièces.

## Frame 2 : Titre

- status: animated
- src: compositions/titre.html
- duration: 2.5s
- transition_in: cut
- scene: carton bois, « Couche par couche », titre en trois lignes, l'onde s'aplatit en soulignement cuivre

## Frame 3 : La base

- status: animated
- src: index.html (5,5 à 9 s)
- duration: 3.5s
- transition_in: cut
- scene: la coque tombe et se pose, « coque imprimée · {base_height_mm} mm »
- voiceover: Tout part d'une coque imprimée.

## Frame 4 : L'énergie

- status: animated
- src: index.html (9 à 13 s)
- duration: 4s
- transition_in: cut
- scene: « {cells} cellules », trois poses, « {battery} · {energy_wh} Wh · cellules plates »
- voiceover: Des cellules plates, pour rester fin.

## Frame 5 : Le cerveau

- status: animated
- src: index.html (13 à 17 s)
- duration: 4s
- transition_in: cut
- scene: le cerveau et la carte puissance tombent ensemble, « {mcu} · charge USB-C »
- voiceover: Le cerveau et sa carte de puissance.

## Frame 6 : Les quadrants

- status: animated
- src: index.html (17 à 23 s)
- duration: 6s
- transition_in: cut
- scene: « {quadrants} quadrants », quatre poses régulières, le compteur de spirales monte d'un quadrant à chaque pose, puis « {leds} LED »
- voiceover: Un quadrant par quart du plateau, tous identiques.

## Frame 7 : Le bois

- status: animated
- src: index.html (23 à 27 s)
- duration: 4s
- transition_in: cut
- scene: le contreplaqué recouvre tout, puis une vague de lumière traverse ses trous en diagonale, « {plywood_mm} mm · {leds} points lumineux »
- voiceover: Du bois par-dessus, la lumière passe au travers.

## Frame 8 : Une pièce

- status: animated
- src: index.html (27 à 32 s)
- duration: 5s
- transition_in: cut
- scene: gros plan sur e4, plateau vide : feutre, bobine et condensateur, aimant, coque, écartés et légendés ({felt_mm}, {pawn_coil_mm}, {coil_uh}, {pawn_magnet_mm}) ; ils s'emboîtent, la case s'allume, la note sonne, « {line.pawn-white.name} · {line.pawn-white.label} »
- voiceover: Dans chaque pièce, une bobine et un condensateur.

## Frame 9 : Les pièces

- status: animated
- src: index.html (32 à 38 s)
- duration: 6s
- transition_in: cut
- scene: « {lines_count} notes », les douze familles tombent chacune sur sa note, du plus grave au plus aigu
- voiceover: Chaque famille de pièces tombe sur sa note.

## Frame 10 : Terminé

- status: animated
- src: index.html (38 à 41,5 s)
- duration: 3.5s
- transition_in: same camera
- scene: la caméra s'approche du plateau fini, « {module_cm} cm », « {thickness_mm} mm d'épaisseur · sur batterie »
- voiceover: Fini, et sur batterie.

## Frame 11 : Base chariot

- status: animated
- src: index.html (41,5 à 47,5 s)
- duration: 6s
- transition_in: cut
- scene: plan large ; le module plateau se soulève avec ses pièces, la base fine sort, la base chariot entre, le module s'y pose, « {gantry_thickness_mm} mm · CoreXY · phase 2 »
- voiceover: Le même plateau change de base : le chariot, en phase 2.

## Frame 12 : Fin

- status: animated
- src: compositions/fin.html
- duration: 7s
- transition_in: cut
- scene: carton bois, titre, la gamme des douze notes et l'onde qui s'amortit, état du projet, adresse du dépôt, signature « Échec et Watt »
