# Découpage en épisodes et scripts

Quatre saisons qui suivent les phases du projet. La saison 1 (la
maquette) est écrite plan par plan : ses étapes sont connues et
documentées dans le dépôt. Les saisons 2 à 4 sont des synopsis avec
accroche et plans obligatoires ; elles seront détaillées quand la
conception correspondante existera, en gardant le même gabarit.

Gabarit d'une fiche : accroche (les deux premières secondes), l'idée
unique, la liste des plans, la voix off, le texte à l'écran, la
rubrique du jour (le chiffre, la décision, le raté), la relance vers
l'épisode suivant, et les notes de tournage. Les durées de plans sont
indicatives ; la voix off est écrite pour être dite, pas lue : la
raccourcir au montage plutôt que de l'accélérer.

Convention de numérotation : E00 à E30. Chaque épisode publié allume
une case du plateau de progression (a1, b1, c1... en lisant les
rangées).

Rappel de la règle du secret : avant l'épisode E29, le destinataire
s'appelle « notre pote » à l'écran et dans les descriptions.

## Saison 1. La maquette 2 x 2

Ce que la saison raconte : une idée (reconnaître une pièce par sa
note), une conception faite entièrement par des programmes, deux
cartes commandées, une maquette assemblée à la main, et la mesure qui
décide si l'architecture tient. Fin de saison : la maquette reconnaît
quatre pièces et allume leurs cases.

### E00. Teaser : « On construit un échiquier qui joue tout seul »

- **Accroche** : plan macro d'une pièce qui glisse seule sur un
  plateau (à défaut, en attendant le portique : une pièce déplacée
  à la main hors champ par un aimant sous une planche), texte
  « aucune main ».
- **Idée** : poser la promesse et les règles du jeu de la série.
- **Plans** :
  1. La pièce qui glisse (2 s, ralenti).
  2. Les deux mains qui se serrent au-dessus du plan de travail (1 s).
  3. Rafale de 6 plans de 0,5 s : spirale de cuivre, fil émaillé,
     imprimante 3D, écran de routage, oscilloscope, contreplaqué.
  4. Un calendrier avec une date entourée, floutée (1 s).
  5. Face caméra à deux : « et il ne doit rien savoir » (3 s).
  6. Plateau de progression vide, puis la case a1 s'allume (1 s).
- **Voix off** : « On va construire un échiquier qui reconnaît chaque
  pièce, qui les déplace tout seul, et qui joue contre toi. De zéro.
  Deux cartes électroniques, un portique, du bois, et beaucoup de
  soudure. C'est pour l'anniversaire d'un pote. Il ne doit rien
  savoir. Suis-nous, on te montre tout, y compris ce qui rate. »
- **Texte à l'écran** : AUCUNE MAIN / DE ZÉRO / IL NE SAIT RIEN /
  J moins N.
- **Rubrique** : le compte à rebours apparaît pour la première fois.
- **Relance** : « Épisode 1 : comment un plateau peut savoir qu'un
  cavalier est un cavalier, sans caméra. »
- **Tournage** : les plans de rafale se prennent tout au long de la
  saison ; monter le teaser en dernier, le publier en premier. La
  pièce qui glisse : un aimant néodyme sous une planche de 3 mm et
  une pièce avec un disque ferrite collé, filmé à 60 i/s.

### E01. Chaque pièce a sa note

- **Accroche** : douze notes jouées vite (la signature), texte
  « 12 pièces, 12 notes ».
- **Idée** : le plateau reconnaît une pièce parce qu'elle contient un
  résonateur LC passif accordé sur une fréquence qui lui est propre.
  Pas de caméra, pas de pile dans la pièce.
- **Plans** :
  1. Un verre à pied qu'on fait tinter avec l'ongle (2 s).
  2. Trois verres remplis à des niveaux différents, trois notes (3 s).
  3. Macro : une bobine plate et un condensateur dans la paume (3 s).
  4. Dessin au feutre sur le contreplaqué : une bobine sous la case,
     une bobine dans la pièce, une flèche « on tape, on écoute » (5 s).
  5. Écran : la courbe d'un ringdown, sinusoïde qui s'éteint (3 s).
  6. Écran : le plan de fréquences, douze traits de 217 à 613 kHz
     (3 s), recadré depuis `frequency-plan.svg`.
  7. Face caméra : « et le condensateur, c'est le niveau d'eau dans le
     verre » (3 s).
- **Voix off** : « Comment un plateau sait-il qu'un cavalier est un
  cavalier ? Pas de caméra, pas de puce, pas de pile. Chaque pièce
  cache une bobine et un condensateur. Ensemble, ça fait un
  résonateur : on lui donne un coup, il vibre à sa fréquence, comme un
  verre. Le condensateur règle la note. Douze valeurs, douze notes, de
  217 à 613 kilohertz. Sous chaque case, une bobine tape et écoute à
  travers le bois. Le plateau entend la note, il sait qui est là. »
