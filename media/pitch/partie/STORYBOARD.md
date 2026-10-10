---
format: 1080x1920
duration: 53s
message: "Chaque coup d'une partie montre une fonction du plateau"
arc: "accroche → titre → sept coups, sept fonctions → mat → chiffre → fin"
audience: "financement participatif, Instagram et TikTok"
mode: collaborative
---

Fil conducteur : la partie elle-même, le coup du berger (1. e4 e5 2. Fc4
Cc6 3. Dh5 Cf6 4. Dxf7#), dont la notation s'écrit sous le mot clé au fil
des coups. Une seule caméra 3D qui coupe franchement à chaque coup ; les
cases s'allument en blanc pour le joueur, en ambre pour l'adversaire en
ligne. Les chiffres entre accolades sont des clés de `assets/facts.js`.
Toute la scène 3D vit dans `index.html` ; les plans ci-dessous sont des
fenêtres de temps de cette scène et de `compositions/textes.html`.

## Frame 1 : Accroche

- status: animated
- src: index.html (0 à 2,5 s) et compositions/textes.html
- duration: 2.5s
- transition_in: cut
- scene: plateau en position de départ, vue large, « Mat en 4 coups »
- voiceover: Une partie, sur un échiquier qui écoute.

## Frame 2 : Titre

- status: animated
- src: compositions/titre.html
- duration: 3s
- transition_in: cut
- scene: carton bois, « Le coup du berger », titre en trois lignes, l'onde s'aplatit en soulignement cuivre

## Frame 3 : Détection

- status: animated
- src: index.html (5,5 à 10 s)
- duration: 4.5s
- transition_in: cut
- scene: 1. e4, le pion blanc se pose, sa case s'allume, « pion blanc · {line.pawn-white.label} », sa note sonne
- voiceover: Il reconnaît la pièce à sa note.

## Frame 4 : En ligne

- status: animated
- src: index.html (10 à 14,5 s)
- duration: 4.5s
- transition_in: cut
- scene: e7 et e5 clignotent en ambre, le pion noir de l'adversaire en ligne est joué
- voiceover: L'adversaire joue en ligne, les cases s'allument.

## Frame 5 : Arbitre

- status: animated
- src: index.html (14,5 à 18,5 s)
- duration: 4s
- transition_in: cut
- scene: 2. Fc4, coche cyan « coup légal »
- voiceover: Chaque coup est vérifié.

## Frame 6 : Horloge

- status: animated
- src: index.html (18,5 à 23 s)
- duration: 4.5s
- transition_in: cut
- scene: Cc6 en ambre, puis gros plan sur l'horloge dont la barre bascule seule
- voiceover: L'horloge bascule seule, sans fil.

## Frame 7 : Sa note

- status: animated
- src: index.html (23 à 27 s)
- duration: 4s
- transition_in: cut
- scene: 3. Dh5, « dame blanche · {line.queen-white.label} », la note aiguë de la dame
- voiceover: Chaque pièce a sa note, la dame sonne aigu.

## Frame 8 : L'erreur

- status: animated
- src: index.html (27 à 31 s)
- duration: 4s
- transition_in: cut
- scene: Cf6 en ambre, les « ?? » tombent quand le cavalier se pose
- voiceover: Il ne joue pas à ta place.

## Frame 9 : Prise

- status: animated
- src: index.html (31 à 36 s)
- duration: 5s
- transition_in: cut
- scene: le pion f7 sort du plateau, la dame s'y pose, « pion noir retiré · dame blanche posée »
- voiceover: Il suit aussi les prises.

## Frame 10 : Échec et mat

- status: animated
- src: index.html (36 à 41 s)
- duration: 5s
- transition_in: cut
- scene: la caméra tourne autour du roi noir en e8 qui clignote en ambre, « partie terminée · horloge arrêtée »

## Frame 11 : Le chiffre

- status: animated
- src: compositions/chiffre.html
- duration: 5s
- transition_in: cut
- scene: fond encre, « {idle_scan_hz}/s », « écoutes par seconde, sur chacune des {squares} cases », « moteur sur Pi ou partie en ligne »

## Frame 12 : Fin

- status: animated
- src: compositions/fin.html
- duration: 7s
- transition_in: cut
- scene: carton bois, titre, la gamme des douze notes et l'onde qui s'amortit, état du projet, adresse du dépôt, signature « Échec et Watt »
