# Série vidéo « Échec et Watt » : la bible

Documenter la construction de l'échiquier en épisodes courts verticaux
(TikTok, Reels, Shorts), tournés au fil du projet avec Romain, et
offerts à Ayglon avec le plateau le jour de son anniversaire. Ce
dossier est la bible de la série : concept, format, direction
artistique, organisation, règles de publication. Le découpage et les
scripts sont dans [episodes.md](episodes.md), la méthode de tournage
dans [tournage.md](tournage.md), le montage dans
[montage.md](montage.md).

Rien de ce dossier ne fait autorité sur la technique : les chiffres
cités dans les scripts viennent de `config/board.yaml` et des notes
de `docs/notes/`, et sont à relire avant chaque tournage.

## Le concept en une phrase

Deux amis construisent, de zéro, un échiquier qui reconnaît les
pièces et les déplace tout seul, pour l'offrir à un troisième qui ne
doit rien savoir. Le spectateur suit les étapes, les ratés et la
mesure qui peut tout faire tomber, jusqu'à la remise du cadeau.

Deux fils narratifs se croisent :

- **Le fil technique** : une idée par épisode, expliquée avec un objet
  dans la main, jamais avec un schéma seul.
- **Le fil humain** : le secret, le compte à rebours jusqu'à
  l'anniversaire, la complicité avec Romain, et la réaction finale
  d'Ayglon comme dernier épisode.

## Titre et identité

Titre recommandé : **Échec et Watt**. Deux variantes en réserve :
« Cavalier seul » (le plateau joue sans main) et « Roque and roll ».
Le titre apparaît en carton d'ouverture 0,5 s maximum, puis en petit
dans le coin haut gauche.

Signature sonore : chaque pièce du projet est un résonateur accordé
entre 217 et 613 kHz. Ramenées mille fois plus bas, ces fréquences
tombent dans l'audible (217 à 613 Hz, du la 3 au ré dièse 5) : **chaque
pièce a sa note**. La série s'ouvre et se ferme sur cette gamme de
douze notes jouée en ringdown (attaque nette, extinction douce), et
chaque identification de pièce à l'écran est ponctuée de « sa » note.
Le son est à synthétiser depuis les fréquences calculées par
`chessboard_calc` (proposition d'outil dans [montage.md](montage.md)).

## Le format

| Paramètre | Choix |
|---|---|
| Cadre | vertical 9:16, 1080 x 1920 |
| Cadence | 30 i/s, 60 i/s pour les ralentis (aimants, pièces qui bougent) |
| Durée | 45 à 75 s ; le teaser et les épisodes pivot peuvent aller à 90 s |
| Structure | accroche (0 à 2 s), contexte (une phrase), le geste, le résultat ou le raté, la relance |
| Voix | voix off enregistrée après tournage, plus quelques prises face caméra pour les moments forts |
| Sous-titres | incrustés, toujours (la majorité regarde sans le son) |
| Rythme | un plan toutes les 2 à 4 s, jamais plus de 6 s sans changement |
| Langue | français, tutoiement, phrases courtes, aucun jargon sans image qui l'explique |

Une règle d'or : **un épisode, une idée**. Si un tournage produit deux
idées, il produit deux épisodes.

## Les rubriques récurrentes

Elles donnent un rythme reconnaissable et facilitent l'écriture.

- **Le chiffre** : un nombre du projet plein écran, en police mono,
  avec sa phrase d'explication (exemple : « 12 : le nombre de notes,
  donc de types de pièces à reconnaître »). Une fois par épisode.
- **La décision** : quand un épisode repose sur un ADR, un carton
  « Décision 0002 : ferrite, jamais néodyme » avec la raison en une
  ligne. Cela relie la série au dépôt sans le montrer.
- **Le raté** : ce qui n'a pas marché, montré sans détour. C'est la
  rubrique qui fait revenir les gens.
- **Le compte à rebours** : « J moins N » avant l'anniversaire, en
  petit dans le coin bas droit, tenu à jour à chaque épisode.
- **Le plateau de progression** : un échiquier 8 x 8 stylisé où chaque
  épisode publié allume une case. Il ferme chaque épisode (1 s) et
  montre d'un coup d'œil où en est la série.

## Direction artistique

Le projet a déjà une esthétique : bois, cuivre des spirales, noir et
blanc des cases, points lumineux de camp. La série la reprend.

### Palette