- **Texte à l'écran** : PAS DE CAMÉRA / UNE BOBINE + UN CONDO /
  ON TAPE, ON ÉCOUTE / 217 à 613 kHz.
- **Le chiffre** : 12. « Douze classes : six pièces, deux couleurs. »
- **La décision** : 0001, résonateurs LC passifs. « Zéro
  électronique dans la pièce, elle ne tombe jamais en panne. »
- **Relance** : « Mais si tout est décidé par un seul fichier, qui a
  raison quand on se trompe ? Épisode 2. »
- **Tournage** : cuisine (verres), plan de travail (macro). La bobine
  et le condensateur peuvent venir d'un premier essai de bobinage,
  même moche. Le ringdown peut être une animation avant d'avoir la
  vraie mesure (à remplacer par la vraie dans E09).

### E02. Le fichier qui commande tout

- **Accroche** : un pion qu'on fait avancer de e2 à e4 et qui se
  coince entre deux pièces, texte « bloqué dès le premier coup ».
- **Idée** : toutes les dimensions du projet viennent d'un seul
  fichier, et un test empêche de casser le plateau par une mauvaise
  valeur. La contrainte reine : une pièce en mouvement doit passer
  entre deux pièces posées.
- **Plans** :
  1. Deux pièces posées, une troisième qu'on tente de faire passer
     entre les deux, elle accroche (3 s, vue du dessus).
  2. Écran : `config/board.yaml` qui défile, zoom sur `pitch` avec
     ses deux valeurs 40 et 50 (3 s).
  3. Dessin sur le contreplaqué : deux cercles, une flèche, la formule
     r mobile + r statique <= p/2 (4 s).
  4. Écran : on change une valeur, on lance `pytest`, il passe au
     rouge (3 s).
  5. Écran : on remet la valeur, tout est vert, « 66 passed » (2 s).
  6. Face caméra Romain : « du coup on ne sait pas encore si les
     cases feront 40 ou 50 millimètres » (3 s).
- **Voix off** : « Tout le projet tient dans un seul fichier : la
  taille des cases, les bobines, les aimants, les fréquences. Le
  code, les cartes, les pièces imprimées : tout est calculé à partir
  de lui. Et il y a une règle qu'on n'a pas le droit de casser : une
  pièce qui se déplace doit passer entre deux pièces posées. Si je
  mets une valeur qui viole ça, un test devient rouge et rien ne
  part en fabrication. Parce que sinon, la partie se bloque dès
  e2-e4. »
- **Texte à l'écran** : UN SEUL FICHIER / r + r <= p/2 / ROUGE =
  INTERDIT / 40 ou 50 mm ?
- **Le chiffre** : 21. « Vingt et une paires de pièces à faire passer
  l'une à côté de l'autre. »
- **La décision** : 0006, le pas de case reste ouvert. « On tranchera
  sur mesure, pas sur intuition. »
- **Relance** : « Et les cartes électroniques ? Personne ne les a
  dessinées. Épisode 3. »
- **Tournage** : les plans écran s'enregistrent en une session avec
  un terminal en police 2x et fond sombre.

### E03. Des cartes dessinées par un programme

- **Accroche** : timelapse du routage, des centaines de pistes qui
  apparaissent en 2 s, texte « personne n'a dessiné ça ».
- **Idée** : les deux cartes de la maquette sont générées par des
  scripts (spirales, schéma, placement, routage), et il reste sept
  liaisons qu'un humain doit finir à la main. Montrer la fierté et la
  limite.
- **Plans** :
  1. Timelapse de routage (enregistrement d'écran d'une régénération,
     accéléré) (3 s).
  2. Écran : la carte bobines, zoom sur une spirale, quatre couches
     qui se superposent (3 s), depuis `coil-board.png` ou pcbnew.
  3. Écran : la carte analogique, vue entière puis zoom sur le
     « chevelu », les fils fins qui restent à router (3 s).
  4. Plan de travail : Romain et Étienne devant l'écran, KiCad
     ouvert, une piste tirée à la main, soupir (4 s).
  5. Écran : DRC zéro, puis le bouton d'export des gerbers (2 s).
  6. Match cut : le rendu 3D de la carte devient (plus tard) la vraie
     carte. Laisser le raccord ouvert pour E07.
- **Voix off** : « Ces cartes, on ne les a pas dessinées. On a écrit
  des programmes qui les dessinent à partir du fichier : les
  spirales des bobines sur quatre couches, le schéma, le placement,
  le routage. Quatre cent quatre-vingt-dix-neuf pistes, deux cent
  cinquante-neuf vias, zéro erreur de fabrication. Sauf que le
  routeur maison a une limite : sept liaisons coincées dans les
  couloirs trop serrés. Celles-là, on les finit à la main. Un quart
  d'heure. Et on peut commander. »
