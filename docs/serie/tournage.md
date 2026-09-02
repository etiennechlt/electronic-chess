# Tournage : méthode, matériel, rushes, journal

Le principe : **tout filmer, tout le temps, sans jamais bloquer le
projet**. Un plan de 5 s pris au bon moment vaut plus qu'une heure de
reconstitution. La série se monte à partir de rushes courts et bien
nommés ; ce document dit comment les produire et les ranger.

## Matériel minimal

| Poste | Choix | Note |
|---|---|---|
| Caméra | deux téléphones récents, 4K 30 i/s, 1080p 60 i/s pour les ralentis | un sur les mains, un sur l'écran ou le visage |
| Stabilisation | un trépied de table à bras articulé, un trépied classique | le bras au-dessus de la table pour la vue du dessus |
| Macro | une lentille macro à clipser, ou le mode macro du téléphone | indispensable pour le cuivre, le fil, les soudures |
| Lumière | une lampe LED de bureau orientable, une feuille de papier calque en diffuseur | rasante pour le relief, diffuse pour les visages |
| Son | un micro cravate sans fil (ou filaire) pour les face caméra, le téléphone posé sur la table pour l'ambiance | la voix off s'enregistre à part, au calme, dans un placard à vêtements |
| Écran | enregistrement d'écran natif de l'ordinateur, terminal en police 2x et fond sombre | jamais l'écran filmé au téléphone |
| Oscilloscope | filmer l'écran de face avec le téléphone, ou exporter la capture | régler la persistance pour que le ringdown reste visible |

## Réglages du téléphone

- Verrouiller l'exposition et la mise au point avant chaque prise
  (appui long sur le sujet), sinon l'image pompe quand la main entre.
- Mode vidéo classique, pas le mode « cinématique » qui floute au
  hasard.
- Grille des tiers activée. Pour les plans destinés au vertical,
  filmer en vertical ; pour les plans vue du dessus, filmer en
  horizontal 4K et recadrer au montage.
- Ralentis à 60 i/s minimum (120 si disponible) : aimants, pièces qui
  bougent, LED qui s'allument, fil qui s'enroule.
- Stockage : vider les téléphones sur le disque après chaque séance.

## Les plans récurrents (à faire à chaque séance)

Ce sont les plans de coupe qui sauvent un montage. Cinq secondes de
chacun, à chaque séance, même si rien n'a changé :

1. Vue du dessus du plan de travail, mains en action.
2. Macro de l'objet du jour (carte, bobine, puck, planche).
3. Plan « épaule » sur celui qui fait le geste.
4. Le visage de l'autre qui regarde, réaction.
5. Plan large des deux au-dessus de la table.
6. L'écran principal du jour, enregistré, pas filmé.
7. Le calendrier ou le téléphone avec la date (compte à rebours).
8. Le plateau de progression physique (si on en fabrique un : une
   grille 8 x 8 en bois avec des pastilles à retourner).

## Plans à ne surtout pas manquer (une seule occasion)

- L'ouverture du colis (E07) : filmer dès la porte, ne rien
  déballer avant.
- Le premier allumage de chaque carte (E07), le premier ringdown
  (E09), la mesure M2 (E10), la première identification (E12), le
  premier déplacement automatique (E20) : **une prise continue** sur
  un téléphone, plans de coupe sur l'autre. La vraie réaction ne se
  rejoue pas.
- Les ratés : quand quelque chose casse, sortir le téléphone avant de
  jurer.
- Chaque mesure du protocole M1 à M11, même 10 s : E13 en a besoin.
- La remise à Ayglon (E29) : deux téléphones, un sur lui, un sur le
  plateau, et un troisième si possible sur les deux qui offrent.

## Nommage des rushes

Les rushes ne vont jamais dans le dépôt git. Ils vivent sur un disque
partagé (ou un dossier cloud commun) avec cette structure :

```
serie/
  rushes/
    2026-09-14_E05_impression/
      E05_01_buse-macro.mp4
      E05_02_timelapse.mp4
      E05_03_pieces-alignees_dessus.mp4
      E05_ecran_build-all.mp4
    2026-09-20_E06_bobinage/
  ecrans/            enregistrements d'écran, même nommage
  son/               voix off, ambiances, signature sonore
  cartons/           images fixes exportées du dépôt (svg, png)
  montage/           projets de montage, un par épisode
  exports/           E05_v1.mp4, E05_v2.mp4, E05_final.mp4
```

Règles :

- Un dossier par séance : `AAAA-MM-JJ_Exx_sujet`. Une séance qui sert
  deux épisodes va dans le dossier du premier, avec un raccourci ou
  une note dans le journal.
- Un fichier : `Exx_NN_contenu_cadre.mp4`, où le cadre est `dessus`,
  `macro`, `epaule`, `large`, `face`, `ecran`, `ralenti`.
- Renommer le soir même. Un rush non renommé sous 24 h est un rush
  perdu.
- Les meilleurs plans de coupe (les huit récurrents) se copient en
  plus dans `rushes/_broll/` pour être trouvés en dix secondes.

## Journal de tournage

À tenir à jour après chaque séance. Statuts : à tourner, en cours,
tourné, monté, publié.

| Épisode | Titre | Statut | Séances | Plans manquants |
|---|---|---|---|---|
| E00 | Teaser | à tourner | | rafale de six plans, pièce qui glisse |
| E01 | Chaque pièce a sa note | à tourner | | verres, bobine dans la paume |
| E02 | Le fichier qui commande tout | à tourner | | pièces qui se coincent, écran pytest |
| E03 | Des cartes dessinées par un programme | à tourner | | timelapse routage, finition pcbnew |
| E04 | Commander | à tourner | | écrans de commande |
| E05 | L'imprimante | à tourner | | timelapse, pièces alignées |
| E06 | Bobiner à la main | à tourner | | perceuse macro, quatre bobines |
| E07 | Le colis | à tourner | | ouverture, allumage |
| E08 | Le bois | à tourner | | perçage, époxy, feutre |
| E09 | Premier signal | à tourner | | nappes, console, oscilloscope, son |
| E10 | La mesure qui peut tout faire tomber | à tourner | | prise continue M2 |
| E11 | Pourquoi pas le néodyme | à tourner | | pièces qui se retournent, M3, M7 |
| E12 | Elle reconnaît les pièces | à tourner | | calibration, LED, M5 |
| E13 | Bilan | à tourner | | tableau, rushes M8 M10 M11 |

Les saisons 2 à 4 s'ajoutent au tableau quand leurs fiches sont
écrites.

## Checklist avant une séance

- [ ] Fiche de l'épisode relue (accroche, plans, chiffre, raté).
- [ ] Batteries chargées, stockage vidé.
- [ ] Trépied de table, lampe, lentille macro dans le sac.
- [ ] Micro cravate testé.
- [ ] Plan de travail dégagé, seul l'objet du jour et les outils.
- [ ] Manches relevées, mains propres.
- [ ] Les chiffres du jour vérifiés dans `board.yaml` ou le rapport
      `chessboard_calc`.

## Checklist après une séance

- [ ] Rushes copiés sur le disque et renommés.
- [ ] Les huit plans récurrents pris (sinon les faire tout de suite).
- [ ] Journal mis à jour : statut, plans manquants.
- [ ] Une ligne de notes pour la voix off : ce qui s'est vraiment
      passé, la phrase drôle, le chiffre surprenant.
