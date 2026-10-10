---
format: 1080x1920
duration: 60s
message: "Des pièces passives qui chantent, un plateau qui écoute"
arc: "mystère → principe → objet → preuve"
audience: "financement participatif, Instagram et TikTok"
mode: collaborative
---

Fil conducteur : la ligne d'oscilloscope (`compositions/scope.html`) qui
sonne à chaque pièce identifiée, devient la grande onde des plans 05 à 07,
le soulignement du titre et l'onde qui s'amortit à la fin. Plan tenu : 12.
Raccords : coupes franches, sauf les raccords sur objet (08 vers 09, la
base ouverte puis habillée en 13). Les chiffres entre accolades sont des
clés de `assets/facts.js`.

Les plans d'objet (01, 02, 04, 08 à 11, 13) sont une seule scène 3D, à
la racine (`index.html`), sur le temps global : pièces Staunton aux
diamètres de base calculés, plateau, base chariot et horloge exportés
de CadQuery. Les compositions de ces plans ne portent plus que les
mots ; les cartons et les plans d'onde (03, 05 à 07, 12, 14, 15) les
recouvrent.

## Frame 1 : Pièce

- status: animated
- src: compositions/s01-piece.html
- duration: 3.5s
- transition_in: cut
- scene: un pion noir tombe sur un sol sombre et se pose, « 0 puce, 0 pile, 0 contact »
- voiceover: Une pièce d'échecs.

## Frame 2 : Pose

- status: animated
- src: compositions/s02-pose.html
- duration: 4s
- transition_in: cut
- scene: le pion posé en e4 du plateau vide, anneaux cyan, la case s'allume, « pion noir » et sa fréquence
- voiceover: Et pourtant, le plateau sait laquelle.

## Frame 3 : Titre

- status: animated
- src: compositions/s03-titre.html
- duration: 3.5s
- transition_in: cut
- scene: carton bois, titre, l'onde s'aplatit en soulignement cuivre

## Frame 4 : Dans la pièce

- status: animated
- src: compositions/s04-dans-la-piece.html
- duration: 4s
- transition_in: cut
- scene: le pion ouvert, feutre, bobine et condensateur, aimant, coque s'écartent vers le bas, légendes qui suivent les pièces
- voiceover: Dedans, une bobine et un condensateur.

## Frame 5 : Frappe

- status: animated
- src: compositions/s05-frappe.html
- duration: 4s
- transition_in: cut
- scene: front d'excitation puis ringdown du pion noir sur la fenêtre d'écoute
- voiceover: Le plateau frappe. La pièce sonne.

## Frame 6 : Douze notes

- status: animated
- src: compositions/s06-douze-notes.html
- duration: 5s
- transition_in: cut
- scene: les douze raies montent une à une sur la gamme
- voiceover: {lines_count} pièces, {lines_count} notes, de {band_low_khz} à {band_high_khz} kHz.

## Frame 7 : Identifiée

- status: animated
- src: compositions/s07-identifiee.html
- duration: 3.5s
- transition_in: cut
- scene: le spectre tombe sur la dame blanche, coche
- voiceover: Une FFT, et la pièce est reconnue.

## Frame 8 : Plateau

- status: animated
- src: compositions/s08-plateau.html
- duration: 3.5s
- transition_in: cut
- scene: le plateau fin et ses pièces en position de départ, lente avancée, côté et épaisseur
- voiceover: Un plateau fin, sur batterie, sans câble.

## Frame 9 : Éclaté

- status: animated
- src: compositions/s09-eclate.html
- duration: 4.5s
- transition_in: match
- scene: même cadre que 08, les couches s'écartent, quatre mots clés de haut en bas, la couche nommée s'éclaire en cyan
- voiceover: Sous le bois, {coils} spirales et {leds} LED.

## Frame 10 : Arbitre

- status: animated
- src: compositions/s10-arbitre.html
- duration: 4s
- transition_in: cut
- scene: e2-e4 sur le plateau, les deux points lumineux de la case, roque, prise en passant, promotion
- voiceover: Il vérifie chaque coup, même les plus rares.

## Frame 11 : Horloge

- status: animated
- src: compositions/s11-horloge.html
- duration: 3.5s
- transition_in: cut
- scene: l'horloge à bascule, sa barre bascule à chaque coup, liaison radio
- voiceover: Contre un moteur ou en ligne, horloge comprise.

## Frame 12 : Autonomie

- status: animated
- src: compositions/s12-autonomie.html
- duration: 3.5s
- transition_in: cut
- scene: « le chiffre » : l'autonomie compte puis tient, plan tenu du film

## Frame 13 : Chariot

- status: animated
- src: compositions/s13-chariot.html
- duration: 3.5s
- transition_in: cut
- scene: la base chariot ouverte, le module plateau s'y pose avec un bruit sourd, en option, phase 2
- voiceover: Une base qui déplace les pièces toute seule.

## Frame 14 : Un seul fichier

- status: animated
- src: compositions/s14-un-fichier.html
- duration: 5s
- transition_in: cut
- scene: les lignes de config/board.yaml, les tests, les composants, les cartes générées
- voiceover: Tout part d'un seul fichier.

## Frame 15 : Fin

- status: animated
- src: compositions/s15-fin.html
- duration: 5s
- transition_in: cut
- scene: carton bois, la gamme sonne et l'onde s'amortit, état du projet, lien et signature « Échec et Watt »