- **Texte à l'écran** : GÉNÉRÉ / 499 PISTES / 7 À LA MAIN / DRC : 0.
- **Le raté** : la bataille du routage (57 liaisons ouvertes, puis
  51, 46, 40, 21, 16, 12, 9 : afficher la suite en mono, un chiffre
  par 0,3 s). « Deux nuits blanches pour passer de cinquante-sept à sept. »
- **Relance** : « Maintenant, il faut payer. Chine ou Europe ?
  Épisode 4. »
- **Tournage** : enregistrer l'écran pendant `export.sh` et une
  régénération complète ([runbook](../notes/08-regenerer.md)), puis
  filmer la vraie finition pcbnew des sept nets. Corriger le jack J1
  à l'écran pendant qu'on y est (note 07), ça fait un bon raté.

### E04. Commander : Chine ou Europe ?

- **Accroche** : deux prix côte à côte pour la même puce, « 8,91 »
  et « 3,69 », texte « même puce ».
- **Idée** : où commander quoi, et pourquoi le panaché gagne. Un
  épisode « argent » assumé, les gens adorent.
- **Plans** :
  1. Écran : la fiche d'approvisionnement, deux colonnes Europe et
     Asie (2 s).
  2. Carton : AD8421, 8,91 USD contre 3,69 USD (2 s).
  3. Carton : Nucleo, 17 EUR en Europe contre 29 EUR en revendeur
     asiatique, « l'inverse » (2 s).
  4. Écran : le panier JLCPCB, la prévisualisation d'assemblage, une
     ligne à vérifier (4 s).
  5. Face caméra Étienne : « les aimants, on les prend en Europe : la
     nuance, c'est le paramètre pivot du projet » (3 s).
  6. Le clic sur payer, quatre fois (4 s, montage rapide).
  7. Un calendrier : « 2 à 5 semaines » (1 s).
- **Voix off** : « Pour la même puce, huit quatre-vingt-onze en
  Europe, trois soixante-neuf en Asie. Alors tout en Chine ? Non. La
  carte Nucleo est moins chère et plus sûre en Europe. Les aimants
  aussi : on a besoin d'une nuance précise de ferrite, et là-bas, on
  ne peut pas vérifier. Donc quatre commandes : les cartes et les
  puces assemblées chez JLCPCB, la Nucleo chez ST, les aimants et le
  fil émaillé en Europe. Cent soixante à cent quatre-vingts euros, et
  deux à cinq semaines d'attente. »
- **Texte à l'écran** : MÊME PUCE / x2,4 / 4 COMMANDES / 160 à 180
  EUR / 2 à 5 SEMAINES.
- **Le chiffre** : 138. « Cent trente-huit composants sur la carte
  analogique, dont un QFN. Non, on ne les soude pas à la main. »
- **Relance** : « Cinq semaines, c'est long. On imprime. Épisode 5. »
- **Tournage** : le jour de la commande réelle. Filmer les écrans de
  paiement sans numéros de carte ni adresse (cadrer serré ou flouter).

### E05. Pendant qu'on attend : l'imprimante

- **Accroche** : macro d'une buse qui dépose la première couche d'un
  puck, texte « en attendant la Chine ».
- **Idée** : la mécanique de la maquette est elle aussi générée
  depuis le fichier (CadQuery) : pucks de test, gabarits de bobinage,
  support d'aimant réglable, gabarit de perçage. Tout sort de
  l'imprimante en une soirée.
- **Plans** :
  1. Écran : `build_all.py` qui tourne, les STL qui apparaissent (2 s).
  2. Écran : la vue éclatée du puck (`piece-exploded.png`), rotation
     (2 s).
  3. Match cut : le puck à l'écran devient le puck sur le plateau
     d'impression (2 s).
  4. Timelapse d'impression, 3 s.
  5. Table vue du dessus : les pièces alignées, on les nomme une à une
     avec un texte (pucks, noyaux, flasques, platine, coupelle,
     gabarit) (5 s).
  6. Macro : la fente latérale du puck pour le condensateur, un doigt
     qui montre (2 s).
  7. Romain qui visse la coupelle sur la platine, la fait monter et
     descendre (3 s).
- **Voix off** : « Les pièces mécaniques aussi sortent du fichier :
  un script produit les modèles, l'imprimante fait le reste. Des
  pucks de test, avec la poche pour la bobine, celle pour l'aimant,
  et une fente pour le condensateur. Des gabarits pour bobiner à la
  bonne taille. Un support d'aimant réglable, un demi-millimètre par
  tour de vis, pour une mesure qu'on te montrera plus tard. Et un
  gabarit de perçage pour la surface en bois. Quatre-vingt-dix
  grammes de plastique, trois euros. »
