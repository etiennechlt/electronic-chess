# Montage : gabarit, son, sous-titres, export, publication

Un épisode se monte en deux heures quand les rushes sont nommés et la
fiche écrite. Ce document fixe le gabarit pour que tous les épisodes
se ressemblent, quel que soit celui qui monte.

## Outils

| Besoin | Choix recommandé | Alternative |
|---|---|---|
| Montage | DaVinci Resolve (gratuit, timeline verticale, sous-titres automatiques, gestion couleur) | CapCut sur téléphone pour les épisodes simples |
| Enregistrement d'écran | OBS (Linux, macOS, Windows), ou l'outil natif | |
| Voix off | le téléphone en mode dictaphone dans un placard, ou Audacity | |
| Cartons et plateau de progression | Inkscape ou Figma, exportés en PNG 1080 x 1920 avec fond transparent | |
| Musique et sons | bibliothèques libres : Pixabay Music, YouTube Audio Library (usage hors YouTube autorisé pour la plupart des titres, vérifier), Freesound (CC0) | les sons intégrés de l'application, uniquement si on ne cross-poste pas |

## Gabarit de timeline

Un projet type à dupliquer, avec les pistes suivantes, de haut en
bas :

1. **Cartons** : titre d'ouverture (0,5 s), le chiffre, la décision,
   le plateau de progression final.
2. **Texte à l'écran** : les mots clés, un par plan maximum.
3. **Sous-titres** : générés puis relus, style unique (voir plus bas).
4. **Écrans** : enregistrements d'écran recadrés et zoomés.
5. **Vidéo B** : plans de coupe, ralentis.
6. **Vidéo A** : plans principaux.
7. **Voix off**.
8. **Sons** : clics, ringdown, signature sonore.
9. **Musique** : à -18 dB sous la voix, coupée net sur le verdict.

Ordre de montage : voix off d'abord (enregistrée à partir du script,
raccourcie au besoin), image ensuite calée sur la voix, texte, sons,
musique, sous-titres en dernier.

## Structure temporelle d'un épisode de 60 s

| Temps | Contenu | Règle |
|---|---|---|
| 0 à 2 s | accroche : le plan le plus fort, le texte le plus court | pas de titre, pas de logo, pas de bonjour |
| 2 à 3 s | carton titre 0,5 s | grotesque grasse, fond bois ou cuivre |
| 3 à 10 s | contexte en une phrase de voix off | un plan large ou un dessin sur la planche |
| 10 à 40 s | le geste : ce qu'on fait, plans de 2 à 4 s | une seule idée, alterner dessus, macro, épaule |
| 40 à 50 s | le résultat ou le raté, le chiffre | mono plein écran pour le chiffre |
| 50 à 57 s | la relance, face caméra ou voix off | la question de l'épisode suivant |
| 57 à 60 s | plateau de progression, une case s'allume, signature sonore | toujours identique |

Le compte à rebours reste affiché en permanence en bas à droite, hors
de la zone d'interface (au-dessus des 250 px du bas).

## Sous-titres

- Générés automatiquement (Resolve, CapCut) puis **relus mot à mot** :
  les termes techniques sont systématiquement massacrés (microhenry,
  ringdown, ferrite).
- Style : grotesque Bold 64 px, blanc, contour noir 4 px, pas de fond,
  centrés, tiers inférieur (entre 1 300 et 1 550 px de hauteur).
- Deux lignes maximum, 6 mots par ligne au plus, coupure aux
  respirations de la voix.
