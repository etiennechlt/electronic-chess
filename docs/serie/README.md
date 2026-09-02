# Série vidéo « Échec et Watt » : la bible

Documenter la construction de l'échiquier en épisodes courts verticaux
(TikTok, Reels, Shorts), tournés au fil du projet avec Romain, et
offerts à Ayglon avec le plateau, à Noël (son anniversaire, le 1er
octobre, est une étape en chemin). Ce
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
  la remise, la complicité avec Romain, et la réaction finale
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
- **Le compte à rebours** : « J moins N » avant la remise, en
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

Le principe : sur chaque étape, l'un mène et l'autre est en support ;
**celui qui est en support tient la caméra et monte l'épisode**. Le
meneur commente son geste à l'écran et enregistre la voix off, parce
qu'il sait ce qu'il vient de faire.

| Étape | Mène (à l'écran, voix off) | Support (caméra, montage) |
|---|---|---|
| Conception électronique, cartes, commande (E01 à E04) | Étienne | Romain |
| Impression, bobinage, bois (E05, E06, E08) | Romain | Étienne |
| Colis, câblage, firmware, mesures (E07, E09 à E13) | Étienne | Romain |
| Plateau 8 x 8, électronique (saison 2) | Étienne | Romain |
| Portique CoreXY, mécanique, ébénisterie (E19 à E22, E26, E27) | Romain | Étienne |
| Firmware de jeu, Pi, batterie (E23 à E25) | Étienne | Romain |
| Test final et remise (E28 à E30) | les deux | un troisième téléphone si possible |

Script : Étienne, relu par Romain, à partir de
[episodes.md](episodes.md). Face caméra : les deux, chacun tient la
caméra pour l'autre.

Rituel de tournage : avant chaque séance, relire la fiche de
l'épisode (accroche, plans obligatoires, chiffre, raté). Après la
séance, dix minutes pour renommer les rushes et noter dans le
journal de [tournage.md](tournage.md) ce qui manque.

## Publication : en différé, épisode par épisode

Choix retenu : rien n'est publié avant la remise du cadeau. Les
épisodes sont montés au fil du projet (au plus tard une semaine après
le tournage, sinon la mémoire des rushes s'efface), puis sortent
après la remise, **un par jour**, dans l'ordre, la réaction d'Ayglon
en avant-dernier et l'épilogue en dernier.

Conséquences pratiques :

- Le compte à rebours reste filmé en direct : il compte les jours
  jusqu'à la date de remise réelle, et c'est ce qui donne de la
  tension à la série même vue après coup.
- Le secret est narratif : jusqu'à E29, le destinataire s'appelle
  « notre pote » à l'écran, pour que la révélation garde son effet.
- Avant publication : accord d'Ayglon pour son image (E29, E30), et
  relecture de tous les épisodes déjà montés d'une traite pour
  vérifier la cohérence du compte à rebours et du plateau de
  progression.
- Pendant le projet, un compte n'est pas nécessaire ; les proches
  peuvent voir les exports en avant-première par un dossier partagé.

Musique : les bibliothèques intégrées de TikTok et Instagram ne sont
licenciées que dans l'application. Pour pouvoir cross-poster et
garder les fichiers, préférer des sons libres (voir
[montage.md](montage.md)) et la signature sonore maison.

## Calendrier

Deux dates : l'anniversaire d'Ayglon le **1er octobre 2026**, et le
repli **Noël 2026**. Point de départ : le 2 septembre, avec la
maquette conçue mais rien de physique.

### Ce qu'un mois permet, et ce qu'il ne permet pas

Le plateau complet (64 cases, portique, jeu) n'est pas atteignable
pour le 1er octobre : les cartes de la phase 2 ne sont pas conçues,
et une commande en Asie prend 2 à 5 semaines à elle seule. La
maquette 2 x 2, elle, peut fonctionner pour le 1er octobre à une
condition : commander les cartes **cette semaine** (finition pcbnew
et correction du jack J1 comprises), en livraison express, et faire
tout le reste (impression, bobinage, bois, câblage) pendant
l'attente.

Plan retenu : **la remise du plateau se fait à Noël**. Le 1er
octobre devient une étape de la série, avec deux variantes à choisir
selon l'état de la maquette la dernière semaine de septembre :

- **La promesse** : si la maquette reconnaît les quatre pièces, on
  offre à Ayglon une pièce d'échecs équipée de son résonateur et une
  carte : « ton cadeau est en construction, il sera prêt à Noël ».
  La maquette qui joue sa note sous ses yeux fait un épisode fort au
  milieu de la série (E13bis) ; le secret change de nature : il sait
  qu'il y a un cadeau, pas ce que c'est.
- **Le silence** : la maquette n'est pas prête, on offre autre chose,
  le secret reste entier jusqu'à Noël. La série n'en parle pas.

### Rétro-planning vers Noël

Il n'y a **aucune marge pour une deuxième commande** de cartes :
celles du plateau 8 x 8 doivent partir à la mi-octobre pour arriver
mi-novembre, ce qui impose de concevoir la phase 2 en septembre,
pendant l'attente des cartes de la maquette, et non après les
mesures. Les mesures de la maquette ne feront que confirmer ou
corriger cette conception (le pas de case surtout : concevoir en
paramétrique, choisir p à la commande).

| Semaine | Projet | Épisodes à tourner |
|---|---|---|
| 2 au 8 septembre | finition pcbnew (7 nets, jack J1), export, 4 commandes en express, impression des pièces | E01, E02, E03, E04, E05 |
| 9 au 22 septembre | bobinage (5 bobines), contreplaqué percé, feutre, câblage préparé ; conception du plateau 8 x 8 (quadrants, mux, chaîne LED) | E06, E08, rafale du teaser |
| 23 au 30 septembre | réception (si express), bring-up, M1 à M5 au minimum, M2 en priorité | E07, E09, E10, E11, E12 |
| 1er octobre | anniversaire : la promesse ou le silence | E13bis (si promesse) |
| 2 au 12 octobre | M6 à M11, tableau de synthèse, choix de p, ADR ; gel de la conception 8 x 8 | E13, E14 |
| 13 au 19 octobre | commande des quadrants 8 x 8 et de leur électronique ; début du CoreXY (conception, impression) ; bobinage de 32 résonateurs commencé | E16 (début), E19 (conception) |
| 20 octobre au 16 novembre | attente des cartes : CoreXY imprimé et assemblé à vide, firmware 8 x 8 et arbitre écrits sur la maquette, pièces du commerce achetées et ouvertes | E16, E19, E18 (arbitre sur maquette) |
| 17 au 30 novembre | quadrants reçus, assemblage 8 x 8, calibration complète, premier scan de 64 cases | E15, E17 |
| 1er au 13 décembre | portique sous le plateau, e2-e4, couloir, roque, Pi et moteur d'échecs | E20 à E24 |
| 14 au 21 décembre | batterie, caisse, surface finale, pièces définitives | E25, E26, E27 |
| 22 au 24 décembre | test final, emballage | E28 |
| 25 décembre | remise | E29 |
| 26 décembre au 25 janvier | publication, un épisode par jour, E30 en clôture | E30 (tourné entre Noël et le jour de l'an) |

Règle de montage pendant tout ce temps : un épisode monté au plus
tard une semaine après son tournage, par celui qui était en support.
Ce qui n'est pas monté sous une semaine est mis en attente et se
monte pendant l'attente des cartes (fin octobre), jamais en décembre.

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