- **Texte à l'écran** : GÉNÉRÉ AUSSI / PUCK / GABARIT / 0,5 mm PAR
  TOUR / 90 g.
- **Le chiffre** : 90 g. « Toute la mécanique de la maquette. »
- **Le raté** : si une impression échoue (elle échouera), la garder.
- **Relance** : « Le gabarit de bobinage, c'est pour ça. Épisode 6 :
  on bobine à la main. »
- **Tournage** : imprimante, soirée. Prévoir un timelapse depuis le
  téléphone posé, mode intervalle.

### E06. Bobiner à la main

- **Accroche** : perceuse qui tourne, le fil qui s'enroule, texte
  « 45 microhenrys, à la main ».
- **Idée** : les bobines des pièces sont plates, en fil émaillé de
  0,25 mm, bobinées sur un gabarit monté dans une perceuse, collées
  au vernis. On vérifie l'inductance au LCR-mètre si on en a un, sinon
  on fait confiance à la mesure de l'épisode 9.
- **Plans** :
  1. Le noyau et la flasque montés sur l'axe M3 dans le mandrin (2 s).
  2. Le fil qui part de l'encoche, premier tour à la main (2 s).
  3. Perceuse en vitesse lente, le fil qui monte en spirale plate,
     macro (4 s).
  4. Pinceau de vernis, on attend, on retire la flasque (3 s).
  5. La bobine plate dans la paume, à côté d'une pièce de deux euros
     (2 s).
  6. Si LCR-mètre : l'écran qui affiche l'inductance (2 s). Sinon :
     quatre bobines alignées, « on saura à l'épisode 9 » (2 s).
  7. Soudure du condensateur C0G aux deux fils, mise en place dans la
     fente du puck (4 s).
  8. Le raté : le fil qui casse ou une bobine qui se défait au
     démoulage (2 s).
- **Voix off** : « Une bobine plate, quarante-cinq microhenrys, en
  fil émaillé d'un quart de millimètre. Le gabarit imprimé donne le
  diamètre, la perceuse fait les tours, le vernis fige le tout. On
  en fait quatre pour la maquette, plus une de rechange, et surtout
  quatre identiques : on veut savoir si des bobines faites à la main
  se ressemblent assez pour ne pas avoir à les trier. Puis on soude
  le condensateur qui fixe la note, et on glisse tout dans le
  puck. »
- **Texte à l'écran** : 45 µH / FIL 0,25 / VERNIS / 4 IDENTIQUES ? /
  12 nF = PION.
- **Le chiffre** : 4 x 12 nF, 10 nF, 8,2 nF, 6,8 nF. « Les quatre
  notes du bas de la gamme : si celles-là se distinguent, les autres
  suivront. »
- **Relance** : « Le facteur sonne à la porte. Épisode 7. »
- **Tournage** : atelier, lampe rasante pour la macro du fil.
  Bobiner quatre fois exactement de la même manière (mesure M6).

### E07. Le colis

- **Accroche** : cutter sur le carton, texte « 5 semaines ».
- **Idée** : déballage, inspection, comparaison rendu contre réel, et
  le premier allumage sans rien de branché derrière. Épisode plaisir.
- **Plans** :
  1. Ouverture du carton, sachets sous vide (3 s).
  2. Match cut attendu depuis E03 : le rendu de la carte analogique
     devient la vraie carte (2 s).
  3. Macro des spirales de cuivre de la carte bobines, lumière rasante
     (3 s).
  4. Loupe sur le QFN du buck, « c'est bien soudé » (2 s).
  5. Les deux cartes assemblées bord à bord sur le connecteur 12
     broches (3 s).
  6. Alimentation 12 V branchée, doigt sur le régulateur : pas chaud,
     multimètre sur le 5 V et le 3,3 V (4 s).
  7. Les deux face caméra, soulagés (2 s).
- **Voix off** : « Cinq semaines plus tard. Deux cartes bobines nues,
  deux cartes analogiques assemblées, cent trente-huit composants
  posés par un robot. On vérifie tout à la loupe, on compare au
  rendu, on branche le 12 volts en retenant notre souffle. Cinq
  volts, trois virgule trois. Rien ne fume. On peut respirer. »
- **Texte à l'écran** : 5 SEMAINES / RENDU vs RÉEL / RIEN NE FUME /
  5,0 V.
- **Le raté** : le composant manquant ou l'erreur de référence, s'il y
  en a (voir la liste à vérifier au panier dans le
  [guide](../../hardware/mockup-2x2/README.md)). S'il n'y en a pas,
  le dire : « pour une fois ».