- Un mot clé par sous-titre peut passer en cuivre (#B87333) ou en
  cyan (#2EC4B6) pour la mesure ; jamais plus d'un.
- Pas de majuscules criées dans les sous-titres ; les majuscules sont
  réservées au texte à l'écran.

## Zones sûres (1080 x 1920)

| Zone | Réservée à | Ne rien y mettre d'important |
|---|---|---|
| 0 à 100 px (haut) | barre de statut, titre de la série en petit | |
| 100 à 250 px | nom de compte et boutons selon l'application | |
| 250 à 1 550 px | contenu | zone utile |
| 1 550 à 1 920 px | légende, boutons, barre de progression | sous-titres jamais ici |
| 0 à 120 px (bord droit), sur toute la hauteur | boutons like, commentaire, partage | |

## Son

- **Voix off** : niveau cible -16 LUFS intégré, crête -1 dB. Couper
  les silences de plus de 0,4 s. Pas de réverbération.
- **Musique** : un seul morceau par saison pour créer l'habitude, à
  -18 dB sous la voix, coupé net sur les verdicts et les ratés, puis
  reprise.
- **Signature sonore** : les douze notes du plan de fréquences
  ramenées mille fois plus bas (217 à 613 Hz), jouées en ringdown
  (attaque instantanée, décroissance exponentielle de 0,4 s), montante
  à l'ouverture, une seule note à chaque identification de pièce.
  Proposition d'outil, à valider avant de l'écrire : un script
  `tools/serie/signature.py` qui lit les fréquences par
  `chessboard_calc` et écrit un `.wav` par note plus la gamme
  complète, paramétré sur le pas de case comme tout le reste. Tant
  qu'il n'existe pas, un synthétiseur gratuit (Vital, Surge) fait
  l'affaire avec une sinusoïde et une enveloppe courte.
- **Sons de geste** : clic de relais, bip de terminal, cutter,
  perceuse : garder les sons réels des rushes plutôt que des banques.
  Ils sont plus crédibles.

## Cartons et éléments graphiques

Fabriquer une fois, réutiliser partout, dans `serie/cartons/` :

- `titre.png` : « Échec et Watt », fond bois, texte noir, souligné
  cuivre.
- `chiffre.png` : cadre pour « le chiffre », mono, fond noir, chiffre
  en cuivre, phrase en blanc.
- `decision.png` : cadre pour « la décision », numéro d'ADR en mono,
  titre en grotesque.
- `rate.png` : cadre pour « le raté », fond ambre, texte noir.
- `plateau_Exx.png` : le plateau de progression, une version par
  épisode (a1 allumé, puis a1 et b1, etc.), cases allumées en cuivre,
  case du jour en cyan.
- `jmoins.png` : gabarit du compte à rebours, mono, bas droit.
- Les images du dépôt (`docs/images/`) recadrées en vertical :
  architecture, empilement, plan de fréquences, rendus des cartes,
  puck éclaté.

## Étalonnage

- Un seul réglage par séance, copié sur tous les plans de la séance.
- Balance des blancs neutre sur le bois (le bois ne doit pas virer
  au jaune ni au rose), contraste modéré, saturation naturelle.
- Les plans d'écran ne s'étalonnent pas.
- Les ralentis à 60 i/s se ralentissent à 50 %, jamais moins (sinon
  saccades).

## Export

| Paramètre | Valeur |
|---|---|
| Résolution | 1080 x 1920 |
| Cadence | 30 i/s |
| Codec | H.264, profil High, 20 à 25 Mbit/s |
| Son | AAC 48 kHz, 256 kbit/s, stéréo |
| Fichier | `exports/Exx_final.mp4`, versions intermédiaires `Exx_v1.mp4` |
| Durée | vérifier 45 à 75 s (90 s maximum pour E00, E10, E29) |

Exporter une fois, publier le même fichier sur toutes les
plateformes. Ne pas laisser une application recompresser un export
déjà passé par une autre.

## Fiche de publication

Par épisode, dans le journal de [tournage.md](tournage.md) ou une
note à part :

- **Titre** : le titre de la fiche, sans numéro à l'écran mais avec le
  numéro en légende (« E06 »).
- **Légende** : deux lignes : l'idée de l'épisode, puis la question de
  la relance. Trois à cinq mots-clés en fin de légende (échecs, DIY,
  électronique, impression 3D, bois), pas plus.
- **Vignette** : le plan d'accroche avec le texte d'accroche.
- **Heure** : publication en différé après Noël, un épisode par jour
  à la même heure, dans l'ordre ; programmer la file entière d'un
  coup avec l'outil de planification de l'application.
- **Secret** : relire la légende et la vignette pour vérifier
  qu'aucun prénom ne désigne le destinataire (jusqu'à E29), même si
  la série sort après la remise : c'est la révélation qui fait la
  chute.
- **Relecture d'ensemble** : avant de programmer la file, regarder
  tous les épisodes d'une traite pour vérifier le compte à rebours,
  le plateau de progression et les raccords entre épisodes montés à
  des mois d'écart.

## Checklist de sortie

- [ ] L'accroche tient en 2 s et sans le son.
- [ ] Une seule idée.
- [ ] Le chiffre vérifié contre `board.yaml` ou le rapport.
- [ ] Sous-titres relus, termes techniques corrects.
- [ ] Rien d'important dans les zones d'interface.
- [ ] Compte à rebours à jour.
- [ ] Plateau de progression : la bonne case allumée.
- [ ] Signature sonore à la fin.
- [ ] Aucun prénom ni indice sur le destinataire.
- [ ] Niveau sonore -16 LUFS, musique sous la voix.
- [ ] Durée entre 45 et 75 s.
- [ ] Fichier nommé `Exx_final.mp4`, publié depuis le même fichier
      partout.