| Rôle | Couleur | Usage |
|---|---|---|
| Fond | bois clair (#D9B98C) ou plan réel de contreplaqué | cartons, fond des chiffres |
| Encre | noir profond (#141414) | texte principal, cases noires |
| Cuivre | #B87333 | accents, soulignements, spirales à l'écran |
| Camp blanc | blanc chaud (#F4EFE6) | LED de camp blanc, cases blanches |
| Camp noir | ambre (#FFB347) | LED de camp noir, alertes, « le raté » |
| Signal | cyan (#2EC4B6) | courbes, ringdown, tout ce qui vient de la mesure |

Deux couleurs maximum par écran en plus du noir et du blanc.

### Typographie

- Titres et cartons : une grotesque grasse et large (Inter Black,
  Archivo Black ou équivalent), majuscules, interlettrage serré.
- Chiffres et données : une mono (JetBrains Mono, IBM Plex Mono).
  Tout ce qui vient d'une mesure est en mono, systématiquement.
- Sous-titres : la même grotesque en Bold, blanc avec contour noir de
  4 px, 2 lignes maximum, centrées dans le tiers inférieur, jamais
  sur les zones couvertes par l'interface de l'application (les 250
  px du bas et les 100 px du haut).

### Image

- Lumière : lumière du jour de côté ou une lampe unique en diagonale,
  jamais de plafonnier seul. Les plans macro (spirales, soudures,
  bobinage) avec une lampe rasante pour faire ressortir le relief.
- Cadres récurrents : plan de travail vu du dessus (trépied ou bras
  au-dessus de la table), macro à 10 cm, plan « épaule » sur celui
  qui fait le geste, plan large des deux à la fin.
- Mains à l'écran : toujours propres, manches relevées, une seule
  action par plan.
- Écrans : les captures (KiCad, terminal, notebook) sont recadrées en
  vertical et zoomées sur la zone utile, fond sombre, police à 2x.
  Jamais un écran entier filmé au téléphone.
- Ralenti : réservé aux aimants, aux pièces qui se déplacent et aux
  LED qui s'allument.

### Grammaire de montage

- Coupe franche partout. Un seul type de transition autorisé en plus :
  le « match cut » sur un objet (la pièce dessinée devient la pièce
  imprimée).
- Texte à l'écran : un mot clé par plan au maximum, pop simple, pas
  d'animation typographique complexe.
- Le ringdown (courbe qui s'éteint) est le motif visuel de la série :
  il sert d'intertitre, de barre de progression et de fermeture.

## Organisation à deux

| Rôle | Qui | Contenu |
|---|---|---|
| Réalisation et montage | à répartir | choix des plans, montage, export |
| Voix off | à répartir | enregistrement après montage image |
| Face caméra | les deux | chacun tient la caméra pour l'autre |
| Technique à l'écran | les deux | celui qui fait le geste le commente |
| Script | Étienne, relu par Romain | à partir de [episodes.md](episodes.md) |

Proposition : Étienne porte l'électronique et le firmware à l'écran,
Romain la mécanique et le bois, et chacun filme l'autre. Le montage
tourne par épisode pour ne pas créer de goulot.

Rituel de tournage : avant chaque séance, relire la fiche de
l'épisode (accroche, plans obligatoires, chiffre, raté). Après la
séance, dix minutes pour renommer les rushes et noter dans le
journal de [tournage.md](tournage.md) ce qui manque.

## Publication et secret

Ayglon ne doit rien voir avant l'anniversaire. Deux options :

1. **Compte privé** (recommandé) : un compte dédié, abonnés validés à
   la main, Ayglon exclu. Les épisodes sortent au fil du projet, les
   proches suivent, et le jour J on lui remet le plateau avec le
   compte et un accès. Le dernier épisode est sa réaction.
2. **Publication différée** : tout est monté au fil de l'eau mais
   rien n'est publié avant la remise. Les épisodes sortent ensuite un
   par jour, avec la réaction en clôture. Moins de retours pendant le
   projet, mais aucun risque de fuite.

Dans les deux cas : aucun prénom d'Ayglon dans les titres ou les
descriptions avant la remise (dire « notre pote », « le destinataire »),
aucun tag, et un seul mot de passe partagé entre Étienne et Romain.

Musique : les bibliothèques intégrées de TikTok et Instagram ne sont
licenciées que dans l'application. Pour pouvoir cross-poster et
garder les fichiers, préférer des sons libres (voir
[montage.md](montage.md)) et la signature sonore maison.

## Calendrier

La série suit les phases du projet. Les délais de commande (2 à 5
semaines pour l'Asie) fixent le rythme de la saison 1 ; la date de
l'anniversaire fixe la fin. À compléter dès que la date est connue.

| Saison | Sujet | Épisodes | Quand |
|---|---|---|---|
| 1 | La maquette 2 x 2 : l'idée, les cartes, les mesures | E00 à E13 | dès maintenant, pendant la commande et le montage |
| 2 | Le plateau 8 x 8 de détection | E14 à E18 | après les mesures |
| 3 | Le portique CoreXY et le jeu | E19 à E25 | après le plateau |
| 4 | Finition, ébénisterie, remise du cadeau | E26 à E30 | les dernières semaines, jour J |

Rythme de publication visé : un épisode par semaine en phase calme,
deux par semaine pendant les mesures et le montage. Garder toujours
deux épisodes d'avance montés.

## Ce que le dépôt fournit

Une bonne part des visuels existe déjà et se régénère
([runbook](../notes/08-regenerer.md)) :

- `docs/images/architecture.svg`, `stackup-blueprint.svg`,
  `frequency-plan.svg` : à recadrer en vertical pour les cartons.
- `docs/images/coil-board.png`, `analog-board.png`, `mockup-3d.png`,
  `piece-exploded.png`, `magnet-bracket.png` : rendus des cartes et
  de la mécanique, parfaits pour les match cuts avec le réel.
- `python -m chessboard_calc report --pitch all` : les tables de
  fréquences et de diamètres pour « le chiffre ».
- Le routeur maison : enregistrer l'écran pendant une régénération
  donne un timelapse de routage (épisode E03).
- Le firmware : la sortie CSV en console et le dump `r` des 512
  échantillons donnent la courbe de ringdown à animer (E09).