- **Relance** : « Avant de brancher le cerveau, il faut le bois.
  Épisode 8. »
- **Tournage** : le jour de la livraison, sans préparation, c'est le
  charme. Lampe rasante et macro prêtes à l'avance.

### E08. Le bois

- **Accroche** : mèche qui traverse le contreplaqué, texte « deux
  trous par case ».
- **Idée** : la surface de jeu est en contreplaqué percé au gabarit :
  quatre trous de fixation et deux points lumineux par case, aux coins
  opposés, pour afficher le camp qui occupe la case. Le bois est
  transparent au champ de mesure.
- **Plans** :
  1. Le gabarit imprimé scotché sur la planche (2 s).
  2. Perçage des trous de 2,5 mm, sciure, vue du dessus (4 s).
  3. Dessin sur la planche : pourquoi deux coins opposés (un coin
     partagé entre deux cases de camps différents serait ambigu) (4 s).
  4. Époxy translucide dans les trous, spatule, surface affleurante
     (3 s).
  5. La planche posée sur la carte bobines, entretoises, vis M3 (3 s).
  6. Feutre adhésif, lissage (2 s).
  7. Une LED qui s'allume à travers le bois, en amorce (1 s, teaser
     de E12).
- **Voix off** : « Le plateau sera en bois. Le bois ne gêne pas la
  mesure : seule l'épaisseur compte, et l'humidité, qu'on mesurera.
  Le gabarit imprimé place tout : les vis, et deux points lumineux
  par case, aux coins opposés, pour dire quel camp occupe la case.
  Deux coins opposés, parce qu'un coin partagé entre deux cases de
  couleurs différentes ne voudrait rien dire. On perce, on remplit
  d'époxy, on ponce, on colle le feutre. »
- **Texte à l'écran** : 2 POINTS PAR CASE / COINS OPPOSÉS / ÉPOXY /
  FEUTRE.
- **La décision** : 0009, LED de camp et surface bois. « Le rendu des
  plateaux du commerce, la mesure en plus. »
- **Relance** : « Le cerveau, maintenant. Épisode 9 : est-ce qu'elle
  chante ? »
- **Tournage** : atelier de Romain, aspirateur à portée pour les
  plans propres. Filmer aussi la version acrylique si elle existe,
  pour la mesure M10.

### E09. Premier signal

- **Accroche** : un oscilloscope où apparaît une sinusoïde qui
  s'éteint, texte « elle chante ». C'est l'épisode le plus important
  de la saison après E10.
- **Idée** : câbler la Nucleo, flasher, lancer un dump brut, et voir
  le premier ringdown d'une vraie pièce sur une vraie case. Puis
  l'entendre : on ramène la fréquence dans l'audible.
- **Plans** :
  1. Nappes Dupont branchées une à une selon la table du guide, vue
     du dessus (4 s, accéléré).
  2. Écran : `make`, puis la copie du binaire sur le lecteur NUCLEO
     (2 s).
  3. Console série : le bandeau de démarrage, « 3,78 Méch/s » (2 s).
  4. Le puck 12 nF posé sur la case 1, main qui se retire (1 s).
  5. Console : commande `r`, 512 nombres qui défilent (2 s).
  6. Écran : le notebook trace la courbe, une sinusoïde qui s'éteint
     (3 s).
  7. Oscilloscope sur TP2, la même courbe en vrai (3 s).
  8. Le son : la courbe rejouée mille fois plus lentement, une note
     qui s'éteint, face caméra les deux qui écoutent (4 s).
  9. Console : `s`, une ligne CSV, la colonne fa proche de 217 000
     (2 s).
- **Voix off** : « Vingt nappes, un binaire, un port série. On pose
  la pièce sur la case, et on demande au plateau ce qu'il entend.
  Cinq cent douze échantillons. Une sinusoïde qui s'éteint : c'est
  la pièce qui vibre, à travers le bois, à deux cent dix-sept
  kilohertz. On ne peut pas l'entendre. Alors on la ralentit mille
  fois. Voilà. C'est la note du pion noir. »
- **Texte à l'écran** : 20 NAPPES / 512 POINTS / 217 kHz / x1000 /
  ELLE CHANTE.
- **Le chiffre** : 3,78 Méch/s. « Le convertisseur écoute presque
  quatre millions de fois par seconde. »
- **Le raté** : le premier branchement qui ne marche pas (il y en
  aura un : une nappe décalée d'une broche). Le montrer avec le
  tableau des nappes à l'écran.
- **Relance** : « Maintenant, la mesure qui peut tout faire tomber.
  Épisode 10. »
- **Tournage** : plan de travail, deux téléphones (un sur l'écran, un
  sur les mains). Remplacer rétroactivement l'animation de E01 par la
  vraie courbe si E01 n'est pas encore publié.

### E10. La mesure qui peut tout faire tomber

- **Accroche** : une main qui approche un aimant d'un puck, ralenti,
  texte « si ça rate, on recommence tout ».
- **Idée** : l'aimant de pièce est indispensable (c'est lui que le
  portique attrapera) mais un aimant tue la résonance. Le pari du
  projet : un aimant en ferrite, transparent au champ de mesure, à
  la place du néodyme. La mesure M2 dit si le pari tient : le facteur
  de qualité Q doit rester au-dessus de 30 et chuter de moins de
  20 %.
- **Plans** :
  1. Deux disques dans la paume : le ferrite noir mat et le néodyme
     nickelé brillant (2 s).
  2. Dessin sur la planche : Q, la note qui dure ou qui s'étouffe,
     deux courbes (4 s).
  3. Mesure sans aimant, console, `r`, courbe, texte « Q = ... » (3 s).
  4. Insertion du ferrite dans la poche du puck, macro (2 s).
  5. Silence, le puck posé, `r`, la courbe apparaît (4 s, le suspense).
  6. Carton mono : Q avant, Q après, la chute en pourcentage (3 s).
  7. Face caméra : verdict, quel qu'il soit (4 s).
- **Voix off** : « Chaque pièce doit avoir un aimant, pour que le
  portique puisse la tirer. Mais un aimant, ça étouffe la vibration.
  Tout le projet repose sur un pari : utiliser de la ferrite, un
  aimant faible et invisible pour la mesure, au lieu du néodyme.
  Sans aimant, la note dure. On insère le ferrite. Si la note
  s'étouffe de plus de vingt pour cent, on repart de zéro. »
  Fin à écrire le jour même, avec les vrais chiffres.
- **Texte à l'écran** : FERRITE vs NÉODYME / Q / SANS : ... / AVEC :
  ... / VERDICT.
- **La décision** : 0002, ferrite dure, jamais néodyme. « La décision
  pivot du projet, jugée aujourd'hui. »
- **Relance** : si ça tient : « Et avec du néodyme, ça donne quoi ?
  Épisode 11. » Si ça rate : « On a un plan B. Épisode 11. » (repli
  du protocole : fil de Litz, puis reed switches).
- **Tournage** : ne pas tricher sur le suspense : tourner en une prise
  continue en plus des plans de coupe, pour avoir la vraie réaction.

### E11. Pourquoi pas le néodyme

- **Accroche** : un aimant néodyme sous une planche, trois pièces qui
  se retournent et s'agglutinent, ralenti, texte « voilà pourquoi ».
- **Idée** : le néodyme dans les pièces aurait deux défauts : il
  étouffe la note (mesure M3, chute attendue de 40 à 70 %) et un
  aimant fort sous le plateau ferait sauter les pièces voisines. En
  bonus, la mesure M7 : à quelle distance le chariot doit-il se garer
  pour ne pas perturber la mesure.
- **Plans** :
  1. Démonstration des pièces qui se retournent (3 s, 60 i/s).
  2. Un puck avec néodyme, `r`, la courbe qui s'éteint très vite (3 s).
  3. Carton : Q ferrite contre Q néodyme (2 s).
  4. Le support réglable sous la case 3, le N42 dans la coupelle (2 s).
  5. Romain tourne la vis, un demi-millimètre par tour, Étienne lit
     la fréquence à chaque pas (5 s, accéléré, chiffres en mono).
  6. Carton : la distance à partir de laquelle la note bouge de plus
     de 2 kHz (2 s).
- **Voix off** : « Avec du néodyme dans la pièce, la note meurt deux
  fois plus vite, et surtout, dès qu'un aimant fort passe dessous,
  les pièces voisines se retournent. Donc ferrite dans les pièces, et
  le néodyme reste sous le plateau, sur le chariot. Reste à savoir à
  quelle distance ce chariot doit se garer pour ne pas fausser la
  mesure. On le fait monter d'un demi-millimètre par tour, et on
  regarde quand la note commence à bouger. »
- **Texte à l'écran** : NÉODYME : ... % / FERRITE : ... % / 0,5 mm
  PAR TOUR / PARKING : ... mm.
- **Le chiffre** : la distance de parking mesurée.
- **Relance** : « Il est temps de lui apprendre à reconnaître les
  pièces. Épisode 12. »
- **Tournage** : mesures M3 et M7 le même jour. Les pièces qui se
  retournent : pièces d'échecs classiques avec un disque néodyme
  collé dessous, néodyme fort sous la planche.

### E12. Elle reconnaît les pièces

- **Accroche** : quatre pucks posés au hasard, la console affiche
  leurs noms, les LED s'allument aux bonnes couleurs, texte « sans
  regarder ».
- **Idée** : calibration (seize mesures par case, moyennes en
  mémoire), identification au plus proche voisin, LED de camp. Le
  premier moment où la maquette fait ce que le plateau final fera.
  Inclure la diaphonie (M5) : une pièce sur une case n'est pas
  entendue par la voisine.
- **Plans** :
  1. Console : `c`, la calibration défile, seize lignes par case (3 s).
  2. Les pucks mélangés dans une main, yeux fermés, posés au hasard
     (3 s).
  3. Console : `i`, quatre noms (2 s).
  4. Console : `l`, les points lumineux s'allument à travers le bois,
     blanc pour un camp, ambre pour l'autre (3 s, 60 i/s).
  5. On échange deux pucks, on relance, les couleurs suivent (3 s).
  6. Diaphonie : un seul puck sur la case 1, le scan des cases 2 à 4
     reste silencieux, carton « moins de -20 dB » (3 s).
  7. Face caméra à deux, la première vraie joie (3 s).
- **Voix off** : « Seize mesures par case, on apprend la note exacte
  de chaque pièce. Puis on mélange, on pose sans regarder, et on
  demande. Pion, cavalier, fou, tour. On échange deux pièces. Elle
  suit. Et les cases voisines ? Elles n'entendent rien : chaque case
  n'écoute que ce qui est posé dessus. Quatre cases, quatre pièces.
  Il en reste soixante et huit. »
- **Texte à l'écran** : CALIBRATION / SANS REGARDER / PION, CAVALIER,
  FOU, TOUR / LES VOISINES N'ENTENDENT RIEN.
- **Le chiffre** : 16. « Seize mesures par case pour apprendre une
  note. »
- **Relance** : « Bilan de la maquette, et une décision à prendre :
  40 ou 50 millimètres. Épisode 13. »
- **Tournage** : après M4 et M5. Baisser la lumière pour les LED à
  travers le bois. Cet épisode est le premier « payoff » : y mettre
  le plus de soin au montage.

### E13. Bilan : 40 ou 50 ?

- **Accroche** : le tableau de synthèse du protocole qui se remplit
  ligne par ligne, vert, vert, vert, un ambre, texte « verdict ».
- **Idée** : passer en revue ce que la maquette a décidé : la ferrite
  tient (ou pas), le rapport signal sur bruit, la dispersion des
  bobines faites main, le buck contre le LDO, le bois contre
  l'acrylique, les LED qui ne perturbent pas la mesure, la voie
  d'extraction retenue. Et trancher la taille des cases.
- **Plans** :
  1. Le tableau M1 à M11 à l'écran, une ligne à la fois (6 s).
  2. Plan de coupe pour chaque ligne marquante : le Pi en WiFi posé à
     côté de la carte (M8), la plaque d'acrylique contre la planche
     (M10), les LED allumées pendant une mesure (M11) (6 s).
  3. Dessin : deux plateaux, 40 et 50, avec une main d'adulte dessus
     (3 s).
  4. Le chiffre qui décide (SNR, séparation, dispersion) (3 s).
  5. Face caméra : la décision, et ce que ça change pour la suite
     (5 s).
  6. Le plateau de progression : toute la première rangée allumée
     (2 s).
- **Voix off** : « Onze mesures, onze questions. La ferrite : ...
  Le bruit du WiFi du Raspberry : ... Le bois contre le plastique :
  aucune différence. Les LED pendant la mesure : rien. Les bobines
  faites main : ... pour cent d'écart, pas besoin de les trier. Et la
  question qu'on traîne depuis l'épisode 2 : quarante ou cinquante
  millimètres. Verdict : ... Saison 2 : les soixante-quatre cases. »
  À compléter avec le tableau de synthèse rempli.
- **Texte à l'écran** : 11 MESURES / une ligne par verdict / 40 ou
  50 : ... / SAISON 2.
- **La décision** : 0006 close (pas de case) et 0007 close (voie
  d'extraction). Nouveaux ADR à écrire dans le dépôt le même jour.
- **Relance** : bande-annonce de 5 s de la saison 2, avec le plan
  8 x 8 s'il existe déjà.
- **Tournage** : une matinée, une fois le tableau rempli. Réutiliser
  les rushes de M8, M10 et M11 tournés au fil des mesures : prévoir
  dès E09 de filmer chaque mesure, même courte.

## Saison 2. Le plateau 8 x 8

Synopsis : passer de quatre cases à soixante-quatre. Le plateau est
découpé en quatre quadrants (ADR 0004), la chaîne de mesure est
multiplexée, les LED forment une seule chaîne, et la calibration
complète prend du temps. Cette saison est à détailler quand la
conception de la phase 2 existera ; les épisodes ci-dessous en sont
le squelette.

| Épisode | Titre | Accroche | Plans obligatoires |
|---|---|---|---|
| E14 | Soixante-quatre fois plus | le plan 2 x 2 qui se réplique en 8 x 8 à l'écran | dessin des quadrants, le calcul des voies du mux, le chiffre : nombre de LED (81 ou 128 selon le rendu) |
| E15 | Les quatre quadrants | quatre cartes posées bord à bord comme un puzzle | déballage, assemblage, le connecteur entre quadrants, premier scan de 64 cases |
| E16 | Trente-deux pièces | bobinage à la chaîne, timelapse | le kit de 32 résonateurs, 12 classes, tri ou non selon M6, les pièces du commerce ouvertes et équipées |
| E17 | Calibrer tout | le plateau vide, la console qui apprend 64 cases | l'algorithme en dessin, une pièce déposée n'importe où, reconnue partout, la carte de chaleur des fréquences |
| E18 | Une partie entière (sans bouger) | deux joueurs, chaque coup affiché sur l'écran | l'arbitre : roque, prise en passant, promotion, le coup illégal refusé, plateau de progression : deux rangées |

## Saison 3. Le portique et le jeu

Synopsis : le plateau apprend à bouger les pièces. Portique CoreXY
sous le plateau, aimant N42 sur le chariot, distance de parking de
E11 respectée, couloir de E02 enfin mis à l'épreuve. Puis le moteur
d'échecs sur le Raspberry Pi, le jeu en ligne, la batterie.

| Épisode | Titre | Accroche | Plans obligatoires |
|---|---|---|---|
| E19 | Deux moteurs, un chariot | les courroies croisées d'un CoreXY qui bougent, hypnotique | dessin du CoreXY, impression et assemblage, premier mouvement à vide |
| E20 | e2-e4 | la première pièce qui glisse toute seule, ralenti, silence | l'aimant qui monte, la pièce qui part, le retour au parking, le raté (la pièce qui décroche) |
| E21 | Le couloir | un cavalier qui passe entre deux pièces sans les toucher | rappel de E02, la trajectoire à l'écran, le passage en ralenti, mesure de la marge |
| E22 | Le roque | deux pièces qui bougent pour un seul coup | roque, prise avec pièce évacuée hors plateau, promotion, la bande de stockage |
| E23 | Le cerveau optionnel | un Raspberry Pi Zero qui s'éteint entre deux coups | ADR 0003 : le STM32 est maître, le Pi se réveille pour réfléchir, l'UART isolée, le WiFi qui ne perturbe rien (rappel M8) |
| E24 | Elle joue contre nous | une partie complète contre le moteur, accélérée | Romain qui perd, ou pas ; l'ouverture jouée par le plateau ; le coup du chariot pendant que l'humain réfléchit |
| E25 | Sur batterie | débrancher la prise en pleine partie, rien ne s'arrête | budget d'énergie, autonomie calculée puis mesurée, le chiffre |

## Saison 4. Finition et remise

Synopsis : de la machine à l'objet. Le plateau devient beau, les
pièces deviennent des pièces, et le secret prend fin.

| Épisode | Titre | Accroche | Plans obligatoires |
|---|---|---|---|
| E26 | La caisse | rabot sur du bois massif, copeaux | ébénisterie, l'assemblage du cadre, la surface finale, huile, les 128 points lumineux au premier allumage |
| E27 | Les pièces | une pièce du commerce coupée en deux, le résonateur à l'intérieur | ouverture, encastrement, feutre, pesée, la note de chaque pièce jouée en gamme complète : la signature sonore en vrai |
| E28 | Le test final | Étienne contre Romain, partie complète, sans un mot | tout ce qui marche, un dernier raté et sa correction, l'emballage |
| E29 | Joyeux anniversaire | Ayglon qui ouvre le paquet | la réaction en une prise continue, le premier coup joué, le plateau qui répond ; premier épisode où son prénom apparaît |
| E30 | Épilogue | le plateau de progression, 64 cases allumées | Ayglon qui joue seul contre le plateau, remerciements, ce qu'on ferait autrement, le coût total, le temps total |

## Épisodes bonus (à tourner si l'occasion se présente)

- **Le routeur** : dix minutes de coulisses en format long (YouTube)
  sur la bataille du routage et les trois garanties de la note 04.
  Le public technique le réclamera.
- **Le budget** : un épisode récapitulatif chiffré à la fin de chaque
  saison.
- **Questions du public** : répondre en un épisode aux trois
  questions les plus posées (typiquement : « pourquoi pas des
  capteurs à effet Hall », « pourquoi pas la RFID », « ça coûte
  combien »). Les réponses sont dans les ADR 0001 et 0002.
